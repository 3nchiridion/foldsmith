---
description: Adapt this whole app for iPhone Duo, hands-free (resumes a migration already under way)
argument-hint: "[app folder] [--structural]"
---
Adapt this whole app for iPhone Duo with the foldsmith-duo skill, hands-free: every screen, every pose. Preserve
existing behavior. Verify every pose. If `.duo/migration.json` exists (a migration under way, or an audit), resume from
it and take what is left from the top.
The arguments, if any: $ARGUMENTS
- An app folder named there is the app to adapt; with none named, it is this folder.
- The preflight runs first, in a shell that has not sourced `.duo/env`; if it blocks, show its fix list and stop.
  One exception: on `duo-migration`, uncommitted changes outside `.duo/` are the migration's own (an interrupted
  session's unfinished change, or a build's side effect): finish and commit that change, or put it aside with the stash
  line the preflight prints (it keeps `.duo/`), log which, and run the preflight again.
- The run never logs in to the app. A screen that needs the person's own login waits in `todo` as `needs sign-in`;
  once they have signed in on the Duo simulator themselves, this command checks it again and carries on, never
  reinstalling the app.
- Unless `--structural` is given, or the arguments ask in words for the structural changes, make local changes only,
  and write each structural one as a proposal in `.duo/PLAN.md`'s Structural section. Taking up an audit, mark each
  item of its Local section made (with its commit), or moved to `todo`, as you go.
- With `--structural` (or those words), the person asks for the structural changes too: once every local change is
  made, verified and committed, make the ones in `.duo/PLAN.md`'s Structural section, one screen group at a time,
  each taken through the capture, the check, a fresh review and the report again, as the skill's Hands-free "Order"
  says.
