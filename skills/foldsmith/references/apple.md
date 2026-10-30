# Apple's rules for iPhone Duo, condensed

Every line paraphrases a source in `raw/apple-docs/` and carries its citation: `tt-<id> m:ss` is a tech talk chapter's
start time, `hig <section>` the HIG article "Designing for iPhone Duo", `overview` the Technology Overview "Preparing
your app for iPhone Duo". API names are the ones the iOS 27.1 SDK declares (`raw/sdk/DIFF.md`), which differ from the
doc pages in places. No transcript text is quoted.

## Layout in general
- Lay out from size classes, layout margins and safe-area insets; never from device identity, idiom, orientation or
  screen size [hig best practices 1; tt-111461 2:46; overview].
- The outer display is compact width; the inner display is regular in both dimensions and ignores supported interface
  orientations [tt-111461 2:46].
- No layout per pose; one experience that adapts [hig anatomy; tt-111466 3:42, 10:01].
- Same functionality and element state on both displays; the inner display may add one level of hierarchy (Mail: list
  or message closed, list and message open) [hig best practices 2, 3].
- Safe areas are asymmetric: inset each side on its own, never double one side [tt-111461 6:06].
- `UIScreen.main` is ambiguous on two displays; use the scene, environment or trait collection [tt-111461 3:57].

## Reserved regions
- Three regions: the outer camera (always active), the inner camera (active while in use) and the fold, a division
  that is active only while the phone is part folded [hig reserved regions; tt-111463 7:50].
- `GeometryProxy.reservedRegions(kind:options:layoutDirectionBehavior:)` with `kind: .division | .occlusion`;
  `options` defaults to active regions only, `.includeInactive` adds the rest; frames already include the margins
  [tt-111463 6:39; api-swiftui; raw/sdk/DIFF.md]. UIKit: `UIView.reservedRegions(kind:options:)`.
- An inactive division still matters: use it for an even column count, and to reserve space so layout does not jump
  when the fold activates [tt-111463 7:50; api-swiftui].
- Regions are empty on the first evaluation and arrive within 0.1–0.3 s [raw/METRICS-NOTES.md].
- Most apps need no query: split views, tab bars, alerts, menus and sheets adapt on their own; scroll containers do not
  split content at a division [api-swiftui; tt-111463 8:39].

## Around the fold
- Content spanning the fold in book reads badly, like a photo across a book's spine [tt-111463 1:29].
- Displacement: move what must move into the space that is available, one control, a container or a section at a
  time, and no further than the visual relationships allow [tt-111463 2:26].
- Continuously scrolling content (articles, feeds, documents, lists) must not displace [tt-111463 2:26]; interactive
  elements stay away from the hinge except inside scrollable content [tt-111466 9:28].
- Where content goes depends on the pose: in book, alerts move to the trailing side; propped like a laptop, viewed
  content goes on the top half and controls on the bottom half [tt-111463 4:00].
- Adapt beyond position: Reminders keeps an even 50/50 split; Fitness keeps the outer margins and widens the spacing
  at the hinge so each container stays in its region [tt-111463 5:12].
- Grids prefer an even column count; avoid extreme layout changes on a fold; small adjustments over rearrangement
  [hig reserved regions].

## Containers
- Prefer system containers: `NavigationStack`, `NavigationSplitView`, `TabView`, `List`, `ScrollView` adapt on their
  own [tt-111463 8:39; overview].
- Split views expand on the inner display, collapse to one pane on the outer, and adjust column widths to the inner
  display's symmetry [hig split views; hig reserved regions].
- The inner display wants its width used: split views, two columns reflowing from one, a tab bar as sidebar for dense
  apps (`defaultTabBarPlacement(.sidebar)`) [tt-111466 7:34; tt-111461 5:01].
- `ArrangementView` (UIKit `UIArrangementViewController`): split for a main/detail pair neither of which may be hidden,
  overlay for a foreground over a background; HStack/VStack → split, ZStack → overlay [tt-111463 9:20, 14:39].
  Keep navigation containers outside it, and never put it inside `List` or `ScrollView` [tt-111463 16:09; overview].
- Overlay when part folded: primary trailing or bottom of the fold, secondary leading or top [overview].

## Sheets and alerts
- The system moves alerts, context menus and sheets for the fold [hig reserved regions]; part folded, sheets slide off
  the fold [tt-111466 8:36].
- `presentationPlacement(_:)` with `.automatic`, `.leading`, `.center`, `.trailing` (27.0); on the inner display a
  trailing sheet gets a vertical bar, a centred or leading one horizontal items [overview; tt-111462 3:09].

## Bars
- Bars become one vertical stack on the side of the outer display, and on the inner display when it is wider than
  tall; inner portrait keeps horizontal bars [hig vertical controls; tt-111462 0:28].
- Only bars provided by navigation containers move: custom `UIToolbar`, `UINavigationBar` or `UITabBar` content is not
  considered [tt-111462 2:00].
- Order: primary navigation (Back, Close) at the top, prominent actions (`topBarPinnedTrailing`) next, then the
  original groups [tt-111462 4:29].
- Every item needs a title and a symbol; text-only and custom-view items never go vertical; prefer symbols
  [tt-111462 5:56, 9:00; overview]. `ToolbarItemAxisBehavior` (`.horizontalOnly`, `.verticalPreferred`) [raw/sdk/DIFF.md].
- Custom views read `toolbarVerticalEdge` (`HorizontalEdge?`, nil when no vertical bar) [tt-111462 10:07; raw/sdk/DIFF.md].
- Overflow from bottom to top by default; `visibilityPriority`; keep frequent and badge-bearing items visible longest;
  merge app menus into `ToolbarOverflowMenu` [tt-111462 11:40, 13:10].
- Don't override bar placement in general; opt out (`toolbarVerticalBehavior(.disabled)`) only for single-page,
  bottom-heavy apps or simple sheets [hig vertical controls; tt-111462 14:21].

## Hinge, scenes, tools
- Hinge angle and status (`onHingeChange`, `UIHingeInteraction`) are for interactions and effects; layout uses the
  arrangement and region APIs [tt-111464 2:35].
- New windows cannot be created on the outer display [tt-111464 3:38].
- Apple's own agent skill, App Resizability (Xcode 27.1), covers API-level migration for SwiftUI and iPhone Duo
  [tt-111461 9:12]. This skill does not repeat it: it adds the pattern choice and the pose evidence.
