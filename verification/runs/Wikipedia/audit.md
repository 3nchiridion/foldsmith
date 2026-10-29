# Wikipedia on iPhone Duo — audit

Unmodified app (wikipedia-ios 2031b89), built against the iOS 27.1 SDK (Xcode 27.1), Debug, ad-hoc signed, on the
iPhone Duo simulator `<Duo simulator UDID>`. Logged out. Flow: `.duo/flows/Wikipedia.flow` (11
screens). Captured with `tools/capture-app.sh` into `.duo/captures/Wikipedia/before/` (not in git): 77 cells, each with
its accessibility snapshot; `tabs` and `contents` were captured again after the first pass (see Notes).

## Static scans (step 1)
| Class | Result |
|---|---|
| T13 no-scene-lifecycle | not hit: `UIApplicationSceneManifest` in `Wikipedia/Wikipedia-Info.plist` (and the Alpha, Local, Experimental plists), `SceneDelegate.swift` |
| T9 inactive-division-ignored | no `reservedRegions` anywhere (the app reads no fold yet) |
| T14 columns-off-fold | no `navigationSplitViewColumnWidth` / `…ColumnWidth` (no split view in the app) |
| T10 stranded-horizontal-item | no SwiftUI `ToolbarItem` hit; 16 `UIBarButtonItem(title:)` (editors, Help, Page History, reading list sort): none on a captured screen. Not in the scan: the article toolbar's `IconBarButtonItem`s are custom-view items (`Wikipedia/Code/IconBarButtonItem.swift`), which Apple says never go vertical [tt-111462 5:56] — confirmed in the captures below |
| T3 custom-bar-not-vertical | 7 hand-made `UIToolbar`/`UINavigationBar` (Help, references, random article, talk page, keyboard accessory, image recommendations): none on a captured screen |

## Findings, screen × pose
Detector output (`before/detectors.md`) plus what the shots show. `·` = no finding. "eye" = seen in the shot or the
snapshot, not reported by a detector; "not counted" = a detector hit that the shot shows is not a defect, with why.

| Screen | closed | closed-sideways | book | laptop | tent | flat-sideways | flat-upright |
|---|---|---|---|---|---|---|---|
| community | · | · | T14 | · | · | · | · |
| for-you | · | T4 (eye) | T5 | · | · | T5 | · |
| search | · | · | T1 · T5 | · | · | T5 | · |
| article | T10 (eye) | T10 (eye) | T1 · T5 · T7 (eye) | · | · | T5 · T7 (eye) | · |
| contents | · | · | T1 · T14 · T7 | · (T7 not counted) | · (T7 not counted) | T7 | · (T7 not counted) |
| places | · | · | T1 (T14 not counted) | · (T1 not counted) | · (T1 not counted) | · | · |
| saved | · | · | T1 · T5 | · | · | T5 | · |
| activity | · | · | T5 | · | · | T5 | · |
| tabs | · | · | T14 | · | · | · | · |
| profile | · | · | T15 | · | · | · | · |
| settings | · | · | · | · | · | · | · |

