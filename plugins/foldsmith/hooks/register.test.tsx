import type { On } from 'claude-code'
import { expect, mock, test } from 'claude-code/testing'

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

// The longest label a button may carry: a long screen name goes in a wrapping text beside a short button.
const NAME_LABEL_MAX = 32

const at = (bodyColumns: number) => ({ ...PANE, props: { ...PANE.props, bodyColumns } })

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

// All seven poses, shots in book and laptop.
const SEVEN = JSON.stringify({
  app: 'Notes',
  phase: 'verify',
  screens: [
    {
      name: 'Folders',
      cells: {
        book: { state: 'finding', label: 'T5', before: '.duo/captures/Notes/before/folders-book-inner.png', after: '.duo/captures/Notes/after/folders-book-inner.png' },
        laptop: { state: 'verified', before: '.duo/captures/Notes/before/folders-laptop-inner.png', after: '.duo/captures/Notes/after/folders-laptop-inner.png' },
      },
    },
    { name: 'Note', cells: { book: { state: 'unchanged' } } },
  ],
})

// Paths to the files the plugin may read; a progress file is any key ending in .duo/migration.json.
type Files = { [path: string]: string }

// What sips makes of a file: its size, and the base64 length of a JPEG it writes. The default draws every picture as
// the 720 × 506 shot of a book pose, in eight characters.
type Pictures = { size?: (file: string) => [number, number]; bytes?: (out: string) => number | undefined }

// What the Mac answers besides files: `find` fails as a timed-out one does, `store` makes reading the store fail, `stored`
// fills the store first, `timers` collects each timer's interval, `clock` leaves the timers to a mock.clock, `duo` lists a
// booted iPhone Duo simulator, `shown` has the pane on screen, `fail` makes sips fail for the files it matches, and `wait`
// holds back a program until the promise it returns resolves.
type Faults = {
  find?: boolean
  store?: boolean
  stored?: { [key: string]: unknown }
  timers?: number[]
  clock?: boolean
  duo?: boolean
  shown?: boolean
  fail?: (argv: string[]) => boolean
  wait?: (argv: string[]) => Promise<void> | undefined
}

