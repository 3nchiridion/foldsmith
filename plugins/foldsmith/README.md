# Foldsmith plugin

Foldsmith adapts an existing iOS app to iPhone Duo, Apple's foldable, hands-free on your Mac. It finds the app's
screens, captures each one in all seven poses on the simulator, applies a measured layout pattern where a screen needs
one, and checks every pose again with before and after shots. It commits each change on a `duo-migration` branch in
your app's repository, app code only (its working folder `.duo/` is never committed), and never pushes; a pane beside
the chat shows the run as it goes. It can also audit an app without changing it, review a migration independently in
a new session, and export the App Store's iPhone Duo screenshots from its captures.

## Requirements
Foldsmith runs in Claude Code (the terminal, an IDE extension or the desktop app's Code tab) on a Mac, since it builds
your app and drives the simulator:
- Xcode 27.1 with the iOS 27.1 simulator runtime;
- an iPhone Duo simulator whose name contains "Duo" (the driver drives only those). Foldsmith never creates one; if
  `xcrun simctl list devices` shows none, make one:
  ```
  xcrun simctl create "iPhone Duo" com.apple.CoreSimulator.SimDeviceType.iPhone-Duo com.apple.CoreSimulator.SimRuntime.iOS-27-1
  ```
- python3 3.9 or later, and `rg` (ripgrep; in Claude Code its own stands in);
- 5 GB free on the home volume, 10 to be safe;
- Claude Code 2.1.308 or later (`claude update`; 2.1.236 and older reject the plugin's hooks);
- your app's source (SwiftUI or UIKit) in a git repository, building for the simulator with Xcode 27.1, with nothing
  uncommitted outside `.duo/` before you start, since the run commits on a branch. `.duo/` is kept out of git
  (`.git/info/exclude`); `git clean -fdx` deletes it, the progress file with it.

Nothing else is installed or downloaded: no xcodegen (the tap runner's Xcode project is committed and `xcodebuild`
builds it), the simulator driver ships with the skill, and the App Store export uses macOS's built-in `sips`. Both
commands begin with the skill's preflight, which checks all of this read-only and prints the exact command for each
fix; the fixes are yours to run, and while anything is missing the run stops with that list.

An app without the scene lifecycle cannot launch on the iOS 27.1 SDK: Foldsmith adopts it with Apple's
`app-resizability` skill when that is installed, and otherwise stops and says so. A screen no taps reach is left for
you, with the reason; one that only needs some content gets it, added through the app. Foldsmith never logs in to your
app and never types into a login form: for a screen that needs your own login it first tries the app's own UI-test
launch arguments and demo modes, and otherwise leaves it for you, until you have logged in on the Duo simulator
yourself and run `/foldsmith-start` again. That run checks those screens again and carries on hands-free, without
reinstalling the app. Their shots hold your own content and stay in `.duo/captures/`, out of git.

## What one install brings
- **The `foldsmith-duo` skill**: finds the app's screens, captures each one in all seven Duo poses, classifies it
  against Foldsmith's decision table, applies that pattern's reference implementation, and checks every pose with
  before/after screenshots and the detectors. Hands-free it makes local fixes only: each runs only where the phone has
  a fold, adds no container to the app and changes no navigation. A structural fix (a container where the app has
  none, rerouted navigation, a change on every device) it proposes in `.duo/PLAN.md`, with the navigation routes it
  would touch, and makes only when you pass `--structural`. It never stops to ask; what it cannot do goes to its
  "left" list with the reason, and what a review or a look finds that no detector shows it records as an issue: an
  open regression keeps its screen from done, and so do a control gone with no record of where it went, a `verified`
  cell that keeps its old finding, a cited commit not on the branch and an after shot from older code; the run does
  not finish without an independent review on record (or a record of why none could be started). It reads the
  project's contribution rules first and commits in the project's style, one screen at a time, on its own
  `duo-migration` branch (`git switch -c duo-migration --no-track`), app code only, so the branch can become a pull
  request; it never pushes and opens none. It checks that the branch still builds with the Xcode the project's CI uses
  (`tools/sdkguard.py`: every iOS 27 API and Foldsmith reference type inside `#if compiler(>=6.4)`). It also audits an
  app without changing it, and exports the App Store's iPhone Duo screenshots from the captures: per screen, one shot
  for each size App Store Connect lists for iPhone Duo (the outer display 1398 × 2034 and 2034 × 1398, the inner
  display 2007 × 2853 and 2853 × 2007), only from cells verified or fine as they were, with a clean detector table and
  no open issue in that pose, flattened to JPEG with no alpha channel and never resized.
- **`/foldsmith-audit`**: what your app needs on the Duo, changing nothing. It runs the preflight, captures every screen
  in every pose, runs the detectors, looks at every shot and classifies each screen, then writes `.duo/audit.md` (the
  classes per screen and pose, the classification and why) and `.duo/PLAN.md` (per screen, the pattern and the fix,
  local or structural), and exports the App Store set from the cells already fine. No code change, no branch, no
  commit; the progress file ends at phase `classify`, so the pane shows it and `/foldsmith-start` takes it up later.
  A clean detector table is not a pass.
- **`/foldsmith-start`**: the migration, in your app's folder. It runs the preflight first, and resumes from an audit's
  progress file or from where the last session stopped; after you have logged in on the simulator yourself, it checks
  the screens that needed your own login again. `/foldsmith-start --structural` also makes the structural changes it
  proposed.
- **`/foldsmith-review`**: an independent review of the migration, in a new session: the diff, the captures and the
  code against the skill's `references/review.md`, the run's own report read last. It records confirmed findings as
  issues and the review in the progress file, and appends `## Independent review (<date>)` to `.duo/REPORT.md`; it
  changes no code and commits nothing. With a regression recorded, `/foldsmith-start` resumes and fixes it.
- **The pane** beside the chat, following `.duo/migration.json` (the skill rewrites it after every step). It finds the
  newest progress file under the session's folder by itself, and in the desktop app or VS Code offers an App picker
  when there are several (elsewhere, `/foldsmith watch <folder>` switches):
  - the app, its folder and branch, where the run stands (the phase, or Finished and what is left for you), and
    Resume migration, Open report and Show captures (the last two not on the phone: they open on the Mac);
  - the figures: screens finished, poses good, defects by class (`T14 ×10 · T5 ×5`) with Inspect next, which goes to
    the next defect, and what is left for you; under them a bar of every cell by state, with its legend;
  - the picked cell, large: its state, pattern and defect classes (and any class waived, with the reason), every pose
    as a button (keys 1 to 8), the screen picker (‹ Screen and Screen ›, keys `k` and `j`, on the phone, past 64
    screens or with a name over 32 characters), Previous, Next and Next defect, before and after as large as the pane
    allows, side by side while both keep a useful size, with the fold drawn (a blue band while the phone is bent,
    dashed when it lies flat), and the skill's notes on that screen in full;
  - Enlarge above each shot, and Compare full size where both draw larger than on the dashboard (not on the phone,
    which offers Enlarge only where it draws the shot larger), draw the shot, or both, across the whole pane and never
    smaller than on the dashboard, sharp: fitted to the pane's height or filling its width (`f`, desktop and VS Code;
    the phone fills its width). The poses, Previous, Next and the screen buttons move through the cells without
    leaving it, Open in Preview (desktop and VS Code) opens the capture itself, and ‹ Dashboard (`z`) goes back;
  - the screen × pose matrix: a row per screen, its name a button that picks it (a name over 20 characters wraps
    beside a View button), each cell its state or defect classes;
  - what is left, each item in full with a button per screen it names, and what is done (behind Show done when the
    pane's text budget runs short), kept in the progress file, so they survive the session;
  - the simulator, live: the panel that is drawing, every 4 seconds while the pane is on screen and no shot is
    enlarged, for a migration of up to 40 screens (above that it says the live view is off), and never while a capture
    runs (it says it is waiting); Pause / Resume;
  - the activity, newest first: five lines, then fifty more at a time, then a page at a time.

  From 150 columns wide (not on the phone) the matrix sits beside the stage, and the shots keep the size a narrower
  pane gives them: a landscape pair spans the pane below the figures, the picked cell and the matrix; a portrait pair
  stays in the stage's column, the matrix and the notes beside it. No text is cut short: long lines wrap, and what
  does not fit the pane's text budget waits behind a button (what is left and what is done a page at a time). In a
  terminal the figures are one line, the matrix is text, pictures draw where the terminal shows images (kitty and
  Ghostty; elsewhere the shot's description), Enlarge before, Enlarge after and Compare full size sit in one row, and
  the enlarged view is the capture itself as a terminal image.

Commands: `/foldsmith-audit [app folder]` audits the app without changing it; `/foldsmith-start [app folder]
[--structural]` runs or resumes the migration (with `--structural`, the structural changes too); `/foldsmith-review
[app folder]` reviews a migration independently (in a new session), changing no code; `/foldsmith` opens the pane;
`/foldsmith watch <folder>` follows an app in another folder (remembered per folder; `/foldsmith watch` alone goes
back to the newest); `/foldsmith demo` shows sample data; `/foldsmith off` returns to the progress file.

## Install
From the Claude directory: add Foldsmith under Customize → Plugins → Discover on claude.ai, and it reaches Claude Code
when a session next starts; or, in Claude Code 2.1.287 or later, add it with `/plugin directory`. Either way, the pane
needs Claude Code 2.1.308 or later.

Or from this repository's marketplace, at the prompt of a Claude Code terminal session:

```
/plugin install foldsmith --marketplace 3nchiridion/foldsmith
```

Answer `y` to add the marketplace, then pick a scope. From a shell: `claude plugin install foldsmith --marketplace 3nchiridion/foldsmith`.
If `--marketplace` is not offered, Claude Code is older than 2.1.308: run `claude update` first. In the desktop app: click +
next to the prompt box, then Plugins, Add marketplace with `3nchiridion/foldsmith`, then Add plugin.

Install it one way, not both: Claude Code loads only one copy of a plugin, and it may not be the one you update.

## First run
`/foldsmith demo` shows the pane with sample data. In your app's folder, `/foldsmith-audit` shows what the app needs
without changing it (its capture alone takes about 27 s a screen and pose: NetNewsWire's 35 cells take about 16
minutes), and `/foldsmith-start` starts the migration; in a later session, running it again resumes from where it
stopped. A migration takes hours, since every screen is captured in every pose before and after its change:
IceCubesApp's five screens took about two. Results depend on the app.
IceCubesApp's five public screens and NetNewsWire's five ended with no detector finding in any pose (8 and 19 cells
fixed and verified, the rest fine as they were); an independent review afterwards confirmed 7 items in IceCubesApp,
none a regression (the rest of the app was not run), and 15 in NetNewsWire, 9 of them regressions, mostly from a
three-level change a hands-free run now proposes instead of making. Wikipedia's run finished 2 of its 11 screens and
did not pass review: its last check found 2 medium and 6 low regressions and 2 incomplete fixes. None is fixed. When a
run ends, read `.duo/REPORT.md` and review the commits on `duo-migration` before you merge them; Foldsmith never merges.
If the run could not start its own independent review (its report says so), run `/foldsmith-review` in a new session
first.

## What it runs, reads and sends
Everything runs on your Mac, as you. The pane's and the skill's own code send nothing anywhere, and the skill downloads
nothing: its simulator driver is bundled. What reaches the network is the app's own build and use, and your Claude
conversation.

**The pane** (`hooks/register.tsx`, a Claude Code mod) has three hooks:
- `session.start` registers the `/foldsmith` command, reads your home folder (`/usr/bin/printenv HOME`), makes its
  scratch folder (`mkdir -p ~/Library/Caches/foldsmith`), starts three timers that run for the whole session, and looks
  for progress files: every 1.5 seconds it checks the followed app's `.duo/migration.json` and reads it when it has
  changed (and, while a shot is enlarged on the desktop or in VS Code, whether its strips are cut), every minute it
  looks for progress files again, and every 4 seconds, only while the pane is drawn on screen, not paused and no shot
  is enlarged, for a migration of up to 40 screens, it takes a frame of the simulator. Before each frame it checks for
  `<followed folder>/.duo/.capture.lock`: while that is there as a real file (not a link), a capture is driving the
  simulator, and the live view runs nothing (no `simctl`, no `duo.py`) and shows "waiting while a capture runs". A
  capture removes its lock when it ends, however it is stopped (even `kill -9` of its top process); one that outlives
  every capture (a crash, a reboot) keeps the live view waiting until the next capture replaces it, or until you
  remove that file by hand once no capture runs;
- `command.run`, for `/foldsmith` only, opens the pane: `demo` shows sample data, `off` goes back to the progress file,
  `watch <folder>` follows that folder and remembers the choice, and with nothing after it, it looks for progress files;
- `ui.render` draws the pane.

The pane follows, and opens by itself for, only a progress file under the session's folder, or the app you picked for
that folder (until `/foldsmith watch` alone); app folders remembered from other sessions are offered in its list and
followed only when you pick one. A session started in your home folder, or a folder above it, searches nothing and
follows only an app you pick there. It runs these programs, each by its
full path in `/usr/bin` or `/bin`, with the paths and the simulator's ID filled in:
- `find <session folder> -maxdepth 5 … -path '*/.duo/migration.json' -print`, to find progress files (it skips
  `node_modules`, `.git`, build folders and captures, and never runs in your home folder or a folder above it);
- `git -C <app folder> branch --show-current`, each time the progress file changes, to show the branch;
- `xcrun simctl list devices booted -j`, to find the booted iPhone Duo simulator (the one the progress file names, if
  that one is booted); the live view passes `duo.py` only a simulator it has just found booted (`duo.py` boots one
  that shut down in between, and runs the programs listed under the skill below);
- for the live view, `python3 <duo.py> --udid <ID> shot --out ~/Library/Caches/foldsmith --name live`, where `duo.py`
  is only `~/Library/Caches/duo-driver/scripts/duo.py`, then `~/.claude/skills/iphone-duo-simulator/scripts/duo.py`,
  never a path named by a progress file or found in the project; without one, `xcrun simctl io <ID> screenshot
  ~/Library/Caches/foldsmith/live.png`. The skill no longer fills the first of these (its driver is bundled in its own
  folder), so on a fresh install the live frame comes from `simctl io screenshot`;
- `sips`, to make a shot a JPEG small enough to draw in `~/Library/Caches/foldsmith` and read its size, and, when you
  enlarge a shot on the desktop or in VS Code, to make a larger copy of it and of the other shot of that cell there
  and cut each into strips (padding it with `-p`, cropping each strip with `-c`), each drawn as its own picture; a
  cut that fails is not run again until the shot changes;
- `open`, only when you press a button: Open report opens `.duo/REPORT.md` in your text editor and Show captures shows
  the `.duo/captures` folder in Finder, each only when it is a real file or folder in the app's folder and not a link;
  Open in Preview, in the enlarged view on the desktop and in VS Code, opens that shot in Preview
  (`/System/Applications/Preview.app`, PNG and JPEG files only).

It reads the `.duo/migration.json` of each app folder it finds or remembers, checks whether its `.duo/.capture.lock`
exists, and reads the before and after shots those files name, only inside that app's folder (a `.duo` folder or
progress file that is a link, or a shot path that leads out by `..` or through a link, is ignored), checks that
`.duo/REPORT.md` exists before offering Open report, and reads its own pictures in `~/Library/Caches/foldsmith`, which
it draws inside the pane as embedded images. It writes only those pictures (the enlarged copies and their strips among
them), and in Claude Code's plugin storage the paths of up to eight app folders where it found a progress file and, for
each session folder, the app you chose to follow (with `/foldsmith watch`, the App picker or a Migrations found button). It changes nothing in your app and makes
no network request: the `http://www.w3.org/2000/svg` in its code is the name of the SVG format, not an address. Its
Start migration, Resume migration and Restart if stopped buttons put `/foldsmith-start` in the prompt for you to send;
they do not send it. When you follow the session from the Claude mobile app, the pane's drawings, simulator frames and
shots included, reach that device through Claude Code, as the rest of the session does.

**The skill** (`skills/foldsmith-duo/`), when you ask it to audit or adapt an app:
- first runs its preflight, `tools/preflight.sh <app folder>`, which only reads: `xcodebuild -version`, `xcode-select
  -p`, `xcrun simctl list -j`, the `Info.plist` of each `/Applications/Xcode*.app` (only when Xcode 27.1 is not the
  selected one), the versions of `python3`, `rg` and Claude Code (`$CLAUDE_CODE_EXECPATH --version`, else `claude
  --version`), `df -Pk ~`, `git rev-parse`, `git status`, `git branch` and `git check-ignore` in the app, the
  `simulator` of the app's `.duo/migration.json`, the app's earlier `.duo/env` (read as text, never run), and the tap
  runner's `.xctestrun` in `~/Library/Caches/duo-tap/build`, and runs the read-only `git ls-files`, `git for-each-ref`,
  `git show-ref` and `git rev-parse` (files already tracked under `.duo/`, a remote `duo-migration` branch, an upstream
  on a local one) and `tools/sdkguard.py --ci-only` (below). It installs, creates, renames and boots nothing, and writes
  only `<app>/.duo/env` (the simulator's ID and the paths of the driver and the tap runner) and one line in the
  repository's `.git/info/exclude`, `/.duo/*` (after the app folder's path, when the app is not at the repository's
  root), which keeps everything in `.duo/` out of git;
- checks the project's CI toolchain with `tools/sdkguard.py`, which reads the CI files (`.github/workflows/*.yml` and
  `*.yaml`, `.github/actions/**/action.yml`, the `.sh` scripts a workflow runs, `.xcode-version`,
  `.circleci/config.yml`, `bitrise.yml`, `.gitlab-ci.yml`, `.travis.yml`, `fastlane/Fastfile`, `Makefile`,
  `ci_scripts/`), each `/Applications/Xcode*.app`'s `Contents/version.plist` and the changed Swift files, and runs the
  read-only `git rev-parse`, `diff`, `ls-files`, `merge-base`, `symbolic-ref` and `for-each-ref`. It writes nothing and
  runs no build: the `xcodebuild` line it prints, for an installed Xcode that matches the CI's, the skill runs as it
  runs any build, into `~/Library/Caches/duo-build`;
- builds the app with `xcodebuild`, which downloads the app's Swift packages if they are not already on the Mac, and
  its tap runner (`tools/tap/DuoTap.xcodeproj`, committed, so no xcodegen) with `xcodebuild build-for-testing` /
  `test-without-building`, into `~/Library/Caches/duo-tap`;
- drives the iPhone Duo simulator you already have with `xcrun simctl` (`list`, `install`, `launch`, `terminate`,
  `openurl`, and `uninstall` and `privacy reset` of that app only) and with the driver `duo.py` (`launch`, `fold`,
  `orient`, `shot`). The skill never creates, clones or erases a simulator; to recover one that crash-loops it may
  shut it down and boot it again;
- bundles `duo.py` and the helper it compiles, `duo_fold.c`: MIT, from the community repository
  `WhitenWhiten/iphone-duo-simulator-skill` at commit 60cdda2, unchanged, in `skills/foldsmith-duo/tools/driver/` with
  its licence and a README naming the commit and the files' hashes. It downloads nothing; a `DUO_PY` you set is used
  instead. The driver runs `xcrun simctl list`, `boot` (and `bootstatus`) of a Duo simulator that is shut down,
  `spawn`, `io enumerate`, `io screenshot`, `io recordVideo`, `launch` and `terminate`, and `xcrun devicectl device
  info displays` to learn which display is on. It compiles `duo_fold.c` once with `xcrun -sdk iphonesimulator clang`,
  signs it ad hoc with `codesign -s -` and caches it, with each simulator's pose, in `~/.cache/duo-kit`. It never
  creates, clones, erases or shuts down a simulator, never runs `simctl io … screenConfig`, and makes no network
  request;
- runs one capture at a time: each holds `.duo/.capture.lock` (its pids, start time, flow hash and output folder) while
  it drives the simulator, and a second one refuses. A capture stops before the disk has under 3 GB free and names the
  largest `~/Library/Caches/duo-*` folders; it deletes nothing. Stopped (Ctrl-C, a time limit, or `kill -9` of its
  top process), it lets go of the app, stops its `xcodebuild`, removes its lock and says where it stopped, so the next
  capture can resume from there;
- uses the app on the simulator through the tap runner: it taps, types, answers system alerts (permission prompts too)
  and adds content through the app when a screen needs some. With `APP_PATH` set it reinstalls the app before each
  screen, which clears the app's data on the simulator. The app makes whatever network requests it normally makes;
- runs the detectors with `swift run duo-detect` from `tools/detect/` (no package dependencies), building into
  `~/Library/Caches/duo-detect`; the static scans with `rg` (ripgrep), which also lists the app's navigation routes
  for a plan (`tools/routes.sh`); and its own scripts with `bash` and `python3` (standard library only), which also
  use `perl` (for time limits), `sips`, `shasum`, `df` and `du`. The flow file it writes for each app
  (`.duo/flows/<app>.flow`) is run by `bash`: in a repository someone else wrote, read it before you resume a
  migration there, as you would a build script;
- keeps the progress file with `tools/progress.py`, which runs the read-only `git rev-parse`, `diff`, `ls-files`,
  `merge-base` and `log` in the app's repository (with `GIT_OPTIONAL_LOCKS=0`, so it never writes git's index), for
  the code identity each capture records, the commits the run cites and the shots taken from older code;
