import type { On } from 'claude-code'
import { expect, test } from 'claude-code/testing'

const PANE = {
  plugin: 'duo-migration',
  component: 'Pane',
  requestId: 'duo-migration',
  props: {
    title: 'Duo migration',
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

// Stands for the engine and the Mac beneath the plugin: the files, find, git, sips, the store and the clock.
function machine(on: On, files: Files, mtime: (path: string) => number = () => 1) {
  const store: { [key: string]: unknown } = {}
  on('command.register', () => ({ value: { command: 'duo' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('clock.every', () => ({ value: undefined }))
  on('ui.panes', () => ({ value: [] }))
  on('store.get', (_, e) => ({ value: store[e.key] }))
  on('store.set', (_, e) => {
    store[e.key] = e.value
    return { value: undefined }
  })
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('fs.exists', (_, e) => ({ value: e.path in files || e.path.endsWith('.png') }))
  on('fs.stat', (_, e) => ({ value: { kind: 'file', size: 10, mtimeMs: mtime(e.path), isLink: false } }))
  on('fs.read', (_, e) => ({ value: e.as === 'bytes' ? { base64: 'SlBFRw==' } : files[e.path] ?? '' }))
  on('process.run', (_, e) => {
    const [command] = e.argv
    const stdout = e.argv.includes('-g')
      ? 'x.jpg\n  pixelWidth: 720\n  pixelHeight: 506\n'
      : command === '/usr/bin/printenv'
        ? '/Users/me\n'
        : command === 'find'
          ? Object.keys(files).filter(path => path.endsWith('/.duo/migration.json')).join('\n')
          : command === 'git'
            ? 'duo-migration\n'
            : ''
    return { value: { exitCode: 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
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

test('/duo demo shows sample data with all eight poses', async ($, on) => {
  machine(on, {})
  on('command.run', () => ({ text: '' }))
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })
  await $.command.run({ command: 'duo', args: 'demo', origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 100 } })

  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /Mail \(demo\)/ })).toBeDefined()
  const header = await ui.find({ type: 'Text', text: /CLS/ })
  for (const pose of ['CLS', 'CLS↔', 'BOOK', 'LAP', 'TENT', 'FLAT', 'FLT↔', 'SPL½']) expect(header?.text).toContain(pose)
  expect(await ui.find({ type: 'Text', text: /○ Compose: no pattern yet/ })).toBeDefined()
  await ui.unmount()
})
