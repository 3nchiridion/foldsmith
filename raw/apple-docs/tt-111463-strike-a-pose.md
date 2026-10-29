# Tech Talk 111463 — Strike a pose with adaptive layouts on iPhone Duo

Presenters: Maria (Human Interface Designer), Harry (UI Frameworks).
Page: https://developer.apple.com/videos/play/tech-talks/111463/
HD: https://devstreaming-cdn.apple.com/videos/tech-talks/111463/1/dcd8d7bb-94d3-4f48-bd2b-e3a6e10fec1e/downloads/tech-talks-111463_hd.mp4?dl=1

## Chapters
0:00 Introduction · 0:27 Reserved regions · 1:29 Designing around the hinge · 2:26 Displacement patterns · 4:00 Choose where content moves · 5:12 Adapt content to its new region · 6:39 Query reserved regions · 7:50 Division and occlusion · 8:39 System containers that adapt · 9:20 Introducing arrangements · 11:17 Build with ArrangementView · 12:00 Configure split · 13:21 Overlay · 14:39 Choose between arrangements · 16:09 When not to use an arrangement · 16:34 Next steps

## Guidance (close paraphrase)
- Each display has its own size class. Hinge and the two cameras reserve space; treat them like any other region a layout adapts to (cf. iPadOS window controls). Outer camera always present; system bars lay out vertically within the new safe area. Inner display adapts for the fold or the FaceTime camera when active.
- Book pose: display curves through the center; content spanning the fold reads badly (photo across a book spine).
- **Displacement** = reframing existing elements into the space actually available so content stays visible, reachable, unobstructed. Scope: one button → a container → a layout section. Move elements independently when they adapt alone, together when they are a unit. Don't move so far that visual relationships weaken. **Continuously scrolling content (articles, feeds, documents, lists) must not displace** — moving it breaks scroll continuity.
- Destination follows purpose and pose:
  - Book (partially folded, held): alerts move to the trailing side, closer to where they'd appear when closed.
  - Propped on a table (laptop/tabletop): top region for content viewed at a distance (alerts); bottom region for interactive controls (media controls) because it is a stable touch surface.
  - Several suitable regions: contextual placement wins (search sits over the keyboard when focused; as the device folds its width/position adapt to stay over the content it searches).
- Adaptations beyond position/size are allowed. System repositions action sheets, alerts, menus, popovers around reserved regions. Reminders split view keeps both columns visible in an even 50/50 split. Fitness grid keeps outer margins and increases spacing around the hinge so each container stays within its region.
- Division vs occlusion: division splits an area (the fold; active only when folded; **width zero when flat**; inactive regions still useful, e.g. even column count). Occlusion covers an area (FaceTime camera; active only while camera is active). Default query returns active only; `.includeInactive` returns both.
- System containers adapt automatically: navigation (`NavigationStack`, `NavigationSplitView`, `TabView`) and content (`List`, `ScrollView`).
- Arrangement = layout container between navigation and content containers; maps inputs (horizontal/vertical size class, aspect ratio, active division regions) → outputs (show a view? its frame). Example: Podcasts Now Playing + transcript.
- Split default: horizontal when wider than tall, vertical when taller; `axes` restricts; if it can't split on its primary axis it shows only one view.
- Overlay: stacked by default; side by side when folded; `overlayArrangementZIndex` lets a view switch collapsed/expanded. UIKit: `state(for:).zIndex`.
- Choosing: existing HStack/VStack → split; ZStack → overlay. No precedent: overlay for a clear foreground/background relationship where partially obscured scrollable content is acceptable (Accessibility Reader); split for main/detail where neither should be obscured (Podcasts transcript).
- Don't put navigation containers inside an ArrangementView; don't put an ArrangementView inside `List`/`ScrollView`.
- Next steps: audit centered layouts; consider two-column or displacement; adopt Reserved Regions for the highest-priority manually laid-out controls.

## Symbols
SwiftUI: `GeometryReader`, `GeometryProxy.reservedRegions(kind:options:)`, `onGeometryChange`, `.division`, `.occlusion`, `.includeInactive`, `frame`, `ArrangementView`, `arrangementViewStyle`, `.split`, `.overlay`, `.split.axes(.horizontal)`, `overlayArrangementZIndex`.
UIKit: `UIView.reservedRegions(kind:)`, `UIArrangementViewController`, `setViewController(_:for:)`, `.primary`, `.secondary`, `updateArrangement(.split.axes(.horizontal))`, `UISplitArrangement`, `state(for:)`, `zIndex`.

## Code as published (timestamps)
```swift
// 6:46
GeometryReader { proxy in
  let regions = proxy.reservedRegions(kind: .division)
}
// 7:03 UIKit
let regions = view.reservedRegions(kind: .division)
let frames = regions.map(\.frame)
// 7:22
let regions = proxy.reservedRegions(kind: .division, options: .includeInactive)
// 8:07
let regions = proxy.reservedRegions(kind: .occlusion)
// 11:23
NavigationStack {
  ArrangementView { PlayerView() } secondary: { UpNextView() }
}
// 11:26 UIKit
let arrangementVC = UIArrangementViewController()
let navController = UINavigationController(rootViewController: arrangementVC)
arrangementVC.setViewController(PlayerViewController(), for: .primary)
arrangementVC.setViewController(UpNextViewController(), for: .secondary)
// 12:00 / 12:41
.arrangementViewStyle(.split)
.arrangementViewStyle(.split.axes(.horizontal))
// 13:07 UIKit
arrangementVC.updateArrangement(.split.axes(.horizontal))
// 13:26
ArrangementView { UpNextView() } secondary: { PlayerView() }
  .arrangementViewStyle(.overlay)
// 14:07
enum UpNextMinimization { case collapsed, expanded }
struct UpNextView: View {
  @Environment(\.overlayArrangementZIndex) private var zIndex: Int
  var body: some View { UpNextList(minimization: minimization) }
  var minimization: UpNextMinimization { zIndex > 0 ? .collapsed : .expanded }
}
// 14:21 UIKit
let primaryState = arrangementVC.state(for: .primary)
myModel.minimization = (primaryState?.zIndex ?? 0) > 0 ? .collapsed : .expanded
```
