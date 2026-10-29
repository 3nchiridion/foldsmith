# NetNewsWire on iPhone Duo — migration report

Branch `duo-migration` (from `duo-baseline`), iOS 27.1 SDK, Xcode 27.1, simulator iPhone Duo
`<Duo simulator UDID>`. Five screens × seven poses, captured before and after with
`tools/capture-app.sh` (accessibility snapshot per shot, then `duo-detect`). Shots live in `.duo/captures/` (not in
git); `.duo/audit.md` has the findings and the classification.

## Result
| Screen | Pattern | Before (detectors + eye) | After | Status |
|---|---|---|---|---|
| feeds | Fold-aligned split, three levels | T14 book, T1 laptop/tent, T7 every inner pose | clean: the sidebar beside the article (follow-up) | verified in all seven poses |
| timeline | Fold-aligned split | T14 book, T1 + T7 laptop/tent, T7 flat-upright | clean | verified in all seven poses |
| article | Fold-aligned split (detail pane) | T14 book | clean | verified in all seven poses |
| settings | Fold-aligned split, sheet rule | T15 book | clean | verified in all seven poses |
| add-feed | Fold-aligned split, sheet rule | T10 closed/closed-sideways, T15 book | clean | verified in all seven poses |

`duo-detect`: before 3 findings in 35 captures (T15 settings/book, T15 add-feed/book, T14 article/book); after 0.
The rest were found by looking at the shots (the detectors exempt a `WKWebView` placeholder as scrolling content and do
not treat an empty pane as a container).

## What changed (one commit per screen)
- `iOS/FoldAlignedSplit.swift` (new): the P1 pattern for a UIKit split. The fold is read from
  `UIView.reservedRegions(kind: .division, options: .includeInactive)`, gated `#available(iOS 27.1, *)`; nothing reads
  device, idiom or orientation.
- **article** (`67b5cc7`): on a display with a fold `SceneCoordinator` sets no column width (primary and supplementary
  min/max/preferred → automatic) and never saves widths there; elsewhere the saved widths apply exactly as before. The
  system then puts the timeline/article boundary on the fold in book (timeline to 455.5, article from 495.5) and keeps
  the leading pane narrower when flat (340 pt). A 320 pt `minimumSecondaryColumnWidth` (iOS 26 API) lets the timeline
  tile beside the article on the upright inner display (669 pt): two panes in laptop, tent and flat-upright, as the
  decision table's cell says [apple-apps/settings/laptop] and the v0 SwiftUI reference could not do.
  `RootSplitViewController` re-reads the fold on layout and on `UIHingeInteraction` updates.
- **timeline** (`ebe206a`): on a display with a fold the empty article page's "No selection" placeholder sits at 25 %
  of the pane instead of 45 %, which was on the laptop/tent fold. Re-rendered when the window gains or loses the fold.
- **settings** (`936019c`): every sheet presented through the root split gets
  `sheetPresentationController.preferredPlacement = .trailing` while a vertical division is active and `.automatic`
  otherwise, and follows the fold while it is up (sheet presented on the cover, then unfolded to book: trailing).
- **add-feed** (`2b5f2a9`): the sheet rule above, plus title + symbol bar items (Cancel → `xmark`, Add →
  `checkmark`) on iOS 27.1 so they join the vertical bar on the outer display and on the trailing sheet; earlier
  systems keep the text buttons.

## Existing behavior
- iPhone (no fold), iPad and Mac: unchanged by construction — every change is gated on a division region (iOS 27.1)
  except the Add Feed bar items, which show `xmark`/`checkmark` glyphs instead of "Cancel"/"Add" on every iOS 27.1
  device (the label text is kept for accessibility). Not run on a non-Duo simulator: this run may touch only the Duo.
- Duo outer display: the app collapses to its navigation stack as before; closed and closed-sideways shots match.
- Not run: the app's unit tests.

## Left to do
- Sheets and screens not in the flows (Add Folder, feed and account inspectors, Current Activity, article search,
  full-screen image) were not captured. Add Folder and the inspectors are presented through the same root and get the
  sheet rule; Add Folder (`AddFolderView.swift:60-70`) has the same text-only Cancel/Add bar items Add Feed had (T10 by static scan, not captured; Add Folder is presented from `MainFeedCollectionViewController`, so it gets the sheet placement only when the fold changes while it is up).
- Split View half window (475 × 669): not drivable headless, not verified.

## Where the skill's references and the SDK differ
- The P1 reference is SwiftUI (`NavigationSplitView`); this app is a UIKit three-column `UISplitViewController`. The
  rule carried over (no column width → the system aligns the boundary with the fold), measured here for the
  supplementary/secondary boundary of a triple-column split.
- The P1 page's upright row ("the detail, 0–669; the sidebar one tap away") is the SwiftUI reference's shortfall; a
  UIKit split tiles at 669 pt once `minimumSecondaryColumnWidth` is lowered, matching the decision-table cell.
