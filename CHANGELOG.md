# Changelog

Versions of the repository, as tagged, and from 0.8.1 the versions of the Claude Code plugin, which carries its own
version in `plugins/foldsmith/.claude-plugin/plugin.json` (0.6.0 to 0.8.0 are described in their commits).

## Plugin 0.8.2 — 2026-11-02
The Claude directory's check of 0.8.0 held the plugin for an invisible character: a zero-width space written as itself
in `hooks/register.tsx`.

- **The pane's code** writes that zero-width space as `\u200B`, as the line below it does; what the pane draws is
  unchanged.
- **A new test**, `scripts/test_text.py`, refuses an invisible character in any text file the repository tracks: format
  characters (zero-width spaces and joiners, bidirectional controls, byte-order marks), control characters other than
  tab and newline (a carriage return among them), spaces other than the plain one, line and paragraph separators,
  private-use characters, variation selectors, and the letters and marks Unicode lets a reader ignore (Hangul fillers
  among them); a tracked file that is not UTF-8 must be a PNG. `.github/TOPICS.md` loses the one it had.
- **The skill** words its rule as "never sign in or type login details" (it said "credentials"), in `SKILL.md` and
  `references/simulator.md`; the rule is the same. `references/simulator.md` no longer names the source NetNewsWire's
  first build generates. These were the likeliest matches for the same check's three credential findings, which do not
  say what they matched.

## Plugin 0.8.1 — 2026-11-01
What the NetNewsWire rerun with 0.8.0 showed was still broken: the branch did not build with the project's CI, the
upright article pane lost Share, Previous and Next with nothing to show where they went, the gate passed a `verified`
cell that kept its old finding and done lines that said more than the cells, a cited commit had been amended away,
after shots came from code older than the final commit, the run committed its own `.duo/` files against the project's
rules, and the independent review was skipped because the session could not start a subagent.

- **The migration's commits.** The migration never commits `.duo/`: the preflight puts `/.duo/*` in
  `.git/info/exclude` (it used to add `/.duo/env` only), so commits carry app code only and the branch can become a
  pull request. It reads the project's contribution rules first and follows them (default commit subject: a
  present-tense verb, `Adapt the timeline and article to iPhone Duo (Fold-aligned split)`, no more `Duo:`), makes its
  branch with `git switch -c duo-migration --no-track`, logs the commit it started from, and never amends or rebases a
  commit once it is cited. The report says what the project asks of a pull request; none is opened.
