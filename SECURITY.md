# Security

## Reporting a vulnerability
Use GitHub's private vulnerability reporting: the repository's **Security** tab → **Report a vulnerability**. Please do
not open a public issue for a security problem. There is no bug bounty.

## What the skill and the plugin run
Foldsmith drives Xcode and the iOS Simulator on your Mac. Everything below runs as you, on your machine; nothing is
sent anywhere except the one fetch from GitHub noted.

**The skill** (`skills/foldsmith-duo/`, the same in the plugin), when you ask it to adapt an app:
- **Builds** your app with `xcodebuild` against the iOS 27.1 SDK, and the tap runner (`tools/tap/`, generated with
  `xcodegen`) with `xcodebuild build-for-testing` / `test-without-building`.
- **Drives the iPhone Duo simulator** you already have, with `xcrun simctl` (`list`, `install`, `launch`, `terminate`,
  `openurl`, and, between screens of an app that remembers its onboarding, `uninstall` and `privacy reset` of that app
  only) and with the community driver `duo.py` (`fold`, `orient`, `shot`). It never creates, clones, erases or shuts
  down a simulator.
- **Fetches `duo.py`** from [WhitenWhiten/iphone-duo-simulator-skill](https://github.com/WhitenWhiten/iphone-duo-simulator-skill)
  at one fixed commit (`60cdda2f487434c9c3cd4dad9431e12a48ec1d04`) into `~/Library/Caches/duo-driver`, only when it is
  missing. That is the only network access.
- **Runs the detectors** with `swift run duo-detect` from `tools/detect/` (no package dependencies), building into
  `~/Library/Caches/duo-detect`.
- **Changes your app's code** and commits each change on a branch named `duo-migration` in your app's repository. It
  **never pushes**, opens no pull request, and merges nothing. It writes `.duo/` in your app's folder (progress file,
  flows, reports; captures are kept out of git through `.git/info/exclude`).
- Runs its own scripts with `bash` and `python3` (standard library only).

**The plugin's pane** (Claude Code), while it is open: reads `.duo/migration.json` under the session's folder
(`find`), the app's branch (`git branch --show-current`), and lists the booted simulator (`xcrun simctl list`); every
4 seconds while the pane is on screen it takes a simulator screenshot (`duo.py shot`, or `xcrun simctl io … screenshot`)
into `/tmp/foldsmith` and scales it with `sips`. Its buttons open the report, a capture or the captures folder with
`open`. It writes nothing in your repository.

Review the branch the skill leaves before merging it, as you would any contributor's: the skill is an agent editing
code, and the report says what it changed and what it left.
