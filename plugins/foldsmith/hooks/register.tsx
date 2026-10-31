import { atom, read, update } from 'claude-code'
import type { Color, EngineInterface, Register } from 'claude-code'

import type { Cell, CellState, Expanded, Folder, Known, Migration, Phase, Pick, Picture, PoseId, Screen, Source } from '../types'

// The skill writes this file at every step; the pane only reads it.
const STATUS_FILE = '.duo/migration.json'
const PANE = 'foldsmith'
const TITLE = 'Foldsmith'
// The SVG namespace, the only URL in this file: a name, not an address the pane contacts.
const SVG_NS = 'http://www.w3.org/2000/svg'
const LIVE_EVERY_MS = 4000
const LOOK_EVERY_MS = 60000
// The width, in CSS pixels, the drawings' type is sized for: wider, the matrix's type grows. NARROW is the least the
// pane lays them out at; a narrower body scales them down.
const WIDE = 440
const NARROW = 320
// A cell of the pane's code font, in CSS pixels, taken a little small so a drawing sized from `bodyColumns` never
// overflows the body. Past TWO_UP the lists and the picked cell sit side by side under the matrix.
const PX_PER_CELL = 7
const MAX_MATRIX = 1000
const TWO_UP = 720
// The tallest a portrait shot is drawn, and the height of the box that stands for a shot not captured yet.
const SHOT_H = 360
const EMPTY_H = 96
// An Svg's markup is capped at 131072 characters; a shot's JPEG stays under this, made smaller if it must.
const MAX_JPEG = 120000

const migration = atom({ plugin: 'foldsmith', key: 'migration' } as const, null as Migration | null)
const source = atom({ plugin: 'foldsmith', key: 'source' } as const, 'none' as Source)
const error = atom({ plugin: 'foldsmith', key: 'error' } as const, null as string | null)
// The app folder the pane follows; null is the session's own folder.
const root = atom({ plugin: 'foldsmith', key: 'root' } as const, null as string | null)
const live = atom({ plugin: 'foldsmith', key: 'live' } as const, null as Picture | null)
const liveNote = atom({ plugin: 'foldsmith', key: 'liveNote' } as const, null as string | null)
const paused = atom({ plugin: 'foldsmith', key: 'paused' } as const, false)
const pick = atom({ plugin: 'foldsmith', key: 'pick' } as const, null as Pick | null)
const pictures = atom({ plugin: 'foldsmith', key: 'pictures' } as const, {} as { [file: string]: Picture })
const known = atom({ plugin: 'foldsmith', key: 'known' } as const, [] as Known[])
const folderInfo = atom({ plugin: 'foldsmith', key: 'folderInfo' } as const, { branch: null, report: false } as Folder)
const expanded = atom({ plugin: 'foldsmith', key: 'expanded' } as const, { notes: false, log: false } as Expanded)

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

// Width over height of a shot in each pose, for the space a shot not taken yet will need.
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

const STATE_TEXT: Record<CellState, string> = {
  pending: '',
  unchanged: '—',
  finding: '✗',
  proposed: '◆',
  migrated: '…',
  verified: '✓',
}

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

const STATE_COLOR: Record<CellState, Color> = {
  pending: 'inactive',
  unchanged: 'subtle',
  finding: 'error',
  proposed: 'suggestion',
  migrated: 'warning',
  verified: 'success',
}

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

const clip = (text: string, max: number) => (text.length > max ? `${text.slice(0, max - 1)}…` : text)

const posesOf = (m: Migration) => (m.poses && m.poses.length > 0 ? m.poses : ALL_POSES)

const cellOf = (cells: { [pose: string]: Cell }, pose: string): Cell => cells[pose] ?? { state: 'pending' }

const screenOf = (m: Migration, name: string | undefined) => m.screens.find(s => s.name === name)

// Every class seen in a cell: the audit's list when it kept one, else the matrix label of a defect.
const codesOf = (cell: Cell) =>
  (cell.finding ?? (cell.state === 'finding' ? cell.label ?? '' : '')).split(/\s+/).filter(code => /^T\d+$/.test(code))

const describe = (code: string) => (CLASS_NAME[code] ? `${code} ${CLASS_NAME[code]}` : code)

// What a matrix cell shows: the defect's class, else the state's glyph; the label itself is in the cell's tooltip.
const cellText = (cell: Cell) =>
  cell.state === 'finding' ? (/^T\d+$/.test(cell.label ?? '') ? cell.label! : codesOf(cell)[0] ?? STATE_TEXT.finding) : STATE_TEXT[cell.state]

const STYLE_FONT = 'text{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text",system-ui,sans-serif}'

const PAD = 12
const ROW_H = 34

