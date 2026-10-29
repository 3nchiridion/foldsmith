# DuoTap

A UI-test bundle with no host app: it launches any installed app on the iPhone Duo simulator by bundle id, taps a
list of labels while the phone is shut, then holds the app in the foreground until the host releases it. While it
holds, the host can ask for the app's accessibility tree (`posed` → `snapshot.json`, `snapped`) or for a relaunch and
the same taps again (`again` → `tapped` or `failed`). `scripts/capture-corpus-flow.sh` drives it, one
`xcodebuild test-without-building` per screen, with duo.py doing the folds, the turns and the shots of every pose in
between; starting a test run is about 24 s of the old per-pose cost.

Why not Xcode's own device-interaction tools: they answer through Xcode's agent bridge, which on 27.1 asks the
user to approve the agent per Xcode launch and per connection, and each scripted command is a new connection.

## Build once
```sh
cd Tap && xcodegen generate
xcodebuild build-for-testing -project DuoTap.xcodeproj -scheme DuoTapUITests \
  -destination "platform=iOS Simulator,id=$DUO_UDID" -derivedDataPath build
ls build/Build/Products/*.xctestrun
```
Steps in `DUO_TAPS` are separated by `;`. A plain step taps by label or identifier (exact, else a case-insensitive
substring of a label). `type:<text>` types into the focused field, `springboard:<label>` taps a button of a system
alert if one is up (permission prompts, "Open in …?"), `try:<label>` taps only if the element is there,
`wait:<seconds>` pauses, `cell:<n>` taps the n-th hittable cell from the top (a feed's newest article).

`TEST_RUNNER_DUO_ARGS` (the flow script's `LAUNCH_ARGS`) passes launch arguments to the app, for an app's own UI-test
switches such as Firefox's `FIREFOX_SKIP_INTRO`.

## Run one flow by hand
```sh
mkdir -p /tmp/duo-flags && rm -f /tmp/duo-flags/*
TEST_RUNNER_DUO_BUNDLE=<bundle-id> TEST_RUNNER_DUO_TAPS='Connect to my Home Assistant;Enter address manually' \
TEST_RUNNER_DUO_FLAGS=/tmp/duo-flags \
xcodebuild test-without-building -xctestrun build/Build/Products/DuoTapUITests_*.xctestrun \
  -destination "platform=iOS Simulator,id=$DUO_UDID" &
# wait for /tmp/duo-flags/tapped, fold and shoot with duo.py; touch /tmp/duo-flags/again to relaunch and tap again;
# then: touch /tmp/duo-flags/release
```