// Stands for the engine and the Mac beneath the plugin: the files, find, git, sips, the store and the clock. `links` maps
// each symbolic link to where it leads. It returns every program the plugin ran, as its argv.
function machine(
  on: On,
  files: Files,
  mtime: (path: string) => number = () => 1,
  links: { [path: string]: string } = {},
  faults: Faults = {},
  pictures: Pictures = {},
) {
  const store: { [key: string]: unknown } = { ...faults.stored }
  const runs: string[][] = []
  on('command.register', () => ({ value: { command: 'foldsmith' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.scroll', () => ({}))
  if (!faults.clock)
    on('clock.every', (_, e) => {
      faults.timers?.push(e.ms)
      return { value: undefined }
    })
  on('ui.panes', () => ({ value: faults.shown ? [{ id: 'foldsmith', title: 'Foldsmith', isShown: true, isFocused: false, isPlaced: true }] : [] }))
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
  on('fs.read', (_, e) => {
    if (e.as !== 'bytes') return { value: files[e.path] ?? '' }
    const n = pictures.bytes?.(e.path)
    return { value: { base64: n === undefined ? 'SlBFRw==' : 'A'.repeat(n) } }
  })
  on('process.run', async (_, e) => {
    const argv = [...e.argv]
    runs.push(argv)
    const command = argv[0]?.split('/').pop()
    if (command === 'find' && faults.find) return { deny: 'timed out after 8000 ms' }
    await faults.wait?.(argv)
    const file = argv[argv.length - 1] ?? ''
    const [w, tall] = pictures.size?.(file) ?? [720, 506]
    const stdout = argv.includes('-g')
      ? `${file}\n  pixelWidth: ${w}\n  pixelHeight: ${tall}\n`
      : command === 'printenv'
        ? '/Users/me\n'
        : command === 'find'
          ? Object.keys(files).filter(path => path.endsWith('/.duo/migration.json')).join('\n')
          : command === 'git'
            ? 'duo-migration\n'
            : command === 'xcrun' && argv.includes('list') && faults.duo
              ? JSON.stringify({ devices: { ios: [{ udid: 'DUO-1', name: 'iPhone Duo' }] } })
              : ''
    const exitCode = command === 'sips' && faults.fail?.(argv) ? 1 : 0
    return { value: { exitCode, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  return runs
}

type Node = { type?: string; props?: { [name: string]: unknown }; children?: unknown[] }

// Every element of a drawn tree, depth first.
function walk(node: unknown, visit: (el: Node) => void) {
  if (!node || typeof node !== 'object') return
  const el = node as Node
  visit(el)
  for (const child of el.children ?? []) walk(child, visit)
}

// The characters of text a tree draws: strings, labels, alts and options.
function drawnText(tree: unknown) {
  let n = 0
  walk(tree, el => {
    for (const child of el.children ?? []) if (typeof child === 'string') n += child.length
    for (const name of ['label', 'alt']) if (typeof el.props?.[name] === 'string') n += (el.props[name] as string).length
    if (Array.isArray(el.props?.options)) for (const o of el.props.options as { value: string; label?: string }[]) n += (o.label ?? o.value).length
  })
  return n
}

const svgs = (tree: unknown) => {
  const all: { [name: string]: unknown }[] = []
  walk(tree, el => {
    if (el.type === 'Svg' && el.props) all.push(el.props)
  })
  return all
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

test('the progress file drives the header, the figures and the matrix', async ($, on) => {
  machine(on, { '/app/.duo/migration.json': STATUS })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const desktop = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect((await desktop.find({ type: 'Text', text: /^Notes$/ }))?.text).toBe('Notes')
  expect((await desktop.find({ type: 'Text', text: /^● Audit$/ }))?.text).toBe('● Audit')
  expect((await desktop.find({ type: 'Text', text: /branch/ }))?.text).toBe('this folder · branch duo-migration')
  const screens = JSON.stringify((await desktop.find({ key: 'kpi-screens' }))?.children)
  expect(screens).toContain('0 of 1')
  expect(screens).toContain('screens finished')
  expect(JSON.stringify((await desktop.find({ key: 'kpi-defects' }))?.children)).toContain('"1"')
  const drawn = svgs(await desktop.drawn())
  const head = drawn.find(svg => String(svg.alt).includes('matrix'))
  expect(head).toBeDefined()
  expect(head?.isInteractive).toBeUndefined()
  expect(drawn.find(svg => String(svg.alt).endsWith('cells'))?.alt).toBe('Defect 1, Not captured 2, of 3 cells')
  const row = drawn.find(svg => String(svg.alt).startsWith('Folders row:'))
  expect(String(row?.alt)).toBe('Folders row: Not captured: Closed, Tent; Defect T5: Book')
  await desktop.unmount()

  const terminal = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await terminal.find({ type: 'Text', text: /screens finished/ }))?.text).toContain('0 of 1 screens finished')
  expect((await terminal.find({ type: 'Text', text: /screens finished/ }))?.text).toContain('1 with defects')
  expect((await terminal.find({ type: 'Text', text: /Folders/ }))?.text).toContain('✗')
  expect((await terminal.find({ type: 'Text', text: /TENT/ }))?.text).toContain('BOOK')
  await terminal.unmount()
})

test('done and left are read off the cells when the skill keeps no lists', async ($, on) => {
  machine(on, { '/app/.duo/migration.json': MIGRATED })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(JSON.stringify((await ui.find({ key: 'kpi-screens' }))?.children)).toContain('1 of 2')
  expect(JSON.stringify((await ui.find({ key: 'kpi-poses' }))?.children)).toContain('3 of 4')
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
  expect((await ui.find({ key: 'pose:book' }))?.props.variant).toBe('primary')
  expect(await ui.find({ type: 'Text', text: /^T14 columns-off-fold · T1 crease-straddle$/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^the pane edge sits on the fold$/ })).toBeDefined()

  await ui.press({ key: 'prev' })
  expect((await ui.find({ key: 'pose:closed' }))?.props.variant).toBe('primary')
  expect((await ui.find({ key: 'pose:book' }))?.props.variant).toBeUndefined()
  await ui.press({ key: 'next-defect' })
  expect((await ui.find({ key: 'pose:book' }))?.props.variant).toBe('primary')
  await ui.unmount()
})

test('before and after are drawn with the fold where the phone bends, and enlarge in the pane', async ($, on) => {
  machine(on, { '/app/.duo/migration.json': MIGRATED })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  await ui.select({ key: 'screen', value: 'Folders' })
  const pair = JSON.stringify((await ui.find({ key: 'pair' }))?.children)
  expect(pair).toContain('Folders in Book, before')
  expect(pair).toContain('href=\\"data:image/jpeg;base64,SlBFRw==\\"')
  expect(pair).toContain('class=\\"fold active\\"')
  expect(await ui.find({ key: 'open-after' })).toBeUndefined()

  await ui.press({ key: 'zoom-after' })
  expect(await ui.find({ key: 'open-after' })).toBeDefined()
  expect(await ui.find({ key: 'zoom-close' })).toBeDefined()
  await ui.press({ key: 'zoom-close' })

  await ui.press({ key: 'pose:closed' })
  expect(JSON.stringify((await ui.find({ key: 'pair' }))?.children)).not.toContain('class=\\"fold')
  await ui.unmount()
})

test('a wide pane puts the notes beside the matrix and the shots across it; a narrow one stacks them', async ($, on) => {
  machine(on, { '/app/.duo/migration.json': MIGRATED })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const wide = await $.ui.mount({ ...at(160), surface: 'desktop' })
  await wide.select({ key: 'screen', value: 'Folders' })
  const band = await wide.find({ key: 'band' })
  expect(band?.props.flexDirection).toBe('row')
  const [notes, navigator] = (band?.children ?? []).map(child => JSON.stringify(child))
  expect(notes).toContain('Folders · Book')
  expect(navigator).toContain('Screen by pose matrix')
  expect(JSON.stringify((await wide.find({ key: 'pair-row' }))?.children)).toContain('Folders in Book, before')
  expect(JSON.stringify((await wide.find({ key: 'lower' }))?.children)).toContain('Folders: Fold-aligned split')
  const drawn = svgs(await wide.drawn())
  for (const svg of drawn) expect(String(svg.source)).toContain(`height="${svg.height}"`)
  const head = drawn.find(svg => String(svg.alt).includes('matrix'))
  const strip = drawn.find(svg => String(svg.alt).startsWith('Folders row:'))
  expect(strip?.width).toBe(head?.width)
  await wide.unmount()

  // One column: the stage first, then the matrix with what is left and done.
  const narrow = await $.ui.mount({ ...PANE, surface: 'desktop' })
  await narrow.select({ key: 'screen', value: 'Folders' })
  const columns = await narrow.find({ key: 'columns' })
  expect(columns?.props.flexDirection).toBe('column')
  const parts = (columns?.children ?? []).map(child => JSON.stringify(child))
  const stage = parts.findIndex(part => part.includes('Folders in Book, before'))
  const nav = parts.findIndex(part => part.includes('Folders: Fold-aligned split'))
  expect(stage).toBeGreaterThan(-1)
  expect(nav).toBeGreaterThan(stage)
  expect(parts[stage]).not.toContain('Folders: Fold-aligned split')
  await narrow.unmount()
})

test('a wider pane never draws the shots smaller', async ($, on) => {
  machine(on, { '/app/.duo/migration.json': MIGRATED })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const width = async (cols: number) => {
    const ui = await $.ui.mount({ ...at(cols), surface: 'desktop' })
    await ui.select({ key: 'screen', value: 'Folders' })
    const shot = svgs(await ui.drawn()).find(svg => svg.alt === 'Folders in Book, before')
    await ui.unmount()
    return Number(shot?.width)
  }
  const base = await width(140)
  expect(base).toBeGreaterThan(400)
  expect(await width(160)).toBeGreaterThanOrEqual(base)
  expect(await width(200)).toBeGreaterThanOrEqual(base)
})

test('a press on a row, or on a screen named in what is left, picks that screen', async ($, on) => {
  const status = JSON.stringify({ ...JSON.parse(MIGRATED), todo: ['Note: the pane edge sits on the fold'] })
  machine(on, { '/app/.duo/migration.json': status })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  await ui.press({ key: 'row:Folders' })
  expect((await ui.find({ key: 'screen' }))?.props.value).toBe('Folders')
  expect((await ui.find({ key: 'pose:book' }))?.props.variant).toBe('primary')
  await ui.press({ key: 'pose:closed' })
  await ui.press({ key: 'todo:0:Note' })
  expect((await ui.find({ key: 'screen' }))?.props.value).toBe('Note')
  expect((await ui.find({ key: 'pose:book' }))?.props.variant).toBe('primary')
  await ui.unmount()
})

test('the enlarged view takes the pane, keeps its keys, and goes back to the dashboard', async ($, on) => {
  machine(on, { '/app/.duo/migration.json': SEVEN })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect((await ui.find({ key: 'pose:book' }))?.props.hotkey).toBe('3')
  await ui.press({ key: 'zoom' })
  expect(await ui.find({ key: 'zoom-view' })).toBeDefined()
  expect(await ui.find({ key: 'columns' })).toBeUndefined()
  expect((await ui.find({ key: 'zoom-close' }))?.props.hotkey).toBe('z')
  expect((await ui.find({ key: 'view-both' }))?.props.variant).toBe('primary')
  // Both drawn one above the other across the width, fit and fill are the same: no toggle.
  expect(await ui.find({ key: 'zoom-fit' })).toBeUndefined()

  await ui.press({ key: 'pose:laptop' })
  expect(await ui.find({ key: 'zoom-view' })).toBeDefined()
  expect((await ui.find({ key: 'pose:laptop' }))?.props.variant).toBe('primary')
  await ui.press({ key: 'view-after' })
  expect(await ui.find({ key: 'zoom-before' })).toBeUndefined()
  expect(await ui.find({ key: 'zoom-after' })).toBeDefined()
  expect((await ui.find({ key: 'zoom-fit' }))?.props.hotkey).toBe('f')

  // Every hotkey in a tree is its own.
  const keys: string[] = []
  walk(await ui.drawn(), el => {
    if (el.type === 'Button' && typeof el.props?.hotkey === 'string') keys.push(el.props.hotkey)
  })
  expect(new Set(keys).size).toBe(keys.length)

  await ui.press({ key: 'zoom-close' })
  expect(await ui.find({ key: 'columns' })).toBeDefined()
  expect(await ui.find({ key: 'zoom-view' })).toBeUndefined()
  await ui.unmount()
})

test('an enlarged shot is cut into strips under the cap, each one row lower in a padded copy', async ($, on) => {
  const runs = machine(on, { '/app/.duo/migration.json': SEVEN }, () => 1, {}, {}, {
    // A laptop capture 2007 × 2853; the copy made at the long side L keeps that shape.
    size: file => {
      const long = Number(/-z(\d+)/.exec(file)?.[1] ?? 0)
      const band = /-z(\d+)q\d+-(\d+)-(\d+)\.jpg$/.exec(file)
      if (band) {
        const [l, n, i] = [Number(band[1]), Number(band[2]), Number(band[3])]
        return [Math.round((l * 2007) / 2853), Math.floor(((i + 1) * l) / n) - Math.floor((i * l) / n)]
      }
      return long ? [Math.round((long * 2007) / 2853), long] : [2007, 2853]
    },
    // The whole copy encodes to 130 characters a pixel of its long side; a strip to 90000.
    bytes: out => (/-z\d+q\d+\.jpg$/.test(out) ? Number(/-z(\d+)/.exec(out)?.[1]) * 130 : /-z\d+q\d+-\d+-\d+\.jpg$/.test(out) ? 90000 : undefined),
  })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...at(120), surface: 'desktop' })
  await ui.press({ key: 'pose:laptop' })
  await ui.press({ key: 'zoom-after' })
  const tree = await ui.drawn()
  const parts = svgs(tree).filter(svg => /Folders in Laptop, after \(part \d of 4\)/.test(String(svg.alt)))
  expect(parts.length).toBe(4)
  const all = svgs(tree)
  for (const svg of all) {
    expect(String(svg.source).length).toBeLessThanOrEqual(131072)
    expect(Number(svg.width)).toBeLessThanOrEqual(4096)
    expect(Number(svg.height)).toBeLessThanOrEqual(4096)
  }
  expect(all.reduce((n, svg) => n + String(svg.source).length, 0)).toBeLessThanOrEqual(520000)
  const crops = runs.filter(argv => argv.includes('-c'))
  expect(crops.length).toBeGreaterThanOrEqual(4)
  // Every strip is cut one row lower in the padded copy, at 1 + y for the strip that starts at y of the copy's height.
  for (const argv of crops) {
    const [, l, n, i] = (/-z(\d+)q\d+-(\d+)-(\d+)\.jpg$/.exec(argv[argv.length - 1] ?? '') ?? []).map(Number)
    const y = Math.floor((i! * l!) / n!)
    expect(argv[argv.indexOf('--cropOffset') + 1]).toBe(String(1 + y))
    expect(argv[argv.indexOf('-c') + 1]).toBe(String(Math.floor(((i! + 1) * l!) / n!) - y))
  }
  expect(runs.some(argv => argv.includes('-p') && argv.includes('2402'))).toBe(true)
  await ui.unmount()
})

test('a shot too detailed for the cap says so, and is never drawn over it', async ($, on) => {
  machine(on, { '/app/.duo/migration.json': MIGRATED }, () => 1, {}, {}, { bytes: () => 130000 })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  await ui.select({ key: 'screen', value: 'Folders' })
  const pair = JSON.stringify((await ui.find({ key: 'pair' }))?.children)
  expect(pair).toContain('Too detailed to draw here')
  expect(pair).not.toContain('data:image/jpeg')
  await ui.unmount()
})

test('nothing is cut with an ellipsis, the text stays under the budget, and every activity line can be reached', async ($, on) => {
  const name = 'settings-appearance-advanced-reading-mode'
  const log = Array.from({ length: 400 }, (_, i) => `${String(10 + Math.floor(i / 60)).padStart(2, '0')}:${String(i % 60).padStart(2, '0')} line ${i} ${'the detectors ran again over every pose and '.repeat(6)}`)
  const todo = [`${name}: ${'a long reason the skill left this screen for you, with every measure it took; '.repeat(11)}`, 'Folders: verify tent']
  const status = JSON.stringify({
    ...JSON.parse(SEVEN),
    phase: 'done',
    screens: [...JSON.parse(SEVEN).screens, { name, cells: { book: { state: 'finding', label: 'T14' } } }],
    todo,
    log,
  })
  machine(on, { '/app/.duo/migration.json': status })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  for (const surface of ['desktop', 'mobile', 'terminal'] as const) {
    for (const cols of [60, 100, 160]) {
      const ui = await $.ui.mount({ ...at(cols), surface })
      const tree = await ui.drawn()
      walk(tree, el => {
        if (el.type === 'Text') expect(String(el.props?.wrap ?? 'wrap')).not.toMatch(/truncate|end|middle/)
        for (const child of el.children ?? []) if (typeof child === 'string') expect(child).not.toMatch(/\u2026|\.\.\./)
        for (const prop of ['label', 'alt', 'source']) if (typeof el.props?.[prop] === 'string') expect(el.props[prop] as string).not.toMatch(/\u2026|\.\.\./)
        if (el.type === 'Button') expect(String(el.props?.label).length).toBeLessThanOrEqual(NAME_LABEL_MAX)
      })
      expect(drawnText(tree)).toBeLessThan(95000)
      await ui.unmount()
    }
  }

  // The long name wraps beside a short button.
  const ui = await $.ui.mount({ ...at(100), surface: 'desktop' })
  expect((await ui.find({ key: `row:${name}` }))?.props.label).toBe('View')
  const seen = new Set<number>()
  const collect = async () => {
    for (const text of await ui.findAll({ type: 'Text', text: /^line \d+ / })) seen.add(Number(/^line (\d+)/.exec(text.text)?.[1]))
  }
  await collect()
  for (let i = 0; i < 20 && (await ui.find({ key: 'log' })); i++) {
    await ui.press({ key: 'log' })
    await collect()
    expect(drawnText(await ui.drawn())).toBeLessThan(95000)
  }
  expect(await ui.find({ key: 'log-older' })).toBeDefined()
  for (let i = 0; i < 20 && (await ui.find({ key: 'log-older' })); i++) {
    await ui.press({ key: 'log-older' })
    await collect()
    expect(drawnText(await ui.drawn())).toBeLessThan(95000)
  }
  expect(seen.size).toBe(400)
  expect((await ui.find({ type: 'Text', text: /^Entries \d+ to 400 of 400, newest first$/ }))?.text).toBeDefined()
  await ui.unmount()
})


test('sixty screens draw; past sixty-four the screen picker becomes buttons', async ($, on) => {
  const many = (n: number) =>
    JSON.stringify({
      app: 'Big',
      phase: 'audit',
      poses: ['closed', 'book', 'tent'],
      screens: Array.from({ length: n }, (_, i) => ({ name: `screen-${i}`, cells: { book: { state: i % 7 ? 'unchanged' : 'finding', label: 'T5' } } })),
    })
  machine(on, { '/sixty/.duo/migration.json': many(60), '/seventy/.duo/migration.json': many(70) })
  on('command.run', () => ({ text: '' }))
  await $.session.start({ cwd: '/sixty', surface: 'desktop', isInteractive: true })

  const sixty = await $.ui.mount({ ...at(100), surface: 'desktop' })
  expect((await sixty.find({ key: 'screen' }))?.type).toBe('Select')
  expect(await sixty.find({ key: 'row:screen-59' })).toBeDefined()
  await sixty.unmount()

  await $.command.run({ command: 'foldsmith', args: 'watch /seventy', origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 100 } })
  const seventy = await $.ui.mount({ ...at(100), surface: 'desktop' })
  expect(await seventy.find({ key: 'screen' })).toBeUndefined()
  expect(await seventy.find({ key: 'screen-next' })).toBeDefined()
  await seventy.press({ key: 'screen-next' })
  // The picked row's name is in the accent colour, as its cell is.
  expect(JSON.stringify((await seventy.find({ key: 'row:screen-1' }))?.children)).toContain('"color":"suggestion"')
  expect(JSON.stringify((await seventy.find({ key: 'row:screen-2' }))?.children ?? [])).not.toContain('suggestion')
  await seventy.unmount()
})

test('the phone draws no picker and nothing that opens on the Mac', async ($, on) => {
  const status = JSON.stringify({ ...JSON.parse(MIGRATED), phase: 'done', todo: ['Note: three levels'] })
  machine(on, { '/app/.duo/migration.json': status, '/app/.duo/REPORT.md': '# Report', '/other/.duo/migration.json': STATUS })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...at(50), surface: 'mobile' })
  expect(await ui.find({ key: 'resume' })).toBeDefined()
  for (const key of ['screen', 'app', 'report', 'captures', 'zoom', 'view-both']) expect(await ui.find({ key })).toBeUndefined()
  expect(await ui.find({ key: 'screen-next' })).toBeDefined()
  // A landscape pair stacks on a phone, each shot the pane's width: enlarging it would draw nothing larger.
  await ui.press({ key: 'row:Folders' })
  expect((await ui.find({ key: 'pair' }))?.props.flexDirection).toBe('column')
  for (const key of ['zoom', 'zoom-before', 'zoom-after']) expect(await ui.find({ key })).toBeUndefined()
  await ui.unmount()

  // Not even on a wide phone does the matrix move beside the stage.
  const wide = await $.ui.mount({ ...at(160), surface: 'mobile' })
  expect(await wide.find({ key: 'band' })).toBeUndefined()
  await wide.unmount()
})

test('the pane follows the newest progress file under the folder, and switches on a pick', async ($, on) => {
  const older = JSON.stringify({ ...JSON.parse(STATUS), app: 'Old' })
  const newer = JSON.stringify({ ...JSON.parse(MIGRATED), app: 'New' })
  machine(on, { '/work/a/.duo/migration.json': older, '/work/b/.duo/migration.json': newer }, path => (path.startsWith('/work/b') ? 5 : 1))
  await $.session.start({ cwd: '/work', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: /^New$/ })).toBeDefined()
  expect((await ui.find({ type: 'Text', text: /branch/ }))?.text).toBe('b · branch duo-migration')
  const app = await ui.find({ key: 'app' })
  expect(app?.props.value).toBe('/work/b')
  expect((app?.props.options as { label: string }[]).map(o => o.label)).toEqual(['New', 'Old'])

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
  expect(JSON.stringify((await ui.find({ key: 'kpi-left' }))?.children)).toContain('left for you')
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

  const desktop = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const strips = svgs(await desktop.drawn()).filter(svg => String(svg.alt).includes(' row: '))
  expect(strips.some(svg => String(svg.source).includes('◐'))).toBe(true)
  await desktop.unmount()
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

// --- the redesign's own rules

// The real captures' shapes: laptop portrait 2007 × 2853, the rest landscape 2853 × 2007. A copy made at a long side L
// (named in its file) keeps that shape, a padded one has two more rows, and a strip is its share of the copy's height.
function shaped(file: string): [number, number] {
  const [w, h] = /laptop/.test(file) ? [2007, 2853] : [2853, 2007]
  const long = Number(/-z(\d+)/.exec(file)?.[1] ?? /-(\d+)q\d+\.jpg$/.exec(file)?.[1] ?? 0)
  const scale = long ? long / Math.max(w, h) : 1
  const [sw, sh] = [Math.round(w * scale), Math.round(h * scale)]
  const band = /-z\d+q\d+-(\d+)-(\d+)\.jpg$/.exec(file)
  if (band) {
    const [n, i] = [Number(band[1]), Number(band[2])]
    return [sw, Math.floor(((i + 1) * sh) / n) - Math.floor((i * sh) / n)]
  }
  return /-pad\.png$/.test(file) ? [sw, sh + 2] : [sw, sh]
}

// Every pose the skill captures, in its order.
const ALL = ['closed', 'closed-sideways', 'book', 'laptop', 'tent', 'flat-sideways', 'flat-upright', 'split-half']

const tall = (bodyColumns: number, bodyRows: number) => ({ ...PANE, props: { ...PANE.props, bodyColumns, scroll: { offset: 0, bodyRows } } })

const widthOf = (tree: unknown, alt: RegExp) => Math.max(0, ...svgs(tree).filter(svg => alt.test(String(svg.alt))).map(svg => Number(svg.width)))

test('an enlarged shot is never drawn smaller than on the dashboard, and Compare shows only where it draws larger', async ($, on) => {
  machine(on, { '/app/.duo/migration.json': SEVEN }, () => 1, {}, {}, { size: shaped })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  for (const cols of [60, 100, 131, 160]) {
    for (const pose of ['book', 'laptop']) {
      const label = new RegExp(`^Folders in ${pose === 'book' ? 'Book' : 'Laptop'}, after`)
      const ui = await $.ui.mount({ ...tall(cols, 52), surface: 'desktop' })
      await ui.press({ key: `pose:${pose}` })
      const dash = widthOf(await ui.drawn(), label)
      expect(dash).toBeGreaterThan(150)
      const compare = Boolean(await ui.find({ key: 'zoom' }))
      await ui.press({ key: 'zoom-after' })
      const single = widthOf(await ui.drawn(), label)
      expect(single).toBeGreaterThanOrEqual(dash)
      await ui.press({ key: 'view-both' })
      const both = widthOf(await ui.drawn(), label)
      expect(both).toBeGreaterThanOrEqual(dash)
      // Compare is offered exactly where both draw larger than on the dashboard.
      expect(compare).toBe(both > dash * 1.1)
      await ui.press({ key: 'zoom-close' })
      await ui.unmount()
    }
  }
  // A pane only 20 rows high fits a shot smaller than the dashboard's cap: the enlarged one is still no smaller.
  for (const pose of ['book', 'laptop']) {
    const label = new RegExp(`^Folders in ${pose === 'book' ? 'Book' : 'Laptop'}, after`)
    const low = await $.ui.mount({ ...tall(131, 20), surface: 'desktop' })
    await low.press({ key: `pose:${pose}` })
    const dash = widthOf(await low.drawn(), label)
    await low.press({ key: 'zoom-after' })
    expect(widthOf(await low.drawn(), label)).toBeGreaterThanOrEqual(dash)
    await low.press({ key: 'zoom-close' })
    await low.unmount()
  }
  // At 60 columns a landscape pair already spans the pane: nothing larger fits.
  const narrow = await $.ui.mount({ ...tall(60, 52), surface: 'desktop' })
  await narrow.press({ key: 'pose:book' })
  expect(await narrow.find({ key: 'zoom' })).toBeUndefined()
  expect(await narrow.find({ key: 'zoom-after' })).toBeDefined()
  await narrow.unmount()
  const wide = await $.ui.mount({ ...tall(131, 52), surface: 'desktop' })
  await wide.press({ key: 'pose:book' })
  expect((await wide.find({ key: 'zoom' }))?.props.label).toBe('Compare full size')
  await wide.press({ key: 'zoom' })
  expect((await wide.find({ key: 'view-both' }))?.props.label).toBe('Both')
  await wide.unmount()
})

test('a single enlarged shot fits the pane until f fills its width', async ($, on) => {
  machine(on, { '/app/.duo/migration.json': SEVEN }, () => 1, {}, {}, { size: shaped })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...tall(100, 40), surface: 'desktop' })
  await ui.press({ key: 'pose:laptop' })
  const dash = widthOf(await ui.drawn(), /^Folders in Laptop, after/)
  await ui.press({ key: 'zoom-after' })
  // The pane shows 40 rows of 17 px, less 200 px of controls; a portrait shot 2007 × 2853 fits that height.
  const fitted = widthOf(await ui.drawn(), /^Folders in Laptop, after/)
  expect(fitted).toBeLessThanOrEqual(Math.max(dash, Math.floor((40 * 17 - 200) * (2007 / 2853))) + 1)
  expect((await ui.find({ key: 'zoom-fit' }))?.props.label).toBe('Fill width')
  await ui.press({ key: 'zoom-fit' })
  expect(widthOf(await ui.drawn(), /^Folders in Laptop, after/)).toBe(Math.floor(99 * 8.2))
  expect((await ui.find({ key: 'zoom-fit' }))?.props.label).toBe('Fit to pane')
  await ui.unmount()
})

test('a very wide pane never draws a picture taller than a drawing may be', async ($, on) => {
  machine(on, { '/app/.duo/migration.json': SEVEN }, () => 1, {}, {}, { size: shaped })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  for (const cols of [300, 360, 480]) {
    const ui = await $.ui.mount({ ...tall(cols, 52), surface: 'desktop' })
    await ui.press({ key: 'pose:laptop' })
    await ui.press({ key: 'zoom-after' })
    if ((await ui.find({ key: 'zoom-fit' }))?.props.label === 'Fill width') await ui.press({ key: 'zoom-fit' })
    for (const view of ['view-after', 'view-both']) {
      await ui.press({ key: view })
      for (const svg of svgs(await ui.drawn())) {
        expect(Number(svg.width)).toBeLessThanOrEqual(4096)
        expect(Number(svg.height)).toBeLessThanOrEqual(4096)
      }
    }
    await ui.press({ key: 'zoom-close' })
    await ui.unmount()
  }
})

test('the phone enlarges only what it draws larger, and never offers what opens on the Mac', async ($, on) => {
  machine(on, { '/app/.duo/migration.json': SEVEN }, () => 1, {}, {}, { size: shaped })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  // A portrait pair sits side by side on a 52-column phone: enlarged, a shot takes the whole width.
  const phone = await $.ui.mount({ ...at(52), surface: 'mobile' })
  await phone.press({ key: 'pose:laptop' })
  const dash = widthOf(await phone.drawn(), /^Folders in Laptop, after/)
  expect(await phone.find({ key: 'zoom' })).toBeUndefined()
  await phone.press({ key: 'zoom-after' })
  expect(widthOf(await phone.drawn(), /^Folders in Laptop, after/)).toBeGreaterThan(dash * 1.5)
  for (const key of ['view-both', 'zoom-fit', 'open-after', 'open-before']) expect(await phone.find({ key })).toBeUndefined()
  await phone.press({ key: 'zoom-close' })
  await phone.unmount()

  // Both, opened on the Mac, shows one shot on the phone, with nothing that opens on the Mac.
  const desktop = await $.ui.mount({ ...at(131), surface: 'desktop' })
  await desktop.press({ key: 'zoom' })
  await desktop.unmount()
  const later = await $.ui.mount({ ...at(52), surface: 'mobile' })
  expect(await later.find({ key: 'zoom-view' })).toBeDefined()
  for (const key of ['view-both', 'zoom-fit', 'open-after', 'open-before', 'zoom-before']) expect(await later.find({ key })).toBeUndefined()
  expect(await later.find({ key: 'zoom-after' })).toBeDefined()
  await later.unmount()
})

test('a long screen name is never a picker option or a button label, and keeps to its own row', async ($, on) => {
  const name = 'settings-appearance-theme-picker-x'
  const status = JSON.stringify({ ...JSON.parse(MIGRATED), screens: [...JSON.parse(MIGRATED).screens, { name, cells: { book: { state: 'finding', label: 'T5' } } }] })
  const longApp = JSON.stringify({ ...JSON.parse(STATUS), app: 'Wikipedia for iPhone Duo, the second run' })
  machine(on, { '/work/a/.duo/migration.json': status, '/work/b/.duo/migration.json': longApp }, path => (path.startsWith('/work/a') ? 5 : 1))
  await $.session.start({ cwd: '/work', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...at(60), surface: 'desktop' })
  expect(name.length).toBe(34)
  expect(await ui.find({ key: 'screen' })).toBeUndefined()
  expect((await ui.find({ key: 'screen-next' }))?.props.plain).toBe(true)
  expect(await ui.find({ type: 'Text', text: /j\/k screen/ })).toBeDefined()
  // The App picker falls back to buttons, each app's name beside its folder.
  expect(await ui.find({ key: 'app' })).toBeUndefined()
  expect(await ui.find({ key: 'app:/work/b' })).toBeDefined()
  // The name wraps beside its View button in the name column, which is sized by the short names: rows stay rows.
  expect((await ui.find({ key: `row:${name}` }))?.props.label).toBe('View')
  const rows: Node[] = []
  walk(await ui.drawn(), el => {
    if (el.type === 'Box' && (el.children ?? []).some(child => (child as Node).type === 'Svg' && String((child as Node).props?.alt).includes(' row: '))) rows.push(el)
  })
  expect(rows.length).toBe(3)
  for (const row of rows) {
    expect(row.props?.flexDirection).toBe('row')
    expect((row.children?.[row.children.length - 1] as Node).type).toBe('Svg')
    // 'Folders', the longest name a button carries, and a button's padding; never less than 16 beside a long name.
    expect(Number((row.children?.[0] as Node).props?.width)).toBe(16)
  }
  expect(JSON.stringify(rows[2]?.children?.[0])).toContain('"label":"View"')
  await ui.unmount()
})

test('on a terminal the shots keep their shape, and the enlarged view is the capture itself', async ($, on) => {
  const runs = machine(on, { '/app/.duo/migration.json': SEVEN }, () => 7, {}, {}, { size: shaped })
  await $.session.start({ cwd: '/app', surface: 'terminal', isInteractive: true })

  for (const cols of [100, 200, 300]) {
    const ui = await $.ui.mount({ ...at(cols), surface: 'terminal' })
    await ui.press({ key: 'pose:laptop' })
    const images: Node[] = []
    walk(await ui.drawn(), el => {
      if (el.type === 'Image') images.push(el)
    })
    expect(images.length).toBe(2)
    for (const image of images) {
      const shape = Number(image.props?.columns) / (2 * Number(image.props?.rows))
      expect(Math.abs(shape / (2007 / 2853) - 1)).toBeLessThan(0.1)
      // As large as half the pane allows, up to 60 rows.
      expect(Number(image.props?.columns)).toBeGreaterThanOrEqual(Math.min(Math.floor((cols - 4) / 2) - 1, Math.round(60 * 2 * (2007 / 2853)) - 1))
      // Keyed by the capture's mtime, so a shot captured again is drawn again.
      expect((image.props?.source as { generation?: number }).generation).toBe(7)
    }
    await ui.unmount()
  }

  const ui = await $.ui.mount({ ...at(100), surface: 'terminal' })
  await ui.press({ key: 'pose:laptop' })
  const before = runs.length
  await ui.press({ key: 'zoom-after' })
  const tree = await ui.drawn()
  const images: Node[] = []
  walk(tree, el => {
    if (el.type === 'Image') images.push(el)
  })
  expect(images.length).toBe(1)
  expect((images[0]?.props?.source as { file?: string }).file).toBe('/app/.duo/captures/Notes/after/folders-laptop-inner.png')
  expect(svgs(tree).length).toBe(0)
  // No strips are cut for a terminal, which draws the capture itself.
  expect(runs.slice(before).some(argv => argv.some(arg => /-z\d+/.test(arg)))).toBe(false)
  await ui.unmount()
})

test("the terminal's matrix fits a narrow pane, its picked cell in balanced brackets", async ($, on) => {
  const name = 'settings-appearance-theme'
  const status = JSON.stringify({ ...JSON.parse(SEVEN), poses: ALL, screens: [...JSON.parse(SEVEN).screens, { name, cells: { book: { state: 'finding', label: 'T5' } } }] })
  machine(on, { '/app/.duo/migration.json': status })
  await $.session.start({ cwd: '/app', surface: 'terminal', isInteractive: true })

  for (const cols of [52, 60, 80]) {
    const ui = await $.ui.mount({ ...at(cols), surface: 'terminal' })
    const matrix = await ui.find({ key: 'matrix' })
    const texts: string[] = []
    walk(matrix, el => {
      if (el.type === 'Text') texts.push((el.children ?? []).filter(child => typeof child === 'string').join(''))
    })
    expect(texts.length).toBeGreaterThan(3)
    for (const text of texts) expect(text.length).toBeLessThanOrEqual(cols - 1)
    expect(texts.some(text => text.includes('[✗]'))).toBe(true)
    expect(texts.some(text => /\[[^\]]*$/.test(text))).toBe(false)
    await ui.unmount()
  }
})

test('every hotkey and every key in a tree is its own, on every surface', async ($, on) => {
  const many = JSON.stringify({ ...JSON.parse(SEVEN), screens: [...JSON.parse(SEVEN).screens, ...Array.from({ length: 70 }, (_, i) => ({ name: `s${i}`, cells: {} }))] })
  machine(on, { '/app/.duo/migration.json': SEVEN, '/big/.duo/migration.json': many })
  on('command.run', () => ({ text: '' }))
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const check = (tree: unknown) => {
    const hotkeys: string[] = []
    const keys: string[] = []
    walk(tree, el => {
      if (el.type === 'Button' && typeof el.props?.hotkey === 'string') hotkeys.push(el.props.hotkey)
      if ((el.type === 'Button' || el.type === 'Select') && typeof el.props?.key === 'string') keys.push(el.props.key)
    })
    expect(hotkeys.length).toBeGreaterThan(5)
    expect(new Set(hotkeys).size).toBe(hotkeys.length)
    expect(new Set(keys).size).toBe(keys.length)
  }
  for (const folder of ['/app', '/big']) {
    await $.command.run({ command: 'foldsmith', args: `watch ${folder}`, origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 100 } })
    for (const [surface, cols] of [['desktop', 100], ['desktop', 160], ['mobile', 52], ['terminal', 100]] as const) {
      const ui = await $.ui.mount({ ...at(cols), surface })
      check(await ui.drawn())
      if (await ui.find({ key: 'zoom-after' })) {
        await ui.press({ key: 'zoom-after' })
        check(await ui.drawn())
        await ui.press({ key: 'zoom-close' })
      }
      await ui.unmount()
    }
  }
})

