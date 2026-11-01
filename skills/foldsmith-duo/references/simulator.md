# Driving the iPhone Duo simulator

What worked on the project's Mac (Xcode 27.1, iOS 27.1 runtime). There is no public `simctl` command to fold or turn
a Duo; `duo.py`, the community driver (`iphone-duo-simulator-skill` at commit 60cdda2, MIT), posts the same hinge and
orientation event Xcode's Device Hub posts. It ships with the skill in `tools/driver/` (`duo.py`, `duo_fold.c`, its
licence and a README naming the upstream commit; the repository keeps it in `third_party/duo-driver/`), unchanged, and
the preflight writes its path into `.duo/env` as `DUO_PY` unless you set another (the capture scripts take it by
default too): nothing is downloaded. It drives
only simulators whose name contains "duo" (any case). Device Hub's own buttons work too, by hand.

## The seven poses

| Pose | `duo.py fold` | `duo.py orient` | Window (pt) | Division |
|---|---|---|---|---|
| closed | `close` | `sideways` | 466 × 678 | none |
| closed-sideways | `close` | `upright` | 678 × 466 | none |
| book | `book` | `sideways` | 951 × 669 | vertical, active |
| laptop | `laptop` | `upright` | 669 × 951 | horizontal, active |
| tent | `laptop` | `landscape-right` | 669 × 951 | horizontal, active |
| flat-sideways | `open` | `sideways` | 951 × 669 | vertical, inactive |
| flat-upright | `open` | `upright` | 669 × 951 | horizontal, inactive |

Split View's half window cannot be driven headless. Tent is laptop's fold turned hinge-up; Apple does not define it.
Measurements: `metrics.md`.

## Rules that cost a day to learn
- Never run `xcrun simctl io <duo> screenConfig`: SpringBoard crash-loops on the next hinge event (recovery: shutdown,
  boot).
- Wait about 2 s after a fold before posting an orientation; an orientation posted while the hinge moves is dropped.
- Check the shot's shape against the pose. If it is wrong, post the other orientation, then this one again; a repeat of
  the same orientation can be a no-op for the app.
- `duo.py shot` captures the panel that is drawing. A dark screen can make it save both panels: keep the pose's panel
  (cover for closed poses, inner otherwise).
- Apps with an app-group container need ad-hoc signing for the simulator:
  `CODE_SIGN_IDENTITY=- CODE_SIGN_STYLE=Manual DEVELOPMENT_TEAM= PROVISIONING_PROFILE_SPECIFIER=`.
