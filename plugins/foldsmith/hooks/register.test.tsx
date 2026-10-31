import type { On } from 'claude-code'
import { expect, test } from 'claude-code/testing'

const PANE = {
  plugin: 'foldsmith',
  component: 'Pane',
  requestId: 'foldsmith',
  props: {
    title: 'Foldsmith',
    isFocused: false,
    bodyColumns: 80,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 40 },
    view: {},
  },
} as const

const STATUS = JSON.stringify({
  app: 'Notes',
  phase: 'audit',
  poses: ['closed', 'book', 'tent'],
  screens: [{ name: 'Folders', cells: { book: { state: 'finding', label: 'T5' } } }],
  log: ['10:00 Captured 3 poses'],
})

const MIGRATED = JSON.stringify({
  app: 'Notes',
  phase: 'verify',
  poses: ['closed', 'book'],
  screens: [
    {
      name: 'Folders',
      pattern: 'Fold-aligned split',
      cells: {
        closed: { state: 'unchanged' },
        book: { state: 'verified', label: 'split', before: '.duo/captures/Notes/before/folders-book-inner.png', after: '.duo/captures/Notes/after/folders-book-inner.png' },
      },
    },
    { name: 'Note', cells: { closed: { state: 'unchanged' }, book: { state: 'finding', label: 'T14', finding: 'T14 T1' } } },
  ],
})

// Paths to the files the plugin may read; a progress file is any key ending in .duo/migration.json.
type Files = { [path: string]: string }

