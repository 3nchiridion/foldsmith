#!/usr/bin/env python3
"""Keep .duo/migration.json, the hands-free skill's progress file, which the Foldsmith pane reads.

Every command takes the file's lock, reads it, changes one thing and writes it whole (a temporary file, then a rename),
so the pane never reads half a file and a capture running beside the agent loses none of its writes.

    progress.py init <app> [--simulator UDID]          a new file: phase screens, the seven poses, nothing else
    progress.py phase <screens|audit|classify|migrate|verify|done>
    progress.py screen <name> [--pattern NAME]         add a screen, or set its pattern
    progress.py cell <screen> <pose,…|all|inner> <state> [--label TEXT]
    progress.py shot <before|after> <screen> <pose> <png>   the shot's path on its cell (capture-app.sh calls it)
    progress.py todo <text> | todo --remove <prefix>   what is left, in the order it will be done
    progress.py done <text>                             what is finished; drops todo items that start with <screen>:
    progress.py done --remove <prefix>                  retract done lines that start with <prefix> (a wrong one)
    progress.py check [<screen>…]                       what keeps a screen from done (below), one per line, then the
                                                        open issues; exit 1 if anything keeps one from done, 2 for a
                                                        name that is no screen
    progress.py waive <screen> <pose,…|all|inner> <id> <why>   a detector line the shot does not bear out, and why; the
                                                        id `unchanged` for a fine-as-is cell where only live content
                                                        moved (a toast, content still loading)
    progress.py issue add <screen> <pose,…|all|inner|-> <high|medium|low> <what happens> [--regression]
                [--found-by detector|eye|review|test] [--where <file:line>]
                                                        what review, a look or a test found that no detector
                                                        table shows, on a screen of the file (- for no pose; found
                                                        by review unless said); prints its id
    progress.py issue fix <id> <how>                    the issue is fixed, and how
    progress.py issue wontfix <id> <why>                left as it is, and why (never a regression)
    progress.py log <text>                              one line, timestamped, newest last
    progress.py show                                    the file, summarised

A screen never ends worse than it started, so `done <screen>: …` and `phase done` refuse, changing nothing, while any of
these is left on that screen (on any screen, for `phase done`). A done line names its screens as the pane reads them:
the words before its first ": ", split at commas and "and", each a screen's whole name or its first words, in any case
(`inbox, message: …`, `article and contents from Home: …`); a line with no ": ", or with a part that names no screen
of the file or the before table, is refused too. The checks:
  - a pose the detectors found clean in the before capture that the after capture has a finding in (one not waived on
    its cell), or where no detector ran after (not captured, or no-rotate: neither can be waived);
  - a pose that had findings before where the after capture has a class the before one did not (not waived on its
    cell): T1 T5 before and T14 after is a new problem, not the old one fixed;
  - a cell marked `unchanged` whose before and after accessibility snapshots (the <screen>-<pose>.json the tap runner
    writes beside each shot) differ: every element with a label or an identifier outside scrolling content and not a
    system element (same-screen.py's exclusions), as type, label or identifier, and frame in whole points, the rows
    with an identifier and no label of a list that is itself outside scrolling content (a sidebar's), and the
    window's size. Other rows of lists are not compared. What moves on its own is left out: text that changes only in
    its numbers, in place (a clock, a relative date), the keyboard, and on a map the pins at its edge and the card a
    pin opens. Mark it `verified` if the change is right, or waive `unchanged` on it; a missing or unreadable snapshot
    is noted, not counted;
  - an open issue marked as a regression that names the screen.
The detectors' tables are the detectors.md that capture-app.sh writes in each capture's folder (where most of the cells'
shots are, else .duo/captures/<app>/<before|after>). Without a before table there is nothing to compare them with, and
the check says so.

--file <path> names the file (default: .duo/migration.json under the current directory). Paths stored in the file are
relative to the app's repository, the folder that holds .duo/.
"""
import argparse
import collections
import contextlib
import fcntl
import importlib.util
import json
import math
import os
import pathlib
import re
import sys
import tempfile
import time