- **The project's toolchain.** New `tools/sdkguard.py [<app folder>] [--base <rev>] [--scheme <name>] [--ci-only]`:
  the Xcode the repository's CI selects (GitHub Actions, `.xcode-version`, CircleCI, Bitrise, GitLab, Travis, fastlane,
  Makefile; Xcode Cloud's `ci_scripts/` named as set in App Store Connect), the installed Xcodes and the build line for
  the one that matches, and every iOS 27 availability check, curated iOS 27.0/27.1 symbol (53, each version read from
  the iOS 27.1 SDK), Foldsmith reference type, or name the branch declares only inside the guard (a helper, a member,
  a local, a property wrapper's `$x`, a type whose pre-Duo twin is in `#else`) added since the base and used outside
  `#if compiler(>=6.4)`. It reads GitHub matrices, variables (YAML, shell defaults, Makefile) and the scripts, Makefile
  and local actions a workflow runs, leaves comments out, and names a workflow that builds on a runner image's default
  Xcode instead of saying no Xcode is named. Declarations, argument labels, overrides, and locals or members that
  shadow a guarded name are not uses; the rules and the cases it does not follow are in its docstring and
  `references/simulator.md`. Its reading of uses was tested against swiftc with the guard forced false.
  CI below Xcode 27: each is an error (exit 1), the lines that do not compile and the availability checks counted
  apart; CI on 27.0: the 27.1 symbols are, guard or not (the run is then blocked on the CI: a proposal and an issue,
  not a regression); CI on 27.1 or none named: notes. `// sdkguard: ok <why>` waives a line from that line or alone on
  the line above, and every waived line is listed with its why. Every iOS 27 API and every reference type now goes
  inside `#if compiler(>=6.4)` with the pre-Duo code in `#else`, `#available` kept inside, and the report has a
  "Builds with the project's toolchain" line. `references/apple.md` has a Toolchain section: `#available` is a
  run-time check, Swift 6.4 ships in Xcode 27.0 and 27.1 (so no supported compile-time check separates them), and each
  API's version as the SDK declares it. `tools/README.md` gets a row for `sdkguard.py`.
- **The reference implementations** in `Sources/Patterns/` are each wrapped whole in `#if compiler(>=6.4)`, so a copy
  compiles to nothing on an older Xcode, and each pattern page shows its call site inside the same guard with the
  pre-Duo layout in `#else` (Fold-aligned split's UIKit snippet keeps Mac Catalyst out too, whose SDK has no reserved
  regions). A test checks each file stays wrapped whole, since `swift test` does not compile them.
- **The independent review is a step with a record.** New `references/review.md` (its inputs, a nine-item checklist,
  how findings are refuted, graded and recorded), `progress.py review <subagent|session|none> "<summary>"`, and the
  command `/foldsmith-review [app folder]`, which runs the review in a new session, records issues and the review,
  appends `## Independent review (<date>)` to `.duo/REPORT.md` and changes no code. `phase done` refuses with no
  review on record; a regression added after `phase done` sets the run back to `verify`. The run drafts
  `.duo/REPORT.md` before the review, so the review's last item checks its claims, and adds the review section after.
- **The gate** (`progress.py`) also refuses, for `done <screen>: …` and `phase done`:
  - a control gone from a cell (in its before snapshot, not in its after one) with no record of where it went:
    `progress.py controls` lists them, `progress.py moved` records where one went, with a snapshot of that cell that
    shows it (a shot proves only its own pose: the cover's says nothing about an inner pose's overflow), an `--as`
    label the before snapshot lacks, or a line of a file git tracks that puts it there (an inner pose's overflow
    cannot be opened by the tap runner); a record whose control is back is noted as no longer needed;
  - a `verified` cell whose after table keeps a class its before table had, and a `verified` or `unchanged` cell
    with a class before where no detector ran after;
  - a done line saying "verified in every pose" (or "all poses") when not every cell of its screens is verified,
    with the counts to write instead;
  - a cited commit (done lines, issues, moved records, PLAN.md's `made:` lines) that is not on the branch, naming the
    commit with the same tree or subject;
  - a `verified` or `unchanged` cell whose after shot was captured from other code than the code now (rebuild and
    install from the committed tree, then capture again; `waive … stale` with why where the changes cannot reach it,
    which holds until the next change outside `.duo/`), or whose after shot is missing from a folder that has a
    `.captured` (a capture stopped mid-screen removes the shot and its line).
  New `progress.py codeid` prints the code identity the captures record (git's diff settings and a growing object
  store do not change it); `show` adds the cell counts, every waiver, moved record and review. The stricter checks can
  refuse a progress file written before 0.8.1: NetNewsWire's and IceCubesApp's fixtures are refused for done lines saying "verified in every
  pose" over cells left unchanged, and for having no review; Wikipedia's is also refused for contents laptop, tent and
  flat-upright, marked verified with T7 still in the after table.
- **Captures carry the code identity.** `.captured` lines have it as a fourth field (`<flow sha256> <screen> <pose>
  <code>`), and `capture.txt` has a `code:` line. `RESUME=1` takes again every cell captured from other code, and
  never keeps a line written before 0.8.1. A capture without `RESUME=1` marks its cells' old lines `retaking` instead
  of deleting them, so a capture stopped early cannot hide stale after shots from the gate.
- **Preflight.** A warning when files under `.duo/` are tracked (with the `git rm -r --cached` fix, and why an
  earlier commit is not checked out in the app folder afterwards; it replaces the old tracked-`.duo/env` warning), a
  note when a remote `duo-migration` exists and no local one does, a warning when the local one tracks it (not when
  the person pushed the run's own branch), and a note with the CI's Xcode (`sdkguard.py --ci-only`). Where the
  project's own `.gitignore` ignores `.duo/`, its fixes name no exclusion.
- **Detectors.** T10 checks an item only in a bar that reaches the vertical bar's band: the sheet it sits in, else the
  narrowest navigation bar over it, else the window. Items go vertical only when their container sits on the
  display's edge, and in a split only the detail column's do [tt-111462 3:09]. A sheet away from that edge keeps a
  horizontal bar of its own: NetNewsWire's Add Feed centred open flat, or on the leading half in book (there its
  defect is the side, T15). Table change, NetNewsWire's Add Feed: before, book `T10 T15` → `T15` and flat-sideways
  `T10` → `·` (first run and 0.8.0 rerun); the rerun's after, flat-sideways `T10` → `·`. Wikipedia, IceCubesApp and
  the A/B baselines: no change. `patterns/TAXONOMY.md`'s T10 evidence says the same.
- **Fold-aligned split.** Bar items in the 328 pt upright detail (`visibilityPriority`, `menuRepresentation`; SDK API,
  not yet measured on a run); the sheet rule covers every sheet route, nested sheets included; every transient message
  (loading, empty, error) moves off the fold, not only "No selection"; six checks a `--structural` UIKit three-level
  change must pass, from the first NetNewsWire run's regressions.
- **References.** `LAUNCH_ARGS` quoting corrected: no quotes inside the value (the tap runner splits at each space and
  quotes reach the app as characters). New advice on apps that restore their last selection, a first build that fails
  on a generated source, zsh, and how `rg` is found. The skill's example done line no longer says "verified in every
  pose". A late fix is committed, rebuilt and installed before every screen `check` lists is captured again. The
  review subagent gets `references/review.md` by its path, so it finds the tools beside it.

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