// Stands for the engine and the Mac beneath the plugin: the files, find, git, sips, the store and the clock. `links` maps
// each symbolic link to where it leads. `faults.find` makes find fail as a timed-out one does, `faults.store` makes reading
// the store fail, `faults.stored` fills the store first, and `faults.timers` collects each timer's interval. It returns
// every program the plugin ran, as its argv.
function machine(
  on: On,
  files: Files,
  mtime: (path: string) => number = () => 1,
  links: { [path: string]: string } = {},
  faults: { find?: boolean; store?: boolean; stored?: { [key: string]: unknown }; timers?: number[] } = {},
) {
  const store: { [key: string]: unknown } = { ...faults.stored }
  const runs: string[][] = []
  on('command.register', () => ({ value: { command: 'foldsmith' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('clock.every', (_, e) => {
    faults.timers?.push(e.ms)
    return { value: undefined }
  })
  on('ui.panes', () => ({ value: [] }))
  on('store.get', (_, e) => (faults.store ? { deny: 'store unavailable' } : { value: store[e.key] }))
  on('store.set', (_, e) => {
    store[e.key] = e.value
    return { value: undefined }
  })
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('fs.exists', (_, e) => ({ value: e.path in files || e.path.endsWith('.png') }))
  const real = (path: string) =>
    links[path] ?? `/${path.split('/').reduce((parts: string[], part) => (part === '..' ? parts.slice(0, -1) : part && part !== '.' ? [...parts, part] : parts), []).join('/')}`
  on('fs.stat', (_, e) => ({
    value: {
      kind: /\/(\.duo|captures)$/.test(e.path) ? 'dir' : 'file',
      size: 10,
      mtimeMs: mtime(e.path),
      isLink: e.path in links,
      ...(e.resolve ? { realPath: real(e.path) } : {}),
    },
  }))
  on('fs.read', (_, e) => ({ value: e.as === 'bytes' ? { base64: 'SlBFRw==' } : files[e.path] ?? '' }))
  on('process.run', (_, e) => {
    runs.push([...e.argv])
    const command = e.argv[0].split('/').pop()
    if (command === 'find' && faults.find) return { deny: 'timed out after 8000 ms' }
    const stdout = e.argv.includes('-g')
      ? 'x.jpg\n  pixelWidth: 720\n  pixelHeight: 506\n'
      : command === 'printenv'
        ? '/Users/me\n'
        : command === 'find'
          ? Object.keys(files).filter(path => path.endsWith('/.duo/migration.json')).join('\n')
          : command === 'git'
            ? 'duo-migration\n'
            : ''
    return { value: { exitCode: 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  return runs
}

test('with no progress file the pane says so and offers to start, on every surface', async ($, on) => {
  machine(on, {})
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    expect(await ui.find({ type: 'Text', text: /No migration in this folder/ })).toBeDefined()
    expect(await ui.find({ key: 'start' })).toBeDefined()
    await ui.unmount()
  }
})

test('the progress file drives the header, totals and matrix', async ($, on) => {
  machine(on, { '/app/.duo/migration.json': STATUS })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const desktop = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect((await desktop.find({ type: 'Text', text: /^Notes$/ }))?.text).toBe('Notes')
  expect((await desktop.find({ type: 'Text', text: /^● Audit$/ }))?.text).toBe('● Audit')
  expect((await desktop.find({ type: 'Text', text: /branch/ }))?.text).toBe('this folder · branch duo-migration')
  expect((await desktop.find({ type: 'Text', text: /screens finished/ }))?.text).toContain('0 of 1 screens finished')
  expect((await desktop.find({ type: 'Text', text: /screens finished/ }))?.text).toContain('1 with defects')
  const matrix = (await desktop.findAll({ type: 'Svg' })).find(svg => String(svg.props.alt).includes('matrix'))
  expect(matrix?.props.isInteractive).toBe(true)
  expect(String(matrix?.props.source)).toContain('Folders · Book: Defect (T5 stretched-single-column)')
  await desktop.unmount()

  const terminal = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await terminal.find({ type: 'Text', text: /Folders/ }))?.text).toContain('✗')
  expect((await terminal.find({ type: 'Text', text: /TENT/ }))?.text).toContain('BOOK')
  await terminal.unmount()
})

test('done and left are read off the cells when the skill keeps no lists', async ($, on) => {
  machine(on, { '/app/.duo/migration.json': MIGRATED })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect((await ui.find({ type: 'Text', text: /screens finished/ }))?.text).toContain('1 of 2 screens finished · 3 of 4 poses good')
  expect((await ui.find({ type: 'Text', text: /^✓ Folders/ }))?.text).toBe('✓ Folders: Fold-aligned split')
  expect((await ui.find({ type: 'Text', text: /^○ Note/ }))?.text).toBe('○ Note: Book T14')
  await ui.unmount()
})

test("the skill's own done and todo lists win", async ($, on) => {
  const status = JSON.stringify({ ...JSON.parse(MIGRATED), done: ['Folders: split'], todo: ['Note: no pattern yet', 'Folders: verify tent'] })
  machine(on, { '/app/.duo/migration.json': status })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /^Left/ }))?.text).toBe('Left (2)')
  expect(await ui.find({ type: 'Text', text: /○ Note: no pattern yet/ })).toBeDefined()
  expect((await ui.find({ type: 'Text', text: /^Done/ }))?.text).toBe('Done (1)')
  await ui.unmount()
})

test('the pane opens on a defect, names its classes and steps through the cells', async ($, on) => {
  const status = JSON.stringify({ ...JSON.parse(MIGRATED), todo: ['Note: the pane edge sits on the fold'] })
  machine(on, { '/app/.duo/migration.json': status })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect((await ui.find({ key: 'screen' }))?.props.value).toBe('Note')
  expect((await ui.find({ key: 'pose' }))?.props.value).toBe('book')
  expect(await ui.find({ type: 'Text', text: /^T14 columns-off-fold · T1 crease-straddle$/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^the pane edge sits on the fold$/ })).toBeDefined()

  await ui.press({ key: 'prev' })
  expect((await ui.find({ key: 'pose' }))?.props.value).toBe('closed')
  await ui.press({ key: 'next-defect' })
  expect((await ui.find({ key: 'pose' }))?.props.value).toBe('book')
  await ui.unmount()
})

test('before and after are drawn with the fold where the phone bends', async ($, on) => {
  machine(on, { '/app/.duo/migration.json': MIGRATED })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  await ui.select({ key: 'screen', value: 'Folders' })
  const pair = JSON.stringify((await ui.find({ key: 'pair' }))?.children)
  expect(pair).toContain('Folders in Book, before')
  expect(pair).toContain('href=\\"data:image/jpeg;base64,SlBFRw==\\"')
  expect(pair).toContain('class=\\"fold active\\"')
  expect(await ui.find({ key: 'open-after' })).toBeDefined()

  await ui.select({ key: 'pose', value: 'closed' })
  expect(JSON.stringify((await ui.find({ key: 'pair' }))?.children)).not.toContain('class=\\"fold')
  await ui.unmount()
})

test('a wide pane draws the matrix across it, with what is left and done beside the picked cell', async ($, on) => {
  machine(on, { '/app/.duo/migration.json': MIGRATED })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const wide = await $.ui.mount({ ...PANE, props: { ...PANE.props, bodyColumns: 130 }, surface: 'desktop' })
  const matrix = (await wide.findAll({ type: 'Svg' })).find(svg => String(svg.props.alt).includes('matrix'))
  expect(Number(matrix?.props.width)).toBeGreaterThan(440)
  expect(String(matrix?.props.source)).toContain(`height="${matrix?.props.height}"`)
  const columns = await wide.find({ key: 'columns' })
  expect(columns?.props.flexDirection).toBe('row')
  const [standing, inspector] = (columns?.children ?? []).map(child => JSON.stringify(child))
  expect(standing).toContain('Folders: Fold-aligned split')
  expect(inspector).toContain('Note in Book, before')
  await wide.unmount()

  // One column: what is left and done comes before the picked cell's shots.
  const narrow = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const stacked = await narrow.find({ key: 'columns' })
  expect(stacked?.props.flexDirection).toBe('column')
  const [first, second] = (stacked?.children ?? []).map(child => JSON.stringify(child))
  expect(first).toContain('Folders: Fold-aligned split')
  expect(first).not.toContain('Note in Book, before')
  expect(second).toContain('Note in Book, before')
  await narrow.unmount()
})

test('the pane follows the newest progress file under the folder, and switches on a pick', async ($, on) => {
  const older = JSON.stringify({ ...JSON.parse(STATUS), app: 'Old' })
  const newer = JSON.stringify({ ...JSON.parse(MIGRATED), app: 'New' })
  machine(on, { '/work/a/.duo/migration.json': older, '/work/b/.duo/migration.json': newer }, path => (path.startsWith('/work/b') ? 5 : 1))
  await $.session.start({ cwd: '/work', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: /^New$/ })).toBeDefined()
  expect((await ui.find({ type: 'Text', text: /branch/ }))?.text).toBe('b · branch duo-migration')
  expect((await ui.find({ key: 'app' }))?.props.value).toBe('/work/b')

  await ui.select({ key: 'app', value: '/work/a' })
  expect(await ui.find({ type: 'Text', text: /^Old$/ })).toBeDefined()
  await ui.unmount()
})

