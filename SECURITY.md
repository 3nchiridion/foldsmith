# Security

## Reporting a vulnerability
Use GitHub's private vulnerability reporting: the repository's **Security** tab → **Report a vulnerability**. Please do
not open a public issue for a security problem. There is no bug bounty.

## What the skill and the plugin run
Foldsmith drives Xcode and the iOS Simulator on your Mac. Everything below runs as you, on your machine. The pane's and
the skill's own code send nothing anywhere, and the skill fetches nothing at run time; the network is reached only by
the app's own build (Swift packages) and use on the simulator, and by your Claude conversation. When you follow a session from
the Claude mobile app, the pane's drawings, simulator frames and shots included, reach that device through Claude Code. The plugin's README, "What it
runs, reads and sends", gives every program and when it runs.

**The skill** (`skills/foldsmith-duo/`, the same in the plugin), when you ask it to audit or adapt an app:
- **Checks the Mac first** with `tools/preflight.sh`: read-only (`xcodebuild -version`, `xcrun simctl list`, `df`,
  `git status`, `ls-files`, `for-each-ref`, `show-ref` and `check-ignore` in the app, the tools' versions, the app's
  progress file and earlier `.duo/env`, read as text and never run, and `tools/sdkguard.py --ci-only`), it installs,
  creates, renames and boots nothing, and writes only `.duo/env` in the app and one line of the repository's
  `.git/info/exclude`, `/.duo/*`, which keeps the app's `.duo/` out of git. Each fix it prints is for you to run.
- **Checks the project's CI toolchain** with `tools/sdkguard.py`: it reads the repository's CI files, each
  `/Applications/Xcode*.app/Contents/version.plist` and the changed Swift files, runs only read-only git commands
  (`rev-parse`, `diff`, `ls-files`, `merge-base`, `symbolic-ref`, `for-each-ref`), and writes nothing.
- **Keeps its progress file** with `tools/progress.py`, which runs only read-only git commands in the app's repository
  (`rev-parse`, `diff`, `ls-files`, `merge-base`, `log`, with `GIT_OPTIONAL_LOCKS=0`) and sends nothing anywhere.
- **Builds** your app with `xcodebuild` against the iOS 27.1 SDK, and the tap runner (`tools/tap/DuoTap.xcodeproj`,
  committed, so no xcodegen) with `xcodebuild build-for-testing` / `test-without-building`.
- **Drives the iPhone Duo simulator** you already have, with `xcrun simctl` (`list`, `install`, `launch`, `terminate`,
  `openurl`, and, between screens of an app that remembers its onboarding, `uninstall` and `privacy reset` of that app
  only) and with the community driver `duo.py` (`launch`, `fold`, `orient`, `shot`), which boots the Duo simulator if
  it is shut down and builds and signs a small helper it runs inside the simulator (kept in `~/.cache/duo-kit`). It
  never creates, clones or erases a simulator; to recover one that crash-loops it may shut it down and boot it again.
- **Fetches nothing.** `duo.py` and its helper `duo_fold.c` ship with the skill in `tools/driver/`: MIT, copied
  unchanged from `WhitenWhiten/iphone-duo-simulator-skill` at commit `60cdda2f487434c9c3cd4dad9431e12a48ec1d04`
  (`third_party/duo-driver/` here, whose README gives the files' sha256 and what the driver runs; it makes no network
  request). CI's goldens job (G2) uses that copy too, so the driver is fetched nowhere.
- **Never logs in to your app and never types credentials.** A screen that needs your own login waits until you have
  signed in on the simulator yourself.
- **Runs one capture at a time** under a lock file (`.duo/.capture.lock`), stops before the disk has under 3 GB free,
  and deletes nothing to make room: it names the largest `~/Library/Caches/duo-*` folders for you to judge.
- **Runs the detectors** with `swift run duo-detect` from `tools/detect/` (no package dependencies), building into
  `~/Library/Caches/duo-detect`.
- **Exports App Store screenshots** with `tools/appstore.py`, which converts captures with `sips`, makes no network
  call and never uploads. Its only write outside its output folder (`.duo/appstore/`) is one line in the app
  repository's `.git/info/exclude`. It refuses an output folder that holds the app or its progress file, replaces only
  files it wrote there (a `README.md` it did not write stops it), and reads no shot path that leads outside the
  repository.
- **Changes your app's code** (a migration, never an audit or a review) and commits each change on a branch named
  `duo-migration` in your app's repository, app code only. It **never pushes**, opens no pull request, and merges
  nothing. It writes `.duo/` in your app's folder (progress file, flows, reports, captures, the App Store set,
  `.duo/env` and lock files), none of it committed: the preflight's line in `.git/info/exclude` keeps it out of git.
- Runs its own scripts with `bash` and `python3` (standard library only), and each app's flow file
  (`.duo/flows/<app>.flow`, which it writes) with `bash`: in a repository someone else wrote, read that file before you
  resume a migration there, as you would a build script.

**The plugin's pane** (Claude Code): it finds `.duo/migration.json` files under the session's folder (`find`, never in
your home folder or a folder above it) and follows by itself only those or the app you picked for that folder, shows the app's branch (`git branch --show-current`) and lists the booted simulator
(`xcrun simctl list`); every 4 seconds while it is drawn, and never while a capture holds `.duo/.capture.lock`, it
takes a frame of a booted Duo simulator into `~/Library/Caches/foldsmith` (`duo.py shot`, with only the `duo.py` in
`~/Library/Caches/duo-driver` or `~/.claude/skills`, never a path from a progress file or the project, nor the
skill's bundled copy; or `xcrun simctl io … screenshot`) and scales it with `sips`. It runs each program by its full path, reads progress files and shots only inside the app's folder (not through a
link out of it), and its buttons open the report as text, show the captures folder in Finder, or open a shot in Preview, never a
link. It writes nothing in your repository and makes
no network request.

Review the branch the skill leaves before merging it, as you would any contributor's: the skill is an agent editing
code, and the report says what it changed and what it left.
