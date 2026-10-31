---
description: Adapt this whole app for iPhone Duo, hands-free (resumes a migration already under way)
argument-hint: "[app folder] [--structural]"
---
Adapt this whole app for iPhone Duo with the foldsmith-duo skill, hands-free: every screen, every pose. Preserve
existing behavior. Verify every pose. If `.duo/migration.json` exists, resume from it and take what is left from the top.
The arguments, if any: $ARGUMENTS
- An app folder named there is the app to adapt; with none named, it is this folder.
- Unless `--structural` is given, or the arguments ask in words for the structural changes, make local changes only,
  and write each structural one as a proposal in `.duo/PLAN.md`.
- With `--structural` (or those words), the person asks for the structural changes too: once every local change is
  made, verified and committed, make the ones proposed in `.duo/PLAN.md`, one screen group at a time, each taken
  through the capture, the check, a fresh review and the report again, as the skill's Hands-free "Order" says.
