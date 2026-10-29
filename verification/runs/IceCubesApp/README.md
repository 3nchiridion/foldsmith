# IceCubesApp, migrated hands-free (2026-10-28)

The second run of the hands-free skill (`skills/iphone-duo-patterns/SKILL.md`), and the first on a SwiftUI app: the
`/duo-start` prompt and nothing else about the work, run by a fresh Claude Code agent with the skill, on the project's
iPhone Duo simulator (iOS 27.1, Xcode 27.1). The prompt added only this machine's facts (where Xcode, `duo.py` and the
tap runner are; that no Mastodon account may be created) and the project's limits (no simulator changes, no push, no
edits to this repository, strangers' posts never committed). The app was IceCubesApp at 98098b9
(`raw/corpus/IceCubesApp`, a clone made by `raw/corpus/clone.sh`, not committed), copied outside this repository with one baseline commit on `main`; the skill committed its
work on `duo-migration` there. Headless `claude -p`, used for NetNewsWire, was signed out, so the run was a subagent.

| File | What it is |
|---|---|
| `REPORT.md` | the skill's report: per screen the pattern, what changed, what is left and why, and "Skill problems" |
| `audit.md` | the audit of the unmodified app and the classification of each screen |
| `migration.json` | the progress file at the end of the run (what the `duo-migration` pane reads) |
| `IceCubesApp.flow` | the screens the skill found and the taps that reach them, logged out |
| `detectors-before.md`, `detectors-after.md` | `duo-detect` on the snapshots before (33) and after (35) |
| `IceCubesApp.patch` | the code change, `main..duo-migration` without `.duo/`; **AGPL-3.0**, as IceCubesApp is |
| `LICENSE-AGPL-3.0` | the license of the patch: IceCubesApp's `LICENSE` at 98098b9, unchanged |
| `commits.txt` | the run's four commits |

The shots stay outside: the timeline and the post show strangers' posts.

Result: five screens reachable without an account, all Fold-aligned split, all verified in all seven poses (G3), in
about two hours (the before capture 35 min, the after capture 23 min). Before: T15 on the Add Account sheet in book;
T7 on the post (flat sideways), Settings (laptop) and Display Settings (laptop, flat sideways), where a fold re-presented
Add Account over the screen; and a crash closing the phone from tent with Settings selected, so Settings showed the
Home Screen in both flat poses. The cause of the T7s and the crash was one: the logged-out tabs sat in an untitled
sidebar-only `TabSection`, and every fold rebuilt the tab bar's items. Plain tabs fixed both; the sheet rule
(`foldAwareSheetPlacement()` on every sheet, `readsBookFold()` on the window's root) fixed T15. `duo-detect`: 2 findings
before (the crash read `n/a`), 0 after. The timeline needed nothing: the system's tab sidebar already splits at the
fold. Screens that need an account are in `todo`.

Spot-checked by eye after the run (2026-10-28): Add Account on the trailing half in book; Settings in front in tent and
both flat poses; the post in flat sideways; the tab sidebar ending at the fold in book.

What the run changed in this repository (Phase 4, step 8), from its "Skill problems":
- Taps: XCTest waited 60 s for SpringBoard before every tap (its check for system alerts); the tap runner now turns
  that check off. Settings → Display Settings, closed only: 243 s → 61 s.
- `capture-app.sh` exits 3 and repeats the lines when a screen or pose was skipped, takes `SCREEN=` to probe one screen
  behind taps, and documents `TAP_TIMEOUT`.
- A crash on the fold is a finding: the runner says when the app is not in front, and `duo-detect` reports T7 there.
- The capture's "lost the screen" line names the pose after which it was lost.
- The reference files compile for Mac Catalyst, visionOS and macOS too (no reserved regions in those SDKs;
  `.trailing` unavailable on visionOS and macOS); `FoldAlignedSplit.swift` gains `readsBookFold()`.
- P1 says what to do with a `TabView` sidebar, and the hazard the run found in one; the decision table's I1 says what a
  feed is, and the pages that disagreed now point to it; the T10 scan matches whole words.
