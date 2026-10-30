# NetNewsWire, migrated hands-free (2026-10-27)

The first run of the hands-free skill (`skills/foldsmith/SKILL.md`) on a corpus app: one prompt, no
questions, run by a Claude Code agent with the skill and the `iphone-duo-simulator` driver, on the project's iPhone Duo
simulator (iOS 27.1, Xcode 27.1). The app was NetNewsWire at d9ec7df (`raw/corpus/NetNewsWire`, a clone made by `raw/corpus/clone.sh`, not committed), copied outside this
repository, with a `duo-baseline` commit; the skill committed its work on `duo-migration` there.

| File | What it is |
|---|---|
| `REPORT.md` | the skill's report: per screen the pattern, what changed, what is left and why |
| `audit.md` | the audit of the unmodified app and the classification of each screen |
| `migration.json` | the progress file at the end of the run (what the Foldsmith pane reads) |
| `NetNewsWire.flow` | the screens the skill found and the taps that reach them |
| `detectors-before.md`, `detectors-after.md` | `duo-detect` on the 35 snapshots before and after |
| `NetNewsWire.patch` | the code change, `duo-baseline..duo-migration` without `.duo/` (NetNewsWire is MIT) |
| `LICENSE-MIT-NetNewsWire` | the license of the patch: NetNewsWire's `LICENSE` at d9ec7df, unchanged |
| `commits.txt` | one commit per screen, then the feeds follow-up |

Result of the run: five screens, all Fold-aligned split. Timeline, article, settings and Add Feed were verified in all
seven poses; feeds was left in `todo` (T7 in the five inner poses: unfolding from the feeds list showed an empty
timeline beside "No selection"; NetNewsWire has three levels and P1 described two). The detectors went from 3 findings
to 0; the rest (T14 on the feeds and timeline panes in book, T1 on "No selection" in laptop and tent, T7, T10 on Add
Feed's text-only buttons) were seen in the shots only. Captures took about 76 of the run's minutes (about 65 s a cell).

Follow-up, the same day, after the owner decided the three-level question (the sidebar beside the article): the last
commit makes the split two panes on the inner display, the list pane (feeds, then the timeline pushed on it) and the
article (`REPORT.md`, "Follow-up"). Recaptured with one test run per screen: 35 cells in 915 s, `duo-detect` 0, every
shot checked. All five screens are verified in all seven poses (G3).

`detectors-before.md` and `detectors-after.md` are rerun with the detectors of Phase 4 step 5, which close the run's
misses: the before captures now show 26 findings (T14 on all three split panes in book, T1 on "No selection" in laptop
and tent, T7 on feeds in every inner pose and on the timeline upright, T10 on Add Feed, T15 on both sheets), everything
the run saw by eye; the after captures show none.

Phase 4 step 9 (2026-10-28, after the Wikipedia run) taught T10 custom-view toolbar items. On these captures it finds
one the run and its review missed, before and after alike: the article's Reader View button,
`UIBarButtonItem(customView:)` in `ArticleViewController.swift`, stays beside the vertical bar on the cover and in the
detail pane (8 cells after: article, timeline and feeds in book and flat-sideways, the article closed and
closed-sideways). Not fixed here; `detectors-before.md` and `detectors-after.md` are left as they were run.

The run's own shots and snapshots stay outside the repository, as for every run.
