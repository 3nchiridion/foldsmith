# Mac phase — run this in Claude Code on the Mac, from the repo root

> Historical: the Phase 1 plan as it was run on the owner's Mac. It stays because `DEVIATIONS.md` records departures
> from it. To use the catalog or the skill, see `README.md` and `plugins/foldsmith/README.md`.

Everything that needs Xcode 27.1 or the Duo simulator. Each step writes into [`raw/`](https://github.com/3nchiridion/foldsmith-evidence/tree/main/raw/) and nothing else
is allowed to start until the step's output exists. Copy the prompt block into Claude Code.

```
You are continuing the duo-patterns project. Read STATUS.md, EVAL.md and raw/*/README.md first.
Phase 1 is partly done from the cloud; finish the Mac-only parts, in this order, and stop after each
step to show me the output before starting the next.

Step 1 — SDK truth.
Run scripts/extract-sdk.sh. Then diff every signature and default it finds against
raw/apple-docs/api-swiftui.md and raw/apple-docs/api-uikit.md. Write raw/sdk/DIFF.md listing each
mismatch (name, docs said, SDK says) and the DeviceHinge.Status cases and ToolbarVerticalEdge type.
Also run `xcrun agent skills export --output-dir raw/sdk/apple-skill` and read Apple's own
App Resizability skill; summarize in raw/sdk/APPLE-SKILL.md what it does and does not cover
(we must not duplicate it).

Step 2 — Probe.
Install xcodegen if needed. cd Probe && xcodegen generate, build DuoProbe for the iPhone Duo simulator,
fix compile errors against the real SDK (update ProbeRoot.swift; record every change in raw/sdk/DIFF.md).
Install github.com/WhitenWhiten/iphone-duo-simulator-skill into ~/.claude/skills and locate its duo.py.
Run DUO_UDID=<udid> DUO_PY=<path> scripts/run-probe.sh. Then python3 scripts/metrics-to-poses.py.
Show me raw/metrics.json. Check specifically: window size and insets per pose; whether seq==1 samples
have empty region arrays; secondsToSettle; division frame when flat (inactive) vs book/laptop (active);
occlusion frames on the outer display; toolbarVerticalEdge per pose. Compare against the community table
in raw/complaints/README.md §B and note agreements and disagreements.

Step 3 — Apple's apps as oracle.
Run scripts/capture-system-apps.sh. Open every screenshot with Read and fill each
raw/apple-apps/<app>/NOTES.md line: where the bars went, how the fold was handled, what moved.
Mail and Music are not on the simulator: leave a note saying so.

Step 4 — Corpus.
bash raw/corpus/clone.sh. For each app: follow its README to build for the Duo simulator against
27.1 (bundle exec pod install for Signal; Package.swift for Firefox). Record build outcome in
raw/corpus/BUILDS.md (succeeded / needed target bump / failed and why). For every app that runs,
capture every pose for its 3–5 main screens and log every defect in raw/corpus/defects.csv with the
columns in patterns/TAXONOMY.md, using T-ids where one fits and NEW-<n> where none does.

Stop there. Phase 2 (clustering, decision table) begins only when raw/sdk/DIFF.md, raw/metrics.json,
raw/apple-apps/*/NOTES.md and raw/corpus/defects.csv all exist. Report anything you could not do as a
deviation in DEVIATIONS.md, not as done.
```

## What to expect to go wrong
- `scripts/run-probe.sh` depends on `duo.py` for fold control; there is no public `simctl` fold command. If `duo.py` doesn't work on your Xcode build, fall back to Device Hub buttons and the script's manual prompts.
- `simctl io screenshot` may capture the switched-off display; `duo.py shot` is the known workaround.
- ProbeRoot.swift was written without an SDK: expect two to five compile errors (environment key type for `toolbarVerticalEdge`, `onGeometryChange` isolation under `SWIFT_DEFAULT_ACTOR_ISOLATION = MainActor`, `DeviceHinge.Status` description, `ReservedRegion.ID` interpolation). Fix and log.
- Corpus builds will take the longest. Signal (CocoaPods, iOS 15) and 2048 (ObjC, iOS 8, 2018) may not build; a failed build is itself a data point (compatibility mode) — screenshot it anyway if it installs.
