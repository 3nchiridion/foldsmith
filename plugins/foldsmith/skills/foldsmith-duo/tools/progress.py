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
    progress.py check [<screen>…]                       the regressions below, one per line; exit 1 if there are any
    progress.py waive <screen> <pose,…|all|inner> <id> <why>   a detector line the shot does not bear out, and why
    progress.py log <text>                              one line, timestamped, newest last
    progress.py show                                    the file, summarised

A screen never ends worse than it started, so `done <screen>: …` (or `<screen>, <screen>: …`) and `phase done` refuse,
changing nothing, while a regression is left: a pose the detectors found clean in the before capture that the after
capture has a finding in (one not waived on its cell), or where no detector ran after (not captured, or no-rotate:
neither can be waived). The detectors' tables are the detectors.md that capture-app.sh writes in each capture's folder
(where most of the cells' shots are, else .duo/captures/<app>/<before|after>). Without a before table there is nothing
to compare, and the check says so.

--file <path> names the file (default: .duo/migration.json under the current directory). Paths stored in the file are
relative to the app's repository, the folder that holds .duo/.
"""
import argparse
import collections
import contextlib
import fcntl
import json
import os
import pathlib
import sys
import tempfile
import time

POSES = ["closed", "closed-sideways", "book", "laptop", "tent", "flat-sideways", "flat-upright"]
INNER = POSES[2:]
PHASES = ["screens", "audit", "classify", "migrate", "verify", "done"]
STATES = ["pending", "unchanged", "finding", "proposed", "migrated", "verified"]


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
    """Each pose clean in the before capture's detector table that the after capture's is not clean in, less the class
    ids waived on its cell, one line each; names (casefolded) limits it to those screens. None without a before table."""
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
            if words != ["·"]:
                continue
            now = after.get(key, (name, {}))[1].get(pose, ["n/a"])
            if now in ([], ["n/a"]):
                found.append(f"{name} {pose}: clean before, not captured after")
                continue
            if now == ["no-rotate"]:
                found.append(f"{name} {pose}: clean before, no-rotate after (the app kept the other orientation, so "
                             "no detector ran)")
                continue
            left = [w for w in now if w != "·" and w not in waived.get(key, {}).get(pose, {})]
            if left:
                found.append(f"{name} {pose}: clean before, {' '.join(left)} after")
    return found


def refuse_regressions(m, repo, names, what):
    found = regressions(m, repo, names)
    if found is None:
        print(f"no detector table in {captures(m, repo, 'before')}: no regression check", file=sys.stderr)
    elif found:
        sys.exit(f"{what} refused, nothing changed: worse than before in a pose the detectors found clean\n  "
                 + "\n  ".join(found) + "\nFix it or revert the change for that screen, then capture it again into "
                 "the after folder (SCREEN=<screen>). A line the shot does not bear out: `progress.py waive <screen> "
                 "<pose> <id> \"<why>\"`, and say why in the report. A pose with no detector run after (not captured, or "
                 "no-rotate) is never clean and cannot be waived.")


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
            print(f"{m.get('app')}: {m['phase']}, {len(m['screens'])} screens, {len(m.get('done', []))} done, "
                  f"{len(m.get('todo', []))} left")
            for s in m["screens"]:
                cells = " ".join(f"{p}={s['cells'].get(p, {}).get('state', 'pending')}" for p in m.get("poses") or POSES)
                print(f"  {s['name']} ({s.get('pattern', 'no pattern')}): {cells}")
            return
        if a.cmd == "check":
            found = regressions(m, repo, {n.casefold() for n in a.screens} if a.screens else None)
            if found is None:
                print(f"no detector table in {captures(m, repo, 'before')}: nothing to compare")
            else:
                print("\n".join(found) if found else "no regressions")
            sys.exit(1 if found else 0)
        if a.cmd == "phase":
            if a.phase == "done":
                refuse_regressions(m, repo, None, "phase done")
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
            named = {n.strip().casefold() for n in a.text.split(":", 1)[0].split(",")}
            refuse_regressions(m, repo, named, f"done {a.text.split(':', 1)[0]}")
            done = m.setdefault("done", [])
            if a.text not in done:
                done.append(a.text)
            name = a.text.split(":", 1)[0]
            m["todo"] = [t for t in m.get("todo", []) if not t.startswith(name + ":")]
            log(m, f"done {a.text}")
        elif a.cmd == "waive":
            if not a.why.strip():
                sys.exit("waive needs the reason the shot does not bear the line out")
            s = screen(m, a.screen)
            for pose in poses(m, a.poses):
                s["cells"].setdefault(pose, {"state": "pending"}).setdefault("waived", {})[a.id] = a.why
            log(m, f"waived {a.id} on {a.screen} / {a.poses}: {a.why}")
        elif a.cmd == "log":
            log(m, a.text)
        save(path, m)


if __name__ == "__main__":
    main()