POSES = ["closed", "closed-sideways", "book", "laptop", "tent", "flat-sideways", "flat-upright"]
INNER = POSES[2:]
PHASES = ["screens", "audit", "classify", "migrate", "verify", "done"]
STATES = ["pending", "unchanged", "finding", "proposed", "migrated", "verified"]
SEVERITIES = ["high", "medium", "low"]
FOUND_BY = ["detector", "eye", "review", "test"]
NOT_CLASSES = {"·", "n/a", "no-rotate"}   # a table cell's words that are not a class id
LISTS = {"table", "collectionView"}        # whose rows with an identifier and no label are compared (a sidebar's)
CARD = (320, 200)   # pt: the largest card a map pin opens that is left out with it (Wikipedia's: 240 x 116-134)

DETECTORS_FIX = ("Fix it or revert the change for that screen, then capture it again into the after folder "
                 "(SCREEN=<screen>). A line the shot does not bear out: `progress.py waive <screen> <pose> <id> "
                 "\"<why>\"`, and say why in the report. A pose with no detector run after (not captured, or "
                 "no-rotate) is never clean and cannot be waived.")
UNCHANGED_FIX = ("Look at both shots. The change is right: `progress.py cell <screen> <pose> verified`. It is wrong: "
                 "fix it or revert it, and capture again. Only live content moved (a toast, content still loading, a "
                 "feed's rows): `progress.py waive <screen> <pose> unchanged \"<why>\"`.")
ISSUES_FIX = ("Fix each one, or revert the change that caused it, then `progress.py issue fix <id> \"<how>\"`. A "
              "regression is never left as it is.")


