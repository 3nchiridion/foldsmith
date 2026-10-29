# Wikipedia on iPhone Duo — migration report

Branch `duo-migration` (from `main`, wikipedia-ios 2031b89), iOS 27.1 SDK (Xcode 27.1), Debug, ad-hoc signed, on the
iPhone Duo simulator `<Duo simulator UDID>`. Logged out. Eleven screens (`.duo/flows/Wikipedia.flow`)
× seven poses, captured with `tools/capture-app.sh` (a shot and an accessibility snapshot per cell, then `duo-detect`):
before into `.duo/captures/Wikipedia/before/` (19:14–19:53 UTC, two screens again after), after into `…/after/`
(20:31–21:09 UTC; after the first review saved, search, activity, article and contents again, 22:06–22:24; after the
second review saved, search, activity, article, contents, community and settings again, 23:30–23:52, and article and
contents once more, 00:00–00:12; after the third review saved, search, activity, article, contents and settings again,
00:57–01:19, and article and contents once more, 01:24–01:32; after the fourth review article and contents again,
02:24–02:32, replacing a run at 02:12 whose flow passed a boolean as a string, see Skill problems). Evidence captures
that are not migration screens (`.duo/flows/Wikipedia-probes.flow`):
`…/probes/` (the system overflow menu opened on the cover; an article opened from Home in every pose). Shots are not in
git. Findings, classification and reasons: `.duo/audit.md`. Four reviews found defects the run had passed; see "Found in
review". The detector tables below come from the synced tools, rerun over the full before and after in the fourth
review.

## Result
| Screen | Pattern | Before (synced detectors + eye) | After | Status |
|---|---|---|---|---|
| community (Home › Community, Explore) | Even grid | T14 book | clean; columns 418 → 366 pt (see Costs) | done: verified in book and flat-sideways, unchanged elsewhere |
| for-you (Home › For You, empty) | Fold-aligned split, not applied | T5 book, flat-sideways; T1 book (illustration, eye); T4 closed-sideways (eye) | same | `todo` |
| search (Search tab, History) | Fold-aligned split | T1 · T5 book; T5 flat-sideways | T14 book, flat-sideways: the nav-bar search field stops at 371 of 455 pt; by eye the top-bar capsule ends 18 pt short of its margin | `todo` (both); everything else verified |
| article (Moon, from Search) | Reflowing columns (classified); bars + Search's split | T10 closed, closed-sideways; T1 · T5 · T7 book; T5 · T7 flat-sideways | T14 book, flat-sideways: the list pane's search field beside it (316 of 455 pt); by eye the detail pane's top bar stops 38–42 pt short of its edge | `todo` (both; and articles from Home or Places, T5); closed and closed-sideways verified; laptop, tent, flat-upright verified (the toolbar's plain items, a change: see Existing behaviour) |
| contents (from Saved, Activity, Search) | Arrangement: no page; the contents take the list pane beside the article | T1 · T10 · T14 · T7 book; T10 · T7 flat-sideways; T7 laptop, tent, flat-upright | T7 in the inner poses: the cover's Close button, a presentation change (not counted); book, flat-sideways: by eye the detail pane's top bar stops 38–42 pt short of its edge (T14) | `todo` (that bar, book and flat-sideways; contents from Home or Places with the article); laptop, tent, flat-upright verified (toolbar; contents inline as before) |
| places (map) | none fits a map | T1 book (the search field across the fold); the detector's T14 is hidden list text, a false hit | same | `todo` |
| saved (All articles) | Fold-aligned split | T1 · T5 book; T5 flat-sideways | T14 book, flat-sideways: the nav-bar search field; by eye the top-bar capsule ends 18 pt short of its margin | `todo` (both); everything else verified |
| activity (logged out) | Fold-aligned split | T5 book, flat-sideways | detectors clean; by eye the list pane's top-bar capsule ends about 18 pt short of its margin, as Saved's (T14) | `todo` (that capsule); everything else verified |
| tabs (four article tabs) | Even grid | T14 book | clean; cards 207×276 → 177×236 pt (see Costs) | done |
| profile (Account sheet) | Fold-aligned split (sheet rule) | T15 book; T5 flat-sideways (eye, third review) | book clean; flat-sideways T5 unchanged (centred sheet) | `todo` (flat-sideways) |
| settings | Fold-aligned split, reverted | T5 book, flat-sideways | T5, as before (the split was reverted in the third review) | `todo` |

Two screens done (community, tabs). Activity and contents were called done until the fourth review: their top bars stop
short of their pane's edge as Saved's and the article's do, so they are in `todo` with them (E16). None of the others
is worse than before.

## Detectors before and after
Synced tools (third review: a row's title and value count as one column, a pane check for T14, maps count as scrolling
content), rerun over the full before and after in the fourth review. Cells with a finding: **23 before → 16 after**;
lines 44 → 17. Of the 16 after-cells, 5 are contents' T7 (not counted: the cover's overlay has a Close button, the
contents beside the article do not need one), 6 are the list pane's navigation-bar search field (T14, `todo`), 2 are For
You (T5), 1 is Places (T1 of its search field; its T14 line is hidden list text, a false hit) and 2 are Settings (T5,
its split reverted). Not in the tables, from the shots and reviews: For You's illustration on the fold (T1, book) and its
card under the bar (T4, closed-sideways); profile's centred sheet flat sideways (T5); the detail pane's top bar stopping
38–42 pt short of its edge (article, contents); the list pane's top-bar capsule 18 pt short of its margin (saved,
search, activity).

Before (`before/detectors.md`):

| config | closed | closed-sideways | book | laptop | tent | flat-sideways | flat-upright |
|---|---|---|---|---|---|---|---|
| activity | · | · | T5 | · | · | T5 | · |
| article | T10 | T10 | T1 T5 T7 | · | · | T5 T7 | · |
| community | · | · | T14 | · | · | · | · |
| contents | · | · | T1 T10 T14 T7 | T7 | T7 | T10 T7 | T7 |
| for-you | · | · | T5 | · | · | T5 | · |
| places | · | · | T1 T14 | · | · | · | · |
| profile | · | · | T15 | · | · | · | · |
| saved | · | · | T1 T5 | · | · | T5 | · |
| search | · | · | T1 T5 | · | · | T5 | · |
| settings | · | · | T5 | · | · | T5 | · |
| tabs | · | · | T14 | · | · | · | · |

After (`after/detectors.md`):

| config | closed | closed-sideways | book | laptop | tent | flat-sideways | flat-upright |
|---|---|---|---|---|---|---|---|
| activity | · | · | · | · | · | · | · |
| article | · | · | T14 | · | · | T14 | · |
| community | · | · | · | · | · | · | · |
| contents | · | · | T7 | T7 | T7 | T7 | T7 |
| for-you | · | · | T5 | · | · | T5 | · |
| places | · | · | T1 T14 | · | · | · | · |
| profile | · | · | · | · | · | · | · |
| saved | · | · | T14 | · | · | T14 | · |
| search | · | · | T14 | · | · | T14 | · |
| settings | · | · | T5 | · | · | T5 | · |
| tabs | · | · | · | · | · | · | · |

## What changed (one commit per change)
- `cd5c34e` **profile → Fold-aligned split** (the sheet rule). `WMFComponents/Utility/WMFFold.swift` reads the fold
  from `UIView.reservedRegions(kind: .division, options:)` behind `#available(iOS 27.1, *)`. While a vertical division
  is active every sheet presented from a `WMFComponentNavigationController` or the root gets
  `preferredPlacement = .trailing`, otherwise `.automatic`; sheets already up follow the fold. In book the Account sheet
  runs from 483.5 to 943 pt, under the vertical bar's band, with its own vertical bar holding Close (Apple: a trailing
  sheet gets a vertical bar); flat it is centred.