test('Inspect next goes to the next defect, not the next cell', async ($, on) => {
  const status = JSON.stringify({
    app: 'Notes',
    phase: 'verify',
    poses: ['closed', 'book', 'tent'],
    screens: [
      { name: 'A', cells: { closed: { state: 'unchanged' }, book: { state: 'unchanged' }, tent: { state: 'unchanged' } } },
      { name: 'B', cells: { closed: { state: 'unchanged' }, book: { state: 'finding', label: 'T5' }, tent: { state: 'unchanged' } } },
    ],
  })
  machine(on, { '/app/.duo/migration.json': status })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  await ui.select({ key: 'screen', value: 'A' })
  await ui.press({ key: 'pose:closed' })
  const inspect = await ui.find({ key: 'inspect' })
  expect(inspect?.props.plain).toBe(true)
  await ui.press({ key: 'inspect' })
  expect((await ui.find({ key: 'screen' }))?.props.value).toBe('B')
  expect((await ui.find({ key: 'pose:book' }))?.props.variant).toBe('primary')
  await ui.unmount()
})

test("the activity starts with five lines, and the cell's classes, waived and found, are named", async ($, on) => {
  const status = JSON.stringify({
    app: 'Notes',
    phase: 'verify',
    poses: ['closed', 'book', 'tent'],
    screens: [
      { name: 'A', cells: { book: { state: 'verified', finding: 'T5', waived: { T5: 'the column is a list, read across' } }, tent: { state: 'finding', label: 'T14' } } },
      { name: 'B', cells: { book: { state: 'finding', label: 'T14', finding: 'T14 T1' } } },
    ],
    log: Array.from({ length: 6 }, (_, i) => `10:0${i} entry ${i}`),
  })
  machine(on, { '/app/.duo/migration.json': status })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect((await ui.findAll({ type: 'Text', text: /^entry \d$/ })).length).toBe(5)
  expect(await ui.find({ type: 'Text', text: /^entry 0$/ })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /^5 of 6, newest first$/ })).toBeDefined()
  expect(await ui.find({ key: 'log' })).toBeDefined()
  expect(JSON.stringify((await ui.find({ key: 'kpi-defects' }))?.children)).toContain('T14 ×2 · T1')
  await ui.select({ key: 'screen', value: 'A' })
  await ui.press({ key: 'pose:book' })
  expect(await ui.find({ type: 'Text', text: /^Found in the audit: T5 stretched-single-column$/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^Waived T5 stretched-single-column: the column is a list, read across$/ })).toBeDefined()
  await ui.unmount()
})