@contextlib.contextmanager
def locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path.parent / ".migration.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def load(path):
    if not path.exists():
        sys.exit(f"no progress file at {path}: run `progress.py init <app>` first")
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, m):
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".migration.", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(m, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def screen(m, name):
    for s in m["screens"]:
        if s["name"].casefold() == name.casefold():
            return s
    s = {"name": name, "cells": {}}
    m["screens"].append(s)
    return s


def poses(m, spec):
    if spec == "all":
        return m.get("poses") or POSES
    if spec == "inner":
        return [p for p in (m.get("poses") or POSES) if p in INNER]
    return spec.split(",")


def log(m, text):
    m.setdefault("log", []).append(f"{time.strftime('%H:%M')} {text}")


def captures(m, repo, kind):
    """The folder of the <kind> capture: where most of its cells' shots are, else .duo/captures/<app>/<kind>."""
    folders = collections.Counter(
        (pathlib.Path(c[kind]) if pathlib.Path(c[kind]).is_absolute() else repo / c[kind]).parent
        for s in m["screens"] for c in s["cells"].values() if c.get(kind))
    return folders.most_common(1)[0][0] if folders else repo / ".duo" / "captures" / m.get("app", "") / kind


def table(folder):
    """duo-detect's --markdown table in <folder>: screen (casefolded) → (its name, pose → the cell's words: "·" for
    clean, class ids, "no-rotate" or "n/a"), for the captures in that folder itself; None if there is no table."""
    path = folder / "detectors.md"
    if not path.exists():
        return None
    rows = [[c.strip() for c in line.strip().strip("|").split("|")]
            for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("|")]
    if not rows:
        return {}
    out, prefix = {}, folder.name + "/"
    for row in rows[2:]:
        if row[0].startswith(prefix):
            name = row[0][len(prefix):]
            out[name.casefold()] = (name, dict(zip(rows[0][1:], (c.split() for c in row[1:]))))
    return out


def regressions(m, repo, names=None):
    """From the detectors' tables, one line each: a pose clean in the before capture that the after capture is not
    clean in, and a pose with findings before where the after capture has a class the before one did not, less the
    class ids waived on its cell; names (casefolded) limits it to those screens. None without a before table."""
    before = table(captures(m, repo, "before"))
    if before is None:
        return None
    after = table(captures(m, repo, "after")) or {}
    waived = {s["name"].casefold(): {p: c.get("waived", {}) for p, c in s["cells"].items()} for s in m["screens"]}
    found = []
    for key, (name, cells) in before.items():
        if names is not None and key not in names:
            continue
        for pose, words in cells.items():
            now = after.get(key, (name, {}))[1].get(pose, ["n/a"])
            mine = waived.get(key, {}).get(pose, {})
            if words != ["·"]:
                new = [w for w in now if w not in NOT_CLASSES and w not in words and w not in mine]
                if new and any(w not in NOT_CLASSES for w in words):
                    found.append(f"{name} {pose}: {' '.join(words)} before, {' '.join(now)} after "
                                 f"({' '.join(new)} {'is' if len(new) == 1 else 'are'} new)")
                continue
            if now in ([], ["n/a"]):
                found.append(f"{name} {pose}: clean before, not captured after")
                continue
            if now == ["no-rotate"]:
                found.append(f"{name} {pose}: clean before, no-rotate after (the app kept the other orientation, so "
                             "no detector ran)")
                continue
            left = [w for w in now if w != "·" and w not in mine]
            if left:
                found.append(f"{name} {pose}: clean before, {' '.join(left)} after")
    return found


def same_screen():
    """same-screen.py, whose kept() holds the exclusions it scores screens by, from the copy beside this file; None
    without it."""
    path = pathlib.Path(__file__).resolve().with_name("same-screen.py")
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location("same_screen", path)
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True   # no __pycache__ beside the skill's tools
    spec.loader.exec_module(module)
    return module


def text(value):
    """A label or identifier as text: a snapshot written by hand can hold a number there."""
    return value if isinstance(value, str) else "" if value is None else str(value)


def first_line(label):
    label = text(label)
    return next((line for line in label.splitlines() if line.strip()), label)


def moving(d, ss):
    """The nodes same-screen.py keeps that move without the app's layout changing, by index: the keyboard's own
    controls and the place it holds in the app (identifier inputView), a pin that runs off the map's edge (under
    100 x 100 pt and, cut to the window, wholly on the map: every such pin of Wikipedia's ran off the window's edge),
    and the card a pin opens (no larger than CARD, its label's first line the pin's). Wikipedia's Places and an
    IceCubesApp sheet showed each."""
    nodes = d["nodes"]
    maps = [n["frame"] for n in nodes if n["type"] == "map"]
    width, height = d["window"]
    system, bar = [False] * len(nodes), [False] * len(nodes)
    for i, n in enumerate(nodes):
        parent = n["parent"]
        system[i] = n["type"] in ss.SYSTEM or n.get("identifier") == "inputView" or (parent >= 0 and system[parent])
        bar[i] = parent >= 0 and (bar[parent] or nodes[parent]["type"] in ss.BARS)

    def over(f):
        return any(f[0] < m[0] + m[2] and m[0] < f[0] + f[2] and f[1] < m[1] + m[3] and m[1] < f[1] + f[3]
                   for m in maps)

    def on_map(f):   # cut to the window, wholly on a map (within a point)
        x0, y0 = max(f[0], 0), max(f[1], 0)
        x1, y1 = min(f[0] + f[2], width), min(f[1] + f[3], height)
        return any(x0 >= m[0] - 1 and y0 >= m[1] - 1 and x1 <= m[0] + m[2] + 1 and y1 <= m[1] + m[3] + 1 for m in maps)

    loose = [not bar[i] and n["type"] not in ss.BARS and n["type"] != "map" and over(n["frame"])
             for i, n in enumerate(nodes)] if maps else [False] * len(nodes)
    pins = {i for i, n in enumerate(nodes)
            if loose[i] and n["frame"][2] <= ss.MAP_ITEM and n["frame"][3] <= ss.MAP_ITEM and on_map(n["frame"])}
    pinned = {first_line(nodes[i].get("label")) for i in pins if nodes[i].get("label")}
    return {i for i, n in enumerate(nodes)
            if system[i] or i in pins or (loose[i] and n.get("label") and n["frame"][2] <= CARD[0]
                                          and n["frame"][3] <= CARD[1] and first_line(n["label"]) in pinned)}


def snapshot(repo, shot):
    """The tap runner's snapshot beside a shot: <screen>-<pose>-<cover|inner>.png → <screen>-<pose>.json."""
    png = pathlib.Path(shot) if pathlib.Path(shot).is_absolute() else repo / shot
    return png.with_name(re.sub(r"-(cover|inner)$", "", png.stem) + ".json")


def whole(frame):
    """A frame in whole points; a value a hair under .5 (a frame read as a float) rounds as .5 does."""
    return tuple(math.floor(v + 0.501) for v in frame)


def number(v):
    return f"{round(v, 1):g}"


def quoted(label):
    """A label in a line, quoted: its first line, cut to 40 characters."""
    label = first_line(label)
    return f"\"{label if len(label) <= 40 else label[:39] + '…'}\""


def named(key):
    """(type, label) in a line: "Cancel" button."""
    return f"{quoted(key[1])} {key[0]}"


def layout(d, ss):
    """(type, label or identifier) → the frames, in the snapshot's order, of the elements same-screen.py keeps that
    have a label or an identifier, less those moving() leaves out, and of the rows with an identifier and no label of
    a list it keeps (a sidebar that is a list: IceCubesApp's lost a row and moved the rest up 54 pt). Other rows of
    lists, and elements with neither label nor identifier, are left out."""
    out = collections.defaultdict(list)
    nodes = d["nodes"]
    index = {id(n): i for i, n in enumerate(nodes)}
    skip = moving(d, ss)
    lists = set()
    for n in ss.kept(d):
        name = text(n.get("label")) or text(n.get("identifier"))
        if n["type"] in LISTS:
            lists.add(index[id(n)])
        if name and index[id(n)] not in skip:
            out[(n["type"], name)].append(n["frame"])
    for n in nodes:
        if n["type"] == "cell" and n["parent"] in lists and text(n.get("identifier")) and not text(n.get("label")):
            out[("cell", text(n["identifier"]))].append(n["frame"])
    return out


def same_line(f, g):
    """Two frames of text on the same line: the same top and height in whole points, and the same left edge, right
    edge or centre (within a point), so text aligned any way that only changed its words."""
    return whole(f)[1::2] == whole(g)[1::2] and any(
        abs(x - y) <= 1 for x, y in ((f[0], g[0]), (f[0] + f[2], g[0] + g[2]), (f[0] + f[2] / 2, g[0] + g[2] / 2)))


def live(a, b):
    """Two texts one live value apart: the same once their numbers are masked, or both holding one (9:41 → 10:02,
    "Updated 6 minutes ago" → "Updated 1 hour ago"). A heading renamed ("Inbox" → "Archive") is not."""
    number = re.compile(r"\d+")
    return number.sub("#", a) == number.sub("#", b) or bool(number.search(a) and number.search(b))


def layout_change(before, after, ss):
    """How the two snapshots differ in layout, one phrase per element that differs (the window first, if it does).
    Text that changed only its numbers in place (a clock, a relative date, a count) is live content, not layout."""
    out = []
    wa, wb = [round(v) for v in before["window"]], [round(v) for v in after["window"]]
    if wa != wb:
        out.append(f"the window {wa[0]}x{wa[1]} → {wb[0]}x{wb[1]}")
    a, b = layout(before, ss), layout(after, ss)
    gone, new = [], []
    for key in list(a) + [k for k in b if k not in a]:
        left, right = [], list(b.get(key, []))
        for f in a.get(key, []):
            same = next((g for g in right if whole(g) == whole(f)), None)
            if same is None:
                left.append(f)
            else:
                right.remove(same)
        for f, g in zip(left, right):   # the same element, resized or moved
            if whole(f)[2:] != whole(g)[2:]:
                out.append(f"{named(key)} {number(f[2])}x{number(f[3])} → {number(g[2])}x{number(g[3])}")
            else:
                out.append(f"{named(key)} at {number(f[0])},{number(f[1])} → {number(g[0])},{number(g[1])}")
        paired = min(len(left), len(right))
        gone += [(key, f) for f in left[paired:]]
        new += [(key, g) for g in right[paired:]]
    for key, f in list(gone):
        words = key[0] == "staticText"
        hit = next(((k, g) for k, g in new if k[0] == key[0]
                    and (same_line(f, g) if words else whole(g)[:2] == whole(f)[:2])), None)
        if hit:
            gone.remove((key, f))
            new.remove(hit)
            if not (words and live(key[1], hit[0][1])):   # the same place, other words: a control or heading renamed
                out.append(f"{named(key)} now {quoted(hit[0][1])}")
    return out + [f"{named(k)} gone" for k, _ in gone] + [f"{named(k)} new" for k, _ in new]


def changed_cells(m, repo, names=None):
    """Each cell marked `unchanged`, with a before and an after shot and no `unchanged` waiver, whose two snapshots
    differ in layout: (one line each, notes for the cells with nothing to compare); names (casefolded) limits it."""
    found, notes, ss = [], [], False
    order = {p: i for i, p in enumerate(m.get("poses") or POSES)}
    for s in m["screens"]:
        if names is not None and s["name"].casefold() not in names:
            continue
        for pose, c in sorted(s["cells"].items(), key=lambda pc: order.get(pc[0], len(order))):
            if c.get("state") != "unchanged" or not c.get("before") or not c.get("after") \
                    or "unchanged" in c.get("waived", {}):
                continue
            if ss is False:
                ss = same_screen()
            if ss is None:
                notes.append(f"(no same-screen.py beside {pathlib.Path(__file__).name}: no cell marked fine as is was "
                             "compared)")
                return found, notes
            paths = [snapshot(repo, c[kind]) for kind in ("before", "after")]
            try:
                before, after = (json.loads(p.read_text(encoding="utf-8")) for p in paths)
                differ = layout_change(before, after, ss)
            except FileNotFoundError:
                notes.append(f"({s['name']} {pose}: no snapshot to compare)")
                continue
            except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError) as err:
                notes.append(f"({s['name']} {pose}: snapshot unreadable, not compared: {err})")
                continue
            if differ:
                found.append(f"{s['name']} {pose}: fine as is, but the screen changed ({len(differ)} "
                             f"{'element differs' if len(differ) == 1 else 'elements differ'}, e.g. {differ[0]})")
    return found, notes


