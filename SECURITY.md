# Security

## Reporting a vulnerability
Use GitHub's private vulnerability reporting: the repository's **Security** tab → **Report a vulnerability**. Please do
not open a public issue for a security problem. There is no bug bounty.

## What the skill and the plugin run
Foldsmith drives Xcode and the iOS Simulator on your Mac. Everything below runs as you, on your machine. The pane's and
the skill's own code send nothing anywhere; the network is reached only by the one fetch from GitHub noted, by the app's
own build (Swift packages) and use on the simulator, and by your Claude conversation. When you follow a session from
the Claude mobile app, the pane's drawings, simulator frames and shots included, reach that device through Claude Code. The plugin's README, "What it
runs, reads and sends", gives every program and when it runs.

**The skill** (`skills/foldsmith-duo/`, the same in the plugin), when you ask it to adapt an app:
- **Builds** your app with `xcodebuild` against the iOS 27.1 SDK, and the tap runner (`tools/tap/`, generated with
  `xcodegen`) with `xcodebuild build-for-testing` / `test-without-building`.
- **Drives the iPhone Duo simulator** you already have, with `xcrun simctl` (`list`, `install`, `launch`, `terminate`,
  `openurl`, and, between screens of an app that remembers its onboarding, `uninstall` and `privacy reset` of that app
  only) and with the community driver `duo.py` (`launch`, `fold`, `orient`, `shot`), which boots the Duo simulator if it
  is shut down and builds and signs a small helper it runs inside the simulator (kept in `~/.cache/duo-kit`). It never creates, clones or erases a
  simulator; to recover one that crash-loops it may shut it down and boot it again.
- **Fetches `duo.py`** from [WhitenWhiten/iphone-duo-simulator-skill](https://github.com/WhitenWhiten/iphone-duo-simulator-skill)
  at one fixed commit (`60cdda2f487434c9c3cd4dad9431e12a48ec1d04`) into `~/Library/Caches/duo-driver`, only when it is
  missing, from that public repository.
- **Runs the detectors** with `swift run duo-detect` from `tools/detect/` (no package dependencies), building into
  `~/Library/Caches/duo-detect`.
- **Changes your app's code** and commits each change on a branch named `duo-migration` in your app's repository. It
  **never pushes**, opens no pull request, and merges nothing. It writes `.duo/` in your app's folder (progress file,
  flows, reports; captures are kept out of git through `.git/info/exclude`).
- Runs its own scripts with `bash` and `python3` (standard library only), and each app's flow file
  (`.duo/flows/<app>.flow`, which it writes) with `bash`: in a repository someone else wrote, read that file before you
  resume a migration there, as you would a build script.

**The plugin's pane** (Claude Code): it finds `.duo/migration.json` files under the session's folder (`find`) and
follows by itself only those or the app you picked for that folder, shows the app's branch (`git branch --show-current`) and lists the booted simulator
(`xcrun simctl list`); every 4 seconds while it is drawn it takes a frame of a booted Duo simulator into
`~/Library/Caches/foldsmith` (`duo.py shot`, with only the `duo.py` in `~/Library/Caches/duo-driver` or
`~/.claude/skills`, never a path from a progress file or the project; or `xcrun simctl io … screenshot`) and scales it
with `sips`. It runs each program by its full path, reads shots only inside the app's folder (not through a link out of
it), and its buttons open the report as text, show the captures folder in Finder, or open a shot in Preview, never a
link. It writes nothing in your repository and makes
no network request.

Review the branch the skill leaves before merging it, as you would any contributor's: the skill is an agent editing
code, and the report says what it changed and what it left.
