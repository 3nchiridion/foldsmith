# Foldsmith plugin

Adapt a whole iOS app to iPhone Duo hands-free, and watch it happen. One install brings:

- **The `foldsmith-duo` skill** (`skills/`): finds the app's screens, captures each one in all seven Duo poses,
  classifies it against the decision table, applies the pattern's reference implementation, and proves every pose
  with before/after screenshots and the detectors. It never stops to ask; what it cannot do goes to its "left" list
  with the reason. It commits one screen at a time on a `duo-migration` branch and never pushes.
- **`/foldsmith-start`**: the one command to run in your app's folder. Run it again in a later session and it resumes from
  where the last one stopped.
- **The pane** beside the chat, following `.duo/migration.json` (the skill rewrites it after every step). It finds the
  newest progress file under the session's folder by itself, and offers an App picker when there are several:
  - the app, its folder and branch, and where the run stands (the phase, or Finished and what is left for you);
  - the simulator, live: the panel that is drawing, every 4 seconds while the pane is on screen; Pause / Resume;
  - the screen × pose matrix: hover a cell for its state and defect classes;
  - the picked cell: its state, classes and the skill's reason, and before and after with the fold drawn (a red band
    while the phone is bent, dashed when it lies flat); Previous, Next and Next defect step through the cells;
  - what is done and what is left, kept in the progress file, so it survives the session;
  - the activity, newest first;
  - Resume migration, Open report and Show captures.

Commands: `/foldsmith-start [app folder]` runs or resumes the migration; `/foldsmith` opens the pane; `/foldsmith watch <folder>` follows
an app in another folder (remembered per folder; `/foldsmith watch` alone goes back to the newest); `/foldsmith demo` shows sample
data; `/foldsmith off` returns to the progress file.

