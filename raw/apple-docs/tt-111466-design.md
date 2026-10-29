# Tech Talk 111466 — Design for iPhone Duo

Presenters: Marcos, Vince (Apple Design).
Page: https://developer.apple.com/videos/play/tech-talks/111466/
HD: https://devstreaming-cdn.apple.com/videos/tech-talks/111466/1/980a0539-ceb6-4452-b0e8-e47ae3347068/downloads/tech-talks-111466_hd.mp4?dl=1

## Chapters
0:00 Intro · 0:28 Design principles · 3:42 Adapting your design · 5:07 Positioning controls · 6:33 Outer display · 7:34 Inner display · 8:36 Sheet behavior · 9:28 Fold avoidance · 10:01 Conclusion

## Guidance (close paraphrase)
- Closed: compact, familiar, one-hand. Open: largest iPhone display. Also used partially folded, seated like a laptop, standing.
- Closed pose: controls move from top/bottom to the **right side** to maximize vertical space and right-thumb reach. Partially folded: content shifts away from the center curve; interactive elements move to the sides or the bottom half.
- Split View is a 50/50 split; PiP pinning also exists → resizable layouts matter.
- Don't build a layout per pose. Two size classes: compact width (outer), regular width (inner). Avoid fixed widths, breakpoints, screen-specific metrics. Use layout margins and horizontal safe-area insets. A bespoke seated/hands-free layout is allowed only if it keeps the same controls and hierarchy.
- Controls move to the side and share vertical space with Live Activities and the status bar; overflow into a menu when short. Controls too wide for the side (text buttons, segmented controls) stay in the nav bar.
- Outer: most content needs an offset so it is not under controls; safe-area insets provide it. Immersive non-scrolling layouts may center on the full display; mixes are fine (full-width header, inset scrollable content).
- Inner: use the width — split views, two-column layouts reflowing from one column, tab bar as sidebar for dense apps.
- Sheets: outer display can use side controls, or disable the vertical bar for simple sheets (then the sheet stops short of the front camera). Inner: standard horizontal bars. Partially folded: sheets slide off the fold.
- Fold avoidance is built into system components (nudges interactive elements from the center when partially folded). Use system components; keep interactive elements away from the hinge except inside scrollable content.
- One experience that adapts; support resizability.