test('the fold is drawn in the accent blue: a band with edges while bent, dashed while flat', async ($, on) => {
  const status = JSON.stringify({
    ...JSON.parse(SEVEN),
    screens: [
      { name: 'Folders', cells: { ...JSON.parse(SEVEN).screens[0].cells, 'flat-sideways': { state: 'verified', before: '.duo/captures/Notes/before/folders-flat-sideways-inner.png' } } },
    ],
  })
  machine(on, { '/app/.duo/migration.json': status })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const pair = JSON.stringify((await ui.find({ key: 'pair' }))?.children)
  expect(pair).toContain('class=\\"fold active\\"')
  expect(pair).toContain('class=\\"fold edge\\"')
  expect(pair).toContain('.fold.active{fill:#2f6fde;fill-opacity:.12}')
  expect(await ui.find({ type: 'Text', text: /^Blue band: the fold/ })).toBeDefined()
  await ui.press({ key: 'pose:flat-sideways' })
  expect(JSON.stringify((await ui.find({ key: 'pair' }))?.children)).toContain('class=\\"fold inactive\\"')
  // A pose with no shots says so once, without empty boxes.
  await ui.press({ key: 'pose:tent' })
  expect(await ui.find({ key: 'pair' })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /^No shots yet for this pose$/ })).toBeDefined()
  await ui.unmount()
})