test('a finished migration starts with the simulator paused and offers what is left', async ($, on) => {
  const status = JSON.stringify({ ...JSON.parse(MIGRATED), phase: 'done', todo: ['Note: three levels, a design call'] })
  machine(on, { '/app/.duo/migration.json': status, '/app/.duo/REPORT.md': '# Report' })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect((await ui.find({ type: 'Text', text: /^Finished/ }))?.text).toBe('Finished · 1 left for you')
  expect((await ui.find({ type: 'Text', text: /^paused$/ }))?.text).toBe('paused')
  expect((await ui.find({ key: 'live' }))?.props.label).toBe('Resume')
  expect((await ui.find({ key: 'resume' }))?.props.label).toBe('Resume migration')
  expect(await ui.find({ key: 'report' })).toBeDefined()
  expect((await ui.find({ type: 'Text', text: /^Left for you/ }))?.text).toBe('Left for you (1)')
  await ui.unmount()
})

test('/foldsmith demo shows sample data with all eight poses', async ($, on) => {
  machine(on, {})
  on('command.run', () => ({ text: '' }))
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })
  await $.command.run({ command: 'foldsmith', args: 'demo', origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 100 } })

  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /Mail \(demo\)/ })).toBeDefined()
  const header = await ui.find({ type: 'Text', text: /CLS/ })
  for (const pose of ['CLS', 'CLS↔', 'BOOK', 'LAP', 'TENT', 'FLAT', 'FLT↔', 'SPL½']) expect(header?.text).toContain(pose)
  expect(await ui.find({ type: 'Text', text: /○ Compose: no pattern yet/ })).toBeDefined()
  await ui.unmount()
})

test('a progress file from a shared repository cannot make the pane open a link or read outside the app', async ($, on) => {
  const status = JSON.stringify({
    ...JSON.parse(MIGRATED),
    driver: '/app/evil.py',
    screens: [
      { name: 'Folders', cells: { book: { state: 'verified', before: '../../etc/outside.png', after: '/Users/me/elsewhere.png' } } },
      { name: 'Note', cells: { book: { state: 'verified', before: '.duo/captures/Notes/before/linked.png' } } },
    ],
  })
  const links = { '/app/.duo/REPORT.md': '/app/notes.command', '/app/.duo/captures/Notes/before/linked.png': '/etc/outside.png' }
  const runs = machine(on, { '/app/.duo/migration.json': status, '/app/.duo/REPORT.md': '# Report' }, () => 1, links)
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  await ui.press({ key: 'report' })
  await ui.press({ key: 'captures' })
  await ui.select({ key: 'screen', value: 'Note' })
  await ui.unmount()
  const ran = runs.map(argv => argv.join(' '))
  expect(ran.filter(line => line.startsWith('/usr/bin/open'))).toEqual(['/usr/bin/open -R /app/.duo/captures'])
  expect(ran.some(line => /evil\.py|\.\.|elsewhere|outside|linked/.test(line))).toBe(false)
  expect(ran.every(line => line.startsWith('/'))).toBe(true)
})