- `0c288f1` **community → Even grid**; `4ee89e9` (second review) card heights measured with the live cell's margins.
- `6e8b992` **article: toolbar and W off the fold** (also contents); `0ffa2ce` (second review) overflow, priorities,
  contents button, W; `00db16f` search item titled for the overflow.
- `5a84010` **tabs → Even grid.**
- `1067adb`, `b790031`, `26cf97a` **saved, activity, search → Fold-aligned split** (`WMFFoldSplitContainerViewController`,
  the Search state beside the article, pop-to-root on a second tap); `75d98fe` (first review) the bar's 84 pt inset
  cancelled in both panes, an empty-pane placeholder; `328cb92` (second review) search results, the tab bar beside an
  article, theme, Activity's copy.
- `9c259a0` (first review) contents as the overlay in the detail pane — replaced by `03e1d80` (second review): the
  contents in the list pane beside the article.
- `aa81129` (second review) **settings → Fold-aligned split**, reverted by `a04b528` (third review).
- Third review: `aa1085b` every walk of the hierarchy unwraps the container (state restoration, theme, tab bar on every
  selection change, back-to-root routes, the visible screen; the contents follow the detail pane's top screen and hide
  the covered list); `962e2f2` contents follow their article, margins, the W's label, the Search item's gate, the overflow
  disabled with the toolbar; `162a1c6` the lead image's margin kept in step.
- Fourth review: `4e0f095` what is opened from the detail pane stacks there (the router, link handling, push
  notifications, the visible article), root checks that count the detail pane, the imported reading list through the
  container, the tab bar with the transition, main-actor fixes; `3c385e8` Edit disabled (not missing) in the merged
  overflow, the open-contents fill and VoiceOver labels back, open contents carry over between articles, contents come
  back only on top; `3c66733` two more walks (the watchlist route, a second tap on the tab).
- `dae0c7d` audit; `4b8955f`, `344056a`, `cb9681d`, `de87a89` and the last commit: this report.

1284 lines added, 66 removed in 19 files (16 Swift sources, 3 localization tables); two new Swift files, both in the
WMFComponents package (no Xcode project edit). New strings: `fold-split-detail-empty`, `fold-split-activity-detail-empty`,
`fold-split-home-button-accessibility-label` (en and qqq written by the app's build); `fold-split-settings-detail-empty`
went with the Settings revert.

## Bars, per pose (from the after snapshots and the probes)
The article's bars, opened from Search (the flow) and from Home (`probes/article-home-*`):

| Pose | In the vertical bar | In the system overflow (one tap on More) |
|---|---|---|
| closed | Back, Tabs, Profile, More, Contents, Languages, Save, Find in page | Search, Reading themes, and the app's More actions (Edit, Revision history, Talk page, Watch, Share, the tab's previous/next article): `probes/overflow-closed-cover.png` |
| closed-sideways | Back, Tabs, Profile, More, Contents, Save | Search, Languages, Find in page, Reading themes, the app's More actions |
| book, flat-sideways, from Search (detail pane) | Contents, Languages, Save, Find in page, Reading themes; no tab bar (an open article hides it, as before) | the detail pane's top bar holds W, Search, Tabs, Profile and the system More with the app's More actions |
| book, from Home (no split) | Back, W, Tabs, Profile, More, Contents, Languages, Save, Find in page | Search, Reading themes, the app's More actions |
| flat-sideways, from Home (no split) | Back, Search, Tabs, Profile, More, Contents, Languages, Save, Find in page (the W is the centred title: the fold is not active) | Reading themes, the app's More actions |
| laptop, tent, flat-upright | none (horizontal bars, as before: the app's own More in the bottom toolbar) | — |

The overflow menu was opened only on the cover: a tap reaches only the shut phone, and the menu closes on a fold. In book
and flat sideways what the overflow holds is read from the snapshot (what is not in the bars) and `additionalOverflowItems`.

Saved and Activity in book and flat sideways: their More, Tabs and Profile moved from the vertical bar into the list
pane's top bar, because the vertical bar goes with the detail pane (Apple: in split views only the detail column
participates). Search's Clear, Tabs and Profile were already in its top bar before and stay there, in the list pane's.

Beside the list an open article is the root of the detail pane: there is no Back. The W is the way back to the list
(its label says so: "Wikipedia, return to Search"), as Back was; the tab bar is hidden while the article is open, as it
was full screen, so the count of taps to another tab is unchanged (W, then the tab, against Back, then the tab).

## Costs
- Community (Even grid): two columns of 366 pt instead of 418 pt in book and flat sideways, with a 125 pt gutter at the
  hinge (371–496 pt); the leading column now stops about 85 pt short of the fold, against 32.5 pt before. Cards get
  taller and their text wraps more.
- Tabs (Even grid): four columns of 177 pt instead of 207 pt, a 126 pt gutter (370–496 pt), the leading pair stopping
  about 85 pt short of the fold. Titles still fit; the description line under them now truncates ("Natural satellite
  orbiting E…"), and the extract loses two of its six lines.
- Article actions that now take two taps (the system overflow) where they took one: on the cover, Search and Reading
  themes; on the cover turned sideways, also Languages and Find in page; in book from Home, Search (its place in the
  vertical bar went to the W). Every action is still there (`probes/overflow-closed-cover.png`).

## Existing behaviour
- No reserved region means no change in layout: iPhone, iPad, the Duo's inner display held upright, and every system
  before iOS 27.1. Two exceptions: on any iOS 27.1 device the article toolbar's items change (next bullet), and on the
  Duo's outer display, which has the vertical bar, the article's toolbar goes into that bar and some actions move into
  the system overflow ("Bars, per pose"; "Costs" lists the actions that take two taps there). On iOS 27.1 Saved,
  Activity and Search sit in an invisible container even without a fold, so every walk of the view hierarchy was
  checked to unwrap it (third and fourth reviews):
  - unwrapped or routed through the container: `NavigationStateController` (save and restore of the open article;
    main-actor), the theme pass (`applyTheme(_:toNavigationControllers:)`, `applyTheme(toPresentedViewController:)`,
    `allNavigationControllers`, `updateUserInterfaceStyleOfNavigationControllersForCurrentTheme`), the tab bar
    (re-evaluated on every selection change and tap), `currentTabNavigationController`, `visibleViewController()`, the
    back-to-root routes (`.savedPages`, `.activity`, `switchToSearch`, the imported reading list, a second tap on the
    tab, which counts the detail pane), `debounceRemoveArticlesForDeletedTabParts`, `logDidSelectViewController`,
    `logTabBarSelectionsForActivityTab`, the Activity visit count;
  - the tab's front stack (the detail stack while it shows an article, else the list's; fourth review): the router's
    `currentNavigationController` (More › Talk page, the footer's talk link, user, talk and in-app web links, the
    editor's cancel), its watchlist target, `processLinkUserActivity`, Notifications Center from a push notification,
    and `visibleArticleViewController()` (a deep link to the open article, the return from the web editor, the Search
    quick action);
  - "at the root" counts the detail pane: the language-variant alerts and the evergreen account-creation prompt stand
    down while an article is open beside the list, as they do over an open article on main;
  - checked and unaffected: `AppViewControllerTipWrapper` (Home only; reads the tab's `tabBarItem`, which the container
    shares), `ViewControllerTransitionsController` and `DetailTransition` (they look for a detail source among the
    selected tab and fall through for a stack as for a container), `editingFlowViewControllerInHierarchy`,
    `topMostViewController` and `dismissPresentedViewControllers` (`presentedViewController` reaches the ancestors'
    presentations from the list stack), `isViewingEligibleMainTab` (the list's root), the orientation queries,
    `ViewControllerRouter`'s settings check, the Home and Places routes and Explore's Notifications Center (their tabs are
    their own stacks), the random-article shortcut and a modal reading list's article (articles pushed onto the list go
    to the detail pane), `ExploreViewController` and `TalkPageViewController` (their own presentations), and the
    coordinators handed a navigation controller (`SavedCoordinator`, `HomeCoordinator`, `ArticleCoordinator`,
    `LinkCoordinator` get the list stack, or the detail stack from inside the detail pane and from the router, which is
    what they push onto).
- Changes on any iOS 27.1 device, by design: the article toolbar's items are plain titled items (Save's long press shows
  a one-item menu, "Add to reading list"); they keep the VoiceOver labels the old buttons took from their image names
  (reading themes: "font size"), and with the contents open inline the hide item keeps its filled rounded square (drawn
  into its image). Where bars are vertical the app's More menu is part of the system overflow menu, and while the
  toolbar is disabled every one of its actions shows disabled, Edit included; visibility priorities decide what
  overflows; the Search item's title and priority come with them (27.1).
