# DIFF — docs notes vs the iOS 27.1 SDK

SDK: `iPhoneSimulator27.1.sdk`, Xcode 27.1 (27A9275). Source: `scripts/extract-sdk.sh` output in this folder
(the `*.txt` excerpts are verbatim Apple SDK text, so they are git-ignored; run the script to regenerate them),
plus direct reads of `SwiftUICore`/`SwiftUI`/`UIKit` `arm64-apple-ios-simulator.swiftinterface` and UIKit headers.
Compared against `raw/apple-docs/api-swiftui.md` and `raw/apple-docs/api-uikit.md` (2026-10-24).

Legend: **MISMATCH** = docs notes are wrong or would mislead code · **GAP** = docs notes were silent or
"default unknown", SDK fills it · **OK** = confirmed.

## The two things Step 1 asked for explicitly

**`DeviceHinge.Status` cases (SwiftUI):** a `struct` (not an enum) with `static var closed`, `partiallyOpen`,
`fullyOpen`. Hashable, Sendable. No `unknown`, no `CustomStringConvertible`, so `switch` needs a `default`
and `"\(status)"` prints the struct dump, not a name.
UIKit's counterpart `UIHinge.Status` is an `NS_ENUM` with **four** cases: `unknown = 0`, `closed`, `partiallyOpen`, `fullyOpen`.

**`ToolbarVerticalEdge` type:** does not exist. `EnvironmentValues.toolbarVerticalEdge` is `HorizontalEdge?`
(get-only). `nil` = no vertical toolbar. UIKit uses its own `UIVerticalBarEdge` (`.unspecified`, `.leading`, `.trailing`).

## SwiftUI

| Name | Docs notes said | SDK says | Kind |
|---|---|---|---|
| `ArrangementView.init(primary:secondary:)` | plain closures | `@ContentBuilder` closures (not `@ViewBuilder`); struct is `nonisolated`, `~Sendable` | MISMATCH (minor) |
| `ArrangementViewStyle` | three built-in styles | public `@MainActor` protocol with `makeBody(configuration:)`: custom styles are possible. Static accessors `.automatic`, `.split`, `.overlay` | GAP |
| `overlayArrangementEdge(_:)` | one modifier, "type not shown", horizontal edge | **two overloads**: `(_ edge: VerticalEdge?)` and `(_ edge: HorizontalEdge?)` | MISMATCH |
| `overlayArrangementZIndex` | missing from doc page; seen in talk | `EnvironmentValues.overlayArrangementZIndex: Int { get set }` | GAP → confirmed |
| `splitArrangementAxis` | missing from doc page; seen in community code | `EnvironmentValues.splitArrangementAxis: Axis? { get set }` | GAP → confirmed |
| `splitArrangementFixedLayoutSize(horizontal:vertical:)` | defaults not shown | `horizontal: Bool = true, vertical: Bool = true` | GAP |
| `splitArrangementLayoutRatio(min…:ideal…:max…:)` / `splitArrangementLayoutSize(…)` | all `CGFloat?`, defaults not shown | every parameter `= nil` | GAP |
| `ReservedRegion` conformances | `Identifiable, Hashable, Equatable, Sendable, CustomStringConvertible, …` | `Equatable, Hashable, Identifiable, Sendable` only. **Not** `CustomStringConvertible`; `ID` and `Kind` aren't either | **MISMATCH**: string interpolation in `Probe/DuoProbe/ProbeRoot.swift` must log fields explicitly |
| `ReservedRegion` properties | `var` | all get-only | OK (read-only) |
| `GeometryProxy.reservedRegions(kind:options:layoutDirectionBehavior:)` | `options` and `layoutDirectionBehavior` defaults unknown | `options: QueryOptions = []`, `layoutDirectionBehavior: LayoutDirectionBehavior = .mirrors` | GAP |
| `ReservedRegion.QueryOptions` | `static var includeInactive` | `@frozen OptionSet`, `rawValue: Int` | OK |
| `DeviceHinge` | `Equatable, Hashable, Sendable`; `angle: Angle`, `status` | `Hashable, Sendable`; same members | OK |
| `DeviceHingeContext` | `hinge: DeviceHinge?`, "other members not shown" | `hinge` is the **only** member; `Equatable, Sendable` | GAP |
| `onHingeChange(isEnabled:_:)` | `isEnabled` default unknown | `isEnabled: Bool = true`; action `@escaping (_ oldContext:, _ newContext:) -> Void` | GAP |
| `toolbarVerticalBehavior(_:)` | `.disabled` | `ToolbarVerticalBehavior` struct: `.automatic`, `.disabled` | OK |
| `toolbarVerticalCompressionBehavior(_:)` | `.prefersToolbarItems` | `.automatic`, `.prefersToolbarItems`, **`.prefersTabBar`** | GAP (third case undocumented) |
| `ToolbarItemVisibilityPriority` | named only | `.automatic`, `.low`, `.high`, `init(lowerThan:)`, `init(higherThan:)`, `Comparable`; `.visibilityPriority(_:)` on `ToolbarContent` and `CustomizableToolbarContent`. **Available iOS 27.0**, not 27.1 | GAP |
| `ToolbarContent.axisBehavior(_:)` | type `AxisBehavior` | type is **`ToolbarItemAxisBehavior`**: `.automatic`, `.horizontalOnly`, `.verticalPreferred` | **MISMATCH** (type name) |
| `ToolbarOverflowMenu` | named only | `struct ToolbarOverflowMenu<Content: View>: ToolbarContent, CustomizableToolbarContent` | OK |
| `ToolbarItemPlacement.topBarPinnedTrailing` | named only | exists; unavailable on macOS/tvOS/watchOS | OK |
| `presentationPlacement(_:)` | named only | `PresentationPlacement`: `.automatic`, `.leading`, `.center`, `.trailing`. **Available 27.0** | GAP |
| `backgroundExtensionEffect()` | named only | also `backgroundExtensionEffect(isEnabled:)` | GAP |
| `sceneAccessory` / `CameraCaptureAccessory` / `onAvailabilityChange` | named only | `sceneAccessory(@ContentBuilder content:)` where `C: SceneAccessoryContent`; `CameraCaptureAccessory<Content: View>: SceneAccessoryContent`; `onAvailabilityChange(perform: (_ isAvailable: Bool) -> Void)` is on `SceneAccessoryContent`, not `View` | GAP |
| `defaultTabBarPlacement(_:)` | `.sidebar` | `AdaptableTabBarPlacement`: `.automatic`, `.tabBar`, `.sidebar` | OK |
| Availability | "Introduced 27.1" per platform | `@available(anyAppleOS 27.1, *)` on the Duo layout APIs | OK |