test('Open in Preview is offered only for a capture in the app folder; a missing one says so', async ($, on) => {
  const status = JSON.stringify({
    ...JSON.parse(SEVEN),
    screens: [{ name: 'Folders', cells: { book: { state: 'verified', before: '../outside/before.png', after: '.duo/captures/Notes/after/folders-book-inner.png' } } }],
  })
  machine(on, { '/app/.duo/migration.json': status })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...at(131), surface: 'desktop' })
  await ui.press({ key: 'zoom-after' })
  await ui.press({ key: 'view-both' })
  expect(await ui.find({ key: 'open-after' })).toBeDefined()
  expect(await ui.find({ key: 'open-before' })).toBeUndefined()
  expect(JSON.stringify(svgs(await ui.drawn()).map(svg => svg.source))).toContain('Not found in the app folder')
  await ui.unmount()

  const terminal = await $.ui.mount({ ...at(100), surface: 'terminal' })
  expect(await terminal.find({ type: 'Text', text: /Not found in the app folder/ })).toBeDefined()
  await terminal.unmount()
})

test('nothing drawn while pictures and strips are still being made carries an ellipsis', async ($, on) => {
  const clock = mock.clock(on)
  let slow = false
  machine(on, { '/app/.duo/migration.json': SEVEN }, () => 1, {}, { clock: true, wait: argv => (slow && argv[0] === '/usr/bin/sips' ? clock.sleep(5000) : undefined) }, { size: shaped })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const clean = (tree: unknown) =>
    walk(tree, el => {
      for (const child of el.children ?? []) if (typeof child === 'string') expect(child).not.toMatch(/…|\.\.\./)
      for (const prop of ['label', 'alt', 'source']) if (typeof el.props?.[prop] === 'string') expect(el.props[prop] as string).not.toMatch(/…|\.\.\./)
    })
  const ui = await $.ui.mount({ ...at(100), surface: 'desktop' })
  slow = true
  await ui.press({ key: 'pose:laptop' })
  expect(JSON.stringify(svgs(await ui.drawn()).map(svg => svg.source))).toContain('Loading')
  clean(await ui.drawn())
  await ui.press({ key: 'zoom-after' })
  expect(await ui.find({ type: 'Text', text: /^· Sharpening$/ })).toBeDefined()
  clean(await ui.drawn())
  await clock.advance(60000)
  expect(await ui.find({ type: 'Text', text: /^· 2007 × 2853 capture$/ })).toBeDefined()
  clean(await ui.drawn())
  await ui.unmount()
})

