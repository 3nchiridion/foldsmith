# Foldsmith

Measured layout patterns and hands-free migration for iPhone Duo, proven in every pose.

<!-- DEMO: 45–60s screen recording of /foldsmith-start on NetNewsWire → matrix fills → before/after on the fold. docs/assets/demo.gif linked to demo.mp4 -->

<p align="center">
  <img src="https://developer.apple.com/iphone-duo/images/main_2x.png" alt="iPhone Duo partially folded in book pose, showing the Home Screen across both halves" width="600">
  <br>
  <sub>Image © Apple Inc. All rights reserved. Reproduced from Apple's <a href="https://developer.apple.com/iphone-duo/">iPhone Duo developer page</a> solely for the purpose of identification.</sub>
</p>

iPhone is a trademark of Apple Inc., registered in the U.S. and other countries, and iPhone Duo is a trademark of Apple
Inc. Foldsmith is independent and is not affiliated with, sponsored by, or endorsed by Apple Inc.

## Why now
- **The App Store marks apps that are ready.** Submit iPhone Duo screenshots and the product page shows a badge telling
  people the app is optimized for iPhone Duo ([Apple Developer: Prepare](https://developer.apple.com/iphone-duo/prepare/));
  Apple calls it the Made for iPhone Duo badge
  ([Newsroom, Oct 22, 2026](https://www.apple.com/newsroom/2026/10/developers-bring-incredible-new-app-experiences-to-iphone-duo/)).
- **The screenshots become required.** Starting April 2027, apps submitted to the App Store must include iPhone Duo
  screenshots ([Apple Developer News, Oct 5, 2026](https://developer.apple.com/news/?id=kkphp5qo); App Store Connect
  Help scopes it to apps built with the iOS 27.1 SDK or later:
  [screenshot specifications](https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/)).

## What makes it different
- **Detectors that read any app.** Eight defect classes (a pane boundary off the fold, text across it, a bar item
  stranded beside the vertical bar, state lost on the fold, …) found from an app's accessibility tree on the simulator,
  in every pose: [`Sources/DuoDetectors/`](Sources/DuoDetectors/), the classes in [the taxonomy](patterns/TAXONOMY.md),
  and the catalog read through XCTest, where they agree with its own records in all 119 captures
  ([`verification/accessibility/`](https://github.com/3nchiridion/foldsmith-evidence/tree/main/verification/accessibility)).
- **Seven-pose matrices, set against Apple's own apps.** Each pattern is captured in all seven poses
  ([the matrices](docs/images/matrices/)), and three of the four are compared with the Apple app that does the same
  thing, in the poses Apple shows it in: Settings on the simulator (six poses); Fitness (two), Podcasts and Accessibility
  Reader (three) in Apple's tech-talk frames. Where they differ is written down ([`verification/oracle/`](https://github.com/3nchiridion/foldsmith-evidence/tree/main/verification/oracle)).
- **Three real migrations.** The skill adapted NetNewsWire and IceCubesApp (five screens each, logged out for
  IceCubesApp, verified in every pose; a detector added after NetNewsWire's run finds its Reader View button beside the
  vertical bar in 8 cells, not fixed) and ran on Wikipedia, which did not pass review (2 of 11 screens; 15 confirmed
  items left unfixed, two of them medium regressions, all listed). Each has the detectors' findings before and after,
  the report and the patch ([`verification/runs/`](https://github.com/3nchiridion/foldsmith-evidence/tree/main/verification/runs)).

<p align="center">
  <img src="docs/images/split-aligned-book.png" alt="The catalog's Fold-aligned split on the iPhone Duo simulator, folded like a book: a list in the leading half and the article in the trailing half, the boundary on the fold" width="600">
  <br>
  <sub>The catalog's Fold-aligned split in book pose, captured on the iPhone Duo simulator: the boundary on the fold.</sub>
</p>

## Install
In a Claude Code terminal session, for the pane and `/foldsmith-start` (in the desktop app: + next to the prompt box,
then Plugins, Add marketplace `3nchiridion/foldsmith`):

```
/plugin install foldsmith --marketplace 3nchiridion/foldsmith
```

In Codex, Cursor, GitHub Copilot, Gemini CLI or any agent that reads Agent Skills, for the skill alone:

```
npx skills add 3nchiridion/foldsmith
```

Either needs macOS with Xcode 27.1 and an iPhone Duo simulator ([Requirements](#requirements)). More ways in:
[the plugin, step by step](#installing-the-plugin) and [other agents](#other-agents).

## Start here
| You want to | Go to |
|---|---|
| adapt your app with Claude Code | [Hands-free migration](#hands-free-migration-with-claude-code) below, and [the plugin's README](plugins/foldsmith/README.md) |
| copy a layout into your app | [`Sources/Patterns/`](Sources/Patterns/): one copy-in Swift file per pattern (to keep Fold-aligned split's two panes upright too, copy `FoldAlignedTiledSplit.swift` with `FoldAlignedSplit.swift`) |
| read a pattern: when to use it, what it does in each pose, and why | [Fold-aligned split](patterns/fold-aligned-split.md), [Even grid](patterns/even-grid.md), [Arrangement](patterns/arrangement.md), [Reflowing columns](patterns/reflowing-columns.md) |
| find which pattern a screen needs | [the decision table](patterns/DECISION-TABLE.md) (and the defect classes in [the taxonomy](patterns/TAXONOMY.md)) |
| check a claim | [`EVAL.md`](EVAL.md) (the gates and where each stands), [`verification/`](https://github.com/3nchiridion/foldsmith-evidence/tree/main/verification/) (the captures, the comparisons with Apple's apps, the three migrations) |
| see how it was built | [`docs/history/`](docs/history/) (the working log, every departure from the plan, the first plan) |

## Status
On 2026-10-29: four patterns, each with a reference implementation, a pose matrix captured in all seven poses and
detector results. Three of them, Fold-aligned split, Even grid and Arrangement, are compared with Apple's apps:
Settings captured on the simulator, and Fitness, Podcasts and Accessibility Reader in frames from Apple's tech talk
111463, renders that show two or three poses (`EVAL.md` §7 has the gates and where each pattern differs from Apple's
app). The fourth, Reflowing columns, has no Apple app to compare with yet.

The plugin's skill was run on three open-source apps ([`verification/runs/`](https://github.com/3nchiridion/foldsmith-evidence/tree/main/verification/runs/)): IceCubesApp's five logged-out screens
and NetNewsWire's five are verified in every pose (a detector added after NetNewsWire's run finds its Reader View
button in 8 cells, not fixed); Wikipedia's run finished 2 of its 11 screens and did not pass review: 15 confirmed
items are left unfixed, two of them medium regressions. The detectors read any app through its accessibility tree.

## Hands-free migration with Claude Code
Install the `foldsmith` plugin, open your app's folder in Claude Code, and run `/foldsmith-start`. The bundled
`foldsmith-duo` skill takes the whole app from audit to verified without stopping to ask: it finds the screens,
captures each in all seven Duo poses, applies the catalog's patterns, and proves every pose with before/after shots.
It commits one screen at a time on a `duo-migration` branch, never pushes, and keeps `.duo/migration.json` current,
so a later session resumes where it stopped.

A pane beside the chat follows it: the live simulator, the screen × pose matrix, before and after for any screen and
pose, and what is done and what is left.

<p align="center">
  <img src="docs/images/foldsmith-pane.svg" alt="The Foldsmith pane's matrix: four screens (Inbox, Message, Compose, Settings) against the seven iPhone Duo poses and Split View's half, each column headed by a pose icon, with cells colored for defect found, pattern proposed, migrated, verified, fine as is, or not captured" width="668">
  <br>
  <sub>The pane's matrix, from <code>/foldsmith demo</code> sample data. It follows the system's light or dark mode.</sub>
</p>

### Requirements
- macOS with Xcode 27.1 and the iOS 27.1 simulator runtime;
- one iPhone Duo simulator, for example `xcrun simctl create "iPhone Duo" com.apple.CoreSimulator.SimDeviceType.iPhone-Duo
  com.apple.CoreSimulator.SimRuntime.iOS-27-1`;
- [xcodegen](https://github.com/yonaskolb/XcodeGen) (`brew install xcodegen`), which generates the tap runner's, the
  catalog's and the probe's Xcode projects;
- Claude Code 2.1.308 or later (tested with 2.1.308; 2.1.236 and older reject the plugin's hooks), so run
  `claude update` first;
- the [iphone-duo-simulator-skill](https://github.com/WhitenWhiten/iphone-duo-simulator-skill) driver (`duo.py`),
  which the skill fetches at a fixed commit into `~/Library/Caches/duo-driver` when it is missing.

### Installing the plugin
At the prompt of a Claude Code terminal session:

```
/plugin install foldsmith --marketplace 3nchiridion/foldsmith
```

Answer `y` to add the marketplace, then pick a scope. From a shell:

```
claude plugin install foldsmith --marketplace 3nchiridion/foldsmith
```

If `--marketplace` is not offered, Claude Code is older than 2.1.308: run `claude update` first.

In the desktop app, where `/plugin` does not run: click + next to the prompt box, then Plugins, Add marketplace with
`3nchiridion/foldsmith`, then Add plugin. Run `/foldsmith demo` to preview the pane with sample data.

### Other agents
The skill, `foldsmith-duo`, needs no Claude Code: its tools are shell, Python and Swift, and its progress file is plain
JSON. Only the pane and `/foldsmith-start` are Claude Code's. From a shell:

```
npx skills add 3nchiridion/foldsmith                     # asks which agents; -g installs for every project
gh skill install 3nchiridion/foldsmith foldsmith-duo     # GitHub CLI 2.90 or later
```

Or copy `skills/foldsmith-duo/` by hand into one of:
- `~/.claude/skills/` (every project) or `.claude/skills/` in your app: Claude Code;
- `.agents/skills/` in your app, or `~/.agents/skills/`: Codex, GitHub Copilot, Gemini CLI, OpenCode, Amp, Cursor;
- `.cursor/skills/` in your app, or `~/.cursor/skills/`: Cursor.

Then ask your agent to adapt the app for iPhone Duo. Codex can also install the plugin from this repository, whose
`.claude-plugin/marketplace.json` it reads: `codex plugin marketplace add 3nchiridion/foldsmith`, then
`codex plugin add foldsmith@foldsmith`. Only the skill comes through: Codex skips the pane's hooks file with a startup
warning, and leaves out `/foldsmith-start`, whose prompt takes an argument (worked out from Codex 0.166's source; not yet
tried end to end).

## Build and test
With Xcode 27.1 and xcodegen:
- `swift test`: the detectors on the committed captures' frame records and accessibility snapshots (`Tests/Fixtures/`,
  G3), and the tests that hold each pattern to its captures;
- `swift run duo-detect <dir>`: the detectors on a folder of frame records or accessibility snapshots;
- `python3 scripts/sync-skill-references.py --check`: the skill's generated references match their sources (run it
  without `--check` after editing `patterns/`, `Sources/` or `SKILL.md`);
- `cd Examples/Catalog && xcodegen generate && open Catalog.xcodeproj`, then run the catalog on the iPhone Duo
  simulator;
- `gh workflow run ci.yml -f goldens=true`: G2, every config captured in every pose and compared with the goldens in
  [foldsmith-evidence](https://github.com/3nchiridion/foldsmith-evidence) (locally: check it out beside this repository, or set `FOLDSMITH_EVIDENCE`).

## Repository map
| Folder | What it holds |
|---|---|
| `patterns/` | the pattern pages, the decision table, the defect taxonomy, and how the patterns were chosen (`CLUSTERING.md`) |
| `Sources/Patterns/` | the reference implementations, one copy-in file per pattern |
| `Sources/DuoDetectors/`, `Sources/duo-detect/` | the pose model and the detectors (T1, T2, T4, T5, T7, T10, T14, T15: the defect classes in `patterns/TAXONOMY.md`), for the catalog's records or any app's accessibility tree: `swift run duo-detect <dir>`; `Package.swift` at the root builds them |
| `Sources/DuoPoseTesting/`, `Tests/` | a harness for app tests, and the tests that hold the patterns to their captures (their frame records, accessibility snapshots and the three runs' progress files in `Tests/Fixtures/`) |
| `Examples/Catalog/` | the catalog app: each reference beside the defect it fixes; the pose matrices are captured from it |
| `plugins/foldsmith/` | the plugin: the skill, `/foldsmith-start`, and the pane |
| `skills/foldsmith-duo/` | the skill on its own: `SKILL.md`, its references (generated from `patterns/`) and tools |
| [foldsmith-evidence](https://github.com/3nchiridion/foldsmith-evidence) | the evidence, in a repository of its own: `verification/` (`matrices/`, the goldens; `oracle/`, against Apple's apps; `accessibility/`, the catalog read through XCTest; `runs/`, the three migrations; `ab/`, a blind A/B, set aside) and `raw/` (notes on Apple's talks and docs, SDK notes, measured metrics, screenshots of Apple's and the corpus apps, developer questions, the corpus manifest and defects) |
| `scripts/` | capture (catalog, corpus apps, Apple apps), matrix compose and diff, the progress file, skill sync, redaction |
| `Probe/`, `Tap/` | DuoProbe, which logged each pose's geometry; DuoTapUITests, which taps an app on the shut Duo and holds it while the host folds and shoots |
| `docs/` | `history/` (the working log `STATUS.md`, `DEVIATIONS.md`, the first plan `MAC-PHASE.md`) and images (`images/matrices/`: each pattern's pose matrix, small) |
| `.claude-plugin/` | `marketplace.json`: this repository as the Claude Code marketplace `foldsmith`, listing its one plugin `foldsmith` |
| `.github/workflows/` | `ci.yml`: the detector tests and builds (G1, G3) on pushes to main and on pull requests; G2 on manual dispatch |

`EVAL.md` at the root is the pre-registered contract: the gates, the rubric, and in §7 where each gate stands.

## Contributing
A problem with the plugin: open an issue with the app, the pose and its `.duo/migration.json`. A corpus app or a
migration case study goes to [foldsmith-evidence](https://github.com/3nchiridion/foldsmith-evidence): the corpus app's repository and commit in `raw/corpus/manifest.txt`
and its findings in `raw/corpus/defects.csv`, with evidence under `raw/corpus/evidence/<app>/`; a case study as a
`verification/runs/<app>/` folder like the three there (README, REPORT.md, audit.md, migration.json, the patch with its
licence). Edits to `patterns/` or `Sources/` need `python3 scripts/sync-skill-references.py` rerun.

## License
MIT (`LICENSE`) for everything here, code and text. The iPhone Duo photo at the top is Apple's, shown from Apple's
developer page and not stored here. The third-party material is in [foldsmith-evidence](https://github.com/3nchiridion/foldsmith-evidence), each piece with its licence
beside it: Microsoft's sources (MIT), three patches that keep their projects' licences (IceCubesApp's AGPL-3.0,
Wikipedia's and NetNewsWire's MIT), and screenshots of other apps, which belong to their owners.
