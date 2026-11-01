# The independent review

A run does not review its own change. In both NetNewsWire runs every regression left at the end was found by a
reviewer who had not made the change, after the run had passed its own checks; on Wikipedia each such review found
regressions the run had passed, among them state restoration and theming broken on every iOS 27.1 device
(foldsmith-evidence, `verification/runs/`). This page is that review. Step 6 of the skill gives it to a fresh
subagent; `/foldsmith-review` runs it in a new session. It changes no code, commits nothing and switches no branch.

## What the reviewer gets
- The app folder and the base: the commit `duo-migration` started from, which one line of the progress file's log
  names (`branch duo-migration from <commit>`: look for that line alone); for a run that did not log it,
  `duo-baseline` when the repository has it, else `git merge-base duo-migration <default branch>`.
- The diff: `git diff <base>..duo-migration -- . ':(exclude).duo'` and `git log --format='%h %s' <base>..duo-migration`.
- The captures: `.duo/captures/<app>/before/` and `after/`, each cell's shot (`<screen>-<pose>-cover.png` on the
  closed poses, `-inner.png` on the others), its accessibility snapshot (`<screen>-<pose>.json`), the detectors' table
  (`detectors.md`) and `capture.txt`.
- The cells: `python3 tools/progress.py show`, `check` and `controls`.
- Not the run's conclusions. `.duo/REPORT.md` (in a run, a draft without its review section, which the run adds
  after this review), `.duo/audit.md`, `.duo/PLAN.md`, the done lines and the rest of the log are read only at the
  last step, to check them. A subagent is given this page by its path (its skill folder holds the `tools/` to run),
  the app folder and the base, nothing else.

