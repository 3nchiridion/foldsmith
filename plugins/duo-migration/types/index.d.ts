export type PoseId =
  | 'closed'
  | 'closed-sideways'
  | 'book'
  | 'laptop'
  | 'tent'
  | 'flat-sideways'
  | 'flat-upright'
  | 'split-half'

export type CellState = 'pending' | 'unchanged' | 'finding' | 'proposed' | 'migrated' | 'verified'

// `before` and `after`: shots of this screen in this pose, relative to the app's repo. `finding`: every class the
// audit saw there, space-separated (`T14 T7`); `label` is the one the matrix shows. `waived`: class id → why the shot
// does not bear out that detector line after the migration (`progress.py waive`); the pane does not show it.
export type Cell = {
  state: CellState
  label?: string
  finding?: string
  before?: string
  after?: string
  waived?: { [classId: string]: string }
}

export type Screen = { name: string; pattern?: string; cells: { [pose: string]: Cell } }

// `approve` is read from older progress files; the hands-free skill no longer stops there.
export type Phase = 'screens' | 'audit' | 'classify' | 'approve' | 'migrate' | 'verify' | 'done'

export type Migration = {
  app?: string
  phase: Phase
  simulator?: string
  driver?: string
  poses?: PoseId[]
  screens: Screen[]
  done?: string[]
  todo?: string[]
  log?: string[]
}

export type Source = 'none' | 'file' | 'demo'

// A shot made small enough to draw: a JPEG's bytes, base64, and the PNG it came from.
export type Picture = { jpeg: string; width: number; height: number; file: string; at: number }

export type Pick = { screen: string; pose: string }

// A progress file found under the session's folder or followed before: the app's folder, its name, when it changed.
export type Known = { root: string; app: string; mtime: number }

// What the pane knows about the followed folder besides the progress file.
export type Folder = { branch: string | null; report: boolean }

export type Expanded = { notes: boolean; log: boolean }

declare module 'claude-code' {
  interface PluginState {
    'duo-migration': {
      migration: Migration | null
      source: Source
      error: string | null
      root: string | null
      live: Picture | null
      liveNote: string | null
      paused: boolean
      pick: Pick | null
      pictures: { [file: string]: Picture }
      known: Known[]
      folderInfo: Folder
      expanded: Expanded
    }
  }
}