test('a detailed shot is made smaller until its strips fit; a cut that fails is not run again', async ($, on) => {
  const clock = mock.clock(on)
  // The whole copy at long side L encodes to 480000 × √(L / 2400) characters: far slower than its area falls.
  const runs = machine(on, { '/app/.duo/migration.json': SEVEN }, () => 1, {}, { clock: true }, {
    size: shaped,
    bytes: out => (/-z\d+q\d+\.jpg$/.test(out) ? Math.round(480000 * Math.sqrt(Number(/-z(\d+)/.exec(out)?.[1]) / 2400)) : /-z\d+q\d+-\d+-\d+\.jpg$/.test(out) ? 95000 : undefined),
  })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...at(100), surface: 'desktop' })
  await ui.press({ key: 'pose:laptop' })
  await ui.press({ key: 'zoom-after' })
  expect(svgs(await ui.drawn()).filter(svg => /^Folders in Laptop, after \(part \d of 4\)$/.test(String(svg.alt))).length).toBe(4)
  const sips = () => runs.filter(argv => argv[0] === '/usr/bin/sips').length
  const settled = sips()
  await clock.advance(1500 * 4)
  expect(sips()).toBe(settled)
  await ui.unmount()
})

test('a shot still too detailed at the smallest copy is sharpened at a lower JPEG quality', async ($, on) => {
  const runs = machine(on, { '/app/.duo/migration.json': SEVEN }, () => 1, {}, {}, {
    size: shaped,
    // Whatever its size, a whole copy fits two strips only at quality 45.
    bytes: out => (/-z\d+q55\.jpg$/.test(out) ? 260000 : /-z\d+q\d+\.jpg$/.test(out) ? 190000 : /-z\d+q\d+-\d+-\d+\.jpg$/.test(out) ? 95000 : undefined),
  })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...at(100), surface: 'desktop' })
  await ui.press({ key: 'pose:laptop' })
  await ui.press({ key: 'zoom' })
  expect(svgs(await ui.drawn()).filter(svg => /^Folders in Laptop, (before|after) \(part \d of 2\)$/.test(String(svg.alt))).length).toBe(4)
  const crops = runs.filter(argv => argv.includes('-c'))
  expect(crops.every(argv => argv[argv.indexOf('formatOptions') + 1] === '45' && argv.some(arg => /-z1280q45-/.test(arg)))).toBe(true)
  await ui.unmount()
})

