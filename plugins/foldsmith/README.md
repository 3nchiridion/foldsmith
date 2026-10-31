# Foldsmith plugin

Foldsmith adapts an existing iOS app to iPhone Duo, Apple's foldable, hands-free on your Mac. It finds the app's
screens, captures each one in all seven poses on the simulator, applies a measured layout pattern where a screen needs
one, and checks every pose again with before and after shots. It commits each change on a `duo-migration` branch in
your app's repository and never pushes; a pane beside the chat shows the run as it goes.

## Requirements
Foldsmith runs in Claude Code (the terminal, an IDE extension or the desktop app's Code tab) on a Mac, since it builds
your app and drives the simulator:
- Xcode 27.1 with the iOS 27.1 simulator runtime;
- an iPhone Duo simulator whose name contains "Duo" (the tools find it by its name). Foldsmith never creates one; if
  `xcrun simctl list devices` shows none, make one:
  ```
  xcrun simctl create "iPhone Duo" com.apple.CoreSimulator.SimDeviceType.iPhone-Duo com.apple.CoreSimulator.SimRuntime.iOS-27-1
  ```
- xcodegen (`brew install xcodegen`);
- Claude Code 2.1.308 or later (`claude update`; 2.1.236 and older reject the plugin's hooks);
- your app's source (SwiftUI or UIKit) in a git repository, building for the simulator with Xcode 27.1, with your own
  work committed before you start.

An app without the scene lifecycle cannot launch on the iOS 27.1 SDK: Foldsmith adopts it with Apple's
`app-resizability` skill when that is installed, and otherwise stops and says so. A screen no taps reach (a members-only
one, say) is left for you, with the reason; one that only needs some content gets it, added through the app.

## What one install brings
- **The `foldsmith-duo` skill**: finds the app's screens, captures each one in all seven Duo poses, classifies it
  against Foldsmith's decision table, applies that pattern's reference implementation, and checks every pose with
  before/after screenshots and the detectors. Hands-free it makes local fixes only: each runs only where the phone
  has a fold, adds no container to the app and changes no navigation. A structural fix (a container where the app has
  none, rerouted navigation, a change on every device) it proposes in `.duo/PLAN.md`, with the navigation routes it
  would touch, and makes only when you pass `--structural`. It never stops to ask; what it cannot do goes to its
  "left" list with the reason, and what a review or a look finds that no detector shows it records as an issue: an
  open regression keeps its screen from done. It commits one screen at a time on a `duo-migration` branch and never
  pushes.
- **`/foldsmith-start`**: the one command to run in your app's folder. Run it again in a later session and it resumes from
  where the last one stopped; `/foldsmith-start --structural` also makes the structural changes it proposed.
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
    enlarged, for a migration of up to 40 screens (above that it says the live view is off); Pause / Resume;
  - the activity, newest first: five lines, then fifty more at a time, then a page at a time.

  From 150 columns wide (not on the phone) the matrix sits beside the stage, and the shots keep the size a narrower
  pane gives them: a landscape pair spans the pane below the figures, the picked cell and the matrix; a portrait pair
  stays in the stage's column, the matrix and the notes beside it. No text is cut short: long lines wrap, and what
  does not fit the pane's text budget waits behind a button (what is left and what is done a page at a time). In a
  terminal the figures are one line, the matrix is text, pictures draw where the terminal shows images (kitty and
  Ghostty; elsewhere the shot's description), Enlarge before, Enlarge after and Compare full size sit in one row, and
  the enlarged view is the capture itself as a terminal image.

Commands: `/foldsmith-start [app folder] [--structural]` runs or resumes the migration (with `--structural`, the
structural changes too); `/foldsmith` opens the pane; `/foldsmith watch <folder>` follows an app in another folder
(remembered per folder; `/foldsmith watch` alone goes back to the newest); `/foldsmith demo` shows sample data;
`/foldsmith off` returns to the progress file.

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
`/foldsmith demo` shows the pane with sample data. In your app's folder, `/foldsmith-start` starts the migration; in a
later session, running it again resumes from where it stopped. A run takes hours, since every screen is captured in
every pose before and after its change: IceCubesApp's five screens took about two. Results depend on the app.
IceCubesApp's five public screens and NetNewsWire's five ended with no finding in any pose: 8 and 19 cells fixed and
verified, the rest fine as they were (NetNewsWire's feeds screen after a follow-up on a design call made by Foldsmith's
owner; a detector added after that run finds its Reader View button beside the vertical bar in 8 cells, not fixed; the
rest of IceCubesApp was not run). Wikipedia's run finished 2 of its 11 screens and did not pass review: its last check
found 2 medium and 6 low regressions and 2 incomplete fixes, none fixed. When a run ends, read `.duo/REPORT.md` and
review the commits on `duo-migration` before you merge them; Foldsmith never merges.

## What it runs, reads and sends
Everything runs on your Mac, as you. The pane's and the skill's own code send nothing anywhere. What reaches the network
is the one fetch of `duo.py` below, the app's own build and use, and your Claude conversation.

**The pane** (`hooks/register.tsx`, a Claude Code mod) has three hooks:
- `session.start` registers the `/foldsmith` command, reads your home folder (`/usr/bin/printenv HOME`), makes its
  scratch folder (`mkdir -p ~/Library/Caches/foldsmith`), starts three timers that run for the whole session, and looks
  for progress files: every 1.5 seconds it checks the followed app's `.duo/migration.json` and reads it when it has
  changed (and, while a shot is enlarged on the desktop or in VS Code, whether its strips are cut), every minute it
  looks for progress files again, and every 4 seconds, only while the pane is drawn on screen, not paused and no shot
  is enlarged, for a migration of up to 40 screens, it takes a frame of the simulator;
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
  is only the one in `~/Library/Caches/duo-driver` or `~/.claude/skills/iphone-duo-simulator`, never a path named by a
  progress file or found in the project; without one, `xcrun simctl io <ID> screenshot ~/Library/Caches/foldsmith/live.png`;
- `sips`, to make a shot a JPEG small enough to draw in `~/Library/Caches/foldsmith` and read its size, and, when you
  enlarge a shot on the desktop or in VS Code, to make a larger copy of it and of the other shot of that cell there
  and cut each into strips (padding it with `-p`, cropping each strip with `-c`), each drawn as its own picture; a
  cut that fails is not run again until the shot changes;
- `open`, only when you press a button: Open report opens `.duo/REPORT.md` in your text editor and Show captures shows
  the `.duo/captures` folder in Finder, each only when it is a real file or folder in the app's folder and not a link;
  Open in Preview, in the enlarged view on the desktop and in VS Code, opens that shot in Preview
  (`/System/Applications/Preview.app`, PNG and JPEG files only).

It reads the `.duo/migration.json` of each app folder it finds or remembers, and the before and after shots those files
name, only inside that app's folder (a `.duo` folder or progress file that is a link, or a shot path that leads out by
`..` or through a link, is ignored), checks that
`.duo/REPORT.md` exists before offering Open report, and reads its own pictures in `~/Library/Caches/foldsmith`, which
it draws inside the pane as embedded images. It writes only those pictures (the enlarged copies and their strips among
them), and in Claude Code's plugin storage the paths of up to eight app folders where it found a progress file and, for
each session folder, the app you chose to follow (with `/foldsmith watch`, the App picker or a Migrations found button). It changes nothing in your app and makes
no network request: the `http://www.w3.org/2000/svg` in its code is the name of the SVG format, not an address. Its
Start migration, Resume migration and Restart if stopped buttons put `/foldsmith-start` in the prompt for you to send;
they do not send it. When you follow the session from the Claude mobile app, the pane's drawings, simulator frames and
shots included, reach that device through Claude Code, as the rest of the session does.

**The skill** (`skills/foldsmith-duo/`), when you ask it to adapt an app:
- builds the app with `xcodebuild`, which downloads the app's Swift packages if they are not already on the Mac, and
  its tap runner (`tools/tap/`, generated with `xcodegen`) with `xcodebuild build-for-testing` /
  `test-without-building`, into `~/Library/Caches/duo-tap`;
- drives the iPhone Duo simulator you already have with `xcrun simctl` (`list`, `install`, `launch`, `terminate`,
  `openurl`, and `uninstall` and `privacy reset` of that app only) and with the community driver `duo.py` (`launch`,
  `fold`, `orient`, `shot`). `duo.py` boots the Duo simulator if it is shut down, builds a small helper with `xcrun
  clang` and signs it ad hoc with `codesign` (kept, with each simulator's pose, in `~/.cache/duo-kit`), runs it inside
  the simulator with `xcrun simctl spawn`, and asks `xcrun devicectl` which display is on. The skill never creates,
  clones or erases a simulator; to recover one that crash-loops it may shut it down and boot it again;
- uses the app on the simulator through the tap runner: it taps, types, answers system alerts (permission prompts too)
  and adds content through the app when a screen needs some. With `APP_PATH` set it reinstalls the app before each
  screen, which clears the app's data on the simulator. The app makes whatever network requests it normally makes;
- fetches `duo.py` from [WhitenWhiten/iphone-duo-simulator-skill](https://github.com/WhitenWhiten/iphone-duo-simulator-skill)
  at one fixed commit (`60cdda2f487434c9c3cd4dad9431e12a48ec1d04`) into `~/Library/Caches/duo-driver`, only when that
  commit is not already there, from that public repository. A `duo.py` you already have is used instead;
- runs the detectors with `swift run duo-detect` from `tools/detect/` (no package dependencies), building into
  `~/Library/Caches/duo-detect`; the static scans with `rg` (ripgrep), which also lists the app's navigation routes
  for a plan (`tools/routes.sh`); and its own scripts with `bash` and `python3`
  (standard library only), which also use `perl` (for time limits), `sips` and `shasum`. The flow file it writes for
  each app (`.duo/flows/<app>.flow`) is run by `bash`: in a repository someone else wrote, read it before you resume a
  migration there, as you would a build script;
- reads the app's code, every shot and the app's crash reports (`~/Library/Logs/DiagnosticReports`) into your Claude
  conversation, may start a fresh subagent to review a screen's diff and shots, and adopts the scene lifecycle with
  Apple's `app-resizability` skill when that is installed;
- changes your app's code and commits each change on a `duo-migration` branch; it never pushes, opens no pull request
  and merges nothing. It writes `.duo/` in your app's folder (the progress file, flows, reports, the plan of proposed
  structural changes and captures) and adds the captures and its lock file to the repository's `.git/info/exclude`.
  Each capture also leaves its `xcodebuild` test logs and results and its accessibility dumps in a `duo-tap.*` folder
  in your temporary folder.

## Development
Report a problem as an issue in the repository, with the app, the pose and what the pane or `.duo/REPORT.md` showed
(for a private app, describe it rather than attaching its files).

The pane's hooks have tests in `hooks/register.test.tsx`; run them with `claude plugin test plugins/foldsmith`
(Claude Code 2.1.308 or later) and check the manifest with `claude plugin validate plugins/foldsmith`. `skills/foldsmith-duo/` here is a copy of the repository's `skills/foldsmith-duo/`, made by
`python3 scripts/sync-skill-references.py` from the repository root. Edit `SKILL.md` and `references/apple.md`,
`simulator.md` and `detectors-static.md` in that folder, and everything else at its source (`patterns/`, `Sources/`,
`scripts/`, `Tap/`), then rerun the script.

## License
MIT (`LICENSE`). iPhone and iPhone Duo are trademarks of Apple Inc. Foldsmith is independent and is not affiliated
with, sponsored by, or endorsed by Apple Inc.

