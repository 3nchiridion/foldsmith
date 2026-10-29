# Ice Cubes on iPhone Duo — migration report

Branch `duo-migration` from `main` (8614ae9, the unmodified app), Xcode 27.1, iOS 27.1 SDK, simulator iPhone Duo
`<Duo simulator UDID>`, logged out (no account exists and none may be made). Five screens × seven
poses, captured before and after with `tools/capture-app.sh` (an accessibility snapshot with every shot, then
`duo-detect`). The shots show strangers' posts: they stay in `.duo/captures/` (excluded from git); `.duo/audit.md`
has the findings and the classification, `.duo/detectors-before.md` and `.duo/detectors-after.md` the detector tables.

Run: 07:51–09:52 (about 2 h). Before capture 34 min 52 s, after capture 23 min 19 s; the rest was the flow
check (12 min), diagnosis and probes.

## Result
| Screen | Pattern | Before (detectors + eye) | After | Status |
|---|---|---|---|---|
| add-account | Fold-aligned split (sheet rule) | T15 book | clean | verified in all seven poses |
| timeline | Fold-aligned split (the system tab sidebar; no change needed) | clean | clean | verified in all seven poses |
| status | Fold-aligned split (state kept on fold) | T7 flat-sideways | clean | verified in all seven poses |
| settings | Fold-aligned split (state kept on fold) | T7 laptop; crash after tent (T7 tent, flat-sideways, flat-upright) | clean | verified in all seven poses |
| settings-display | Fold-aligned split (state kept on fold) | T7 laptop, flat-sideways | clean | verified in all seven poses |

`duo-detect`: before 2 findings in 33 snapshots (T15 add-account/book, T7 status/flat-sideways; settings
flat-sideways and flat-upright read `n/a`, the app having crashed); after 0 findings in 35. The rest of the "before"
column came from the capture's own lines ("the shut phone lost the screen on the way to …") and a crash report.

## What was wrong, and why
- **The Add Account sheet came back on folds, and the app crashed (T7).** Logged out, `AppView` put the two tabs
  (Timeline, Settings) in an untitled `TabSection` with `.tabPlacement(.sidebarOnly)`, Settings itself
  `.sidebarOnly`. On iPhone Duo each change of the vertical bar (a fold, a turn of the cover) makes `UITabBarController`
  rebuild its items. A logging build showed what that did: with Settings selected, the hidden Timeline tab appeared and
  disappeared within 50 ms, and its `onAppear` (logged out: present Add Account) put the sheet back over whatever the
  person was reading; with Timeline selected the same rebuild re-presented it over a post. Closing the phone from tent
  with Settings selected crashed: `NSInvalidArgumentException: -[__NSArrayM insertObject:atIndex:]: object cannot be
  nil` in `-[UITabBarController _tabs_rebuildTabBarItemsAnimated:]`, from `_UITabBarControllerAdaptiveVisualStyle
  _verticalBarAvailabilityDidChange` (reproduced twice, same pose).
- **Sheets on the leading half in book (T15).** The system places sheets on the leading half while the fold is
  active (Add Account at 8–467.5 pt); the app set no placement.
- **Already right:** in book the system's tab sidebar ends at 455.5 pt and the tab's content starts at 495.5 pt, so
  the boundary is on the fold with no width set (none is set anywhere: T14 clean); flat sideways the sidebar is the
  narrower pane (≈ 0–280 pt). Timeline, post and settings forms scroll across the horizontal fold in laptop, tent and
  flat upright (exempt), and the outer display draws the bars vertically.

## What changed (one commit per change)
- `761fc95` **status, settings, settings-display**: the logged-out tabs are plain `Tab`s, the path the app already
  uses on iPhone (`AppView.swift`, one condition and a comment). No more tab-bar rebuilds that surface the hidden tab,
  no crash. Checked with the logging build first (settings in all seven poses: no transient appearance, no crash),
  then with probes of status and settings-display in all seven poses.
- `725ff38` **add-account**: the P1 sheet rule. `Packages/DesignSystem/Sources/DesignSystem/Duo/
  FoldAwareSheetPlacement.swift` carries the reference's `duoBookFoldIsActive` and `foldAwareSheetPlacement()`, and a
  `readsBookFold()` modifier on the window's root (`IceCubesApp+Scene.swift`) that reads the active vertical division
  from `GeometryProxy.reservedRegions(kind: .division)`. Every sheet's content carries `foldAwareSheetPlacement()`:
  the router's sheets (`withSheetDestinations`, Add Account among them), the media viewer, Settings' Add Account, and
  the composer (drafts, media edit, language, custom emoji), status row (selectable text, share as image), list,
  notifications-policy, relationship-note and account-switcher sheets. Gated `#available(iOS 27.1, *)` and `#if
  os(iOS) && !targetEnvironment(macCatalyst)`; nothing reads device, idiom or orientation.
