#!/usr/bin/env python3
"""Pixelate other people's content in captured shots, from the accessibility snapshot taken with each shot.

    python3 scripts/redact-shots.py <capture-dir> <screen> [<screen> ...]

For every `<screen>-<pose>-<panel>.png` in <capture-dir> with its `<screen>-<pose>.json` (capture-corpus-flow.sh with
SNAPSHOT=1), the shot is overwritten with these regions pixelated in 12 pt blocks:
- the visible area of every scrolling container (a timeline's posts, avatars, names and photos: a timeline's rows are
  buttons as often as text, so the whole area goes rather than chosen leaves);
- while a sheet is up, everything outside the sheet (what is dimmed behind it may be missing from the tree).
Every image inside a scrolling container then becomes one flat block of its average colour (12 pt blocks still leave
a large photo's faces several blocks wide), except where the keyboard covers it. Then the system's bars are put back as shot: navigation bars, tab bars and every item inside a bar, so bar placement
(R5) can still be judged. Layout stays readable as blocks; words and faces do not. Used for the apps whose screens show strangers' posts
(IceCubesApp's timelines), the same way for every capture of that app, so no condition is treated differently.
A shot whose size does not match its snapshot's window (the app did not rotate) is pixelated whole, and reported.
"""
import json
import pathlib
import sys

from PIL import Image

SCROLLING = {"scrollView", "table", "collectionView", "webView", "textView"}
BARS = {"navigationBar", "toolbar", "tabBar"}
ITEMS = {"button", "staticText", "image", "icon", "popUpButton", "menuButton", "searchField", "segmentedControl", "tab"}
POSES = ["closed", "closed-sideways", "book", "laptop", "tent", "flat-sideways", "flat-upright"]
BLOCK_PT = 12   # pixel block size, in points


def intersect(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    return (x0, y0, x1 - x0, y1 - y0) if x1 > x0 and y1 > y0 else None


def regions(snapshot):
    """(regions to pixelate, images to flatten, keyboard, regions to put back), in window points as (x, y, w, h)."""
    nodes = snapshot["nodes"]
    window = snapshot["window"]
    children = {}
    for i, n in enumerate(nodes):
        children.setdefault(n["parent"], []).append(i)
    sheet = None
    for i, n in enumerate(nodes):
        if n.get("identifier") == "PopoverDismissRegion":
            later = [j for j in children.get(n["parent"], []) if j > i]
            if later and nodes[later[0]]["frame"][2] < window[0] - 1:
                sheet = nodes[later[0]]["frame"]
    out = []
    if sheet:
        x, y, w, h = sheet
        W, H = window
        out += [(0, 0, x, H), (x + w, 0, W - x - w, H), (x, 0, w, y), (x, y + h, w, H - y - h)]
    keep, flat, keyboard = [], [], []
    in_scroll, in_bar = [False] * len(nodes), [False] * len(nodes)
    root = [None] * len(nodes)   # the top-level scrolling container a node is in
    cell = [None] * len(nodes)   # the list cell a node is in: it clips (an aspect-fill photo overhangs it)
    for i, n in enumerate(nodes):
        p = n["parent"]
        if p >= 0:
            cell[i] = p if nodes[p]["type"] == "cell" else cell[p]
            in_scroll[i] = in_scroll[p] or nodes[p]["type"] in SCROLLING
            root[i] = root[p] if root[p] is not None else (p if nodes[p]["type"] in SCROLLING else None)
            # as AccessibilitySnapshot.swift: a bar's items are under it with no scrolling container in between
            # (SwiftUI hosts a whole column inside a window-sized toolbar)
            in_bar[i] = nodes[p]["type"] not in SCROLLING and (in_bar[p] or nodes[p]["type"] in BARS)
        x, y, w, h = n["frame"]
        if n["type"] in SCROLLING and not in_scroll[i]:
            out.append((x, y, w, h))
        elif n["type"] in ("navigationBar", "tabBar") and min(w, h) <= 150:
            keep.append((x, y, w, h))
        elif in_bar[i] and n["type"] in ITEMS:
            keep.append((x, y, w, h))
        if n["type"] == "keyboard" or n.get("identifier") == "inputView":
            keyboard.append((x, y, w, h))   # drawn over the app: what an image's frame has under it is not the image
        if n["type"] in ("image", "icon") and root[i] is not None:
            part = intersect((x, y, w, h), nodes[root[i]]["frame"])
            if part and cell[i] is not None:
                part = intersect(part, nodes[cell[i]]["frame"])
            if part:
                flat.append(part)
    return out, flat, keyboard, keep


def flatten(img, box):
    box = tuple(int(round(v)) for v in box)
    x0, y0, x1, y1 = max(0, box[0]), max(0, box[1]), min(img.width, box[2]), min(img.height, box[3])
    if x1 - x0 < 1 or y1 - y0 < 1:
        return
    img.paste(img.crop((x0, y0, x1, y1)).resize((1, 1), Image.BOX).getpixel((0, 0)), (x0, y0, x1, y1))


def pixelate(img, box):
    box = tuple(int(round(v)) for v in box)
    x0, y0, x1, y1 = max(0, box[0]), max(0, box[1]), min(img.width, box[2]), min(img.height, box[3])
    if x1 - x0 < 2 or y1 - y0 < 2:
        return
    part = img.crop((x0, y0, x1, y1))
    block = max(2, int(BLOCK_PT * img.width / max(1, img.info.get("window_w", img.width))))
    small = part.resize((max(1, part.width // block), max(1, part.height // block)), Image.BILINEAR)
    img.paste(small.resize(part.size, Image.NEAREST), (x0, y0))


def main(directory, screens):
    directory = pathlib.Path(directory)
    done = 0
    for screen in screens:
        for pose in POSES:
            snap = directory / f"{screen}-{pose}.json"
            shots = [p for p in directory.glob(f"{screen}-{pose}-*.png")
                     if p.stem[len(screen) + len(pose) + 2:] in ("cover", "inner")]
            for shot in shots:
                img = Image.open(shot).convert("RGB")
                if not snap.exists():
                    print(f"{shot.name}: no snapshot, pixelated whole")
                    img.info["window_w"] = img.width / 3
                    pixelate(img, (0, 0, img.width, img.height))
                    img.save(shot)
                    continue
                s = json.loads(snap.read_text())
                sx, sy = img.width / s["window"][0], img.height / s["window"][1]
                img.info["window_w"] = s["window"][0]
                if abs(sx - sy) / sx > 0.02:
                    print(f"{shot.name}: {img.width}×{img.height} px is not the window {s['window']}, pixelated whole")
                    pixelate(img, (0, 0, img.width, img.height))
                else:
                    original = img.copy()
                    hide, flat, keyboard, keep = regions(s)
                    for x, y, w, h in hide:
                        pixelate(img, (x * sx, y * sy, (x + w) * sx, (y + h) * sy))
                    pixelated = img.copy()
                    for x, y, w, h in flat:
                        flatten(img, (x * sx, y * sy, (x + w) * sx, (y + h) * sy))
                    for source, regions_ in ((pixelated, keyboard), (original, keep)):
                        for x, y, w, h in regions_:
                            box = tuple(int(round(v)) for v in (max(0, x) * sx, max(0, y) * sy, (x + w) * sx, (y + h) * sy))
                            box = (box[0], box[1], min(img.width, box[2]), min(img.height, box[3]))
                            if box[2] - box[0] > 1 and box[3] - box[1] > 1:
                                img.paste(source.crop(box), box[:2])
                img.save(shot)
                done += 1
    print(f"redacted {done} shots in {directory}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2:])