Needs Xcode 27.1 with the iOS 27.1 simulator runtime, one iPhone Duo simulator (`xcrun simctl create "iPhone Duo"
com.apple.CoreSimulator.SimDeviceType.iPhone-Duo com.apple.CoreSimulator.SimRuntime.iOS-27-1`), xcodegen (`brew install
xcodegen`) and Claude Code 2.1.308 or later (2.1.236 and older reject the plugin's hooks). The skill fetches the
community `duo.py` driver (`iphone-duo-simulator-skill`) at a fixed commit into `~/Library/Caches/duo-driver` if it is
not on the machine. In a terminal, pictures draw where the
terminal can show images (kitty, Ghostty, iTerm2 3.5+), and the matrix is text.

## Install

At the prompt of a Claude Code terminal session:

```
/plugin install foldsmith --marketplace 3nchiridion/foldsmith
```

Answer `y` to add the marketplace, then pick a scope. From a shell: `claude plugin install foldsmith --marketplace 3nchiridion/foldsmith`.
If `--marketplace` is not offered, Claude Code is older than 2.1.308: run `claude update` first. In the desktop app: click +
next to the prompt box, then Plugins, Add marketplace with `3nchiridion/foldsmith`, then Add plugin.

## What it runs, reads and sends
Everything runs on your Mac, as you. The pane's and the skill's own code send nothing anywhere. What reaches the network
is the one fetch of `duo.py` below, the app's own build and use, and your Claude conversation.

**The pane** (`hooks/register.tsx`, a Claude Code mod) has three hooks:
- `session.start` registers the `/foldsmith` command, reads your home folder (`/usr/bin/printenv HOME`), makes its
  scratch folder (`mkdir -p ~/Library/Caches/foldsmith`), looks for progress files, and starts three timers that run
  for the whole session: every 1.5 seconds it reads the followed app's `.duo/migration.json`, every minute it looks for
  progress files again, and every 4 seconds, only while the pane is drawn on screen and not paused, it takes a frame of
  the simulator;
- `command.run`, for `/foldsmith` only, opens the pane: `demo` shows sample data, `off` goes back to the progress file,
  `watch <folder>` follows that folder and remembers the choice, and with nothing after it, it looks for progress files;
- `ui.render` draws the pane.

The pane follows, and opens by itself for, only a progress file under the session's folder, or the app you picked for
that folder (until `/foldsmith watch` alone); app folders remembered from other sessions are offered in its list and
followed only when you pick one. It runs these programs, each by its
full path in `/usr/bin` or `/bin`, with the paths and the simulator's ID filled in:
- `find <session folder> -maxdepth 5 … -path '*/.duo/migration.json' -print`, to find progress files (it skips
  `node_modules`, `.git`, build folders and captures);
- `git -C <app folder> branch --show-current`, each time the progress file changes, to show the branch;
- `xcrun simctl list devices booted -j`, to find the booted iPhone Duo simulator (the one the progress file names, if
  that one is booted); the live view passes `duo.py` only a simulator it has just found booted (`duo.py` boots one
  that shut down in between, and runs the programs listed under the skill below);
- for the live view, `python3 <duo.py> --udid <ID> shot --out ~/Library/Caches/foldsmith --name live`, where `duo.py`
  is only the one in `~/Library/Caches/duo-driver` or `~/.claude/skills/iphone-duo-simulator`, never a path named by a
  progress file or found in the project; without one, `xcrun simctl io <ID> screenshot ~/Library/Caches/foldsmith/live.png`;
- `sips`, to make a shot a small JPEG in `~/Library/Caches/foldsmith` and read its size;
- `open`, only when you press a button: Open report opens `.duo/REPORT.md` in your text editor and Show captures shows
  the `.duo/captures` folder in Finder, each only when it is a real file or folder in the app's folder and not a link;
  Open before and Open after open that shot in Preview (`/System/Applications/Preview.app`, PNG and JPEG files only).

It reads every `.duo/migration.json` it finds or remembers and the before and after shots those files name, only
inside that app's folder (a path that leads out of it, by `..` or through a link, is ignored), checks that
`.duo/REPORT.md` exists before offering Open report, and reads its own pictures in `~/Library/Caches/foldsmith`, which
it draws inside the pane as embedded images. It writes only those pictures, and in Claude Code's plugin storage the
paths of up to eight app folders where it found a progress file and, for each session folder, the app you chose to
follow (with `/foldsmith watch`, the App picker or a Migrations found button). It changes nothing in your app and makes
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
  `~/Library/Caches/duo-detect`; the static scans with `rg` (ripgrep); and its own scripts with `bash` and `python3`
  (standard library only), which also use `perl` (for time limits), `sips` and `shasum`. The flow file it writes for
  each app (`.duo/flows/<app>.flow`) is run by `bash`: in a repository someone else wrote, read it before you resume a
  migration there, as you would a build script;
- reads the app's code, every shot and the app's crash reports (`~/Library/Logs/DiagnosticReports`) into your Claude
  conversation, may start a fresh subagent to review a screen's diff and shots, and adopts the scene lifecycle with
  Apple's `app-resizability` skill when that is installed;
- changes your app's code and commits each change on a `duo-migration` branch; it never pushes, opens no pull request
  and merges nothing. It writes `.duo/` in your app's folder (the progress file, flows, reports and captures) and adds
  the captures and its lock file to the repository's `.git/info/exclude`. Each capture also leaves its `xcodebuild`
  test logs and results and its accessibility dumps in a `duo-tap.*` folder in your temporary folder.

## Development
The pane's hooks have tests in `hooks/register.test.tsx`; run them with `claude plugin test plugins/foldsmith`
(Claude Code 2.1.308 or later) and check the manifest with `claude plugin validate plugins/foldsmith`. `skills/foldsmith-duo/` here is a copy of the repository's `skills/foldsmith-duo/`, made by
`python3 scripts/sync-skill-references.py` from the repository root. Edit `SKILL.md` and `references/apple.md`,
`simulator.md` and `detectors-static.md` in that folder, and everything else at its source (`patterns/`, `Sources/`,
`scripts/`, `Tap/`), then rerun the script.

## License
MIT (`LICENSE`). iPhone and iPhone Duo are trademarks of Apple Inc. Foldsmith is independent and is not affiliated
with, sponsored by, or endorsed by Apple Inc.