What each one is:
- **community** book: Explore's two card columns are centred on the window (`ColumnarCollectionViewLayoutMetrics.exploreViewMetrics`), so the trailing column starts at 458 pt, inside the fold (T14). Flat sideways has the same geometry against the inactive division: not a finding by the taxonomy, but the pattern below changes it too.
- **for-you** (logged out, no reading history: the feed shows its "Your feed is empty for now" end card): book and flat sideways, the card's text column runs 20–585 pt across the division (T5). Closed sideways (eye): the card's title and subtitle shrink to an unreadable size and sit under the leading vertical bar (T4); they are not in the accessibility tree, so no detector sees them.
- **search** (the tab's root, the History list of recently read articles): book, the search field spans 20–867 pt across the fold (T1); the list is one 951 pt text column (T5, book and flat sideways).
- **article** (Moon): book and flat sideways, one 827 pt text column (T5); book, the centred "W" home button (424–463 pt) is on the fold (T1). Eye: the bottom toolbar's six buttons (contents, languages, save, find in page, theme, more) are `IconBarButtonItem`s with custom views; on the cover they stay a horizontal bar over the text while the navigation bar goes vertical (T10, closed and closed-sideways), and wherever the system draws a vertical bar on the inner display (book, flat sideways) they are not drawn at all — empty glass capsules, and not in the accessibility tree — so the article loses its toolbar there (T7: functionality not kept across poses).
- **contents** (the article's table of contents): on the cover an overlay with a Close button; on the inner display the app's inline sidebar (0–318 pt) beside the article. Book: the article pane 318–867 straddles the fold (T14) and the "W" is on it (T1). Book and flat sideways: the toolbar is gone (as for article), so nothing on screen hides the contents again (T7; the detector also reports the missing Close). Laptop, tent, flat upright: the detector reports T7 because the cover's Close button is not on the inner display; there the contents stay open beside the article and the toolbar's contents button hides them, so nothing is lost: not counted.
- **places**: book, the "Search Places" field spans 20–867 pt across the fold (T1). Not counted: book T14 "column 100–542" (hidden list text, nothing on screen there: the list panel is 15–340 pt, the callout 540–778 pt); laptop and tent T1 on 17 pt "controls" and cluster counts, which are map annotations that pan with the map (scrolling content, which Apple exempts [tt-111466 9:28]). The capture's "the shut phone lost the screen after …" lines for places are not T7: the reference snapshot was taken before the map loaded its pins, and `same-screen.py` counts each pin (see the report's Skill problems); every shot shows Places.
- **saved** (All articles, two saved): book, the search field (20–867 pt) and the All articles / Reading lists picker (16–851 pt) cross the fold (T1); one 692 pt text column (T5, book and flat sideways).
- **activity** (logged out: the "See more reading and editing insights / Log in" card): one 506 pt text column across the division (T5, book and flat sideways).
- **tabs** (four tabs open): four equal columns across the window; in book the third (437.7–644.3 pt) straddles the fold (T14). Flat sideways is the same geometry against the inactive division (not a finding).
- **profile** (the Account sheet): book, the system places the page sheet on the leading half, 8–467.5 pt (T15).
- **settings**: full-screen list; rows scroll across the fold, the Done button is in the vertical bar. Clean.

## Classification (step 3)
From the model and the screen's purpose, not its current layout. I1/I2 per `references/decision-table.md`.

| Screen | Relationship | Mode | Why | Pattern (step 4) |
|---|---|---|---|---|
| community | peer | viewing | Explore's cards are of many kinds (featured article, picture of the day, in the news, on this day, top read, games) browsed side by side; I1 names "an Explore grid" as peer, and `even-grid.md` uses this very feed (trailing column at 458.7 pt) as its corpus "before". A tap on some cards opens an article, which I1's first clause would call hierarchical: the pages disagree (Skill problems); the more specific text, naming this feed, wins | P3 Even grid |
| for-you | hierarchical | viewing | a card opens its article (I1: "an article into its text") | P1 Fold-aligned split |
| search | hierarchical | viewing | the tab's root is History, recently read articles, each opening its article | P1 Fold-aligned split |
| article | continuous | viewing | one article read in order | P2 Reflowing columns |
| contents | supporting | viewing | the table of contents is only meaningful next to its article (I1: like a transcript or an inspector) | P4 Arrangement: no page yet |
| places | continuous | viewing | the map is the screen (I1 lists a map as continuous); the floating list of places supports it | P2's page is for text read in order (its Context); no page fits a map |
| saved | hierarchical | viewing | saved articles, each opening its article | P1 Fold-aligned split |
| activity | hierarchical | viewing | logged in, a timeline of the articles read and edited, each opening its page, under summary modules; logged out, one card | P1 Fold-aligned split |
| tabs | peer | viewing | open tabs as cards side by side, a switcher (I1: "photo cards") | P3 Even grid |
| profile | hierarchical | viewing | a short list of destinations (log in, donate, settings) shown as a sheet | P1 Fold-aligned split (its sheet rule) |
| settings | hierarchical | viewing | the settings list and its pages | P1 Fold-aligned split; no finding, stays as it is |

## Notes
- Launch arguments are the app's own UI-test switches (`WikipediaUITests/Config/UITestLaunchArgument.swift`); they
  work in Debug except the reading list seed and the network fixtures, which need the `UITEST` flag. So Moon and Mount
  Everest were saved, and three tabs opened, through the app with the tap runner before the capture.
- `contents` was first captured on the article: the Table of Contents button is disabled until the page loads and the
  tap landed early. The flow now waits 5 s; recaptured.
- Logged out by the brief's rules: Activity's insights, the Account's log-in flow, the watchlist and the editors were
  not reached.
