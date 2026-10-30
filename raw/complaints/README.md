# Developer complaints, questions and Apple's answers — collected 2026-10-24

Three sources: Apple engineers' Group Lab answers (forum thread 847644, summary of Sept 16–17 labs),
the UIKit Q&A threads 847769–848078 (digested by Anton Gubarenko, 2026-09-30), and GitHub issues/PRs
in real apps filed Sept 21 – Oct 23. Verbatim quotes are kept short; most lines are close paraphrase.

## A. Facts Apple engineers confirmed that the docs don't state (fills gaps in raw/apple-docs)

State and lifecycle
- Fold/unfold and the inner↔outer transition are **size-class and trait changes**, not a scene disconnect. The process stays alive; the app is resized in place; no new scene. (847644 #1, #5, #9, #47)
- Text input, scroll position, video playback position are generally preserved automatically across the hinge transition; `scrollPosition(id:anchor:)` normally unnecessary. (#4, #6, #7, 848035, 848042)
- Sheets are not dismissed on fold; they adapt. (848034)
- `UIRequiresFullScreen` is honored; the app still resizes on open/close. (#3, #68)
- Multiple instances share `UserDefaults`/`AppStorage` like iPad multi-window. (#2)
- New windows only on the inner display. No Stage Manager. No free-form drag-to-resize; size follows pose and Split View. (#24, #27, #37, #112)

Geometry and detection
- **No pose value exists.** Compose hinge status + angle + orientation + size class. No Duo `UIUserInterfaceIdiom`; no device-identification API; no hinge trait. (#52, #98, 847775, 848007)
- Inner display: regular × regular size class when full-width; compact when in Split View. Outer: compact width in portrait. (#59, 847903)
- The inner display does not honor `UISupportedInterfaceOrientations`; the outer does. (#100, 847851)
- `toolbarVerticalEdge`/`verticalBarEdge` is the recommended signal for "are bars vertical right now", better than size class or orientation. (#109)
- Touches under a custom element that overlaps the camera's reserved region are suppressed or may not register. (#33)
- Which side of the division a view is on: no semantic API; inspect region frames. (848078, 847854)
- Additional UIKit layout-region APIs named: `UIView.LayoutRegion.bar(onEdge:extent:)`, `UIView.LayoutRegion.margins(cornerAdaptation:)`, `UIView.layoutGuide(for:)`. (847835, 848019)
- `UIArrangementViewController` split ratio: horizontal split, primary width fractional 0.33 via view properties (`defaultViewProperties` / `setViewProperties(_:for:)`), then `updateArrangement`. (847990) — the UIKit counterpart to SwiftUI `splitArrangementLayoutRatio`.
- Reserved regions re-evaluated on trait/layout updates; `UIHingeInteraction` for physical state. (847876)

Bars and sheets
- Standalone `UITabBar` / custom bars / Lottie bars never go vertical; only `TabView`/`UITabBarController` and navigation-controller-managed toolbars. (#18, #35, #36, #77, #84, #102)
- Tab bar cannot be forced vertical in every pose; horizontal on inner portrait is expected. Placement heuristics are not enumerated. (847817, 847898)
- Segmented controls are not vertical-bar candidates; no exclusive-selection substitute offered. (847811)
- Don't toggle `preferredVerticalBarBehavior` per screen. (847864)
- **No preference order for sheet placement** (centered when flat, trailing when folded is not expressible); enhancement request filed; workaround is querying reserved regions. (847797) ← catalog candidate
- Bottom controls above content in outer landscape stay with their content area, not the side bar (Mail). (#105)
- `UICollectionViewCompositionalLayout` does not avoid the division automatically. (847879)
- `WKWebView` cannot use the Safari viewport-segments/posture experiments; CSS insets ignore the division; host must pass geometry to the page. (848036)

Compatibility modes (by build SDK, not Info.plist)
- Pre-27 SDK: compatibility box — iPhone-mini aspect ratio left of the status bar when closed; centered at familiar aspect when open. 27.0 SDK: extends under the status bar on inner. 27.1 SDK: edge to edge, vertical bars. Cannot request the old mode. (#62, #64, #70, #71, 847856)
- Xcode 27 builds require the scene lifecycle. (847769)

### Remainder of thread 847644 (characters 100000–121562), read 2026-10-26
That part carries no question numbers; items are labelled R1–R23 in reading order. Close paraphrase.
- R1 Portrait-only apps still get size-class changes; the outer display honours supported orientations, the inner does not (regular × regular).
- R2 A dense custom bottom bar does not move to the side on its own unless built from toolbar items; reposition it from `ReservedRegion` / `toolbarVerticalEdge` / `verticalBarEdge`.
- R3 A custom vertical tab bar should become `UITabBarController`, which lays out vertically when appropriate and offers an inner-display sidebar; check safe areas against `verticalBarEdge`.
- R4 Overriding `horizontalSizeClass` very likely blocks the system's updates on fold.
- R5 A bottom bar is acceptable for a full-width, non-scrolling layout such as Calculator; vertical bars are an option, and `toolbarVerticalBehavior` / `preferredVerticalBarBehavior` can disable them.
- R6 Text-label tab bars stay horizontal; symbols work much better with the vertical bar.
- R7 In book pose the split axis follows the shape (horizontal when wider than tall, vertical when taller); use `UISplitViewController` / `NavigationSplitView`, which adapt column width and margins. ← catalog
- R8 Inspectors: a trailing column in regular width (inner display fully open), a sheet in compact width or on the outer display; in split views a collapsed inspector shows as a sheet over the secondary column. ← catalog
- R9 Keep the same functionality and element state across displays; make small adjustments, not dramatic rearrangements. ← catalog (rubric R4, R7)
- R10 No custom layout per pose is required; adapt through size classes.
- R11 Concentric corners across poses: `ConcentricRectangle`, `UICornerConfiguration`.
- R12 Adaptive layout over device checks; size classes describe space, not device; `ViewThatFits` picks the first child that fits.
- R13 Storyboards: Auto Layout, safe-area guides, no fixed widths, system containers.
- R14 The inner display ignores supported orientations; lay out by size class.
- R15 Multi-column tables across the hinge: no hard-coded dimensions; read `reservedRegions(kind: .division)` and move columns clear of it. ← catalog
- R16 An app without Split View still works on the inner display but at a familiar aspect ratio, not an adapted layout; start from `UISplitViewController` / `NavigationSplitView`, which collapse to one stack when closed.
- R17 Controls near the hinge when partially folded: keep them clear of the division's frame from the reserved-region APIs. ← catalog (T1)
- R18 Split views: safe areas are often asymmetric, handle each side; use the system split containers.
- R19 Size classes do not encode where the hinge is; use reserved regions with `GeometryReader` / `GeometryProxy`. ← catalog
- R20 A text-labelled menu button in the vertical bar: use a symbol or let it go to overflow; give items both a title and a symbol.
- R21 Which pane is primary and which secondary in a split arrangement has no fixed rule; it follows the app's content hierarchy. ← catalog (input I1)
- R22 Do not assume fixed sizes; prefer changing aspect ratio over letterboxing, and fill unavoidable padding with artwork.
- R23 Figma and Sketch kits are on Apple Design Resources.
Nothing in this part covers laptop or tent layout or keyboard placement.

Testing
- Simulator can't show reachability, asymmetric safe areas and weight distribution; validate targets and bar placement on device. (#89)
- Apple's own agent skill: **App Resizability** in Xcode 27.1 (SwiftUI + Duo). (#86, #88)

## B. Community-measured metrics (to be re-measured by the probe; cite as provisional)
From liquid_glass_widgets #348 (Flutter `MediaQuery.padding`, simulator) and the `foldable` package README:

| Pose | Window (pt) | Insets L,T,R,B | Bars |
|---|---|---|---|
| Closed, outer portrait | 466 × 678 | 0, 0, 84, 34 | vertical, right |
| Closed, outer landscape | 678 × 466 | 84,0,0,34 or 0,0,84,34 | vertical, camera side |
| Open, inner landscape | 951 × 669 | 0, 0, 84, 34 | vertical, right |
| Open, inner portrait | 669 × 951 | 0, 82, 0, 34 | horizontal |
| Fold (division) width | 40 pt (inner, 951 × 669) | | |
| Half of inner width | 455.5 pt (sven-ericmolzahn/iphone-duo-probe) | | |

Other community observations: vertical tab bar with 4 tabs ≈ 48 × 212 pt capsule; bottom-bar items end 24 pt above the screen edge; `reservedRegions` empty on first geometry evaluation, populated later (iphone-duo-probe); fold reaches Flutter display features ~1 s after the device rests half open (LeanCode's Flutter package duo_kit).

## C. What real apps are actually hitting (GitHub, Sept 21 – Oct 23)

| Repo / issue | Archetype | Reported problem or decision |
|---|---|---|
| staude/amiscara-agents #215 | chat/agent client | Custom input bar and pane header must become `.toolbar` items or get a deliberate layout; candidate strip items: pane switcher, new prompt, stop, upload, dictation |
| vdhamer/Photo-Club-Hub #848 | tabbed photo app | Tab bar vs sidebar on inner must be chosen deliberately; which bar compresses first; single-Done sheets should disable the vertical bar; unclear whether `tabBarMinimizeBehavior` does anything vertical |
| hsilviu05/SnapWorth #361 | result/hero screens | Fixed 360 pt full-width hero with `scaledToFill` crops heavily on the wide display and runs under the vertical bar |
| ksharma-xyz/KRAIL #2041 | list + map (Compose MP) | Align list/map split with the fold; book → list one side / map other; laptop → map upright half, list + controls flat half; if a half is narrower than the 320 dp map minimum, show one pane, don't straddle |
| tarioto/Mettiti #113 | card feed | Full-width cards become wide empty strips on inner; a card can sit across the crease; fix: two equal columns with the gutter on the fold, one column anywhere narrower |
| Graphite-Note/Graphite #56, #63 | document editor | Tabs button needs a symbol to move to the side bar; bottom bar split into groups with visibility priorities; More → system overflow; divider/palettes/banner/Read-Aloud player placed around the fold; even library columns; keyboard Undo/Redo only in compact width; "what does a single document do across the fold with the sidebar hidden" |
| llun/schrift #187 | split-view notes | Fold handling never engaged on an *unfolded* Duo because the inactive division is dropped by the default query → fixed with `.includeInactive` |
| OpenCoven/coven-cave #6193 | chat column | Keep chat column, centered cards, sheets clear of the active division and inner camera occlusion; gated by `#available`, deployment target iOS 18; UI tests on the Duo simulator instead of idiom checks; before/after screenshots as acceptance evidence |
| IanHoar/hop-tales #35 | reading | Product rule "card, ball, mic pill and rail never move" conflicts with automatic re-layout on fold; needs a deliberate answer |
| jusso-dev/duo-fortune-ball #29 | single-object toy | Always use one `ArrangementView(.split)` so fold/unfold animates instead of rebuilding; object one side, controls the other |
| MWBMPartners/MeedyaManager #228 | — | Closed as not planned: no iPhone version exists yet |

## D. Recurring defect classes visible so far (seed for the taxonomy; confirm against the corpus)
1. Custom bar does not go vertical; content runs under the system vertical bar.
2. Control or card straddles the active division.
3. Full-width content becomes an empty wide strip on the inner display (no column reflow).
4. Fixed-size hero/media crops or ignores asymmetric safe areas.
5. Fold handling never engages because inactive division regions were not requested.
6. Layout rebuilt instead of animated across fold (view identity lost).
7. Sheet/overflow decisions left to defaults where the app type wants the other compression behavior.
8. Text-only or segmented controls stranded horizontal while everything else moved.
9. Product rules ("these never move") not reconciled with system displacement.
10. Content under the inner camera occlusion when the camera is active; touches swallowed.

## Sources
- https://developer.apple.com/forums/thread/847644 (Group Lab summary; read in full: chars 0–100000 on 2026-10-24, the remainder on 2026-10-26 as R1–R23)
- https://antongubarenko.substack.com/p/iphone-duo-uikit-q-and-a-forums (digest of threads 847769–848078)
- https://github.com/sdegenaar/liquid_glass_widgets/issues/348
- https://github.com/staude/amiscara-agents/issues/215 · https://github.com/vdhamer/Photo-Club-Hub/issues/848 · https://github.com/hsilviu05/SnapWorth/issues/361 · https://github.com/ksharma-xyz/KRAIL/issues/2041 · https://github.com/tarioto/Mettiti/issues/113 · https://github.com/Graphite-Note/Graphite/issues/56 · https://github.com/Graphite-Note/Graphite/issues/63 · https://github.com/llun/schrift/pull/187 · https://github.com/OpenCoven/coven-cave/issues/6193 · https://github.com/IanHoar/hop-tales/issues/35 · https://github.com/jusso-dev/duo-fortune-ball/pull/29 · https://github.com/MWBMPartners/MeedyaManager/issues/228
- https://github.com/sven-ericmolzahn/iphone-duo-probe (455.5 pt half, first-frame empty regions)
