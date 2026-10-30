# Phase 2 clustering — 2026-10-26

Input: [`raw/corpus/defects.csv`](https://github.com/3nchiridion/foldsmith-evidence/blob/main/raw/corpus/defects.csv) at the end of Mac step 4 (49 rows, eight apps), [`raw/metrics.json`](https://github.com/3nchiridion/foldsmith-evidence/blob/main/raw/metrics.json), [`raw/apple-apps/`](https://github.com/3nchiridion/foldsmith-evidence/tree/main/raw/apple-apps/),
[`raw/apple-docs/`](https://github.com/3nchiridion/foldsmith-evidence/tree/main/raw/apple-docs/), and Apple engineers' Group Lab answers (`raw/complaints/README.md §A`, now read in full).
Output: the settled `patterns/TAXONOMY.md`, the reclassified `defects.csv` (29 rows), and the filled
`patterns/DECISION-TABLE.md`. Citation rule as amended on 2026-10-26 (EVAL.md §5).

## 1. Two corrections before clustering

**The fold band.** The division frame in [`raw/metrics.json`](https://github.com/3nchiridion/foldsmith-evidence/blob/main/raw/metrics.json) starts at 455.5 pt and is 40 pt wide: 455.5–495.5 pt,
centred on the display's middle (475.5 pt), 20 pt margin each side. [`raw/METRICS-NOTES.md`](https://github.com/3nchiridion/foldsmith-evidence/blob/main/raw/METRICS-NOTES.md) said "centred at 455.5", and
Home Assistant, Wikipedia, Signal and Firefox were measured against 435.5–475.5. Every fold finding was re-measured
against the frame. All book findings hold. Four laptop/tent rows fail (the element ends above 455.5 pt), and one new row
appears: NetNewsWire's No selection label sits in the laptop band, which the pilot never measured.

**Scrolling content.** Apple keeps interactive elements away from the hinge *except inside scrollable content*
[tt-111466 9:28], and continuously scrolling content (articles, feeds, documents, lists) must not be displaced
[tt-111463 2:26]. Apple's Safari scrolls content straight across the horizontal fold [apple-apps/safari/laptop-inner.png].
So text inside a scrolling list or article that crosses the laptop fold is the prescribed behaviour, not a defect.
Sixteen laptop/tent rows were that case. T1 now covers only elements that do not scroll: fixed controls, fixed text,
focal images. In book, a single scrolling column across the fold is still a finding, but as `T5`: Apple's answer there is
to use the width (two columns, split views) [tt-111466 7:34], not to displace the column.

### Rows dropped (22)
| app | screen | pose | was | why dropped |
|---|---|---|---|---|
| HomeAssistant | launch | laptop | T1 | scrolling content in the horizontal fold (exempt) |
| HomeAssistant | launch | tent | T1 | scrolling content in the horizontal fold (exempt) |
| HomeAssistant | servers | laptop | T1 | scrolling content in the horizontal fold (exempt) |
| HomeAssistant | servers | tent | T1 | scrolling content in the horizontal fold (exempt) |
| HomeAssistant | manual-url | laptop | T1 | clear of the corrected band |
| HomeAssistant | manual-url | tent | T1 | clear of the corrected band |
| Wikipedia | explore | laptop | T1 | scrolling content in the horizontal fold (exempt) |
| Wikipedia | explore | tent | T1 | scrolling content in the horizontal fold (exempt) |
| Wikipedia | settings | laptop | T1 | scrolling content in the horizontal fold (exempt) |
| Wikipedia | settings | tent | T1 | scrolling content in the horizontal fold (exempt) |
| Wikipedia | article | laptop | T1 | scrolling content in the horizontal fold (exempt) |
| Wikipedia | article | tent | T1 | scrolling content in the horizontal fold (exempt) |
| Wikipedia | places | laptop | T1 | scrolling content in the horizontal fold (exempt) |
| Wikipedia | places | tent | T1 | scrolling content in the horizontal fold (exempt) |
| Signal | phone | laptop | T1 | clear of the corrected band |
| Signal | phone | tent | T1 | clear of the corrected band |
| Signal | restore | laptop | T1 | duplicate of the splash finding behind the sheet |
| Signal | restore | tent | T1 | duplicate of the splash finding behind the sheet |
| Firefox | launch | laptop | T1 | scrolling content in the horizontal fold (exempt) |
| Firefox | launch | tent | T1 | scrolling content in the horizontal fold (exempt) |
| Firefox | settings | laptop | T1 | scrolling content in the horizontal fold (exempt) |
| Firefox | settings | tent | T1 | scrolling content in the horizontal fold (exempt) |

## 2. Class decisions

Admission rule (unchanged): a class enters the taxonomy with evidence in ≥ 2 corpus apps or as a hazard Apple names.

| was | now | decision | why |
|---|---|---|---|
| T1 control-in-crease | **T1 crease-straddle** | admitted | 5 apps, 14 rows; Apple names it [tt-111466 9:28; tt-111463 1:29]. Renamed: text lines and focal images straddle as often as controls |
| T3 custom-bar-not-vertical | **T3** | admitted | Firefox; Apple names it [tt-111462 2:00, 10:07] |
| T5 stretched-single-column | **T5** | admitted | Wikipedia (article, Settings); Apple names the alternative [tt-111466 7:34; hig best practices 2] |
| NEW-1 | **T13 no-scene-lifecycle** | admitted | 2048, Kickstarter; Apple: Xcode 27 builds require scene lifecycle [doc app-resizability task 3, `raw/sdk/APPLE-SKILL.md`]. Owned by Apple's skill: the catalog detects and routes, does not fix |
| NEW-2 + Wikipedia's Explore grid | **T14 columns-off-fold** | admitted | NetNewsWire (split at 323 pt), Wikipedia (grid column at 458.7 pt); Apple: split views match the fold's symmetry, grids keep each container in its region [hig reserved-regions; tt-111463 5:12] |
| NEW-3 | **T15 sheet-in-book** | admitted | 4 apps, 6 sheets, all from the system's automatic placement; Apple: sheets slide off the fold [tt-111466 8:36], alerts go trailing in book [tt-111463 4:00] |
| NEW-4 | NEW-4 | provisional | one app; Apple documents both compression modes as valid [hig vertical-controls], the defect is inconsistency between screens |
| T6 | T6 | out of scope | the one row is not Duo-specific |

## 3. Counts after reclassification (29 rows)
| class | closed | closed-sideways | book | laptop | tent | flat-sideways | flat-upright | all | rows | apps |
|---|---|---|---|---|---|---|---|---|---|---|
| T1 |  |  | 10 | 2 | 2 |  |  |  | 14 | Firefox, HomeAssistant, NetNewsWire, Signal, Wikipedia |
| T3 | 1 |  |  |  |  |  |  |  | 1 | Firefox |
| T5 |  |  | 2 |  |  |  |  |  | 2 | Wikipedia |
| T13 |  |  |  |  |  |  |  | 2 | 2 | 2048, Kickstarter |
| T14 |  |  | 2 |  |  |  |  |  | 2 | NetNewsWire, Wikipedia |
| T15 |  |  | 6 |  |  |  |  |  | 6 | Firefox, HomeAssistant, IceCubesApp, Signal |
| NEW-4 |  | 1 |  |  |  |  |  |  | 1 | Wikipedia |
| T6 |  | 1 |  |  |  |  |  |  | 1 | Wikipedia |

What the pose columns say: every surviving `T1` in laptop/tent is a fixed focal image or fixed label; book carries most
findings; the cover carries the bar findings (`T3` upright, `NEW-4` turned); the flat poses carry none, because the
division is inactive.

## 4. Not observed, and what that means

- `T7` state loss: none. Every flow folded from shut into its pose with its state intact (Home Assistant, Wikipedia,
  Signal: 35 captures each; Firefox: 42). Matches Apple's answers that the system preserves state across the hinge.
- `T2` occlusion, `T4` under-system-bar, `T10` stranded text item, `T12` letterboxing: none in the captures; all builds
  used the 27.1 SDK, and the inner camera was never active.
- `T8` re-layout animation, `T11` Split View squeeze: not measurable with stills or headless.

## 5. Recommendation for v0's three patterns (EVAL.md §6)
**Fold-aligned split**, **Even grid** and **Reflowing columns.** They carry the admitted classes with the most evidence:
`T14` (columns off the fold: NetNewsWire, Wikipedia), `T5` (one stretched column: Wikipedia) and `T1` in book (fixed
elements on the fold: five apps). They also cover the A/B set: NetNewsWire is hierarchical (Fold-aligned split);
IceCubesApp's timeline and Home Assistant's dashboard are peer content, viewed and controlled (Even grid).
**Arrangement** and **Whole object** are named and cited in the decision table but wait for v0.1. `T15` (sheets in
book) and `T3` (custom bars) are rules every pattern carries, not patterns of their own. *(2026-10-29, Phase 4 step
12: the owner moved **Arrangement** into v0 as the third pattern to pass G1–G4, because no Apple frame looked at shows a
text in columns, so Reflowing columns' G4 has no oracle; Reflowing columns stays in the catalog. See `docs/history/DEVIATIONS.md`.)*
