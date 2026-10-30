# references/

Everything the skill knows, each file traceable to `raw/` or to a measured capture in `verification/`.

| File | What it is | Made by |
|---|---|---|
| `decision-table.md` | copy of `patterns/DECISION-TABLE.md` (`UNJUSTIFIED` cells count as no cell) | `scripts/sync-skill-references.py` |
| `taxonomy.md` | copy of `patterns/TAXONOMY.md` | `scripts/sync-skill-references.py` |
| `patterns/<name>.md`, `patterns/matrices/` | the v0 pattern pages and their pose matrices | `scripts/sync-skill-references.py` |
| `metrics.md` | pose table from `raw/metrics.json` | `scripts/sync-skill-references.py` |
| `apple.md` | Apple's rules condensed from `raw/apple-docs/`, with citations, no transcript text | by hand |
| `simulator.md` | pose control and capture commands that worked on the Mac | by hand |
| `detectors-static.md` | source scans for T3, T5, T9, T10, T13, T14 | by hand |
| `../tools/` | capture scripts, tap runner, detectors (copies; see `tools/README.md`) | `scripts/sync-skill-references.py` |

Do not edit the generated files here: edit the source and run `python3 scripts/sync-skill-references.py`. CI fails
when they differ (`--check`). Nothing in here may contain a rule that is not traceable to `raw/`.