- reads the app's code, every shot and the app's crash reports (`~/Library/Logs/DiagnosticReports`) into your Claude
  conversation, starts a fresh subagent for the independent review (`references/review.md`) when the session can, and
  adopts the scene lifecycle with Apple's `app-resizability` skill when that is installed;
- exports the App Store set with `tools/appstore.py`, which reads `.duo/migration.json`, the capture's `detectors.md`
  and its PNGs (only paths inside the repository), runs `sips` locally, writes JPEGs and a README under
  `.duo/appstore/`, and adds `/.duo/appstore/` (after the app folder's path, when the app is not at the repository's
  root) to the repository's `.git/info/exclude`. It replaces only files it wrote, stopping at a README there that it
  did not write, and makes no network connection and uploads nothing;
- in an audit (`/foldsmith-audit`) writes only under `.duo/` (and the `.git/info/exclude` lines named here), and
  changes no source, branch or commit;
- in a migration changes your app's code and commits each change on a `duo-migration` branch, app code only; it never
  pushes, opens no pull request and merges nothing. It writes `.duo/` in your app's folder (the progress file, flows,
  reports, the plan of proposed structural changes, captures, `.duo/env` and the App Store set), none of it committed:
  the preflight's `/.duo/*` line in `.git/info/exclude` keeps it out of git;
