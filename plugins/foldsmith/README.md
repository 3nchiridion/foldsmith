# Foldsmith plugin

Adapt a whole iOS app to iPhone Duo hands-free, and watch it happen. One install brings:

- **The `foldsmith` skill** (`skills/`): finds the app's screens, captures each one in all seven Duo poses,
  classifies it against the decision table, applies the pattern's reference implementation, and proves every pose
  with before/after screenshots and the detectors. It never stops to ask; what it cannot do goes to its "left" list
  with the reason. It commits one screen at a time on a `duo-migration` branch and never pushes.
- **`/duo-start`**: the one command to run in your app's folder. Run it again in a later session and it resumes from
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

Commands: `/duo-start [app folder]` runs or resumes the migration; `/duo` opens the pane; `/duo watch <folder>` follows
an app in another folder (remembered per folder; `/duo watch` alone goes back to the newest); `/duo demo` shows sample
data; `/duo off` returns to the progress file.

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
If `--marketplace` is not offered, Claude Code is older than 2.1.308: run `claude update` first. To skip the
repository's evidence (about 79 MB in all): `claude plugin marketplace add 3nchiridion/foldsmith --sparse
.claude-plugin plugins`, then `claude plugin install foldsmith@foldsmith`. In the desktop app: click + next to the prompt box, then Plugins, Add marketplace
with `3nchiridion/foldsmith`, then Add plugin.

## Development
The pane's hooks have tests in `hooks/register.test.tsx`; run them with `claude plugin test plugins/foldsmith`
(Claude Code 2.1.308 or later) and check the manifest with `claude plugin validate plugins/foldsmith`. `skills/foldsmith/` here is a copy of the repository's `skills/foldsmith/`, made by
`python3 scripts/sync-skill-references.py` from the repository root. Edit `SKILL.md` and `references/apple.md`,
`simulator.md` and `detectors-static.md` in that folder, and everything else at its source (`patterns/`, `Sources/`,
`scripts/`, `Tap/`), then rerun the script.

## License
MIT (`LICENSE`). iPhone and iPhone Duo are trademarks of Apple Inc. Foldsmith is independent and is not affiliated
with, sponsored by, or endorsed by Apple Inc.

