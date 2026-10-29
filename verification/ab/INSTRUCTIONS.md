# Rater instructions

> Set aside 2026-10-27 (EVAL.md §4): kept for a later study; nobody is being recruited.

**Frozen when the recruitment request is posted** (EVAL.md §4.4). Any later change is a deviation, logged in
`docs/history/DEVIATIONS.md` with the reason.

Thank you for rating. You will look at screenshots of three open-source iOS apps running on the iPhone Duo simulator
(Apple's foldable iPhone, iOS 27.1) and score how well each screen uses the device. Nothing else about the screenshots
is explained, on purpose: please do not try to find out how they were made, and do not discuss them with other
raters until the results are published.

## What you get
- `items/<id>/` — one folder per item. An item is one screen of one app, captured in seven poses: the same app state,
  folded into each pose in turn. Files are named by pose (`closed.png`, `book.png`, …). `matrix.png` shows all seven
  side by side.
- `sheet.csv` — one row per item and pose, with columns `R1` … `R7` to fill with 0, 1 or 2, and a `note` column
  (optional, free text).
- The app's name is given for each item. Items are in random order; the same screen of the same app may appear more
  than once, looking different. Rate each item on its own.

## The device, in one paragraph
Closed, the iPhone Duo is a phone with one outer display (466 × 678 pt). Open, it has an inner display of 951 × 669 pt
with a fold down the middle at x = 455.5–495.5 pt (that band includes the fold's own margins). On both displays the
system draws a vertical bar on one side, where toolbars and tab bars go, beside the camera. Apple's guidance: keep
controls, text lines and focal images off a fold that is partly folded; let scrolling content cross it; in laptop pose
put what you view on the upper half and what you touch on the lower half; in book pose put sheets and alerts on the
trailing (right-hand) half.

| Pose | What it is | Fold |
|---|---|---|
| closed | shut, outer display upright | none |
| closed-sideways | shut, outer display turned on its side | none |
| book | open partway, held like a book | vertical, **active** |
| laptop | open partway, lower half flat like a laptop | horizontal, **active** |
| tent | laptop's fold, standing on its edges | horizontal, **active** |
| flat-sideways | fully open, held sideways | vertical, inactive (a flat screen) |
| flat-upright | fully open, held upright | horizontal, inactive (a flat screen) |

An *active* fold is a real crease you would look across. An *inactive* fold is flat glass: nothing has to avoid it, but
an even split there still reads well.

## The rubric (0 / 1 / 2 for each, per pose)
Score what you see in that pose's screenshot, using the other poses of the same item only for R4 and R7.

| | Criterion | 2 | 1 | 0 |
|---|---|---|---|---|
| R1 | Reachability: primary actions within reach for that pose; nothing interactive in the fold band | primary actions where the hand is (laptop: lower half; book: either half, not the fold); no control on an active fold | one minor control awkwardly placed or touching the fold band | a primary action out of reach, or a control on an active fold |
| R2 | Crease: no text line, control or focal image straddles an active fold | nothing crosses an active fold (scrolling content may) | one secondary item crosses it | a primary control, a text column's lines or the main image cross it |
| R3 | Occlusion: nothing meaningful under the camera; no clipped bar items | clear | something minor near or under the camera, or one clipped item | meaningful content or a control under the camera, or several clipped items |
| R4 | Continuity: across poses, the same content and selection stay visible; no reordering of controls | same content and selection in every pose | content shifts or a selection is hidden in one pose | content or state lost, or controls reordered between poses |
| R5 | Bars: bars on the system's bar side in the standard order; nothing stranded horizontal that should be vertical; nothing duplicated | system bar placement in this pose | one item stranded or duplicated | a whole bar in the wrong place, or bars duplicated |
| R6 | Use of space: the inner display gains an information level or breathing room; no empty strips; no single column stretched across the display | the larger display is used well for this content | usable but plain, or one empty strip | a stretched single column, large empty areas, or content squeezed |
| R7 | Consistency: controls recognizably in the same places across poses | consistent | one control moves unexpectedly | controls are hard to find from one pose to the next |

On the outer display (closed, closed-sideways) there is no fold: R2 is 2 unless something is cut off by the screen
edge, and R6 judges a phone-sized layout.

Ignore: the status bar, the keyboard's own layout, the content of web pages or posts, network errors, colours and
branding. Judge layout only.

## Practicalities
- About 60–90 minutes for the whole sheet. You can stop and come back.
- Return `sheet.csv` (and nothing else) as instructed in the message that brought you here.
- Your scores are published with the results as `rater-1` … `rater-n`. Your name appears only if you ask for it.
