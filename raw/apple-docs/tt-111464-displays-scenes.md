# Tech Talk 111464 — Leverage multiple displays and scenes on iPhone Duo

Presenters: Chris Donegan (UI Frameworks), Alex Muller (System Experience).
Page: https://developer.apple.com/videos/play/tech-talks/111464/
HD: https://devstreaming-cdn.apple.com/videos/tech-talks/111464/1/b6d9b8a0-71ba-4f7a-acfc-4fb339dae7ff/downloads/tech-talks-111464_hd.mp4?dl=1

## Chapters
0:00 Intro · 0:49 Respond to the hinge · 1:18 Pitch bend from hinge angle · 2:35 Hinge data vs layout APIs · 2:59 Split view multitasking · 3:38 Multiple scenes · 4:22 Scene accessories · 5:00 Camera capture accessory · 5:34 Teleprompter accessory · 6:44 Next steps

## Guidance (close paraphrase)
- `onHingeChange` (SwiftUI) / `UIHingeInteraction` (UIKit): discrete status (closed, partially open, fully open) + continuous angle. Closure gets previous and current context; `context.hinge == nil` means no hinge.
- **Hinge data is for interactions and effects; layout uses arrangement and region APIs.**
- All apps participate in Split View (two apps side by side). A second layout stacks video and apps. Handle both via size classes and scene geometry. iPad/iPhone-Mirroring-resizable apps are ready.
- Duo is the first iPhone with multiple instances of an app's UI. iPad multi-window support carries over. **New windows cannot be created on the outer display**; reserved for the inner display; availability is dynamic → handle errors; `UIWindowSceneActivationAction` hides itself when unavailable.
- Scene accessories: content on multiple displays at once; system controls availability dynamically; enabled by default; observe availability.
- `CameraCaptureAccessory`: extra UI on the outer display while main UI is on inner; available when full screen on inner with an active camera session; register on the same view as the camera UI. `sceneAccessory` modifier; `onAvailabilityChange` (e.g. device closes → unavailable).
- Not covered: scene lifecycle on fold/unfold, state preservation, continuity between displays.

## Symbols
SwiftUI: `onHingeChange`, `DeviceHinge`, `hinge.status`, `hinge.angle`, `.partiallyOpen`, `sceneAccessory`, `CameraCaptureAccessory(isEnabled:)`, `onAvailabilityChange`.
UIKit: `UIHingeInteraction`, `UIWindowSceneActivationAction`.

## Code as published
```swift
// 2:17
GuitarView(pitchBend: pitchBend)
  .onHingeChange { _, context in
    if let hinge = context.hinge, hinge.status == .partiallyOpen {
      pitchBend = calculatePitchBend(angle: hinge.angle)
    } else { pitchBend = 0 }
  }
// 6:25
CameraView(model: model)
  .sceneAccessory {
    CameraCaptureAccessory(isEnabled: $model.isEnabled) { TeleprompterView(model: model) }
      .onAvailabilityChange { newValue in model.isAvailable = newValue }
  }
  .toolbar { TeleprompterToggle(isEnabled: $model.isEnabled).disabled(!model.isAvailable) }
```

# Tech Talk 111465 — Build a great camera experience for iPhone Duo (chapter map only)
Page: https://developer.apple.com/videos/play/tech-talks/111465
Chapters seen: … 3:00 Understand AVCaptureDevicePosition · 4:06 Initialize a direction coordinator · 4:50 Use both displays at once · 5:38 Device descriptors · 6:17 Handle a direction change · 7:03 Polish camera preview · 8:03 Handle rotation · 8:47 Next steps.
Symbols: `AVCaptureDevicePosition`, `AVCaptureDeviceDirectionCoordinator(view:deviceTypes:)`, `.builtInOuterUltraWideCamera`.
Out of scope for the pattern catalog except "Use both displays at once" (4:50), which is the only Apple material on simultaneous inner+outer use besides the camera accessory above.