- UIKit has no `presentationPlacement`; the 27.0 SDK's `UISheetPresentationController.preferredPlacement`
  (`.automatic/.leading/.center/.trailing`) does the same. UIKit has no reserved-region change callback: layout plus
  `UIHingeInteraction` was enough on the simulator.
- `references/detectors-static.md`: the T13 line `rg -L 'UIApplicationSceneManifest'` lists matches (`-L` is
  `--follow` in ripgrep), not files without one; the T14 scan misses `…SupplementaryColumnWidth`; the T10 scan misses
  multi-line `ToolbarItem` and `Button(NSLocalizedString(…))`.

## Per screen, per pose
### feeds — Fold-aligned split

| Pose | State | Before | After |
|---|---|---|---|
| closed | unchanged | `.duo/captures/NetNewsWire/before/feeds-closed-cover.png` | `.duo/captures/NetNewsWire/after/feeds-closed-cover.png` |
| closed-sideways | unchanged | `.duo/captures/NetNewsWire/before/feeds-closed-sideways-cover.png` | `.duo/captures/NetNewsWire/after/feeds-closed-sideways-cover.png` |
| book | finding (T7) | `.duo/captures/NetNewsWire/before/feeds-book-inner.png` | `.duo/captures/NetNewsWire/after/feeds-book-inner.png` |
| laptop | finding (T7) | `.duo/captures/NetNewsWire/before/feeds-laptop-inner.png` | `.duo/captures/NetNewsWire/after/feeds-laptop-inner.png` |
| tent | finding (T7) | `.duo/captures/NetNewsWire/before/feeds-tent-inner.png` | `.duo/captures/NetNewsWire/after/feeds-tent-inner.png` |
| flat-sideways | finding (T7) | `.duo/captures/NetNewsWire/before/feeds-flat-sideways-inner.png` | `.duo/captures/NetNewsWire/after/feeds-flat-sideways-inner.png` |
| flat-upright | finding (T7) | `.duo/captures/NetNewsWire/before/feeds-flat-upright-inner.png` | `.duo/captures/NetNewsWire/after/feeds-flat-upright-inner.png` |

### timeline — Fold-aligned split

| Pose | State | Before | After |
|---|---|---|---|
| closed | unchanged | `.duo/captures/NetNewsWire/before/timeline-closed-cover.png` | `.duo/captures/NetNewsWire/after/timeline-closed-cover.png` |
| closed-sideways | unchanged | `.duo/captures/NetNewsWire/before/timeline-closed-sideways-cover.png` | `.duo/captures/NetNewsWire/after/timeline-closed-sideways-cover.png` |
| book | verified | `.duo/captures/NetNewsWire/before/timeline-book-inner.png` | `.duo/captures/NetNewsWire/after/timeline-book-inner.png` |
| laptop | verified | `.duo/captures/NetNewsWire/before/timeline-laptop-inner.png` | `.duo/captures/NetNewsWire/after/timeline-laptop-inner.png` |
| tent | verified | `.duo/captures/NetNewsWire/before/timeline-tent-inner.png` | `.duo/captures/NetNewsWire/after/timeline-tent-inner.png` |
| flat-sideways | verified | `.duo/captures/NetNewsWire/before/timeline-flat-sideways-inner.png` | `.duo/captures/NetNewsWire/after/timeline-flat-sideways-inner.png` |
| flat-upright | verified | `.duo/captures/NetNewsWire/before/timeline-flat-upright-inner.png` | `.duo/captures/NetNewsWire/after/timeline-flat-upright-inner.png` |

### article — Fold-aligned split

| Pose | State | Before | After |
|---|---|---|---|
| closed | unchanged | `.duo/captures/NetNewsWire/before/article-closed-cover.png` | `.duo/captures/NetNewsWire/after/article-closed-cover.png` |
| closed-sideways | unchanged | `.duo/captures/NetNewsWire/before/article-closed-sideways-cover.png` | `.duo/captures/NetNewsWire/after/article-closed-sideways-cover.png` |
| book | verified | `.duo/captures/NetNewsWire/before/article-book-inner.png` | `.duo/captures/NetNewsWire/after/article-book-inner.png` |
| laptop | verified | `.duo/captures/NetNewsWire/before/article-laptop-inner.png` | `.duo/captures/NetNewsWire/after/article-laptop-inner.png` |
| tent | verified | `.duo/captures/NetNewsWire/before/article-tent-inner.png` | `.duo/captures/NetNewsWire/after/article-tent-inner.png` |
| flat-sideways | verified | `.duo/captures/NetNewsWire/before/article-flat-sideways-inner.png` | `.duo/captures/NetNewsWire/after/article-flat-sideways-inner.png` |
| flat-upright | verified | `.duo/captures/NetNewsWire/before/article-flat-upright-inner.png` | `.duo/captures/NetNewsWire/after/article-flat-upright-inner.png` |