test('a session in the home folder searches nothing and follows no app by itself', async ($, on) => {
  const runs = machine(on, { '/Users/me/apps/notes/.duo/migration.json': STATUS }, () => 1, {}, { stored: { recent: ['/Users/me/apps/notes'] } })
  on('command.run', () => ({ text: '' }))
  await $.session.start({ cwd: '/Users/me', surface: 'desktop', isInteractive: true })

  expect(runs.some(argv => argv[0] === '/usr/bin/find')).toBe(false)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: /No migration in this folder/ })).toBeDefined()
  expect(await ui.find({ key: 'follow:/Users/me/apps/notes' })).toBeDefined()
  await ui.unmount()

  const reply = await $.command.run({ command: 'foldsmith', args: 'watch ~/apps/notes', origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 100 } })
  expect(reply.text).toBe('Foldsmith pane: following apps/notes.')
  expect(runs.some(argv => argv.join(' ') === '/usr/bin/git -C /Users/me/apps/notes branch --show-current')).toBe(true)
  const followed = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await followed.find({ type: 'Text', text: /^Notes$/ })).toBeDefined()
  await followed.unmount()
})

test('a search that fails still shows the progress file in the folder', async ($, on) => {
  const runs = machine(on, { '/app/.duo/migration.json': STATUS }, () => 1, {}, { find: true })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  // Read at the start itself, before any timer runs: the failed search did not end the start.
  expect(runs.some(argv => argv[0] === '/usr/bin/find')).toBe(true)
  expect(runs.some(argv => argv.join(' ') === '/usr/bin/git -C /app branch --show-current')).toBe(true)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: /^Notes$/ })).toBeDefined()
  await ui.unmount()
})

test('when looking for progress files fails, the timers still run and /foldsmith still opens the pane', async ($, on) => {
  const timers: number[] = []
  machine(on, {}, () => 1, {}, { store: true, timers })
  on('command.run', () => ({ text: '' }))
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true }).catch(() => undefined)

  expect(timers.length).toBe(3)
  const reply = await $.command.run({ command: 'foldsmith', args: '', origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 100 } })
  expect(reply.text).toBe('Foldsmith pane opened.')
})

test('a project under the home folder is searched and followed', async ($, on) => {
  const runs = machine(on, { '/Users/me/work/a/.duo/migration.json': STATUS })
  await $.session.start({ cwd: '/Users/me/work', surface: 'desktop', isInteractive: true })

  expect(runs.some(argv => argv[0] === '/usr/bin/find' && argv[1] === '/Users/me/work')).toBe(true)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: /^Notes$/ })).toBeDefined()
  await ui.unmount()
})

for (const cwd of ['/Users/me/', '/users/ME']) {
  test(`the home folder spelled ${cwd} is still not searched`, async ($, on) => {
    const runs = machine(on, {})
    await $.session.start({ cwd, surface: 'desktop', isInteractive: true })
    expect(runs.some(argv => argv[0] === '/usr/bin/find')).toBe(false)
  })
}

test('a .duo folder that is a link is not read', async ($, on) => {
  machine(on, { '/app/.duo/migration.json': STATUS }, () => 1, { '/app/.duo': '/elsewhere/.duo' })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: /a link, not a file in the app folder/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^Notes$/ })).toBeUndefined()
  await ui.unmount()
})

test('a linked progress file is left out of what the search finds', async ($, on) => {
  const older = JSON.stringify({ ...JSON.parse(STATUS), app: 'Real' })
  const newer = JSON.stringify({ ...JSON.parse(STATUS), app: 'Linked' })
  machine(on, { '/work/a/.duo/migration.json': older, '/work/b/.duo/migration.json': newer }, path => (path.startsWith('/work/b') ? 5 : 1), {
    '/work/b/.duo/migration.json': '/elsewhere/migration.json',
  })
  await $.session.start({ cwd: '/work', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: /^Real$/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /a link/ })).toBeUndefined()
  await ui.unmount()
})

test('a progress file that is a link is not read, and its error goes with it', async ($, on) => {
  const files: Files = { '/app/.duo/migration.json': STATUS }
  machine(on, files, () => 1, { '/app/.duo/migration.json': '/elsewhere/migration.json' })
  on('command.run', () => ({ text: '' }))
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: /a link, not a file in the app folder/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^Notes$/ })).toBeUndefined()
  await ui.unmount()

  await $.command.run({ command: 'foldsmith', args: 'watch /other', origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 100 } })
  const other = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await other.find({ type: 'Text', text: /a link, not a file/ })).toBeUndefined()
  await other.unmount()
})
