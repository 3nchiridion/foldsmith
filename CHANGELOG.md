# Changelog

Versions of the repository, as tagged. The Claude Code plugin carries its own version in
`plugins/foldsmith/.claude-plugin/plugin.json`.

## v0.1.0 — 2026-10-30
The first public release.

Status, as the README gives it: on 2026-10-29, four patterns, each with a reference implementation, a pose matrix
captured in all seven poses and detector results. Three of them, Fold-aligned split, Even grid and Arrangement, are
compared with Apple's apps (Settings on the simulator; Fitness, Podcasts and Accessibility Reader in Apple's tech-talk
frames). The fourth, Reflowing columns, has no Apple app to compare with yet. The skill was run on three open-source
apps: IceCubesApp's five logged-out screens and NetNewsWire's five ended with no finding in any pose (8 and 19 cells
fixed and verified, the rest fine as they were; NetNewsWire's Reader View button, found later, is not fixed);
Wikipedia's run finished 2 of its 11 screens and did not pass review.

- **Patterns**: Fold-aligned split (with a tiled form that keeps both panes upright), Even grid, Arrangement and
  Reflowing columns, each a page in `patterns/` and a copy-in file in `Sources/Patterns/`; the decision table and the
  defect taxonomy.
- **Detectors**: eight defect classes read from a catalog record or any app's accessibility tree (`swift run
  duo-detect <dir>`); `DuoPoseTesting` for app tests.
- **The skill** `foldsmith-duo`, installable in Claude Code, Codex, Cursor and other agents (`npx skills add
  3nchiridion/foldsmith`): adapts a whole app hands-free and proves every pose.
- **The plugin** `foldsmith` 0.5.0 for Claude Code: the skill, `/foldsmith-start`, and a pane with the live simulator,
  the screen × pose matrix, before and after, and what is done and left (`/foldsmith`, `/foldsmith watch`,
  `/foldsmith demo`, `/foldsmith off`).
- **Evidence** in [foldsmith-evidence](https://github.com/3nchiridion/foldsmith-evidence): the goldens, the comparisons
  with Apple's apps, the accessibility captures, the three migrations and the primary material.
- Renamed before release: the repository (duo-patterns, then duo-kit), the commands (`/duo-start` → `/foldsmith-start`,
  `/duo` → `/foldsmith`) and the skill (`iphone-duo-patterns`, then `foldsmith`, now `foldsmith-duo`).
