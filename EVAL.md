# EVAL.md — pre-registered success criteria

Written **before** any pattern is named (2026-10-24). Changing anything below after patterns exist is a
deviation and gets logged in `docs/history/DEVIATIONS.md` with the reason. "The owner" below is the project's maintainer,
who decides what ships; amendments carry the date and "(owner)".

## 1. What "right" means, and who decides
None of it is decided by the author or the authoring agent.

| Gate | Decided by | Pass condition |
|---|---|---|
| G1 Compiles | Xcode 27.1 in CI | Every pattern reference implementation and the harness build against the iOS 27.1 SDK with zero warnings in our own code |
| G2 Goldens | DuoPoseTesting in CI | Every pattern's pose matrix matches its committed goldens (perceptual diff ≤ 0.5 % pixels) |
| G3 Detectors | Taxonomy detectors in CI | Zero findings on every pattern and on every migrated corpus app, for every pose |
| G4 Oracle | Side-by-side with Apple's app | For each pattern, the matched system app in the same pose shows the same pane assignment and bar placement (documented in `verification/oracle/<pattern>.md` with both screenshots) |
| G5 Blind A/B | ≥ 5 iOS developers who are not the author | Skill-migrated screenshots beat bare-agent screenshots on the rubric in §3, per pose, with raters blind to condition |
| G6 Strangers | Maintainers and other skill authors | ≥ 1 corpus PR merged; ≥ 2 external skills/lists link the catalog; ≥ 1 case study submitted by someone else |

v0 ships when G1–G4 pass for three patterns and G5 has been *run* (whatever the result, published). G6 is tracked, not gated.

*Note 2026-10-29: the owner set G5 aside on 2026-10-27 (§4, §6), so v0 ships when G1–G4 are met for three patterns and one corpus app has been migrated by the skill and plugin (§6). §7 records where each gate stands.*