- For Saved, Activity and Search on any iOS 27.1 device, the tab bar over an open article is hidden and shown by the app
  (`setTabBarHidden`) from the navigation delegate, not by UIKit's `hidesBottomBarWhenPushed`, because the tab is the
  container, not the stack. It moves alongside the push or pop (through the transition coordinator, so with the finger
  in a back swipe) and is put back if the swipe is cancelled. Not verified with an interactive swipe (the tap runner has
  no swipe; captures show only the settled states, which match main). For Home and Places, which are their own stacks,
  the app only clears a hide it set itself and leaves the rest to UIKit, as on main.
- On the sideways inner display Saved, Activity and Search show a list pane beside a detail pane; an article opened from
  them opens in the detail pane and its contents take the list pane; the tab bar hides while an article is open there.
  Open contents carry over to the next article there, as the inline contents did on main (the same preference); the
  capture flow starts with them closed (`-TableOfContentsIsVisibleInline <false/>`), as the before capture had them.
- Not run: the app's tests, the Experimental and Alpha targets, any device but the Duo simulator. Paths that need a tap
  on the inner display (the W in the detail pane, the contents after an in-article link, a programmatic tab switch, the
  routes from the detail pane, the contents carried to the next article) or a swipe (the tab bar during a back swipe)
  were checked by code path, not by a capture.

## Left to do (`todo` in `.duo/migration.json`)
- **places**: no pattern yet (a map; Reflowing columns is for text read in order). The search field spans the fold in
  book (T1). The detector's T14 there (a column 100–480 pt) is hidden list text, nothing drawn: a false hit.
- **for-you**: Fold-aligned split not applied: the Home tab holds For You (hierarchical) and Community (peer, an Even
  grid) in one stack. Logged out the feed is empty: T5 in book and flat sideways, T1 in book (the illustration, x
  434–539, not in the accessibility tree), T4 in closed-sideways.
- **settings**: Fold-aligned split reverted in the third review (see Found in review). T5 in book and flat sideways,
  as before the migration.
- **saved, search, activity, article, contents**: T14 in book and flat sideways. The search field in the list pane's
  navigation bar stops at 371 of 455 pt (316 with Cancel, beside an article: saved, search, article; detector), the
  list's top-bar capsule ends about 18 pt short of its margin (saved, search, activity; eye), and the detail pane's top
  bar stops 38–42 pt short of its edge (article, contents; the W at 512, its last item ending at 825 of 867; eye). UIKit gives a navigation bar the vertical bar's trailing inset wherever its stack sits. Tried: the bar's layout
  margins, the search bar's margins, a vertical-bar opt-out for the list's stack, a negative `additionalSafeAreaInsets`
  on the stack, a `UINavigationBar` subclass reporting no trailing inset; none moves them. Everything else in both panes
  reaches its edges.
- **article and contents from Home or Places**: Reflowing columns not built (a `WKWebView`; contents jumps, find in page,
  scroll restoration and the native lead image use vertical offsets). From Home or Places the article is one 827 pt
  column in book and flat sideways (T5, `probes/article-home-book-inner.png`), and its contents open in the app's inline
  form beside that column, across the fold. There the W moves into the vertical bar while the book fold is active.
- **profile**: T5 flat sideways, the centred Account sheet's text column (186–760 pt) across the inactive division,
  unchanged from before (the pattern centres sheets while flat).
- Not captured: Split View's half window; logged-in screens; reading lists, the language picker, find in page, the
  theme popover.

## Found in review
### First round
The coordinator looked at the first after-capture and found two defects I had passed:
1. **contents, book and flat sideways — a regression, not "cramped".** In the 372 pt detail pane the inline contents
   column was about 90 pt wide and broke words ("etymol/ogy", "Classifi-/cation"), and the article beside it was clipped
   at the pane's edge (the two T4 links). Before the migration both were readable. Cause: the detail pane gave the
   article the window's regular size class, so the app chose its inline contents, and the stack inset the article by
   the bar's 84 pt on top. Fixed in `9c259a0` and `75d98fe`: the overlay, and the full pane for the article (web view
   496–867 pt, the contents 0–300 pt over the window). Closing and opening again keeps the contents open; upright the
   app's inline contents are unchanged.
2. **saved, search, activity — the list stopped 84 pt short of the fold.** The search field 20–371 pt, the segmented
   control 16–355 pt, cells and separators to 371 pt in a pane that ends at 455 pt. Fixed in `75d98fe` for everything
   but the navigation bar's search field (still 20–371 pt; see Left to do): segmented control 16–439 pt, rows and
   separators 0–455 pt, Activity's card text to 404 pt.
