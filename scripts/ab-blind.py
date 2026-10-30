#!/usr/bin/env python3
"""EVAL.md §4 step 3: turn the A/B captures into a blind rating packet, and seal the key.

    python3 scripts/ab-blind.py pack <runs-dir> <packet-dir> <mapping.json>
    python3 scripts/ab-blind.py unseal <mapping.json>

pack: <runs-dir> holds one folder per run, `<app>-<condition>/<app>/<screen>-<pose>-<panel>.png` as
scripts/capture-poses.sh writes them. Every app × screen × condition becomes an item with a random id: the seven pose
shots renamed `<pose>.png` and a `matrix.png` of all seven. Items are shuffled. The packet also gets `sheet.csv` (one
row per item and pose, R1–R7 empty) and a copy of verification/ab/INSTRUCTIONS.md. The mapping (id → app, screen,
condition, plus a random salt) is written to <mapping.json>, which must be outside the repository; its SHA-256 goes to
verification/ab/SEAL.txt, the only part committed before scoring.

unseal: checks <mapping.json> against SEAL.txt and copies it to verification/ab/mapping.json for scripts/ab-score.py.

Needs Pillow for the matrix image (pip install pillow); without it the packet is made with no matrix.png.
"""
import csv
import hashlib
import json
import os
import pathlib
import random
import secrets
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
AB = pathlib.Path(os.environ.get("FOLDSMITH_EVIDENCE", ROOT.parent / "foldsmith-evidence")) / "verification" / "ab"
POSES = ["closed", "closed-sideways", "book", "laptop", "tent", "flat-sideways", "flat-upright"]
CRITERIA = [f"R{i}" for i in range(1, 8)]


def shots(run_dir):
    """{screen: {pose: path}} for one run's captures (the pose's own panel only)."""
    found = {}
    for png in sorted(run_dir.rglob("*.png")):
        stem = png.stem
        for panel in ("cover", "inner"):
            if stem.endswith("-" + panel):
                stem = stem[: -len(panel) - 1]
                break
        else:
            continue
        pose = max((p for p in POSES if stem.endswith("-" + p)), key=len, default=None)
        if pose:
            found.setdefault(stem[: -len(pose) - 1], {})[pose] = png
    return found


def matrix(paths, out):
    try:
        from PIL import Image
    except ImportError:
        return False
    images = [Image.open(paths[p]).convert("RGB") if p in paths else None for p in POSES]
    height = 480
    scaled = [im.resize((round(im.width * height / im.height), height)) if im else Image.new("RGB", (300, height), "white")
              for im in images]
    gap = 12
    canvas = Image.new("RGB", (sum(im.width for im in scaled) + gap * (len(scaled) - 1), height), "white")
    x = 0
    for im in scaled:
        canvas.paste(im, (x, 0))
        x += im.width + gap
    canvas.save(out)
    return True


def pack(runs_dir, packet, mapping_path):
    runs_dir, packet, mapping_path = map(lambda p: pathlib.Path(p).resolve(), (runs_dir, packet, mapping_path))
    if ROOT in mapping_path.parents:
        sys.exit("the mapping must be written outside the repository")
    if packet.exists() and any(packet.iterdir()):
        sys.exit(f"{packet} is not empty")
    items = []
    for run in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        app, _, condition = run.name.rpartition("-")
        if not app or condition not in ("A", "B"):
            continue
        for screen, poses in shots(run).items():
            items.append({"app": app, "screen": screen, "condition": condition, "poses": poses})
    if not items:
        sys.exit(f"no <app>-A / <app>-B captures under {runs_dir}")
    rng = random.SystemRandom()
    rng.shuffle(items)
    ids = set()
    mapping = {"salt": secrets.token_hex(16), "items": {}}
    rows = []
    for item in items:
        while (iid := secrets.token_hex(3)) in ids:
            pass
        ids.add(iid)
        folder = packet / "items" / iid
        folder.mkdir(parents=True)
        for pose, src in item["poses"].items():
            shutil.copyfile(src, folder / f"{pose}.png")
        matrix(item["poses"], folder / "matrix.png")
        mapping["items"][iid] = {k: item[k] for k in ("app", "screen", "condition")}
        rows += [[iid, item["app"], pose] + [""] * len(CRITERIA) + [""] for pose in POSES]
    with open(packet / "sheet.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item", "app", "pose"] + CRITERIA + ["note"])
        w.writerows(rows)
    shutil.copyfile(AB / "INSTRUCTIONS.md", packet / "INSTRUCTIONS.md")
    data = json.dumps(mapping, indent=2, sort_keys=True).encode()
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    mapping_path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    (AB / "SEAL.txt").write_text(f"sha256 {digest}\nitems {len(items)}\n")
    print(f"{len(items)} items → {packet}; mapping → {mapping_path}; sealed {digest}")


def unseal(mapping_path):
    data = pathlib.Path(mapping_path).read_bytes()
    sealed = (AB / "SEAL.txt").read_text().split()[1]
    if hashlib.sha256(data).hexdigest() != sealed:
        sys.exit("mapping does not match SEAL.txt")
    (AB / "mapping.json").write_bytes(data)
    print("unsealed → verification/ab/mapping.json")


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "pack":
        pack(*sys.argv[2:])
    elif len(sys.argv) == 3 and sys.argv[1] == "unseal":
        unseal(sys.argv[2])
    else:
        sys.exit(__doc__)