test('a cut that cannot fit, or whose strips come back wrong, says so and is not run again at each check', async ($, on) => {
  const clock = mock.clock(on)
  const runs = machine(on, { '/app/.duo/migration.json': SEVEN }, () => 1, {}, { clock: true }, {
    // The before shot never fits; the after shot's strips come back a row short.
    size: file => (/after/.test(file) && /-z\d+q\d+-\d+-\d+\.jpg$/.test(file) ? [shaped(file)[0], shaped(file)[1] - 1] : shaped(file)),
    bytes: out => (/-z\d+q\d+\.jpg$/.test(out) ? (/before/.test(out) ? 999999 : 150000) : /-z\d+q\d+-\d+-\d+\.jpg$/.test(out) ? 90000 : undefined),
  })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...at(100), surface: 'desktop' })
  await ui.press({ key: 'pose:laptop' })
  await ui.press({ key: 'zoom' })
  expect(await ui.find({ type: 'Text', text: /^· too detailed to sharpen$/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^· drawn from the dashboard copy$/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /Sharpening/ })).toBeUndefined()
  const sips = () => runs.filter(argv => argv[0] === '/usr/bin/sips').length
  const settled = sips()
  await clock.advance(1500 * 4)
  expect(sips()).toBe(settled)
  await ui.unmount()
})

test('a write to the progress file keeps the strips; a shot captured again is cut again', async ($, on) => {
  const clock = mock.clock(on)
  let written = 1
  let captured = 1
  const runs = machine(on, { '/app/.duo/migration.json': SEVEN }, path => (path.endsWith('migration.json') ? written : path.endsWith('.png') ? captured : 1), {}, { clock: true }, { size: shaped })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...at(100), surface: 'desktop' })
  await ui.press({ key: 'zoom-after' })
  expect(await ui.find({ type: 'Text', text: /capture$/ })).toBeDefined()
  const cuts = () => runs.filter(argv => argv[0] === '/usr/bin/sips' && argv.includes('-Z') && argv.some(arg => /-z\d+\.png$/.test(arg))).length
  const first = cuts()
  expect(first).toBeGreaterThan(0)
  written = 2
  await clock.advance(1500)
  expect(cuts()).toBe(first)
  expect(await ui.find({ type: 'Text', text: /capture$/ })).toBeDefined()
  captured = 2
  await ui.unmount()
  // Drawn before the new strips are cut, the old ones are not passed off as the new capture.
  const again = await $.ui.mount({ ...at(100), surface: 'desktop' })
  expect(await again.find({ type: 'Text', text: /^· Sharpening$/ })).toBeDefined()
  expect(await again.find({ type: 'Text', text: /capture$/ })).toBeUndefined()
  await clock.advance(1500)
  expect(cuts()).toBeGreaterThan(first)
  expect(await again.find({ type: 'Text', text: /capture$/ })).toBeDefined()
  await again.unmount()
})

