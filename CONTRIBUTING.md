# Contributing

Thank you for looking. Three kinds of contribution are welcome:

- **A problem with the plugin or the skill**: open an issue with the app (or a minimal project), the pose, what you
  expected, and the run's `.duo/migration.json`. Leave out anything private: the progress file names screens, not data.
- **A corpus app or a migration case study** goes to
  [foldsmith-evidence](https://github.com/3nchiridion/foldsmith-evidence): a corpus app's repository and commit in
  `raw/corpus/manifest.txt` and its findings in `raw/corpus/defects.csv`, with shots under `raw/corpus/evidence/<app>/`;
  a case study as a `verification/runs/<app>/` folder like the three there (README, REPORT.md, audit.md, migration.json,
  the patch with its licence). Redact other people's posts in any shot (`scripts/redact-shots.py`).
- **A pattern**, below. A pattern is a claim about every pose, so it comes with its measurements, not after them.

Work on a branch and open a pull request against `main`; CI runs the detector tests and the builds (`EVAL.md` G1, G3).

## Adding a pattern
The gates in [`EVAL.md`](EVAL.md) are the contract: the reference builds with zero warnings (G1), its pose matrix
matches its goldens (G2), the detectors find nothing on it in any pose (G3), and it matches the Apple app that does the
same thing, in the poses Apple shows it in (G4).

### 1. Measure the need
- Find the defect the pattern fixes in real apps: rows in foldsmith-evidence's `raw/corpus/defects.csv`, each with a
  shot, and the class it belongs to in [`patterns/TAXONOMY.md`](patterns/TAXONOMY.md).
- Find the Apple app that solves the same layout, and capture it or cite Apple's published frames of it (linked, never
  stored).
- Find the cell it fills in [`patterns/DECISION-TABLE.md`](patterns/DECISION-TABLE.md): content relationship ×
  interaction mode × pose. A pattern no cell needs is not added; a cell marked `UNJUSTIFIED` needs evidence first.
  [`patterns/CLUSTERING.md`](patterns/CLUSTERING.md) shows how the four patterns were chosen.

### 2. Write the page and the reference
- `patterns/<pattern>.md` from [`patterns/TEMPLATE.md`](patterns/TEMPLATE.md): context, forces, the solution per pose
  with a citation on every row, consequences, known uses, when not to use it, and the detectors it must pass.
- `Sources/Patterns/<Pattern>.swift`: one copy-in file with no dependency on this repository, iOS 27.1 APIs behind
  `#available(iOS 27.1, *)` with the pre-Duo layout as the fallback, and Duo-only code behind
  `#if os(iOS) && !targetEnvironment(macCatalyst)`. Never branch on device identity, idiom or orientation.

### 3. Put it in the catalog and capture its matrix
- In `Examples/Catalog/`, a demo for the pattern in `Catalog/Demos.swift` (a case for it in `CatalogApp.swift`) with at
  least two variants: `aligned`, the reference, and a "before" variant that reproduces the defect. Record the views the
  detectors read with the catalog's tracking modifiers, as the other demos do.
- Add its configs (`<pattern>:<variant>`) to `CONFIGS` in `scripts/capture-catalog.sh`.
- With foldsmith-evidence checked out beside this repository (or `FOLDSMITH_EVIDENCE` set), build and install the
  catalog on the iPhone Duo simulator, then
  `DUO_UDID=<udid> DUO_PY=<duo.py> scripts/capture-catalog.sh <pattern>:aligned <pattern>:<before>`: shots and frame
  records go to the evidence repository, and the frame records are packed into `Tests/Fixtures/matrices.json`.
- `python3 scripts/compose-matrix.py` composes the matrix in the evidence repository and refreshes the small copy in
  `docs/images/matrices/`, which the page shows.
- Capture the catalog's accessibility snapshots too (`scripts/capture-corpus-flow.sh` with `SNAPSHOT=1`, into the
  evidence repository's `verification/accessibility/catalog/`), then run `python3 scripts/pack-fixtures.py`, which packs
  them into `Tests/Fixtures/accessibility-catalog.json`.

### 4. Hold it with the tests and the detectors
- `Tests/DuoPoseTestingTests/MatrixTests.swift`: add the reference to `referenceIsCleanInEveryPose`, the before variant
  and the classes it must show to `beforeVariantShowsItsDefectAndNothingElse`, and update the config count.
  `AccessibilityTests.swift` checks that the snapshots agree with the frame records; update its count.
- If the defect is one no detector finds, add one: a type conforming to `Detector` in
  `Sources/DuoDetectors/Detectors/Detector.swift`, listed in `Detectors.all`, with cases in `DetectorTests.swift` and a
  row in `patterns/TAXONOMY.md`.
- Add the decision-table row (or fill the cell) that routes screens to the pattern, citing the evidence.

### 5. Compare with Apple, then sync
- `verification/oracle/<pattern>.md` in the evidence repository: the reference beside the Apple app in each pose Apple
  shows it in, and where they differ.
- Add the page to `PAGES` in `scripts/sync-skill-references.py`, run it, and commit what it writes: the skill
  (`skills/foldsmith-duo/`) and the plugin's copy carry the page, the reference and the matrix.

Before the pull request: `swift test`, `python3 -m unittest discover -s scripts -p 'test_*.py'`,
`python3 scripts/sync-skill-references.py --check`, and, if you touched the plugin, `claude plugin validate
plugins/foldsmith` and `claude plugin test plugins/foldsmith` (Claude Code 2.1.308 or later). G2 runs on demand:
`gh workflow run ci.yml -f goldens=true`.
