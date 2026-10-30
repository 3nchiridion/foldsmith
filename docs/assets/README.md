# The demo recording

The README opens with a 45–60 second recording of `/foldsmith-start` on NetNewsWire: the matrix fills, then before and
after on the fold. This page says what to record and how to lay out the screen, so a take can be redone the same way.

## What goes where
| File | What | Budget |
|---|---|---|
| `docs/assets/demo.gif` | an 8–10 s loop: the matrix filling, then one before/after on the fold. The README shows it inline | 1.5 MB at most: 960 px wide, 10–12 fps, 128 colours |
| `demo.mp4` | the full 45–60 s cut. Not in this repository, which it would make large again, and not on a release of it either: `gh skill install` takes a repository's latest release over its main branch. Put it on a release of foldsmith-evidence and link the GIF to that release's page, where it plays (an asset link downloads instead) | H.264, 1920 × 1080, 30 fps, AAC or no audio, under 50 MB |

Replace the `<!-- DEMO: … -->` comment under the README's title with:

```html
<p align="center"><a href="<the foldsmith-evidence release page>"><img src="docs/assets/demo.gif" alt="/foldsmith-start on NetNewsWire: the pose matrix fills in, then a screen before and after on the fold" width="960"></a></p>
```

## Before you record
- NetNewsWire at the commit the evidence run used (`d9ec7df`, foldsmith-evidence `verification/runs/NetNewsWire/`), in a
  folder with a neutral path (for example `~/demo/NetNewsWire`): the path shows in the pane's header.
- Feeds you own or that are public domain, or NetNewsWire's bundled defaults. No one's private posts, no account.
- The iPhone Duo simulator booted (iOS 27.1, Xcode 27.1), the app not yet migrated (no `.duo/` folder; delete it to
  re-record), the `duo-migration` branch absent.
- The Foldsmith plugin installed in the Claude Code desktop app (+ next to the prompt box, then Plugins, Add marketplace
  `3nchiridion/foldsmith`, then Add plugin), where the pane draws its matrix and shots; a terminal draws text.
- macOS: dark mode, a Focus mode on (no notifications), the Dock hidden, the menu-bar clock hidden or at a neutral time.
  Claude Code: a fresh session named something neutral; the pane docked on the right.

## Screen layout
One 1920 × 1080 display (or a window of that size), recorded whole:

```
┌──────────────────────────── 1920 ────────────────────────────┐
│ Claude Code transcript (~960 px)  │  Foldsmith pane (~960 px) │
│                                   │  matrix across the top    │
│ /foldsmith-start                  │  Left/Done | picked cell  │
│ … the run's narration …           │  before / after, the fold │
└───────────────────────────────────┴───────────────────────────┘
```

Size the pane so what is left and done sits beside the picked cell: it switches to two columns at about 105 columns of
its code font, roughly 800 px or more. Make the transcript's text large enough to read at 720p (View → Zoom In), then
check the pane again: zoom scales it too, and if it drops to one column, widen it or zoom once less.

## Shot list (45–60 s)
| Time | On screen | Edit |
|---|---|---|
| 0–4 s | The pane on NetNewsWire before anything runs; cut to the before shot of the timeline in book pose: the split boundary at 320 pt, a third of the way across, and the detail pane lying across the fold | caption: "NetNewsWire on iPhone Duo, before" |
| 4–9 s | Type `/foldsmith-start`, press Return | real time |
| 9–35 s | The run: screens found, the matrix filling cell by cell (red, then blue, amber, green) | sped up 8–16×, caption "sped up"; cut the waiting |
| 35–52 s | Pick the timeline in book: before and after side by side with the fold drawn; Next › once (Next defect, if a cell is still a finding) | real time |
| 52–60 s | End card: "Foldsmith — measured layout patterns and hands-free migration for iPhone Duo, proven in every pose", `github.com/3nchiridion/foldsmith`, and "iPhone and iPhone Duo are trademarks of Apple Inc. Foldsmith is not affiliated with Apple." | still |

The GIF is cropped to the pane (about 960 px wide, so 1:1): two seconds of the matrix filling, then 6–8 seconds of the
before/after from 35–52 s, looped.

## Rules
- Say "on the simulator" in a caption: these are simulator captures, not a device.
- No Apple product imagery animated, tilted or redrawn; the simulator's own frames only.
- No Ice Cubes or other apps with strangers' posts on screen.
- Nothing personal: your name, other projects, notifications, the full home path.
- A real run, cut for time; never a staged matrix. The sample data from `/foldsmith demo` may be used only if the
  caption says "sample data".
