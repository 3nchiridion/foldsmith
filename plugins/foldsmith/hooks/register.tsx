import { atom, read, update } from 'claude-code'
import type {
  BoxProps,
  ButtonProps,
  Color,
  ElementConstructor,
  EngineInterface,
  ImageProps,
  Register,
  RenderElement,
  SelectProps,
  SvgProps,
  TextProps,
} from 'claude-code'

import type { Cell, CellState, Folder, Known, LogView, Migration, Phase, Pick, Picture, PoseId, Screen, Source, Zoom, ZoomSide } from '../types'

// The skill writes this file at every step; the pane only reads it.
const STATUS_FILE = '.duo/migration.json'
const PANE = 'foldsmith'
const TITLE = 'Foldsmith'
// The SVG namespace, the only URL in this file: a name, not an address the pane contacts.
const SVG_NS = 'http://www.w3.org/2000/svg'
const LIVE_EVERY_MS = 4000
const LOOK_EVERY_MS = 60000

// --- the width model
// CSS pixels per body cell. The desktop was measured at about 8.5 (a 902 px drawing filled 131 cells less two); 8.2
// leaves a little margin so nothing sized from `bodyColumns` overflows. VS Code and the phone are not measured.
const PX_PER_CELL: { [surface: string]: number } = { desktop: 8.2, vscode: 7, mobile: 7 }
// A footnote line on the desktop, in CSS pixels (measured), for the height the pane shows at once.
const PX_PER_ROW = 17
// From this many cells the pane draws the picked cell's notes beside the matrix, and the shots across the whole width.
const WIDE_COLS = 150
// Pixels between two shots side by side, and the matrix's column widths and row height.
const GAP_PX = 16
const ROW_PX = 30
const COL_PX_WIDE = 56
const COL_MIN = 36
const COL_MAX = 96
// A screen name longer than this is drawn as wrapping text beside a short button, never as a button's label; a Select
// is drawn only for at most SELECT_MAX options of at most SELECT_LABEL characters, so nothing is cut.
const NAME_BUTTON_MAX = 20
const SELECT_MAX = 64
const SELECT_LABEL = 32

// --- pictures
// An Svg's markup is capped at 131072 characters: a picture's JPEG stays under TILE_MAX. A shot on the dashboard is
// the first rung of the ladder that fits (measured: a text-heavy article fits at 820 px, a map at 1024, settings at 1280).
const TILE_MAX = 120000
const TILE_TARGET = 100000
const STAGE_LADDER: [number, number][] = [
  [1280, 55],
  [1280, 45],
  [1024, 45],
  [820, 45],
  [640, 40],
  [480, 35],
]
const LIVE_LADDER: [number, number][] = [
  [720, 55],
  [720, 45],
  [560, 40],
  [480, 35],
]
// The enlarged view cuts a shot into horizontal strips, each its own Svg under the cap: the long side in pixels and
// the most strips, for one shot and for each of two side by side. A detailed shot is made smaller, down to
// ZOOM_LONG_MIN, then at a lower JPEG quality (measured on the Wikipedia run: a map in book fits 4 strips at 1968 px).
const ZOOM_LONG_SINGLE = 2400
const ZOOM_LONG_BOTH = 1800
const ZOOM_LONG_MIN = 1280
const ZOOM_TILES_SINGLE = 4
const ZOOM_TILES_BOTH = 2
const TILES_KEPT = 12
// Dashboard shots kept in memory, the last used first out.
const SHRUNK_KEPT = 24
// The tallest a drawing may be, in CSS pixels.
const SVG_MAX = 4096
// The live frame is drawn only for a migration of at most this many screens, so a large tree stays light.
const LIVE_MAX_SCREENS = 40

// --- drawn text
// The engine draws at most 100000 characters of text in one tree and cuts the rest; the pane spends at most this many,
// whole lines only, and offers the rest behind buttons.
const TEXT_BUDGET = 90000
const LOG_DEFAULT = 5
const LOG_PAGE = 50
// The most text the picked screen's notes take on the stage; the rest are in the lists below.
const WHY_BUDGET = 12000

const migration = atom({ plugin: 'foldsmith', key: 'migration' } as const, null as Migration | null)
const source = atom({ plugin: 'foldsmith', key: 'source' } as const, 'none' as Source)
const error = atom({ plugin: 'foldsmith', key: 'error' } as const, null as string | null)
// The app folder the pane follows; null is the session's own folder.
const root = atom({ plugin: 'foldsmith', key: 'root' } as const, null as string | null)
const live = atom({ plugin: 'foldsmith', key: 'live' } as const, null as Picture | null)
const liveNote = atom({ plugin: 'foldsmith', key: 'liveNote' } as const, null as string | null)
const paused = atom({ plugin: 'foldsmith', key: 'paused' } as const, false)
const pick = atom({ plugin: 'foldsmith', key: 'pick' } as const, null as Pick | null)
const pictures = atom({ plugin: 'foldsmith', key: 'pictures' } as const, {} as { [file: string]: Picture | null })
const known = atom({ plugin: 'foldsmith', key: 'known' } as const, [] as Known[])
const folderInfo = atom({ plugin: 'foldsmith', key: 'folderInfo' } as const, { branch: null, report: false } as Folder)
const logView = atom({ plugin: 'foldsmith', key: 'logView' } as const, { start: 0, count: LOG_DEFAULT } as LogView)
const doneShown = atom({ plugin: 'foldsmith', key: 'doneShown' } as const, false)
// The first item drawn of what is done and of what is left, when they are drawn a page at a time.
const doneStart = atom({ plugin: 'foldsmith', key: 'doneStart' } as const, 0)
const leftStart = atom({ plugin: 'foldsmith', key: 'leftStart' } as const, 0)
const zoom = atom({ plugin: 'foldsmith', key: 'zoom' } as const, null as Zoom | null)
const zoomFit = atom({ plugin: 'foldsmith', key: 'zoomFit' } as const, true)
// Bumped when enlarged strips land, so the pane draws them.
const zoomRev = atom({ plugin: 'foldsmith', key: 'zoomRev' } as const, 0)

// Apple's six poses from the HIG, plus closed-sideways and the Split View half window, in the skill's order.
const ALL_POSES: PoseId[] = [
  'closed',
  'closed-sideways',
  'book',
  'laptop',
  'tent',
  'flat-sideways',
  'flat-upright',
  'split-half',
]

const POSE_LABEL: Record<PoseId, string> = {
  closed: 'Closed',
  'closed-sideways': 'Closed sideways',
  book: 'Book',
  laptop: 'Laptop',
  tent: 'Tent',
  'flat-sideways': 'Flat sideways',
  'flat-upright': 'Flat upright',
  'split-half': 'Split View',
}

// The matrix header's names for columns too narrow for the full ones.
const HEAD_SHORT: Record<PoseId, string> = {
  closed: 'Closed',
  'closed-sideways': 'Closed↔',
  book: 'Book',
  laptop: 'Laptop',
  tent: 'Tent',
  'flat-sideways': 'Flat↔',
  'flat-upright': 'Flat',
  'split-half': 'Split½',
}

// The terminal matrix's six-character columns.
const POSE_SHORT: Record<PoseId, string> = {
  closed: 'CLS',
  'closed-sideways': 'CLS↔',
  book: 'BOOK',
  laptop: 'LAP',
  tent: 'TENT',
  'flat-sideways': 'FLT↔',
  'flat-upright': 'FLAT',
  'split-half': 'SPL½',
}

const poseLabel = (pose: string) => POSE_LABEL[pose as PoseId] ?? pose

// Each icon is drawn in a 36 × 36 box, in the style of Apple's pose illustrations.
const POSE_ICON: Record<PoseId, string> = {
  closed: '<rect x="11" y="3" width="14" height="30" rx="3"/><circle class="dot" cx="21" cy="7.5" r="1.4"/>',
  'closed-sideways': '<rect x="3" y="11" width="30" height="14" rx="3"/><circle class="dot" cx="28.5" cy="15" r="1.4"/>',
  book: '<path d="M4 7 L18 10 L32 7 L32 29 L18 32 L4 29 Z"/><path class="crease" d="M18 10 L18 32"/>',
  laptop: '<rect x="8" y="3" width="20" height="16" rx="2.5"/><path d="M8 19 L28 19 L32 32 L4 32 Z"/>',
  tent: '<path d="M25 7 L31 30 L24 30 Z"/><path d="M10 7 L25 7 L21 31 L5 31 Z"/>',
  'flat-sideways': '<rect x="2" y="7" width="32" height="22" rx="3"/>',
  'flat-upright': '<rect x="7" y="3" width="22" height="30" rx="3"/>',
  'split-half': '<rect x="2" y="7" width="32" height="22" rx="3"/><rect class="half" x="4.5" y="9.5" width="12" height="17" rx="1.5"/>',
}

// The inner display's fold in each pose: the division is active while the phone is bent, inactive when it lies flat.
const FOLD: Partial<Record<PoseId, 'active' | 'inactive'>> = {
  book: 'active',
  laptop: 'active',
  tent: 'active',
  'flat-sideways': 'inactive',
  'flat-upright': 'inactive',
}
// The division is 40 pt of the inner display's 951 pt long side, centred (the captures' window, at 3× pixels).
const FOLD_SHARE = 40 / 951

// Width over height of a shot in each pose, for the space a shot not drawn yet will need.
const ASPECT: Record<PoseId, number> = {
  closed: 1398 / 2034,
  'closed-sideways': 2034 / 1398,
  book: 2853 / 2007,
  laptop: 2007 / 2853,
  tent: 2007 / 2853,
  'flat-sideways': 2853 / 2007,
  'flat-upright': 2007 / 2853,
  'split-half': 475 / 669,
}

// The defect classes (skills/foldsmith-duo/references/taxonomy.md).
const CLASS_NAME: Record<string, string> = {
  T1: 'crease-straddle',
  T2: 'content-under-occlusion',
  T3: 'custom-bar-not-vertical',
  T4: 'under-system-bar',
  T5: 'stretched-single-column',
  T6: 'fixed-size-hero',
  T7: 'state-loss-on-fold',
  T8: 'relayout-not-animated',
  T9: 'inactive-division-ignored',
  T10: 'stranded-horizontal-item',
  T11: 'split-view-squeeze',
  T12: 'letterbox-compat',
  T13: 'no-scene-lifecycle',
  T14: 'columns-off-fold',
  T15: 'sheet-in-book',
}

const PHASES: { id: Phase; label: string }[] = [
  { id: 'screens', label: 'Screens' },
  { id: 'audit', label: 'Audit' },
  { id: 'classify', label: 'Classify' },
  { id: 'migrate', label: 'Migrate' },
  { id: 'verify', label: 'Verify' },
]

// What a matrix cell shows besides a defect's classes: one glyph each, never cut.
const MARK: Record<CellState, string> = {
  pending: '',
  unchanged: '—',
  finding: '✗',
  proposed: '◆',
  migrated: '◐',
  verified: '✓',
}

// The terminal's matrix: one glyph per cell.
const GLYPH: Record<CellState, string> = {
  pending: '·',
  unchanged: '─',
  finding: '✗',
  proposed: '◆',
  migrated: '◐',
  verified: '✓',
}

const STATE_WORD: Record<CellState, string> = {
  pending: 'Not captured',
  unchanged: 'Fine as is',
  finding: 'Defect',
  proposed: 'Pattern proposed',
  migrated: 'Migrated, not verified yet',
  verified: 'Verified',
}

// The text colour of a state's mark, and the fill of its chip (drawn in the inverse text colour).
const STATE_COLOR: Record<CellState, Color> = {
  pending: 'inactive',
  unchanged: 'subtle',
  finding: 'error',
  proposed: 'suggestion',
  migrated: 'warning',
  verified: 'success',
}
const CHIP_COLOR: Record<CellState, Color> = { ...STATE_COLOR, unchanged: 'inactive' }

// The order of the progress bar and its legend.
const LEGEND: { state: CellState; label: string }[] = [
  { state: 'verified', label: 'Verified' },
  { state: 'unchanged', label: 'Fine as is' },
  { state: 'migrated', label: 'Migrated' },
  { state: 'proposed', label: 'Proposed' },
  { state: 'finding', label: 'Defect' },
  { state: 'pending', label: 'Not captured' },
]

const DEMO: Migration = {
  app: 'Mail (demo)',
  phase: 'migrate',
  poses: ALL_POSES,
  screens: [
    {
      name: 'Inbox',
      pattern: 'Fold-aligned split',
      cells: {
        closed: { state: 'unchanged' },
        'closed-sideways': { state: 'unchanged' },
        book: { state: 'verified', label: 'split' },
        laptop: { state: 'verified', label: 'split' },
        tent: { state: 'migrated' },
        'flat-sideways': { state: 'verified', label: 'split' },
        'flat-upright': { state: 'verified', label: 'split' },
        'split-half': { state: 'unchanged' },
      },
    },
    {
      name: 'Message',
      pattern: 'Reader',
      cells: {
        closed: { state: 'unchanged' },
        'closed-sideways': { state: 'finding', label: 'T4', finding: 'T4' },
        book: { state: 'migrated', label: 'reader' },
        laptop: { state: 'proposed', label: 'stacked' },
        tent: { state: 'proposed', label: 'viewer' },
        'flat-sideways': { state: 'proposed', label: 'reader' },
        'flat-upright': { state: 'migrated', label: 'reader' },
        'split-half': { state: 'unchanged' },
      },
    },
    {
      name: 'Compose',
      cells: {
        closed: { state: 'unchanged' },
        'closed-sideways': { state: 'unchanged' },
        book: { state: 'proposed', label: 'sheet→' },
        laptop: { state: 'finding', label: 'T1', finding: 'T1' },
        tent: { state: 'pending' },
        'flat-sideways': { state: 'unchanged' },
        'flat-upright': { state: 'unchanged' },
        'split-half': { state: 'finding', label: 'T11', finding: 'T11' },
      },
    },
    {
      name: 'Settings',
      cells: Object.fromEntries(ALL_POSES.map(pose => [pose, { state: 'unchanged' } as Cell])),
    },
  ],
  log: [
    '10:02 Captured 8 poses × 4 screens on iPhone Duo (iOS 27.1)',
    '10:09 Classified 4 screens; patterns from the decision table',
    '10:31 Inbox: NavigationSplitView in book, laptop, flat — 0 findings',
    '10:40 Message: migrating to the reader pattern',
  ],
  done: ['Inbox: Fold-aligned split, verified in book, laptop and flat', 'Settings: fine as is in every pose'],
  todo: ['Message: migrate to the reader pattern, then verify', 'Compose: no pattern yet (continuous / editing, UNJUSTIFIED in tent); T1 in laptop', 'Inbox: verify tent'],
}

const escapeXml = (text: string) =>
  text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

const clamp = (n: number, low: number, high: number) => Math.max(low, Math.min(high, n))

const round1 = (n: number) => Math.round(n * 10) / 10

// A long name may wrap after - _ / and . (a zero-width space after each); text otherwise wraps only at spaces.
const breakable = (text: string) => text.replace(/([-_/.])/g, '$1​')

