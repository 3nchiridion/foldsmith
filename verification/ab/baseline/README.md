# verification/ab/baseline/

The three A/B apps unmodified, at their `baseline` commits, through the frozen flows (`../flows/`) with
`scripts/capture-poses.sh`, on the iOS 27.1 Duo simulator the runs use, 2026-10-27. They are the "before" for the
report and the check that every frozen flow reaches its screen. Raters do not see them.

Each folder holds `<screen>-<pose>-<panel>.png` (the shot), `<screen>-<pose>.json` (the accessibility snapshot taken in
the same pose), `capture.txt` (flow hash, time, device), `detectors.md` and `findings.txt`.

Every flow reached every screen in every pose: 4 + 3 + 4 screens × 7 poses, 77 shots, each with its snapshot.

## Findings checked against the shots

Every finding was compared with its screenshot. "Yes" means the shot shows it; "no" means the element is in the tree
but not on screen (covered elements stay in XCTest's tree, `docs/history/DEVIATIONS.md`).

### HomeAssistant

| screen | pose | class | element | on screen |
|---|---|---|---|---|
| launch | book | T1 | Connect to my Home Assistant (265.7–685.7) | yes |
| launch | book | T1 | Learn more (432.8–518.5) | yes |
| launch | book | T5 | centred text column 194.5–756.8 | yes |
| launch | flat-sideways | T5 | the same column, inactive division | yes |
| manual-url | book | T15 | address sheet 8–467.5 on the leading half | yes |
| servers | book | T1 | Enter address manually (325–542.3) | yes |
| servers | book | T5 | server list 213.2–653.8 | yes |
| servers | flat-sideways | T5 | the same list, inactive division | yes |
| servers | book | T1 | searching-servers-dots, logo-in-circle, "Check that your Home Assistant is powered on…" | no: the server list covers them |
| servers | laptop, tent | T1 | searching-servers-dots, logo-in-circle | no: the server list covers them |

Seen in the shots and not found:
- **learn-more, book:** the Safari sheet (`SFSafariViewController`) sits on the leading half, a T15. Its content is
  drawn by another process; the tree holds only a window-sized container after `PopoverDismissRegion`, so the adapter
  has no sheet frame to judge.
- **launch, laptop and tent:** the second description line ("Home Assistant is open source…", y 410.7–497) lies across
  the horizontal fold. It is inside a scroll view, and T1 exempts scrolling content; this one is too short to scroll.

Launch in closed was shot again after the run: its first snapshot was lost while the simulator service was stuck behind
a second Duo simulator (deleted, `../PROTOCOL.md`). `capture.txt` records it.

### IceCubesApp

| screen | pose | class | element | on screen |
|---|---|---|---|---|
| launch | book | T15 | Add Account sheet 8–467.5 on the leading half | yes |

The timeline in book is the system split: the sidebar ends inside the fold (475.5 pt) and the posts start past it
(495.7 pt). The launch and timeline shots are redacted (`scripts/redact-shots.py`): posts are blocks, photos and server
banners are flat colour. The timeline's rows report the window's full width in the tree; the adapter measures a row by
what it holds, so it reads the posts' column at 515.7–847 pt (`docs/history/DEVIATIONS.md`).

### NetNewsWire

| screen | pose | class | element | on screen |
|---|---|---|---|---|
| article | book | T14 | the article pane 340–827 beside the 320 pt timeline | yes |
| settings | book | T15 | Settings sheet 8–467.5 on the leading half | yes |

With nothing to restore, the app opens on the inner screen with its feeds sidebar hidden and "No selection" in the
detail pane; the feeds list shows only on the cover. The timeline in book is the 320 pt timeline beside an empty detail
pane, which has no content to judge. The flow overrides the app's saved selection at every launch (`../flows/`,
`docs/history/DEVIATIONS.md`): before that, every capture after the first article started on that article. Reading the article
marks it read, so the inessential feed's unread count drops by one after the first article capture.
