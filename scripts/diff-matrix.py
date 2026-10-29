#!/usr/bin/env python3
"""G2: compare a fresh catalog capture against the committed pose matrices (the goldens).

    OUT=/tmp/fresh scripts/capture-catalog.sh          # capture somewhere else
    python3 scripts/diff-matrix.py /tmp/fresh [verification/matrices] [--partial]

For each <pattern>/<config>-<pose>.png in the golden folder, the share of pixels that differ by more than a small
tolerance, with the system's own status areas masked: every occlusion region the app reported (the clock and status
cluster, the cameras), since the clock changes between runs. Fails (exit 1) when any shot differs by more than 0.5 %
of its pixels (EVAL.md G2) or is missing from the fresh capture (--partial skips missing ones, for a spot check).
"""
import json
import pathlib
import sys

from PIL import Image, ImageChops

THRESHOLD = 0.005   # EVAL.md G2: perceptual diff ≤ 0.5 % pixels
TOLERANCE = 24      # per-channel difference treated as resampling noise


def masked(png, frames):
    img = Image.open(png).convert("RGB")
    if frames.exists():
        d = json.loads(frames.read_text())
        k = img.width / d["window"][0] if d["window"][0] else 1
        for r in d["occlusions"]:
            box = [round(r["x"] * k), round(r["y"] * k), round((r["x"] + r["w"]) * k), round((r["y"] + r["h"]) * k)]
            img.paste((0, 0, 0), box)
    return img


def share(a, b):
    if a.size != b.size:
        return 1.0
    diff = ImageChops.difference(a, b).convert("L").point(lambda v: 255 if v > TOLERANCE else 0)
    return diff.histogram()[255] / (a.width * a.height)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    partial = "--partial" in sys.argv
    fresh = pathlib.Path(args[0])
    golden = pathlib.Path(args[1] if len(args) > 1 else "verification/matrices")
    checked = 0
    worst, failed = 0.0, []
    for g in sorted(golden.glob("*/*.png")):
        rel = g.relative_to(golden)
        f = fresh / rel
        if not f.exists():
            if not partial:
                failed.append(f"{rel}: missing")
            continue
        checked += 1
        s = share(masked(g, g.with_suffix(".json")), masked(f, f.with_suffix(".json")))
        worst = max(worst, s)
        if s > THRESHOLD:
            failed.append(f"{rel}: {s:.2%} of pixels differ")
    for line in failed:
        print(line)
    print(f"{checked} of {len(list(golden.glob('*/*.png')))} goldens compared, worst {worst:.2%}, "
          f"{len(failed)} failed (threshold {THRESHOLD:.1%})")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
