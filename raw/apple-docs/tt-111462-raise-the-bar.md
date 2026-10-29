# Tech Talk 111462 — Raise the bar with iPhone Duo

Presenters: Anna (UI Frameworks), Maria (Human Interface Designer).
Page: https://developer.apple.com/videos/play/tech-talks/111462/
HD: https://devstreaming-cdn.apple.com/videos/tech-talks/111462/1/9a60db88-d15d-4892-8b56-18e11523d8e4/downloads/tech-talks-111462_hd.mp4?dl=1

## Chapters
0:00 Intro · 0:28 Why bars move to the side · 1:29 Agenda · 2:00 Opt in · 3:09 Shared bar region · 4:29 Order items · 5:56 Prepare toolbar content · 8:00 Control the axis · 9:00 Prefer symbol-only · 10:07 Adapt custom views · 11:40 Overflow menu · 13:10 Visibility priority · 14:21 When to opt out · 14:53 Next steps

## Guidance (close paraphrase)
- Wider aspect ratio → more horizontal space; top/bottom controls move to the side, preserving vertical space and reach. Position persists on inner landscape; inner portrait returns to horizontal bars. Same components, different layout.
- Opt in: (1) rebuild against latest SDK; (2) use bars that navigation containers provide — SwiftUI `toolbar` on `NavigationStack`/`NavigationSplitView`; UIKit `UINavigationController`/`UITabBarController`. Custom `UIToolbar`/`UINavigationBar`/`UITabBar` content is **not considered**.
- Shared bar region = nav, toolbar and tab bar rotated 90° into one vertical stack (Notes: toolbar; Clock: tab bar; Fitness: both). Rules: items go vertical only when their container sits on a display edge; in split views only the detail column participates; expanded inspectors get no vertical bar; outer-display sheets show a vertical toolbar if they have one; inner-display sheets are centered with horizontal items, `preferredPlacement` left → no vertical bar, right → vertical bar; RTL keeps the bar on the hardware side.
- Order top → bottom: primary navigation (back/close; `cancellationAction` / leading item with `leftItemsSupplementBackButton == false`), prominent actions (`topBarPinnedTrailing` / `pinnedTrailingGroup`), then original groups; a vertical spacer separates former top-bar and bottom-bar items.
- Vertical bars: fixed width, flexible item height → symbol-only items. Icon items go vertical; text-only (Edit) stay horizontal. Always supply a title (used in overflow and expanded forms).
- `AxisBehavior`: `.horizontalOnly` for items that flip symbol↔text (custom Select/Done); `.verticalPreferred` for custom views that have a vertical representation. Custom and complex views stay horizontal by default.
- Prefer symbols; badges can turn text+symbol into symbol-only (`badge` API, iOS 26). If text carries standalone information (cart total) keep horizontal. Keyboard accessory bars stay with the keyboard.
- Custom views: must fit the fixed width or adapt; read `toolbarVerticalEdge` (env) / `verticalBarEdge` (trait) — set when items can be vertical, nil otherwise. Vertical bars have no scroll-edge effect by default but do get a background under Reduce Transparency. Flexible spacers are zero on the vertical axis; fixed spacers keep their minimum. Don't add extra spacing.
- Overflow happens more on outer landscape and when keyboard or PiP competes. Toolbars compress first by default (navigation-focused, e.g. Podcasts); task-oriented (Games) can prefer the tab bar compresses — `toolbarVerticalCompressionBehavior(.prefersToolbarItems)` / `verticalBarCompressionBehavior = .prefersBarItems`. Merge app overflow into the system menu (`ToolbarOverflowMenu` / `additionalOverflowItems`); ellipsis reserved for overflow.
- Overflow order bottom → top by default; `visibilityPriority` high/low/custom; prioritize groups first, then items; frequent actions and badge-bearing items overflow last.
- Opt out: single-page bottom-heavy apps (Calculator); control-heavy sheets with one item. `toolbarVerticalBehavior(.disabled)` / `preferredVerticalBarBehavior = .disabled`.
- Next steps: build with latest SDK; audit bars; update custom items for vertical; assign overflow priorities.

## Symbols
SwiftUI: `toolbar`, `ToolbarItem`, `.bottomBar`, `.cancellationAction`, `.topBarPinnedTrailing`, `.axisBehavior(.verticalPreferred | .horizontalOnly)`, `.badge(_:)`, `toolbarVerticalEdge` (env), `.toolbarVerticalCompressionBehavior(.prefersToolbarItems)`, `ToolbarOverflowMenu`, `.visibilityPriority(.high)`, `.toolbarVerticalBehavior(.disabled)`, `preferredPlacement` (sheets).
UIKit: `UINavigationController`, `UITabBarController`, `navigationItem.leftItemsSupplementBackButton`, `navigationItem.leadingItemGroups`, `navigationItem.pinnedTrailingGroup`, `UIBarButtonItem.axisBehavior`, `UIBarButtonItem.badge = .count(7)`, `traitCollection.verticalBarEdge`, `navigationItem.verticalBarCompressionBehavior = .prefersBarItems`, `navigationItem.additionalOverflowItems` + `UIDeferredMenuElement`, `UIBarButtonItem.visibilityPriority`, `preferredVerticalBarBehavior: UIVerticalBarBehavior`.

## Code as published
```swift
// 2:24
NavigationStack { ContentView().toolbar { ToolbarItem(placement: .bottomBar) { ... } } }
// 5:00
ToolbarItem(placement: .cancellationAction) { ... }
navigationItem.leftItemsSupplementBackButton = false
navigationItem.leadingItemGroups = [UIBarButtonItemGroup(...)]
// 5:24
ToolbarItem(placement: .topBarPinnedTrailing) { ... }
navigationItem.pinnedTrailingGroup = UIBarButtonItemGroup(...)
// 8:08 / 8:36 / 8:52
ToolbarItem { ProfileView() }.axisBehavior(.verticalPreferred)
ToolbarItem { SelectOrDoneButton() }.axisBehavior(.horizontalOnly)
let item = UIBarButtonItem(customView: CompassView()); item.axisBehavior = .verticalPreferred
// 9:27
ToolbarItem(...) { InboxButton().badge(7) }
item.badge = .count(7)
// 10:36
@Environment(\.toolbarVerticalEdge) var edge
switch traitCollection.verticalBarEdge { ... }
// 12:23
Tab("Recents", systemImage: "clock") {
  ContentView().toolbarVerticalCompressionBehavior(.prefersToolbarItems)
}
navigationItem.verticalBarCompressionBehavior = .prefersBarItems
// 12:43
.toolbar { ToolbarOverflowMenu { Button("Scan") {}; Button("Connect") {} } }
navigationItem.additionalOverflowItems = UIDeferredMenuElement({ provider in
  provider(self.persistentOverflowItems())
})
// 13:21
ToolbarItem { Button(...) {} }.visibilityPriority(.high)
item.visibilityPriority = .high
// 14:47
NavigationStack { ContentView().toolbarVerticalBehavior(.disabled) }
override var preferredVerticalBarBehavior: UIVerticalBarBehavior { .disabled }
```

Inconsistencies on the page to verify against the SDK: `toolbarCompressionBehavior` (prose) vs `toolbarVerticalCompressionBehavior` (code); `.prefersToolbarItems` (SwiftUI) vs `.prefersBarItems` (UIKit).
