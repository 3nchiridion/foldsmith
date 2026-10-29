# UIKit API reference notes (from documentation JSON, 2026-10-24)

## UIArrangementViewController
https://developer.apple.com/documentation/uikit/uiarrangementviewcontroller
```swift
@MainActor class UIArrangementViewController: UIViewController
  init()
  func updateArrangement<A>(_ arrangement: A, animated: Bool)        // constraint on A not shown; presumably A: Arrangement
  func setViewController(_ vc: UIViewController?, for placement: ViewPlacement, animated: Bool)
  func viewController(for placement: ViewPlacement) -> UIViewController?
  func placement(for vc: UIViewController) -> ViewPlacement?
  func state(for placement: ViewPlacement) -> ViewState?
  protocol Arrangement           // UIArrangement in ObjC
  struct ViewPlacement           // .primary, .secondary (ObjC also has ...PlacementNone)
  struct ViewState               // doc page lists no members; talk 111463 reads `.zIndex`
struct UISplitArrangement: Arrangement   { func axes(_: UIAxis) -> UISplitArrangement }    // default style
struct UIOverlayArrangement: Arrangement { func axes(_: UIAxis) -> UIOverlayArrangement }
// usage: arrangementVC.updateArrangement(.split.axes(.horizontal)); .overlay.axes(.horizontal)
```
Introduced 27.1 on iOS, iPadOS (both **beta** in metadata), Mac Catalyst, tvOS, visionOS.
No stored properties documented. No ratio/size preference API documented on the UIKit side (SwiftUI has `splitArrangementLayoutRatio` etc.) — **check SDK for UIKit equivalents.**

## UIView.ReservedRegion
https://developer.apple.com/documentation/uikit/uiview/reservedregion
```swift
extension UIView {
  struct ReservedRegion: Equatable, Hashable, Identifiable
    let frame: CGRect              // view coords, points, includes margins
    let isActive: Bool
    let kind: Kind                 // static let occlusion / division
    let margins: UIEdgeInsets
    struct QueryOptions { static let includeInactive }
  func reservedRegions(kind: ReservedRegion.Kind, options: ReservedRegion.QueryOptions /* default: active only */) -> [ReservedRegion]
}
```
Introduced 27.1 on iOS, iPadOS, Mac Catalyst, tvOS, visionOS. Framework views adjust automatically; custom views that place content must query.

## Named by Apple, not yet pulled
`UIHingeInteraction`, `UIVerticalBarBehavior` (`.disabled`), `UIViewController.preferredVerticalBarBehavior`, `UITraitCollection.verticalBarEdge`, `UIVerticalBarCompressionBehavior` (`.prefersBarItems`), `UINavigationItem.verticalBarCompressionBehavior`, `UIBarButtonItem.axisBehavior` (`.horizontalOnly`, `.verticalPreferred`), `UIBarButtonItem.visibilityPriority` / `UIBarButtonItemVisibilityPriority`, `UIBarButtonItem.badge = .count(_)`, `UINavigationItem.pinnedTrailingGroup`, `.leadingItemGroups`, `.additionalOverflowItems`, `UISheetPresentationController.preferredPlacement`, `UIBackgroundExtensionView`, `UICornerConfiguration`, `UIWindowSceneActivationAction`, `UITabBarController.sidebar.preferredPlacement`.
