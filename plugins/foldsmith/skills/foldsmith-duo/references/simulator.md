# Driving the iPhone Duo simulator

What worked on the project's Mac (Xcode 27.1, iOS 27.1 runtime). There is no public `simctl` command to fold or turn
a Duo; `duo.py` (community driver, `iphone-duo-simulator-skill`) posts the same hinge and orientation event Xcode's
Device Hub posts. Device Hub's own buttons work too, by hand.

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

## Probe first, capture once
A full capture starts one test run per screen and takes every pose while it holds the app, about 27 s a cell:
NetNewsWire's 35 cells take about 16 minutes (38 with one test run per cell, as before). While fixing a screen, probe
the poses the change touches instead. A screen with no taps, or an app that reopens where it was, about 25 s a shot:
`duo.py launch <bundle>`, `duo.py fold book`, wait 2 s, `duo.py orient sideways`, `duo.py shot --out <dir> --name
probe`. A screen behind taps: `SCREEN=<screen> ONLY="book laptop" tools/capture-app.sh <flow> <scratch dir>`, the flow's
own taps for that one screen in those poses, about a minute plus 27 s a pose (a scratch directory, not `before` or
`after`, so no cell changes). The full capture of every pose is for the audit and the proof.

A tap takes about 4 s. If the runner's log (`$XCODE_OUT/<screen>.log`) shows "Wait for com.apple.springboard to idle"
followed a minute later by "App animations complete notification not received" before each tap, XCTest's handling of
system alerts is back on: the runner turns it off (SpringBoard on the Duo simulator can keep an animation running, the
status bar's Wi-Fi "searching"), and `DUO_SYSTEM_ALERTS=1` is the only thing that turns it on. A flow with many taps
can still need more than the 150 s a screen gets to launch and reach its screen: raise `TAP_TIMEOUT`.

## Tools bundled with this skill (`../tools/`, copies of the Foldsmith repository's)
- `tools/capture-app.sh <flow-file> <out-dir>`: the whole capture in one command. Every screen the flow file lists
  (`BUNDLE=`, optional `LAUNCH_ARGS=`, `SCREENS=( "<screen>=<tap>;…" … )`), every pose, each with its snapshot, then the
  detectors: `<out-dir>/detectors.md`. Use it for the audit (`.duo/captures/<app>/before`) and the proof (`…/after`).
  `LAUNCH_ARGS` are user defaults: write a boolean as `-Key '<false/>'` (property-list syntax), since `-Key NO` arrives as
  the string "NO" and an app that reads a `Bool` ignores it. The app keeps its saved settings from screen to screen (a
  screen's taps that open the contents leave them open for the next), so pin every setting a capture depends on there.
  `SCREEN="a b"` and `ONLY="book laptop"` limit it to those screens and poses; `TAP_TIMEOUT` (default 150 s) is how
  long a screen's taps may take. It exits 3, and repeats the lines, when any screen or pose was skipped: a skipped cell
  is missing, not clean. Rerun those cells (`SCREEN=… ONLY=…`) before reading the table: a `SCREEN=` rerun into the
  same folder adds to its `capture.txt` under a "recaptured" line and keeps the first pass's lines; each screen's
  latest capture decides the exit code, so a screen skipped earlier and not captured since still counts as missing.
- `tools/capture-corpus-app.sh <name> <bundle-id>`: the launch screen of an installed app in every pose.
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
  app's accessibility tree in that pose (`<screen>-<pose>.json`), which is what the detectors read. Build its runner
  once, outside the skill's folder and the app's repository (about 10 s): `T=~/Library/Caches/duo-tap; mkdir -p $T &&
  xcodegen generate --spec tools/tap/project.yml --project $T && xcodebuild build-for-testing -project
  $T/DuoTap.xcodeproj -scheme DuoTapUITests -destination "platform=iOS Simulator,id=$DUO_UDID" -derivedDataPath
  $T/build`, then `DUO_TAP_XCTESTRUN=$(ls $T/build/Build/Products/*.xctestrun)`.
- `tools/progress.py`: every change to `.duo/migration.json` (`init`, `phase`, `screen`, `cell`, `todo`, `done`,
  `log`, `show`; `--help` lists them), locked and written whole. `capture-app.sh` calls it for each shot of a `before`
  or `after` capture, so the cells get their pictures as the capture goes. A wrong line comes out the same way it went
  in: `todo --remove <prefix>`, `done --remove <prefix>`. `done <screen>: …` and `phase done` compare the detectors.md
  in the before and after folders and refuse, changing nothing, while a pose clean before has a finding after or no
  after capture; `check [<screen>…]` lists those (exit 1 if any), and `waive <screen> <pose,…> <id> "<why>"` records a
  line the shot does not bear out on its cell (a pose not captured, or `no-rotate`, cannot be waived: no detector ran
  there). Each capture removes a screen's snapshots in the poses it takes first, so a pose it skips is not captured.
- Both write to `.duo/captures/<name>/` in the current directory (`OUT=<dir>` to change it) and need `DUO_UDID` and
  `DUO_PY` (the path to `duo.py`).
- `swift run --package-path tools/detect --scratch-path ~/Library/Caches/duo-detect duo-detect .duo/captures/<name>
  --markdown .duo/detectors.md` (`capture-app.sh` runs it): the taxonomy
  detectors (T1, T2, T4, T5, T10, T14, T15, and T7 across poses) on those snapshots, one row per screen, one column per
  pose. T10 covers custom-view toolbar items as well as text ones, T7 in book or flat-sideways can mean the shut
  phone's stranded toolbar items are gone there (the line says which), and T14 also reports a leading pane whose
  search field or segmented control stops well short of the fold. A cell reading `no-rotate` means the app's window kept the other orientation in that pose. T7 in a pose whose
  line says "the app was not in front" means it crashed or quit on the way there: the shot shows the Home Screen, and
  the simulator's crash report (`~/Library/Logs/DiagnosticReports/<app name>-<date>.ips`, moved to `Retired/` after a
  while) says where. A crash on the fold can be intermittent: one capture without it proves nothing.

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
search field or a segmented control shows it; measure the rest against the pane in the snapshot.