The review needs no simulator. Where only a shot settles a claim, probe into a scratch folder (`simulator.md`, "Probe
first, capture once"), never into `before` or `after`, and never beside a running capture (`.duo/.capture.lock`); a
probe needs the preflight run and `source .duo/env` first, like any capture.
Measure from the snapshots (frames in points) and the code: a contact sheet hides 84 pt.

## The checklist, in this order
1. **Controls that left the screen.** `python3 tools/progress.py controls` lists every control a cell's before snapshot
   has and its after snapshot lacks, and the `moved` record that covers it, if any. Check each record's evidence: a
   `shot` is an after or probe snapshot of that cell (`<screen>-<pose>.json`; `moved` refuses another pose's) that has
   the control, or its `--as` label, one the before snapshot lacks; a `code` line, of a file git tracks, must put that
   control there in that pose (a `menuRepresentation`, `additionalOverflowItems`, a menu), on a path the pose takes. A
   gone control with no record, or with evidence that does not hold, is a regression. Count the taps each moved control
   now costs, and look for actions that lived only on it: NetNewsWire's Find in Article was only in the article's own
   share sheet, so Share gone from the upright article pane left it no proven route.
2. **Each changed pose against its panes' edges.** For every cell whose snapshots differ, take each pane's frame from
   the after snapshot (its navigation bar, its list) and check each control and row against the pane's edges and the
   fold's band (`metrics.md`): nothing past an edge, nothing fixed across the fold, no text cut off or broken mid-word
   (the shot), no pane's content stopping short of its edge (Wikipedia's search field ended at 371 of 455 pt).
3. **Routes and walks.** `bash tools/routes.sh <app folder> <types the diff changes>`, and the keyboard commands, which
   it does not list (`rg -n "UIKeyCommand|keyCommands|keyboardShortcut"`). Follow each line through the changed code:
   every walk of the hierarchy (`as? UINavigationController`, `selectedViewController`, `presentedViewController`,
   `viewControllers`), state restoration, user activities (Handoff, Spotlight, Siri), deep links, notifications, quick
   actions, keyboard commands. Ask of each: does it reach the screen it reached before, in every pose, with what it
   carried (a selection, a search, the open item)? Does every state that follows a screen follow it still (a pane
   showing one article's contents after another opens)? A view the diff lays over another must hide what it covers
   from accessibility.
4. **Sheet routes and their placement.** Every sheet among the `present` lines `tools/routes.sh` lists (UIKit
   `present(` of a page or form sheet, SwiftUI `.sheet(`), nested sheets included (a sheet presented from a sheet):
   each sets the trailing placement while a vertical division is active (`preferredPlacement = .trailing`,
   `.presentationPlacement(.trailing)` or `foldAwareSheetPlacement()`). NetNewsWire's rerun left about a dozen nested
   routes without it while its report said "every sheet".
5. **Transient messages on the fold.** Every centred message a pane draws while it has nothing else to show: loading,
   empty, error, "No selection". Find them (placeholder views, `ContentUnavailableView`, a web view's message styles)
   and check each sits off the fold in laptop and tent (y 455.5–495.5 pt). Most are never captured: read the code.
   NetNewsWire's "Loading…" kept a style at 45 % of the pane's height, on the fold, after "No selection" was moved.
6. **The project's toolchain.** `python3 tools/sdkguard.py <app folder> --base <base> --scheme <scheme>`. The lines
   it counts as not compiling (a symbol, or a name declared only inside the guard) mean the branch does not build with
   the Xcode the project's CI uses: high, a regression. An availability check outside the guard compiles, but on a
   build with the CI's Xcode it opens the iOS 27 branch without the guarded code: judge it by what that branch skips,
   a regression (medium or high by the action) when an `else` or fallback, the pre-Duo code, no longer runs on iOS 27
   devices, otherwise low. Either way it is fixed by moving the check inside `#if compiler(>=6.4)` with the code it
   guards. With the CI on exactly Xcode 27.0, exit 1 on 27.1 symbols means the run is blocked on the CI, not a
   regression it can close: check the run proposed moving the CI to 27.1 in `.duo/PLAN.md`, and record it as an issue
   without `--regression`. Each waived line it lists, and its why. A verdict that no CI Xcode is named: look at the
   CI files yourself for one it did not read. It does not follow a guarded enum case written `.name` into another file,
   or a guarded member used outside its own type where another type's extension has the name: search those yourself.
   Where an installed Xcode matches the CI's, the build line it prints, and its result.
7. **Behaviour without a fold.** Each change runs only on the condition it needs (a vertical bar, a reserved region) or
   is the path the app already takes on iPhone; nothing branches on device, idiom or orientation; a Mac Catalyst,
   visionOS or macOS target that shares the code still compiles. A change on an iPhone or iPad without a fold is a
   regression unless the report says what it is and why.
8. **The project's contribution rules.** `CONTRIBUTING*`, the coding guidelines, `.swiftlint.yml`, `.swift-format`, the
   pull-request template: commit subjects in the project's style, property order and file layout as its guidelines
   say, no new warning. `git ls-files .duo` prints nothing (`.duo/` is never committed), and every commit the progress
   file or `.duo/PLAN.md` cites is on the branch (`progress.py check` refuses one that is not).
9. **Last, the claims.** Now read `.duo/REPORT.md` (in a run, the draft without its review section), `.duo/audit.md`,
   `.duo/PLAN.md`, the done lines and the log, and check each claim against items 1 to 8 and the evidence: the counts
   against `progress.py show`; "verified in every pose" against the cells (`unchanged` is not `verified`); each moved
   control's place and its evidence kind (an overflow read from code was not opened); "every sheet" against the routes;
   the toolchain line against sdkguard's verdict; what "not done" leaves out. A claim wider than its evidence is a
   finding.

## What it reports and records
- Each finding: what happens, the poses, the evidence (`file:line`; the snapshot's path, the element's label and
  frame), the severity, regression or not (worse than at the base), and confirmed or refuted.
- Before recording one, try to refute it: read the code path again, look at the other poses' snapshots and the shot.
  Keep what survives (NetNewsWire's rerun review: 18 raised, 9 confirmed, 3 merged into others, 6 refuted).
- Severity, as the NetNewsWire reviews graded it: high for a branch that does not build with the project's CI, or a
  common action that breaks the screen (Mark All as Read bringing up an empty column); medium for an action or control
  with no route left (Share off the upright article pane), or state a route loses (Back closing the article); low for
  one more tap, a transient message on the fold, a redundant load.
- The reviewer records each confirmed finding: `python3 tools/progress.py issue add <screen> <pose,…|all|inner|->
  <high|medium|low> "<what happens>" --found-by review --where <file:line>`, with `--regression` for anything worse
  than at the base. A regression recorded once the phase is `done` sets it back to `verify`.
- Then the review itself: `python3 tools/progress.py review <subagent|session> "<n raised, n confirmed, n
  regressions; what it covered>"`, which keeps the code identity it saw (`check` notes when the code has changed
  since). A session that cannot start a subagent records `review none "<why>"`; its report and closing message then
  tell the person to run `/foldsmith-review` in a new session before merging.
- After a subagent's review the run fixes each confirmed regression, or reverts the change that caused it, and
  captures the screens again (step 6). `/foldsmith-review` fixes nothing: it appends `## Independent review (<date>)`
  to `.duo/REPORT.md`, with the confirmed findings and their issue ids and the refuted ones with why, and with
  regressions recorded says that `/foldsmith-start` resumes and fixes them.
