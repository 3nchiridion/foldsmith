# Technology Overview — Preparing your app for iPhone Duo

Source: https://developer.apple.com/documentation/TechnologyOverviews/preparing-your-app-for-iphone-duo
JSON: https://developer.apple.com/tutorials/data/documentation/TechnologyOverviews/preparing-your-app-for-iphone-duo.json

## Sections
Overview → Address common layout and resizing considerations → Optimize bars for vertical presentation → Organize items in your bars → Arrange views in different poses → Adapt to reserved regions → Improve camera handling → Videos

## Rules (close paraphrase)
- Build with latest Xcode (Xcode 26-and-earlier builds don't extend under status bar/camera). Test in simulator or device first.
- Audit checklist Apple gives: both displays, closed/open/partially folded; rotate in each pose; every view, sheet, popover resizes in every supported orientation and pose; bars present vertically; views/sheets/popovers positioned awkwardly when folding or opening; controls that fall in the fold.
- Prefer system containers (split views, tab bars, arrangement views, navigation stacks). Size relative to container; base calculations on scene/containing-view bounds; Auto Layout in UIKit; automatic trait tracking; never `userInterfaceIdiom` or `UIInterfaceOrientation` for layout.
- Bars vertical on outer when closed, and on some inner views in leading/trailing position when open. Context: inspectors horizontal; split view sidebar/content horizontal, detail vertical; outer sheets vertical by default (`toolbarVerticalBehavior` / `preferredVerticalBarBehavior` to disable); inner sheets horizontal for centered/leading, vertical for trailing (`presentationPlacement` / `preferredPlacement`).
- Custom views read `toolbarVerticalEdge` / `verticalBarEdge`. Hero/background under a vertical bar: `backgroundExtensionEffect()` / `UIBackgroundExtensionView`.
- Item order: Back/Close top, then Done; `topBarPinnedTrailing` / `pinnedTrailingGroup`; custom Back via `cancellationAction` / `leadingItemGroups`. `axisBehavior`, `visibilityPriority`, `ToolbarOverflowMenu` / `additionalOverflowItems`.
- Vertical presentation uses the icon; horizontal uses icon or title (prefers icon); overflow uses both. **Title-only and custom-view items are never presented vertically.**
- Split: side by side when wider than tall; primary top / secondary bottom when taller; adjusts for the fold; maps from HStack/VStack. Overlay: primary over secondary when no division is active (closed or fully open); when partially open, **primary → trailing or bottom relative to the fold, secondary → leading or top**; maps from ZStack. `.split.axes(.horizontal)` limits axis. Don't put an arrangement view inside a navigation split view, list, scroll view or other container that could hide part of it.
- Divisions vs occlusions; fold active when partially open, inactive when fully open. Inner camera occludes when active; outer camera always occludes. SwiftUI `GeometryProxy.reservedRegions(kind:options:layoutDirectionBehavior:)`; UIKit `UIView.reservedRegions(kind:options:)`.
- Camera: three cameras (outer-display front, inner-display front, rear); on open/close/rotate the app may switch displays and the camera may face the other way; when fully open with the rear camera, the outer display can show content too.

## Explicitly absent
First-frame behavior, scene lifecycle on fold, state preservation, split-view minimum sizes, outer-display window creation, Info.plist keys. None mentioned.

## Symbols
SwiftUI: `GeometryReader`, `GeometryProxy.reservedRegions(kind:options:layoutDirectionBehavior:)`, `ReservedRegion`, `ArrangementView`, `toolbar(content:)`, `toolbarVerticalBehavior(_:)`, `presentationPlacement(_:)`, `toolbarVerticalEdge`, `backgroundExtensionEffect()`, `ToolbarItemPlacement.topBarPinnedTrailing`, `.cancellationAction`, `ToolbarContent.axisBehavior(_:)`, `ToolbarContent.visibilityPriority(_:)`, `ToolbarOverflowMenu`.
UIKit: `UIView.ReservedRegion`, `UIView.reservedRegions(kind:options:)`, `UIArrangementViewController`, `UIBackgroundExtensionView`, `UIBarButtonItem.axisBehavior`, `UIBarButtonItem.visibilityPriority`, `UINavigationItem.pinnedTrailingGroup`, `.leadingItemGroups`, `.additionalOverflowItems`, `UIViewController.preferredVerticalBarBehavior`, `UISheetPresentationController.preferredPlacement`, `UITraitCollection.verticalBarEdge`.

## Linked
HIG Designing for iPhone Duo; TN3210 iPhone Mirroring; Adopting Liquid Glass; UIKit Automatic trait tracking; Adapting your app when traits change; Xcode Running your app on simulated or physical devices; AVKit Choosing a camera by the direction it faces; AVFoundation Registering a camera capture accessory on iPhone Duo; videos 111461–111466, wwdc2026/278, wwdc2025/282.
