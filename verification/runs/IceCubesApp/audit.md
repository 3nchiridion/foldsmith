# Ice Cubes on iPhone Duo: audit

Unmodified app (`main`, 8614ae9) built with Xcode 27.1 against the iOS 27.1 SDK, captured logged out on the iPhone Duo
simulator `<Duo simulator UDID>` with `tools/capture-app.sh .duo/flows/IceCubesApp.flow
.duo/captures/IceCubesApp/before` (34 min 52 s; shots and accessibility snapshots in `.duo/captures/`, not in git).

## Static scans (`references/detectors-static.md`)
| Class | Result |
|---|---|
| T13 no-scene-lifecycle | none: a SwiftUI `App` (`IceCubesApp.swift`), `UIApplicationSceneManifest` in the project, `SceneDelegate.swift` in DesignSystem |
| T9 inactive-division-ignored | no `reservedRegions` call in the app |
| T14 columns-off-fold | no column width set anywhere |
| T3 custom-bar-not-vertical | no `UIToolbar(`, `UITabBar(`, `UINavigationBar(` |
| T10 stranded-horizontal-item | three hits: `ListAddAccountView.swift:61` (`Button("action.done")`), `EditRelationshipNoteView.swift:57` (`Button("action.cancel")`), and `StatusKit/Editor/MainView.swift:100`, a false positive (the multi-line pattern runs from `ToolbarItems(` to an alert's `Button("OK")`). The two real hits are on screens that need an account (list membership, a note on a followed account): not reachable here, left in `todo`. |

## Screens
Logged out (no account may be created on this simulator), the app has a two-tab `TabView` (Timeline, Settings),
`.sidebarAdaptable`, with `defaultTabBarPlacement(.sidebar)` in regular width (the app's own iOS 27 code): a tab bar on
the outer display (vertical, as the system draws it), a sidebar on the inner display. Every tab owns a
`NavigationStack` and a `RouterPath`; sheets go through `withSheetDestinations`. Logged out, `TimelineTab.onAppear`
presents the Add Account sheet.

| Screen (flow) | Taps on the shut phone | What it is |
|---|---|---|
| add-account | none (launch) | the Add Account sheet over the Trending timeline |
| timeline | Cancel | mastodon.social's Trending timeline |
| status | Cancel; cell 2 | a post's thread (`StatusDetailView`), pushed on the timeline's stack |
| settings | Cancel; Settings | the Settings form |
| settings-display | Cancel; Settings; Display Settings | Display Settings, pushed on the settings stack |

Everything else needs an account (Notifications, Mentions, Explore, Messages, Profile, Bookmarks, Favorites, Lists,
Followed tags, Links, the composer, account settings): in `todo`. A stranger's profile (`AccountDetailView`) is
reachable logged out but only through avatars and names whose labels change with the timeline; no stable tap reaches
it, so it is in `todo` too.

## Findings, screen × pose
`·` = nothing found (detectors and eye). Detectors (`before/detectors.md`): 33 snapshots, 2 findings.

| Screen | closed | closed-sideways | book | laptop | tent | flat-sideways | flat-upright |
|---|---|---|---|---|---|---|---|
| add-account | · | · | **T15** | · | · | · | · |
| timeline | · | · | · | · | · | · | · |
| status | · | · | · | · | · | **T7** | · |
| settings | · | · | · | **T7** | **T7** | **T7** | **T7** |
| settings-display | · | · | · | **T7** | · | **T7** | · |

Evidence:
- **add-account / book, T15** (detector): the sheet sits at 8–467.5 pt, on the leading half, while the fold
  (455.5–495.5) is active. Same as the corpus row (`raw/corpus/defects.csv`). Flat sideways it is centred; laptop and
  tent span the window across the horizontal fold, a scrolling form (exempt).
- **status / flat-sideways, T7** (detector, and the shot): unfolding to flat sideways presented the Add Account sheet
  again over the post the person was reading, though it had been dismissed (Cancel). None of the shut phone's names
  is on the inner display. The capture then lost the screen on the way to flat-upright (the sheet was still up) and
  relaunched.
- **settings / laptop, T7** (capture line): after the laptop shot, the shut phone showed the Add Account sheet, not
  Settings ("lost the screen on the way to tent"). The laptop shot itself is right.
- **settings / tent, flat-sideways, flat-upright, T7** (crash): after the tent shot (taken after the relaunch), closing
  the phone crashed the app: `NSInvalidArgumentException: -[__NSArrayM insertObject:atIndex:]: object cannot be nil`
  in `-[UITabBarController _tabs_rebuildTabBarItemsAnimated:]`, reached from `_UITabBarControllerAdaptiveVisualStyle
  _verticalBarAvailabilityDidChange` during the window's rotation (crash report `Ice Cubes-2026-10-28-083628.ips`).
  The flat-sideways and flat-upright shots show the Home Screen; their snapshots failed ("not running"), so the
  detectors read `n/a` there.
- **settings-display / laptop, flat-sideways, T7** (capture lines): after each of those shots the shut phone showed
  the Add Account sheet instead of Display Settings ("lost the screen on the way to tent", "… to flat-upright").

Looked at and not findings:
- book, every screen: the system's tab sidebar ends at the fold and the tab's content starts after it (sidebar
  0–455.5, content 495.5–867): the boundary is already on the division. No T14, no T1.
- flat-sideways: sidebar ≈ 0–280, content ≈ 280–867, the leading pane narrower and the inactive division ignored,
  as P1 prescribes for that pose.
- laptop, tent, flat-upright: the sidebar is one tap away (toolbar button), the tab's content fills the 669 pt
  window; timeline, post and both settings forms scroll across the horizontal fold (exempt); no fixed control sits on
  it.
- closed, closed-sideways: one pane, the tab bar and the navigation items in the vertical bar (trailing; leading when
  sideways), every item a symbol.

## Classification (step 3)
Decided from the model and the screen's purpose, not from the layout.

| Screen | Relationship | Mode | Why |
|---|---|---|---|
| add-account | hierarchical | editing | a list of servers, each opening into its detail (rules, stats) before signing in; the field is focused at open and the hand types a server address |
| timeline | hierarchical | viewing | a feed whose posts open into their thread, a detail meaningful alone ("feeds-with-detail") |
| status | hierarchical | viewing | the timeline's detail: one post and its context |
| settings | hierarchical | viewing | a list of categories opening into pages; Apple's Settings is the table's own reference for this row |
| settings-display | hierarchical | editing | the settings detail where values are changed (theme, colours, fonts, sliders) |

## Pattern (step 4)
Every screen is `hierarchical`: **Fold-aligned split (P1)**. The app's container is the system tab sidebar, which
already does what P1's split does in book and flat (boundary on the fold; leading pane narrower when flat) and sets no
width. What P1 still changes here:
- add-account / book (T15): the sheet rule, `presentationPlacement(.trailing)` while the book fold is active.
- status, settings, settings-display (T7): the rule every pattern carries, "keep functionality, element state and
  control positions across poses" [hig best-practices 2–3]: a fold must not bring back a dismissed sheet, change the
  selected tab or crash the app.
- tent for `hierarchical / editing` (add-account, settings-display) is `UNJUSTIFIED`; both are unchanged there, so no
  cell is needed.
