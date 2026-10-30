# STATUS — 2026-10-29 (the working log; Xcode 27.1 on the owner's Mac)

> The working log of the private repository this one was cut from (step 14, 2026-10-29). PR numbers, run ids and
> branch names refer to that repository and do not resolve here. The project was then named duo-kit and is now
> Foldsmith (`DEVIATIONS.md`, step 15); paths and names below are as they were.

Phase 1 is complete: all eight corpus apps are built and recorded. Phase 2 is merged (2026-10-26): taxonomy settled,
decision table filled, five patterns named. Phase 3 is merged (2026-10-27, PR 12): three pattern pages, their reference
implementations, the catalog app, pose matrices captured from it, and the detectors that check them. Phase 4 step 1
(A/B readiness) is merged (PR 13). The owner then set the A/B aside (2026-10-27): Phase 4 is now a hands-free migration
skill and plugin, proved on one corpus app (step 2, merged 2026-10-27, PR 15); steps 3–7 (faster captures, three
levels, detector gaps, the catalog's three levels, two panes upright in SwiftUI) are merged (PRs 16–20); step 8, the
skill on a second app, a SwiftUI one, is merged (PR 21); step 9, a third, UIKit with a web view, reviewed four times, is
merged (PR 22); step 10 makes the progress tool refuse a screen the detectors see got worse (PR 23); step 11 closes
what it can of the v0 gates G2 and G4 (PR 24), the owner having amended G4 to accept Apple's published frames where an
app is not on the simulator; step 12 builds Arrangement (P4), which the owner moved into v0 as its third pattern (PR
25). All merged 2026-10-29; `EVAL.md` §7 records where the gates stand. Step 13 prepares the repository for going
public, and step 14 published it as this repository (the last two sections).
`DEVIATIONS.md` is the authoritative record of every departure; this file is the summary.

## Done

### Cloud part (2026-10-24, no Xcode)
- `raw/apple-docs/` — six tech talks (chapter maps, API lists, published code, close paraphrase), the HIG article,
  the Technology Overview, SwiftUI and UIKit doc-page facts. Transcripts deliberately not stored verbatim.
- `raw/precedent/` — Microsoft's five dual-screen patterns and the TwoPaneLayout/WindowState/FoldableLayout
  source (MIT, pinned), Android canonical layouts, a first vocabulary mapping.
- `raw/complaints/` — Apple engineers' Group Lab answers (read in full; the last fifth on 2026-10-26), the 43-thread UIKit Q&A
  digest, 12 real-app issues/PRs, community-measured metrics, 10 seed defect classes.
- `raw/corpus/` — eight apps profiled; `manifest.txt` + `clone.sh`.
- `EVAL.md` pre-registration; `patterns/DECISION-TABLE.md` (inputs defined, cells empty), `patterns/TAXONOMY.md`
  (12 provisional classes), `patterns/TEMPLATE.md`; `skills/iphone-duo-patterns/SKILL.md` routing skeleton;
  `Package.swift` + `Sources/DuoPoseTesting` (three detector sketches, unit tests).

### Mac step 1 — SDK truth (merged, PR 1)
- `raw/sdk/DIFF.md`: every Duo signature and default checked against the 27.1 SDK. Headline mismatches: no
  `ToolbarVerticalEdge` type (`toolbarVerticalEdge` is `HorizontalEdge?`); `DeviceHinge.Status` is a struct with
  three static cases, UIKit's `UIHinge.Status` an enum with four; `ReservedRegion` is not
  `CustomStringConvertible`; `axisBehavior` takes `ToolbarItemAxisBehavior`; two `overlayArrangementEdge`
  overloads; `.prefersTabBar` and `presentationPlacement` undocumented in the notes.
- `raw/sdk/APPLE-SKILL.md`: Apple's `app-resizability` skill (Xcode 27.1) is a UIKit code-migration skill
  (UIScreen.main, orientation, scene lifecycle, safe area, idiom). It names no layout pattern. The catalog sits
  above it and must not duplicate it.
- `scripts/extract-sdk.sh` refuses SDKs below 27.1. Verbatim SDK and skill text is git-ignored.

### Mac step 2 — Probe (merged, PR 2)
- DuoProbe built and run on the iOS 27.1 Duo simulator; all 7 drivable poses. `raw/metrics.json`,
  `raw/metrics.jsonl` (72 samples), `raw/METRICS-NOTES.md`, screenshots in `raw/apple-apps/_probe/`.
- Pose set grew to 8 (tent added from the HIG). Split-view half cannot be driven headless; it is a unit-test
  size, not a simulator pose.
- Key numbers: inner window 951×669 / 669×951, cover 466×678; division 40 pt centred at 455.5, active only
  when part-folded; closed-sideways is compact/compact; first frame has no regions (they arrive in 0.1–0.3 s).

### Mac step 3 — Apple's apps as oracle (merged, PR 3)
- `raw/apple-apps/`: **2 of 11 apps captured** (Settings, Safari); the simulator runtime ships no others.
- Settings moves its split boundary onto the active vertical fold in book; Safari ignores every fold; neither
  follows the HIG's laptop advice; neither draws a vertical bar on the inner display.

### Mac step 4 — Corpus (pilot merged, PR 4; continuing)
- `raw/corpus/BUILDS.md`, `raw/corpus/defects.csv`, `raw/corpus/evidence/<app>/`.
- Pilot: 3 of 8 apps, launch screen only. Three defects, one per app, none yet seen in a second app:
  NEW-1 2048 traps at launch (no scene lifecycle, rebuilt with SDK 27.1); NEW-2 NetNewsWire's book split sits
  at ≈323 pt, off the fold; NEW-3 IceCubes' Add Account sheet lands on the leading half in book.
- home-assistant/iOS (A/B set): built with ad-hoc signing (the unsigned build traps on its app-group entitlement);
  5 screens × 7 poses (launch, servers, manual URL sheet, empty Connect, Learn more sheet). Findings: `T1` on
  three screens (welcome content, server cards and floating button, the manual-entry Connect button all cross an
  active fold); `NEW-3` on both sheets (placed on the leading half in book, centred when the fold is inactive).
  NEW-3 is now in two apps (IceCubesApp, Home Assistant), which meets the taxonomy's admission bar; T1 is in one
  app and in Apple's guidance.
- Tap path: `Tap/DuoTapUITests` + `scripts/capture-corpus-flow.sh` (XCTest taps the shut phone, duo.py folds and
  shoots). Xcode's device-interaction tools were abandoned (DEVIATIONS.md).
- wikipedia-ios: built the same way (README's team xcconfig, then ad-hoc signing); 5 screens × 7 poses. Findings:
  `T5` for the article and Settings (one column across the whole inner display in book), `T1` on every screen in
  laptop/tent, `NEW-4` (the turned cover's vertical bar compresses the tab bar to one tab on Explore), `T6` (onboarding
  image over its link in compact height). The reader pattern is now measured: a 690–740 pt text column over the fold.
- Signal-iOS: needs Xcode's Metal Toolchain component, then ad-hoc signing (third app with the app-group trap).
  Only the registration flow is reachable (no SMS on the simulator): 5 screens × 7 poses. `NEW-3` on its restore
  sheet (now three apps), `T1` on the splash, permissions and phone screens in book; the registration screens do
  not rotate on the turned cover. The custom-tab-bar hazard it was picked for stays untested.
- kickstarter/ios-oss: builds with the README's mock-data setup and fails to launch on the 27.1 SDK (`UIScene life
  cycle is required`), the second app after 2048 for `NEW-1` and a maintained one. Its custom floating tab bar,
  the hazard it was picked for, cannot be measured without the scene-lifecycle migration.
- firefox-ios: builds with its README setup and runs unsigned; 6 screens × 7 poses. `T3` on the cover (its own
  toolbar stays horizontal where Safari's goes vertical), the first corpus evidence for that class; `T1` for the
  address field and tab-tray control in book and text in the laptop fold; `NEW-3` on its menu and Settings sheets
  (fourth app).
- Step 4 is complete for all eight apps. Optional: deeper screens for NetNewsWire and IceCubesApp, only if Phase 2
  shows a gap they would fill.

## Phase 2 — clustering and the decision table (merged 2026-10-26, PR 10)
- Citation rule amended before any pattern was named: Apple's published guidance in `raw/apple-docs/` now counts
  (EVAL.md §5, DEVIATIONS.md). The rest of the Group Lab thread read (R1–R23 in `raw/complaints/README.md`).
- Two corrections first (`patterns/CLUSTERING.md §1`): the fold band is 455.5–495.5 pt, not 435.5–475.5; and scrolling
  content crossing the laptop fold is Apple's prescribed behaviour, not a defect. 49 rows → 29.
- `patterns/TAXONOMY.md` settled: admitted T1 crease-straddle (5 apps), T3, T5, T13 no-scene-lifecycle (was NEW-1),
  T14 columns-off-fold (NEW-2 + Wikipedia's grid), T15 sheet-in-book (was NEW-3, 4 apps); eight classes named by Apple
  with no corpus evidence; NEW-4 provisional; T6 out of scope.
- `patterns/DECISION-TABLE.md` filled: pose rows from the metrics; 88 cells, 79 cited, 9 `UNJUSTIFIED` (tent editing
  and controlling, editing continuous content across the fold); five patterns named: Fold-aligned split, Reflowing
  columns, Even grid, Arrangement, Whole object; four places where Apple's sources disagree, with the choice made.
- Recommended for v0: Fold-aligned split, Even grid, Reflowing columns.

## Phase 3 — the v0 patterns (merged 2026-10-27, PR 12)
- Reference implementations in `Sources/Patterns/`, one copy-in file each: `FoldAlignedSplit.swift`,
  `EvenGrid.swift`, `ReflowingColumns.swift`. They build against the 27.1 SDK with no warnings in our code (G1).
- `Examples/Catalog`: hosts each reference next to "before" variants that reproduce corpus defects (a fixed 320 pt
  sidebar, an adaptive grid, one wide column, a sheet left to automatic placement), and records every tracked view's
  window frame and the regions it saw.
- `scripts/capture-catalog.sh`: nine configs × seven poses → `verification/matrices/<pattern>/` (shot + frame record);
  `scripts/compose-matrix.py` → `verification/matrices/<pattern>.png`.
- Detectors made real (`Sources/DuoDetectors/Detectors/`, split out of `DuoPoseTesting` so `duo-detect` links without the Testing framework): T1 crease-straddle, T5 stretched-single-column, T14
  columns-off-fold, T15 sheet-in-book (T2, T4 kept). `swift run duo-detect verification/matrices`;
  `MatrixTests` makes `swift test` the gate: references clean in all seven poses, each "before" variant shows its
  defect and nothing else (G3 for the patterns).
- What the measurements changed: the system's `NavigationSplitView` already splits at the fold in book, and any set
  sidebar width turns that off, so P1 sets none; P1 cannot show two panes upright the way Settings does (SwiftUI
  overlays its sidebar at 669 pt; logged as a shortfall in the decision table); T5's threshold redefined; T15's defect
  is the side, not the edge.
- Pattern pages: `patterns/fold-aligned-split.md`, `even-grid.md`, `reflowing-columns.md`.
- Skill: `references/` filled (`apple.md`, `simulator.md`, `detectors-static.md` by hand; the rest generated by
  `scripts/sync-skill-references.py`, checked in CI).

## Phase 4, step 1 — A/B readiness (merged 2026-10-27, PR 13)
- Detectors for any app: `Tap/DuoTapUITests` dumps the app's accessibility tree once the host has the phone in the pose
  (`capture-corpus-flow.sh` with `SNAPSHOT=1`); `Sources/DuoDetectors/AccessibilitySnapshot.swift` maps it to the
  detectors' elements by stated rules; `duo-detect` reads either kind of capture. Checked against ground truth: the
  catalog captured both ways in all 63 config × pose cells gives the same classes (`AccessibilityTests`).
- `scripts/capture-poses.sh` (named in EVAL.md §4): one A/B app, every pose, fixed settle times, frozen flows in
  `verification/ab/flows/`, shots + snapshots + `detectors.md`.
- `verification/ab/`: `PROTOCOL.md` (how the six runs are done; four owner decisions marked), `INSTRUCTIONS.md` (rater
  instructions, frozen at recruitment), `RECRUITMENT.md` (draft for the owner to post); `scripts/ab-blind.py` (random
  ids, shuffled items, the key sealed by its SHA-256) and `scripts/ab-score.py` (sheets → `RESULTS.md`).
- The skill runs outside this repository: `skills/iphone-duo-patterns/tools/` carries the capture scripts, the tap
  runner and the detectors (generated, checked in CI); `references/simulator.md` says how to use them.
- Baselines (`verification/ab/baseline/`): the three apps unmodified through the frozen flows, 77 shots with snapshots.
  18 findings, 11 on screen (Home Assistant T1/T5/T15, IceCubesApp T15, NetNewsWire T14/T15), 7 on covered elements;
  two misses seen only in the shots (an out-of-process Safari sheet, text in a scroll view too short to scroll).

## Phase 4, step 2 — hands-free migration (merged 2026-10-27, PR 15)
- Scope changed by the owner (`DEVIATIONS.md`, 2026-10-27): Claude only; the blind A/B (G5) is set aside; v0 is the
  patterns, the harness, the hands-free skill and plugin, and one corpus migration with them.
- Skill: `skills/iphone-duo-patterns/SKILL.md` goes from one prompt to a report without asking anything: it finds the
  screens and writes a flow file, audits every screen in every pose, classifies, applies the pattern, recaptures and
  verifies, and writes `.duo/REPORT.md`. A problem goes to `todo` and the run moves on. One commit per screen on a
  `duo-migration` branch in the app's repository; it never pushes. `tools/capture-app.sh`: a flow file to shots,
  snapshots and `detectors.md` in one command.
- Plugin `plugins/duo-migration` 0.3.0 bundles the skill (a generated mirror, checked by
  `sync-skill-references.py --check`), `/duo-start` (the hands-free prompt; it resumes from `.duo/migration.json`, and
  takes an app folder) and the pane. The pane follows the newest progress file under the session's folder (or the one
  picked; an App picker when there are several) and shows: the status, totals, the simulator live every 4 s while the
  pane is on screen (paused for a finished run), the screen × pose matrix with each cell's classes in its tooltip, the
  picked cell's state, classes and the skill's reason, its before and after with the fold drawn (active band, dashed
  when flat), Previous / Next / Next defect, Left and Done (one line each, full notes on demand), the activity newest
  first, and Resume migration, Open report, Show captures. Nine plugin tests (`claude plugin test`); the owner
  checked it in the Claude app on the NetNewsWire run (2026-10-27).
- First run, NetNewsWire (`verification/runs/NetNewsWire/`: report, audit, progress file, patch; the shots stay
  outside): one prompt, no questions, about 1 h 45 min. Five screens found, all Fold-aligned split. Timeline, article,
  settings and Add Feed verified in all seven poses (G3 for a corpus app); feeds left in `todo` (T7: unfolding from the
  feeds list shows an empty timeline beside "No selection"; three levels, and P1 describes two). Detectors 3 → 0
  findings; the rest were seen in the shots. The UIKit split now tiles two panes upright, which the SwiftUI reference
  cannot.
- Fixed from the run: reference implementations ship beside the pattern pages (they linked to this private
  repository); a UIKit section on the P1 page; static scans T10, T13, T14; `tools/progress.py` keeps the progress file
  and `capture-app.sh` fills each cell's shot as it lands, so the pane follows a capture; one commit per change; the
  tap runner builds outside the skill; probe before a full capture.

## Phase 4, step 3 — faster captures (merged 2026-10-27, PR 16)
- Where a cell's time went (one book cell of NetNewsWire, measured): 8 s folding shut, 17 s priming the app's
  orientation, 24 s starting the test run, 21 s launching and tapping, 13 s posing, shooting and the snapshot.
- `scripts/capture-corpus-flow.sh` now starts one test run per screen. The tap runner taps once and holds the app;
  for each inner pose the phone is shut again, `scripts/same-screen.py` compares the shut screen's accessibility
  snapshot with the one right after the taps (NetNewsWire: other screens 0.14–0.28, the same screen 0.82–1.00;
  threshold 0.6), and only when it differs does the runner relaunch and tap again (a new `again` request), with a
  line saying the shut phone lost the screen: evidence for T7. A cover left landscape after laptop or tent is turned
  away and back first, as for a shot of the wrong shape. `FRESH=1` relaunches before every inner pose.
- Result on NetNewsWire's installed build: 14 cells (feeds and article, every pose) in 376 s, about 27 s a cell, against
  about 65 s; the full 35 cells would take about 16 minutes instead of 38. Feeds' shots match the run's `after` shots
  (0.00 % of pixels differ on the inner display, under 0.4 % on the cover); timeline and article show the same layout
  with that day's articles.

## Phase 4, step 4 — three levels (merged 2026-10-28, PR 17)
- The owner's decision: for a sidebar, list and detail hierarchy the unfolded phone shows two panes, the sidebar beside
  the detail when unfolded from the sidebar, the list in its place once an item is picked. Written into P1 (SwiftUI: a
  two-column `NavigationSplitView` with a `NavigationStack` in the sidebar column, not yet in the catalog; UIKit:
  "Three levels" in the page's UIKit section) and the skill's migrate step.
- NetNewsWire's feeds screen done that way (`verification/runs/NetNewsWire/`, last commit): while the split is expanded
  on a display with a fold, the feeds list moves onto the timeline column's navigation stack and the primary column's
  stack holds an empty controller; the stacks go back when the split collapses. Two ways that fail are on the page: a
  zero-width timeline column (a UIKit assertion), and moving controllers between columns (the cover pops to the
  sidebar at its next rotation).
- Recaptured with step 3's capture: 35 cells in 915 s (about 26 s a cell), no screen lost on the way back to the shut
  phone, `duo-detect` 0 findings, every shot checked. NetNewsWire: five of five screens verified in all seven poses.

## Phase 4, step 5 — detector gaps closed (merged 2026-10-28, PR 18)
- The NetNewsWire run's misses, each now a rule with tests (`Sources/DuoDetectors`, 31 tests):
  - T14 on panes with no text: `PaneBoundaryOffFold` reads a split view's panes from their navigation bars; two bars
    side by side must meet inside the division (320.5 pt before, 475.5 pt after the migration).
  - T1 inside a web view: a scrolling container that holds one short item is a placeholder, not scrolling content.
  - T7: `StateLossOnFold`, across poses, in `duo-detect`: what stays on the shut phone's screen (bars, controls outside
    scrolling content) must still be on the inner display. Bar names alone are not enough: on the cover NetNewsWire's
    article screen reads "Feeds".
  - T10 at runtime: `StrandedHorizontalItem`, a text-shaped navigation-bar button outside the vertical bar's band.
- On NetNewsWire's before captures the detectors now find 26 findings, everything the run saw by eye; after, 0. On the
  A/B baselines they add T14, T1 and T7 on NetNewsWire's launch and timeline (the run's defects) and a first runtime
  T10, Home Assistant's welcome (Learn more, Connect) in closed-sideways; IceCubesApp's title menu is the bar's title
  and is left alone. T7 and T10 now have corpus evidence and move to the taxonomy's admitted table.
- The accessibility adapter's check against the catalog's frame records leaves T10 out (the records carry no bar items):
  it finds T10 in the catalog's demo sheets, whose Cancel and Add are text.

## Phase 4, step 6 — the catalog: three levels, and the demo sheet's symbols (merged 2026-10-28, PR 19)
- `Examples/Catalog` gains `split:three` and `split:three-list`: three levels (collections, articles, article) in two
  panes, a two-column `FoldAlignedSplit` whose sidebar column holds a `NavigationStack`, the empty detail's placeholder
  high in its pane. The New Item sheet's Cancel and Add are symbols now (T10).
- Captured with `scripts/capture-catalog.sh` (frame records, 4 configs × 7 poses) and `capture-corpus-flow.sh`
  (accessibility, the same 28): `verification/matrices` and `verification/accessibility` now hold 11 configs. Both
  three-level configs are clean in every pose by the frame records; book 0–455.7 | 495.7–867 pt, flat sideways
  0–320 | 320–867 pt. Across poses the accessibility detectors find T7 for `three` upright (laptop, tent,
  flat-upright): SwiftUI shows the detail alone there, empty at the top level. The adapter check against the frame
  records no longer leaves T10 out: the sheets have none. 32 tests.

## Phase 4, step 7 — two panes upright in SwiftUI (merged 2026-10-28, PR 20)
- The owner's call: build it. `Sources/Patterns/FoldAlignedTiledSplit.swift` (copied with `FoldAlignedSplit.swift`):
  upright on the inner display, where the system draws no vertical bar, a two-column `UISplitViewController` that
  tiles (`minimumSecondaryColumnWidth = 320`, no column width), the sidebar and the detail in hosting controllers;
  everywhere else `FoldAlignedSplit`. Tried as a UIKit split in every pose first: the outer display kept its back
  button in a horizontal top bar, because the system finds the vertical bar from the window's root controller down and
  SwiftUI's root does not hand it on; hence the switch. Its cost: both panes are rebuilt when the phone moves between
  an upright inner pose and one with a vertical bar; selection and the sidebar's path survive in the caller, scroll
  positions do not.
- Catalog `split:tiled`, `split:tiled-three`, `split:tiled-three-list`, captured as frame records and accessibility
  (14 configs, 98 captures each way): clean in every pose; upright sidebar 0–320 pt, detail 320–669 pt; book and the
  outer display as `FoldAlignedSplit`. `tiled-three` has no T7 upright, where `three` does. The decision table's upright
  shortfall is closed for SwiftUI apps too; the skill's migrate step uses `FoldAlignedTiledSplit` for P1 in SwiftUI.
- The switch keeps the caller's state: with "Reading list" tapped on the outer display (`capture-corpus-flow.sh`,
  `tiled-three`), every pose showed it beside the detail, through the switch into the UIKit split upright, and the
  shut phone never lost it on the way back.

## Phase 4, step 8 — a second app: IceCubesApp, SwiftUI (merged 2026-10-28, PR 21)
- The skill alone, from `/duo-start`, on IceCubesApp at 98098b9, logged out (no account may be created): a subagent,
  since headless `claude -p` was signed out (`verification/runs/IceCubesApp/`, report, audit, progress file, patch; the
  shots stay outside, they show strangers' posts). About two hours, no questions. Five screens (Add Account, the
  Trending timeline, a post, Settings, Display Settings), all Fold-aligned split, all verified in all seven poses: G3
  for a second corpus app. Screens that need an account are in its `todo`.
- What it found: T15 (Add Account on the leading half in book), and T7 on three screens with one cause: the logged-out
  tabs sat in an untitled sidebar-only `TabSection`, every fold rebuilt the tab bar's items, the hidden Timeline tab
  appeared for a moment and presented Add Account again, and closing the phone from tent with Settings selected crashed
  in `UITabBarController`. Plain tabs fixed both; the sheet rule, applied from the window's root (`readsBookFold()`),
  fixed T15. The timeline needed nothing: the system's tab sidebar already splits at the fold. `duo-detect` 2 → 0
  (the crash read `n/a`); the rest came from the capture's lines and a crash report.
- Fixed from its "Skill problems": the tap runner turns off XCTest's check for system alerts, which waited 60 s for
  SpringBoard before every tap (4 s a tap now; Settings → Display Settings, closed: 243 s → 61 s); a snapshot taken with
  the app gone says so and `duo-detect` reports T7 there (checked by killing the app mid-hold); the "lost the screen"
  line names the pose after which it was lost; `capture-app.sh` exits 3 and repeats the lines when anything was
  skipped, and takes `SCREEN=` to probe one screen behind taps (both checked); `TAP_TIMEOUT` documented. The reference
  files compile for Mac Catalyst, visionOS and macOS too, and `FoldAlignedSplit.swift` gains `readsBookFold()`. P1
  covers a `TabView` sidebar and the hazard above; the decision table's I1 says what a feed is (the pages disagreed);
  the T10 static scan matches whole words (it ran from an app's `ToolbarItems(` type to an alert's OK). T7 has corpus
  evidence in two apps. 33 tests; the plugin, 0.3.1, carries all of it.
- The owner's calls (2026-10-28): the patch stays, AGPL-3.0 with the license's text next to it; IceCubesApp logged
  in is left out.

## Phase 4, step 9 — a third app: Wikipedia, UIKit with a web view, and four review rounds (merged 2026-10-29, PR 22)
- The skill alone, from `/duo-start`, on wikipedia-ios at 2031b89, logged out, by a subagent (`verification/runs/Wikipedia/`:
  report, audit, progress file, flow, patch under MIT with the license beside it; the shots stay outside). Eleven
  screens. The run's own check passed defects, so its work was reviewed: once by the coordinator from the shots, then
  three times by independent reviewers with a skeptic re-checking each finding, and the run's agent fixed what each
  confirmed (2, 10, 22, 23 items). A last review of the fourth round confirmed 15 more (two medium: contents opening on
  every unfold, the random-article shortcut in the list pane); the owner asked to finish there, so they are listed in
  the run's README, not fixed. About 7 h 45 min of the agent's work.
- End state: two screens done (community and the article tabs, Even grids); nine in `todo`, none worse than before in
  any capture.
  Saved, Search, Activity, the article and its contents split at the fold through a container of the app's own, but
  both panes' top bars keep the vertical bar's 84 pt inset (the list's search field ends at 371 of 455 pt) and nothing
  tried moved them; Settings' split broke its coordinators and was reverted (T5); articles from Home or Places stay one
  column (Reflowing columns for a web view not built); Places, For You and the Account sheet flat sideways as before.
  `duo-detect`: 23 cells with a finding before, 16 after. G3 for a third corpus app: not met.
- What the reviews found that no capture showed: the container, present on every iOS 27.1 device, broke state
  restoration, Settings' theme and the tab bar there; routes from the detail pane landed in the list's stack; a custom
  view turned into a titled item lost its VoiceOver label and selected look everywhere; VoiceOver reached a list the
  contents covered.
- Taken into this repository: T10 for custom-view toolbar items, T7 for stranded toolbar items, T14 for a list pane
  short of the fold, map content that pans, a list row as one run (Settings' T5); the tap runner's wait for a disabled
  element, recaptures that keep the record, `progress.py done --remove`; the skill's regression rule, pane
  measurements, gating on the condition that needs it, and a diff review for what no shot shows, handed to a fresh
  reviewer where possible; P1's "UIKit without a split view", P2's web-view section, the decision table's feed and map
  rules. 39 tests; the plugin, 0.3.2, carries all of it.

## Phase 4, step 10 — the regression rule in the tool (merged 2026-10-29, PR 23)
- The skill's rule that a screen never ends worse than it started was a sentence in step 6. `progress.py done <screen>: …`
  and `phase done` now refuse, changing nothing, while a pose the detectors found clean in the before capture has a
  finding in the after capture, or no detector run there (not captured, or `no-rotate`); `check` lists them, and
  `waive <screen> <pose> <id> "<why>"` records on the cell a detector line the shot does not bear out (neither of those
  can be waived). The capture now removes a screen's snapshots in the poses it takes before taking them, so a pose a
  recapture skips is not captured rather than an earlier pass's tree. The refusal says
  what to do: fix it or revert, capture again, or waive with a reason the report repeats. `phase done` checks the
  screens in `todo` too, since `todo` never holds what a run broke.
- It reads the detectors.md each capture writes, so it sees only what the detectors see: none of Wikipedia's
  last-review items, and none of the three runs is refused (their finished screens pass). The diff review and the fresh
  reviewer in step 6 stay.
- An independent review (three reviewers, a skeptic each) confirmed six items, all fixed: a waivable `no-rotate`, an
  earlier pass's snapshots counted as captured, the folder taken from one stray shot, the locale's encoding, and two
  test gaps; it refuted four (waive's unchecked names and an empty before table fail safe or only change a message).
- `scripts/test_progress.py` (20 tests, the three runs' tables among them; each of seven wrong implementations fails
  one) runs in CI; plugin 0.3.3.

## Phase 4, step 11 — the v0 gates G2 and G4 (merged 2026-10-29, PR 24)
- G2 runs in CI, on demand: a `goldens` job (Actions → ci → Run workflow, "goldens" ticked) boots the Duo simulator,
  takes the duo.py driver at a fixed commit, builds and installs the catalog, captures all 14 configs in all seven
  poses into the runner's temp folder and diffs them against `verification/matrices`. First run (2026-10-29, run
  40896969902): 98 of 98 goldens compared, worst 0.00 %, none failed, in about 15 minutes. It is not run on every push
  because it holds the simulator that long.
- G4 for Fold-aligned split: `verification/oracle/fold-aligned-split.md`, Settings against the skill's reference,
  measured pose by pose and re-checked. The same pane assignment and the same system bars in book (the split on the
  crease) and flat sideways (the inactive fold ignored), and one pane beside the same vertical bar on the cover; the
  bar items never match, since the apps draw different controls (Settings: search; the reference: Back, compose, a
  sidebar toggle). Differences, none about the fold: upright, Settings' sidebar is 250 pt where the reference's is 320,
  and the reference draws its bars in a row below the status band; on the turned cover Settings does not rotate, so
  that pose has no oracle.
- G4 amended by the owner (EVAL.md §1): where the matched app is not on the simulator, the reference is set beside
  Apple's own published frames of it, linked at the frame and not stored.
- G4 for Even grid: `verification/oracle/even-grid.md`, against Fitness in the talk 111463 (5:52–6:04). Book: the
  same count, two columns a side, nothing on the fold, the margins kept, the bars in a trailing vertical bar (the items
  differ); but Fitness's gutter at the hinge is the division and its leading columns (about 212 pt) are wider than its
  trailing ones (about 171; estimates from the angled frame, which the amendment's face-on measurement does not
  cover), where the reference's are all 171.75 pt with a 124 pt gutter. Open flat: four columns in both, but Fitness spaces them evenly (columns about 199 pt, its middle
  gutter at about 434 pt, so the inactive division lies inside its third column) where the reference keeps its book
  layout (171.75 pt columns) so folding moves nothing. No frame of the grid found in the other five poses.
- G4 for Reflowing columns: `verification/oracle/reflowing-columns.md`. No source in `raw/apple-docs/` and no frame of
  the talks looked at shows a text in columns: Notes is a split view in the HIG's images (read through their alt
  text), Books is in no source collected, and the talk's example of two columns reflowing from one is Music's album
  page, two blocks side by side. The upright poses and the cover lay out as Safari's one column does (context, not an
  oracle: Safari is not the matched app). Open: the owner decides how it is settled.

## Phase 4, step 12 — Arrangement (P4) (merged 2026-10-29, PR 25)
- The owner's choice (2026-10-29): no Apple frame looked at shows a text in columns, so Reflowing columns' G4 has no
  oracle and Arrangement is built as v0's third pattern to pass G1–G4; Reflowing columns stays in the catalog and the skill with G4 open (EVAL.md §6 amended).
- `patterns/arrangement.md` and `Sources/Patterns/Arrangement.swift`: one `ArrangementView` for every pose, `.split`
  for two views neither may cover, `.overlay` for controls over scrolling content, the overlay's primary drawn at the
  foot of its region. Measured on the simulator: the split stacks the two views on the cover (primary y 82–363,
  secondary 363–644), shows the primary alone on the turned cover, puts the boundary on the fold in book (0–455.5,
  495.5–867.2) and laptop and tent (y 82–455.5, 495.5–917). Open flat the system halved the window, which put the
  transcript's text across the inactive division (T5, found by the accessibility capture); the reference now tells
  the split where the inactive division is, so flat sideways and flat upright lay out as book and laptop.
- Catalog: `arrangement:aligned` (a player and its transcript), `arrangement:overlay` (the controls over text in
  Reflowing columns) and the before variant `arrangement:inline` (an `HStack` with the player in a fixed third,
  Wikipedia's inline contents). 17 configs, 119 captures each way (frame records and accessibility, which agree in all
  119). `inline` shows T5 in book and flat sideways and T1 in laptop and tent; the references are clean everywhere.
- T14 gains `PanesOffHorizontalFold` (panes one above the other against an active horizontal division); 42 tests.
- G4: `verification/oracle/arrangement.md` against Apple's frames of Podcasts and Accessibility Reader (talk 111463).
  Flat sideways and book: the same assignment as Podcasts, player leading and transcript trailing, clear of the
  division, with different bars (Podcasts' actions at the foot of the transcript, the reference's at the top of the
  trailing bar); Podcasts' text starts about 12 pt nearer the division (about 503 pt against 515.7). Upright: Podcasts
  shows one screen, its transcript above the controls and its bar at the foot, where the reference stacks the player
  above the transcript (differs). The overlay has Accessibility Reader's assignment, the controls centred at the foot;
  its columns and card width differ. No frame of either app on the cover, turned or not, or in tent.
- G2: the 21 arrangement captures are its goldens. A goldens run on this branch (2026-10-29, run 40944398016) compared
  119 of 119, worst 0.00 %, none failed; the capture took about 18 minutes for 17 configs.
- The decision table's cover cell for supporting content (the primary alone) is not what the system's split does; it
  is listed where the references fall short of a cell. The skill's step 4 and 5 name the page and its reference; the
  skill's references gain the page, its matrix and `Arrangement.swift` (`scripts/sync-skill-references.py`); plugin
  0.3.4.
- Tried and dropped: `overlayArrangementEdge(VerticalEdge.bottom)` on the overlay's primary left the controls at the
  top (y 82) on the cover and flat, and in laptop moved the text to the bottom half and left the top half empty;
  without it the system sets the primary at its own size in the top leading corner of its region (controls at x 0–168,
  y 82–133.7 on the cover and flat), so the reference gives it the region and aligns it at the foot.

## Phase 4, step 13 — preparing to go public (2026-10-29, in the working repository)
- A release check (secrets and personal data across history, third-party content and licences, the public docs, CI
  safety and a clean clone; each finding re-checked) found no key, token or signing file anywhere in history, no
  unredacted stranger's post, no stored Apple frame or transcript, and a clean clone that builds and passes.
- Fixed here: the README's Apple product photo is gone (the catalog's own capture instead), with a trademark line; the
  README says what this is, what it needs (Xcode 27.1, the Duo simulator, xcodegen, Claude Code 2.1.308 or later) and
  that a build without `--marketplace` needs `claude update`, and a sparse install that skips the corpus screenshots;
  one licence for this project's code and text (MIT), NetNewsWire's beside its patch, and a notice that screenshots of
  other apps are not under `LICENSE`; the plugin and the skill carry `LICENSE`, and the skill's copied pages link
  repository paths to GitHub; the skill fetches `duo.py` at a pinned commit into `~/Library/Caches/duo-driver` (the
  pane looks there too); CI has a read-only token, actions pinned to commits, no persisted credentials, and fails
  where it used to skip; `EVAL.md` §7 records where each gate stands; set-aside and historical files say so. Plugin
  0.3.5.
- Settled by republishing (step 14): the private working repository's history held Apple's photo and personal data in
  commit metadata, and its CI ran on a runner on the owner's Mac.

## Phase 4, step 14 — the public repository (2026-10-29)
- This repository starts from a fresh history: one commit holding the working repository's final tree (its branch
  `release/prep`), authored by the organisation, with no personal data in the tree or the metadata. The working
  repository, with its full history, pull requests and run logs, stays private.
- Layout: the working logs (`STATUS.md`, `DEVIATIONS.md`, `MAC-PHASE.md`) moved to `docs/history/`; `EVAL.md`, the
  gates, stays at the root.
- The screenshots of other apps (`raw/corpus/evidence/`, `raw/apple-apps/`, `verification/ab/baseline/`) are stored
  as 256-colour PNGs at full resolution, about six times smaller; the pose matrices, which G2 compares, are unchanged.
- CI runs on GitHub's hosted `xcode-27` image (Xcode 27.1, the iPhone Duo simulator), so no runner on anyone's machine
  executes workflow code; pull requests get CI.
- The repository was named duo-patterns until it went public. That name remains in these logs, in the comments of the
  migration patches (`verification/runs/*/*.patch`) and in the bundle identifiers (`dev.enchiridion.duopatterns.*`),
  which the recorded snapshots carry. The simulator's UDID in the run records is replaced by a placeholder.

## Not done
- Wikipedia's last review (`verification/runs/Wikipedia/README.md`, "Last check"): 15 items not fixed, two medium
  regressions among them, all in routes that miss the container (`setViewControllers`, a coordinator's own stack, a
  check that reads the list) or a setting read on every unfold.
- Wikipedia's `todo` (`verification/runs/Wikipedia/REPORT.md`): the navigation bars' inset in a custom pane container,
  Reflowing columns for a web view, Settings' split (needs its coordinators to route through the container), Places'
  map, For You beside Community's grid. G3 for a third corpus app waits on the first two.
- NetNewsWire's Reader View button, a custom-view toolbar item the step-9 T10 detector finds in 8 cells after its run:
  not fixed (`verification/runs/NetNewsWire/README.md`).
- Optional corpus depth: deeper screens for NetNewsWire and IceCubesApp with `scripts/capture-corpus-flow.sh`.
- Oracle for 9 of 11 Apple apps: needs a physical iPhone Duo.
- Gates (EVAL.md): G1 and G3 (patterns) run in CI on every push; G2 in CI on demand (step 12's run: 119 of 119
  passing). G3 for a migrated corpus app (EVAL.md §7): IceCubesApp's after captures are clean in every pose;
  NetNewsWire's were clean with the detectors of its run, and the step-9 T10 detector finds its Reader View button in
  8 cells, not fixed; Wikipedia's run left findings in `todo`. G4: documented for Fold-aligned split against Settings
  (step 11; differences upright and on the turned cover) and for Even grid against Fitness's published frames (in book
  the same count and bar placement, but Fitness widens its leading columns where the reference widens the gutter, and
  the bar items differ; spacing and widths differ open flat; no frame found in five poses) and for Arrangement against
  Podcasts and Accessibility Reader (step 12: the same assignment side by side with different bars, differs upright,
  no frame on the cover or in tent); open for Reflowing columns, which no Apple frame looked at shows, and which the
  owner replaced as v0's third pattern by Arrangement. G5 set aside by the owner (2026-10-27); `verification/ab/`
  stays as written. G6 tracked only.
- Captures: about 27 s a cell now (step 3), and taps about 4 s each (step 8). Each inner pose still goes through the shut phone and posts each fold and
  turn with a settle of 2–3 s; going from pose to pose directly would save about a third more, at the cost of opening
  poses from one another rather than from the shut phone.
- T7 compares what is on screen, not state within it (a selection, a scroll offset); the capture's "lost the screen"
  line is not yet a detector finding (a crash is, since step 8).
- IceCubesApp logged in: its inner display switches to the iPad tab sections and the cover back to the iPhone tabs on
  every fold, the rebuild that crashed logged out; it needs an account, which only the owner can sign in to. Left out
  by the owner (2026-10-28).
- `FoldAlignedTiledSplit` rebuilds both panes between upright and vertical-bar poses: scroll positions start over (not
  seen by the T7 detector, which compares what is on screen).

## Three findings that shaped the plan (unchanged)
1. Apple ships its own agent skill (`app-resizability`); API migration is first-party. Read in step 1.
2. No public fold command. The harness is a simulator driver + screenshots + detectors, not a unit-test target.
3. Apple engineers filled doc gaps in the forums (`raw/complaints/README.md §A`); cite, do not re-derive.