- Apps without scene lifecycle fail to launch on the 27.1 SDK (taxonomy T13; Apple's App Resizability skill owns it).
- Reset privacy prompts on reinstall (`xcrun simctl privacy <udid> reset all <bundle id>`) or a permission sheet blanks the flow.
- `duo.py orient` logs the simulator's own names: `sideways` prints "portrait" and `upright` prints "landscape-left".
  The table above is what each pose looks like.

## Before the first capture
`bash tools/preflight.sh <app folder>` (from the app folder: `bash <skill>/tools/preflight.sh .`), in a shell that has
not sourced `.duo/env`, checks this Mac and the app, changing nothing but `.duo/env` and one line of
`.git/info/exclude`, and installs, creates, renames or boots nothing. It prints each check as `ok`, `warn` (does not
block), `note` or `missing` (blocks), with the exact fix under each one that is not ok, and exits 0 when nothing
blocks, 1 when something does (writing nothing), 2 for a wrong call:
- Xcode 27.1 selected (`xcodebuild -version`; an unaccepted licence gets its own fix, `sudo xcodebuild -license
  accept`, and when another Xcode is selected, older or newer, an Xcode 27.1 in /Applications goes into `.duo/env` as
  `DEVELOPER_DIR`, so no `sudo` is needed; a newer one with no 27.1 beside it only warns), and the iOS 27.1 simulator
  runtime (`xcrun simctl list -j`);
- a simulator on that runtime whose name contains "Duo", and whether it is booted. With none, it prints the `xcrun
  simctl create "iPhone Duo" …` line for the person to run (an iPhone Duo named otherwise, the `rename` line); never
  run either yourself;
- python3 3.9 or later, and rg, which the static scans and `tools/routes.sh` read code with (in Claude Code, where
  `rg` is a shell function no script can call, `routes.sh` runs Claude Code's own, `$CLAUDE_CODE_EXECPATH`, as `rg`;
  with neither, it blocks);
- at least 5 GB free on the home volume (`df -Pk ~`), a warning under 10, naming the usual folders to clear and
  deleting nothing (Wikipedia's run took it from 12 GB to 2.1 GB);
- the app folder is a git repository with nothing uncommitted outside `.duo/`, since the migration commits. Its fix
  leaves `.duo/` alone (`git stash push --include-untracked -- ':/' ':(exclude).duo'`, or `git add -A` with the same
  pathspec): an audit's progress file, flows, reports and captures are not committed, and a plain stash would take
  them. On `duo-migration` the changes are the migration's own, and the line says so: the run finishes and commits
  that change or puts it aside, logs which, and runs the preflight again;
- Claude Code 2.1.308 or later, for the pane: this session's, else `claude` on PATH (an older one warns; a note where
  there is none: the skill runs in other agents too).
When nothing is missing it writes `.duo/env` (atomically, values shell-quoted), keeps it out of git (`/.duo/env` in
`.git/info/exclude`) and prints one line per value:
- `DUO_UDID`: the Duo simulator: the progress file's `simulator` when it is an available Duo (a resume captures, and
  the person signs in, there; one that is gone warns), else the one `.duo/env` named, else the booted one when exactly
  one is, else the first;
- `DUO_PY`: the bundled driver, `tools/driver/duo.py`;
- `DUO_TAP_XCTESTRUN`: the tap runner, once it is built under `~/Library/Caches/duo-tap/build` (`DUO_TAP_BUILD` names
  another folder) and newer than its source;
- `DEVELOPER_DIR`: only when the Xcode 27.1 it found is not the selected one, or one you set picked it;
- `FOLDSMITH_ENV` and `FOLDSMITH_ENV_SET`: the file's own path, and the values above as it set them, so a later
  preflight knows which values it inherits are its own.
A `DUO_UDID`, `DUO_PY` or `DUO_TAP_XCTESTRUN` you set before it runs wins when it names one that exists (a `DUO_UDID`:
an available Duo simulator on iOS 27.1). One inherited from `.duo/env` (what the sourced file set, `FOLDSMITH_ENV_SET`,
even if the file has been rewritten since, or equal to the value in the app's `.duo/env`) is the preflight's own, not
yours: it says so and derives it again, so after an update the driver and the tap runner are the new copy's, and an
old copy removed blocks nothing. The paths point into
this skill's folder, which moves when the skill is updated: run the preflight at every start and every resume, without
sourcing `.duo/env` first, and start every other tool call with `source .duo/env &&`.

The tap runner is a committed Xcode project (`tools/tap/DuoTap.xcodeproj`), so `xcodebuild` alone builds it, once,
into a cache outside the skill's folder and the app's repository (about 10 s; xcodebuild leaves only an empty
`xcshareddata/swiftpm/` folder inside the project). The preflight prints this line with the UDID filled in, and with
`DEVELOPER_DIR=<the Xcode 27.1>` before it when `.duo/env` names one: `xcodebuild build-for-testing -project
tools/tap/DuoTap.xcodeproj -scheme DuoTapUITests -destination "platform=iOS Simulator,id=$DUO_UDID" -derivedDataPath
~/Library/Caches/duo-tap/build -quiet`. The runner lands at
`~/Library/Caches/duo-tap/build/Build/Products/DuoTapUITests_*.xctestrun`. Then run the preflight again: it adds it to
`.duo/env` as `DUO_TAP_XCTESTRUN`. No xcodegen is needed.

## Probe first, capture once
A full capture starts one test run per screen and takes every pose while it holds the app, about 27 s a cell:
NetNewsWire's 35 cells take about 16 minutes (38 with one test run per cell, as before). While fixing a screen, probe
the poses the change touches instead. A screen with no taps, or an app that reopens where it was, about 25 s a shot:
`duo.py launch <bundle>`, `duo.py fold book`, wait 2 s, `duo.py orient sideways`, `duo.py shot --out <dir> --name
probe`. A screen behind taps: `SCREEN=<screen> ONLY="book laptop" bash tools/capture-app.sh <flow> <scratch dir>`,
the flow's own taps for that one screen in those poses, about a minute plus 27 s a pose (a scratch directory, not
`before` or `after`, so no cell changes). The full capture of every pose is for the audit and the proof.