test('the live view runs only for a migration of up to 40 screens, and never while a shot is enlarged', async ($, on) => {
  const clock = mock.clock(on)
  const screens = (n: number) => JSON.stringify({ ...JSON.parse(SEVEN), screens: [...JSON.parse(SEVEN).screens, ...Array.from({ length: n - 2 }, (_, i) => ({ name: `s${i}`, cells: {} }))] })
  const runs = machine(on, { '/forty/.duo/migration.json': screens(40), '/more/.duo/migration.json': screens(41) }, () => 1, {}, { clock: true, duo: true, shown: true })
  on('command.run', () => ({ text: '' }))
  await $.session.start({ cwd: '/forty', surface: 'desktop', isInteractive: true })
  const shots = () => runs.filter(argv => argv.includes('screenshot')).length

  const ui = await $.ui.mount({ ...at(100), surface: 'desktop' })
  await clock.advance(4000)
  expect(shots()).toBe(1)
  await ui.press({ key: 'zoom-after' })
  await clock.advance(8000)
  expect(shots()).toBe(1)
  await ui.press({ key: 'zoom-close' })
  await ui.unmount()

  await $.command.run({ command: 'foldsmith', args: 'watch /more', origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 100 } })
  const more = await $.ui.mount({ ...at(100), surface: 'desktop' })
  await clock.advance(8000)
  expect(shots()).toBe(1)
  expect(await more.find({ type: 'Text', text: /^Live view off for migrations of more than 40 screens$/ })).toBeDefined()
  expect(await more.find({ key: 'live' })).toBeUndefined()
  await more.unmount()
})

test('sixty-four screens of defects in every pose, with long notes, stay inside the text budget', async ($, on) => {
  const reason = 'the search field in the list pane stops short of its margin, and every measure the skill took left it there; '.repeat(6)
  const big = (todos: number) =>
    JSON.stringify({
      app: 'Big',
      phase: 'done',
      poses: ALL,
      screens: Array.from({ length: 64 }, (_, i) => ({
        name: `screen-number-${i}`,
        cells: Object.fromEntries(ALL.map(pose => [pose, { state: 'finding', label: 'T14', finding: 'T14 T5 T1 T4' }])),
      })),
      todo: Array.from({ length: todos }, (_, i) => `screen-number-${i % 64}: item ${i} ${reason}`),
    })
  machine(on, { '/app/.duo/migration.json': big(64), '/huge/.duo/migration.json': big(200) })
  on('command.run', () => ({ text: '' }))
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  for (const folder of ['/app', '/huge']) {
    await $.command.run({ command: 'foldsmith', args: `watch ${folder}`, origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 100 } })
    for (const [surface, cols] of [['desktop', 100], ['desktop', 160], ['mobile', 60], ['terminal', 100]] as const) {
      const ui = await $.ui.mount({ ...at(cols), surface })
      const tree = await ui.drawn()
      expect(drawnText(tree)).toBeLessThan(95000)
      expect(JSON.stringify(tree)).not.toContain('not drawn')
      await ui.unmount()
    }
  }

  // What is left is drawn a page at a time, and every item can be reached.
  const ui = await $.ui.mount({ ...at(100), surface: 'desktop' })
  const seen = new Set<number>()
  const collect = async () => {
    for (const text of await ui.findAll({ type: 'Text', text: /^○ screen-number-\d+: item \d+ / })) seen.add(Number(/item (\d+)/.exec(text.text)?.[1]))
  }
  await collect()
  expect(seen.size).toBeLessThan(200)
  for (let i = 0; i < 20 && (await ui.find({ key: 'left-more' })); i++) {
    await ui.press({ key: 'left-more' })
    await collect()
    const tree = await ui.drawn()
    expect(drawnText(tree)).toBeLessThan(95000)
  }
  expect(seen.size).toBe(200)
  expect(await ui.find({ key: 'left-back' })).toBeDefined()
  await ui.unmount()
})

test('what is done, once shown, stays inside the text budget and leaves the activity its buttons', async ($, on) => {
  const done = Array.from({ length: 240 }, (_, i) => `Folders: done item ${i} ${'verified in every pose with the fold-aligned split and no regressions; '.repeat(5)}`)
  const log = Array.from({ length: 50 }, (_, i) => `10:${String(i).padStart(2, '0')} line ${i}`)
  machine(on, { '/app/.duo/migration.json': JSON.stringify({ ...JSON.parse(SEVEN), done, log }) })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const ui = await $.ui.mount({ ...at(100), surface: 'desktop' })
  expect((await ui.find({ key: 'done-toggle' }))?.props.label).toBe('Show done (240)')
  await ui.press({ key: 'done-toggle' })
  const tree = await ui.drawn()
  expect(drawnText(tree)).toBeLessThan(95000)
  expect(JSON.stringify(tree)).not.toContain('not drawn')
  expect(await ui.find({ key: 'log' })).toBeDefined()
  expect(await ui.find({ key: 'done-more' })).toBeDefined()
  const seen = new Set<number>()
  for (let i = 0; i < 20; i++) {
    for (const text of await ui.findAll({ type: 'Text', text: /^✓ Folders: done item \d+ / })) seen.add(Number(/item (\d+)/.exec(text.text)?.[1]))
    if (!(await ui.find({ key: 'done-more' }))) break
    await ui.press({ key: 'done-more' })
    expect(drawnText(await ui.drawn())).toBeLessThan(95000)
  }
  expect(seen.size).toBe(240)
  expect((await ui.find({ key: 'done-toggle' }))?.props.label).toBe('Hide done')
  await ui.press({ key: 'done-toggle' })
  expect((await ui.find({ key: 'done-toggle' }))?.props.label).toBe('Show done (240)')
  await ui.unmount()
})

test('a portrait pair on a wide pane keeps its size, the matrix and the notes beside it', async ($, on) => {
  const status = JSON.stringify({ ...JSON.parse(SEVEN), todo: ['Folders: the list pane stops short of the fold'] })
  machine(on, { '/app/.duo/migration.json': status }, () => 1, {}, {}, { size: shaped })
  await $.session.start({ cwd: '/app', surface: 'desktop', isInteractive: true })

  const width = async (cols: number) => {
    const ui = await $.ui.mount({ ...tall(cols, 52), surface: 'desktop' })
    await ui.press({ key: 'pose:laptop' })
    const tree = await ui.drawn()
    const band = await ui.find({ key: 'band' })
    await ui.unmount()
    return { w: widthOf(tree, /^Folders in Laptop, before$/), band }
  }
  const base = await width(140)
  expect(base.w).toBeGreaterThan(300)
  for (const cols of [150, 160, 200]) {
    const { w, band } = await width(cols)
    expect(w).toBeGreaterThanOrEqual(base.w)
    // At 150 columns eight poses leave the matrix too little room beside the pair: it stays in the band above.
    if (cols === 150) continue
    const [stage, navigator] = (band?.children ?? []).map(child => JSON.stringify(child))
    expect(stage).toContain('Folders in Laptop, before')
    expect(navigator).toContain('Screen by pose matrix')
    expect(navigator).toContain('the list pane stops short of the fold')
  }
})
