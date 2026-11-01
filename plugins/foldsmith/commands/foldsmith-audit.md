---
description: Audit this app for iPhone Duo without changing it (every screen in every pose, the fix per screen, App Store screenshots)
argument-hint: "[app folder]"
---
Audit this app for iPhone Duo with the foldsmith-duo skill: the audit its "What was asked" describes, without a
question and without changing the app's code. The arguments, if any: $ARGUMENTS
- An app folder named there is the app to audit; with none named, it is this folder.
- First the skill's preflight (`tools/preflight.sh <app folder>`, in a shell that has not sourced `.duo/env`). If it
  blocks, show its fix list and stop: the fixes are the person's to make, never yours.
- If an earlier audit left `.duo/migration.json`, take up from it: keep what it found, and check again each screen
  waiting in `todo` as `needs sign-in`. If the progress file is past phase `classify` (a migration's), capture nothing
  into `before`, change no phase, skip the steps below, and report from the file what is left (the skill's
  `tools/progress.py check` and its `todo`).
- Then the skill's steps 1 to 4: find the screens and write their flow, capture every screen in every pose before any
  change (in the background; read the exit code), run the detectors and look at every shot, classify each screen and
  look up its pattern. A clean detector table is not a pass: what the detectors miss is still a finding.
- Write `.duo/audit.md` (per screen and pose, the classes found; the classification and why) and `.duo/PLAN.md` in
  its two sections: `## Local`, per screen the pattern and the fix the migration would make, and `## Structural
  (proposed)`, each structural change with the routes the skill's `tools/routes.sh` lists (the decision table's "Local
  and structural changes" says which is which). PLAN.md also gives the preflight's note on the Xcode the project's CI
  builds with (`tools/sdkguard.py --ci-only`) and what it asks of the migration: below Xcode 27, every iOS 27 API
  inside `#if compiler(>=6.4)`; on Xcode 27.0, a proposal to move the CI to 27.1.
- Export the App Store set from the cells already fine: the skill's `tools/appstore.py --kind before`.
- Change no code, make no branch, commit nothing, push nothing. The progress file ends at phase `classify`, so the
  Foldsmith pane shows the audit, and `/foldsmith-start` later takes it up without repeating it.
- Close with the screens that have findings and the fix for each; the Xcode the project's CI uses (or that none is
  named in the repository); what the App Store set holds, where, and that every
  image must be checked for personal content and the status bar before it is uploaded; and the screens no taps
  reached, with why. For each one that needs the person's own login, say: sign in on the Duo simulator yourself
  (name it as the progress file does, `iPhone Duo (<UDID>)`), then run `/foldsmith-audit` or `/foldsmith-start`
  again.