3. Not a defect, decided: the blank detail pane. The pattern puts an empty detail's placeholder at the top of the pane
   (`fold-aligned-split.md`, Consequences; the catalog's sits at y 202–222 pt); the pane now says "No article selected"
   there.

My own look at the first after-capture missed both: I read the contents as "cramped" from a 300 px contact sheet and
did not measure the list's controls against the pane. Before/after per pose for the five screens is in the tables
below (the first after-capture's shots were replaced in `after/`).

### Second round
Independent reviewers checked every screen and pose against the snapshots; all confirmed, all fixed or kept in `todo`
with what was tried:
1. **Search results beside the article ended at 371 pt** (content views [0,y,371,61], subtitles cut with an ellipsis):
   the results are the search controller's, presented over the search screen, not a screen of the stack, so the inset
   cancellation did not reach them. Now it covers what a stack's screens present inside the stack: results 0–455 pt,
   text to 435 pt (`328cb92`).
2. **The list's navigation bar** (search field 20–371, capsule to 417): not reached; see Left to do for what was tried.
3. **The W in the detail pane did nothing** (popToRoot on a one-screen stack); it now takes the tab back to its list and
   empties the detail pane, as it returned Search to its root before (`0ffa2ce`). Not tappable headless.
4. **Contents in book and flat sideways**: the overlay covered the list and blurred the article. The contents now take
   the list pane, in their inline form, beside the readable article in the detail pane (`03e1d80`): contents [0,0,455,669],
   article 496–867 pt. Open on the cover, they come with the article into the pane; closing brings them back as the
   overlay. Upright unchanged.
5. **The contents button upright was a solid disc** (`isSelected` on a plain item): back to the outline icon.
6. **Article actions behind the overflow**: the app's More now joins the system overflow where bars are vertical
   (`additionalOverflowItems`), contents and save have high priority, reading themes and search low, the tab bar
   compresses first (`.prefersBarItems`), and the tab bar hides beside an open article as it did full screen; the overflow
   capture on the cover shows every action one tap away (`probes/overflow-closed-cover.png`). The search item had no
   title, so it showed as an icon-only row in the overflow; titled (`00db16f`). Per pose: "Bars, per pose".
7. **Community's "In the news" footer ended 7 pt below its cell**: card heights were measured on a placeholder with its
   default margins; now with the live cell's 15 pt (`4ee89e9`). Every card's content ends inside its cell (book: 925 ≤
   940 pt).
8. **Settings rows ran across the fold** (T5 per the taxonomy's own corpus case; the audit called it clean): classified
   hierarchical, now a Fold-aligned split (`aa81129`): the list 0–435 pt, "No setting selected" beside it until a page
   opens.
9. **Activity, logged out, has nothing to open.** Decided by the skill: the relationship comes from the model (Activity
   logged in is a timeline of articles, hierarchical), not from what the screen shows now, and unsplit the login card's
   text crosses the fold again (T5). It stays split; its empty pane now says "Articles you open from your activity
   appear here".
10. **The container's background did not follow the theme**: it does now (`328cb92`).

Report corrections from the second round: the Account sheet's extent in book (483.5–943 pt, Close in its own vertical
bar), the W claim (now verified by `probes/article-home-book-inner.png`), the bar items that moved into the list pane's
top bar, the overflow per pose, For You's T1, and the Even grid's costs — all above.

### Third round
An independent review of the second round confirmed 22 findings (C0–C21), several of them regressions on devices with no
fold. What I did:
- **C12** state restoration lost the open article with Saved, Activity or Search selected (any iOS 27.1 device):
  `NavigationStateController` now unwraps the container (`aa1085b`).
- **C13, C1** theme: the pass now follows a presented container's two stacks; Settings no longer presents one.
- **C16** tab bar carried hidden into another tab: re-evaluated on every selection change and tap, tabs that are their
  own stack left to UIKit (touched only to undo).
- **C18** the Search item's title and priority gated on iOS 27.1 (`962e2f2`).
- **C20** the More actions in the system overflow are disabled while the toolbar is.
- Every other walk of the hierarchy checked: listed under Existing behaviour.
- **C0, C15, C21, C2** Settings' split: reverted (`a04b528`). Its pages are driven by a dozen coordinators that push and
  pop one stack, the donation reminder pops it, and two routes present it; making pushes from a detail page stack on the
  detail, pops reach it and every route split is a rewrite of Settings' navigation, not a pattern applied, and the skill
  does not allow ending a screen worse than it started. Settings' T5 is back in `todo`; C2 no longer applies.
- **C14** the contents follow the detail pane's top screen: another screen taking the pane removes them, and they come
  back when their article is on top again (`aa1085b`, `962e2f2`). Checked by code path (links cannot be tapped on the
  inner display).
- **C4** the list the contents cover is hidden from VoiceOver: the synced detectors no longer read it (contents' list
  pane: only the contents, 0–455 pt).
- **C19** the lead image no longer jumps: 512–851 pt in the detail pane with the contents open or closed, book and flat
  sideways (`962e2f2`, `162a1c6`).
- **C8** contents from Home or Places: in `todo` with the article and in the Result row.
- **C17** the `.savedPages` and `.activity` activities, `switchToSearch` and a second tap on the tab go through the
  container's `popToRoot`.
- **C6** the W beside the list says where it goes ("Wikipedia, return to Search"; its bar-item title names the list), and
  the report says Back is gone there.
- **C3, C5, C7, C9, C10, C11** report corrections: Search's top-bar items (Bars, per pose), the two-tap actions and the
  Even grid's 125/126 pt gutters, 85 pt short of the fold, descriptions not titles (Costs), the detail pane's top bar and
  profile's flat T5 (Left to do).
- Detector tables rewritten from the synced tools over the full before and after; `progress.py done --remove` took back
  the stale Settings, saved, search, article, contents and profile lines.

### Fourth round
The third review confirmed the round-3 fixes and found 23 smaller items (E0–E22 confirmed, U0–U3 plausible). What I did:
- **E5, E15** (medium) what the router opens from an article in the detail pane went onto the list's stack (in the list
  pane, or under open contents): the router's `currentNavigationController` now returns the tab's front stack, the
  detail stack while it shows an article (`4e0f095`). Covers More › Talk page, the footer's talk link, user, talk and
  in-app web links and the editor's cancel. The report's LinkCoordinator line is now true for this route.
- **E6** `visibleArticleViewController()` reads the front stack: a deep link to the open article scrolls it, the return
  from the web editor refreshes it in place, the Search quick action pushes Search onto it.
- **E7, E18** the evergreen prompt and the language-variant alerts count the tab as at its root only with nothing open
  in the detail pane (`isCurrentTabAtRoot`).
- **E8** the imported reading list goes back to Saved's root through the container (detail emptied, contents gone)
  before it is pushed; Notifications Center from a push notification goes on the front stack.
- **E0** for Home and Places, the re-check on a selection change no longer leaves the bar hidden: it only clears a hide
  the app set (`setTabBarHidden(false)`), and UIKit's `hidesBottomBarWhenPushed` does the rest, as on main.
- **E2, E12, E17** Edit is built when the More menu opens (a deferred element), so the disabled copy dropped it; it is
  now a disabled "Edit" with its pencil while the toolbar is disabled (`3c385e8`).
- **E9** the hide-contents item's filled rounded square is drawn into its image (a plain item has no background view).
  Measured as the review did, exact #F8F9FA pixels in the button's box: contents laptop 10,884 before, 10,918 after;
  tent 10,937 / 10,907; flat-upright 10,886 / 10,918; the article control (contents closed) 34 / 34.
- **E10** plain items keep the labels the old buttons had: themes reads "font size" again in every pose (snapshots);
  the hide item "Hide table of contents".
- **E1** open contents beside the list carry over to the next article: show and hide write the app's preference, and a
  new article's first showing reads it, as the inline contents did on main. The capture flow now starts with the
  preference off (it was off in the before capture), so a shot shows contents only when its own taps open them.
- **E3** `NavigationStateController`'s helper and `saveNavigationState` are main-actor.
- **E4** the push override's comment no longer mentions a Settings page.
- **E11** Existing behaviour no longer lists the outer display under "no change"; it points at the bars and costs there.
- **E13, E20** contents' book and flat-sideways cells are no longer "overlay in the Search tab's detail pane"; they are
  findings (T14, the detail pane's top bar), and contents left `done`; laptop, tent and flat-upright are verified
  (toolbar), not "verified in all seven poses".
- **E14, E19** the two stale Skill-problems bullets are corrected: `progress.py` has `done --remove` (it is in
  `references/simulator.md`; I missed it in the first pass), and the covered list is hidden from VoiceOver, so the
  snapshot holds only the contents.
- **E16** Activity's list capsule and the contents' detail top bar stop short like Saved's and the article's: activity
  and contents book and flat-sideways are findings (T14) in `todo`; activity left `done`.
- **E21** article and contents laptop, tent and flat-upright are "verified (toolbar: plain items)", not "unchanged".
- **E22** Places' T1 is the search field; its T14 line is hidden list text (a false hit), now said in the Result row,
  Detectors and Left to do.
- **U0** (plausible: confirmed by reading) the contents came back on `viewWillAppear` or a trait change whichever
  screen topped the detail stack. They now come back only when their article is the top screen.
- **U1** (plausible: confirmed by reading) `setTabBarHidden(_:animated:)` ran outside the transition, so the bar slid in
  at the start of a back swipe and snapped back after a cancel. It now runs in the transition coordinator's
  `animate(alongsideTransition:)`, so it follows the push, pop or swipe, and a cancelled swipe restores the previous
  state. Not verified with a swipe (no swipe in the tap runner); stated under Existing behaviour.
- **U2, U3** (plausible: confirmed by reading) the plain-tab "undo" could leave an explicit hide on a stack whose screen
  hides the bar. Same fix as E0: the app clears only its own hide and never sets one for Home or Places.
- Not in the findings, found by grepping every reader of the list stack again: the router's watchlist target pushed
  onto the list (now the front stack), and a second tap on the tab checked only the list's count, which misses a talk
  page now stacked in the detail pane (now counts the detail pane) (`3c66733`).
- Rebuilt; article and contents recaptured in all seven poses (14 cells, no "lost the screen"); no other screen's
  drawing changed. Detectors rerun over the full before (44 lines) and after (17 lines): the same cells as the third
  round. After, per changed cell: article laptop, tent, flat-upright: themes "font size" at [551,884,40,38], contents
  [25,884,38,38]; contents the same with "Hide table of contents" and the fill; lead image 512–851 pt in the detail pane
  with the contents open or closed (book, flat-sideways), as in the third round.

## Where the references and the SDK differ
- `references/apple.md` names `reservedRegions(kind:options:layoutDirectionBehavior:)` (SwiftUI). UIKit's 27.1 Swift API
  is `UIView.reservedRegions(kind:options:)` returning `UIView.ReservedRegion` (`frame`, `margins`, `isActive`);
  `.includeInactive` matches. `UISheetPresentationController.preferredPlacement` (27.0) is the UIKit counterpart of
  `presentationPlacement`, ignored when a `sourceView` is set.
- The SDK has UIKit vertical-bar hooks the references do not mention: `UIViewController.preferredVerticalBarBehavior`,
  `childForPreferredVerticalBarBehavior`, `setNeedsUpdateOfVerticalBarConfiguration()` (27.1) and
  `UITraitCollection.verticalBarEdge` / `systemTraitsAffectingVerticalBarEdge` (which Wikipedia already used).
  `UITabBarController.sidebar.preferredPlacement` (27.0) can put tabs in a sidebar on an iPhone; not used.

## Skill problems
What in the skill, its references or its tools was wrong, unclear or slow on this run, and what I did instead. Nothing
in `duo-patterns` (this repository's name at the time) was edited.

- **The decision table and `even-grid.md` disagree about this very feed.** I1 says a feed whose tap opens the item's
  own page ("an article into its text") is hierarchical, and in the same sentence lists "an Explore grid" as peer;
  `even-grid.md` uses Wikipedia's Explore as its corpus "before" for P3, while its "When not to use it" sends "a list of
  articles" to P1. Explore's cards mostly open articles. I followed the text that names this feed: community → Even
  grid (logged in `audit.md`). IceCubesApp's run reported the same ambiguity.
- **P1 has no route for a UIKit app without a split view.** The page's UIKit section adjusts an existing
  `UISplitViewController`. Wikipedia's tabs are plain navigation stacks in a `UITabBarController`, and 24 call sites
  push articles onto them through `ArticleCoordinator`. A `UISplitViewController` expands at any regular width, so it
  would also split Saved, Activity and Search on an iPad and on the upright inner display, where the app has no finding.
  I built a small container whose panes come only from reserved regions, a departure from "prefer system containers"
  (logged). What it had to handle that the page does not mention: the tab bar's `hidesBottomBarWhenPushed` and its
  pop-to-root on reselect only work for a navigation controller that *is* the tab; a screen that reappears when its
  article moves to the other pane takes that for a return (Search raised the keyboard across both panes and lost its
  results one fold later); a compact trait for the narrow panes flips trait-driven layouts on every unfold, because the
  window is regular for a moment before the regions arrive (tried and dropped); and the detail pane must stop at the
  trailing safe area or its web view runs under the vertical bar (found by T4, fixed).
- **P2's reference does not fit the usual article view.** `ReflowingColumns.swift` lays out plain paragraphs with
  TextKit. Wikipedia's article is a `WKWebView`; contents, find in page, scroll restoration and the native lead image all
  use vertical offsets, and the page itself says images and tables need their own rule. Left in `todo`.
- **No pattern for a map.** I1 calls a map continuous; the continuous row leads to Reflowing columns, whose Context is
  text read in order. Places → `todo` "no pattern yet".
- **The scans and detectors missed the worst defect.** The T10 scan looks for text-only items; Apple's rule is
  "text-only *and custom-view* items never go vertical". The article's six `UIBarButtonItem(customView:)` buttons (app
  subclass `IconBarButtonItem`) stayed a horizontal bar on the cover and were not drawn at all on the sideways inner
  display. No scan line and no detector reported it (T7 did not see six buttons vanish); found by looking at the shots
  and snapshots.
- **T13's plist glob misses target-named plists.** `rg -l 'UIApplicationSceneManifest' -g 'Info.plist'` finds nothing
  here; the manifest is in `Wikipedia/Wikipedia-Info.plist` (and three more `*-Info.plist`). The other two T13 lines hit,
  so the verdict held. Used `-g '*.plist'`.
- **T7 detector, the other way.** It reports the contents as lost in laptop, tent and flat upright because the cover's
  overlay has a Close button and the inner display's inline sidebar does not; the contents stay open and the toolbar
  hides them. A presentation change; not counted.
- **`same-screen.py` and maps.** Places' map loads its pins after the taps and each pin counts as fixed content, so every
  return to the cover scored 0.33–0.35: Places was relaunched before every inner pose, five "the shut phone lost the
  screen" lines per capture, all false (every shot shows Places), and about a minute more per pose.
- **T1, T14, T4 false hits.** T1 counts map annotations (17 pt pins, cluster counts) as fixed controls in laptop and
  tent; a map pans. T14 reported a Places "column 100–542" from hidden list text, nothing drawn there. T4 counts web-view
  links and scroll indicators near the window's edge as controls. Each read against the shot; listed in `audit.md`.
- **A reachability check that passes but misses.** Step 1's closed capture passed for `contents`, but the full capture
  landed on the plain article: the Table of Contents button is disabled until the page loads, and a tap on a disabled
  button "succeeds". The flow now waits 5 s; `contents` was captured again.
- **A subset recapture rewrites the capture record.** `SCREEN=… capture-app.sh … before` re-runs the detectors over the
  whole folder (good) but overwrites `capture.txt`, losing the first pass's lines (Places' "lost the screen"); I had
  copied them aside. Step 2 asks for exactly this recapture. (Fixed in the synced tools: `capture.txt` now gets a
  "recaptured:" block appended.)
- **Content a defect needs.** The tabs grid only shows T14 with three or more tabs, and Saved was empty; the skill says
  nothing about seeding. I saved two articles and opened three tabs through the app with the tap runner before the
  audit (logged), since the app's own reading-list seed needs the `UITEST` build flag.
- **Navigation stacks inset their screens for the vertical bar wherever they sit.** In UIKit every screen of a
  `UINavigationController` gets a trailing safe-area inset the width of the vertical bar when the bar is on that edge,
  even when the stack's own frame ends far from it (the stack's view reads 0, its screens 84 pt) — and its navigation
  bar's search field keeps it with no public setting I found. The pattern page's UIKit section and the reference files
  (SwiftUI `NavigationSplitView` / a system `UISplitViewController`, which handle it themselves) do not mention it; any
  custom pane container on the Duo hits it. Cancelled per screen with negative `additionalSafeAreaInsets`.
