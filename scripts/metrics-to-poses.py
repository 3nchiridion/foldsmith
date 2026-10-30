#!/usr/bin/env python3
"""Turn raw/metrics.jsonl (DuoProbe output, in the evidence repository 3nchiridion/foldsmith-evidence, beside this one
or at $FOLDSMITH_EVIDENCE) into Sources/DuoDetectors/Resources/poses.json and raw/metrics.json (the per-pose summary
the decision table cites), with a copy at patterns/metrics.json for scripts/sync-skill-references.py.

For each label, the *settled* sample is the last of the burst right after launch, before the first
pause longer than SETTLE_GAP: run-probe.sh then folds out and back, and the app keeps logging under the
old label while the next pose is set up, so later samples are not at this pose. The *first-frame*
sample is seq==1 for that launch. Both are kept so the first-frame vs
settled difference (empty regions on first evaluation, per community reports) is on record.
"""
import json, os, sys, collections, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
EVIDENCE = pathlib.Path(os.environ.get("FOLDSMITH_EVIDENCE", ROOT.parent / "foldsmith-evidence"))
SRC = EVIDENCE / "raw" / "metrics.jsonl"
SETTLE_GAP = 1.5  # seconds
# The hinge state each pose must report (the at-pose hinge reading is the first sample in this state).
EXPECTED_HINGE = {"closed": "closed", "closed-sideways": "closed", "book": "partiallyOpen", "laptop": "partiallyOpen",
                  "tent": "partiallyOpen", "flat-sideways": "fullyOpen", "flat-upright": "fullyOpen"}
# The shape each pose must have (duo.py's measured table); a mismatch means the orientation was dropped.
EXPECTED_SHAPE = {"closed": "tall", "closed-sideways": "wide", "book": "wide", "laptop": "tall",
                  "flat-sideways": "wide", "flat-upright": "tall"}

if not SRC.exists():
    sys.exit(f"missing {SRC}; run scripts/run-probe.sh on the Mac first")

by_label = collections.defaultdict(list)
for line in SRC.read_text().splitlines():
    line = line.strip()
    if not line:
        continue
    if line.startswith("DUOPROBE "):
        line = line[len("DUOPROBE "):]
    s = json.loads(line)
    by_label[s["label"]].append(s)

poses, summary = [], {}
for label, samples in by_label.items():
    samples.sort(key=lambda s: (s["seq"]))
    first = next((s for s in samples if s["seq"] == 1), samples[0])
    burst = [first]
    for s in samples[1:]:
        if s["sinceLastChange"] > SETTLE_GAP:
            break
        burst.append(s)
    settled = burst[-1]
    want = EXPECTED_HINGE.get(label)
    hinge = next((s["hinge"] for s in samples if (s.get("hinge") or {}).get("status") == want), None)
    def region(r):
        # CGRect's Codable form is an unkeyed [origin, size] = [[x, y], [w, h]]; CGSize is [w, h].
        return {"frame": [[r["frame"]["x"], r["frame"]["y"]], [r["frame"]["w"], r["frame"]["h"]]],
                "margins": r["margins"], "isActive": r["isActive"]}
    sc = settled["scene"]
    bounds = sc.get("sceneBounds") or {"w": settled["window"]["w"], "h": settled["window"]["h"]}
    shape = "wide" if bounds["w"] > bounds["h"] else "tall"
    shape_ok = EXPECTED_SHAPE.get(label, shape) == shape
    wsa = sc.get("windowSafeArea")  # schema 2: physical edges, the device's own insets
    poses.append({
        "name": label,
        "display": "outer" if label.startswith("closed") else "inner",
        "window": [bounds["w"], bounds["h"]],
        "safeArea": ({"top": wsa["top"], "leading": wsa["left"], "bottom": wsa["bottom"], "trailing": wsa["right"]}
                     if wsa else settled["safeArea"]),
        "hSizeClass": settled["hSizeClass"], "vSizeClass": settled["vSizeClass"],
        "toolbarVerticalEdge": None if settled["toolbarVerticalEdge"] == "nil" else settled["toolbarVerticalEdge"],
        "divisions": [region(r) for r in settled["divisions"]],
        "occlusions": [region(r) for r in settled["occlusions"]],
    })
    summary[label] = {
        "settled": settled,
        "firstFrame": first,
        "firstFrameHadRegions": bool(first["divisions"] or first["occlusions"]),
        "samples": len(samples),
        "secondsToSettle": round(settled["t"] - first["t"], 3),
        "hingeAtPose": hinge,
        "shape": shape,
        "shapeMatchesPose": shape_ok,
    }

# Pose.swift decodes CGSize as [w,h] and CGRect as [[x,y],[w,h]] (CoreGraphics' Codable conformance). Verify on the Mac with a round-trip test.
(ROOT / "Sources/DuoDetectors/Resources/poses.json").write_text(json.dumps(poses, indent=2))
for out in (EVIDENCE / "raw/metrics.json", ROOT / "patterns/metrics.json"):
    out.write_text(json.dumps(summary, indent=2, sort_keys=True))
print(f"{len(poses)} poses → poses.json; summary → raw/metrics.json (evidence) and patterns/metrics.json")
for p in poses:
    flag = "" if summary[p["name"]]["shapeMatchesPose"] else "   <-- WRONG SHAPE: orientation was not applied, re-run this pose"
    print(f"  {p['name']:16} {p['window']}  insets={p['safeArea']}  div={len(p['divisions'])} occ={len(p['occlusions'])}  edge={p['toolbarVerticalEdge']}{flag}")
