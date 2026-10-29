# SwiftUI API reference notes (from documentation JSON, 2026-10-24)

These are doc-page facts, not the `.swiftinterface`. The Mac phase replaces this with the real
interfaces under `raw/sdk/`. Defaults not shown on the doc pages are marked **(default unknown)**.

## ArrangementView
https://developer.apple.com/documentation/swiftui/arrangementview
```swift
nonisolated struct ArrangementView<Primary: View, Secondary: View>: View
init(primary: () -> Primary, secondary: () -> Secondary)
init(_ configuration: ArrangementViewStyleConfiguration)   // when Primary/Secondary are the configuration's types
```
Introduced 27.1 on iOS, iPadOS, Mac Catalyst, macOS, tvOS, visionOS, watchOS.
Computes layout from available size, size class, hardware features.
Styles: `AutomaticArrangementViewStyle` (default; resolves to split), `SplitArrangementViewStyle`, `OverlayArrangementViewStyle`; each has `axes(_: Axis.Set)`.
Modifiers:
```swift
func arrangementViewStyle(_ style: some ArrangementViewStyle) -> some View
func overlayArrangementEdge(_ edge: /* type not shown */) -> some View   // horizontal edge a view occupies when overlay goes horizontal
func splitArrangementFixedLayoutSize(horizontal: Bool, vertical: Bool) -> some View
func splitArrangementLayoutRatio(_ ratio: CGFloat?) -> some View
func splitArrangementLayoutRatio(minHorizontal:idealHorizontal:maxHorizontal:minVertical:idealVertical:maxVertical:) -> some View  // all CGFloat?
func splitArrangementLayoutSize(minWidth:idealWidth:maxWidth:minHeight:idealHeight:maxHeight:) -> some View              // all CGFloat?
```
Doc page omits `overlayArrangementZIndex` (used in talk 111463 at 14:07 as `@Environment(\.overlayArrangementZIndex) var zIndex: Int`) and `splitArrangementAxis`/`overlayArrangementZIndex` seen in community sample code. **Verify in SDK.**

## ReservedRegion
https://developer.apple.com/documentation/swiftui/reservedregion
```swift
struct ReservedRegion: Identifiable, Hashable, Equatable, Sendable, CustomStringConvertible, ...
  var id: ReservedRegion.ID
  var kind: ReservedRegion.Kind          // .occlusion | .division (static vars on a struct)
  var frame: CGRect                      // view coordinates, points, origin top-leading; ALREADY includes margins
  var margins: EdgeInsets                // extra clearance for interactive content
  var isActive: Bool
struct ReservedRegion.QueryOptions { static var includeInactive }
extension GeometryProxy {
  func reservedRegions(kind: ReservedRegion.Kind,
                       options: ReservedRegion.QueryOptions,          // (default unknown; examples omit it → has a default)
                       layoutDirectionBehavior: LayoutDirectionBehavior) -> [ReservedRegion]  // (default unknown)
}
```
Facts stated on the page:
- Only regions overlapping the view (incl. partial) are returned; can be empty.
- Active only by default; `.includeInactive` adds inactive.
- Fully open Duo: division is inactive → no division regions without the option. Inactive regions still carry frames: use them to reserve space so layout doesn't jump on activation.
- Frames may have negative coordinates or extend past the view.
- RTL: frames mirrored by default; `layoutDirectionBehavior: .fixed` for unmirrored.
- Custom `Layout`: `bounds` in `placeSubviews` may not start at (0,0); compute from (0,0), add `bounds.origin` at placement.
- Most apps don't need to query; split views, tab bars, alerts, context menus, sheets adjust automatically. Scroll containers don't split content at a division by default. Prefer `ArrangementView` for two related views around a fold.
- Activation: fold active when partially open **or closed** (page wording); outer camera always active; inner camera active while in use.

## DeviceHinge / onHingeChange
https://developer.apple.com/documentation/swiftui/devicehinge
```swift
struct DeviceHinge: Equatable, Hashable, Sendable
  var angle: Angle
  var status: DeviceHinge.Status        // cases NOT listed on the page; talks: closed / partiallyOpen / fullyOpen
struct DeviceHingeContext { var hinge: DeviceHinge? /* other members not shown */ }
extension View {
  func onHingeChange(isEnabled: Bool, _ action: (DeviceHingeContext, DeviceHingeContext) -> Void) -> some View  // isEnabled default unknown; example omits it
}
```
Introduced 27.1. **iOS and iPadOS flagged beta in doc metadata on 2026-10-24.**
Status is derived by the system from angle **and device orientation**.

## Other symbols named by Apple for Duo (not yet pulled)
`toolbarVerticalBehavior(_:)`, `ToolbarVerticalBehavior.disabled`, `toolbarVerticalEdge` (EnvironmentValues), `toolbarVerticalCompressionBehavior(_:)`, `ToolbarVerticalCompressionBehavior.prefersToolbarItems`, `ToolbarItemVisibilityPriority`, `ToolbarOverflowMenu`, `ToolbarContent.axisBehavior(_:)` (`.horizontalOnly`, `.verticalPreferred`), `ToolbarItemPlacement.topBarPinnedTrailing`, `presentationPlacement(_:)`, `backgroundExtensionEffect()`, `ConcentricRectangle`, `defaultTabBarPlacement(.sidebar)`, `sceneAccessory`, `CameraCaptureAccessory`, `onAvailabilityChange`.
