---
description: Review an iPhone Duo migration independently, in a new session (records what it finds; changes no code)
argument-hint: "[app folder]"
---
Review this app's iPhone Duo migration with the foldsmith-duo skill's `references/review.md`, as the independent
reviewer it describes: this session did not make the change, so judge it from the diff, the captures and the code, and
read the run's report, audit and plan only at the checklist's last step. The arguments, if any: $ARGUMENTS
- An app folder named there is the app to review; with none named, it is this folder.
- It reviews the `duo-migration` branch, checked out, with its `.duo/migration.json` and after captures. Without them,
  or with another branch checked out, say what is missing and stop: switching branches is the person's to do.
- Take the base, the inputs and the nine checks from `references/review.md`, in its order. Run the skill's tools by
  their path with their interpreters (`python3 …/tools/progress.py`, `bash …/tools/routes.sh`, `python3
  …/tools/sdkguard.py`); the review needs no simulator. A probe, where only a shot settles a claim, needs the
  skill's preflight and `source .duo/env` first.
- Try to refute each finding before recording it. Record each confirmed one with `tools/progress.py issue add …
  --found-by review` (`--regression` for anything worse than at the base), then the review with
  `tools/progress.py review session "<summary>"`.
- Append `## Independent review (<date>)` to `.duo/REPORT.md`: the commit reviewed, the confirmed findings (severity,
  regression or not, evidence, issue id) and the refuted ones with why.
- Change no code, capture nothing into `before` or `after`, make no branch, commit nothing, push nothing.
- Close with the findings, most severe first, which are regressions, and what the review could not check. With a
  regression recorded, say that `/foldsmith-start` resumes the migration and fixes it.
