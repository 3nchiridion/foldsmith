#!/usr/bin/env python3
"""EVAL.md §4 step 5: rater sheets → verification/ab/RESULTS.md.

    python3 scripts/ab-score.py <sheet.csv> [<sheet.csv> ...]

Needs verification/ab/mapping.json (scripts/ab-blind.py unseal). Each sheet is one rater's, in the order given
(rater-1, rater-2, …). For every app, condition and pose: the mean total score (R1–R7, 0–14) over the app's screens and
the raters, and the mean of each criterion. The screens are the ones in verification/ab/flows/<app>.flow. A screen a
condition did not produce (the tree did not build, or the frozen taps no longer reach it) scores 0 on every criterion
for that condition (PROTOCOL.md); a screen neither condition produced is left out. Blank cells are counted and
reported, not scored. The raw sheets are copied to verification/ab/sheets/.
"""
import csv
import os
import pathlib
import re
import shutil
import statistics
import sys
import json

ROOT = pathlib.Path(__file__).resolve().parent.parent
AB = pathlib.Path(os.environ.get("FOLDSMITH_EVIDENCE", ROOT.parent / "foldsmith-evidence")) / "verification" / "ab"
POSES = ["closed", "closed-sideways", "book", "laptop", "tent", "flat-sideways", "flat-upright"]
CRITERIA = [f"R{i}" for i in range(1, 8)]


def flow_screens(app):
    text = (AB / "flows" / f"{app}.flow").read_text()
    return re.findall(r'^\s*"([^"=]+)=', text, re.M)


def main(sheets):
    mapping = json.loads((AB / "mapping.json").read_text())["items"]
    produced = {(m["app"], m["screen"], m["condition"]): iid for iid, m in mapping.items()}
    apps = sorted({m["app"] for m in mapping.values()})
    scores = {}   # (rater, item, pose) → [R1..R7]
    blanks = 0
    for r, path in enumerate(sheets, 1):
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                values = []
                for c in CRITERIA:
                    v = (row.get(c) or "").strip()
                    if v in ("0", "1", "2"):
                        values.append(int(v))
                    else:
                        blanks += 1
                        values.append(None)
                scores[(r, row["item"], row["pose"])] = values

    raters = range(1, len(sheets) + 1)
    out = ["# A/B results (G5)", "",
           f"Raters: {len(sheets)}. Scores 0–14 per pose (R1–R7, 0/1/2 each), mean over the app's screens and the raters. "
           "Method: `verification/ab/PROTOCOL.md`; computed by `scripts/ab-score.py`.", ""]
    if blanks:
        out += [f"Blank or invalid cells: {blanks} (left out of the means).", ""]
    for app in apps:
        screens = [s for s in flow_screens(app) if any((app, s, c) in produced for c in "AB")]
        out += [f"## {app}", "", f"Screens: {', '.join(screens)}.", "",
                "| Pose | A (bare) | B (skill) | B − A |", "|---|---|---|---|"]
        criteria_rows = []
        for pose in POSES:
            means = {}
            for cond in "AB":
                totals, per = [], [[] for _ in CRITERIA]
                for s in screens:
                    iid = produced.get((app, s, cond))
                    for r in raters:
                        values = scores.get((r, iid, pose)) if iid else [0] * len(CRITERIA)
                        if values is None:
                            continue
                        if all(v is not None for v in values):
                            totals.append(sum(values))
                        for i, v in enumerate(values):
                            if v is not None:
                                per[i].append(v)
                means[cond] = (statistics.mean(totals) if totals else None,
                               [statistics.mean(p) if p else None for p in per])
            a, b = means["A"][0], means["B"][0]
            fmt = lambda v: "n/a" if v is None else f"{v:.2f}"
            out.append(f"| {pose} | {fmt(a)} | {fmt(b)} | {fmt(b - a) if a is not None and b is not None else 'n/a'} |")
            criteria_rows.append(f"| {pose} | " + " | ".join(f"{fmt(x)} / {fmt(y)}" for x, y in zip(means['A'][1], means['B'][1])) + " |")
        out += ["", "Per criterion (A / B):", "", "| Pose | " + " | ".join(CRITERIA) + " |",
                "|---|" + "---|" * len(CRITERIA)] + criteria_rows + [""]
    (AB / "sheets").mkdir(exist_ok=True)
    for r, path in enumerate(sheets, 1):
        shutil.copyfile(path, AB / "sheets" / f"rater-{r}.csv")
    out += ["Raw sheets: `verification/ab/sheets/rater-<n>.csv`; mapping: `verification/ab/mapping.json`."]
    (AB / "RESULTS.md").write_text("\n".join(out) + "\n")
    print("→ verification/ab/RESULTS.md")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