function counts(m: Migration) {
  const tally: Record<CellState, number> = { pending: 0, unchanged: 0, finding: 0, proposed: 0, migrated: 0, verified: 0 }
  for (const screen of m.screens) for (const pose of posesOf(m)) tally[cellOf(screen.cells, pose).state] += 1
  return tally
}

// The screen × pose matrix at `width` CSS pixels, the picked cell outlined; each cell's tooltip says what it holds.
// Its type grows with the width past WIDE, up to 1.35 times, and shrinks in proportion below it, as a drawing scaled
// down would; its columns follow the type. Rows never grow, so an app with many screens still leaves room below.
function matrixSvg(m: Migration, chosen: Pick | null, width = WIDE): { source: string; width: number; height: number } {
  const poses = posesOf(m)
  const inner = width - PAD * 2
  const fs = width < WIDE ? width / WIDE : Math.min(1.35, 1 + (width - WIDE) / 1000)
  const px = (n: number) => Math.round(n * fs * 10) / 10
  const col = Math.min(96, Math.floor((inner - Math.round(84 * fs)) / poses.length))
  const nameW = inner - col * poses.length
  const rowH = Math.round(ROW_H * Math.min(fs, 1))
  const scale = Math.min(1.15, fs, (col - 6) / 36)
  const lineH = Math.round(11 * fs)
  const labelY = Math.round(36 * scale) + Math.round(14 * fs)
  const headH = labelY + lineH + Math.round(5 * fs)
  const tally = counts(m)

  const head = poses
    .map((pose, i) => {
      const x = nameW + i * col
      const lines = poseLabel(pose).split(' ')
      return (
        `<g class="icon" transform="translate(${x + col / 2 - 18 * scale} 2) scale(${scale})">${POSE_ICON[pose] ?? ''}</g>` +
        lines
          .map(
            (line, l) =>
              `<text class="pose" x="${x + col / 2}" y="${labelY + l * lineH}" text-anchor="middle">${escapeXml(line)}</text>`,
          )
          .join('')
      )
    })
    .join('')

  let picked = ''
  const rows = m.screens
    .map((screen, r) => {
      const y = headH + r * rowH
      const baseline = y + rowH / 2 + px(4)
      const name = `<text class="name" x="0" y="${baseline}">${escapeXml(clip(screen.name, Math.floor(nameW / (6.6 * fs))))}</text>`
      const cells = poses
        .map((pose, i) => {
          const cell = cellOf(screen.cells, pose)
          const x = nameW + i * col
          const text = clip(cellText(cell), Math.max(3, Math.floor((col - 8) / (6 * fs))))
          const codes = codesOf(cell)
          const tip =
            `${screen.name} · ${poseLabel(pose)}: ${STATE_WORD[cell.state]}` +
            (codes.length ? ` (${codes.map(describe).join(', ')})` : cell.label ? ` (${cell.label})` : '')
          if (chosen?.screen === screen.name && chosen.pose === pose) {
            picked = `<rect class="pick" x="${x + 1.5}" y="${y + 2.5}" width="${col - 3}" height="${rowH - 5}" rx="7"/>`
          }
          return (
            `<g><title>${escapeXml(tip)}</title>` +
            `<rect class="cell ${cell.state}" x="${x + 3}" y="${y + 4}" width="${col - 6}" height="${rowH - 8}" rx="5"/>` +
            (text
              ? `<text class="label ${cell.state}" x="${x + col / 2}" y="${baseline}" text-anchor="middle">${escapeXml(text)}</text>`
              : '') +
            '</g>'
          )
        })
        .join('')
      return `<line class="rule" x1="0" x2="${inner}" y1="${y}" y2="${y}"/>${name}${cells}`
    })
    .join('')

  // Only the states the matrix holds, with their counts, wrapped to the width.
  let lx = 0
  let ly = headH + m.screens.length * rowH + px(18)
  const legend = LEGEND.filter(item => tally[item.state] > 0)
    .map(item => {
      const text = `${item.label} ${tally[item.state]}`
      const w = px(17) + text.length * px(5.8) + 14
      if (lx > 0 && lx + w - 14 > inner) {
        lx = 0
        ly += px(17)
      }
      const part =
        `<rect class="cell ${item.state}" x="${lx}" y="${ly - px(9)}" width="${px(12)}" height="${px(12)}" rx="3"/>` +
        `<text class="legend" x="${lx + px(17)}" y="${ly + 1}">${escapeXml(text)}</text>`
      lx += w
      return part
    })
    .join('')

  const height = Math.ceil(ly + 6 + PAD * 2)
  const style = `${STYLE_FONT}
    .icon *{fill:#dde7fb;stroke:#151a2d;stroke-width:2.2;stroke-linejoin:round;stroke-linecap:round}
    .icon .dot{fill:#151a2d;stroke:none}.icon .crease{fill:none}.icon .half{fill:#9fbaf0;stroke:none}
    .pose{font-size:${px(9.5)}px;fill:#5f5e5a}.name{font-size:${px(11.5)}px;font-weight:500;fill:#1f1e1d}
    .legend{font-size:${px(10)}px;fill:#5f5e5a}.rule{stroke:#e4e2da;stroke-width:0.5}
    .label{font-size:${px(10)}px;font-weight:500}
    .card{fill:#ffffff;stroke:#e4e2da;stroke-width:1}
    .pick{fill:none;stroke:#2f6fde;stroke-width:2}
    .cell.pending{fill:none;stroke:#c9c7bd;stroke-dasharray:3 3}
    .cell.unchanged{fill:#f1efe8}.label.unchanged{fill:#888780}
    .cell.finding{fill:#fcebeb}.label.finding{fill:#a32d2d}
    .cell.proposed{fill:#e6f1fb}.label.proposed{fill:#0c447c}
    .cell.migrated{fill:#faeeda}.label.migrated{fill:#854f0b}
    .cell.verified{fill:#eaf3de}.label.verified{fill:#27500a}
    @media (prefers-color-scheme:dark){
      .card{fill:#1f1e1d;stroke:#3a3936}.pick{stroke:#7aa7ff}
      .icon *{fill:#22304a;stroke:#d6e0f5}.icon .dot{fill:#d6e0f5}.icon .crease{fill:none}.icon .half{fill:#3d5b94}
      .pose,.legend{fill:#b4b2a9}.name{fill:#f1efe8}.rule{stroke:#3a3936}
      .cell.pending{stroke:#5f5e5a}.cell.unchanged{fill:#2c2c2a}.label.unchanged{fill:#b4b2a9}
      .cell.finding{fill:#501313}.label.finding{fill:#f7c1c1}
      .cell.proposed{fill:#042c53}.label.proposed{fill:#b5d4f4}
      .cell.migrated{fill:#412402}.label.migrated{fill:#fac775}
      .cell.verified{fill:#173404}.label.verified{fill:#c0dd97}
    }`

  return {
    width,
    height,
    source:
      `<svg xmlns="${SVG_NS}" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}">` +
      `<style>${style}</style><rect class="card" x="0.5" y="0.5" width="${width - 1}" height="${height - 1}" rx="14"/>` +
      `<g transform="translate(${PAD} ${PAD})">${head}${rows}${picked}${legend}</g></svg>`,
  }
}