*Amended 2026-10-29 (owner): where a pattern's matched app is not on the simulator, G4 sets the reference beside Apple's own published frames of that app (a tech talk or HIG image, linked at the frame and not stored, since the frames are Apple's), measured where a frame is face-on. A pose that no published frame shows has no oracle. See `docs/history/DEVIATIONS.md`.*

## 2. Corpus apps to be migrated (pre-selected, see `raw/corpus/README.md`)
A/B set (three): **IceCubesApp** (feed, SwiftUI-heavy), **NetNewsWire** (list-detail, mixed), **home-assistant/iOS** (dashboard/controls).
Rationale: one per content relationship; all SPM-only so a bare agent has no build excuse. Firefox and Wikipedia are migration targets later, not A/B subjects, because their legacy branching would confound the comparison with build fixes.

## 3. Rubric (per screenshot, per pose; 0 / 1 / 2 each)
R1 Reachability — primary actions within the thumb zone for that pose; nothing interactive in the crease band.
R2 Crease — no text line, control, or focal image straddles an active division.
R3 Occlusion — nothing meaningful under the camera occlusion when active; no clipped bar items.
R4 Continuity — opening/closing keeps the same content and selection visible; no state loss, no re-layout that reorders controls.
R5 Bars — bars on the hardware side with the standard order; nothing stranded horizontal that should be vertical, nothing duplicated.
R6 Use of space — inner display gains an information level or breathing room; no empty strips, no stretched single columns.
R7 Consistency — control positions are recognizably the same across poses.
Max 14 per pose. Raters see only screenshots + the app name; condition labels are stripped.

## 4. Blind A/B protocol
1. Same prompt to both conditions: *"Adapt this app for iPhone Duo. Preserve existing behavior. Verify every pose."* Condition A: bare Claude Code / Codex. Condition B: same agent with the skill installed. Same model, same day, one run each (no cherry-picking; record the run ids).
2. Both outputs built on the same machine; screenshots taken by `scripts/capture-poses.sh` (identical poses, identical settle time).
3. Screenshots renamed by a script to random ids; mapping sealed until scoring is done.
4. Raters: ≥ 5 iOS developers recruited publicly (post the request before the runs). Each rates every screenshot on R1–R7. Rater instructions are frozen in `verification/ab/INSTRUCTIONS.md` before recruitment.
5. Report: mean score per condition per pose per app, with the raw sheet. Published in `verification/ab/RESULTS.md` regardless of direction.

*Set aside 2026-10-27 (owner): v0 is a hands-free migration tool for Claude Code, and the blind A/B with recruited raters
is not run for it. The harness (`verification/ab/`: protocol, flows, baselines, blinding and scoring scripts) stays for a
later study. The evidence for v0 is a whole corpus app migrated end to end by the skill alone (G3). See `docs/history/DEVIATIONS.md`.*

## 5. Decision-table discipline
Every cell in `patterns/DECISION-TABLE.md` cites either a system-app screenshot in `raw/apple-apps/`, a measured constraint in `raw/metrics.json`, or Apple's published guidance in `raw/apple-docs/` (a tech talk with its timestamp, or a HIG or documentation section by name). A cell with no citation is marked `UNJUSTIFIED` and the pattern it points to cannot ship.

*Amended 2026-10-26, before any pattern was named: the third source was added because the iOS 27.1 simulator runtime ships only two of Apple's apps. See `docs/history/DEVIATIONS.md`. Corpus findings (`raw/corpus/defects.csv`) still do not count as citations: they show what goes wrong, not what Apple prescribes.*

## 6. Scope lock
v0 = three patterns + harness + skill + one corpus migration + the A/B run. Anything else is v0.1+.

*Amended 2026-10-27 (owner): v0 = three patterns + harness + the hands-free skill and its Claude Code plugin (pane, `/duo-start` (now `/foldsmith-start`)) + one corpus migration done by them. The A/B run is set aside (§4).*

*Amended 2026-10-29 (owner): Arrangement (P4) is built in v0, as the third pattern to pass G1–G4, because no Apple frame looked at shows a text in columns, so Reflowing columns' G4 has no oracle (`verification/oracle/reflowing-columns.md`). Reflowing columns stays in the catalog and the skill with G4 open. See `docs/history/DEVIATIONS.md`.*

## 7. Where the gates stand (2026-10-29)
A record, not a verdict: whether these results make v0 complete is the owner's decision, not yet recorded.

| | G1 | G2 | G3 | G4 |
|---|---|---|---|---|
| Fold-aligned split | met: built in the private working repository's CI on every push, and in this repository's CI on pushes to main and pull requests; a clean build on 2026-10-29 (catalog, package, tap runner) had no warnings in our code, which CI does not check | met: 119 of 119 goldens, worst 0.00 %, in the private working repository's CI on 2026-10-29 (its run logs are not public); not yet run on this repository's hosted CI | met for the references: clean in every pose (`MatrixTests`) | against Settings (`verification/oracle/fold-aligned-split.md`): the same panes and system bars in book and flat sideways, one pane on the cover; differs upright (sidebar 250 against 320 pt, a bar row); bar items differ in every pose; no oracle on the turned cover |
| Even grid | met, as above | met | met for the references | against Fitness's published frames (`verification/oracle/even-grid.md`): in book the same count, assignment and bar placement, the column widths differ; open flat the spacing and widths differ; no frame found in five poses |
| Arrangement | met, as above | met | met for the references | against Podcasts' and Accessibility Reader's published frames (`verification/oracle/arrangement.md`): the same assignment side by side, the bars differ; differs upright; the overlay has Reader's assignment; no frame on the cover or in tent |
| Reflowing columns (in the catalog, not one of v0's three) | met, as above | met | met for the references | open: no Apple frame looked at shows a text in columns (`verification/oracle/reflowing-columns.md`) |

G4's condition asks for the same pane assignment and bar placement. Fold-aligned split and Arrangement have poses where
the bar placement, or upright the layout, differs from Apple's app; Even grid has Fitness's column count and bar
placement in the two poses with a frame, with different column widths and spacing; the bar items differ for all three,
and the pages say where. Corpus migration (G3 for a migrated app):
IceCubesApp's after captures are clean in every pose; NetNewsWire's were clean with the detectors of its run, and the
T10 detector added later finds its Reader View button in 8 cells, not fixed; Wikipedia's run left findings in `todo`
(`verification/runs/`). G3's corpus part is met on IceCubesApp's five logged-out screens; whether it is judged on one
app (§6) or on every migrated app (§1), and with each run's detectors or the current ones, is the owner's decision,
not yet recorded. G5 is set aside; G6 (strangers) has nothing yet.