- The timeline needed nothing: its cells were `unchanged` in every pose, before and after.

## Existing behaviour
- Sheets: unchanged everywhere except while a vertical fold is active (iPhone Duo in book), where they open on the
  trailing half. On a device without a division `presentationPlacement(.automatic)` is the system's own placement;
  visionOS and Mac Catalyst compile the modifiers away.
- Logged-out tabs, every device: same two tabs, same order in code, same selection. Seen on the Duo: the sidebar no
  longer shows the empty section header (its disclosure chevron), and the outer display's bar lists Timeline above
  Settings (before: Settings above Timeline on the cover only, while the sidebar listed Timeline first). On iPad and
  Mac, logged out, Settings was sidebar-only and may now also appear in the floating tab bar: not run, this run used
  only the Duo simulator.
- Logged in: `AppView`'s logged-in paths are untouched.
- Builds: iOS simulator, Debug, clean. DesignSystem for visionOS Simulator fails in the unmodified
  `ToastOverlayView.swift:38` (`glassEffect(_:in:)` is unavailable in visionOS), with or without this branch; the new
  file compiled there without error. Mac Catalyst not built. The app's unit tests were not run.

## Left to do (`todo` in `.duo/migration.json`)
- Screens that need an account: Notifications, Mentions, Explore, Messages, Profile, Bookmarks, Favorites, Lists,
  Followed tags, Links, the composer, account settings. No account may be created on this simulator.
- Logged in, `AppView` gives the regular-width inner display the iPad tab sections (untitled or sidebar-only
  `TabSection`s, sidebar-only tabs) and the cover the iPhone tabs, so the tab set changes on every fold. The rebuild
  that crashed logged out may apply there; it needs an account to capture.
- A stranger's profile (`AccountDetailView`): reachable logged out only through avatars and names whose labels change
  with the timeline; no stable tap.
- Static T10 hits not captured (behind an account): `ListAddAccountView.swift:61` (`Button("action.done")`) and
  `EditRelationshipNoteView.swift:57` (`Button("action.cancel")`), text-only bar items.
- Split View's half window (475 × 669): not drivable headless.
- Upright (laptop, tent, flat upright) the tab sidebar is one tap away and the tab's content fills the window, where
  the decision table's cell says two panes [apple-apps/settings/laptop]. No taxonomy class covers it and the detectors
  found nothing there, so those cells are `unchanged` as the skill rules; it is the same upright shortfall the P1 page
  records for `FoldAlignedSplit`.