// One shot at `width`, captioned, with the fold drawn where the inner display bends: a red band while the division
// is active, a dashed outline while the phone lies flat. With no shot, a short dashed box saying why.
function shotSvg(title: string, pic: Picture | null, note: string, fold: 'active' | 'inactive' | undefined, width: number, aspect: number) {
  const top = 18
  const ratio = pic ? pic.width / pic.height : aspect
  const shotH = pic ? Math.round(width / ratio) : Math.min(EMPTY_H, Math.round(width / ratio))
  const parts = [`<text class="t" x="0" y="12">${escapeXml(title)}</text>`]
  if (pic) {
    parts.push(
      `<image x="0" y="${top}" width="${width}" height="${shotH}" preserveAspectRatio="xMidYMid meet" href="data:image/jpeg;base64,${pic.jpeg}"/>`,
    )
    if (fold) {
      const band = (ratio >= 1 ? width : shotH) * FOLD_SHARE
      const rect =
        ratio >= 1
          ? `x="${(width - band) / 2}" y="${top}" width="${band}" height="${shotH}"`
          : `x="0" y="${top + (shotH - band) / 2}" width="${width}" height="${band}"`
      parts.push(`<rect class="fold ${fold}" ${rect}/>`)
      parts.push(`<text class="f" x="${width}" y="12" text-anchor="end">${fold === 'active' ? 'fold' : 'fold, flat'}</text>`)
    }
    parts.push(`<rect class="frame" x="0.5" y="${top + 0.5}" width="${width - 1}" height="${shotH - 1}" rx="6"/>`)
  } else {
    parts.push(
      `<rect class="empty" x="0.5" y="${top + 0.5}" width="${width - 1}" height="${shotH - 1}" rx="6"/>` +
        `<text class="n" x="${width / 2}" y="${top + shotH / 2}" text-anchor="middle">${escapeXml(note)}</text>`,
    )
  }
  const full = top + shotH
  const style = `${STYLE_FONT}
    .t{font-size:11px;font-weight:500;fill:#5f5e5a}.n{font-size:11px;fill:#888780}.f{font-size:10px;fill:#a32d2d}
    .frame{fill:none;stroke:#e4e2da}.empty{fill:none;stroke:#c9c7bd;stroke-dasharray:3 3}
    .fold.active{fill:#e24b4a;fill-opacity:0.28}.fold.inactive{fill:none;stroke:#e24b4a;stroke-opacity:0.7;stroke-dasharray:4 3}
    @media (prefers-color-scheme:dark){.t{fill:#b4b2a9}.n{fill:#888780}.f{fill:#f09595}.frame{stroke:#3a3936}.empty{stroke:#5f5e5a}}`
  return {
    width,
    height: full,
    source:
      `<svg xmlns="${SVG_NS}" viewBox="0 0 ${width} ${full}" width="${width}" height="${full}">` +
      `<style>${style}</style>${parts.join('')}</svg>`,
  }
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
// Where the pane keeps the simulator's frames and the small copies of shots it draws: ~/Library/Caches/foldsmith,
// set when the session starts (a folder of the user's own, not a shared one in /tmp).
let scratch = ''
// The status file's last seen mtime; module state, so a reload re-reads the file.
let lastMtime = -1
let liveBusy = false
let liveFrame = 0
const shrunk = new Map<string, Picture>()

const parentOf = (path: string) => path.replace(/\/[^/]*$/, '') || '/'

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

// A PNG made into a JPEG at most `max` pixels on its long side, small enough to draw on any surface.
async function shrink($: EngineInterface, png: string, max: number, cache = true): Promise<Picture | null> {
  if (!scratch) return null
  try {
    const { mtimeMs } = await $.fs.stat(png)
    const id = `${png}@${mtimeMs}@${max}`
    const known = cache ? shrunk.get(id) : undefined
    if (known) return known
    const out = `${scratch}/${png.replace(/[^A-Za-z0-9]/g, '_').slice(-100)}-${max}.jpg`
    const made = await $.process.run(['/usr/bin/sips', '-Z', String(max), '-s', 'format', 'jpeg', '-s', 'formatOptions', '55', png, '--out', out])
    if (made.exitCode !== 0) return null
    const size = await $.process.run(['/usr/bin/sips', '-g', 'pixelWidth', '-g', 'pixelHeight', out])
    const width = Number(/pixelWidth: (\d+)/.exec(size.stdout)?.[1] ?? 0)
    const height = Number(/pixelHeight: (\d+)/.exec(size.stdout)?.[1] ?? 0)
    if (!width || !height) return null
    const { base64 } = await $.fs.read(out, { as: 'bytes' })
    if (base64.length > MAX_JPEG && max > 300) return shrink($, png, Math.round(max * 0.7), cache)
    const pic: Picture = { jpeg: base64, width, height, file: png, at: mtimeMs }
    if (cache) shrunk.set(id, pic)
    return pic
  } catch {
    return null
  }
}

// The before and after shots of the picked screen and pose, made small.
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
  const next: { [file: string]: Picture } = {}
  for (const path of [cell?.before, cell?.after]) {
    if (!path) continue
    const file = await absolute($, path)
    if (!file) continue
    const pic = await shrink($, file, 720)
    if (pic) next[file] = pic
  }
  await update($, pictures, () => next)
}

