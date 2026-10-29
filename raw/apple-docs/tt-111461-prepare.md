# Tech Talk 111461 — Prepare your app for iPhone Duo

Presenter: David Jackson (UI Frameworks).
Page: https://developer.apple.com/videos/play/tech-talks/111461/
HD: https://devstreaming-cdn.apple.com/videos/tech-talks/111461/1/e852bda6-e8c0-400d-8c6d-a37cb19ae254/downloads/tech-talks-111461_hd.mp4?dl=1

## Chapters
0:00 Intro · 0:30 Build with the latest SDK · 1:17 Get started in Xcode · 1:33 Adopt flexible layouts · 2:46 Use size classes · 3:57 Avoid screen assumptions · 5:01 Adopt standard navigation · 6:06 Respect safe areas · 8:08 Use reserved regions · 9:12 Next steps

## Guidance (close paraphrase)
- Apps run on Duo without recompiling. iOS 27 SDK: app extends left of the status bar on the inner display. iOS 27.1 SDK: extends to the screen edge; standard navigation and toolbar buttons lay out vertically. Xcode 26 and earlier builds do not extend under status bar and camera.
- Xcode 27.1 Device Hub: buttons at the bottom of the simulator window open, close, rotate, fold.
- Design for a continuum of sizes; no idiom or screen-size assumptions. iOS 27 also lets apps be resized larger than ever via iPhone Mirroring on Mac.
- Size classes replace orientation. Outer display behaves like other iPhones; inner is regular in both dimensions; **the inner display does not honor supported interface orientations**.
- `UIScreen.main` is ambiguous on a two-display device and will be deprecated; use environment, trait collection or scene bounds. `traitCollection.displayScale` replaces `UIScreen.main.scale`.
- Concentricity: `ConcentricRectangle` (SwiftUI) / `UICornerConfiguration` (UIKit) to match screen corners.
- Split views and tab views adapt across poses; inner display may opt into a sidebar (`defaultTabBarPlacement(.sidebar)` / `tabBarController.sidebar.preferredPlacement = .sidebar`).
- Keep interactive content inside the safe area; let background art extend past. Safe areas and layout margins are often asymmetric: handle each side independently; test in Split View.
- iOS 27.1: `ReservedRegion` (SwiftUI) / `UIViewReservedRegion` (UIKit) for custom bars and edge-to-edge UI.
- Next steps: **the app modernization skill from "Modernize your UIKit app" is now called App Resizability in Xcode 27.1, supporting SwiftUI and iPhone Duo.** Download Xcode 27.1, simulate with Device Hub, follow adaptive layout practices, try the skill.

## Code as published
```swift
// 2:59
@Environment(\.horizontalSizeClass) private var horizontalSizeClass
@Environment(\.verticalSizeClass) private var verticalSizeClass
traitCollection.horizontalSizeClass; traitCollection.verticalSizeClass
// 4:16
let screen = window?.windowScene?.screen
// 4:30
ConcentricRectangle().fill(Color.green).padding(8.0).ignoresSafeArea()
// UIKit: UICornerConfiguration
// 5:44
TabView { … }.defaultTabBarPlacement(.sidebar)
tabBarController.sidebar.preferredPlacement = .sidebar
// 6:52 / 7:07
foreground.frame = view.bounds.inset(by: view.safeAreaInsets)
.ignoresSafeArea(); backgroundView.frame = view.bounds
// 7:30 — asymmetric insets
let width = view.bounds.width - view.safeAreaInsets.left * 2      // wrong
let width = view.bounds.inset(by: view.safeAreaInsets).width      // right
// 9:25
let screenScale = UIScreen.main.scale            // before
let screenScale = traitCollection.displayScale   // after
```

## Related
Meet with Apple 285/286 (Group Labs); tech-talks 111464, 111462, 111463; WWDC26 278 Modernize your UIKit app.