## Long captures: in the background, one at a time
A full capture outlasts what a shell call may run in the foreground (Wikipedia's 77 cells took 39 minutes), so run it
in the background: in Claude Code with `run_in_background`, which reports the exit code when it ends; elsewhere
`(bash tools/capture-app.sh <flow> <out-dir>; echo "exit $?") > <out-dir>.log 2>&1 &`, then read the log's last
line. The exit code says how it ended:

| Exit | What it means | What to do |
|---|---|---|
| 0 | every cell asked for was captured: each has its line in `<out-dir>/.captured` (its shot and its snapshot landed) | read the table, look at the shots |
| 2 | a wrong call, caught before anything is touched (no lock taken, `capture.txt` as it was): no flow file, no `BUNDLE` or `SCREENS` in it, a `SCREEN=` that names none of its screens, an `ONLY=` word that is not a pose, `DUO_UDID` unset, `DUO_PY` or `DUO_TAP_XCTESTRUN` not a file | fix the call; usually `source .duo/env` |
| 3 | cells not captured: a screen its taps did not reach, a pose with no shot or no snapshot (every such line says "skipped"); `findings.txt` and stderr repeat the lines and list each cell of the run with no line in `.captured` | capture them again (`SCREEN=… ONLY=…`) before reading the table: a missing cell is missing, not clean |
| 4 | under 3 GB free on the disk of the home folder or the output folder, checked before the capture, before each screen and before the detectors' build; the message names the space and the three largest `~/Library/Caches/duo-*` folders with their sizes | delete nothing; hands-free, put it first in `todo` and end the run, so the person frees space; then `RESUME=1` |
| 5 | another capture holds `.duo/.capture.lock` and its pid is a running `capture-app.sh` or `capture-corpus-flow.sh`; nothing was touched | wait for it to end; never remove the lock of a live capture |
| 128 + n | stopped by signal n: 130 INT, 143 TERM, 129 HUP | the same command with `RESUME=1` |
| any other (usually 1) | an unexpected failure; `capture.txt` ends with a `stopped:` line naming the screen and pose | read it and the runner's log (`$XCODE_OUT/<screen>.log`), then `RESUME=1` |

Never start a build or a second capture while one runs: both drive the one simulator. The lock is `.duo/.capture.lock`
beside the progress file (`CAPTURE_LOCK` names another; `capture-corpus-flow.sh` or `capture-corpus-app.sh` run on its
own takes `.duo/.capture.lock` under the current folder). It holds the capture's pid, start time, flow sha256 and output
folder, from before `capture.txt` is written until the capture ends, and a `flow pid` line for the
`capture-corpus-flow.sh` that `capture-app.sh` runs; the Foldsmith pane runs nothing for its live frame while it is
there. A lock is live while any pid in it is a running capture; one whose pids are dead, or now belong to programs that
are no capture, is replaced with a note. A `capture-app.sh` killed outright (`kill -9`, a task stop that kills only its
pid: no trap runs) leaves its flow script running alone; that one notices it has lost its parent (before each screen
and pose, and while it waits for the runner), lets the runner go, ends `capture.txt` with `stopped: capture-app.sh (pid
N) was killed without stopping the capture at …`, and removes the lock, so no second capture ever drives the simulator
beside it.

An interrupted capture (INT, TERM or HUP: Ctrl-C, a shell's time limit, a closed terminal) touches the runner's
`release` flag, sends xcodebuild TERM if it has not exited within 10 s and KILL 10 s after that, removes the lock, and
ends `capture.txt` with `stopped: interrupted (SIG…) at <screen> in <pose>, <time>. The cells captured before it are
kept: the same command with RESUME=1 carries on from there.`, naming the signal the person sent (`capture-app.sh`
passes INT on to its flow script as USR1, since a background job ignores INT). Any other early exit writes the same
line with `exit N`.

Each cell captured (its shot and its snapshot) is recorded in `<out-dir>/.captured` with the flow's sha256. With
`RESUME=1`, the same flow file into the same folder keeps the cells recorded there whose files still exist ("kept from
the earlier capture"; a screen with every cell kept starts no runner), captures the rest, adds a `resumed:` line to
`capture.txt`, and runs the detectors over the whole folder. A changed flow (another sha256) says so and captures every
cell. A capture without `RESUME=1` first clears the record of the cells it takes, so a resume never keeps a cell an
earlier build captured.

## Taps
A tap takes about 4 s. If the runner's log (`$XCODE_OUT/<screen>.log`) shows "Wait for com.apple.springboard to idle"
followed a minute later by "App animations complete notification not received" before each tap, XCTest's handling of
system alerts is back on: the runner turns it off (SpringBoard on the Duo simulator can keep an animation running, the
status bar's Wi-Fi "searching"), and `DUO_SYSTEM_ALERTS=1` is the only thing that turns it on. A flow with many taps
can still need more than the 150 s a screen gets to launch and reach its screen: raise `TAP_TIMEOUT`.

## Tools bundled with this skill (`../tools/`, copies of the Foldsmith repository's)
- `tools/capture-app.sh <flow-file> <out-dir>`: the whole capture in one command. Every screen the flow file lists
  (`BUNDLE=`, optional `LAUNCH_ARGS=`, optional `APP_PATH=<.app>`, `SCREENS=( "<screen>=<tap>;…" … )`), every pose,
  each with its snapshot, then the detectors: `<out-dir>/detectors.md`. The app must be installed on the simulator
  already (`xcrun simctl install "$DUO_UDID" <.app>`, a booted simulator; build it with `-derivedDataPath` outside its
  repository, `~/Library/Caches/duo-build/<app>`, so the build leaves nothing uncommitted there). `APP_PATH` instead
  uninstalls the app and installs that `.app` afresh before every screen (with its privacy prompts reset), for an app
  that remembers its onboarding: it clears the app's data and any login each time. Use it for the audit
  (`.duo/captures/<app>/before`) and the proof (`…/after`).
  `LAUNCH_ARGS` are user defaults: write a boolean as `-Key '<false/>'` (property-list syntax), since `-Key NO` arrives as
  the string "NO" and an app that reads a `Bool` ignores it. The app keeps its saved settings from screen to screen (a
  screen's taps that open the contents leave them open for the next), so pin every setting a capture depends on there.
  `SCREEN="a b"` and `ONLY="book laptop"` limit it to those screens and poses; `TAP_TIMEOUT` (default 150 s) is how
  long a screen's taps may take. Before each screen it removes that screen's shots and snapshots in the poses it is
  about to take, so a pose it misses is missing, not the earlier pass's picture. It exits 3, and repeats the lines,
  when any cell of the run has no line in `<out-dir>/.captured` (a skip, a failed shot, a missing snapshot): a missing
  cell is not clean. Rerun those cells (`SCREEN=… ONLY=…`) before reading the table: a `SCREEN=` rerun into the same
  folder adds to its `capture.txt` under a "recaptured" line and keeps the first pass's lines; for the flow's other
  screens each one's latest capture decides, so a screen skipped earlier and not captured since still counts as
  missing.
  `RESUME=1` and `CAPTURE_LOCK`: "Long captures". `PROGRESS` (default `.duo/migration.json`) is the progress file the
  cells are written to, and the lock goes beside it. `CAPTURE_LOCK_PID` and `FLOW_SHA` are what `capture-app.sh` sets
  for `capture-corpus-flow.sh`, not for you. Exit codes: "Long captures".
- `tools/capture-corpus-app.sh <name> <bundle-id>`: the launch screen of an installed app in every pose, under the
  same lock and disk guard as the others.
- `tools/capture-corpus-flow.sh <name> <bundle-id> '<screen>=<tap>;<tap>' …`: deeper screens, reached by XCUITest
  taps on the shut phone (taps reach only the cover), then folded into each pose and shot. One test run serves a
  screen in every pose: before each inner pose the phone is shut again and `tools/same-screen.py` checks it still
  shows the screen; when it does not, the line says so, naming the pose after which it was lost (evidence for T7 in
  that pose), and the runner relaunches and taps again. What scrolls and what lies on a map (its place names, the
  pins and counts an app draws over it) are left out of that comparison. A plain tap step on a disabled element waits
  up to 15 s for it to be enabled and fails the screen if it never is (a button the app enables once its page has
  loaded), so a flow no longer lands silently on the screen before it; a `try:` step does not wait.
  A menu or popover the last tap opens closes on the next fold, so the inner poses read as "lost the screen" (not T7):
  capture an overflow menu in a probe flow with `ONLY="closed closed-sideways"`, and read what an inner pose's overflow
  holds from its snapshot (what the bars lack) and the code. A control that exists only on the inner display (a button
  in a detail pane, a list pane that now holds another screen) cannot be tapped: check it by its shots and its code
  path, and say so in the report.
  `FRESH=1` relaunches before every inner pose. `SNAPSHOT=1` also saves the
  app's accessibility tree in that pose (`<screen>-<pose>.json`), which is what the detectors read. Its runner: "Before
  the first capture".
- `tools/progress.py`: every change to `.duo/migration.json` (`init`, `phase`, `screen`, `cell`, `todo`, `done`,
  `waive`, `issue`, `log`, `check`, `show`; `--help` lists them), locked and written whole. `capture-app.sh` calls it
  for each shot of a `before` or `after` capture, so the cells get their pictures as the capture goes. A wrong line
  comes out the same way it went in: `todo --remove <prefix>`, `done --remove <prefix>`. A done line names its screens
  as the pane reads them: the words before its first `: `, split at commas and "and", each a screen's name or its first
  words (`article and contents from Home: …`); one with no `: `, or a part that names no screen, is refused. `done
  <screen>: …` and `phase done` refuse, changing nothing, while any of these is left on that screen (on any screen,
  for `phase done`); `check [<screen>…]` lists them, then the open issues, regressions first, and exits 1 if anything
  blocks (2 for a name that is no screen):
  - a pose clean in the before folder's detectors.md that has a finding in the after folder's, or no after capture;
  - a pose with findings before whose after cell has a class the before one did not (`<screen> book: T1 T5 before, T14
    after (T14 is new)`): a new problem, not the old one fixed;
  - a pose not captured before (`n/a` in the before table: a cell the audit's capture skipped) that has a finding
    after, not waived: nothing tells it from a regression until that pose is captured into `before` (from the commit
    the migration started from, as for a screen behind a login below);
  - a cell marked `unchanged` whose before and after snapshots (`<screen>-<pose>.json` beside the shots) differ in
    layout: every element with a label or an identifier outside scrolling content and not a system element (the ones
    `same-screen.py` ignores are ignored), as type, label or identifier, and frame in whole points, and the rows with
    an identifier and no label of a list outside scrolling content (a sidebar's). Other rows of lists are not
    compared: look at both shots of a list before you leave its cell `unchanged`. What moves on its own is not
    counted: text that changes only its numbers in place (a clock, a relative date), the keyboard, and on a map the
    pins at its edge and the card a pin opens. Mark the cell `verified` if it changed and is right, or `waive <screen>
    <pose> unchanged "<why>"` where only other live content moved (a toast, content still loading, a feed's rows). A
    cell with no snapshot to compare, or one that cannot be read, is noted, not counted: it proves nothing either way;
  - an open issue marked as a regression.

  `waive <screen> <pose,…> <id> "<why>"` records on its cell a detector line, or a new class, the shot does not bear
  out (a pose not captured, or `no-rotate`, cannot be waived: no detector ran there). `issue add <screen>
  <pose,…|all|inner|-> <high|medium|low> "<what happens>" [--regression] [--found-by detector|eye|review|test]
  [--where <file:line>]` records what a review, a look or a test found that no detector table shows (`-` for no pose;
  `--found-by` is `review` unless given) and prints its id (`I1`, `I2`, …, never reused); the screen is one the file
  or the before table names (one the flows do not reach: `screen <name>` first). `issue fix <id> "<how>"` and `issue
  wontfix <id> "<why>"` close it, and `wontfix` is refused for a regression (fix it, or revert the change that caused
  it). `show` counts the open issues. Each capture removes a screen's snapshots in the poses it takes first, so a pose
  it skips is not captured.
- Both write to `.duo/captures/<name>/` in the current directory (`OUT=<dir>` to change it). `DUO_PY` defaults to the
  bundled `tools/driver/duo.py`; without `DUO_UDID` (and `capture-corpus-flow.sh`, with it `capture-app.sh`, without
  `DUO_TAP_XCTESTRUN`), they exit 2 before touching anything. `source .duo/env` sets all three.
- `tools/preflight.sh <app folder>`: the checks and `.duo/env` ("Before the first capture").
- `tools/appstore.py`: the App Store set ("App Store screenshots").
- `swift run --package-path tools/detect --scratch-path ~/Library/Caches/duo-detect duo-detect <out-dir> --markdown
  <out-dir>/detectors.md`: `capture-app.sh` runs it over every capture, so the proof needs no separate run, and
  `progress.py` and `appstore.py` read only that `detectors.md` beside the shots. The taxonomy
  detectors (T1, T2, T4, T5, T10, T14, T15, and T7 across poses) on those snapshots, one row per screen, one column per
  pose. T10 covers custom-view toolbar items as well as text ones, T7 in book or flat-sideways can mean the shut
  phone's stranded toolbar items are gone there (the line says which), and T14 also reports a leading pane whose
  search field or segmented control stops well short of the fold. A cell reading `no-rotate` means the app's window kept the other orientation in that pose. A
  snapshot taken while the app was not in front means it crashed or quit on the way to that pose: `capture.txt` gets a
  line for it, `capture-app.sh` repeats it at the end in `findings.txt` and on stderr as T7 in that cell, never a clean
  one (the exit code does not change), and the detectors' T7 line says "the app was not in front". The shot shows the
  Home Screen, and the simulator's crash report (`~/Library/Logs/DiagnosticReports/<app name>-<date>.ips`, moved to
  `Retired/` after a while) says where. A crash on the fold can be intermittent: one capture without it proves nothing.
- `tools/routes.sh <app folder> [<type or file name> …]`: the route inventory a structural change's proposal in
  `.duo/PLAN.md` carries, and the change takes through, every line of it: each push, stack replaced, pop,
  presentation, SwiftUI navigation, state restoration, URL, notification and quick action in the app's Swift code, and
  each walk of the hierarchy (`as? UINavigationController`, `selectedViewController`, `viewControllers`, …), as a
  Markdown table (`| file:line | kind | code |`) with a count by kind. With names, only the files that mention one or
  are so named (the types the change wraps or reroutes). It reads the code with `rg`, skipping tests and build folders;
  in Claude Code, where `rg` is a shell function a script cannot call, it runs Claude Code's own
  (`$CLAUDE_CODE_EXECPATH`) as `rg`. A SwiftUI app's moves are listed where it changes a `…path` (`append`,
  `removeLast`, `= []`) or calls a router's `navigate(to:`; follow the rest of an app's own router by hand
  (IceCubesApp presents its sheets by setting `routerPath.presentedSheet`).

What the snapshot-based detectors can and cannot see: they read what accessibility exposes. A SwiftUI grid without
accessible cells is measured from its text; decoration (a sheet's shadow) is ignored; content under a sheet is not in
the tree while the sheet is up. A finding is a frame measurement, so look at the screenshot before you act on it.
Known misreads (Wikipedia): text the app keeps in the tree while hidden can make a column (T14), and so can what
another screen covers (the list's search field under the contents in the list pane read as T14, and VoiceOver reached
it too: hide what you cover from accessibility); a screen shown as an
overlay on the cover and inline on the inner display reads as lost (T7); a control over a map smaller than 100 pt pans
with it (T1 skips it). What accessibility does not show, no detector sees: text cut off at a pane's edge, words broken
in a narrow column, an action moved into an overflow, a control's selected look (the fill Wikipedia's open-contents
button lost, found only by counting its pixels against before). A pane's content stopping short of the fold is T14 only where a
search field or a segmented control shows it; measure the rest against the pane in the snapshot. Record each of these
you find with `progress.py issue add` (`--regression` when it is worse than before), so `done` and the report know it.

## App Store screenshots
`python3 tools/appstore.py [--kind after|before] [--file .duo/migration.json] [--out .duo/appstore]` takes, per screen,
the shots App Store Connect's iPhone Duo screenshots need from a capture already made (`after` by default; an audit's
`before`). The sizes are the ones Apple's screenshot specifications list for iPhone Duo, which the captures already
are: the outer display 1398 × 2034 (`closed`) and 2034 × 1398 (`closed-sideways`), the inner display 2007 × 2853
(`flat-upright`, else `laptop`) and 2853 × 2007 (`book`, else `flat-sideways`). It takes a cell only when it is
`verified` or `unchanged` (for `before`, only `unchanged`: a verified cell's before shot is the layout that was fixed),
its detector table has no class in that pose (waived or not; `no-rotate` and `n/a` neither, and a missing table
refuses every cell), no open issue names it in that pose, and its shot is that size (it never resizes one). Each shot kept is flattened with `sips` to a JPEG with no alpha channel (the
captures have one, which App Store Connect refuses) and read back. It writes `<out>/<size>/NN-<screen>-<pose>.jpg` and
a `README.md` listing each file, each cell passed over and why, and telling the person to check every image for
personal content and the status bar (the capture does not override the clock). It puts `<out>` in
`.git/info/exclude`, as its path from the repository's top (an app in a subfolder of a larger repository too), and
never uploads anything. A rerun replaces only its own `NN-*.jpg` files and its own README (first line `# App Store
screenshots for iPhone Duo`); a `README.md` in `<out>` that it did not write stops it before anything changes, and an
`<out>` that is the app's folder, the repository's top, a folder above either, or `.duo/` itself is refused. A shot
path in the progress file that leads outside the repository is refused unread. Exit 0 when at least one file was
written, 1 when none could be, 2 without `sips` or a progress file, or for an `<out>` refused.

## Screens behind a login: the second pass
The run never signs in and never types credentials. A screen only a login reaches waits in `todo` as `needs sign-in:
<screen>`, its flow line in `.duo/flows/<app>-login.flow`, and the report and the closing message ask the person to
sign in on the Duo simulator themselves, naming it (`iPhone Duo (<UDID>)`, the progress file's `simulator`, which the
next preflight takes), and run `/foldsmith-start` again. On that resume:
- Never uninstall: that signs the person out. `APP_PATH` in a flow uninstalls the app before every screen, so capture
  these screens from a flow without it (`.duo/flows/<app>-login.flow`), always with `SCREEN=` so the folder's
  `capture.txt` is added to, not replaced, and run no flow with `APP_PATH` at all, for any screen, until these screens
  are captured into `after`. A new build goes on
  over the old one: `xcrun simctl install` keeps the app's data and the login.
- Check each one again with a `closed` capture into a scratch folder. One still not reached stays in `todo` with what
  the shot shows (a session lost on relaunch, a login asked for again).
- Each one reached: `progress.py screen <name>`, `todo --remove "needs sign-in: <name>"`, then the workflow from step 2
  for it. Its before is the app as it was before the migration: once a `Duo:` commit exists, build the commit the
  migration started from (the parent of the first `Duo:` commit) in a `git worktree` outside the app's folder (removed
  afterwards), install it over the app, capture into `before` with `SCREEN=`, then install the current build again and
  carry on hands-free.
- The shots now hold the person's own content: they stay in `.duo/captures/` (out of git), the report links them and
  never copies them anywhere git keeps.
