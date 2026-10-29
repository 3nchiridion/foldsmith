# HIG — Designing for iPhone Duo

Source: https://developer.apple.com/design/human-interface-guidelines/designing-for-iphone-duo
JSON: https://developer.apple.com/tutorials/data/design/human-interface-guidelines/designing-for-iphone-duo.json
Published 2026-09-09. No code. No numeric metrics. Close paraphrase, order preserved.

## Structure
Intro → Anatomy (Device poses) → Best practices → Dynamic layouts (Reserved regions / Split views / Arrangement views) → Vertical controls → Resources → Change log

## Anatomy
- Two displays, each with its own front camera; center hinge; many ways to hold and set down.
- Closed: outer display; system puts toolbars and tab bars on the side to maximize vertical content space. Landscape on inner: controls stay on the side for consistency.
- Outer camera: in a corner, always visible, vertically aligned with the side controls. Inner camera: behind the display, hidden until active.
- Poses named in prose: partially folded like a book; flat on a surface; standing on its edges. Alt text: "illustration of six device poses". Poses are not individually named or defined.
- Rules: no custom layout per pose; size classes (compact width = outer, regular width = inner) cover every pose; don't reinvent the app on resize; test poses in Xcode Device Hub.

## Best practices
1. Build to resize: size classes, layout margins, safe-area insets; no fixed widths, no display-specific dependencies.
2. Consistent across displays: same functionality and element state on both; same hierarchy, optionally one more level on inner. Mail: list OR email closed; list AND email open.
3. Same functionality across poses: controls may overflow, content may move or resize, but everything stays reachable.
4. Follow the system vertical layout for bars; refine only.
5. Games: may lock orientation but must fill the screen as the pose changes; prefer changing aspect ratio over letterbox/pillarbox; if unavoidable, fill padding with artwork.

## Dynamic layouts
### Reserved regions (three)
- Outer camera: always present; expands into Dynamic Island for Live Activities; system arranges side elements around it.
- Inner camera: present only while active; UI moves aside when it activates.
- Folding region: conditional; when partially open it divides the inner display into usable regions and excludes the center.
- System moves alerts, context menus and sheets for the fold automatically. Split views adjust column widths and margins to the inner display's symmetry. Custom components: `ReservedRegion`.
- Prefer containers that adapt (Notes split view equalizes pane widths when folded). Grids: prefer an even column count. Avoid extreme layout changes on fold; move only what must move; small adjustments over rearrangement.

### Split views
- Expand on inner, collapse to one pane on outer (regular ↔ compact). Adapt to reserved regions automatically. `NavigationSplitView` / `UISplitViewController`.

### Arrangement views
- Container holding primary + secondary, arranged by size, orientation and reserved regions.
- Split: divides area; horizontal when wider than tall, vertical when taller. Overlay: primary atop secondary; when partially folded, each takes a side.
- Can limit split axes; can collapse overlay secondary.
- Use when the layout already resembles one: HStack/VStack → split; ZStack → overlay.
- Keep navigation containers outside the arrangement view.

## Vertical controls
- Bars move to the side except inner-display portrait, which has room for horizontal bars.
- Side stack (top → bottom on the outer display): Dynamic Island, status bar, toolbar (incl. navigation buttons), tab bar.
- Split View multitasking: each app's controls on its outer edge.
- Vertical controls stay aligned with hardware: same position relative to the outer camera, same side in RTL.
- Account for asymmetry: controls on one edge; use safe areas (including the far edge in Split View).
- Keep control positions consistent across poses.
- Standard order: primary navigation (Back/Close) at top, then prominent actions (Done), then original groups; system adds vertical space between top-bar and bottom-bar items.
- Overflow is bottom → top by default; `ToolbarItemVisibilityPriority` / `UIBarButtonItemVisibilityPriority`; keep frequent actions (Compose, New Note) and status-bearing items (badges) visible longest.
- Don't override default bar placement in general.
- Full display width is acceptable for bar-less, immersive, non-scrolling screens if nothing conflicts with Dynamic Island / status bar (Calculator); background or header may span while scrollable content stays inset.
- Group items with `ToolbarItemGroup` / `UIBarButtonItemGroup`; no fixed spacing.
- Controls live near the content they affect (Mail: list controls above the leading pane, not on the trailing edge).
- Title + symbol for every non-text item; symbols preferred; text labels stay horizontal.
- Compression: navigation-focused apps overflow toolbar items first (default); task-oriented apps minimize the tab bar instead. `ToolbarVerticalCompressionBehavior` / `UIVerticalBarCompressionBehavior`.
- System overflow menu: `ToolbarOverflowMenu` / `UINavigationItem.additionalOverflowItems`; ellipsis reserved for overflow.

## Image alt text (evidence about system-app behavior)
- Mail outer: contents of an email. Mail inner: list leading + email trailing.
- Calculator: iPhone 16 = 4 columns × 5 rows; Duo outer = 5 columns × 4 rows.
- Mail inner panes: leading-pane controls at top of pane; trailing-pane controls vertical on trailing edge.
- Outer display trailing stack labelled: Dynamic Island, status bar, toolbar, tab bar.
- Outer landscape, tab-bar-preserved: toolbar collapsed to overflow. Toolbar-preserved: tab bar collapsed to one control.
- Notes open: leading list pane narrower than trailing pane. Notes folded: panes equal width.
- Split arrangement: primary fills leading half, secondary trailing half. Overlay: secondary fills display, primary smaller and bottom-aligned.

## Links Apple attaches
HIG: Layout, Layout#Size-classes, Designing for iOS, Designing for games, Split views, Toolbars.
Docs: Preparing your app for iPhone Duo; Xcode Device Hub; SwiftUI ArrangementView, ReservedRegion, ToolbarItemGroup, ToolbarItemVisibilityPriority, ToolbarOverflowMenu, ToolbarVerticalCompressionBehavior, GeometryProxy.safeAreaInsets; UIKit UIArrangementViewController, UIBarButtonItemGroup, UIBarButtonItemVisibilityPriority, UINavigationItem.additionalOverflowItems, UISplitViewController, UIVerticalBarCompressionBehavior, UIView.ReservedRegion, UIView.safeAreaInsets.
External: Apple Design Resources (margins and safe areas); App Store screenshot specifications.
