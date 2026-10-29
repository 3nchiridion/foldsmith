# Wikipedia, migrated hands-free and then reviewed (2026-10-28)

The third run of the hands-free skill (`skills/iphone-duo-patterns/SKILL.md`), and the first on a UIKit and
Objective-C app whose articles are a web view. The agent got the `/duo-start` prompt and nothing else about the work:
a fresh Claude Code subagent with the skill, on the project's iPhone Duo simulator (iOS 27.1, Xcode 27.1), since
headless `claude -p` was still signed out. The prompt added this machine's facts (Xcode, `duo.py`, the tap runner), the
app's own build facts (ad-hoc signing for its app-group container, the xcconfig its setup script writes), no sign-in to
Wikipedia, and the project's limits (no simulator changes, no push, no edits to this repository). The app was
wikipedia-ios at 2031b89, copied outside this repository with one baseline commit on `main`; the skill committed its
work on `duo-migration` there.

Unlike the first two runs, this one did not pass review. The run's own check, and each round of fixes after it, passed
defects that a fresh reviewer then found. After four rounds of fixes the last review still confirmed 15, two of them
medium regressions; the owner asked to finish there, so they are listed below, not fixed. What follows says what each
round found.

| File | What it is |
|---|---|
| `REPORT.md` | the skill's report: per screen the pattern, what changed, the bars per pose, costs, existing behaviour, what is left and why, each review round item by item, and "Skill problems" |
| `audit.md` | the audit of the unmodified app and the classification of each screen |
| `migration.json` | the progress file at the end (what the `duo-migration` pane reads) |
| `Wikipedia.flow` | the eleven screens the skill found and the taps that reach them, logged out |
| `detectors-before.md`, `detectors-after.md` | `duo-detect` as of Phase 4 step 9 on the 77 snapshots before and after |
| `Wikipedia.patch` | the code change, `main..duo-migration` without `.duo/`; MIT, as wikipedia-ios is |
| `LICENSE-MIT-Wikimedia` | the license of the patch: wikipedia-ios's `LICENSE.txt` at 2031b89, unchanged |
| `commits.txt` | the run's 28 commits |

The shots stay outside this repository, as for every run.

## Result
Eleven screens, logged out. Two are done: community (Explore, an Even grid, 418 → 366 pt columns off the fold) and the
article tabs (an Even grid). Nine are in the run's `todo`; in every capture none is worse than before, but the last
review found regressions in paths no capture reaches ("Last check"):
- **saved, search, activity, article, contents**: split at the fold by a container of the app's own (the
  "UIKit without a split view" section of `patterns/fold-aligned-split.md`), with articles in the detail pane and
  their contents in the list pane. What keeps them in `todo`: the top bars of both panes keep the vertical bar's
  84 pt inset (the list's search field ends at 371 of 455 pt, the detail's top bar 38–42 pt short of its edge), and
  nothing the run tried moved them. Everything else in both panes reaches its edges.
- **article and contents opened from Home or Places**: still one 827 pt column across the fold (Reflowing columns for
  a web view is not built).
- **settings**: split in the second round, broken in ways the captures could not show, reverted in the third; its rows
  still cross the fold (T5).
- **places** (a map, no pattern), **for-you** (shares Home's stack with community's grid), **profile** (the Account
  sheet's text crosses the inactive fold flat sideways, as before; in book it now sits on the trailing half).

`duo-detect`, the detectors as of Phase 4 step 9, over the run's snapshots: 23 cells with a finding before (44 lines), 16 after (17
lines). Of the 16: the list's search field (T14, 6 cells), contents' T7 in the inner poses (5, the cover's overlay has
a Close button the inline contents do not need: a presentation change, not counted), For You and Settings (T5, 4),
Places (1). The run's own second-round table came from older copies of the detectors (the coordinator had not resynced
the skill after the first review's fixes); it reran them in the third round.

About 7 h 45 min of the agent's work over 8 h 40 min: the run 3 h 5 min, then four rounds of 1 h 10 min, 1 h 50 min,
45 min and 45 min. Free disk went from 12 GB to 2.1 GB.

## What each round found
| Round | Found by | What it found (the report's "Found in review" has every item) |
|---|---|---|
| the run | the run's own check | seven of eleven screens verified in every pose, settings needing nothing, three in `todo`; 21 cells → 10 by the detectors of that time; it read contact sheets |
| first | the coordinator, from the shots | 2 defects passed as clean: the contents in a 372 pt pane breaking words and pushing the article past its edge (a regression), and the lists stopping 84 pt short of the fold |
| second | an independent review (three reviewers by screen group, a skeptic per finding) | 10 items: search results 84 pt short, the W dead in the detail pane, the contents overlay covering the list and blurring the article, actions behind the system overflow, Settings across the fold, a card ending below its cell, and others; six report claims the evidence contradicted |
| third | an independent review (four reviewers, a skeptic each) | 22 items, among them state restoration and Settings' theme broken on every iOS 27.1 device by the container, Settings sub-pages replacing each other with no Back, stale contents beside a new article, VoiceOver reaching the list under the contents, the tab bar carried into other tabs |
| fourth | an independent review (four reviewers, a skeptic each) | 23 items: routes from the detail pane (Talk page, links, notifications) opening in the list pane, three more walks of the hierarchy reading the list, the themes button's VoiceOver label and the open-contents fill lost on every iOS 27.1 device, Edit missing from the disabled overflow, open contents no longer carrying over |
| after the fourth | an independent review of round four (two reviewers, a skeptic each) | see "Last check" below |

Through the fourth round every confirmed regression was fixed or its change reverted (Settings' split); the agent was
told each time that a regression never goes to `todo`.

## Last check
Two reviewers, one of the fourth round's code and one of the report, each with a skeptic, confirmed 15 items (none
refuted). Not fixed; each needs a tap on the inner display, a fold with an article open, or a notification, which no
capture here reaches:
- **Medium:** unfolding with an article open covers the list pane with its contents whenever the app's "contents
  visible" preference is true, which it is by default and which closing them on the cover no longer clears (the
  carry-over of the fourth round reads it on every entry into the pane, not only for a new article). The random-article
  shortcut opens in the 455 pt list pane, in place of the list: it reaches the list's stack through
  `setViewControllers`, which the container's push override never sees.