- **Size-class layouts in a narrow pane.** A pane narrower than the outer display still has the window's regular size
  class, so the app's own regular-width layouts (Wikipedia's inline contents) land in a 372 pt pane; and a compact trait
  for the pane flips them on every unfold, because the window is regular for a moment before the reserved regions
  arrive. The page says nothing about what a pane's screens should be told; I decided per screen from the pane.
- **A presentation does not survive its presenter moving between stacks.** The contents overlay presented on the cover
  stayed attached but undrawn after the article moved into the detail pane, which blocked presenting it again; it has
  to be dismissed first. Worth a line wherever the page says "move the detail screens between the stacks".
- **Neither the detectors nor my look caught the review's defects.** No class covers content that stops short of its
  pane (84 pt of blank before the fold) or a column too narrow to set words; T4 caught only two clipped links. The skill
  says "look at every shot", and a contact sheet is not enough: measure controls against their pane in the snapshot.
- **Speed.** As documented: 39 min for 77 cells (about 30 s a cell), taps a few seconds, no 60 s SpringBoard stalls.
  A build beside a capture slowed the capture noticeably; I stopped doing that. Each one-screen probe took 3–6 min.
- **The skill's reference copy is behind its source.** SKILL.md (step 5) sends a UIKit app to "the page's UIKit section
  … with or without a split view controller", and the second review pointed at "UIKit without a split view" in
  `references/patterns/fold-aligned-split.md`; the skill's copy has no such section. It exists only in the repository's
  `patterns/fold-aligned-split.md` (the sync script was not run for that file). Read it there.
