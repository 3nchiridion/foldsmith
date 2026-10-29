# Apple primary sources — iPhone Duo

Collected 2026-10-24 from developer.apple.com (video pages and documentation JSON).
Transcripts are Apple's copyright and are **not** stored here. Each note holds: chapter map,
every API symbol named, code listings as published, and a close paraphrase of the guidance.
For verbatim text, each note links the HD video; the Mac phase can transcribe locally if needed.

| File | Source | ID |
|---|---|---|
| `tt-111466-design.md` | Design for iPhone Duo (Marcos, Vince — Apple Design) | tech-talks/111466 |
| `tt-111461-prepare.md` | Prepare your app for iPhone Duo (David Jackson — UI Frameworks) | tech-talks/111461 |
| `tt-111462-raise-the-bar.md` | Raise the bar with iPhone Duo (Anna — UI Frameworks; Maria — HI Design) | tech-talks/111462 |
| `tt-111463-strike-a-pose.md` | Strike a pose with adaptive layouts (Maria; Harry — UI Frameworks) | tech-talks/111463 |
| `tt-111464-displays-scenes.md` | Leverage multiple displays and scenes (Chris Donegan; Alex Muller) | tech-talks/111464 |
| (in `tt-111464-displays-scenes.md`) | Build a great camera experience for iPhone Duo | tech-talks/111465 (chapter map only) |
| `hig-designing-for-iphone-duo.md` | HIG article, published 2026-09-09 | /design/human-interface-guidelines/designing-for-iphone-duo |
| `techoverview-preparing.md` | Technology Overview: Preparing your app for iPhone Duo | /documentation/TechnologyOverviews/preparing-your-app-for-iphone-duo |
| `api-swiftui.md` | ArrangementView, ReservedRegion, DeviceHinge, onHingeChange | documentation/swiftui/* |
| `api-uikit.md` | UIArrangementViewController, UIView.ReservedRegion | documentation/uikit/* |

Also referenced by Apple, not yet pulled: Meet with Apple "iPhone Duo Group Lab" 285 and 286;
WWDC26 "Modernize your UIKit app" (278); WWDC25 "Make your UIKit app more flexible" (282);
TN3210 iPhone Mirroring; Xcode "Device Hub" doc; AVKit "Choosing a camera by the direction it faces";
AVFoundation "Registering a camera capture accessory on iPhone Duo".

## Fact that changes the competitive picture

Apple ships its own agent skill. The "app modernization skill" from WWDC26 is renamed
**App Resizability** in Xcode 27.1 and now covers SwiftUI and iPhone Duo (111461, 9:12).
API-level migration is therefore first-party. Anything this project ships at the API layer
competes with Apple; the pattern catalog and the pose-matrix evidence do not.

## Where Apple is silent (gaps the measurement phase must fill)

- No numeric metrics anywhere: no point sizes for the fold, margins, bar width, pose window sizes.
- "Six device poses" appear only as an illustration's alt text; the poses are never named or defined.
- Nothing on scene lifecycle across fold/unfold, state preservation, or first-frame region population.
- Nothing on Split View minimum widths.
- `DeviceHinge.Status` cases are not listed in the docs page (talks say closed / partially open / fully open).
- `ArrangementView` docs omit `overlayArrangementZIndex` though the talk uses it; `UIArrangementViewController` docs omit `zIndex` though the talk reads `state(for:).zIndex`.
- iOS/iPadOS availability for `DeviceHinge` and `UIArrangementViewController` is still flagged **beta** in the doc metadata as of 2026-10-24, one day after 27.1 shipped.