- **Low, regressions in book and flat sideways:** a second push-notification tap stacks a second Notifications Center
  (the "already showing" check reads the list's stack); removing a closed tab's article from the detail pane leaves it
  blank, with no placeholder and the tab bar still hidden; tapping the current tab in the tabs overview re-creates its
  article; the Search quick action pushes Search over the article and the tab bar reappears beside it; screens the list
  pane opens through the router (Activity's diffs and contributions) stack on an unrelated article in the detail pane
  when one is open, and open in the list pane when none is.
- **Low, elsewhere:** the open-contents icon drawn on its restored fill is 18 % smaller and dark grey instead of black
  (upright, every iOS 27.1 device); a cancelled back swipe can still bring back the previous article's contents (the
  fourth round's guard covers a trait change only); `ArticleTableOfContentsDisplayController` still reads main-actor
  state without isolation.
- **Report slips:** the random-article shortcut listed as unaffected; the themes item's label claimed for the cover,
  where it sits in the overflow; the upright inner display called "no reserved region" (it has a horizontal one the app
  ignores); a time total and a pixel count off by a little; a plausible item named U2 that the findings file calls U3.

What these share: the container decides where a route goes by what the detail pane holds, and several of the app's
routes reach a stack without the container (`setViewControllers`, a coordinator's own stack, a check that reads the
list). The split page now says to route by where an action comes from and to cover every way onto a stack.

## Changes where there is no fold
What the migration changes on a device or pose with no reserved region, all in the report's "Existing behaviour":
- on any iOS 27.1 device, the article toolbar's items are plain titled items (same VoiceOver labels, same open-contents
  look, Save's long press a one-item menu), and Saved, Activity and Search sit in an invisible container, whose tab bar
  the app hides and shows over an open article with the push or pop (not by `hidesBottomBarWhenPushed`; not checked
  with an interactive swipe, which the tap runner cannot do);
- on the Duo's cover, which has a vertical bar, the article's toolbar goes into it and some actions move into the
  system overflow (the report's "Costs" lists the ones that now take two taps).
Nothing changes before iOS 27.1. The app's tests, its Experimental and Alpha targets and every device but the Duo
simulator were not run. Paths that need a tap on the inner display (the W in the detail pane, routes from it, contents
after a link) were checked in code, not captured.

## What this repository took from it (Phase 4, step 9)
- **Detectors**: T10 also reads custom-view toolbar items (the article toolbar stayed horizontal on the cover and
  vanished in book, found by eye); T7 also reports toolbar items stranded on the shut phone that no inner pose has;
  T14 also reports a list pane whose search field or segmented control stops short of the fold; small things lying on
  a map pan with it (Places' pins), in the detectors and in `same-screen.py`; a list row's content is one run, so a
  settings row with its title and value on either side of the fold is T5 (Settings, which no detector saw).
- **Tools**: the tap runner waits up to 15 s for a disabled element before a plain tap (the contents button is
  disabled until the page loads); a `SCREEN=` recapture keeps the first pass's lines and each screen's latest capture
  decides the exit code; `progress.py done --remove`.
- **The skill**: seed content a defect needs; read detector lines against the shots; the regression rule (never end
  worse); measure each pane's controls against its edges; check that moved controls still work; gate what changes for
  the Duo on 27.1 and on the condition that needs it, even where an API is older; a custom view turned into a titled
  item keeps its label, look and enabled state; read the diff for what no shot shows (every walk of the hierarchy a
  container changes, every route into a changed screen, covered views, state that follows its screen), and hand it to
  a fresh reviewer where a subagent can be started.
- **The patterns**: Fold-aligned split's "UIKit without a split view" (a container, its effect on every device, the
  bar's inset, size classes in a narrow pane, moving screens between stacks, routing by where an action comes from, pushes from a detail page,
  what the list pane holds, when not to split); Reflowing columns' "When the text is a web page"; the decision table's
  feed and map rules and bar-items rule; Even grid's costs.
- **References**: `simulator.md` on recaptures, maps, menus that close on a fold, inner-only controls, covered content
  in the tree, `LAUNCH_ARGS` booleans and settings that carry between screens; `detectors-static.md`'s custom-view scan
  and the T13 plist glob.