- **`progress.py`'s `--remove` is easy to miss** (corrected in the fourth review; the first pass said it did not exist).
  `todo --remove <prefix>` and `done --remove <prefix>` are in `references/simulator.md` and the tool's usage, but
  SKILL.md's list of its commands (`phase`, `screen`, `cell`, `todo`, `done`, `log`) leaves them out; I found them only
  in the third round and used them then and in the fourth.
- **Taps reach only the cover.** The overflow menu in book, the W in the detail pane and the contents in the list pane
  cannot be tapped headless; and an overflow screen opened on the cover closes on the next fold, so the capture reports
  "the shut phone lost the screen" (a false T7) for it. Verified on the cover and from snapshots instead.
- **A screen inside a custom pane may not carry `verticalBarEdge`.** The article in the detail pane kept the app's More
  item because its own trait read unspecified; reading the window root's trait works.
- **What the accessibility tree shows under an accessory.** Until the third round, with the contents over the list pane
  the snapshot also held the list beneath them, and a detector reading frames saw both. The covered list is now hidden
  from VoiceOver (`accessibilityElementsHidden`), so the snapshot holds only the contents. The page could say that a
  pane's accessory must hide what it covers.
- **The new step-6 rule worked as a checklist.** Measuring every pane's controls against its edges in the snapshots
  (a small script) found what contact sheets hid: content stopping short of the fold, text clipped at a pane's edge,
  a card's footer below its cell.
- **A container on every iOS 27.1 device multiplies the walks to check.** Wrapping tab stacks in a container that is
  invisible without a fold still changes the hierarchy everywhere: state restoration, the theme pass and the tab bar
  broke on devices with no fold until each walk was unwrapped. The pattern page's "UIKit without a split view" says to
  unwrap the container where the app casts a tab; it should say to grep every walk (`as? UINavigationController`,
  `selectedViewController`, `presentedViewController`, `viewControllers`) and to re-evaluate the tab bar on every
  selection change.
- **A split is only as good as the routes into it.** Settings had two presentation routes and a dozen coordinators that
  push and pop one stack; splitting one route and redirecting pushes broke Back and Confirm. The page could say when not
  to split: a list whose pages navigate on their own.