### settings — Fold-aligned split

| Pose | State | Before | After |
|---|---|---|---|
| closed | unchanged | `.duo/captures/NetNewsWire/before/settings-closed-cover.png` | `.duo/captures/NetNewsWire/after/settings-closed-cover.png` |
| closed-sideways | unchanged | `.duo/captures/NetNewsWire/before/settings-closed-sideways-cover.png` | `.duo/captures/NetNewsWire/after/settings-closed-sideways-cover.png` |
| book | verified | `.duo/captures/NetNewsWire/before/settings-book-inner.png` | `.duo/captures/NetNewsWire/after/settings-book-inner.png` |
| laptop | unchanged | `.duo/captures/NetNewsWire/before/settings-laptop-inner.png` | `.duo/captures/NetNewsWire/after/settings-laptop-inner.png` |
| tent | unchanged | `.duo/captures/NetNewsWire/before/settings-tent-inner.png` | `.duo/captures/NetNewsWire/after/settings-tent-inner.png` |
| flat-sideways | unchanged | `.duo/captures/NetNewsWire/before/settings-flat-sideways-inner.png` | `.duo/captures/NetNewsWire/after/settings-flat-sideways-inner.png` |
| flat-upright | unchanged | `.duo/captures/NetNewsWire/before/settings-flat-upright-inner.png` | `.duo/captures/NetNewsWire/after/settings-flat-upright-inner.png` |

### add-feed — Fold-aligned split

| Pose | State | Before | After |
|---|---|---|---|
| closed | verified | `.duo/captures/NetNewsWire/before/add-feed-closed-cover.png` | `.duo/captures/NetNewsWire/after/add-feed-closed-cover.png` |
| closed-sideways | verified | `.duo/captures/NetNewsWire/before/add-feed-closed-sideways-cover.png` | `.duo/captures/NetNewsWire/after/add-feed-closed-sideways-cover.png` |
| book | verified | `.duo/captures/NetNewsWire/before/add-feed-book-inner.png` | `.duo/captures/NetNewsWire/after/add-feed-book-inner.png` |
| laptop | unchanged | `.duo/captures/NetNewsWire/before/add-feed-laptop-inner.png` | `.duo/captures/NetNewsWire/after/add-feed-laptop-inner.png` |
| tent | unchanged | `.duo/captures/NetNewsWire/before/add-feed-tent-inner.png` | `.duo/captures/NetNewsWire/after/add-feed-tent-inner.png` |
| flat-sideways | unchanged | `.duo/captures/NetNewsWire/before/add-feed-flat-sideways-inner.png` | `.duo/captures/NetNewsWire/after/add-feed-flat-sideways-inner.png` |
| flat-upright | unchanged | `.duo/captures/NetNewsWire/before/add-feed-flat-upright-inner.png` | `.duo/captures/NetNewsWire/after/add-feed-flat-upright-inner.png` |

## Timing
| Step | Time |
|---|---|
| Unmodified build (`build/`, iOS 27.1 SDK) | 59 s |
| Tap runner (`xcodegen` + `build-for-testing`) | 9 s; detectors first `swift build` ≈ 10 s |
| Flow check, 5 screens closed only | 339 s |
| Audit capture, 35 cells | 2274 s (≈ 65 s a cell) |
| Incremental builds per migration step | 12–19 s |
| Probes during migration | `duo.py` direct launch ≈ 25 s a shot; `capture-app.sh` 2 cells 130–144 s |
| Proof capture, 35 cells | 2277 s |

## Follow-up: feeds (2026-10-27, after the owner's decision)
The owner decided the open question: unfolded from the feeds list, the two panes are the sidebar and the article. The
split now shows two panes on the inner display, the list pane and the article; the list pane is the feeds list, and a
picked feed pushes the timeline onto it (Back returns to the feeds). A triple-column split pairs only the timeline with
the article in its two-pane mode, and a zero-width timeline column crashes (a UIKit assertion), so while the split is
expanded on a display with a fold the feeds list moves onto the timeline column's navigation stack and the primary
column's stack holds an empty controller (`SceneCoordinator`, "sidebar beside the article"). The stacks go back in
`splitViewController(_:topColumnForCollapsingToProposedTopColumn:)`, which then answers from the app's state. Moving
the controllers between columns instead (`setViewController(_:for:)`) popped the cover to the feeds list at its next
rotation, and hooking `viewWillTransition` hung the app with Add Feed up; both reverted.

Recaptured with the faster capture (one test run per screen): 35 cells in 915 s, no screen lost on the way back to the
shut phone, `duo-detect` 0 findings, every shot checked. All five screens are verified in all seven poses.