def issues_of(m):
    """The file's issues, those written by hand too: a list of entries, each a dict (a missing list is empty)."""
    return [i for i in m.get("issues") or [] if isinstance(i, dict)]


def open_issues(m, names=None):
    """The open issues, regressions first (an entry with no status is open); names (casefolded) limits them to those
    screens."""
    out = [i for i in issues_of(m) if i.get("status", "open") == "open"
           and (names is None or text(i.get("screen")).casefold() in names)]
    return sorted(out, key=lambda i: not i.get("regression"))


def issue_line(m, i):
    every, at = m.get("poses") or POSES, i.get("poses") or []
    where = ("" if not at else " all" if at == every
             else " inner" if at == [p for p in every if p in INNER] else " " + " ".join(map(text, at)))
    about = ", ".join([text(i.get("severity")) or "no severity", f"found by {text(i.get('found_by')) or 'review'}"]
                      + ([text(i["where"])] if i.get("where") else []))
    kind = "regression" if i.get("regression") else "issue"
    ident, name = text(i.get("id")) or "(no id)", text(i.get("screen"))
    return f"{ident} {name}{where}: open {kind} ({about}): {text(i.get('what'))}"


def issue(m, ident):
    for i in issues_of(m):
        if text(i.get("id")).casefold() == ident.casefold():
            return i
    sys.exit(f"no issue {ident}: `progress.py check` lists the open ones")