- **The tools I ran in the second round were out of date** (the coordinator's note): with the synced copies Settings'
  T5, the list pane's search field (T14) and the covered list under the contents showed up, and map pins stopped
  counting.
- **A boolean launch argument must be written as plist** (fourth review). `capture-app.sh` and
  `capture-corpus-flow.sh` describe `LAUNCH_ARGS="A B"` as launch arguments, and they reach `NSUserDefaults` through the
  argument domain: `-Key NO` arrives as the string "NO". Wikipedia reads its contents preference with
  `object(forKey:) as? NSNumber`, so the string was ignored, the default (open) applied, the article screen opened with
  its contents, and the capture logged "the shut phone lost the screen" for the contents screen. `-Key <false/>` works.
  The flow docs could say so.
- **Flows share the app's saved state.** A preference one screen's taps write (open contents) changes the next screen's
  shot, and a relaunch does not reset it; the flow format has no reset step. Set with a launch argument.
- **Which stack is "current" depends on what is shown.** The third round unwrapped every walk to the list stack; the
  fourth review found routes that should land on the detail stack while it shows an article (the router, link
  handling, the visible article, root checks). "UIKit without a split view" could say: give the container a front
  stack and an at-root test, and route by them.
- **A change the detectors and a contact sheet cannot see.** The open-contents fill (#F8F9FA on glass) was lost in the
  second round; neither the detectors nor my look saw it. The review found it by counting exact pixels in the button's
  box before and after, which is what I used to confirm the fix.

## Time and disk
- 14:11–17:15 EDT, about 3 h 5 min: audit about 75 min; migration and probes about 75 min; after capture 37 min; report
  about 15 min. First review 17:17–18:26, about 1 h 10 min. Second review 18:30–20:20, about 1 h 50 min (the 49-cell
  and 14-cell recaptures about 35 min). Third review 20:50–21:35, about 45 min (the 42-cell and 14-cell recaptures
  about 30 min). Fourth review 22:06–22:50, about 45 min (two 14-cell recaptures, about 8 min each, the first replaced;
  two builds). In all about 7 h 45 min of work over 8 h 40 min.
- One derived data folder, `~/Library/Caches/duo-wikipedia` (3.0 GB, steady). Free space went from 12 GB at the start
  to 2.1–2.8 GB in the third round (the coordinator's reviews ran beside the run); in the third round I removed only my
  own temporary probe folders in the scratchpad (about 0.3 GB). In the fourth round free space read 2.1 GB at every
  check (before and after each build, capture and detector run); it never went under the 2 GB stop line, and I deleted
  nothing.

## Per screen, per pose
Shots of the screens recaptured after the reviews point at the latest `after` shots; earlier after-shots of those screens
are not kept.

### community — Even grid

| Pose | State | Before | After |
|---|---|---|---|
| closed | unchanged | `.duo/captures/Wikipedia/before/community-closed-cover.png` | `.duo/captures/Wikipedia/after/community-closed-cover.png` |
| closed-sideways | unchanged | `.duo/captures/Wikipedia/before/community-closed-sideways-cover.png` | `.duo/captures/Wikipedia/after/community-closed-sideways-cover.png` |
| book | verified (Even grid) | `.duo/captures/Wikipedia/before/community-book-inner.png` | `.duo/captures/Wikipedia/after/community-book-inner.png` |
| laptop | unchanged | `.duo/captures/Wikipedia/before/community-laptop-inner.png` | `.duo/captures/Wikipedia/after/community-laptop-inner.png` |
| tent | unchanged | `.duo/captures/Wikipedia/before/community-tent-inner.png` | `.duo/captures/Wikipedia/after/community-tent-inner.png` |
| flat-sideways | verified (Even grid) | `.duo/captures/Wikipedia/before/community-flat-sideways-inner.png` | `.duo/captures/Wikipedia/after/community-flat-sideways-inner.png` |
| flat-upright | unchanged | `.duo/captures/Wikipedia/before/community-flat-upright-inner.png` | `.duo/captures/Wikipedia/after/community-flat-upright-inner.png` |

### for-you — Fold-aligned split

| Pose | State | Before | After |
|---|---|---|---|
| closed | unchanged | `.duo/captures/Wikipedia/before/for-you-closed-cover.png` | `.duo/captures/Wikipedia/after/for-you-closed-cover.png` |
| closed-sideways | finding (T4) | `.duo/captures/Wikipedia/before/for-you-closed-sideways-cover.png` | `.duo/captures/Wikipedia/after/for-you-closed-sideways-cover.png` |
| book | finding (T5) | `.duo/captures/Wikipedia/before/for-you-book-inner.png` | `.duo/captures/Wikipedia/after/for-you-book-inner.png` |
| laptop | unchanged | `.duo/captures/Wikipedia/before/for-you-laptop-inner.png` | `.duo/captures/Wikipedia/after/for-you-laptop-inner.png` |
| tent | unchanged | `.duo/captures/Wikipedia/before/for-you-tent-inner.png` | `.duo/captures/Wikipedia/after/for-you-tent-inner.png` |
| flat-sideways | finding (T5) | `.duo/captures/Wikipedia/before/for-you-flat-sideways-inner.png` | `.duo/captures/Wikipedia/after/for-you-flat-sideways-inner.png` |
| flat-upright | unchanged | `.duo/captures/Wikipedia/before/for-you-flat-upright-inner.png` | `.duo/captures/Wikipedia/after/for-you-flat-upright-inner.png` |

### search — Fold-aligned split

| Pose | State | Before | After |
|---|---|---|---|
| closed | unchanged | `.duo/captures/Wikipedia/before/search-closed-cover.png` | `.duo/captures/Wikipedia/after/search-closed-cover.png` |
| closed-sideways | unchanged | `.duo/captures/Wikipedia/before/search-closed-sideways-cover.png` | `.duo/captures/Wikipedia/after/search-closed-sideways-cover.png` |
| book | finding (T14) | `.duo/captures/Wikipedia/before/search-book-inner.png` | `.duo/captures/Wikipedia/after/search-book-inner.png` |
| laptop | unchanged | `.duo/captures/Wikipedia/before/search-laptop-inner.png` | `.duo/captures/Wikipedia/after/search-laptop-inner.png` |
| tent | unchanged | `.duo/captures/Wikipedia/before/search-tent-inner.png` | `.duo/captures/Wikipedia/after/search-tent-inner.png` |
| flat-sideways | finding (T14) | `.duo/captures/Wikipedia/before/search-flat-sideways-inner.png` | `.duo/captures/Wikipedia/after/search-flat-sideways-inner.png` |
| flat-upright | unchanged | `.duo/captures/Wikipedia/before/search-flat-upright-inner.png` | `.duo/captures/Wikipedia/after/search-flat-upright-inner.png` |

### article — Reflowing columns

| Pose | State | Before | After |
|---|---|---|---|
| closed | verified (Reflowing columns (bars)) | `.duo/captures/Wikipedia/before/article-closed-cover.png` | `.duo/captures/Wikipedia/after/article-closed-cover.png` |
| closed-sideways | verified (Reflowing columns (bars)) | `.duo/captures/Wikipedia/before/article-closed-sideways-cover.png` | `.duo/captures/Wikipedia/after/article-closed-sideways-cover.png` |
| book | finding (T14) | `.duo/captures/Wikipedia/before/article-book-inner.png` | `.duo/captures/Wikipedia/after/article-book-inner.png` |
| laptop | verified (toolbar: plain items) | `.duo/captures/Wikipedia/before/article-laptop-inner.png` | `.duo/captures/Wikipedia/after/article-laptop-inner.png` |
| tent | verified (toolbar: plain items) | `.duo/captures/Wikipedia/before/article-tent-inner.png` | `.duo/captures/Wikipedia/after/article-tent-inner.png` |
| flat-sideways | finding (T14) | `.duo/captures/Wikipedia/before/article-flat-sideways-inner.png` | `.duo/captures/Wikipedia/after/article-flat-sideways-inner.png` |
| flat-upright | verified (toolbar: plain items) | `.duo/captures/Wikipedia/before/article-flat-upright-inner.png` | `.duo/captures/Wikipedia/after/article-flat-upright-inner.png` |

### contents — Arrangement (no page yet)

| Pose | State | Before | After |
|---|---|---|---|
| closed | unchanged | `.duo/captures/Wikipedia/before/contents-closed-cover.png` | `.duo/captures/Wikipedia/after/contents-closed-cover.png` |
| closed-sideways | unchanged | `.duo/captures/Wikipedia/before/contents-closed-sideways-cover.png` | `.duo/captures/Wikipedia/after/contents-closed-sideways-cover.png` |
| book | finding (T14) | `.duo/captures/Wikipedia/before/contents-book-inner.png` | `.duo/captures/Wikipedia/after/contents-book-inner.png` |
| laptop | verified (toolbar: plain items, contents inline as before) | `.duo/captures/Wikipedia/before/contents-laptop-inner.png` | `.duo/captures/Wikipedia/after/contents-laptop-inner.png` |
| tent | verified (toolbar: plain items, contents inline as before) | `.duo/captures/Wikipedia/before/contents-tent-inner.png` | `.duo/captures/Wikipedia/after/contents-tent-inner.png` |
| flat-sideways | finding (T14) | `.duo/captures/Wikipedia/before/contents-flat-sideways-inner.png` | `.duo/captures/Wikipedia/after/contents-flat-sideways-inner.png` |
| flat-upright | verified (toolbar: plain items, contents inline as before) | `.duo/captures/Wikipedia/before/contents-flat-upright-inner.png` | `.duo/captures/Wikipedia/after/contents-flat-upright-inner.png` |

### places — none (map)

| Pose | State | Before | After |
|---|---|---|---|
| closed | unchanged | `.duo/captures/Wikipedia/before/places-closed-cover.png` | `.duo/captures/Wikipedia/after/places-closed-cover.png` |
| closed-sideways | unchanged | `.duo/captures/Wikipedia/before/places-closed-sideways-cover.png` | `.duo/captures/Wikipedia/after/places-closed-sideways-cover.png` |
| book | finding (T1) | `.duo/captures/Wikipedia/before/places-book-inner.png` | `.duo/captures/Wikipedia/after/places-book-inner.png` |
| laptop | unchanged | `.duo/captures/Wikipedia/before/places-laptop-inner.png` | `.duo/captures/Wikipedia/after/places-laptop-inner.png` |
| tent | unchanged | `.duo/captures/Wikipedia/before/places-tent-inner.png` | `.duo/captures/Wikipedia/after/places-tent-inner.png` |
| flat-sideways | unchanged | `.duo/captures/Wikipedia/before/places-flat-sideways-inner.png` | `.duo/captures/Wikipedia/after/places-flat-sideways-inner.png` |
| flat-upright | unchanged | `.duo/captures/Wikipedia/before/places-flat-upright-inner.png` | `.duo/captures/Wikipedia/after/places-flat-upright-inner.png` |

### saved — Fold-aligned split

| Pose | State | Before | After |
|---|---|---|---|
| closed | unchanged | `.duo/captures/Wikipedia/before/saved-closed-cover.png` | `.duo/captures/Wikipedia/after/saved-closed-cover.png` |
| closed-sideways | unchanged | `.duo/captures/Wikipedia/before/saved-closed-sideways-cover.png` | `.duo/captures/Wikipedia/after/saved-closed-sideways-cover.png` |
| book | finding (T14) | `.duo/captures/Wikipedia/before/saved-book-inner.png` | `.duo/captures/Wikipedia/after/saved-book-inner.png` |
| laptop | unchanged | `.duo/captures/Wikipedia/before/saved-laptop-inner.png` | `.duo/captures/Wikipedia/after/saved-laptop-inner.png` |
| tent | unchanged | `.duo/captures/Wikipedia/before/saved-tent-inner.png` | `.duo/captures/Wikipedia/after/saved-tent-inner.png` |
| flat-sideways | finding (T14) | `.duo/captures/Wikipedia/before/saved-flat-sideways-inner.png` | `.duo/captures/Wikipedia/after/saved-flat-sideways-inner.png` |
| flat-upright | unchanged | `.duo/captures/Wikipedia/before/saved-flat-upright-inner.png` | `.duo/captures/Wikipedia/after/saved-flat-upright-inner.png` |

### activity — Fold-aligned split

| Pose | State | Before | After |
|---|---|---|---|
| closed | unchanged | `.duo/captures/Wikipedia/before/activity-closed-cover.png` | `.duo/captures/Wikipedia/after/activity-closed-cover.png` |
| closed-sideways | unchanged | `.duo/captures/Wikipedia/before/activity-closed-sideways-cover.png` | `.duo/captures/Wikipedia/after/activity-closed-sideways-cover.png` |
| book | finding (T14) | `.duo/captures/Wikipedia/before/activity-book-inner.png` | `.duo/captures/Wikipedia/after/activity-book-inner.png` |
| laptop | unchanged | `.duo/captures/Wikipedia/before/activity-laptop-inner.png` | `.duo/captures/Wikipedia/after/activity-laptop-inner.png` |
| tent | unchanged | `.duo/captures/Wikipedia/before/activity-tent-inner.png` | `.duo/captures/Wikipedia/after/activity-tent-inner.png` |
| flat-sideways | finding (T14) | `.duo/captures/Wikipedia/before/activity-flat-sideways-inner.png` | `.duo/captures/Wikipedia/after/activity-flat-sideways-inner.png` |
| flat-upright | unchanged | `.duo/captures/Wikipedia/before/activity-flat-upright-inner.png` | `.duo/captures/Wikipedia/after/activity-flat-upright-inner.png` |

### tabs — Even grid

| Pose | State | Before | After |
|---|---|---|---|
| closed | unchanged | `.duo/captures/Wikipedia/before/tabs-closed-cover.png` | `.duo/captures/Wikipedia/after/tabs-closed-cover.png` |
| closed-sideways | unchanged | `.duo/captures/Wikipedia/before/tabs-closed-sideways-cover.png` | `.duo/captures/Wikipedia/after/tabs-closed-sideways-cover.png` |
| book | verified (Even grid) | `.duo/captures/Wikipedia/before/tabs-book-inner.png` | `.duo/captures/Wikipedia/after/tabs-book-inner.png` |
| laptop | unchanged | `.duo/captures/Wikipedia/before/tabs-laptop-inner.png` | `.duo/captures/Wikipedia/after/tabs-laptop-inner.png` |
| tent | unchanged | `.duo/captures/Wikipedia/before/tabs-tent-inner.png` | `.duo/captures/Wikipedia/after/tabs-tent-inner.png` |
| flat-sideways | verified (Even grid) | `.duo/captures/Wikipedia/before/tabs-flat-sideways-inner.png` | `.duo/captures/Wikipedia/after/tabs-flat-sideways-inner.png` |
| flat-upright | unchanged | `.duo/captures/Wikipedia/before/tabs-flat-upright-inner.png` | `.duo/captures/Wikipedia/after/tabs-flat-upright-inner.png` |

### profile — Fold-aligned split

| Pose | State | Before | After |
|---|---|---|---|
| closed | unchanged | `.duo/captures/Wikipedia/before/profile-closed-cover.png` | `.duo/captures/Wikipedia/after/profile-closed-cover.png` |
| closed-sideways | unchanged | `.duo/captures/Wikipedia/before/profile-closed-sideways-cover.png` | `.duo/captures/Wikipedia/after/profile-closed-sideways-cover.png` |
| book | verified (Fold-aligned split) | `.duo/captures/Wikipedia/before/profile-book-inner.png` | `.duo/captures/Wikipedia/after/profile-book-inner.png` |
| laptop | unchanged | `.duo/captures/Wikipedia/before/profile-laptop-inner.png` | `.duo/captures/Wikipedia/after/profile-laptop-inner.png` |
| tent | unchanged | `.duo/captures/Wikipedia/before/profile-tent-inner.png` | `.duo/captures/Wikipedia/after/profile-tent-inner.png` |
| flat-sideways | finding (T5) | `.duo/captures/Wikipedia/before/profile-flat-sideways-inner.png` | `.duo/captures/Wikipedia/after/profile-flat-sideways-inner.png` |
| flat-upright | unchanged | `.duo/captures/Wikipedia/before/profile-flat-upright-inner.png` | `.duo/captures/Wikipedia/after/profile-flat-upright-inner.png` |

### settings — Fold-aligned split (reverted)

| Pose | State | Before | After |
|---|---|---|---|
| closed | unchanged | `.duo/captures/Wikipedia/before/settings-closed-cover.png` | `.duo/captures/Wikipedia/after/settings-closed-cover.png` |
| closed-sideways | unchanged | `.duo/captures/Wikipedia/before/settings-closed-sideways-cover.png` | `.duo/captures/Wikipedia/after/settings-closed-sideways-cover.png` |
| book | finding (T5) | `.duo/captures/Wikipedia/before/settings-book-inner.png` | `.duo/captures/Wikipedia/after/settings-book-inner.png` |
| laptop | unchanged | `.duo/captures/Wikipedia/before/settings-laptop-inner.png` | `.duo/captures/Wikipedia/after/settings-laptop-inner.png` |
| tent | unchanged | `.duo/captures/Wikipedia/before/settings-tent-inner.png` | `.duo/captures/Wikipedia/after/settings-tent-inner.png` |
| flat-sideways | finding (T5) | `.duo/captures/Wikipedia/before/settings-flat-sideways-inner.png` | `.duo/captures/Wikipedia/after/settings-flat-sideways-inner.png` |
| flat-upright | unchanged | `.duo/captures/Wikipedia/before/settings-flat-upright-inner.png` | `.duo/captures/Wikipedia/after/settings-flat-upright-inner.png` |
