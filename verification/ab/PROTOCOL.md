# A/B protocol — how G5 is run

> Set aside 2026-10-27 (EVAL.md §4): kept for a later study; nobody is being recruited.

EVAL.md §4 is the pre-registration; this file is how it is carried out on the project's Mac. Where it has to choose
something §4 leaves open, the choice is marked **owner decision** until the owner confirms it, and then frozen with
everything else here when the recruitment request goes out (§4.4). A change after that is a deviation.

## Order (EVAL.md §4)
1. Freeze `INSTRUCTIONS.md`, this file, the flows in `flows/` and the skill as installed (`skills/iphone-duo-patterns`
   at a named commit). Done when the recruitment request is posted.
2. Post the recruitment request (`RECRUITMENT.md`). **The runs start only after it is up.**
3. Six runs: three apps × two conditions, one run each, same model, same day where the machine allows (below).
4. Build each run's result, capture it with `scripts/capture-poses.sh`, blind it with `scripts/ab-blind.py`.
5. Raters score; the mapping is unsealed; `scripts/ab-score.py` writes `RESULTS.md`, whatever the direction.

## Subjects
IceCubesApp, NetNewsWire, home-assistant/iOS (EVAL.md §2), each at its commit in `raw/corpus/manifest.txt`, set up
exactly as `raw/corpus/BUILDS.md` records (the same xcconfig, secrets and signing flags), committed as a local
`baseline` commit so a run's diff is only the agent's.

## Conditions
Same for both, except the one line marked B.

| | |
|---|---|
| Agent | Claude Code CLI (`claude -p`), the version installed on the day, recorded |
| Model | `claude-opus-5-5`, pinned with `--model` |
| Prompt | exactly: `Adapt this app for iPhone Duo. Preserve existing behavior. Verify every pose.` |
| Working directory | a fresh clone of the subject at its `baseline` commit, in its own folder |
| Configuration | a fresh `CLAUDE_CONFIG_DIR` per run: no user CLAUDE.md, memory, plugins, MCP servers or user skills. **Owner decision:** it needs one sign-in per config folder, or an API key (`--bare` with `ANTHROPIC_API_KEY`), which only the owner can supply. |
| Simulator driver | both conditions get the community `iphone-duo-simulator-skill` as a project skill (`.claude/skills/`), the only scriptable way to fold the simulator; without it "verify every pose" cannot be done at all, and the comparison would measure the driver rather than the catalog. **Owner decision.** |
| **B only** | `skills/iphone-duo-patterns/` copied to `.claude/skills/iphone-duo-patterns/` in the clone |
| Permissions | **Owner decision:** `--dangerously-skip-permissions` (the run builds, installs and drives the simulator unattended; it can reach anything the owner's account can) or an allowlist of build and simulator commands, which both agents would hit equally. |
| Limits | 3 hours wall clock and `--max-budget-usd` (**owner decision**, same cap for every run). A run that hits a limit stops there and is captured as it stands. |
| Operator | the person running the session sends nothing but the prompt. If the agent stops to ask for approval (the skill's step 3 does), the operator answers, at most twice per run: `Proceed with what you propose.` Nothing else, in either condition. Every resume is logged. |
| Order | per app, the condition that goes first is drawn by `python3 -c 'import secrets; print(secrets.choice("AB"))'`, logged |
| Logs | `--output-format stream-json` to `runs/<app>-<condition>.jsonl` (kept out of git until results are out; then committed with paths and anything personal removed), session ids in `runs/RUNS.md` |

The simulator is shared: before each run the subject app is uninstalled and its privacy grants reset; nothing else is
erased. Runs go one after another (one Duo simulator, 19 GB free for build folders; a build folder is deleted after
its capture). Six runs of up to three hours do not fit in one day; "same day" becomes "consecutive days, same model and
CLI version", logged as a deviation if it happens.

## Capture
After each run, outside the agent's session: build the run's tree with the baseline's build command (the agent's own
build settings, if it changed any, are used as the tree has them), install it, and run
`scripts/capture-poses.sh <app> verification/ab/runs/<app>-<condition>`. The flows are frozen: a screen the run no
longer reaches by them is recorded as missing, not re-tapped by hand.

Strangers' posts: IceCubesApp's launch and timeline screens show other people's Mastodon posts. Its flow lists them in
`REDACT`, and `capture-poses.sh` pixelates them right after every capture, baseline and both conditions alike
(`scripts/redact-shots.py`): the visible area of every scrolling container and whatever is dimmed behind a sheet become
12 pt blocks; every image inside a scrolling container (a photo in a post, a server's banner) becomes one flat block of
its average colour, clipped to its cell, since a large photo's faces are still several blocks wide; then the keyboard
and navigation bars, tab bars and bar items are put back. Layout and bars stay judgeable; a scrolling sidebar shows as
blocks too. Snapshots keep no label from inside scrolling content in any app.

The unmodified apps were captured the same way first: `baseline/<app>/` (shots, snapshots, `detectors.md`). They are
the "before" for the report and a check that every frozen flow reaches its screen; raters do not see them. They were
taken on the Duo simulator the runs use. A second one, made to capture in parallel, stopped responding in tent and
was deleted: `duo.py` must find exactly one Duo for the agents.

Scoring of what does not exist, decided now: a tree that does not build, or a screen the frozen taps no longer reach,
scores 0 on every criterion in every pose for that condition. A screen missing in both conditions is left out.

The detectors run on every capture (`detectors.md` next to the shots). They are reported beside the ratings, not
mixed into them; G3's zero-findings bar applies to the one corpus migration (EVAL.md §6), not to A/B runs.

## Blinding (`scripts/ab-blind.py`)
- One item per app × screen × condition: the seven pose shots and a matrix, renamed to a random id. Item order is
  shuffled; the app name stays (raters see it, §3).
- The mapping (id → app, screen, condition) and a random salt go to a file **outside the repository**; only its
  SHA-256 is committed (`SEAL.txt`). Unsealing (`--unseal <mapping>`) checks the hash before anything is scored.
- The packet raters receive: `items/`, `sheet.csv`, `INSTRUCTIONS.md`. Nothing in it names a condition.

## Scoring (`scripts/ab-score.py`)
Each rater's `sheet.csv` → mean score (0–14) per condition per pose per app, the per-criterion means, and the raw
sheets, into `RESULTS.md`. Published whatever the direction (§4.5).

## Not decided here
- How the packet reaches raters and how sheets come back (owner: email, a shared folder, a form).
- Where the recruitment request is posted (owner). The request describes the rating task without linking the
  repository.