def known(m, repo):
    """The screens a line may name, casefolded → as written: the file's, then the before table's."""
    out = {name.casefold(): name for name, _ in (table(captures(m, repo, "before")) or {}).values()}
    out.update({s["name"].casefold(): s["name"] for s in m["screens"]})
    return out


def done_screens(m, repo, line):
    """The screens a done line names, casefolded, read as the pane reads them: the words before its first ": ", split
    at commas and "and", each a screen's whole name or its first words, in any case. Exits, changing nothing, for a
    line with no ": " or a part that names no screen."""
    names = known(m, repo)
    listed = ", ".join(sorted(names.values())) or "none yet"
    head, colon, _ = line.partition(": ")
    if not colon:
        sys.exit(f"done refused, nothing changed: a done line is `<screen>: <what is finished>` (`<screen>, <screen>: "
                 f"…` for several). Screens: {listed}.")
    if head.strip().casefold() in names:
        return {head.strip().casefold()}
    found, unknown = set(), []
    for part in re.split(r",\s*|\s+and\s+", head):
        words = part.strip().casefold()
        hits = {n for n in names if words == n or words.startswith(n + " ")}
        if words and not hits:
            unknown.append(part.strip())
        found |= hits
    if unknown or not found:
        parts = ", ".join(f'"{u}"' for u in unknown or [head.strip()])
        sys.exit(f"done refused, nothing changed: {parts} names no screen. Screens: {listed}. A line about something "
                 "other than a screen goes in the log (`progress.py log`).")
    return found