- in a review (`/foldsmith-review`) writes only the progress file's issues and review, a section of `.duo/REPORT.md`
  and, where only a shot settles a claim, a probe capture into a scratch folder under `.duo/captures/`; it changes no
  code, branch or commit.
  Each capture also leaves its `xcodebuild` test logs and results and its accessibility dumps in a `duo-tap.*` folder
  in your temporary folder.

## Development
Report a problem as an issue in the repository, with the app, the pose and what the pane or `.duo/REPORT.md` showed
(for a private app, describe it rather than attaching its files).

The pane's hooks have tests in `hooks/register.test.tsx`; run them with `claude plugin test plugins/foldsmith`
(Claude Code 2.1.308 or later) and check the manifest with `claude plugin validate plugins/foldsmith`. `skills/foldsmith-duo/` here is a copy of the repository's `skills/foldsmith-duo/`, made by
`python3 scripts/sync-skill-references.py` from the repository root. Edit `SKILL.md` and `references/apple.md`,
`simulator.md` and `detectors-static.md` in that folder, and everything else at its source (`patterns/`, `Sources/`,
`scripts/`, `Tap/`, `third_party/duo-driver/`), then rerun the script.

## License
MIT (`LICENSE`). iPhone and iPhone Duo are trademarks of Apple Inc. Foldsmith is independent and is not affiliated
with, sponsored by, or endorsed by Apple Inc.