async function choosePick($: EngineInterface, next: Pick | null) {
  if (!next) return
  await update($, pick, () => next)
  await refreshPictures($)
}

// The followed folder's branch and whether the skill has written its report there.
async function describeFolder($: EngineInterface, base: string) {
  const git = await $.process.run(['/usr/bin/git', '-C', base, 'branch', '--show-current'], { timeoutMs: 3000 })
  const report = await $.fs.exists(`${base}/.duo/REPORT.md`)
  await update($, folderInfo, () => ({ branch: git.exitCode === 0 ? git.stdout.trim() || null : null, report }))
}

async function poll($: EngineInterface) {
  if ((await read($, source)) === 'demo') return
  const base = await folder($)
  const file = `${base}/${STATUS_FILE}`
  try {
    if (!(await $.fs.exists(file))) {
      if (lastMtime !== -1) {
        lastMtime = -1
        await update($, migration, () => null)
        await update($, source, () => 'none')
      }
      return
    }
    const { mtimeMs } = await $.fs.stat(file)
    if (mtimeMs === lastMtime) return
    const firstSeen = lastMtime === -1
    lastMtime = mtimeMs
    const parsed = JSON.parse(await $.fs.read(file)) as Migration
    if (!parsed || !Array.isArray(parsed.screens)) throw new Error('missing "screens" array')
    await update($, migration, () => parsed)
    await update($, source, () => 'file')
    await update($, error, () => null)
    // A finished migration starts with the simulator paused: nothing moves there until someone resumes it.
    if (firstSeen) await update($, paused, () => parsed.phase === 'done')
    await describeFolder($, base)
    await refreshPictures($)
    if (firstSeen) void $.ui.open({ id: PANE, title: TITLE })
  } catch (err) {
    await update($, error, () => `${file}: ${err instanceof Error ? err.message : String(err)}`)
  }
}

