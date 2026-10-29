#!/usr/bin/env python3
"""Compose the pose matrix for each pattern: verification/matrices/<pattern>.png.

Rows are the catalog configs captured for the pattern (the reference variant first), columns the seven poses. Every
cell is the shot scripts/capture-catalog.sh saved, scaled to fit, with the division the app reported drawn over it:
a red band while active, a dashed outline while inactive. Nothing is hand-placed; rerun after every capture.

    python3 scripts/compose-matrix.py [verification/matrices]
"""
import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

POSES = ["closed", "closed-sideways", "book", "laptop", "tent", "flat-sideways", "flat-upright"]
CELL = 240          # longest side of a shot in the matrix, px
PAD, LABEL_W, HEAD_H = 12, 150, 34


def font(size):
    for path in ["/System/Library/Fonts/SFNS.ttf", "/System/Library/Fonts/Helvetica.ttc"]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def pose_of(stem):
    matches = [p for p in POSES if stem.endswith("-" + p)]
    return max(matches, key=len) if matches else None   # "closed-sideways" before "closed"... and "sideways"


def configs(folder):
    stems = {p.stem[: -len(pose) - 1] for p in folder.glob("*.png") if (pose := pose_of(p.stem))}
    return sorted(stems, key=lambda s: (not s.startswith("aligned"), s))


def cell(png, frames):
    shot = Image.open(png).convert("RGB")
    scale = CELL / max(shot.size)
    shot = shot.resize((round(shot.width * scale), round(shot.height * scale)), Image.LANCZOS)
    if frames.exists():
        d = json.loads(frames.read_text())
        overlay = Image.new("RGBA", shot.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        # frames are in points and the shot is at point scale (1 px = 1 pt) before this resize
        k = shot.width / d["window"][0] if d["window"][0] else scale
        for r in d["divisions"]:
            box = [r["x"] * k, r["y"] * k, (r["x"] + r["w"]) * k, (r["y"] + r["h"]) * k]
            if r["isActive"]:
                draw.rectangle(box, fill=(230, 40, 40, 70), outline=(230, 40, 40, 200))
            else:
                x0, y0, x1, y1 = box
                for i in range(0, int(max(x1 - x0, y1 - y0)), 8):
                    if y1 - y0 > x1 - x0:
                        draw.line([(x0, y0 + i), (x0, y0 + i + 4)], fill=(230, 40, 40, 200))
                        draw.line([(x1, y0 + i), (x1, y0 + i + 4)], fill=(230, 40, 40, 200))
                    else:
                        draw.line([(x0 + i, y0), (x0 + i + 4, y0)], fill=(230, 40, 40, 200))
                        draw.line([(x0 + i, y1), (x0 + i + 4, y1)], fill=(230, 40, 40, 200))
        shot = Image.alpha_composite(shot.convert("RGBA"), overlay).convert("RGB")
    return shot


def compose(folder):
    rows = configs(folder)
    if not rows:
        return None
    W = LABEL_W + len(POSES) * (CELL + PAD) + PAD
    H = HEAD_H + len(rows) * (CELL + PAD) + PAD
    out = Image.new("RGB", (W, H), (246, 246, 246))
    draw = ImageDraw.Draw(out)
    f, fb = font(15), font(17)
    for j, pose in enumerate(POSES):
        draw.text((LABEL_W + j * (CELL + PAD) + CELL / 2, HEAD_H / 2), pose, fill=(40, 40, 40), font=fb, anchor="mm")
    for i, row in enumerate(rows):
        y = HEAD_H + i * (CELL + PAD)
        draw.text((PAD, y + CELL / 2), row, fill=(40, 40, 40), font=fb, anchor="lm")
        for j, pose in enumerate(POSES):
            png = folder / f"{row}-{pose}.png"
            x = LABEL_W + j * (CELL + PAD)
            if not png.exists():
                draw.text((x + CELL / 2, y + CELL / 2), "no shot", fill=(160, 60, 60), font=f, anchor="mm")
                continue
            c = cell(png, folder / f"{row}-{pose}.json")
            out.paste(c, (x + (CELL - c.width) // 2, y + (CELL - c.height) // 2))
    target = folder.parent / f"{folder.name}.png"
    out.save(target, optimize=True)
    return target


if __name__ == "__main__":
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "verification/matrices")
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        target = compose(folder)
        if target:
            print(target)