## UIKit

| Name | Docs notes said | SDK says | Kind |
|---|---|---|---|
| `UIArrangementViewController` methods | `animated: Bool` (no default) | Swift methods are `final`; `updateArrangement(_:animated: Bool = false)` and `setViewController(_:for:animated: Bool = false)` | GAP |
| `updateArrangement<A>` constraint | "presumably `A: Arrangement`" | `where A: UIArrangementViewController.Arrangement` (protocol nested in the class) | OK |
| `Arrangement` protocol | members not shown | `associatedtype ViewProperties`, `var defaultViewProperties`, `mutating func setViewProperties(_:for:)` | GAP |
| UIKit split ratio/size API | "none documented, check SDK" | `UISplitArrangement.ViewProperties { width: DimensionRange, height: DimensionRange, layoutPriority: CGFloat }`; `DimensionRange { minimum, preferred, maximum }`; `Dimension`: `.automatic`, `.intrinsic`, `.fractional(_:)`, `.absolute(_:)`. Apply with `setViewProperties(_:for:)` | **GAP, major**: this is the forum's "split ratio via view properties" |
| `UIOverlayArrangement` | `axes(_:)` only | also `ViewProperties { edge: NSDirectionalRectEdge }` via `setViewProperties(_:for:)` | GAP |
| `ViewPlacement` | `.primary`, `.secondary` (ObjC adds `None`) | same; Swift `placement(for:)` returns `nil` where ObjC returns `…PlacementNone` | OK |
| `ViewState` | no members listed; talk reads `.zIndex` | `zIndex: Int`, `splitAxis: UIAxis`, `isHidden: Bool` (get-only) | GAP |
| `UIViewController.arrangementViewController` | not in notes | nearest-ancestor arrangement VC (readonly, optional) | GAP |
| `UIView.ReservedRegion` conformances | `Equatable, Hashable, Identifiable` | same, and **not `Sendable`** (SwiftUI's is). `ID` and `Kind` **are** `CustomStringConvertible` here, unlike SwiftUI | MISMATCH between frameworks |
| `UIView.ReservedRegion` members | `frame`, `isActive`, `kind`, `margins` | also `let id` | GAP |
| `UIView.reservedRegions(kind:options:)` | default "active only" | `@MainActor`, `options: QueryOptions = []`; **no `layoutDirectionBehavior` parameter** in UIKit | GAP |
| `ReservedRegion.QueryOptions.rawValue` | — | UIKit `UInt`, SwiftUI `Int` | note |
| `UIHingeInteraction` | named only | **Objective-C-only class, no Swift overlay**, so it is absent from the `.swiftinterface` (the script's guard warns about it for that reason). Swift: `UIHingeInteraction(updateHandler: (UIHingeInteraction, UIHingeInteraction.Update) -> Void)`, `isEnabled`. `Update.hinge: UIHinge?`, `nil` when the view leaves a hierarchy that provides hinge updates. Handler fires once with the initial state | GAP |
| `UIHinge` | — | `status: UIHinge.Status` (`unknown`/`closed`/`partiallyOpen`/`fullyOpen`), `angle: CGFloat` **in radians**; header says prefer `status` and don't depend on angle update rate | GAP; SwiftUI uses `Angle` and has no `unknown` |
| `UIVerticalBarBehavior` | `.disabled` | `.automatic`, `.disabled`. `preferredVerticalBarBehavior` is readonly (override it), plus `childForPreferredVerticalBarBehavior` and `setNeedsUpdateOfVerticalBarConfiguration()` | GAP |
| `UITraitCollection.verticalBarEdge` | named only | `UIVerticalBarEdge` (`.unspecified`, `.leading`, `.trailing`), declared in `UIVerticalBarEdge.h`, not `UITraitCollection.h`. Reports the preferred edge **even when no bar is visible**; `.unspecified` where the system never uses a vertical bar. Observe via `systemTraitsAffectingVerticalBarEdge` | GAP |
| `UIVerticalBarCompressionBehavior` | `.prefersBarItems` | `.automatic`, `.prefersBarItems`, **`.prefersTabBar`**; set on `UINavigationItem.verticalBarCompressionBehavior` | GAP (third case undocumented) |
| `UIBarButtonItem.axisBehavior` | `.horizontalOnly`, `.verticalPreferred` | `UIBarButtonItem.AxisBehavior`: `.automatic` (default), `.horizontalOnly`, `.verticalPreferred`; 27.1 | OK |
| `UIBarButtonItemVisibilityPriority` | named only | extensible NSInteger enum: `.standard` (default), `.low`, `.high`. **27.0**. Note SwiftUI calls the default `.automatic` | GAP |
| `UINavigationItem.pinnedTrailingGroup`, `additionalOverflowItems` | listed as Duo APIs | exist since **iOS 16**: pre-existing, not new for Duo | MISMATCH (provenance) |
| `UISheetPresentationController.preferredPlacement` | named only | `UISheetPresentationControllerPlacement`: `.automatic`, `.leading`, `.center`, `.trailing`; **27.0** | GAP |
| `UIView.LayoutRegion.bar(onEdge:extent:)` | from forums | exists, two overloads: `UIRectEdge` and `NSDirectionalRectEdge` | OK (confirms forum) |

## Objective-C-only APIs the script's Swift search missed

`extract-sdk.sh` found no Swift-interface hits for these. Like `UIHingeInteraction`, they are all in the UIKit
headers. Several are **older than Duo**, so the notes' "named by Apple for Duo" list mixes new and existing API:

| Name | Header | Available |
|---|---|---|
| `UIBackgroundExtensionView` | `UIBackgroundExtensionView.h` | iOS 26.0 |
| `UIWindowSceneActivationAction` | `UIWindowSceneActivationAction.h` | iOS 15.0 |
| `UISceneAccessory`, `UIViewController.registerSceneAccessory(_:)` | `UISceneAccessory.h`, `UIViewController.h` | iOS 27.0; unavailable on Mac Catalyst |
| `UINavigationItem.leadingItemGroups` | `UINavigationItem.h` | iOS 16.0 |
| `UITabBarController.Sidebar.preferredPlacement` | `UITabBarControllerSidebar.h` | iOS 27.0 |

Only the Duo layout APIs above (arrangements, reserved regions, hinge, vertical bar) are 27.1.

## Changes this implies elsewhere

- `Probe/DuoProbe/ProbeRoot.swift`: don't interpolate `ReservedRegion`, `ReservedRegion.ID`/`Kind` or
  `DeviceHinge.Status` directly in SwiftUI; map `Status` to a string with a `switch` that has a `default`.
  Read `toolbarVerticalEdge` as `HorizontalEdge?`.
- `scripts/extract-sdk.sh`: the symbol search only reads `.swiftinterface` (plus 8 named headers), so
  Objective-C-only classes look missing. The guard's `UIHingeInteraction` anchor will always warn.

## Probe compile fixes (Step 2, Xcode 27.1, SDK 27.1)

`Probe/DuoProbe/ProbeRoot.swift` was written without an SDK. Against the real one it had 1 error and 4 warnings
(docs/history/MAC-PHASE.md expected 2–5 errors; the predicted `toolbarVerticalEdge` key type and `onGeometryChange` isolation
problems did not occur).

| Line | Problem | Fix |
|---|---|---|
| 103 | error: `UIScreen.scale` is `CGFloat`, `SceneInfo.displayScale` is `Double` | `Double(scene?.screen.scale ?? 0)` |
| 75–76 | warning: `Text` interpolation of `Bool` (`isActive`) is deprecated (unlocalized) | `String(r.isActive)` |
| 101, 104 | warning: `UIWindowScene.coordinateSpace` / `interfaceOrientation` deprecated in iOS 26 | read them from `effectiveGeometry` |
| 77, 99 | no compiler message, but `String(describing: DeviceHinge.Status)` prints a struct dump (see the Status note above) | `statusName(_:)` switch with a `default` |

Still interpolated directly: `ReservedRegion.ID` in the change key (line 58) and the logged `id` fields. That compiles
and is stable within a run, but the text is a debug dump, not a readable name; treat it as an opaque key.