def refuse(m, repo, names, what):
    """Exit, changing nothing, while anything keeps the named screens (every screen, for None) from done."""
    found = regressions(m, repo, names)
    changed, notes = changed_cells(m, repo, names)
    issues = [issue_line(m, i) for i in open_issues(m, names) if i.get("regression")]
    if found is None:
        print(f"no detector table in {captures(m, repo, 'before')}: the detectors' findings are not compared",
              file=sys.stderr)
    for note in notes:
        print(note, file=sys.stderr)
    parts = []
    if found:
        parts.append("Worse than before where the detectors look:\n  " + "\n  ".join(found) + "\n" + DETECTORS_FIX)
    if changed:
        parts.append("Marked fine as is, but the screen changed:\n  " + "\n  ".join(changed) + "\n" + UNCHANGED_FIX)
    if issues:
        parts.append("Open regressions:\n  " + "\n  ".join(issues) + "\n" + ISSUES_FIX)
    if parts:
        sys.exit(f"{what} refused, nothing changed.\n" + "\n".join(parts))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", type=pathlib.Path, default=pathlib.Path(".duo/migration.json"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("app"); p.add_argument("--simulator")
    p = sub.add_parser("phase"); p.add_argument("phase", choices=PHASES)
    p = sub.add_parser("screen"); p.add_argument("name"); p.add_argument("--pattern")
    p = sub.add_parser("cell"); p.add_argument("screen"); p.add_argument("poses"); p.add_argument("state", choices=STATES)
    p.add_argument("--label")
    p = sub.add_parser("shot"); p.add_argument("kind", choices=["before", "after"]); p.add_argument("screen")
    p.add_argument("pose"); p.add_argument("png", type=pathlib.Path)
    p = sub.add_parser("todo"); p.add_argument("text"); p.add_argument("--remove", action="store_true")
    p = sub.add_parser("done"); p.add_argument("text"); p.add_argument("--remove", action="store_true")
    p = sub.add_parser("check"); p.add_argument("screens", nargs="*")
    p = sub.add_parser("waive"); p.add_argument("screen"); p.add_argument("poses"); p.add_argument("id")
    p.add_argument("why")
    p = sub.add_parser("issue")
    act = p.add_subparsers(dest="action", required=True)
    q = act.add_parser("add"); q.add_argument("screen"); q.add_argument("poses")
    q.add_argument("severity", choices=SEVERITIES); q.add_argument("what")
    q.add_argument("--regression", action="store_true")
    q.add_argument("--found-by", choices=FOUND_BY, default="review"); q.add_argument("--where")
    q = act.add_parser("fix"); q.add_argument("id"); q.add_argument("note")
    q = act.add_parser("wontfix"); q.add_argument("id"); q.add_argument("note")
    p = sub.add_parser("log"); p.add_argument("text")
    sub.add_parser("show")
    a = ap.parse_args()
    path = a.file.resolve()
    repo = path.parent.parent

    with locked(path):
        if a.cmd == "init":
            if path.exists():
                sys.exit(f"{path} exists: resume from it")
            m = {"app": a.app, "phase": "screens", "poses": POSES, "screens": [], "done": [], "todo": [], "log": []}
            if a.simulator:
                m["simulator"] = a.simulator
            log(m, f"started {a.app}")
            save(path, m)
            return
        m = load(path)
        if a.cmd == "show":
            issues = open_issues(m)
            held = sum(1 for i in issues if i.get("regression"))
            print(f"{m.get('app')}: {m['phase']}, {len(m['screens'])} screens, {len(m.get('done', []))} done, "
                  f"{len(m.get('todo', []))} left, {len(issues)} open issue{'' if len(issues) == 1 else 's'}"
                  + (f" ({held} regression{'' if held == 1 else 's'})" if held else ""))
            for s in m["screens"]:
                cells = " ".join(f"{p}={s['cells'].get(p, {}).get('state', 'pending')}" for p in m.get("poses") or POSES)
                print(f"  {s['name']} ({s.get('pattern', 'no pattern')}): {cells}")
            return
        if a.cmd == "check":
            names = {n.casefold() for n in a.screens} if a.screens else None
            names_known = known(m, repo)
            unknown = [n for n in a.screens if n.casefold() not in names_known]
            if unknown:
                print(f"no screen named {', '.join(unknown)}: screens are "
                      f"{', '.join(sorted(names_known.values())) or 'none yet'}", file=sys.stderr)
                sys.exit(2)
            found = regressions(m, repo, names)
            changed, notes = changed_cells(m, repo, names)
            issues = open_issues(m, names)
            if found is None:
                print(f"no detector table in {captures(m, repo, 'before')}: the detectors' findings are not compared")
            lines = (found or []) + changed
            held = bool(lines) or any(i.get("regression") for i in issues)
            if not held:
                print("no regressions")
            for line in lines + [issue_line(m, i) for i in issues]:
                print(line)
            for note in notes:
                print(note, file=sys.stderr)
            sys.exit(1 if held else 0)
        if a.cmd == "phase":
            if a.phase == "done":
                refuse(m, repo, None, "phase done")
            m["phase"] = a.phase
            log(m, f"phase {a.phase}")
        elif a.cmd == "screen":
            s = screen(m, a.name)
            if a.pattern:
                s["pattern"] = a.pattern
        elif a.cmd == "cell":
            s = screen(m, a.screen)
            for pose in poses(m, a.poses):
                cell = s["cells"].setdefault(pose, {})
                cell["state"] = a.state
                if a.label:
                    cell["label"] = a.label
                elif a.state in ("unchanged", "pending"):
                    cell.pop("label", None)
        elif a.cmd == "shot":
            png = a.png.resolve()
            rel = png.relative_to(repo).as_posix() if png.is_relative_to(repo) else str(png)
            cell = screen(m, a.screen)["cells"].setdefault(a.pose, {"state": "pending"})
            cell[a.kind] = rel
            log(m, f"{a.kind} shot {a.screen} / {a.pose}")
        elif a.cmd == "todo":
            todo = m.setdefault("todo", [])
            if a.remove:
                m["todo"] = [t for t in todo if not t.startswith(a.text)]
            elif a.text not in todo:
                todo.append(a.text)
        elif a.cmd == "done" and a.remove:
            m["done"] = [t for t in m.get("done", []) if not t.startswith(a.text)]
            log(m, f"retracted done {a.text}")
        elif a.cmd == "done":
            name = a.text.partition(": ")[0]
            refuse(m, repo, done_screens(m, repo, a.text), f"done {name}")
            done = m.setdefault("done", [])
            if a.text not in done:
                done.append(a.text)
            m["todo"] = [t for t in m.get("todo", []) if not t.startswith(name + ":")]
            log(m, f"done {a.text}")
        elif a.cmd == "waive":
            if not a.why.strip():
                sys.exit("waive needs the reason the shot does not bear the line out")
            s = screen(m, a.screen)
            for pose in poses(m, a.poses):
                s["cells"].setdefault(pose, {"state": "pending"}).setdefault("waived", {})[a.id] = a.why
            log(m, f"waived {a.id} on {a.screen} / {a.poses}: {a.why}")
        elif a.cmd == "issue" and a.action == "add":
            if not a.what.strip():
                sys.exit("issue add needs what happens")
            every = m.get("poses") or POSES
            where = [] if a.poses == "-" else poses(m, a.poses)
            unknown = [p for p in where if p not in every]
            if unknown:
                sys.exit(f"no pose {', '.join(unknown)}: name poses from {', '.join(every)}, or all, inner or -")
            names = known(m, repo)
            if names and a.screen.casefold() not in names:
                sys.exit(f"no screen named {a.screen}, nothing changed: screens are "
                         f"{', '.join(sorted(names.values()))}. A screen the flows do not reach: `progress.py screen "
                         "<name>` first.")
            name = names.get(a.screen.casefold(), a.screen)
            if not isinstance(m.get("issues"), list):
                m["issues"] = []
            issues = m["issues"]
            n = max([int(i["id"][1:]) for i in issues_of(m) if re.fullmatch(r"I\d+", text(i.get("id")))] + [0]) + 1
            entry = {"id": f"I{n}", "screen": name, "poses": list(where), "severity": a.severity,
                     "regression": a.regression, "found_by": a.found_by, "what": a.what}
            if a.where:
                entry["where"] = a.where
            entry["status"] = "open"
            issues.append(entry)
            log(m, f"issue I{n} {name}{' ' + a.poses if where else ''}: {a.severity}"
                   f"{' regression' if a.regression else ''}, {a.what}")
            print(f"I{n}")
        elif a.cmd == "issue":
            i = issue(m, a.id)
            if not a.note.strip():
                sys.exit(f"issue {a.action} needs {'how it was fixed' if a.action == 'fix' else 'why it stays'}")
            if a.action == "wontfix" and i.get("regression"):
                sys.exit(f"{i['id']} is a regression, so it is never left as it is: fix it, or revert the change that "
                         f"caused it, then `progress.py issue fix {i['id']} \"<how>\"`. Nothing changed.")
            i["status"] = "fixed" if a.action == "fix" else "wontfix"
            i["note"] = a.note
            log(m, f"issue {i['id']} {i['status']}: {a.note}")
        elif a.cmd == "log":
            log(m, a.text)
        save(path, m)


if __name__ == "__main__":
    main()
