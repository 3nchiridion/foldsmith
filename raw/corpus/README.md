# Open-source iOS corpus — the test subjects

Eight apps spanning the archetypes the catalog has to serve. Pinned commits in `manifest.txt`;
`clone.sh` restores them (≈1.8 GB). Profiled 2026-10-24 by grep; build facts need the Mac phase.

| App | Archetype | Build | Min iOS | UI mix (files) | Duo risk signals (grep counts) |
|---|---|---|---|---|---|
| **NetNewsWire** | list-detail reader (3-column) | Xcode proj, SPM | 18.0 | 726 Swift, 10 ObjC; SwiftUI 43 / UIKit 38 | `UIScreen.main` 0 · orientation 0 · idiom 24 · SplitView ✓ (7) |
| **IceCubesApp** | feed / timeline (Mastodon) | Xcode proj, SPM | 18.5 | 431 Swift, SwiftUI 267 / UIKit 6 | `UIScreen.main` 7 · orientation 4 · idiom 13 · SplitView 0 |
| **wikipedia-ios** | reader / article (web content) | Xcode proj, SPM, Bundler | 17.6 (some 16.6) | 1487 Swift, 208 ObjC; SwiftUI 251 / UIKit 186 | `UIScreen.main` 35 · **UIRequiresFullScreen 4** · orientation 11 · idiom 52 · SplitView 0 |
| **Signal-iOS** | chat / messaging | Xcode ws, **CocoaPods** + SPM, Bundler | 15.0 | 2693 Swift; SwiftUI 51 / UIKit 350 | `UIScreen.main` 3 · orientation 56 · idiom 13 · **custom UITabBar 1** · SplitView 2 |
| **firefox-ios** | browser (toolbar-heavy) | **Package.swift** root + Bundler | 15.0 (some 14.0) | 3288 Swift; SwiftUI 173 / UIKit 408 | `UIScreen.main` 44 · **orientation 153 · idiom 188** |
| **home-assistant/iOS** | dashboard / controls | Xcode proj, SPM, Bundler | 16.4 / 17.0 | 2692 Swift; SwiftUI 872 / UIKit 57 | `UIScreen.main` 12 · orientation 5 · idiom 21 |
| **kickstarter/ios-oss** | media-heavy commerce | Xcode proj, SPM, Bundler | 18.0 | 2080 Swift; SwiftUI 118 / UIKit 294 | `UIScreen.main` 8 · idiom 65 · **custom UITabBar 1** |
| **danqing/2048** | game (SpriteKit) | Xcode proj | **8.0**, ObjC, last commit 2018 | 16 ObjC, 1 Swift | `UIScreen.main` 8. Likely a compatibility-mode specimen rather than a migration target; may need target bumps just to build |

Why these: every row is a different content relationship (hierarchical, peer feed, continuous reading, chat, browser chrome, control dashboard, media commerce, fixed-aspect game), so the decision table gets one example per input class. Firefox and Wikipedia carry the most legacy signals (orientation and idiom branching, `UIScreen.main`, `UIRequiresFullScreen`), which is where Apple says Duo breaks apps. Signal and Kickstarter each have a custom `UITabBar` subclass — the exact case Apple says will not go vertical.

Expectations to test, not assumptions: `UIRequiresFullScreen` apps still resize but may letterbox; custom tab bars stay horizontal; orientation branches misfire because the inner display ignores supported orientations; the two SPM-only, SwiftUI-heavy apps (IceCubes, Home Assistant) should be the fastest to migrate and the clearest before/after.

Signal's CocoaPods and the Fastlane/Bundler setups mean "build each unmodified against 27.1" will need `bundle exec pod install` and may need per-repo setup scripts (see each repo's README/BUILDING). Budget a half day for corpus builds alone.

A swap candidate if 2048 won't build: any maintained SpriteKit/SwiftUI game; none with recent commits turned up in a quick search.