## Where the skill's references and the SDK differ
- `FoldAlignedSplit.swift` uses `presentationPlacement(.trailing)` behind `#available(iOS 27.1, *)` only. The 27.1
  SDK declares `PresentationPlacement.trailing` `@available(visionOS, unavailable)` and `@available(macOS,
  unavailable)`, so copied as is into a package that also builds for visionOS (Ice Cubes' DesignSystem) it does not
  compile there. The copy here is wrapped in `#if os(iOS) && !targetEnvironment(macCatalyst)`.
- `reservedRegions(kind:options:layoutDirectionBehavior:)`, `ReservedRegion.isActive`, `.includeInactive`,
  `toolbarVerticalEdge` and `presentationPlacement(_:)` match the SDK as `references/apple.md` names them.

## Skill problems
- **Taps are slow on this simulator, and the default tap timeout fails three-tap screens.** Every XCUITest tap waits
  60 s for SpringBoard to idle ("App animations complete notification not received, will attempt to continue"), so
  `capture-corpus-flow.sh`'s default `TAP_TIMEOUT=150` skipped `settings-display` (three taps) in every pose. The
  knob exists in the script, but neither `references/simulator.md` nor `capture-app.sh`'s header mentions it. Used
  `TAP_TIMEOUT=400`. A status-bar override that stops the Wi-Fi "searching" animation did not change the wait (tried,
  then cleared). Consequence: the five-screen closed-only flow check took 12 min, and the before capture about 60 s a
  cell, against `simulator.md`'s 27 s.
- **`capture-app.sh` exits 0 and prints "N captures, 0 findings" when a screen was skipped in every pose**; only
  `capture.txt` says so. The flow check read "4 captures, 0 findings" with `settings-display` missing.
- **A crash is invisible to the detectors.** When the app is not running the snapshot fails and `duo-detect` writes
  `n/a`; `findings.txt` counted 2 findings with a crash in the run, and `capture-app.sh` still wrote the Home Screen
  shot to the cell as `before`. The taxonomy has no class for a crash on fold; filed under T7 (state lost), with the
  crash report as evidence.
- **"Lost the screen on the way to <pose>" names the next pose, not the one whose round trip lost it.** The skill
  calls the line T7 evidence "on that screen" without saying which cell. Here the loss happened on closing from the
  previous inner pose, so T7 went on that pose (settings: laptop; settings-display: laptop, flat-sideways).
- **Probing a tapped screen.** `simulator.md`'s probe (`duo.py launch`, fold, shot, ≈ 25 s) only works for screens
  with no taps, or apps that reopen where they were. For Ice Cubes' deeper screens I probed with `capture-app.sh` on a
  one-screen scratch flow and `ONLY=…` (4–11 min each, the 60 s taps again).
- **The sheet rule assumes `FoldAlignedSplit`.** Only `FoldAlignedSplit` sets `duoBookFoldIsActive`, inside its own
  `NavigationSplitView`. An app whose split is the system tab sidebar (`TabView` `.sidebarAdaptable` with
  `defaultTabBarPlacement(.sidebar)`, as here) has no way to set it without taking the split too. Factored the fold
  reader into `readsBookFold()` on the window's root.
- **No guidance for a `TabView` sidebar as the P1 container.** Neither the pattern page nor the decision table says
  whether the tab sidebar is the "sidebar" of the three-level rule. Measured here that the system aligns it like a
  split view (book 0–455.5 | 495.5–867; flat ≈ 0–280 | 280–867) and kept it (prefer system containers).
- **The pages disagree on what a feed is.** `even-grid.md` calls "a timeline or chat" continuous content;
  `reflowing-columns.md` calls "a feed, search results" peer content; the decision table's I1 lists "feed" under peer
  and "feeds-with-detail" under hierarchical. Classified the timeline hierarchical (posts open into their thread).
- **The T10 scan has a false positive.** The multi-line pattern `ToolbarItem[^{]*\{` matches a type named
  `ToolbarItems(` and runs on to the next `{`, an alert's `Button("OK")` (`StatusKit/Editor/MainView.swift:100`).

## Per screen, per pose
Labels after verification name the pattern; the finding each `verified` cell had before is in the Result table and in
`.duo/audit.md`.

### add-account — Fold-aligned split

| Pose | State | Label | Before | After |
|---|---|---|---|---|
| closed | unchanged |  | `.duo/captures/IceCubesApp/before/add-account-closed-cover.png` | `.duo/captures/IceCubesApp/after/add-account-closed-cover.png` |
| closed-sideways | unchanged |  | `.duo/captures/IceCubesApp/before/add-account-closed-sideways-cover.png` | `.duo/captures/IceCubesApp/after/add-account-closed-sideways-cover.png` |
| book | verified | Fold-aligned split (sheet rule) | `.duo/captures/IceCubesApp/before/add-account-book-inner.png` | `.duo/captures/IceCubesApp/after/add-account-book-inner.png` |
| laptop | unchanged |  | `.duo/captures/IceCubesApp/before/add-account-laptop-inner.png` | `.duo/captures/IceCubesApp/after/add-account-laptop-inner.png` |
| tent | unchanged |  | `.duo/captures/IceCubesApp/before/add-account-tent-inner.png` | `.duo/captures/IceCubesApp/after/add-account-tent-inner.png` |
| flat-sideways | unchanged |  | `.duo/captures/IceCubesApp/before/add-account-flat-sideways-inner.png` | `.duo/captures/IceCubesApp/after/add-account-flat-sideways-inner.png` |
| flat-upright | unchanged |  | `.duo/captures/IceCubesApp/before/add-account-flat-upright-inner.png` | `.duo/captures/IceCubesApp/after/add-account-flat-upright-inner.png` |

### timeline — Fold-aligned split

| Pose | State | Label | Before | After |
|---|---|---|---|---|
| closed | unchanged |  | `.duo/captures/IceCubesApp/before/timeline-closed-cover.png` | `.duo/captures/IceCubesApp/after/timeline-closed-cover.png` |
| closed-sideways | unchanged |  | `.duo/captures/IceCubesApp/before/timeline-closed-sideways-cover.png` | `.duo/captures/IceCubesApp/after/timeline-closed-sideways-cover.png` |
| book | unchanged |  | `.duo/captures/IceCubesApp/before/timeline-book-inner.png` | `.duo/captures/IceCubesApp/after/timeline-book-inner.png` |
| laptop | unchanged |  | `.duo/captures/IceCubesApp/before/timeline-laptop-inner.png` | `.duo/captures/IceCubesApp/after/timeline-laptop-inner.png` |
| tent | unchanged |  | `.duo/captures/IceCubesApp/before/timeline-tent-inner.png` | `.duo/captures/IceCubesApp/after/timeline-tent-inner.png` |
| flat-sideways | unchanged |  | `.duo/captures/IceCubesApp/before/timeline-flat-sideways-inner.png` | `.duo/captures/IceCubesApp/after/timeline-flat-sideways-inner.png` |
| flat-upright | unchanged |  | `.duo/captures/IceCubesApp/before/timeline-flat-upright-inner.png` | `.duo/captures/IceCubesApp/after/timeline-flat-upright-inner.png` |

### status — Fold-aligned split

| Pose | State | Label | Before | After |
|---|---|---|---|---|
| closed | unchanged |  | `.duo/captures/IceCubesApp/before/status-closed-cover.png` | `.duo/captures/IceCubesApp/after/status-closed-cover.png` |
| closed-sideways | unchanged |  | `.duo/captures/IceCubesApp/before/status-closed-sideways-cover.png` | `.duo/captures/IceCubesApp/after/status-closed-sideways-cover.png` |
| book | unchanged |  | `.duo/captures/IceCubesApp/before/status-book-inner.png` | `.duo/captures/IceCubesApp/after/status-book-inner.png` |
| laptop | unchanged |  | `.duo/captures/IceCubesApp/before/status-laptop-inner.png` | `.duo/captures/IceCubesApp/after/status-laptop-inner.png` |
| tent | unchanged |  | `.duo/captures/IceCubesApp/before/status-tent-inner.png` | `.duo/captures/IceCubesApp/after/status-tent-inner.png` |
| flat-sideways | verified | Fold-aligned split (state kept on fold) | `.duo/captures/IceCubesApp/before/status-flat-sideways-inner.png` | `.duo/captures/IceCubesApp/after/status-flat-sideways-inner.png` |
| flat-upright | unchanged |  | `.duo/captures/IceCubesApp/before/status-flat-upright-inner.png` | `.duo/captures/IceCubesApp/after/status-flat-upright-inner.png` |

### settings — Fold-aligned split

| Pose | State | Label | Before | After |
|---|---|---|---|---|
| closed | unchanged |  | `.duo/captures/IceCubesApp/before/settings-closed-cover.png` | `.duo/captures/IceCubesApp/after/settings-closed-cover.png` |
| closed-sideways | unchanged |  | `.duo/captures/IceCubesApp/before/settings-closed-sideways-cover.png` | `.duo/captures/IceCubesApp/after/settings-closed-sideways-cover.png` |
| book | unchanged |  | `.duo/captures/IceCubesApp/before/settings-book-inner.png` | `.duo/captures/IceCubesApp/after/settings-book-inner.png` |
| laptop | verified | Fold-aligned split (state kept on fold) | `.duo/captures/IceCubesApp/before/settings-laptop-inner.png` | `.duo/captures/IceCubesApp/after/settings-laptop-inner.png` |
| tent | verified | Fold-aligned split (state kept on fold) | `.duo/captures/IceCubesApp/before/settings-tent-inner.png` | `.duo/captures/IceCubesApp/after/settings-tent-inner.png` |
| flat-sideways | verified | Fold-aligned split (state kept on fold) | `.duo/captures/IceCubesApp/before/settings-flat-sideways-inner.png` | `.duo/captures/IceCubesApp/after/settings-flat-sideways-inner.png` |
| flat-upright | verified | Fold-aligned split (state kept on fold) | `.duo/captures/IceCubesApp/before/settings-flat-upright-inner.png` | `.duo/captures/IceCubesApp/after/settings-flat-upright-inner.png` |

### settings-display — Fold-aligned split

| Pose | State | Label | Before | After |
|---|---|---|---|---|
| closed | unchanged |  | `.duo/captures/IceCubesApp/before/settings-display-closed-cover.png` | `.duo/captures/IceCubesApp/after/settings-display-closed-cover.png` |
| closed-sideways | unchanged |  | `.duo/captures/IceCubesApp/before/settings-display-closed-sideways-cover.png` | `.duo/captures/IceCubesApp/after/settings-display-closed-sideways-cover.png` |
| book | unchanged |  | `.duo/captures/IceCubesApp/before/settings-display-book-inner.png` | `.duo/captures/IceCubesApp/after/settings-display-book-inner.png` |
| laptop | verified | Fold-aligned split (state kept on fold) | `.duo/captures/IceCubesApp/before/settings-display-laptop-inner.png` | `.duo/captures/IceCubesApp/after/settings-display-laptop-inner.png` |
| tent | unchanged |  | `.duo/captures/IceCubesApp/before/settings-display-tent-inner.png` | `.duo/captures/IceCubesApp/after/settings-display-tent-inner.png` |
| flat-sideways | verified | Fold-aligned split (state kept on fold) | `.duo/captures/IceCubesApp/before/settings-display-flat-sideways-inner.png` | `.duo/captures/IceCubesApp/after/settings-display-flat-sideways-inner.png` |
| flat-upright | unchanged |  | `.duo/captures/IceCubesApp/before/settings-display-flat-upright-inner.png` | `.duo/captures/IceCubesApp/after/settings-display-flat-upright-inner.png` |
