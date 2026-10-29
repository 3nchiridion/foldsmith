# DuoProbe

Logs, per geometry change, everything layout-relevant the system reports: window size, safe-area insets,
size classes, `toolbarVerticalEdge`, every division and occlusion region (including inactive) with frame,
margins and active state, hinge angle and status, scene and screen bounds. One JSON line per sample,
with `seq`, `t` and `sinceLastChange` so first-frame vs settled behaviour is measurable.

Compiled and run on the iOS 27.1 iPhone Duo simulator on 2026-10-25, in all seven drivable poses
(`raw/METRICS-NOTES.md`). What the SDK says about the API questions it was written around is in `raw/sdk/DIFF.md`.

## Build
```sh
brew install xcodegen            # once
cd Probe && xcodegen generate
xcodebuild -project DuoProbe.xcodeproj -scheme DuoProbe \
  -destination "platform=iOS Simulator,id=$DUO_UDID" -derivedDataPath build build
xcrun simctl install "$DUO_UDID" build/Build/Products/Debug-iphonesimulator/DuoProbe.app
```
Then `DUO_UDID=… DUO_PY=… ../scripts/run-probe.sh`.

## Output
`raw/metrics.jsonl` (schema in `Metrics.swift`, `schema: 2`), `raw/apple-apps/_probe/<pose>-inner.png` or
`<pose>-cover.png` (the display that was drawing) with the overlay:
blue = safe-area frame, red = active division, orange = inactive division, purple = occlusion.
