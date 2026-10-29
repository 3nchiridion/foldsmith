#!/usr/bin/env python3
"""Whether two accessibility snapshots from the tap runner show the same screen: the shut phone on its way to a pose
against the shut phone right after the taps (capture-corpus-flow.sh asks before every inner pose).

What scrolls is left out (rows come and go, and the runner keeps no label there), and so is what lies on a map: its
place names, and the pins and cluster counts an app draws in a layer of its own over it (anything under 100 x 100 pt
wholly inside the map, outside the bars), which come in after the taps and change as it loads. Wikipedia's Places
scored 0.33-0.35 against itself without this and 0.75-0.83 with it, and still at most 0.56 against its other screens.
What stays is the bars, titles and buttons around it, as a multiset of element type and label or identifier. The score is their Jaccard similarity, 0 if
the windows differ in size. Prints the score; exit 0 at or above the threshold, 1 below it, 2 when a file is unreadable.
On NetNewsWire's captures two different screens score 0.14–0.28 and one screen 0.82–1.00, even across builds; the
default threshold sits between.

    same-screen.py <ref.json> <now.json> [--threshold 0.6]
"""
import collections
import json
import sys

SCROLLING = {"scrollView", "table", "collectionView", "webView", "textView", "map"}
SYSTEM = {"statusBar", "keyboard", "key"}
BARS = {"navigationBar", "toolbar", "tabBar"}
MAP_ITEM = 100   # pt: the largest thing that lies on a map (a pin, a count, a label) rather than over it


def signature(path):
    d = json.load(open(path))
    nodes = d["nodes"]
    maps = [n["frame"] for n in nodes if n["type"] == "map"]

    def on_map(f):
        return f[2] <= MAP_ITEM and f[3] <= MAP_ITEM and any(
            f[0] >= m[0] - 1 and f[1] >= m[1] - 1 and f[0] + f[2] <= m[0] + m[2] + 1 and f[1] + f[3] <= m[1] + m[3] + 1
            for m in maps)

    inside = [False] * len(nodes)
    in_bar = [False] * len(nodes)
    sig = collections.Counter()
    for i, n in enumerate(nodes):
        parent = n["parent"]
        in_bar[i] = parent >= 0 and (in_bar[parent] or nodes[parent]["type"] in BARS)
        inside[i] = parent >= 0 and (inside[parent] or nodes[parent]["type"] in SCROLLING)
        inside[i] = inside[i] or (not in_bar[i] and n["type"] not in BARS and n["type"] != "map" and on_map(n["frame"]))
        name = n.get("label") or n.get("identifier")
        if name and not inside[i] and n["type"] not in SYSTEM:
            sig[(n["type"], name)] += 1
    return [round(v) for v in d["window"]], sig


def main():
    args = sys.argv[1:]
    threshold = 0.6
    if "--threshold" in args:
        at = args.index("--threshold")
        threshold = float(args[at + 1])
        del args[at:at + 2]
    if len(args) != 2:
        sys.exit(__doc__)
    try:
        (w1, a), (w2, b) = signature(args[0]), signature(args[1])
    except (OSError, ValueError, KeyError) as err:
        print(f"unreadable: {err}")
        sys.exit(2)
    union = sum((a | b).values())
    score = 0.0 if w1 != w2 else 1.0 if union == 0 else sum((a & b).values()) / union
    print(f"{score:.2f}")
    sys.exit(0 if score >= threshold else 1)


if __name__ == "__main__":
    main()
