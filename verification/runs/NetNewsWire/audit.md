# NetNewsWire — iPhone Duo audit (unmodified, iOS 27.1 SDK)

Build: `NetNewsWire-iOS`, Debug, iOS 27.1 SDK (Xcode 27.1), `CODE_SIGNING_ALLOWED=NO`. Flows: `.duo/flows/NetNewsWire.flow`.
Shots and accessibility snapshots: `.duo/captures/NetNewsWire/before/` (kept out of git). Detectors:
`.duo/captures/NetNewsWire/before/detectors.md` (35 captures, 3 findings). Every shot was also looked at; findings the
detectors cannot see (an empty web view is "scrolling content" to them, a pane edge is not a container) are marked *(eye)*.

## App structure (from source)
- `RootSplitViewController` (UIKit `UISplitViewController`, triple column, `preferredSplitBehavior = .tile`):
  primary **Feeds** (`MainFeedCollectionViewController`), supplementary **Timeline** (`MainTimelineViewController`),
  secondary **Article** (`ArticleViewController`, a `WKWebView`). Compact width collapses it to one navigation stack.
- Display mode: `AppDefaults.splitViewPreferredDisplayMode`, `.oneBesideSecondary` by default on a phone (timeline beside article, feeds behind the sidebar button).
- Column widths: `SceneCoordinator.init` sets min/max/preferred widths for the primary (300–500, saved) and the
  supplementary (280–440, preferred 320 or the saved width).
- Sheets: Settings (`UINavigationController`, `.formSheet`), Add Feed (`UIHostingController(AddFeedView)`, `.formSheet`),
  plus Add Folder, Feed/Account inspectors, Current Activity, all presented from `SceneCoordinator`.

## Static scans (`references/detectors-static.md`)
| Class | Hit | Verdict |
|---|---|---|
| T14 | `SceneCoordinator.swift:351-363` `minimum/maximum/preferredPrimaryColumnWidth`; also `:353-361` `…SupplementaryColumnWidth` (not in the skill's regex, found by hand) | confirmed in book: the split boundary sits at 320 pt, the detail 321–951 straddles the fold |
| T10 | skill regex: none. By hand: `AddFeedView.swift:61-73` `Button(NSLocalizedString("Cancel"…))`, `Button(NSLocalizedString("Add"…))`, text-only, multi-line `ToolbarItem`s; `ShareExtension/ShareViewController.swift:58` `UIBarButtonItem(title: "Add Feed")` (share extension, not an app screen) | confirmed on the cover: Add Feed's Cancel/Add stay a horizontal bar while Settings' Done goes into the vertical column |
| T9, T3 | none | — |
| T13 | `UIApplicationSceneManifest` present in `iOS/Resources/Info.plist` | no finding (the skill's `rg -L` line prints matches, it does not list files without one) |

## Findings, screen × pose
`·` = unchanged (looked at, nothing wrong).

| Screen | closed | closed-sideways | book | laptop | tent | flat-sideways | flat-upright |
|---|---|---|---|---|---|---|---|
| feeds | · | · | T14 *(eye)*, T7 *(eye)* | T1 *(eye)*, T7 *(eye)* | T1 *(eye)*, T7 *(eye)* | T7 *(eye)* | T7 *(eye)* |
| timeline | · | · | T14 *(eye)* | T1 *(eye)*, T7 *(eye)* | T1 *(eye)*, T7 *(eye)* | · | T7 *(eye)* |
| article | · | · | T14 | · | · | · | · |
| settings | · | · | T15 | · | · | · | · |
| add-feed | T10 *(eye)* | T10 *(eye)* | T15 | · | · | · | · |

Details:
- **T14 (book, feeds/timeline/article)**: timeline column 0–320 pt, detail 321–951 pt; the detail pane and the article
  text (detector: column 340–827) straddle the active division 455.5–495.5. Cause: the fixed column widths.
- **T15 (book, settings/add-feed)**: the form sheet sits at 8–467.5 pt, on the leading half, over the list.
- **T1 (laptop, tent; feeds/timeline)**: the detail's "No selection" placeholder is centred (`stylesheet.css`
  `.systemMessage { top: 45% }`) and lands on the horizontal fold (y ≈ 470 pt). The detector exempts it (inside a web
  view); the pattern page names exactly this case.
- **T7 (feeds, inner poses; timeline, upright poses)**: the screen the person was on does not survive the unfold. Feeds
  list on the cover → an empty timeline column and "No selection" (book, flat-sideways) or "No selection" alone
  (laptop, tent, flat-upright); the feeds list is behind the sidebar button. Timeline on the cover → upright inner
  poses show only the empty detail; the list is behind the button. In laptop the split shows the detail alone at 669 pt
  although `.tile` is set: with a 280–440 pt supplementary minimum the system does not tile there.
- **T10 (closed, closed-sideways; add-feed)**: text-only toolbar items stay in a horizontal bar on the cover.
- Not findings: settings and add-feed in laptop/tent (the settings sheet spans the fold but its list scrolls, exempt
  [tt-111466 9:28]; the add-feed sheet ends above the fold with the keyboard below); every centred sheet when flat;
  the article scrolling across the horizontal fold in laptop/tent/flat-upright (scrolling content may cross).

## Classification (step 3)
| Screen | Relationship | Mode | Why | Pattern (decision table) |
|---|---|---|---|---|
| feeds | hierarchical | viewing | a list whose rows open a timeline; the table names "feeds-with-detail" as hierarchical | P1 Fold-aligned split |
| timeline | hierarchical | viewing | a list whose rows open an article | P1 Fold-aligned split |
| article | hierarchical (detail) | viewing | the article is continuous content, but in this app it is the detail pane of the feeds-with-detail split; with P1 it gets one half in book and never crosses the vertical fold. P2's reference lays plain paragraphs with TextKit and cannot take a `WKWebView` of HTML | P1 Fold-aligned split (detail pane) |
| settings | hierarchical | editing | a settings list with toggles, presented as a sheet over the split | P1 Fold-aligned split, sheet rule |
| add-feed | hierarchical | editing | a two-field form presented as a sheet over the split | P1 Fold-aligned split, sheet rule |

Decision-table cells used: `hierarchical / viewing` every pose (all cited); `hierarchical / editing` every pose except
tent, which is `UNJUSTIFIED`. Settings and add-feed have no finding in tent, so nothing there needs a cell.
