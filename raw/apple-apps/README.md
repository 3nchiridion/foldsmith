# Apple's apps as oracle — Mac phase Step 3

Captured with `scripts/capture-system-apps.sh` on the iPhone Duo simulator (iOS 27.1, 24A94425), poses driven by
duo.py. Screenshots are `<app>/<pose>-inner.png` or `<pose>-cover.png` (the display that was drawing); the line per
pose is in `<app>/NOTES.md`. `_probe/` holds the DuoProbe shots from Step 2.

**Coverage: 2 of 11 apps.** The simulator runtime ships only Settings and Safari. Notes, Photos, Calendar, Reminders,
Maps, Files, Contacts, Mail and Music need a physical Duo; their NOTES.md say so.

## What the two apps show

| | Settings | Safari |
|---|---|---|
| Closed (cover) | single list, floating search button; no bars | **vertical bar on the trailing edge** (back, bookmarks top; new tab, tabs bottom), search at the bottom |
| Cover turned | **does not rotate** | rotates; vertical bar becomes one top bar |
| Book (active vertical fold) | **split view boundary moves onto the fold** (sidebar ≈475 pt) | ignores the fold; cards span it |
| Laptop / tent (active horizontal fold) | ignored; columns scroll across it | ignored; content scrolls across it, controls stay at the top |
| Flat sideways | default sidebar ≈320 pt | as book |
| Flat upright | as laptop | as laptop |

- Only one of the two apps adapts to the fold, and only to the vertical one: Settings' split view aligns its column
  boundary with the active division in book and drops back to its default width when flat.
- Neither app follows the HIG's laptop advice (content on the raised half, controls on the flat half); both treat the
  horizontal fold as scrollable space. Tent looks exactly like laptop in both.
- On the inner display neither app draws a vertical bar; Safari keeps a top bar even sideways, where the window's
  trailing inset is 84 pt.

Limits: fresh simulator (signed out, no data, first launch), one screen per app, no interaction between poses.