// A folder's path may wrap after each slash.
const slashes = (path: string) => path.replace(/\//g, '/\u200B')

// The same, only inside words long enough to overflow a narrow column.
const soft = (text: string) => text.replace(/\S{24,}/g, word => breakable(word))

const posesOf = (m: Migration) => (m.poses && m.poses.length > 0 ? m.poses : ALL_POSES)

const cellOf = (cells: { [pose: string]: Cell }, pose: string): Cell => cells[pose] ?? { state: 'pending' }

const screenOf = (m: Migration, name: string | undefined) => m.screens.find(s => s.name === name)

// Every class seen in a cell: the audit's list when it kept one, else the matrix label of a defect.
const codesOf = (cell: Cell) =>
  (cell.finding ?? (cell.state === 'finding' ? cell.label ?? '' : '')).split(/\s+/).filter(code => /^T\d+$/.test(code))

const describe = (code: string) => (CLASS_NAME[code] ? `${code} ${CLASS_NAME[code]}` : code)

// A cell's text in a matrix column `colPx` wide: all of a defect's classes when they fit (6.6 px a character at 11 px),
// else the first and how many more; any other state's glyph.
function cellText(cell: Cell, colPx: number) {
  if (cell.state !== 'finding') return MARK[cell.state]
  const codes = codesOf(cell)
  if (codes.length === 0) return MARK.finding
  const room = colPx - 10
  const all = codes.join('·')
  if (all.length * 6.6 <= room) return all
  const more = `${codes[0]} +${codes.length - 1}`
  return codes.length > 1 && more.length * 6.6 <= room ? more : codes[0]!
}

// The mark beside a pose's name on the pose strip: its first class, or its glyph; none for a pose fine as is.
function poseMark(cell: Cell) {
  if (cell.state === 'unchanged') return ''
  if (cell.state === 'finding') return codesOf(cell)[0] ?? MARK.finding
  return cell.state === 'pending' ? '·' : MARK[cell.state]
}

function counts(m: Migration) {
  const tally: Record<CellState, number> = { pending: 0, unchanged: 0, finding: 0, proposed: 0, migrated: 0, verified: 0 }
  for (const screen of m.screens) for (const pose of posesOf(m)) tally[cellOf(screen.cells, pose).state] += 1
  return tally
}

// How many defect cells carry each class, most first: 'T14 ×10 · T5 ×5 · T1 · T4'.
function classLine(m: Migration) {
  const seen = new Map<string, number>()
  for (const screen of m.screens)
    for (const pose of posesOf(m)) {
      const cell = cellOf(screen.cells, pose)
      if (cell.state === 'finding') for (const code of codesOf(cell)) seen.set(code, (seen.get(code) ?? 0) + 1)
    }
  return [...seen.entries()]
    .sort((a, b) => b[1] - a[1] || Number(a[0].slice(1)) - Number(b[0].slice(1)))
    .map(([code, n]) => (n > 1 ? `${code} ×${n}` : code))
    .join(' · ')
}

// --- the drawings
// One style for every drawing, so a surface that lays several Svgs into one page (the phone's web view) styles each
// class the same way wherever it comes from. Dark mode follows the system through the media query.
const STYLE = `text{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text",system-ui,sans-serif}
.track{fill:#f1efe8}.seg.verified,.sw.verified{fill:#639922}.seg.unchanged,.sw.unchanged{fill:#b4b2a9}
.seg.migrated,.sw.migrated{fill:#ef9f27}.seg.proposed,.sw.proposed{fill:#378add}.seg.finding,.sw.finding{fill:#e24b4a}
.sw.pending{fill:none;stroke:#b4b2a9;stroke-dasharray:2 2}
.lab{font-size:11px;fill:#5f5e5a}.cnt{font-weight:600;fill:#1f1e1d}
.icon *{fill:#dde7fb;stroke:#151a2d;stroke-width:2.2;stroke-linejoin:round;stroke-linecap:round}
.icon .dot{fill:#151a2d;stroke:none}.icon .crease{fill:none}.icon .half{fill:#9fbaf0;stroke:none}
.icon.sel *{fill:#cfe0ff;stroke:#2f6fde}.icon.sel .dot{fill:#2f6fde}.icon.sel .crease{fill:none}
.pose{font-size:10px;fill:#5f5e5a}.pose.tight{font-size:9px}.pose.sel{fill:#2f6fde;font-weight:600}.uline{fill:#2f6fde}
.cell.pending{fill:none;stroke:#c9c7bd;stroke-dasharray:3 3}
.cell.unchanged{fill:#f1efe8}.label.unchanged{fill:#888780}
.cell.finding{fill:#fcebeb}.label.finding{fill:#a32d2d}
.cell.proposed{fill:#e6f1fb}.label.proposed{fill:#0c447c}
.cell.migrated{fill:#faeeda}.label.migrated{fill:#854f0b}
.cell.verified{fill:#eaf3de}.label.verified{fill:#27500a}
.label{font-size:11px;font-weight:600}.glyph{font-size:12px;font-weight:500}
.pick{fill:none;stroke:#2f6fde;stroke-width:2}
.frame{fill:none;stroke:#d3d1c7}.empty{fill:none;stroke:#c9c7bd;stroke-dasharray:4 4}.note{font-size:12px;fill:#888780}
.fold.active{fill:#2f6fde;fill-opacity:.12}.fold.edge{fill:#2f6fde;fill-opacity:.7}
.fold.inactive{fill:none;stroke:#2f6fde;stroke-opacity:.7;stroke-dasharray:4 3}
@media (prefers-color-scheme:dark){
.track{fill:#2c2c2a}.seg.verified,.sw.verified{fill:#97c459}.seg.unchanged,.sw.unchanged{fill:#5f5e5a}
.seg.migrated,.sw.migrated{fill:#fac775}.seg.proposed,.sw.proposed{fill:#85b7eb}.seg.finding,.sw.finding{fill:#f09595}
.sw.pending{stroke:#5f5e5a}.lab{fill:#b4b2a9}.cnt{fill:#f1efe8}
.icon *{fill:#22304a;stroke:#d6e0f5}.icon .dot{fill:#d6e0f5}.icon .crease{fill:none}.icon .half{fill:#3d5b94}
.icon.sel *{fill:#2b4a80;stroke:#9cc0ff}.icon.sel .dot{fill:#9cc0ff}.icon.sel .crease{fill:none}
.pose{fill:#b4b2a9}.pose.sel{fill:#7aa7ff}.uline{fill:#7aa7ff}
.cell.pending{stroke:#5f5e5a}.cell.unchanged{fill:#2c2c2a}.label.unchanged{fill:#b4b2a9}
.cell.finding{fill:#501313}.label.finding{fill:#f7c1c1}
.cell.proposed{fill:#042c53}.label.proposed{fill:#b5d4f4}
.cell.migrated{fill:#412402}.label.migrated{fill:#fac775}
.cell.verified{fill:#173404}.label.verified{fill:#c0dd97}
.pick{stroke:#7aa7ff}.frame{stroke:#444441}.empty{stroke:#5f5e5a}
.fold.active,.fold.edge{fill:#7aa7ff}.fold.inactive{stroke:#7aa7ff}
}`

type Drawing = { source: string; width: number; height: number }

function svg(width: number, height: number, body: string): Drawing {
  return {
    width,
    height,
    source:
      `<svg xmlns="${SVG_NS}" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}">` +
      `<style>${STYLE}</style>${body}</svg>`,
  }
}

// The progress bar: one segment per state, in the legend's order, over a track that stands for what is not captured;
// the legend under it names the states the migration holds, with their counts, wrapped to the width.
function barSvg(tally: Record<CellState, number>, total: number, width: number): Drawing {
  const w = Math.max(160, Math.round(width))
  let cum = 0
  const segments = LEGEND.filter(item => item.state !== 'pending' && tally[item.state] > 0)
    .map(item => {
      const x0 = Math.round((w * cum) / Math.max(1, total))
      cum += tally[item.state]
      const x1 = Math.round((w * cum) / Math.max(1, total))
      return `<rect class="seg ${item.state}" x="${x0}" y="0" width="${x1 - x0}" height="10"/>`
    })
    .join('')
  let lx = 0
  let row = 0
  const legend = LEGEND.filter(item => tally[item.state] > 0)
    .map(item => {
      const count = String(tally[item.state])
      const span = 15 + item.label.length * 6.2 + 4 + count.length * 7
      if (lx > 0 && lx + span > w) {
        lx = 0
        row += 1
      }
      const y = 27 + row * 18
      const part =
        `<rect class="sw ${item.state}" x="${round1(lx + 0.5)}" y="${y - 9.5}" width="10" height="10" rx="3"/>` +
        `<text class="lab" x="${round1(lx + 15)}" y="${y}">${escapeXml(item.label)} <tspan class="cnt">${count}</tspan></text>`
      lx += span + 16
      return part
    })
    .join('')
  const height = 27 + 18 * row + 6
  return svg(
    w,
    height,
    `<defs><clipPath id="bar-clip"><rect width="${w}" height="10" rx="5"/></clipPath></defs>` +
      `<rect class="track" width="${w}" height="10" rx="5"/><g clip-path="url(#bar-clip)">${segments}</g>${legend}`,
  )
}

// The matrix's header: each pose's icon and name over its column, the picked pose's in the accent colour.
function headSvg(poses: PoseId[], colPx: number, picked: string | undefined, full: boolean): Drawing {
  const s = Math.min(0.8, (colPx - 12) / 36)
  // Below 44 px a short name of more than six characters ('Closed↔') puts its arrow on a second line.
  const tight = !full && colPx < 44 ? ' tight' : ''
  const shortOf = (pose: PoseId) => {
    const name = HEAD_SHORT[pose] ?? pose
    return tight && name.length > 6 ? [name.slice(0, -1), name.slice(-1)] : [name]
  }
  const labels = poses.map(pose => {
    const words = poseLabel(pose).split(' ')
    return full ? (words.length > 2 ? [words[0]!, words.slice(1).join(' ')] : words) : shortOf(pose)
  })
  const lines = Math.max(...labels.map(label => label.length))
  const labelY = 4 + 36 * s + 14
  const height = Math.ceil(labelY + (lines - 1) * 12 + 10)
  const body = poses
    .map((pose, i) => {
      const x = i * colPx
      const sel = pose === picked ? ' sel' : ''
      const label = labels[i]!
      return (
        `<g class="icon${sel}" transform="translate(${round1(x + colPx / 2 - 18 * s)} 4) scale(${round1(s * 100) / 100})">${POSE_ICON[pose] ?? ''}</g>` +
        label
          .map(
            (line, l) =>
              `<text class="pose${tight}${sel}" x="${x + colPx / 2}" y="${round1(labelY + l * 12)}" text-anchor="middle">${escapeXml(line)}</text>`,
          )
          .join('') +
        (sel ? `<rect class="uline" x="${x + 8}" y="${height - 3}" width="${colPx - 16}" height="2" rx="1"/>` : '')
      )
    })
    .join('')
  return svg(poses.length * colPx, height, body)
}

// One screen's row of cells, the picked cell outlined. The row's name is drawn beside it as a button, not in here.
function stripSvg(m: Migration, screen: Screen, colPx: number, picked: string | undefined): Drawing {
  const body = posesOf(m)
    .map((pose, i) => {
      const cell = cellOf(screen.cells, pose)
      const x = i * colPx
      const text = cellText(cell, colPx)
      const glyph = cell.state !== 'finding' ? ' glyph' : ''
      return (
        `<rect class="cell ${cell.state}" x="${x + 3}" y="3" width="${colPx - 6}" height="24" rx="5"/>` +
        (text ? `<text class="label ${cell.state}${glyph}" x="${x + colPx / 2}" y="19.5" text-anchor="middle">${escapeXml(text)}</text>` : '') +
        (pose === picked ? `<rect class="pick" x="${x + 1}" y="1" width="${colPx - 2}" height="28" rx="7"/>` : '')
      )
    })
    .join('')
  return svg(posesOf(m).length * colPx, ROW_PX, body)
}

// The fold where the inner display bends: a light band with crisp edges while the division is active, a dashed outline
// while the phone lies flat, in the accent blue (red means a defect). A landscape shot's fold runs down its middle; a
// portrait shot's across it, at `y` from this drawing's top.
function foldRect(fold: 'active' | 'inactive' | undefined, landscape: boolean, w: number, tall: number, y = 0, total = tall) {
  if (!fold) return ''
  if (landscape) {
    const band = w * FOLD_SHARE
    const x = (w - band) / 2
    const [top, high] = [y === 0 ? 0 : -4, tall + 8]
    const edges =
      fold === 'active'
        ? `<rect class="fold edge" x="${round1(x)}" y="${top}" width="1" height="${high}"/><rect class="fold edge" x="${round1(x + band - 1)}" y="${top}" width="1" height="${high}"/>`
        : ''
    return `<rect class="fold ${fold}" x="${round1(x)}" y="${top}" width="${round1(band)}" height="${high}"/>${edges}`
  }
  const band = total * FOLD_SHARE
  const top = (total - band) / 2 - y
  if (top > tall || top + band < 0) return ''
  const edges =
    fold === 'active'
      ? `<rect class="fold edge" x="0" y="${round1(top)}" width="${w}" height="1"/><rect class="fold edge" x="0" y="${round1(top + band - 1)}" width="${w}" height="1"/>`
      : ''
  return `<rect class="fold ${fold}" x="0" y="${round1(top)}" width="${w}" height="${round1(band)}"/>${edges}`
}

// A shot at w × tall, clipped to its rounded frame, the fold drawn over it.
function shotSvg(pic: Picture, w: number, tall: number, fold: 'active' | 'inactive' | undefined, id: string): Drawing {
  return svg(
    w,
    tall,
    `<defs><clipPath id="${id}"><rect width="${w}" height="${tall}" rx="8"/></clipPath></defs><g clip-path="url(#${id})">` +
      `<image width="${w}" height="${tall}" preserveAspectRatio="xMidYMid meet" href="data:image/jpeg;base64,${pic.jpeg}"/>` +
      `${foldRect(fold, pic.width >= pic.height, w, tall)}</g>` +
      `<rect class="frame" x="0.5" y="0.5" width="${w - 1}" height="${tall - 1}" rx="8"/>`,
  )
}

// The box that stands for a shot not drawn: dashed, saying why.
function emptySvg(w: number, tall: number, note: string): Drawing {
  return svg(
    w,
    tall,
    `<rect class="empty" x="1" y="1" width="${w - 2}" height="${tall - 2}" rx="8"/>` +
      `<text class="note" x="${w / 2}" y="${Math.round(tall / 2 + 4)}" text-anchor="middle">${escapeXml(note)}</text>`,
  )
}

// One strip of an enlarged shot, drawn `tall` high at `y` in a shot `total` high; only the first strip's top corners
// and the last's bottom ones are round, so the strips stacked with no gap read as one picture.
function tileSvg(jpeg: string, w: number, tall: number, y: number, total: number, i: number, n: number, fold: 'active' | 'inactive' | undefined, landscape: boolean, id: string): Drawing {
  const first = i === 0
  const last = i === n - 1
  const top = first ? 0 : -20
  const span = tall - top + (last ? 0 : 20)
  return svg(
    w,
    tall,
    `<defs><clipPath id="${id}"><rect y="${top}" width="${w}" height="${span}" rx="10"/></clipPath></defs><g clip-path="url(#${id})">` +
      `<image width="${w}" height="${tall}" preserveAspectRatio="none" href="data:image/jpeg;base64,${jpeg}"/>` +
      `${foldRect(fold, landscape, w, tall, y, total)}</g>` +
      `<rect class="frame" x="0.5" y="${first ? 0.5 : top}" width="${w - 1}" height="${span - (first ? 1 : 0) - (last ? 0.5 : 0)}" rx="10"/>`,
  )
}

function phaseIndex(phase: Phase) {
  if (phase === 'done') return PHASES.length
  return PHASES.findIndex(p => p.id === (phase === 'approve' ? 'classify' : phase))
}

const FINAL: CellState[] = ['verified', 'unchanged']

const isFinished = (m: Migration, screen: Screen) => posesOf(m).every(p => FINAL.includes(cellOf(screen.cells, p).state))

// What is done and what is left: the skill's own lists when it keeps them, else read off the cells.
function progress(m: Migration): { done: string[]; left: string[] } {
  const done =
    m.done ?? m.screens.filter(s => isFinished(m, s)).map(s => (s.pattern ? `${s.name}: ${s.pattern}` : s.name))
  const left =
    m.todo ??
    m.screens
      .filter(s => !isFinished(m, s))
      .map(s => {
        const open = posesOf(m).filter(p => !FINAL.includes(cellOf(s.cells, p).state))
        return `${s.name}: ${open.map(p => `${poseLabel(p)} ${cellOf(s.cells, p).label ?? cellOf(s.cells, p).state}`).join(', ')}`
      })
  return { done, left }
}

// The screens a note names: its words before the first ': ', split at commas and 'and', each matched to a screen by
// its whole name or its first words, without regard to case ('article and contents from Home: ' names both).
function namedScreens(m: Migration, line: string): string[] {
  const colon = line.indexOf(': ')
  if (colon < 0) return []
  const names: string[] = []
  for (const part of line.slice(0, colon).split(/,\s*|\s+and\s+/)) {
    const words = part.trim().toLowerCase()
    const screen =
      m.screens.find(s => s.name.toLowerCase() === words) ?? m.screens.find(s => words.startsWith(`${s.name.toLowerCase()} `))
    if (screen && !names.includes(screen.name)) names.push(screen.name)
  }
  return names
}

// The status beside the app's name.
function statusOf(m: Migration, from: Source, left: number): { text: string; color: Color } {
  if (from === 'demo') return { text: 'Sample data', color: 'subtle' }
  if (m.phase === 'done') {
    return left > 0 ? { text: `Finished · ${left} left for you`, color: 'warning' } : { text: '✓ Finished', color: 'success' }
  }
  return { text: `● ${PHASES[phaseIndex(m.phase)]?.label ?? m.phase}`, color: 'claude' }
}

// Every cell, screen by screen; stepping through them wraps around.
function step(m: Migration, from: Pick | null, delta: number, defectsOnly = false): Pick | null {
  const all = m.screens.flatMap(s => posesOf(m).map(pose => ({ screen: s.name, pose: pose as string })))
  if (all.length === 0) return null
  const at = all.findIndex(p => p.screen === from?.screen && p.pose === from?.pose)
  for (let i = 1; i <= all.length; i++) {
    const next = all[(((at + delta * i) % all.length) + all.length) % all.length]
    if (!next) continue
    if (!defectsOnly || cellOf(screenOf(m, next.screen)?.cells ?? {}, next.pose).state === 'finding') return next
  }
  return null
}

// The next or previous screen in the same pose, wrapping around.
function stepScreen(m: Migration, from: Pick | null, delta: number): Pick | null {
  const n = m.screens.length
  if (n === 0) return null
  const at = m.screens.findIndex(s => s.name === from?.screen)
  const next = m.screens[(((at + delta) % n) + n) % n]
  return next ? { screen: next.name, pose: from?.pose ?? posesOf(m)[0] ?? 'book' } : null
}

// Where a press on a screen's name lands: its first defect, else its first pose not finished, else the pose in view.
function openPose(m: Migration, screen: Screen, current: string | undefined): string {
  const poses = posesOf(m)
  return (
    poses.find(p => cellOf(screen.cells, p).state === 'finding') ??
    poses.find(p => !FINAL.includes(cellOf(screen.cells, p).state)) ??
    (current && poses.includes(current as PoseId) ? current : poses[0] ?? 'book')
  )
}

// The cell the pane opens on: a defect if there is one, else the first shot taken, else the first screen in book.
function defaultPick(m: Migration): Pick | null {
  const first = m.screens[0]
  if (!first) return null
  const defect = step(m, null, 1, true)
  if (defect) return defect
  for (const s of m.screens) {
    const pose = posesOf(m).find(p => s.cells[p]?.after ?? s.cells[p]?.before)
    if (pose) return { screen: s.name, pose }
  }
  const poses = posesOf(m)
  return { screen: first.name, pose: poses.includes('book') ? 'book' : poses[0] ?? 'book' }
}

// --- reading the app's folder

let cwd = '.'
let home = ''
// Where the pane keeps the simulator's frames and the copies of shots it draws: ~/Library/Caches/foldsmith, set when
// the session starts (a folder of the user's own, not a shared one in /tmp).
let scratch = ''
// The status file's last seen mtime; module state, so a reload re-reads the file.
let lastMtime = -1
let liveBusy = false
let liveFrame = 0
// Bumped when the picked cell (or its shots) changes: work begun for an earlier pick is dropped, so a stale picture
// never lands on a new one. A write to the progress file that leaves the pick as it is bumps nothing.
let generation = 0
let pictureKey = ''
// Dashboard shots by file and mtime (null: too detailed to draw under the cap), the last SHRUNK_KEPT used, and the work
// under way for each.
const shrunk = new Map<string, Picture | null>()
const making = new Map<string, Promise<Picture | null | undefined>>()
// Enlarged shots cut into strips, by file and view, for the mtime they were cut from: the strips, or why there are none
// ('detail': too detailed for the cap even small; 'error': sips failed), so a failed cut is not run again until the shot
// changes. The last TILES_KEPT used; module state only, never in the plugin's state.
type Tile = { jpeg: string; y: number; tall: number }
type Tiled = { tiles: Tile[]; w: number; tall: number; nativeW: number; nativeH: number }
type Cut = Tiled | 'detail' | 'error'
const tiles = new Map<string, { at: number; cut: Cut }>()
const cutting = new Map<string, Promise<Cut | 'cancelled'>>()
// The strips the enlarged view waits for, by tileId: a cut for one no longer wanted stops at its next step.
let wanted = new Set<string>()

const tileId = (file: string, both: boolean) => `${file}@${both ? 'both' : 'single'}`

// Keeps a map to its last `most` entries used, the oldest out first.
function remember<V>(map: Map<string, V>, id: string, value: V, most: number) {
  map.delete(id)
  map.set(id, value)
  while (map.size > most) map.delete(map.keys().next().value!)
}

const parentOf = (path: string) => path.replace(/\/[^/]*$/, '') || '/'

const cacheName = (path: string) => path.replace(/[^A-Za-z0-9]/g, '_').slice(-100)

function dims(stdout: string): [number, number] {
  return [Number(/pixelWidth: (\d+)/.exec(stdout)?.[1] ?? 0), Number(/pixelHeight: (\d+)/.exec(stdout)?.[1] ?? 0)]
}

// A folder as the pane names it: relative to the session's folder, else to the home folder.
const shown = (path: string) =>
  path === cwd
    ? 'this folder'
    : path.startsWith(`${cwd}/`)
      ? path.slice(cwd.length + 1)
      : home && path.startsWith(`${home}/`)
        ? `~${path.slice(home.length)}`
        : path

async function folder($: EngineInterface) {
  return (await read($, root)) ?? cwd
}

// `dir` with one slash after it, to test whether a path is inside it ('/' stays '/').
function under(dir: string) {
  return dir.endsWith('/') ? dir : `${dir}/`
}

// Whether the session's folder is one the pane searches: not the home folder or a folder above it, where `find` would walk
// Desktop, Documents and Library every minute (and macOS would ask to let it). A session there, or one where the home
// folder is unknown, follows only a picked app. Compared without trailing slashes or case, as the Mac's disk ignores case.
function searchable() {
  const plain = (path: string) => path.replace(/\/+$/, '').toLowerCase() || '/'
  const [here, mine] = [plain(cwd), plain(home)]
  return home !== '' && mine !== here && !mine.startsWith(under(here))
}

// A folder named after `/foldsmith watch`: from the root, from the home folder (`~/apps/notes`), or from the session's
// folder.
function resolveFolder(path: string) {
  if (home && (path === '~' || path.startsWith('~/'))) return `${home}${path.slice(1)}`
  return path.startsWith('/') ? path : `${cwd}/${path}`
}

// Whether each path is a real folder or file of that kind, not a link. The app's repository can make anything in its
// `.duo` folder a link to somewhere else, so the pane reads and opens only what is really there.
async function isReal($: EngineInterface, checks: [string, 'file' | 'dir'][]) {
  for (const [path, kind] of checks) {
    const stat = await $.fs.stat(path).catch(() => null)
    if (!stat || stat.isLink || stat.kind !== kind) return false
  }
  return true
}

const progressFile = (base: string): [string, 'file' | 'dir'][] => [[`${base}/.duo`, 'dir'], [`${base}/${STATUS_FILE}`, 'file']]

// Writes the error line only when it changes, so a file that stays broken does not redraw the pane at every poll.
async function setError($: EngineInterface, message: string | null) {
  if ((await read($, error)) !== message) await update($, error, () => message)
}

// A shot's path from the progress file, as the real path of a file inside the followed folder. The progress file comes
// with the repository, so a path that leads out of the folder, by '..' or through a link, gives ''.
async function absolute($: EngineInterface, path: string) {
  if (path.split('/').includes('..')) return ''
  const base = await folder($)
  try {
    const [inside, shot] = await Promise.all([
      $.fs.stat(base, { resolve: true }),
      $.fs.stat(path.startsWith('/') ? path : `${base}/${path}`, { resolve: true }),
    ])
    const ok = shot.kind === 'file' && inside.realPath && shot.realPath?.startsWith(under(inside.realPath))
    return ok ? shot.realPath! : ''
  } catch {
    return ''
  }
}

// A PNG made into a JPEG on the first rung of `ladder` (long side, quality) whose base64 fits under TILE_MAX: null
// when even the last rung does not (never a picture over the cap), undefined when sips could not make one.
async function shrink($: EngineInterface, png: string, ladder: [number, number][], at: number): Promise<Picture | null | undefined> {
  for (const [long, quality] of ladder) {
    const out = `${scratch}/${cacheName(png)}-${long}q${quality}.jpg`
    const made = await $.process.run(['/usr/bin/sips', '-Z', String(long), '-s', 'format', 'jpeg', '-s', 'formatOptions', String(quality), png, '--out', out])
    if (made.exitCode !== 0) return undefined
    const { base64 } = await $.fs.read(out, { as: 'bytes' })
    if (base64.length > TILE_MAX) continue
    const size = await $.process.run(['/usr/bin/sips', '-g', 'pixelWidth', '-g', 'pixelHeight', out])
    const [width, height] = dims(size.stdout)
    if (!width || !height) return undefined
    return { jpeg: base64, width, height, file: png, at }
  }
  return null
}

// A shot for the dashboard, made once per file and mtime; the same shot asked for again while it is being made waits
// for that work.
async function stagePicture($: EngineInterface, png: string): Promise<Picture | null | undefined> {
  if (!scratch) return undefined
  try {
    const { mtimeMs } = await $.fs.stat(png)
    const id = `${png}@${mtimeMs}`
    if (shrunk.has(id)) {
      const pic = shrunk.get(id)!
      remember(shrunk, id, pic, SHRUNK_KEPT)
      return pic
    }
    const under_way = making.get(id)
    if (under_way) return await under_way
    const work = shrink($, png, STAGE_LADDER, mtimeMs)
    making.set(id, work)
    try {
      const pic = await work
      if (pic !== undefined) {
        // A shot made again after a capture replaces the copy of its older mtime.
        for (const old of [...shrunk.keys()]) if (old.startsWith(`${png}@`)) shrunk.delete(old)
        remember(shrunk, id, pic, SHRUNK_KEPT)
      }
      return pic
    } finally {
      making.delete(id)
    }
  } catch {
    return undefined
  }
}

// The before and after shots of the picked screen and pose, made for the dashboard. What is already made for these
// files stays while the rest is made, so the pair does not blink.
async function refreshPictures($: EngineInterface) {
  const m = await read($, migration)
  let chosen = await read($, pick)
  if (!m) return
  if (!chosen || !screenOf(m, chosen.screen)) {
    chosen = defaultPick(m)
    await update($, pick, () => chosen)
  }
  if (!chosen) return
  const cell = screenOf(m, chosen.screen)?.cells[chosen.pose]
  const files: string[] = []
  for (const path of [cell?.before, cell?.after]) {
    if (!path) continue
    const file = await absolute($, path)
    if (file) files.push(file)
  }
  // Only the refresh for the cell picked now may start a new generation; one for a pick already left goes no further.
  const now = await read($, pick)
  if (now?.screen !== chosen.screen || now?.pose !== chosen.pose) return
  const key = JSON.stringify([chosen.screen, chosen.pose, files])
  if (key !== pictureKey) {
    pictureKey = key
    generation += 1
  }
  const mine = generation
  const had = await read($, pictures)
  if (mine !== generation) return
  const kept: { [file: string]: Picture | null } = {}
  for (const file of files) if (file in had) kept[file] = had[file]!
  await update($, pictures, () => kept)
  for (const file of files) {
    const pic = await stagePicture($, file)
    if (mine !== generation) return
    if (pic !== undefined && kept[file] !== pic) await update($, pictures, value => ({ ...value, [file]: pic }))
  }
  if (await read($, zoom)) await refreshZoom($)
}

async function choosePick($: EngineInterface, next: Pick | null) {
  if (!next) return
  await update($, pick, () => next)
  await refreshPictures($)
}

// A press on a screen's name: that screen, in the pose its press lands on, and the stage scrolled into view.
async function showScreen($: EngineInterface, name: string, keepPose: boolean, block: 'start' | 'nearest') {
  const m = await read($, migration)
  const screen = m && screenOf(m, name)
  if (!m || !screen) return
  const current = (await read($, pick))?.pose
  await choosePick($, { screen: name, pose: keepPose && current ? current : openPose(m, screen, current) })
  await $.ui.scroll({ to: { key: 'stage' }, in: PANE, block }).catch(() => undefined)
}

// --- the enlarged view

// One shot cut into equal horizontal strips, each a JPEG under TILE_MAX, from a copy at most `longMax` pixels on its
// long side. A copy too detailed for its strips is made smaller (a JPEG's size falls about as the long side to the
// power 1.5, measured, so the next side aims 8% under the cap), down to ZOOM_LONG_MIN, then at a lower quality. sips
// ignores a crop that touches the picture's bottom edge (measured), so the copy is padded by a row above and below
// first and each strip is cut one row lower. A cut for a shot the view no longer waits for stops at its next step.
async function cutTiles($: EngineInterface, png: string, both: boolean, id: string): Promise<Cut | 'cancelled'> {
  const longMax = both ? ZOOM_LONG_BOTH : ZOOM_LONG_SINGLE
  const most = both ? ZOOM_TILES_BOTH : ZOOM_TILES_SINGLE
  const room = most * TILE_TARGET
  const size = await $.process.run(['/usr/bin/sips', '-g', 'pixelWidth', '-g', 'pixelHeight', png])
  const [nativeW, nativeH] = dims(size.stdout)
  if (!nativeW || !nativeH) return 'error'
  const name = `${scratch}/${cacheName(png)}`
  const least = Math.min(ZOOM_LONG_MIN, Math.max(nativeW, nativeH))
  let long = Math.min(longMax, Math.max(nativeW, nativeH))
  let quality = 55
  for (let attempt = 0; attempt < 6; attempt++) {
    if (!wanted.has(id)) return 'cancelled'
    const big = `${name}-z${long}.png`
    const made = await $.process.run(['/usr/bin/sips', '-Z', String(long), png, '--out', big])
    if (made.exitCode !== 0) return 'error'
    const bigSize = await $.process.run(['/usr/bin/sips', '-g', 'pixelWidth', '-g', 'pixelHeight', big])
    const [w, tall] = dims(bigSize.stdout)
    if (!w || !tall) return 'error'
    const probe = `${name}-z${long}q${quality}.jpg`
    const encoded = await $.process.run(['/usr/bin/sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', String(quality), big, '--out', probe])
    if (encoded.exitCode !== 0) return 'error'
    const whole = (await $.fs.read(probe, { as: 'bytes' })).base64
    if (whole.length > room) {
      const next = Math.floor((long * Math.pow(room / whole.length, 2 / 3) * 0.92) / 16) * 16
      if (next < least) {
        if (quality <= 35) return 'detail'
        quality -= 10
      }
      long = Math.max(next, least)
      continue
    }
    let count = Math.max(1, Math.ceil(whole.length / TILE_TARGET))
    if (count === 1 && whole.length <= TILE_MAX) return { tiles: [{ jpeg: whole, y: 0, tall }], w, tall, nativeW, nativeH }
    const padded = `${name}-z${long}-pad.png`
    const pad = await $.process.run(['/usr/bin/sips', '-p', String(tall + 2), String(w), '--padColor', 'FFFFFF', big, '--out', padded])
    if (pad.exitCode !== 0) return 'error'
    for (; count <= most; count++) {
      if (!wanted.has(id)) return 'cancelled'
      const bands = await cutBands($, padded, `${name}-z${long}q${quality}`, w, tall, count, quality)
      if (bands === null) return 'error'
      if (bands !== 'over') return { tiles: bands, w, tall, nativeW, nativeH }
    }
    // Every count left a strip over the cap: a lower quality first, then a smaller copy.
    if (quality > 35) quality -= 10
    else if (long > least) long = Math.max(least, Math.floor((long * 0.85) / 16) * 16)
    else return 'detail'
  }
  return 'detail'
}

// The `count` strips of a padded copy: null when sips fails or a strip is not the height asked for, 'over' when one
// is over the cap.
async function cutBands($: EngineInterface, padded: string, name: string, w: number, tall: number, count: number, quality: number): Promise<Tile[] | 'over' | null> {
  const bands: Tile[] = []
  for (let i = 0; i < count; i++) {
    const y = Math.floor((i * tall) / count)
    const band = Math.floor(((i + 1) * tall) / count) - y
    const out = `${name}-${count}-${i}.jpg`
    const made = await $.process.run(['/usr/bin/sips', '-c', String(band), String(w), '--cropOffset', String(1 + y), '0', '-s', 'format', 'jpeg', '-s', 'formatOptions', String(quality), padded, '--out', out])
    if (made.exitCode !== 0) return null
    const got = await $.process.run(['/usr/bin/sips', '-g', 'pixelHeight', out])
    if (dims(got.stdout)[1] !== band) return null
    const { base64 } = await $.fs.read(out, { as: 'bytes' })
    if (base64.length > TILE_MAX) return 'over'
    bands.push({ jpeg: base64, y, tall: band })
  }
  return bands
}

// The strips of a shot (or why there are none), cut once per mtime and kept among the last TILES_KEPT used: true when
// a new result landed. A cut a newer pick stopped is started again when the view waits for that shot once more.
async function ensureTiles($: EngineInterface, png: string, both: boolean): Promise<boolean> {
  if (!scratch) return false
  try {
    const { mtimeMs } = await $.fs.stat(png)
    const id = tileId(png, both)
    const had = tiles.get(id)
    if (had && had.at === mtimeMs) {
      remember(tiles, id, had, TILES_KEPT)
      return false
    }
    const job = `${id}@${mtimeMs}`
    for (let tries = 0; tries < 2; tries++) {
      let work = cutting.get(job)
      if (!work) {
        work = cutTiles($, png, both, id).catch(() => 'error' as const)
        cutting.set(job, work)
        void work.then(() => cutting.delete(job))
      }
      const cut = await work
      if (cut !== 'cancelled') {
        remember(tiles, id, { at: mtimeMs, cut }, TILES_KEPT)
        return true
      }
      if (!wanted.has(id)) return false
    }
    return false
  } catch {
    return false
  }
}

// The strips the enlarged view needs, when it is drawn sharp (on the desktop and in VS Code): the shown side or sides,
// and for one side the other as well, so flipping between before and after is instant. The pane redraws as each set
// lands.
async function refreshZoom($: EngineInterface) {
  const view = await read($, zoom)
  const m = await read($, migration)
  const chosen = await read($, pick)
  const cell = m && chosen ? screenOf(m, chosen.screen)?.cells[chosen.pose] : undefined
  if (!view?.sharp || !cell || !scratch) {
    wanted = new Set()
    return
  }
  const both = view.side === 'both'
  const order: Side[] = view.side === 'after' ? ['after', 'before'] : ['before', 'after']
  const files: string[] = []
  for (const side of order) {
    const file = cell[side] ? await absolute($, cell[side]!) : ''
    if (file) files.push(file)
  }
  wanted = new Set(files.map(file => tileId(file, both)))
  for (const file of files) {
    const landed = await ensureTiles($, file, both)
    if (landed && (await read($, zoom))) await update($, zoomRev, n => n + 1)
  }
}

// `sharp`: the surface draws the enlarged shot from strips cut for it; the others draw what they already have.
async function enterZoom($: EngineInterface, side: ZoomSide, sharp: boolean) {
  await update($, zoom, () => ({ side, sharp }))
  await $.ui.scroll({ to: 'start', in: PANE }).catch(() => undefined)
  await refreshZoom($)
}

async function leaveZoom($: EngineInterface) {
  wanted = new Set()
  await update($, zoom, () => null)
  await $.ui.scroll({ to: { key: 'stage' }, in: PANE, block: 'start' }).catch(() => undefined)
}

// The followed folder's branch and whether the skill has written its report there.
async function describeFolder($: EngineInterface, base: string) {
  const git = await $.process.run(['/usr/bin/git', '-C', base, 'branch', '--show-current'], { timeoutMs: 3000 })
  const report = await $.fs.exists(`${base}/.duo/REPORT.md`)
  await update($, folderInfo, () => ({ branch: git.exitCode === 0 ? git.stdout.trim() || null : null, report }))
}

// Every 1.5 seconds: the progress file, and while a shot is enlarged its strips (a reload forgets them, and a shot
// captured again needs new ones; strips already cut, or a cut that failed, for the same mtime are not cut again).
async function poll($: EngineInterface) {
  if ((await read($, source)) === 'demo') return
  if (!(await readProgress($)) && (await read($, zoom))?.sharp) await refreshZoom($)
}

// Reads the progress file when it changed: true when it did and the pictures were made again.
async function readProgress($: EngineInterface): Promise<boolean> {
  const base = await folder($)
  const file = `${base}/${STATUS_FILE}`
  try {
    if (!(await $.fs.exists(file))) {
      if (lastMtime !== -1) {
        lastMtime = -1
        await update($, migration, () => null)
        await update($, source, () => 'none')
      }
      await setError($, null)
      return false
    }
    if (!(await isReal($, progressFile(base)))) {
      // Read again in full once a real file is back, even one with the old file's mtime.
      lastMtime = -1
      throw new Error('a link, not a file in the app folder: not read')
    }
    const { mtimeMs } = await $.fs.stat(file)
    if (mtimeMs === lastMtime) return false
    const firstSeen = lastMtime === -1
    lastMtime = mtimeMs
    const parsed = JSON.parse(await $.fs.read(file)) as Migration
    if (!parsed || !Array.isArray(parsed.screens)) throw new Error('missing "screens" array')
    await update($, migration, () => parsed)
    await update($, source, () => 'file')
    await setError($, null)
    // A finished migration starts with the simulator paused: nothing moves there until someone resumes it.
    if (firstSeen) await update($, paused, () => parsed.phase === 'done')
    await describeFolder($, base)
    await refreshPictures($)
    if (firstSeen) void $.ui.open({ id: PANE, title: TITLE })
    return true
  } catch (err) {
    await setError($, `${file}: ${err instanceof Error ? err.message : String(err)}`)
    return false
  }
}

// Progress files under the session's folder (past build output and captures) and those followed before, newest first.
// A search that fails or runs out of time finds nothing this time; the pane goes on with the folders it remembers.
async function discover($: EngineInterface): Promise<Known[]> {
  const prune = ['node_modules', '.git', '.build', 'build', 'DerivedData', 'captures'].flatMap((name, i) =>
    i === 0 ? ['-name', name] : ['-o', '-name', name],
  )
  const found = !searchable()
    ? { stdout: '' }
    : await $.process.run(
        ['/usr/bin/find', cwd, '-maxdepth', '5', '(', ...prune, ')', '-prune', '-o', '-path', '*/.duo/migration.json', '-print'],
        { timeoutMs: 8000 },
      ).catch(() => ({ stdout: '' }))
  const recent = await $.store.get('recent')
  const roots = new Set<string>([
    ...found.stdout
      .split('\n')
      .filter(Boolean)
      .map(file => parentOf(parentOf(file))),
    ...(Array.isArray(recent) ? recent.filter((r): r is string => typeof r === 'string') : []),
  ])
  const list: Known[] = []
  for (const r of roots) {
    const file = `${r}/${STATUS_FILE}`
    try {
      if (!(await isReal($, progressFile(r)))) continue
      const { mtimeMs } = await $.fs.stat(file)
      const app = (JSON.parse(await $.fs.read(file)) as Migration).app
      list.push({ root: r, app: app ?? r.split('/').pop() ?? r, mtime: mtimeMs })
    } catch {
      // An unreadable progress file is left out of the list; following it shows why.
    }
  }
  list.sort((a, b) => b.mtime - a.mtime)
  await update($, known, () => list)
  await $.store.set(
    'recent',
    list.map(k => k.root).slice(0, 8),
  )
  return list
}

// Everything that belongs to one app's run: cleared when the pane follows another, or shows the sample.
async function clearView($: EngineInterface) {
  generation += 1
  pictureKey = ''
  wanted = new Set()
  await update($, pick, () => null)
  await update($, pictures, () => ({}))
  await update($, zoom, () => null)
  await update($, logView, () => ({ start: 0, count: LOG_DEFAULT }))
  await update($, doneShown, () => false)
  await update($, doneStart, () => 0)
  await update($, leftStart, () => 0)
}

async function switchTo($: EngineInterface, path: string | null) {
  lastMtime = -1
  await update($, root, () => path)
  await update($, migration, () => null)
  await update($, source, () => 'none')
  await update($, live, () => null)
  await clearView($)
  await update($, folderInfo, () => ({ branch: null, report: false }))
  await setError($, null)
  await poll($)
}

// Follows the folder picked for this session's folder, else the progress file that changed last.
async function choose($: EngineInterface) {
  const list = await discover($)
  const picked = await $.store.get(`watch:${cwd}`)
  const here = searchable() ? list.find(k => k.root === cwd || k.root.startsWith(under(cwd))) : undefined
  const next = typeof picked === 'string' ? picked : here?.root ?? null
  if (next !== (await read($, root))) await switchTo($, next)
}

// `path` null goes back to following the newest progress file.
async function follow($: EngineInterface, path: string | null) {
  await $.store.set(`watch:${cwd}`, path)
  if ((await read($, source)) === 'demo') await update($, source, () => 'none')
  if (path) await switchTo($, path)
  else await choose($)
}

async function showDemo($: EngineInterface) {
  await update($, migration, () => DEMO)
  await update($, source, () => 'demo')
  await setError($, null)
  await clearView($)
  await update($, pick, () => defaultPick(DEMO))
}

// The booted iPhone Duo simulator: the one the progress file names when that one is booted, else the first booted.
// Only a booted one, as duo.py boots a simulator it is given that is shut down.
async function findDuo($: EngineInterface, named?: string): Promise<string | null> {
  const listed = await $.process.run(['/usr/bin/xcrun', 'simctl', 'list', 'devices', 'booted', '-j'], { timeoutMs: 15000 })
  try {
    const devices = JSON.parse(listed.stdout).devices as { [runtime: string]: { udid: string; name: string }[] }
    const duos = Object.values(devices).flat().filter(d => /duo/i.test(d.name)).map(d => d.udid)
    return (named && duos.includes(named) ? named : duos[0]) ?? null
  } catch {
    return null
  }
}

// The duo.py the pane runs for the live view: only one in the user's own folders, where the skill fetches it, never a
// path from a progress file or the project, which anyone who shares a repository can write.
async function findDriver($: EngineInterface): Promise<string | null> {
  if (!home) return null
  for (const path of [`${home}/Library/Caches/duo-driver/scripts/duo.py`, `${home}/.claude/skills/iphone-duo-simulator/scripts/duo.py`])
    if (await $.fs.exists(path)) return path
  return null
}

// A before or after shot, opened in Preview. Its path comes from the progress file, so only an image is opened.
async function openShot($: EngineInterface, path: string) {
  const file = await absolute($, path)
  if (!file || !/\.(png|jpe?g)$/i.test(file)) return
  await $.process.run(['/usr/bin/open', '-a', '/System/Applications/Preview.app', file])
}

// Open report and Show captures. Both are in the app's folder, which its repository fills, so each must be a real
// folder or file there, not a link (a link could lead to a script that open would run). The report opens as text, and
// the captures folder is shown in Finder, never opened, so a folder made to look like an app cannot launch.
async function openDuo($: EngineInterface, base: string, name: 'REPORT.md' | 'captures') {
  if (!(await isReal($, [[`${base}/.duo`, 'dir'], [`${base}/.duo/${name}`, name === 'captures' ? 'dir' : 'file']]))) return
  await $.process.run(name === 'captures' ? ['/usr/bin/open', '-R', `${base}/.duo/captures`] : ['/usr/bin/open', '-t', `${base}/.duo/REPORT.md`])
}

// One frame of the simulator: the panel that is drawing (through duo.py when it is there), made small. Only while the
// pane is on screen, not paused, not enlarged, and the migration small enough to draw it.
async function liveTick($: EngineInterface) {
  if (liveBusy || !scratch || (await read($, source)) !== 'file' || (await read($, paused)) || (await read($, zoom))) return
  const m = await read($, migration)
  if (!m || m.screens.length > LIVE_MAX_SCREENS) return
  const pane = (await $.ui.panes()).find(p => p.id === PANE)
  if (!pane || !pane.isPlaced || !pane.isShown) return
  liveBusy = true
  try {
    const udid = await findDuo($, m.simulator)
    if (!udid) {
      await update($, liveNote, () => 'no booted iPhone Duo simulator')
      return
    }
    const driver = await findDriver($)
    let png: string | null = null
    if (driver) {
      const shot = await $.process.run(['/usr/bin/python3', driver, '--udid', udid, 'shot', '--out', scratch, '--name', 'live'], {
        timeoutMs: 25000,
      })
      png = /(\/\S+live-(?:cover|inner)\.png)/.exec(shot.stdout)?.[1] ?? null
    } else {
      const shot = await $.process.run(['/usr/bin/xcrun', 'simctl', 'io', udid, 'screenshot', `${scratch}/live.png`], { timeoutMs: 15000 })
      png = shot.exitCode === 0 ? `${scratch}/live.png` : null
    }
    const pic = png ? await shrink($, png, LIVE_LADDER, Date.now()) : null
    if (!pic) {
      await update($, liveNote, () => 'the simulator is not drawing')
      return
    }
    liveFrame += 1
    await update($, live, () => pic)
    await update($, liveNote, () => null)
  } catch (err) {
    await update($, liveNote, () => (err instanceof Error ? err.message : String(err)))
  } finally {
    liveBusy = false
  }
}

const panelOf = (file: string) => (file.includes('live-inner') ? 'inner display' : file.includes('live-cover') ? 'outer display' : 'screen')

// --- drawing the pane

// The elements the pane draws with. Every surface's table holds every name at run time (a name a surface lacks draws
// nothing), so the pane decides by `e.surface`, never by what the table holds.
type Kit = {
  Box: ElementConstructor<BoxProps>
  Text: ElementConstructor<TextProps>
  Button: ElementConstructor<ButtonProps>
  Select: ElementConstructor<SelectProps>
  Svg: ElementConstructor<SvgProps>
  Image: ElementConstructor<ImageProps>
}

type Geometry = {
  surface: string
  cols: number
  rows: number
  // CSS pixels per cell, the usable width in pixels, and the tallest a dashboard shot is drawn.
  pxc: number
  px: number
  capH: number
  wide: boolean
  mobile: boolean
  // The desktop and VS Code: a pointer and keys, and the Mac's own apps to open things in.
  pointer: boolean
  graphical: boolean
}

function geometry(surface: string, cols: number, rows: number): Geometry {
  const pxc = PX_PER_CELL[surface] ?? 7
  const mobile = surface === 'mobile'
  return {
    surface,
    cols,
    rows,
    pxc,
    px: Math.max(240, Math.floor((cols - 1) * pxc)),
    capH: clamp(Math.round(rows * PX_PER_ROW * 0.62), 300, 640),
    wide: !mobile && cols >= WIDE_COLS,
    mobile,
    pointer: surface === 'desktop' || surface === 'vscode',
    graphical: surface === 'desktop' || surface === 'vscode' || mobile,
  }
}

type Side = 'before' | 'after'
// A shot of the picked cell: its path in the progress file, its real file ('' when there is none inside the app's
// folder) and that file's mtime, and the picture (undefined while it is being made, null when it is too detailed to
// draw).
type Shot = { path?: string; file: string; at: number; pic: Picture | null | undefined }

type Ctx = {
  m: Migration
  from: Source
  base: string
  g: Geometry
  poses: PoseId[]
  tally: Record<CellState, number>
  total: number
  finished: number
  left: string[]
  done: string[]
  status: { text: string; color: Color }
  chosen: Pick | null
  screen: Screen | undefined
  cell: Cell | undefined
  codes: string[]
  shots: Record<Side, Shot>
  aspect: number
  fold: 'active' | 'inactive' | undefined
  info: Folder
  frame: Picture | null
  frameNote: string | null
  isPaused: boolean
  found: Known[]
  start: string
  where: string
  log: LogView
  doneOpen: boolean
  doneFrom: number
  leftFrom: number
  // The enlarged view fits the pane's height (else it fills the width).
  fit: boolean
}

// The characters of text a drawing holds, as the engine counts them: texts, labels, alts and options.
function drawnText(node: unknown): number {
  if (typeof node === 'string') return node.length
  if (typeof node === 'number') return String(node).length
  if (!node || typeof node !== 'object') return 0
  if (Array.isArray(node)) return node.reduce((n: number, child) => n + drawnText(child), 0)
  const el = node as { props?: { [name: string]: unknown }; children?: unknown }
  const props = el.props ?? {}
  let n = 0
  for (const name of ['label', 'alt', 'placeholder']) if (typeof props[name] === 'string') n += (props[name] as string).length
  if (Array.isArray(props.options)) for (const o of props.options as { value: string; label?: string }[]) n += (o.label ?? o.value).length
  return n + drawnText(el.children ?? props.children ?? [])
}

// A name on a button when it is short, else the name as wrapping text beside a short button.
function named(k: Kit, key: string, verb: string, name: string, onPress: () => void, dim = true) {
  const { Box, Text, Button } = k
  if (name.length <= NAME_BUTTON_MAX) return <Button key={key} plain dimColor={dim} label={verb ? `${verb} ${name}` : name} onPress={onPress} />
  return (
    <Box flexDirection="row" flexWrap="wrap" alignItems="center" columnGap={1}>
      <Text size="footnote" dimColor={dim} wrap="wrap">
        {breakable(name)}
      </Text>
      <Button key={key} plain dimColor={dim} label={verb || 'Follow'} onPress={onPress} />
    </Box>
  )
}

// A shot's size on the dashboard, `room` pixels across: side by side while each keeps a useful size (170 px for a
// portrait shot, 300 for a landscape one), never taller than the cap.
function pairSize(room: number, aspect: number, capH: number) {
  const half = Math.floor((room - GAP_PX) / 2)
  const sideBySide = aspect < 1 ? half >= 170 : half >= 300
  const w = Math.max(120, Math.min(sideBySide ? half : room, Math.floor(capH * aspect)))
  return { w, tall: Math.round(w / aspect), sideBySide }
}

// The width an enlarged shot is drawn at and whether two sit side by side: one shot fitted to the pane's height (or
// filling its width), two side by side or one above the other. Never narrower than the dashboard draws the shots (two
// that would be are drawn one above the other across the whole width), and never wider or taller than a drawing may be.
function zoomWidth(g: Geometry, aspect: number, both: boolean, fit: boolean): { w: number; row: boolean } {
  const room = g.px
  const dash = pairSize(room, aspect, g.capH).w
  const fitting = fit && g.pointer
  // The pane's visible height less the controls above the shot.
  const fitH = Math.max(240, g.rows * PX_PER_ROW - (room < 700 ? 270 : 200))
  let w: number
  let row = false
  if (!both) w = Math.max(dash, fitting ? Math.min(room, Math.floor(fitH * aspect)) : room)
  else {
    const half = Math.floor((room - GAP_PX) / 2)
    if (fitting) {
      const beside = Math.min(half, Math.floor(fitH * aspect))
      const above = Math.min(room, Math.floor(((fitH - 40) / 2) * aspect))
      row = beside >= above
      w = row ? beside : above
    } else {
      row = aspect < 1 && half >= 170
      w = row ? half : room
    }
    if (w < dash * 1.25) {
      row = false
      w = room
    }
  }
  return { w: clamp(w, 120, Math.floor(SVG_MAX * Math.min(1, aspect))), row }
}

// What the dashboard offers to enlarge: each shot on the desktop and in VS Code (the enlarged view also opens the
// capture in Preview), on the phone only where that draws it larger; both at once only where they draw larger together.
function offers(c: Ctx) {
  const dash = pairSize(c.g.px, c.aspect, c.g.capH).w
  const single = c.g.graphical && (c.g.pointer || zoomWidth(c.g, c.aspect, false, c.fit).w > dash * 1.1)
  const compare =
    c.g.pointer && Boolean(c.shots.before.file && c.shots.after.file) && zoomWidth(c.g, c.aspect, true, c.fit).w > dash * 1.1
  return { single, compare }
}

// The matrix's measures `room` pixels across: the name column (the longest name a button carries, and a button's
// padding; a longer name wraps there beside its View button), the pose columns (COL_PX_WIDE when `fixed`), and
// whether names stand on their own line above their cells because a row would not fit.
function matrixSize(c: Ctx, room: number, fixed: boolean) {
  const n = c.poses.length
  const short = c.m.screens.map(s => s.name.length).filter(length => length <= NAME_BUTTON_MAX)
  const anyLong = short.length < c.m.screens.length
  const nameCols = clamp(Math.max(4, ...short) + 5, anyLong ? 16 : 10, NAME_BUTTON_MAX + 5)
  const stacked = nameCols * c.g.pxc + n * COL_MIN > room
  const colPx = fixed ? COL_PX_WIDE : clamp(Math.floor((room - (stacked ? 0 : nameCols * c.g.pxc)) / n), COL_MIN, COL_MAX)
  const navCols = nameCols + Math.ceil((n * colPx) / c.g.pxc) + 1
  return { nameCols, colPx, stacked, navCols, full: colPx >= 56 }
}

// The header's first lines: the app, where the run stands, the actions, and the folder and branch.
function headerTop($: EngineInterface, k: Kit, c: Ctx) {
  const { Box, Text, Button } = k
  const actions = c.from === 'file' && (
    <Box key="actions" flexDirection="row" flexWrap="wrap" columnGap="xs" rowGap="xs">
      {(c.m.phase !== 'done' || c.left.length > 0) && (
        <Button key="resume" variant="primary" label={c.m.phase === 'done' ? 'Resume migration' : 'Restart if stopped'} onPress={() => void $.prompt.fill({ text: c.start })} />
      )}
      {!c.g.mobile && c.info.report && <Button key="report" label="Open report" onPress={() => void openDuo($, c.base, 'REPORT.md')} />}
      {!c.g.mobile && <Button key="captures" label="Show captures" onPress={() => void openDuo($, c.base, 'captures')} />}
    </Box>
  )
  return (
    <Box key="header" flexDirection="column" gap="xs">
      <Box flexDirection="row" flexWrap="wrap" alignItems="center" justifyContent="space-between" columnGap={2} rowGap="sm">
        <Box flexDirection="row" flexWrap="wrap" alignItems="center" columnGap={1}>
          <Text size={c.g.cols < 90 ? 'heading' : 'title'} weight="semibold">
            {c.m.app ?? 'iPhone Duo migration'}
          </Text>
          <Text size="footnote" weight="medium" color={c.status.color}>
            {c.status.text}
          </Text>
        </Box>
        {c.g.cols >= 90 && actions}
      </Box>
      {c.where && (
        <Text size="footnote" dimColor wrap="wrap">
          {c.where}
        </Text>
      )}
      {c.g.cols < 90 && actions && (
        <Box flexDirection="column" marginTop="sm">
          {actions}
        </Box>
      )}
    </Box>
  )
}

// The figures that say how far the run is, `cols` cells wide and spread across it: screens finished, poses good,
// defects by class with a button to the next one, and what is left; under them the bar of every cell by state.
function overview($: EngineInterface, k: Kit, c: Ctx, cols: number) {
  const { Box, Text, Button, Svg } = k
  const good = c.tally.verified + c.tally.unchanged
  const twoByTwo = cols < 84
  const count = c.m.phase === 'done' ? 4 : 3
  const tileCols = twoByTwo ? Math.floor((cols - 3) / 2) : Math.floor((cols - 1 - 3 * (count - 1)) / count)
  const tile = (key: string, value: string, label: string, color: Color | undefined, more?: RenderElement | false | null) => (
    <Box key={key} flexDirection="column" width={tileCols} flexGrow={1} flexShrink={1}>
      <Text size="title" weight="semibold" tabular color={color}>
        {value}
      </Text>
      <Text size="caption" dimColor>
        {label}
      </Text>
      {more}
    </Box>
  )
  const classes = classLine(c.m)
  const defects = c.tally.finding > 0 && c.chosen && (
    <Box flexDirection="row" flexWrap="wrap" alignItems="center" columnGap={1}>
      {classes && (
        <Text size="caption" color="error" wrap="wrap">
          {classes}
        </Text>
      )}
      <Button key="inspect" plain label="Inspect next" onPress={() => void inspectNext($)} />
    </Box>
  )
  const tiles = [
    tile('kpi-screens', `${c.finished} of ${c.m.screens.length}`, 'screens finished', undefined),
    tile('kpi-poses', `${good} of ${c.total}`, 'poses good', 'success'),
    tile('kpi-defects', String(c.tally.finding), c.tally.finding === 1 ? 'defect' : 'defects', c.tally.finding ? 'error' : 'subtle', defects),
    c.m.phase === 'done' && tile('kpi-left', String(c.left.length), 'left for you', c.left.length ? 'warning' : 'success'),
  ].filter(Boolean)
  const bar = barSvg(c.tally, c.total, Math.floor((cols - 1) * c.g.pxc))
  return (
    <Box key="overview" flexDirection="column" gap="md">
      {twoByTwo ? (
        <Box key="kpis" flexDirection="column" gap="md">
          <Box flexDirection="row" columnGap={3} alignItems="flex-start">
            {tiles.slice(0, 2)}
          </Box>
          <Box flexDirection="row" columnGap={3} alignItems="flex-start">
            {tiles.slice(2)}
          </Box>
        </Box>
      ) : (
        <Box key="kpis" flexDirection="row" alignItems="flex-start" columnGap={3}>
          {tiles}
        </Box>
      )}
      {c.total > 0 && (
        <Svg
          source={bar.source}
          width={bar.width}
          height={bar.height}
          alt={`${LEGEND.filter(item => c.tally[item.state] > 0)
            .map(item => `${item.label} ${c.tally[item.state]}`)
            .join(', ')}, of ${c.total} cells`}
        />
      )}
    </Box>
  )
}

async function inspectNext($: EngineInterface) {
  const m = await read($, migration)
  if (!m) return
  await choosePick($, step(m, await read($, pick), 1, true))
  await $.ui.scroll({ to: { key: 'stage' }, in: PANE, block: 'start' }).catch(() => undefined)
}

function stepper(k: Kit, c: Ctx) {
  const { Box, Text } = k
  const at = phaseIndex(c.m.phase)
  return (
    c.m.phase !== 'done' && (
      <Box flexDirection="row" columnGap={1} flexWrap="wrap">
        {PHASES.map((p, i) => (
          <Text size="footnote" weight={i === at ? 'semibold' : 'regular'} dimColor={i > at}>
            {i < at ? '✓' : i === at ? '●' : '○'} {p.label}
            {i < PHASES.length - 1 ? '  ›' : ''}
          </Text>
        ))}
      </Box>
    )
  )
}

// The picked cell's title and its state chip.
function stageTitle(k: Kit, c: Ctx) {
  const { Box, Text } = k
  if (!c.chosen || !c.cell) return null
  return (
    <Box flexDirection="row" flexWrap="wrap" alignItems="center" columnGap={1} rowGap="xs">
      <Text size="heading" weight="semibold" wrap="wrap">
        {`${soft(c.chosen.screen)} · ${poseLabel(c.chosen.pose)}`}
      </Text>
      <Text size="footnote" weight="semibold" color="inverseText" backgroundColor={CHIP_COLOR[c.cell.state]}>
        {` ${STATE_WORD[c.cell.state]} `}
      </Text>
    </Box>
  )
}

// The pattern, the defect classes, and any class waived for this cell with the reason.
function meta(k: Kit, c: Ctx) {
  const { Box, Text } = k
  const waived = Object.entries(c.cell?.waived ?? {})
  if (!c.screen?.pattern && c.codes.length === 0 && waived.length === 0) return null
  return (
    <Box key="meta" flexDirection="column">
      {c.screen?.pattern && (
        <Text size="footnote" dimColor wrap="wrap">
          Pattern: {c.screen.pattern}
        </Text>
      )}
      {c.codes.length > 0 &&
        (c.cell?.state === 'finding' ? (
          <Text size="footnote" color="error" wrap="wrap">
            {c.codes.map(describe).join(' · ')}
          </Text>
        ) : (
          <Text size="footnote" dimColor wrap="wrap">
            Found in the audit: {c.codes.map(describe).join(' · ')}
          </Text>
        ))}
      {waived.map(([code, why]) => (
        <Text size="footnote" dimColor wrap="wrap">
          Waived {describe(code)}: {soft(why)}
        </Text>
      ))}
    </Box>
  )
}

// Every pose of the picked screen as a button, the picked one primary, the others with their mark; keys 1 to 8.
function poseStrip($: EngineInterface, k: Kit, c: Ctx) {
  const { Box, Text, Button } = k
  if (!c.chosen || !c.screen) return null
  const screen = c.screen
  const name = c.chosen.screen
  return (
    <Box key="poses" flexDirection="row" flexWrap="wrap" alignItems="center" columnGap="xs" rowGap="xs">
      <Text size="footnote" dimColor>
        Pose
      </Text>
      {c.poses.map((pose, i) => {
        const cell = cellOf(screen.cells, pose)
        const picked = pose === c.chosen?.pose
        const mark = picked ? '' : poseMark(cell)
        return (
          <Button
            key={`pose:${pose}`}
            hotkey={i < 9 ? String(i + 1) : undefined}
            variant={picked ? 'primary' : undefined}
            plain={picked ? undefined : true}
            label={poseLabel(pose)}
            onPress={() => void choosePick($, { screen: name, pose })}
          >
            {mark && <Text color={STATE_COLOR[cell.state]}>{`${mark} `}</Text>}
            {poseLabel(pose)}
          </Button>
        )
      })}
    </Box>
  )
}

// The Screen Select, only where it draws and nothing in it would be cut; else ‹ Screen and Screen › (keys k and j).
const screenSelect = (c: Ctx) => !c.g.mobile && c.m.screens.length <= SELECT_MAX && c.m.screens.every(s => s.name.length <= SELECT_LABEL)

// The screen picker and the steps through the cells: the screen steps plain, the cell steps as buttons.
function nav($: EngineInterface, k: Kit, c: Ctx) {
  const { Box, Button, Select } = k
  if (!c.chosen) return null
  const chosen = c.chosen
  const m = c.m
  return (
    <Box key="nav" flexDirection="row" flexWrap="wrap" alignItems="center" columnGap="xs" rowGap="xs">
      {screenSelect(c) ? (
        <Select
          key="screen"
          label="Screen"
          options={m.screens.map(s => ({ value: s.name }))}
          value={chosen.screen}
          onSelect={(value: string) => void choosePick($, { ...chosen, screen: value })}
        />
      ) : (
        [
          <Button key="screen-prev" hotkey="k" plain label="‹ Screen" onPress={() => void choosePick($, stepScreen(m, chosen, -1))} />,
          <Button key="screen-next" hotkey="j" plain label="Screen ›" onPress={() => void choosePick($, stepScreen(m, chosen, 1))} />,
        ]
      )}
      <Button key="prev" hotkey="p" label="‹ Previous" onPress={() => void choosePick($, step(m, chosen, -1))} />
      <Button key="next" hotkey="n" label="Next ›" onPress={() => void choosePick($, step(m, chosen, 1))} />
      {c.tally.finding > 0 && <Button key="next-defect" hotkey="d" label="Next defect" onPress={() => void choosePick($, step(m, chosen, 1, true))} />}
    </Box>
  )
}

// The skill's notes that name the picked screen, each in full: what is left first, then what is done (dim), as many as
// fit WHY_BUDGET. A note about this screen alone drops its name; one about several keeps it.
function why(k: Kit, c: Ctx, cols?: number) {
  const { Box, Text } = k
  if (!c.chosen) return null
  const name = c.chosen.screen
  const notes = [...c.left.map(line => ({ line, done: false })), ...c.done.map(line => ({ line, done: true }))]
    .map(note => ({ ...note, names: namedScreens(c.m, note.line) }))
    .filter(note => note.names.includes(name))
  if (notes.length === 0) return null
  const shown = page(notes.map(note => note.line), 0, WHY_BUDGET).end
  const rest = notes.length - shown
  return (
    <Box key="why" flexDirection="column" gap="xs" width={cols} flexShrink={1}>
      <Text size="footnote" weight="semibold">
        Why
      </Text>
      {notes.slice(0, shown).map(note => (
        <Text size="footnote" dimColor={note.done} wrap="wrap">
          {soft(note.names.length === 1 ? note.line.slice(note.line.indexOf(': ') + 2) : note.line)}
        </Text>
      ))}
      {rest > 0 && (
        <Text size="footnote" dimColor wrap="wrap">
          {rest === 1 ? '1 more note on this screen is in the lists below' : `${rest} more notes on this screen are in the lists below`}
        </Text>
      )}
    </Box>
  )
}

function keysLine(k: Kit, c: Ctx, zoomed: boolean, canFit = false) {
  const { Text } = k
  if (!c.g.pointer || !c.chosen) return null
  const can = offers(c)
  const parts = zoomed
    ? [`1–${c.poses.length} pose`, 'n/p next/previous', 'j/k screen', c.tally.finding > 0 && 'd next defect', 'b/a/c view', canFit && 'f fit or fill', 'z back']
    : [
        `1–${c.poses.length} pose`,
        'n next',
        'p previous',
        !screenSelect(c) && 'j/k screen',
        c.tally.finding > 0 && 'd next defect',
        can.compare && 'c compare',
        can.single && c.shots.before.file && 'b before',
        can.single && c.shots.after.file && 'a after',
      ]
  return (
    <Text size="caption" dimColor wrap="wrap">
      Keys: {parts.filter(Boolean).join(' · ')}
    </Text>
  )
}

const FOLD_NOTE = {
  active: 'Blue band: the fold, where the phone bends',
  inactive: 'Dashed outline: the fold, lying flat',
  none: 'No fold in this pose',
}

// Before and after, as large as the room and the cap allow (each at its own shape), each with a button that enlarges
// it; under them, what the fold drawing means and the button that compares both enlarged. A pose with no shots says
// so in one line.
function pairBlock($: EngineInterface, k: Kit, c: Ctx, room: number) {
  const { Box, Text, Button, Svg } = k
  if (!c.chosen) return null
  if (!c.shots.before.path && !c.shots.after.path)
    return (
      <Box key="pair-block" flexDirection="column">
        <Text size="footnote" dimColor wrap="wrap">
          No shots yet for this pose
        </Text>
      </Box>
    )
  const { w, tall, sideBySide } = pairSize(room, c.aspect, c.g.capH)
  const label = `${c.chosen.screen} in ${poseLabel(c.chosen.pose)}`
  const can = offers(c)
  const shot = (side: Side) => {
    const s = c.shots[side]
    const note = !s.path
      ? 'Not captured yet'
      : !s.file
        ? 'Not found in the app folder'
        : s.pic === undefined
          ? 'Loading'
          : 'Too detailed to draw here'
    const own = s.pic ? s.pic.width / s.pic.height : c.aspect
    const sw = Math.max(120, Math.min(w, Math.floor(c.g.capH * own)))
    const drawing = s.pic ? shotSvg(s.pic, sw, Math.round(sw / own), c.fold, `shot-${side}`) : emptySvg(w, tall, note)
    return (
      <Box key={`shot-${side}`} flexDirection="column" gap="xs">
        <Box flexDirection="row" alignItems="center" justifyContent="space-between" columnGap={1}>
          <Text size="footnote" weight="semibold">
            {side === 'before' ? 'Before' : 'After'}
          </Text>
          {s.file && can.single && (
            <Button key={`zoom-${side}`} plain hotkey={side === 'before' ? 'b' : 'a'} label="Enlarge" onPress={() => void enterZoom($, side, c.g.pointer)} />
          )}
        </Box>
        <Svg source={drawing.source} width={drawing.width} height={drawing.height} alt={`${label}, ${side}`} />
      </Box>
    )
  }
  return (
    <Box key="pair-block" flexDirection="column" gap="sm">
      <Box key="pair" flexDirection={sideBySide ? 'row' : 'column'} columnGap={2} rowGap="md" alignItems="flex-start">
        {shot('before')}
        {shot('after')}
      </Box>
      <Box key="pair-foot" flexDirection="row" flexWrap="wrap" alignItems="center" columnGap={2} rowGap="xs">
        {can.compare && <Button key="zoom" hotkey="c" label="Compare full size" onPress={() => void enterZoom($, 'both', true)} />}
        <Text size="caption" dimColor wrap="wrap">
          {FOLD_NOTE[c.fold ?? 'none']}
        </Text>
      </Box>
    </Box>
  )
}

// A row's cells for a screen reader, grouped by state: 'Defect T5: Book; Verified: Closed, Laptop'.
function rowAlt(c: Ctx, s: Screen) {
  const groups = new Map<string, string[]>()
  for (const pose of c.poses) {
    const cell = cellOf(s.cells, pose)
    const codes = codesOf(cell)
    const head = `${STATE_WORD[cell.state]}${codes.length ? ` ${codes.join(' ')}` : ''}`
    groups.set(head, [...(groups.get(head) ?? []), poseLabel(pose)])
  }
  const parts = [...groups].map(([head, poses]) => (poses.length === c.poses.length ? `${head} in every pose` : `${head}: ${poses.join(', ')}`))
  return `${s.name} row: ${parts.join('; ')}`
}

// The screen × pose matrix: a header drawing of the poses, then one row per screen: its name, pressable, and a drawing
// of its cells. A finished screen's name is dim, so the screens that need attention stand out; the picked one is in
// the accent colour, as its cell and pose are. A long name wraps in the name column beside a View button.
function matrix($: EngineInterface, k: Kit, c: Ctx, room: number, fixed: boolean) {
  const { Box, Text, Button, Svg } = k
  const size = matrixSize(c, room, fixed)
  const picked = c.chosen
  const head = headSvg(c.poses, size.colPx, picked?.pose, size.full)
  const stripW = c.poses.length * size.colPx
  const pressRow = (name: string) => () => void showScreen($, name, true, c.g.wide ? 'nearest' : 'start')
  return (
    <Box key="matrix" flexDirection="column">
      <Text weight="semibold">Screens ({c.m.screens.length})</Text>
      <Box flexDirection="row" alignItems="flex-end">
        {!size.stacked && <Box width={size.nameCols} flexShrink={0} />}
        <Svg
          source={head.source}
          width={head.width}
          height={head.height}
          alt={`Screen by pose matrix, ${c.m.screens.length} screens by ${c.poses.length} poses${picked ? `; picked ${picked.screen} in ${poseLabel(picked.pose)}` : ''}`}
        />
      </Box>
      {c.m.screens.map(s => {
        const isPicked = s.name === picked?.screen
        const strip = stripSvg(c.m, s, size.colPx, isPicked ? picked.pose : undefined)
        const dim = !isPicked && isFinished(c.m, s)
        const long = s.name.length > NAME_BUTTON_MAX
        const name = long ? (
          <Text size="footnote" weight={isPicked ? 'semibold' : 'regular'} color={isPicked ? 'suggestion' : undefined} dimColor={dim} wrap="wrap">
            {breakable(s.name)}
          </Text>
        ) : isPicked ? (
          <Button key={`row:${s.name}`} plain label={s.name} onPress={pressRow(s.name)}>
            <Text weight="semibold" color="suggestion">
              {s.name}
            </Text>
          </Button>
        ) : (
          <Button key={`row:${s.name}`} plain dimColor={dim} label={s.name} onPress={pressRow(s.name)} />
        )
        const view = long && <Button key={`row:${s.name}`} plain dimColor={dim} label="View" onPress={pressRow(s.name)} />
        const cells = <Svg source={strip.source} width={stripW} height={strip.height} alt={rowAlt(c, s)} />
        return size.stacked ? (
          <Box flexDirection="column" alignItems="flex-start">
            <Box flexDirection="row" flexWrap="wrap" alignItems="center" columnGap={1}>
              {name}
              {view}
            </Box>
            {cells}
          </Box>
        ) : (
          <Box flexDirection="row" alignItems="center">
            <Box width={size.nameCols} flexShrink={0} flexDirection="row" flexWrap="wrap" alignItems="center" columnGap={1}>
              {name}
              {view}
            </Box>
            {cells}
          </Box>
        )
      })}
    </Box>
  )
}

// The whole items from `start` that fit `budget` characters (one at least), and where the page before them starts.
function page(lines: string[], start: number, budget: number, cost: (line: string) => number = line => line.length) {
  const from = clamp(start, 0, Math.max(0, lines.length - 1))
  let end = from
  for (let spent = 0; end < lines.length && (end === from || spent + cost(lines[end]!) <= budget); end++) spent += cost(lines[end]!)
  let back = from
  for (let spent = 0; back > 0 && (back === from || spent + cost(lines[back - 1]!) <= budget); back--) spent += cost(lines[back - 1]!)
  return { from, end, back, paged: from > 0 || end < lines.length }
}

// A list drawn a page at a time: where it stands, and the buttons to the page before and after.
function pager(k: Kit, name: string, view: ReturnType<typeof page>, n: number, go: (start: number) => void) {
  const { Box, Text, Button } = k
  return (
    <Box key={`${name}-pager`} flexDirection="row" flexWrap="wrap" alignItems="center" columnGap="xs">
      <Text size="footnote" dimColor>
        {`Items ${view.from + 1} to ${view.end} of ${n}`}
      </Text>
      {view.from > 0 && <Button key={`${name}-back`} plain dimColor label="‹ Previous items" onPress={() => go(view.back)} />}
      {view.end < n && <Button key={`${name}-more`} plain dimColor label="More items ›" onPress={() => go(view.end)} />}
    </Box>
  )
}

// What is left, each item in full with a button to each screen it names, as many as fit `budget` characters; the rest
// a page at a time.
function leftList($: EngineInterface, k: Kit, c: Ctx, budget: number) {
  const { Box, Text, Button } = k
  const cost = (line: string) => line.length + namedScreens(c.m, line).join('').length + 12
  const view = page(c.left, c.leftFrom, budget, cost)
  return (
    <Box key="left" flexDirection="column" gap="sm">
      <Text weight="semibold">
        {c.m.phase === 'done' ? 'Left for you' : 'Left'} ({c.left.length})
      </Text>
      {c.left.length === 0 && (
        <Text size="footnote" dimColor>
          Nothing
        </Text>
      )}
      {c.left.slice(view.from, view.end).map((line, j) => {
        const i = view.from + j
        const names = namedScreens(c.m, line)
        const longOnes = names.filter(name => name.length > NAME_BUTTON_MAX).length
        return (
          <Box flexDirection="column">
            <Text size="footnote" wrap="wrap">
              ○ {soft(line)}
            </Text>
            {names.length > 0 && (
              <Box flexDirection="row" flexWrap="wrap" alignItems="center" columnGap={1}>
                <Text size="footnote" dimColor>
                  Show:
                </Text>
                {names.map(name => {
                  const press = () => void showScreen($, name, false, 'start')
                  if (name.length <= NAME_BUTTON_MAX) return <Button key={`todo:${i}:${name}`} plain label={name} onPress={press} />
                  // The item names it already; with two long names each is shown beside its button.
                  return longOnes === 1 ? <Button key={`todo:${i}:${name}`} plain label="View" onPress={press} /> : named(k, `todo:${i}:${name}`, 'View', name, press, false)
                })}
              </Box>
            )}
          </Box>
        )
      })}
      {view.paged && pager(k, 'left', view, c.left.length, start => void update($, leftStart, () => start))}
    </Box>
  )
}

// What is done, dim: in full while it fits `budget` characters, else behind Show done; once shown, as many items as
// fit, the rest a page at a time.
function doneList($: EngineInterface, k: Kit, c: Ctx, budget: number) {
  const { Box, Text, Button } = k
  const n = c.done.length
  const cost = (line: string) => line.length + 2
  const folded = !c.doneOpen && c.done.reduce((sum, line) => sum + cost(line), 0) > budget
  const view = page(c.done, c.doneFrom, budget, cost)
  const hide = async () => {
    await update($, doneShown, () => false)
    await update($, doneStart, () => 0)
  }
  return (
    <Box key="done" flexDirection="column" gap="xs">
      <Text weight="semibold">Done ({n})</Text>
      {n === 0 && (
        <Text size="footnote" dimColor>
          Nothing yet
        </Text>
      )}
      {folded ? (
        <Box flexDirection="row">
          <Button key="done-toggle" plain dimColor label={`Show done (${n})`} onPress={() => void update($, doneShown, () => true)} />
        </Box>
      ) : (
        c.done.slice(view.from, view.end).map(line => (
          <Text size="footnote" dimColor wrap="wrap">
            ✓ {soft(line)}
          </Text>
        ))
      )}
      {!folded && view.paged && pager(k, 'done', view, n, start => void update($, doneStart, () => start))}
      {!folded && c.doneOpen && (
        <Box flexDirection="row">
          <Button key="done-toggle" plain dimColor label="Hide done" onPress={() => void hide()} />
        </Box>
      )}
    </Box>
  )
}

function simulator($: EngineInterface, k: Kit, c: Ctx, room: number) {
  const { Box, Text, Button, Svg, Image } = k
  if (c.from !== 'file') return null
  if (c.m.screens.length > LIVE_MAX_SCREENS)
    return (
      <Box key="simulator" flexDirection="column" gap="xs">
        <Text weight="semibold">Simulator</Text>
        <Text size="footnote" dimColor wrap="wrap">
          {`Live view off for migrations of more than ${LIVE_MAX_SCREENS} screens`}
        </Text>
      </Box>
    )
  const frame = c.frame
  const showFrame = !c.isPaused && frame
  let drawn: RenderElement | null = null
  if (showFrame && c.g.graphical) {
    const aspect = frame.width / frame.height
    const w = Math.round(aspect >= 1 ? Math.min(room, 420) : Math.min(room, 300 * aspect))
    const svgFrame = shotSvg(frame, w, Math.round(w / aspect), undefined, 'live')
    drawn = <Svg source={svgFrame.source} width={svgFrame.width} height={svgFrame.height} alt="The iPhone Duo simulator, as it is now" />
  } else if (showFrame) {
    const aspect = frame.width / frame.height
    const columns = Math.min(60, c.g.cols - 2)
    drawn = <Image source={{ file: frame.file, format: 'png', generation: liveFrame }} columns={columns} rows={clamp(Math.round(columns / aspect / 2), 4, 60)} alt={panelOf(frame.file)} />
  }
  return (
    <Box key="simulator" flexDirection="column" gap="xs">
      <Box flexDirection="row" alignItems="center" columnGap={1}>
        <Text weight="semibold">Simulator</Text>
        <Text size="footnote" dimColor>
          {c.isPaused ? 'paused' : c.frameNote ?? (frame ? panelOf(frame.file) : 'waiting for a frame')}
        </Text>
        <Button key="live" plain dimColor label={c.isPaused ? 'Resume' : 'Pause'} onPress={() => void update($, paused, value => !value)} />
      </Box>
      {drawn}
    </Box>
  )
}

// The activity, newest first, whole lines: five at first, more on request while they fit the text left in the tree,
// then a page at a time.
function activity($: EngineInterface, k: Kit, c: Ctx, budget: number) {
  const { Box, Text, Button } = k
  const all = c.m.log ?? []
  if (all.length === 0) return null
  const newest = [...all].reverse()
  const start = clamp(c.log.start, 0, Math.max(0, newest.length - 1))
  const want = newest.slice(start, start + Math.max(1, c.log.count))
  const lines: string[] = []
  let spent = 0
  for (const line of want) {
    if (lines.length > 0 && spent + line.length > budget) break
    lines.push(line)
    spent += line.length
  }
  const cut = lines.length < want.length
  const end = start + lines.length
  const paged = start > 0 || cut
  const expanded = c.log.count > LOG_DEFAULT || start > 0
  const caption = expanded ? `Entries ${start + 1} to ${end} of ${newest.length}, newest first` : `${lines.length} of ${newest.length}, newest first`
  const setView = (next: LogView) => () => void update($, logView, () => next)
  return (
    <Box key="activity" flexDirection="column" gap="xs">
      <Box flexDirection="row" flexWrap="wrap" alignItems="center" columnGap={1}>
        <Text weight="semibold">Activity</Text>
        <Text size="footnote" dimColor>
          {caption}
        </Text>
      </Box>
      {lines.map(line => {
        const parts = /^(\d{1,2}:\d{2})\s+([\s\S]*)$/.exec(line)
        return (
          <Box flexDirection="row" columnGap={1}>
            <Box width={6} flexShrink={0}>
              <Text size="footnote" dimColor tabular>
                {parts?.[1] ?? ''}
              </Text>
            </Box>
            <Box flexDirection="column" flexGrow={1} flexShrink={1}>
              <Text size="footnote" dimColor wrap="wrap">
                {soft(parts?.[2] ?? line)}
              </Text>
            </Box>
          </Box>
        )
      })}
      {(end < newest.length || expanded) && (
        <Box key="log-pager" flexDirection="row" flexWrap="wrap" columnGap="xs">
          {!paged && end < newest.length && <Button key="log" plain dimColor label="Show 50 more" onPress={setView({ start, count: c.log.count + LOG_PAGE })} />}
          {paged && start > 0 && (
            <Button key="log-newer" plain dimColor label="‹ Newer" onPress={setView({ start: Math.max(0, start - Math.max(lines.length, LOG_DEFAULT)), count: c.log.count })} />
          )}
          {paged && end < newest.length && <Button key="log-older" plain dimColor label="Older ›" onPress={setView({ start: end, count: c.log.count })} />}
          {expanded && <Button key="log-less" plain dimColor label="Show fewer" onPress={setView({ start: 0, count: LOG_DEFAULT })} />}
        </Box>
      )}
    </Box>
  )
}

// The app picker: app names (with the folder's name where two apps share one), as a Select while every label fits
// it, else as a list of buttons with each folder beside.
function appSwitcher($: EngineInterface, k: Kit, c: Ctx) {
  const { Box, Text, Select } = k
  if (c.g.mobile || !c.g.graphical || c.from !== 'file' || c.found.length < 2 || !c.found.some(f => f.root === c.base)) return null
  const labels = c.found.map(f =>
    c.found.filter(other => other.app === f.app).length > 1 ? `${f.app} (${f.root.split('/').pop() ?? f.root})` : f.app,
  )
  if (c.found.length <= SELECT_MAX && labels.every(label => label.length <= SELECT_LABEL))
    return (
      <Select
        key="app"
        label="App"
        options={c.found.map((f, i) => ({ value: f.root, label: labels[i] }))}
        value={c.base}
        onSelect={(value: string) => void follow($, value)}
      />
    )
  return (
    <Box key="apps" flexDirection="column" gap="xs">
      <Text weight="semibold">App</Text>
      {c.found.map(f => (
        <Box flexDirection="row" flexWrap="wrap" alignItems="center" columnGap={1}>
          {named(k, `app:${f.root}`, '', f.app, () => void follow($, f.root), f.root !== c.base)}
          <Text size="footnote" dimColor wrap="wrap">
            {slashes(shown(f.root))}
          </Text>
        </Box>
      ))}
    </Box>
  )
}

// The enlarged view, in place of the dashboard: one shot across the pane (fitted to the pane's height, or filling its
// width), or both, from sharp strips once they are cut on the desktop and in VS Code, and the dashboard's copy until
// then (and on the phone, where that copy is already sharp at its size). In a terminal, the capture itself.
function zoomView($: EngineInterface, k: Kit, c: Ctx, view: Zoom, fit: boolean) {
  const { Box, Text, Button, Svg, Image } = k
  if (!c.chosen) return null
  const chosen = c.chosen
  const m = c.m
  // The phone shows one shot at a time.
  const side = c.g.mobile && view.side === 'both' ? 'after' : view.side
  const both = side === 'both'
  const sides: Side[] = side === 'both' ? ['before', 'after'] : [side]
  const sharp = view.sharp && c.g.pointer
  // The strips cut from a shot as it is now, or why there are none; undefined while they are being cut.
  const cutOf = (s: Side): Cut | undefined => {
    const shot = c.shots[s]
    const got = sharp && shot.file ? tiles.get(tileId(shot.file, both)) : undefined
    return got && got.at === shot.at ? got.cut : undefined
  }
  const aspectOf = (s: Side) => {
    const cut = cutOf(s)
    const pic = c.shots[s].pic
    return typeof cut === 'object' ? cut.w / cut.tall : pic ? pic.width / pic.height : c.aspect
  }
  const lead = sides.find(s => c.shots[s].file) ?? sides[0]!
  const { w, row } = zoomWidth(c.g, aspectOf(lead), both, fit)
  const across = c.g.graphical ? row : both && aspectOf(lead) < 1
  const room = c.g.px
  const mode = (key: string, hotkey: string, label: string, target: ZoomSide) => (
    <Button key={key} hotkey={hotkey} variant={side === target ? 'primary' : undefined} label={label} onPress={() => void enterZoom($, target, c.g.pointer)} />
  )
  // Fit or fill, where the two draw the shots differently (on the desktop and in VS Code).
  const flip = zoomWidth(c.g, aspectOf(lead), both, !fit)
  const canFit = c.g.pointer && (flip.w !== w || flip.row !== row)
  const fitToggle = canFit && (
    <Button key="zoom-fit" hotkey="f" plain dimColor label={fit ? 'Fill width' : 'Fit to pane'} onPress={() => void update($, zoomFit, value => !value)} />
  )
  const picture = (s: Side, first: boolean) => {
    const shot = c.shots[s]
    const cut = cutOf(s)
    const set = typeof cut === 'object' ? cut : undefined
    const own = aspectOf(s)
    const sw = Math.min(w, Math.floor(SVG_MAX * Math.min(1, own)))
    const total = Math.min(SVG_MAX, Math.round(sw / own))
    const label = `${chosen.screen} in ${poseLabel(chosen.pose)}, ${s}`
    let drawings: RenderElement[] = []
    if (!c.g.graphical) {
      const most = clamp(across ? Math.floor((c.g.cols - 4) / 2) : c.g.cols - 2, 10, 255)
      const rows = clamp(Math.round(most / own / 2), 4, 255)
      const columns = Math.min(most, Math.max(4, Math.round(rows * 2 * own)))
      drawings = [
        shot.file ? (
          <Image source={{ file: shot.file, format: 'png', generation: shot.at }} columns={columns} rows={rows} alt={label} />
        ) : (
          <Text dimColor wrap="wrap">
            {shot.path ? 'Not found in the app folder' : 'Not captured yet'}
          </Text>
        ),
      ]
    } else if (set) {
      drawings = set.tiles.map((t, i) => {
        const top = Math.round((total * t.y) / set.tall)
        const bottom = i === set.tiles.length - 1 ? total : Math.round((total * (t.y + t.tall)) / set.tall)
        const drawing = tileSvg(t.jpeg, sw, bottom - top, top, total, i, set.tiles.length, c.fold, own >= 1, `z-${s}-${i}`)
        return <Svg source={drawing.source} width={drawing.width} height={drawing.height} alt={set.tiles.length > 1 ? `${label} (part ${i + 1} of ${set.tiles.length})` : label} />
      })
    } else if (shot.pic) {
      const drawing = shotSvg(shot.pic, sw, total, c.fold, `z-${s}`)
      drawings = [<Svg source={drawing.source} width={drawing.width} height={drawing.height} alt={label} />]
    } else {
      const drawing = emptySvg(sw, Math.min(total, 160), !shot.path ? 'Not captured yet' : !shot.file ? 'Not found in the app folder' : 'Loading')
      drawings = [<Svg source={drawing.source} width={drawing.width} height={drawing.height} alt={label} />]
    }
    // Where the picture comes from, on the desktop and in VS Code.
    const source = !c.g.pointer || !shot.file
      ? null
      : set
        ? `· ${set.nativeW} × ${set.nativeH} capture`
        : !view.sharp
          ? '· drawn from the dashboard copy'
          : cut === undefined
            ? '· Sharpening'
            : cut === 'detail'
              ? '· too detailed to sharpen'
              : '· drawn from the dashboard copy'
    return (
      <Box key={`zoom-${s}`} flexDirection="column" gap="xs">
        <Box flexDirection="row" flexWrap="wrap" alignItems="center" columnGap={1}>
          <Text size="footnote" weight="semibold">
            {s === 'before' ? 'Before' : 'After'}
          </Text>
          {source && (
            <Text size="footnote" dimColor>
              {source}
            </Text>
          )}
          {c.g.pointer && c.from === 'file' && shot.file && (
            <Button key={`open-${s}`} plain dimColor label="Open in Preview" onPress={() => void openShot($, shot.path!)} />
          )}
          {first && fitToggle}
        </Box>
        <Box flexDirection="column" gap={0}>
          {drawings}
        </Box>
      </Box>
    )
  }
  const pictures = (
    <Box key="zoom-shots" flexDirection="column" gap="sm">
      <Box key="zoom-pair" flexDirection={across ? 'row' : 'column'} columnGap={2} rowGap="md" alignItems="flex-start">
        {sides.map((s, i) => picture(s, i === 0))}
      </Box>
      {c.g.graphical && (
        <Text size="caption" dimColor wrap="wrap">
          {FOLD_NOTE[c.fold ?? 'none']}
        </Text>
      )}
    </Box>
  )
  return (
    <Box key="zoom-view" flexDirection="column" gap="lg">
      <Box key="zoom-head" flexDirection="column" gap="sm">
        <Box key="zoom-bar" flexDirection="row" flexWrap="wrap" alignItems="center" columnGap={1} rowGap="xs">
          <Button key="zoom-close" hotkey="z" label="‹ Dashboard" onPress={() => void leaveZoom($)} />
          {stageTitle(k, c)}
        </Box>
        <Box key="zoom-modes" flexDirection="row" flexWrap="wrap" alignItems="center" columnGap={3} rowGap="xs">
          <Box flexDirection="row" flexWrap="wrap" alignItems="center" columnGap="xs" rowGap="xs">
            {mode('view-before', 'b', 'Before', 'before')}
            {mode('view-after', 'a', 'After', 'after')}
            {!c.g.mobile && mode('view-both', 'c', 'Both', 'both')}
          </Box>
          <Box key="zoom-nav" flexDirection="row" flexWrap="wrap" alignItems="center" columnGap="xs" rowGap="xs">
            <Button key="prev" hotkey="p" label="‹ Previous" onPress={() => void choosePick($, step(m, chosen, -1))} />
            <Button key="next" hotkey="n" label="Next ›" onPress={() => void choosePick($, step(m, chosen, 1))} />
            {c.tally.finding > 0 && <Button key="next-defect" hotkey="d" label="Next defect" onPress={() => void choosePick($, step(m, chosen, 1, true))} />}
            <Button key="screen-prev" hotkey="k" plain label="‹ Screen" onPress={() => void choosePick($, stepScreen(m, chosen, -1))} />
            <Button key="screen-next" hotkey="j" plain label="Screen ›" onPress={() => void choosePick($, stepScreen(m, chosen, 1))} />
          </Box>
        </Box>
        {poseStrip($, k, c)}
        {keysLine(k, c, true, canFit)}
      </Box>
      {c.g.graphical && !both && room - w - 3 * c.g.pxc >= 240 ? (
        <Box key="zoom-body" flexDirection="row" columnGap={3} alignItems="flex-start">
          {pictures}
          <Box flexDirection="column" gap="md" flexShrink={1} width={Math.floor((room - w) / c.g.pxc) - 3}>
            {meta(k, c)}
            {why(k, c)}
          </Box>
        </Box>
      ) : (
        [pictures, meta(k, c), why(k, c, Math.min(c.g.cols - 1, 112))]
      )}
      <Box flexDirection="row">
        <Button key="zoom-close-end" label="‹ Dashboard" onPress={() => void leaveZoom($)} />
      </Box>
    </Box>
  )
}

// The terminal's stage: the pictures as images where the terminal draws them, each keeping the shot's shape.
function terminalPair(k: Kit, c: Ctx) {
  const { Box, Text, Image } = k
  if (!c.chosen) return null
  const most = clamp(Math.floor((c.g.cols - 4) / 2), 10, 120)
  const rows = clamp(Math.round(most / c.aspect / 2), 5, 60)
  const columns = Math.min(most, Math.max(4, Math.round(rows * 2 * c.aspect)))
  const label = `${c.chosen.screen} in ${poseLabel(c.chosen.pose)}`
  const picture = (side: Side) => {
    const s = c.shots[side]
    const title = side === 'before' ? 'Before' : 'After'
    return s.file ? (
      <Image source={{ file: s.file, format: 'png', generation: s.at }} columns={columns} rows={rows} alt={`${title}: ${label} (${s.path})`} />
    ) : (
      <Text dimColor wrap="wrap">
        {title}: {s.path ? 'not found in the app folder' : 'not captured yet'}
      </Text>
    )
  }
  return (
    <Box key="pair" flexDirection="row" flexWrap="wrap" columnGap={2}>
      {picture('before')}
      {picture('after')}
    </Box>
  )
}

// The terminal's matrix, as text: a column per pose, the picked cell in brackets. When a name and its row would not
// fit the pane, every name stands on its own line and the cells sit under it.
function terminalMatrix(k: Kit, c: Ctx) {
  const { Box, Text } = k
  const n = c.poses.length
  const longest = Math.max(0, ...c.m.screens.map(s => s.name.length))
  const cellW = 2 + 6 * n <= c.g.cols - 1 ? 6 : 5
  const nameW = Math.min(longest, 28) + 2
  const ownLine = nameW + cellW * n > c.g.cols - 1
  const indent = ownLine ? 2 : nameW
  const pad = (text: string, width: number) => text.padEnd(width)
  const cells = (s: Screen) =>
    c.poses
      .map(p => {
        const glyph = GLYPH[cellOf(s.cells, p).state]
        return pad(s.name === c.chosen?.screen && p === c.chosen.pose ? `[${glyph}]` : ` ${glyph} `, cellW)
      })
      .join('')
  return (
    <Box key="matrix" flexDirection="column">
      <Text dimColor>{pad('', indent) + c.poses.map(p => pad(POSE_SHORT[p] ?? p, cellW)).join('')}</Text>
      {c.m.screens.map(s =>
        !ownLine && s.name.length <= 28 ? (
          <Text>{pad(s.name, nameW) + cells(s)}</Text>
        ) : (
          <Box flexDirection="column">
            <Text wrap="wrap">{s.name}</Text>
            <Text>{pad('', indent) + cells(s)}</Text>
          </Box>
        ),
      )}
    </Box>
  )
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    cwd = e.cwd
    await $.command.register({
      name: 'foldsmith',
      description:
        'The Foldsmith pane: `/foldsmith` shows it, `/foldsmith watch <folder>` follows another app (`/foldsmith watch` alone ' +
        'follows the newest), `/foldsmith demo` shows sample data, `/foldsmith off` leaves it. `/foldsmith-start` runs the migration.',
    })
    home = (await $.process.run(['/usr/bin/printenv', 'HOME'])).stdout.trim()
    scratch = home ? `${home}/Library/Caches/foldsmith` : ''
    if (scratch) await $.process.run(['/bin/mkdir', '-p', scratch])
    // The timers first, so nothing that fails below can leave the pane without them.
    $.clock.every(1500, () => poll($))
    $.clock.every(LIVE_EVERY_MS, () => liveTick($))
    $.clock.every(LOOK_EVERY_MS, () => choose($))
    await choose($)
    await poll($)

    return next(e)
  })

  on('command.run', { command: 'foldsmith' }, async ($, e) => {
    const [word = '', ...rest] = e.args.trim().split(/\s+/)
    const arg = word.toLowerCase()
    let text = 'Foldsmith pane opened.'
    if (arg === 'demo') {
      await showDemo($)
      text = 'Foldsmith pane: showing sample data.'
    } else if (arg === 'off') {
      await update($, source, () => 'none')
      await switchTo($, await read($, root))
      text = 'Foldsmith pane: back to the progress file.'
    } else if (arg === 'watch') {
      const path = rest.join(' ').replace(/\/+$/, '')
      const full = path ? resolveFolder(path) : null
      await follow($, full)
      text = full ? `Foldsmith pane: following ${shown(full)}.` : 'Foldsmith pane: following the newest migration.'
    } else {
      // Opens the pane even when the look for progress files fails.
      await choose($).catch(() => undefined)
    }
    await $.ui.open({ id: PANE, title: TITLE })

    return { text }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const m = await read($, migration)
    const from = await read($, source)
    const problem = await read($, error)
    const base = await folder($)
    const found = await read($, known)
    const k = $.ui.resolve(e) as unknown as Kit
    const { Box, Text, Button } = k
    const g = geometry(e.surface, e.props.bodyColumns, e.props.scroll?.bodyRows ?? 40)
    const start = base === cwd ? '/foldsmith-start' : `/foldsmith-start ${base}`
    const errorLine = problem && (
      <Text color="error" wrap="wrap">
        {problem}
      </Text>
    )

    if (!m) {
      return (
        <Box flexDirection="column" gap="md">
          <Text weight="semibold" wrap="wrap">
            No migration in {slashes(shown(base))}
          </Text>
          <Text dimColor wrap="wrap">
            /foldsmith-start adapts every screen of the app hands-free and writes {STATUS_FILE} as it goes; this pane follows
            that file: the simulator, every screen in every pose, before and after, and what is done and left.
          </Text>
          <Box flexDirection="row" columnGap={1} rowGap="xs" flexWrap="wrap">
            <Button key="start" variant="primary" label="Start migration" onPress={() => void $.prompt.fill({ text: start })} />
            <Button key="demo" label="Show sample data" onPress={() => void showDemo($)} />
          </Box>
          {found.length > 0 && (
            <Box flexDirection="column" gap="xs">
              <Text size="footnote" weight="semibold">
                Migrations found
              </Text>
              {found.map(f => (
                <Box flexDirection="row" flexWrap="wrap" alignItems="center" columnGap={1}>
                  {named(k, `follow:${f.root}`, '', f.app, () => void follow($, f.root), false)}
                  <Text size="footnote" dimColor wrap="wrap">
                    {slashes(shown(f.root))}
                  </Text>
                </Box>
              ))}
            </Box>
          )}
          {errorLine}
        </Box>
      )
    }

    const shotsByFile = await read($, pictures)
    const chosen = (await read($, pick)) ?? defaultPick(m)
    const screen = screenOf(m, chosen?.screen)
    const cell = chosen && screen ? cellOf(screen.cells, chosen.pose) : undefined
    const shotOf = async (path: string | undefined): Promise<Shot> => {
      const file = path ? await absolute($, path) : ''
      const at = file ? ((await $.fs.stat(file).catch(() => null))?.mtimeMs ?? 0) : 0
      return { path, file, at, pic: file ? shotsByFile[file] : undefined }
    }
    const shots = { before: await shotOf(cell?.before), after: await shotOf(cell?.after) }
    const drawn = shots.before.pic ?? shots.after.pic
    const pose = (chosen?.pose ?? 'book') as PoseId
    const { done, left } = progress(m)
    const tally = counts(m)
    const info = await read($, folderInfo)
    const c: Ctx = {
      m,
      from,
      base,
      g,
      poses: posesOf(m),
      tally,
      total: m.screens.length * posesOf(m).length,
      finished: m.screens.filter(s => isFinished(m, s)).length,
      left,
      done,
      status: statusOf(m, from, left.length),
      chosen,
      screen,
      cell,
      codes: cell ? codesOf(cell) : [],
      shots,
      aspect: drawn ? drawn.width / drawn.height : ASPECT[pose] ?? 1,
      fold: FOLD[pose],
      info,
      frame: await read($, live),
      frameNote: await read($, liveNote),
      isPaused: await read($, paused),
      found,
      start,
      // The sample's status already says what it is.
      where: from === 'demo' ? '' : [slashes(shown(base)), info.branch && `branch ${info.branch}`].filter(Boolean).join(' · '),
      log: await read($, logView),
      doneOpen: await read($, doneShown),
      doneFrom: await read($, doneStart),
      leftFrom: await read($, leftStart),
      fit: await read($, zoomFit),
    }
    const view = await read($, zoom)
    await read($, zoomRev)

    if (view && chosen && screen) {
      return (
        <Box flexDirection="column" gap="md">
          {errorLine}
          {zoomView($, k, c, view, c.fit)}
        </Box>
      )
    }

    // The text a tree holds, spent in order: everything but the lists, then what is left (a page at a time when it
    // would not fit), what is done (behind a button, or a page at a time), and the activity with the rest.
    const spend = (parts: unknown[]) => parts.reduce((n: number, part) => n + drawnText(part), 0)
    const lists = (used: number) => {
      const leftEl = leftList($, k, c, Math.max(2000, TEXT_BUDGET - used - 4000))
      const usedLeft = used + drawnText(leftEl)
      const doneEl = doneList($, k, c, TEXT_BUDGET - usedLeft - 3000)
      return { leftEl, doneEl, usedLists: usedLeft + drawnText(doneEl) }
    }

    if (!g.graphical) {
      const summary = (
        <Text size="footnote" wrap="wrap">
          {c.finished} of {m.screens.length} screens finished · {tally.verified + tally.unchanged} of {c.total} poses good
          {tally.finding > 0 ? ` · ${tally.finding} with defects` : ''}
        </Text>
      )
      const zoomRow = chosen && (shots.before.file || shots.after.file) && (
        <Box key="zoom-row" flexDirection="row" flexWrap="wrap" columnGap={1}>
          {shots.before.file && <Button key="zoom-before" plain hotkey="b" label="Enlarge before" onPress={() => void enterZoom($, 'before', false)} />}
          {shots.after.file && <Button key="zoom-after" plain hotkey="a" label="Enlarge after" onPress={() => void enterZoom($, 'after', false)} />}
          {shots.before.file && shots.after.file && <Button key="zoom" plain hotkey="c" label="Compare full size" onPress={() => void enterZoom($, 'both', false)} />}
        </Box>
      )
      const actions = from === 'file' && (
        <Box flexDirection="row" columnGap={1} flexWrap="wrap">
          {(m.phase !== 'done' || left.length > 0) && (
            <Button key="resume" variant="primary" label={m.phase === 'done' ? 'Resume migration' : 'Restart if stopped'} onPress={() => void $.prompt.fill({ text: start })} />
          )}
          {info.report && <Button key="report" label="Open report" onPress={() => void openDuo($, base, 'REPORT.md')} />}
          <Button key="captures" label="Show captures" onPress={() => void openDuo($, base, 'captures')} />
        </Box>
      )
      const fixed = [
        <Text weight="semibold" wrap="wrap">
          {m.app ?? 'iPhone Duo migration'} <Text color={c.status.color}>{c.status.text}</Text>
        </Text>,
        errorLine,
        stepper(k, c),
        summary,
        <Text dimColor size="footnote" wrap="wrap">
          {LEGEND.map(item => `${GLYPH[item.state]} ${item.label}`).join('   ')}
        </Text>,
        simulator($, k, c, g.px),
        terminalMatrix(k, c),
        <Box key="stage" flexDirection="column">
          {stageTitle(k, c)}
          {meta(k, c)}
        </Box>,
        poseStrip($, k, c),
        nav($, k, c),
        zoomRow,
        terminalPair(k, c),
        why(k, c),
      ]
      const { leftEl, doneEl, usedLists } = lists(spend([...fixed, actions]))
      return (
        <Box flexDirection="column" gap={1}>
          {fixed}
          {leftEl}
          {doneEl}
          {activity($, k, c, TEXT_BUDGET - usedLists)}
          {actions}
        </Box>
      )
    }

    // Graphical surfaces. Below WIDE_COLS: the header and figures, then the stage (the picked cell, its shots large),
    // the matrix, and what is left and done (in two columns from 120 cells). From WIDE_COLS the matrix moves beside the
    // stage, where the shots keep the size a narrower pane gives them: a landscape pair spans the pane below a band of
    // the figures, the cell and the matrix; a portrait pair sits in the stage's column, the matrix and the notes beside.
    const top = headerTop($, k, c)
    const steps = stepper(k, c)
    const twoLists = g.cols >= 120
    const halfCols = Math.floor((g.cols - 4) / 2)
    const listCols = twoLists ? halfCols : g.cols - 1
    const measure = Math.min(g.cols - 1, 112)
    const keys = keysLine(k, c, false)
    const sim = simulator($, k, c, Math.floor(listCols * g.pxc))
    const app = appSwitcher($, k, c)
    // The stage in three groups: what the cell is, the controls that move through the cells, and the shots.
    const cellHead = (withMeta: boolean) => (
      <Box key="cell-head" flexDirection="column" gap="xs">
        {stageTitle(k, c)}
        {withMeta && meta(k, c)}
      </Box>
    )
    const controls = (
      <Box key="controls" flexDirection="column" gap="xs">
        {poseStrip($, k, c)}
        {nav($, k, c)}
        {keys}
      </Box>
    )
    const dash = pairSize(g.px, c.aspect, g.capH)
    const pairPx = dash.sideBySide ? 2 * dash.w + GAP_PX : dash.w
    const lower = (leftEl: RenderElement, doneEl: RenderElement, log: RenderElement | null) => (
      <Box key="lower" flexDirection="row" columnGap={4} alignItems="flex-start">
        <Box flexDirection="column" gap="lg" flexGrow={1} flexShrink={1} width={halfCols}>
          {leftEl}
        </Box>
        <Box flexDirection="column" gap="lg" flexGrow={1} flexShrink={1} width={halfCols}>
          {sim}
          {log}
          {doneEl}
          {app}
        </Box>
      </Box>
    )
    let fixed: unknown[]
    let body: (leftEl: RenderElement, doneEl: RenderElement, log: RenderElement | null) => RenderElement
    // The portrait layout's columns: the stage as wide as the pair at full size, the matrix in the rest.
    const stageCols = Math.ceil(pairPx / g.pxc) + 1
    const sideCols = g.cols - 1 - 3 - stageCols
    const sideSize = matrixSize(c, sideCols * g.pxc, false)
    const split = g.wide && g.px - pairPx - 3 * g.pxc >= 280 && !sideSize.stacked && sideSize.colPx >= 40
    if (split) {
      const pair = pairBlock($, k, c, stageCols * g.pxc)
      const head = (
        <Box key="head" flexDirection="column">
          {overview($, k, c, g.cols - 1)}
        </Box>
      )
      const band = (
        <Box key="band" flexDirection="row" columnGap={3} alignItems="flex-start">
          <Box key="stage" flexDirection="column" gap="lg" flexShrink={0} width={stageCols}>
            {cellHead(true)}
            {controls}
            {pair}
          </Box>
          <Box key="navigator" flexDirection="column" gap="xl" flexShrink={1} width={sideCols}>
            {matrix($, k, c, sideCols * g.pxc, false)}
            {why(k, c, sideCols)}
          </Box>
        </Box>
      )
      fixed = [top, steps, head, band, sim, app]
      body = (leftEl, doneEl, log) => (
        <Box key="columns" flexDirection="column" gap="xl">
          {head}
          {band}
          {lower(leftEl, doneEl, log)}
        </Box>
      )
    } else if (g.wide) {
      const size = matrixSize(c, g.px, true)
      const leftCols = g.cols - 1 - size.navCols - 3
      const pair = pairBlock($, k, c, g.px)
      const band = (
        <Box key="band" flexDirection="row" columnGap={3} alignItems="flex-start">
          <Box key="band-left" flexDirection="column" gap="xl" flexGrow={1} flexShrink={1} width={leftCols}>
            {overview($, k, c, leftCols)}
            <Box key="stage" flexDirection="column" gap="lg">
              {cellHead(true)}
              {controls}
              {why(k, c, Math.min(leftCols, 112))}
            </Box>
          </Box>
          <Box key="navigator" flexDirection="column" flexShrink={0} width={size.navCols}>
            {matrix($, k, c, size.navCols * g.pxc, true)}
          </Box>
        </Box>
      )
      fixed = [top, steps, band, pair, sim, app]
      body = (leftEl, doneEl, log) => (
        <Box key="columns" flexDirection="column" gap="xl">
          {band}
          <Box key="pair-row" flexDirection="column">
            {pair}
          </Box>
          {lower(leftEl, doneEl, log)}
        </Box>
      )
    } else {
      const besidePx = dash.sideBySide ? g.px - pairPx - 3 * g.pxc : 0
      const beside = besidePx >= 240
      const pair = pairBlock($, k, c, g.px)
      const head = (
        <Box key="head" flexDirection="column" gap="lg">
          {top}
          {errorLine}
          {steps}
          {overview($, k, c, g.cols - 1)}
        </Box>
      )
      const stage = (
        <Box key="stage" flexDirection="column" gap="lg">
          {cellHead(!beside)}
          {controls}
          {beside ? (
            <Box flexDirection="row" columnGap={3} alignItems="flex-start">
              {pair}
              <Box flexDirection="column" gap="md" flexShrink={1} width={Math.floor(besidePx / g.pxc)}>
                {meta(k, c)}
                {why(k, c)}
              </Box>
            </Box>
          ) : (
            [pair, why(k, c, measure)]
          )}
        </Box>
      )
      const grid = matrix($, k, c, g.px, false)
      fixed = [head, stage, grid, sim, app]
      body = (leftEl, doneEl, log) => (
        <Box key="columns" flexDirection="column" gap="xl">
          {head}
          {stage}
          {twoLists ? (
            [
              <Box key="navigator" flexDirection="column">
                {grid}
              </Box>,
              lower(leftEl, doneEl, log),
            ]
          ) : (
            [
              <Box key="navigator" flexDirection="column" gap="lg">
                {grid}
                {leftEl}
                {doneEl}
              </Box>,
              <Box key="extras" flexDirection="column" gap="lg">
                {sim}
                {log}
                {app}
              </Box>,
            ]
          )}
        </Box>
      )
    }
    const { leftEl, doneEl, usedLists } = lists(spend(fixed))
    const log = activity($, k, c, TEXT_BUDGET - usedLists)
    return (
      <Box flexDirection="column" gap="lg">
        {g.wide && top}
        {g.wide && errorLine}
        {g.wide && steps}
        {body(leftEl, doneEl, log)}
      </Box>
    )
  })
}