// Progress files under the session's folder (past build output and captures) and those followed before, newest first.
async function discover($: EngineInterface): Promise<Known[]> {
  const prune = ['node_modules', '.git', '.build', 'build', 'DerivedData', 'captures'].flatMap((name, i) =>
    i === 0 ? ['-name', name] : ['-o', '-name', name],
  )
  const found = await $.process.run(
    ['/usr/bin/find', cwd, '-maxdepth', '5', '(', ...prune, ')', '-prune', '-o', '-path', '*/.duo/migration.json', '-print'],
    { timeoutMs: 8000 },
  )
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
      if (!(await $.fs.exists(file))) continue
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

async function switchTo($: EngineInterface, path: string | null) {
  lastMtime = -1
  await update($, root, () => path)
  await update($, migration, () => null)
  await update($, source, () => 'none')
  await update($, live, () => null)
  await update($, pick, () => null)
  await update($, pictures, () => ({}))
  await update($, folderInfo, () => ({ branch: null, report: false }))
  await poll($)
}

// Follows the folder picked for this session's folder, else the progress file that changed last.
async function choose($: EngineInterface) {
  const list = await discover($)
  const picked = await $.store.get(`watch:${cwd}`)
  const here = list.find(k => k.root === cwd || k.root.startsWith(under(cwd)))
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
  await update($, error, () => null)
  await update($, pick, () => defaultPick(DEMO))
  await update($, pictures, () => ({}))
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
  const checks: [string, 'file' | 'dir'][] = [[`${base}/.duo`, 'dir'], [`${base}/.duo/${name}`, name === 'captures' ? 'dir' : 'file']]
  for (const [path, kind] of checks) {
    const stat = await $.fs.stat(path).catch(() => null)
    if (!stat || stat.isLink || stat.kind !== kind) return
  }
  await $.process.run(name === 'captures' ? ['/usr/bin/open', '-R', `${base}/.duo/captures`] : ['/usr/bin/open', '-t', `${base}/.duo/REPORT.md`])
}

// One frame of the simulator: the panel that is drawing (through duo.py when it is there), made small. Only while the
// pane is on screen and not paused.
async function liveTick($: EngineInterface) {
  if (liveBusy || !scratch || (await read($, source)) !== 'file' || (await read($, paused))) return
  const m = await read($, migration)
  if (!m) return
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
    const pic = png ? await shrink($, png, 720, false) : null
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
    await choose($)
    await poll($)
    $.clock.every(1500, () => poll($))
    $.clock.every(LIVE_EVERY_MS, () => liveTick($))
    $.clock.every(LOOK_EVERY_MS, () => choose($))

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
      await follow($, path ? (path.startsWith('/') ? path : `${cwd}/${path}`) : null)
      text = path ? `Foldsmith pane: following ${path}.` : 'Foldsmith pane: following the newest migration.'
    } else {
      await choose($)
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
    const elements = $.ui.resolve(e)
    const { Box, Text, Button } = elements
    // The mobile app draws no picker yet: there the Previous and Next buttons move through the cells.
    const Select = 'Select' in elements ? elements.Select : null
    const graphical = e.surface === 'desktop' || e.surface === 'mobile' || e.surface === 'vscode'
    const fill = (text: string) => () => void $.prompt.fill({ text })
    const start = base === cwd ? '/foldsmith-start' : `/foldsmith-start ${base}`
    const errorLine = problem && <Text color="error">{problem}</Text>

    if (!m) {
      return (
        <Box flexDirection="column" gap={1}>
          <Text weight="semibold">No migration in {shown(base)}</Text>
          <Text dimColor>
            /foldsmith-start adapts every screen of the app hands-free and writes {STATUS_FILE} as it goes; this pane follows
            that file: the simulator, every screen in every pose, before and after, and what is done and left.
          </Text>
          <Box flexDirection="row" gap={1} flexWrap="wrap">
            <Button key="start" variant="primary" label="Start migration" onPress={fill(start)} />
            <Button key="demo" label="Show sample data" onPress={() => void showDemo($)} />
          </Box>
          {found.length > 0 && (
            <Box flexDirection="column">
              <Text size="footnote" weight="medium">
                Migrations found
              </Text>
              {found.map(k => (
                <Box flexDirection="row">
                  <Button key={`follow:${k.root}`} plain dimColor label={`${k.app} · ${shown(k.root)}`} onPress={() => void follow($, k.root)} />
                </Box>
              ))}
            </Box>
          )}
          {errorLine}
        </Box>
      )
    }

    const frame = await read($, live)
    const frameNote = await read($, liveNote)
    const isPaused = await read($, paused)
    const info = await read($, folderInfo)
    const open = await read($, expanded)
    const chosen = (await read($, pick)) ?? defaultPick(m)
    const shots = await read($, pictures)
    const screen = screenOf(m, chosen?.screen)
    const cell = chosen && screen ? cellOf(screen.cells, chosen.pose) : undefined
    const before = cell?.before ? shots[await absolute($, cell.before)] ?? null : null
    const after = cell?.after ? shots[await absolute($, cell.after)] ?? null : null
    const { done, left } = progress(m)
    const tally = counts(m)
    const total = m.screens.length * posesOf(m).length
    const finished = m.screens.filter(s => isFinished(m, s)).length
    const status = statusOf(m, from, left.length)
    const at = phaseIndex(m.phase)
    const codes = cell ? codesOf(cell) : []
    // The left item about the picked screen: the skill's reason it is not finished.
    const note = chosen && left.find(line => line.toLowerCase().startsWith(`${chosen.screen.toLowerCase()}:`))
    const missing = (path: string | undefined) => (path ? 'loading…' : 'not captured yet')
    const toggle = (key: keyof Expanded) => () => void update($, expanded, value => ({ ...value, [key]: !value[key] }))
    const where = [from === 'demo' ? 'sample data' : shown(base), info.branch && `branch ${info.branch}`].filter(Boolean).join(' · ')
    // The body's width in CSS pixels, from its cells. The matrix spans it; past TWO_UP what is left and done sits
    // beside the picked cell, so both show under the matrix without scrolling.
    const cells = e.props.bodyColumns
    const span = Math.max(NARROW, Math.floor((cells - 2) * PX_PER_CELL))
    const twoUp = graphical && span >= TWO_UP
    const side = twoUp ? Math.floor((span - 2 * PX_PER_CELL) / 2) : span
    // The characters a list line shows before it is cut (a footnote character is about 6 px), so a cut line offers
    // its full text.
    const lineChars = graphical ? Math.floor(side / 6.2) : cells - 2

    const header = (
      <Box flexDirection="column">
        <Box flexDirection="row" gap={1} alignItems="center" flexWrap="wrap">
          <Text size="heading" weight="semibold">
            {m.app ?? 'iPhone Duo migration'}
          </Text>
          <Text size="footnote" weight="medium" color={status.color}>
            {status.text}
          </Text>
        </Box>
        <Text dimColor size="footnote" wrap="truncate-middle">
          {where}
        </Text>
      </Box>
    )
    const stepper = m.phase !== 'done' && (
      <Box flexDirection="row" gap={1} flexWrap="wrap">
        {PHASES.map((p, i) => (
          <Text size="footnote" weight={i === at ? 'semibold' : 'regular'} dimColor={i > at}>
            {i < at ? '✓' : i === at ? '●' : '○'} {p.label}
            {i < PHASES.length - 1 ? '  ›' : ''}
          </Text>
        ))}
      </Box>
    )
    const summary = (
      <Text size="footnote">
        {finished} of {m.screens.length} screens finished · {tally.verified + tally.unchanged} of {total} poses good
        {tally.finding > 0 ? ` · ${tally.finding} with defects` : ''}
      </Text>
    )
    const simulatorRow = from === 'file' && (
      <Box flexDirection="row" gap={1} alignItems="center">
        <Text weight="medium">Simulator</Text>
        <Text dimColor size="footnote">
          {isPaused ? 'paused' : frameNote ?? (frame ? panelOf(frame.file) : 'waiting for a frame')}
        </Text>
        <Button key="live" plain dimColor label={isPaused ? 'Resume' : 'Pause'} onPress={() => void update($, paused, value => !value)} />
      </Box>
    )
    const navigation = chosen && (
      <Box flexDirection="row" gap={1} flexWrap="wrap" alignItems="center">
        {Select && m.screens.length > 0 && (
          <Select
            key="screen"
            label="Screen"
            options={m.screens.map(s => ({ value: s.name }))}
            value={chosen.screen}
            onSelect={(value: string) => void choosePick($, { ...chosen, screen: value })}
          />
        )}
        {Select && (
          <Select
            key="pose"
            label="Pose"
            options={posesOf(m).map(p => ({ value: p, label: poseLabel(p) }))}
            value={chosen.pose}
            onSelect={(value: string) => void choosePick($, { ...chosen, pose: value })}
          />
        )}
        <Button key="prev" label="‹ Previous" onPress={() => void choosePick($, step(m, chosen, -1))} />
        <Button key="next" label="Next ›" onPress={() => void choosePick($, step(m, chosen, 1))} />
        {tally.finding > 0 && (
          <Button key="next-defect" label="Next defect" onPress={() => void choosePick($, step(m, chosen, 1, true))} />
        )}
      </Box>
    )
    const detail = chosen && cell && (
      <Box flexDirection="column">
        <Box flexDirection="row" gap={1} flexWrap="wrap">
          <Text weight="semibold">
            {chosen.screen} · {poseLabel(chosen.pose)}
          </Text>
          <Text color={STATE_COLOR[cell.state]}>{STATE_WORD[cell.state]}</Text>
        </Box>
        {screen?.pattern && (
          <Text dimColor size="footnote">
            Pattern: {screen.pattern}
          </Text>
        )}
        {codes.length > 0 && (
          <Text size="footnote" color="error">
            {codes.map(describe).join(' · ')}
          </Text>
        )}
        {note && (
          <Text dimColor size="footnote">
            {note.slice(chosen.screen.length + 1).trim()}
          </Text>
        )}
      </Box>
    )
    const list = (title: string, lines: string[], mark: string, empty: string, dim: boolean) => (
      <Box flexDirection="column">
        <Text size="footnote" weight="medium">
          {title} ({lines.length})
        </Text>
        {lines.length === 0 && (
          <Text dimColor size="footnote">
            {empty}
          </Text>
        )}
        {lines.map(line => (
          <Text size="footnote" dimColor={dim} wrap={open.notes ? 'wrap' : 'truncate-end'}>
            {mark} {line}
          </Text>
        ))}
      </Box>
    )
    const lists = (
      <Box flexDirection="column" gap={1}>
        {list(m.phase === 'done' ? 'Left for you' : 'Left', left, '○', 'Nothing', false)}
        {list('Done', done, '✓', 'Nothing yet', true)}
        {[...left, ...done].some(line => line.length + 2 > Math.min(90, lineChars)) && (
          <Box flexDirection="row">
            <Button key="notes" plain dimColor label={open.notes ? 'Show less' : 'Show full notes'} onPress={toggle('notes')} />
          </Box>
        )}
      </Box>
    )
    const log = m.log ?? []
    const recent = log.slice(open.log ? -40 : -5).reverse()
    const activity = log.length > 0 && (
      <Box flexDirection="column">
        <Text size="footnote" weight="medium">
          Activity
        </Text>
        {recent.map(line => (
          <Text dimColor size="footnote" wrap={open.log ? 'wrap' : 'truncate-end'}>
            {line}
          </Text>
        ))}
        {(log.length > 5 || recent.some(line => line.length > lineChars)) && (
          <Box flexDirection="row">
            <Button
              key="log"
              plain
              dimColor
              label={open.log ? 'Show less' : log.length > 5 ? `Show all (${log.length})` : 'Show full lines'}
              onPress={toggle('log')}
            />
          </Box>
        )}
      </Box>
    )
    const actions = from === 'file' && (
      <Box flexDirection="row" gap={1} flexWrap="wrap">
        {(m.phase !== 'done' || left.length > 0) && (
          <Button key="resume" variant="primary" label={m.phase === 'done' ? 'Resume migration' : 'Restart if stopped'} onPress={fill(start)} />
        )}
        {info.report && (
          <Button key="report" label="Open report" onPress={() => void openDuo($, base, 'REPORT.md')} />
        )}
        <Button key="captures" label="Show captures" onPress={() => void openDuo($, base, 'captures')} />
      </Box>
    )
    const switcher = Select && found.length > 1 && from === 'file' && found.some(k => k.root === base) && (
      <Select
        key="app"
        label="App"
        options={found.map(k => ({ value: k.root, label: `${k.app} · ${shown(k.root)}` }))}
        value={base}
        onSelect={(value: string) => void follow($, value)}
      />
    )

    if (graphical) {
      const { Svg } = $.ui.resolve(e)
      // Drawn interactive (for its tooltips), it needs its height: without one the desktop sizes the frame like a bare
      // iframe, 150 px tall, and the matrix shrinks to fit.
      const matrix = matrixSvg(m, chosen, Math.min(span, MAX_MATRIX))
      const pose = (chosen?.pose ?? 'book') as PoseId
      const fold = FOLD[pose]
      const aspect = (before ?? after) ? (before ?? after)!.width / (before ?? after)!.height : ASPECT[pose] ?? 1
      // Before and after side by side beside the lists, and in one column while each keeps a useful size; a portrait
      // shot no taller than SHOT_H.
      const half = Math.floor((side - 12) / 2)
      const sideBySide = twoUp || half >= 180
      const room = sideBySide ? half : side
      const w = aspect >= 1 ? room : Math.min(room, Math.round(SHOT_H * aspect))
      const pair = [
        shotSvg('Before', before, missing(cell?.before), fold, w, aspect),
        shotSvg('After', after, missing(cell?.after), fold, w, aspect),
      ]
      const frameAspect = frame ? frame.width / frame.height : 1
      const frameSvg = frame && shotSvg('', frame, '', undefined, frameAspect >= 1 ? side : Math.min(side, Math.round(300 * frameAspect)), frameAspect)
      const standing = (
        <Box flexDirection="column" gap={1}>
          {lists}
          {activity}
          {actions}
          {switcher}
        </Box>
      )
      const inspector = (
        <Box flexDirection="column" gap={1}>
          {simulatorRow}
          {!isPaused && frameSvg && (
            <Svg source={frameSvg.source} width={frameSvg.width} height={frameSvg.height} alt="The iPhone Duo simulator, as it is now" />
          )}
          {navigation}
          {detail}
          {chosen && (
            <Box key="pair" flexDirection={sideBySide ? 'row' : 'column'} gap={1}>
              {pair.map((svg, i) => (
                <Svg
                  source={svg.source}
                  width={svg.width}
                  height={svg.height}
                  alt={`${chosen.screen} in ${poseLabel(chosen.pose)}, ${i === 0 ? 'before' : 'after'}`}
                />
              ))}
            </Box>
          )}
          {from === 'file' && (cell?.before || cell?.after) && (
            <Box flexDirection="row" gap={1}>
              {cell?.before && (
                <Button key="open-before" plain dimColor label="Open before" onPress={() => void openShot($, cell.before!)} />
              )}
              {cell?.after && (
                <Button key="open-after" plain dimColor label="Open after" onPress={() => void openShot($, cell.after!)} />
              )}
            </Box>
          )}
        </Box>
      )
      const columnCells = Math.floor((cells - 4) / 2)
      return (
        <Box flexDirection="column" gap={1}>
          {header}
          {errorLine}
          {stepper}
          {summary}
          <Svg
            source={matrix.source}
            width={matrix.width}
            height={matrix.height}
            isInteractive
            alt={`Screen by pose matrix for ${m.screens.length} screens across ${posesOf(m).length} iPhone Duo poses`}
          />
          {twoUp ? (
            <Box key="columns" flexDirection="row" gap={2} alignItems="flex-start">
              <Box flexDirection="column" flexGrow={1} flexShrink={1} width={columnCells}>
                {standing}
              </Box>
              <Box flexDirection="column" flexGrow={1} flexShrink={1} width={columnCells}>
                {inspector}
              </Box>
            </Box>
          ) : (
            <Box key="columns" flexDirection="column" gap={1}>
              {standing}
              {inspector}
            </Box>
          )}
        </Box>
      )
    }

    const { Image } = $.ui.resolve(e)
    const poses = posesOf(m)
    const pad = (text: string, n: number) => clip(text, n).padEnd(n)
    const picture = (file: string | undefined, alt: string, generation?: number) =>
      file ? (
        <Image source={{ file, format: 'png', generation }} columns={24} rows={14} alt={alt} />
      ) : (
        <Text dimColor>{alt}</Text>
      )
    return (
      <Box flexDirection="column" gap={1}>
        <Text weight="semibold">
          {m.app ?? 'iPhone Duo migration'} <Text color={status.color}>{status.text}</Text>
        </Text>
        {errorLine}
        {stepper}
        {summary}
        {simulatorRow}
        {from === 'file' && !isPaused && frame && picture(frame.file, panelOf(frame.file), liveFrame)}
        <Box flexDirection="column">
          <Text dimColor>{pad('', 10) + poses.map(p => pad(POSE_SHORT[p] ?? p, 6)).join('')}</Text>
          {m.screens.map(s => (
            <Text>
              {pad(s.name, 10) +
                poses
                  .map(p => pad((s.name === chosen?.screen && p === chosen.pose ? '[' : '') + GLYPH[cellOf(s.cells, p).state], 6))
                  .join('')}
            </Text>
          ))}
        </Box>
        <Text dimColor size="footnote">
          {LEGEND.map(item => `${GLYPH[item.state]} ${item.label}`).join('   ')}
        </Text>
        {navigation}
        {detail}
        {chosen && (
          <Box flexDirection="row" gap={2}>
            {picture(cell?.before && (await absolute($, cell.before)), `Before: ${missing(cell?.before)}`)}
            {picture(cell?.after && (await absolute($, cell.after)), `After: ${missing(cell?.after)}`)}
          </Box>
        )}
        {lists}
        {activity}
        {actions}
      </Box>
    )
  })
}
