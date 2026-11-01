#!/usr/bin/env python3
"""The App Store's iPhone Duo screenshots, from the shots a capture already took. It never uploads anything.

    python3 appstore.py [--file .duo/migration.json] [--out .duo/appstore] [--kind after|before]

Apple's sizes. App Store Connect Help, "Screenshot specifications", the iPhone Duo row (read 2026-10-31):
https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/
lists 1398 x 2034 and 2034 x 1398 pixels for the outer display, 2007 x 2853 and 2853 x 2007 for the inner one; from
April 2027 they are required for any app built with the iOS 27.1 SDK or later. For every display size the same page
takes 1 to 10 screenshots, .jpeg, .jpg or .png, and no alpha channel or transparency. The captures are exactly those
sizes (the simulator's 3x of the window in points), so nothing is resized:
  outer-portrait    1398 x 2034   closed                       (466 x 678 pt)
  outer-landscape   2034 x 1398   closed-sideways              (678 x 466 pt)
  inner-portrait    2007 x 2853   flat-upright, else laptop    (669 x 951 pt)
  inner-landscape   2853 x 2007   book, else flat-sideways     (951 x 669 pt)
A shot of any other size is refused with the size it has, never resized: it is the wrong panel or the wrong turn.

Per screen of the progress file, one shot for each of the four, from the first pose in that list whose cell passes:
  - its state is verified or unchanged; with --kind before, unchanged only (a verified cell's before shot is the
    layout that was fixed);
  - it has a <kind> shot, and the file is there;
  - the <kind> capture's detector table (detectors.md in that capture's folder) reads clean for the screen in that
    pose: any class id, waived on the cell or not, and no-rotate or n/a refuse it, and so does a missing table;
  - no open issue of the progress file names the screen in that pose;
  - the shot is the size above.
The captures are PNGs with an alpha channel. Each one kept is flattened with macOS's sips into a JPEG at its best
quality (transparent pixels land on white), and the JPEG is read back: no alpha channel and the same size, or it is
removed and refused.

Writes <out>/<size>/NN-<screen>-<pose>.jpg, numbered in the progress file's screen order, and <out>/README.md, which
lists every file, every cell not used and why, and tells the person to check each image for personal content and the
status bar before uploading. A run replaces the files an earlier run wrote there (NN-*.jpg in those four folders, and a
README.md whose first line is this script's heading) and leaves anything else; a README.md there that it did not
write stops it (exit 2) before anything is removed. An <out> that is the app's folder, the repository's top or a
folder above either, or the folder that holds the progress file, is refused. The output stays out of git: an <out>
inside the repository goes into .git/info/exclude, as its path from the repository's top (an app in a subfolder of a
larger repository too), written as a literal pattern.

A shot's path comes from the progress file, which comes with the repository: one that leads outside the repository
(an absolute path elsewhere, or "..") is refused, never read.

Exit 0 when at least one file was written, 1 when none could be (each refusal printed), 2 for a usage error, no sips,
an <out> refused, or a README.md there that this script did not write.
"""
import argparse
import datetime
import importlib.util
import json
import pathlib
import re
import shutil
import subprocess
import sys

SIZES = [   # (folder, display, orientation, (width, height), poses in order of preference)
    ("outer-portrait", "outer display", "portrait", (1398, 2034), ["closed"]),
    ("outer-landscape", "outer display", "landscape", (2034, 1398), ["closed-sideways"]),
    ("inner-portrait", "inner display", "portrait", (2007, 2853), ["flat-upright", "laptop"]),
    ("inner-landscape", "inner display", "landscape", (2853, 2007), ["book", "flat-sideways"]),
]
MOST = 10   # per display size, App Store Connect's limit
OURS = re.compile(r"^\d+-.+\.jpg$")
HEADING = "# App Store screenshots for iPhone Duo"   # the first line of the README.md it writes, and how it knows its own


def progress():
    """progress.py beside this file, for the progress file's capture folders and detector tables."""
    path = pathlib.Path(__file__).resolve().with_name("progress.py")
    spec = importlib.util.spec_from_file_location("foldsmith_progress", path)
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True   # no __pycache__ beside the skill's tools
    spec.loader.exec_module(module)
    return module


def sips_props(path, *keys):
    """sips's answer for each key (pixelWidth, hasAlpha, …), as text; {} if sips cannot read the file."""
    args = ["sips"]
    for k in keys:
        args += ["-g", k]
    r = subprocess.run(args + [str(path)], capture_output=True, text=True)
    if r.returncode != 0:
        return {}
    out = {}
    for line in r.stdout.splitlines():
        k, sep, v = line.strip().partition(":")
        if sep and k in keys:
            out[k] = v.strip()
    return out


def size_of(path):
    p = sips_props(path, "pixelWidth", "pixelHeight")
    try:
        return int(p["pixelWidth"]), int(p["pixelHeight"])
    except (KeyError, ValueError):
        return None


def flatten(src, dst, size):
    """src → a JPEG at dst with no alpha channel, the same size; None, or why it failed (dst removed)."""
    r = subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "best", str(src), "--out", str(dst)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not dst.exists():
        said = (r.stderr or r.stdout).strip().splitlines()
        return f"sips could not convert it ({said[-1] if said else 'no output'})"
    p = sips_props(dst, "pixelWidth", "pixelHeight", "hasAlpha", "format")
    got = (p.get("pixelWidth"), p.get("pixelHeight"))
    why = None
    if p.get("hasAlpha") != "no":
        why = f"the JPEG still reports an alpha channel (hasAlpha: {p.get('hasAlpha', 'unknown')})"
    elif got != (str(size[0]), str(size[1])):
        why = f"the JPEG came out {got[0]} x {got[1]}, not {size[0]} x {size[1]}"
    elif p.get("format") != "jpeg":
        why = f"sips wrote {p.get('format', 'an unknown format')}, not jpeg"
    if why:
        dst.unlink(missing_ok=True)
    return why


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-") or "screen"


def toplevel(repo):
    """The top of the git repository the app's folder is in, or None (no git, or not a repository)."""
    if not shutil.which("git"):
        return None
    top = subprocess.run(["git", "-C", str(repo), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return pathlib.Path(top.stdout.strip()).resolve() if top.returncode == 0 and top.stdout.strip() else None


def exclude(repo, out):
    """Put <out> into the repository's .git/info/exclude (once), as its path from the repository's top with gitignore's
    special characters escaped; the line written, or None outside a repository (or for its top itself)."""
    top = toplevel(repo)
    if top is None:
        return None
    try:
        rel = out.resolve().relative_to(top).as_posix()
    except ValueError:
        return None
    if rel in ("", "."):
        return None
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--git-path", "info/exclude"], capture_output=True,
                       text=True)
    if r.returncode != 0:
        return None
    path = pathlib.Path(r.stdout.strip())
    path = path if path.is_absolute() else repo / path
    line = "/" + re.sub(r"([][*?\\])", r"\\\1", rel) + "/"
    have = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    if line not in have:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(("" if not have or path.read_text(encoding="utf-8").endswith("\n") else "\n") + line + "\n")
    return line


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", type=pathlib.Path, default=pathlib.Path(".duo/migration.json"))
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--kind", choices=["after", "before"], default="after")
    a = ap.parse_args()
    if not shutil.which("sips"):
        print("appstore.py needs macOS's sips, to flatten the shots", file=sys.stderr)
        sys.exit(2)
    path = a.file.resolve()
    if not path.exists():
        print(f"no progress file at {path}", file=sys.stderr)
        sys.exit(2)
    repo = path.parent.parent
    out = (a.out or repo / ".duo" / "appstore").resolve()
    top = toplevel(repo)
    for holder, what in ((repo.resolve(), "the app's folder"), (top, "the repository's top"),
                         (path.parent, "the folder that holds the progress file")):
        if holder is not None and (out == holder or (what != "the folder that holds the progress file"
                                                     and holder.is_relative_to(out))):
            print(f"--out {out} is {what}{'' if out == holder else ' or a folder above it'}: give the screenshots a "
                  "folder of their own (the default is .duo/appstore)", file=sys.stderr)
            sys.exit(2)
    readme = out / "README.md"
    if readme.exists():
        try:
            first = readme.read_text(encoding="utf-8").splitlines()[:1]
        except (OSError, UnicodeDecodeError):
            first = []
        if first != [HEADING]:
            print(f"{readme} is not one this script wrote (its first line is not {HEADING!r}): nothing was changed. "
                  "Give --out a folder of its own.", file=sys.stderr)
            sys.exit(2)
    pr = progress()
    try:
        m = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"{path} cannot be read as a progress file: {e}", file=sys.stderr)
        sys.exit(2)
    if not isinstance(m, dict) or not isinstance(m.get("screens", []), list):
        print(f"{path} is not a progress file (no list of screens)", file=sys.stderr)
        sys.exit(2)
    for s in m.get("screens", []):   # what progress.py and the rest read, made whole: a name and a dict of cells
        if not isinstance(s, dict) or not isinstance(s.get("name"), str) or not isinstance(s.get("cells", {}), dict):
            print(f"{path}: a screen with no name or no cells ({str(s)[:80]})", file=sys.stderr)
            sys.exit(2)
        s.setdefault("cells", {})
    kind = a.kind
    states = ("verified", "unchanged") if kind == "after" else ("unchanged",)
    if not any(c.get(kind) for s in m.get("screens", []) for c in s.get("cells", {}).values()):
        hint = " (an audit has only before shots: --kind before)" if kind == "after" else ""
        print(f"no cell of {path} has a {kind} shot yet{hint}", file=sys.stderr)
        sys.exit(1)
    folder = pr.captures(m, repo, kind)
    table = pr.table(folder)
    issues = pr.open_issues(m)

    within = top or repo.resolve()

    def inside(value):
        """The shot's real path when it is inside the repository, else None."""
        p = pathlib.Path(str(value))
        p = (p if p.is_absolute() else repo / p).resolve()
        return p if p.is_relative_to(within) else None

    def refusal(s, pose, size):
        """Why the cell cannot give an App Store shot of that size; None when it can."""
        c = s.get("cells", {}).get(pose)
        if not c:
            return "not captured"
        state = c.get("state", "pending")
        if state not in states:
            fixed = " (its before shot is the layout that was fixed)" if kind == "before" and state == "verified" else ""
            return f"state {state}{fixed}"
        if not c.get(kind):
            return f"no {kind} shot"
        shot = inside(c[kind])
        if shot is None:
            return f"{c[kind]} is outside the repository (the progress file comes with it): not read"
        if not shot.exists():
            return f"{c[kind]} is not there"
        if table is None:
            return f"no detector table in {folder} (run the detectors over the {kind} capture)"
        words = table.get(s["name"].casefold(), (None, {}))[1].get(pose)
        if words is None:
            return f"no row for it in {folder / 'detectors.md'}"
        if words != ["·"]:
            waived = c.get("waived", {})
            said = " ".join(f"{w} (waived: {waived[w]})" if w in waived else w for w in words)
            return f"detector table: {said}"
        held = [i for i in issues if pr.text(i.get("screen")).casefold() == s["name"].casefold()
                and pose in (i.get("poses") or [])]
        if held:
            return "open issue " + ", ".join(f"{pr.text(i.get('id'))} ({pr.text(i.get('what'))})" for i in held)
        got = size_of(shot)
        if got is None:
            return f"sips cannot read {c[kind]}"
        if got != size:
            return (f"{got[0]} x {got[1]}, not the {size[0]} x {size[1]} App Store Connect lists for this size "
                    "(the wrong panel or the wrong turn): not resized")
        return None

    # Replace an earlier run's files, nothing else.
    for name, *_ in SIZES:
        for f in (out / name).glob("*.jpg") if (out / name).is_dir() else []:
            if OURS.match(f.name):
                f.unlink()
    (out / "README.md").unlink(missing_ok=True)

    made = {name: [] for name, *_ in SIZES}   # folder → [(file, screen, pose, state)]
    skipped = []                              # (screen, size label, [(pose, why)])
    for s in m.get("screens", []):
        for name, display, turn, size, candidates in SIZES:
            tried = []
            for pose in candidates:
                why = refusal(s, pose, size)
                if why is None:
                    c = s["cells"][pose]
                    shot = inside(c[kind])
                    dst = out / name / f"{len(made[name]) + 1:02d}-{slug(s['name'])}-{pose}.jpg"
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    why = flatten(shot, dst, size)
                    if why is None:
                        made[name].append((dst, s["name"], pose, c.get("state"), tried))
                        break
                tried.append((pose, why))
            else:
                skipped.append((s["name"], f"{display}, {turn}", tried))

    total = sum(len(v) for v in made.values())
    for screen_name, label, tried in skipped:
        print(f"{screen_name}: no shot for the {label} (" + "; ".join(f"{p}: {w}" for p, w in tried) + ")")
    if not total:
        print(f"nothing could be exported from the {kind} capture: every cell was refused", file=sys.stderr)
        sys.exit(1)

    rel = lambda p: p.relative_to(out).as_posix()   # noqa: E731
    passed = lambda tried: "; ".join(f"{p}: {w}" for p, w in tried).replace("|", "/")   # noqa: E731
    lines = [
        HEADING,
        "",
        f"Made by Foldsmith's `appstore.py` on {datetime.date.today().isoformat()} from the {kind} capture of "
        f"{m.get('app', 'the app')} (`{folder}`), {total} file{'' if total == 1 else 's'}. Nothing was uploaded.",
        "",
        "**Before you upload anything, open every image and check it:**",
        "- for personal content: names, faces, messages, addresses, places, other people's posts, anything you would",
        "  not publish (the captures show whatever the app showed on the simulator);",
        "- the status bar: the time, battery, signal and carrier it shows (the capture did not override it);",
        "- that the screen is one you want on your product page (an empty detail pane is a real state, not a good",
        "  picture).",
        "",
        "App Store Connect lists these four sizes for iPhone Duo (its Screenshot specifications): 1 to 10 screenshots",
        "per display size, JPEG or PNG, no alpha channel. Each file here is the capture flattened to a JPEG at best",
        "quality and checked for no alpha channel and the size listed; none was resized. Only cells verified or",
        "unchanged" + ("" if kind == "after" else " (an audit's cells that were already fine)") + ", with a clean "
        "detector table and no open issue in that pose, were used.",
    ]
    for name, display, turn, size, candidates in SIZES:
        lines += ["", f"## `{name}/`: {display}, {turn}, {size[0]} × {size[1]}", ""]
        if not made[name]:
            lines.append(f"None: no screen had a {' or '.join(candidates)} cell that could be used (below).")
            continue
        if len(made[name]) > MOST:
            lines += [f"{len(made[name])} files: App Store Connect takes at most {MOST} per display size, so choose.",
                      ""]
        lines += ["| File | Screen | Pose | Cell | Poses passed over |", "|---|---|---|---|---|"]
        lines += [f"| `{rel(f)}` | {sc} | {pose} | {state} | {passed(tried) or '·'} |"
                  for f, sc, pose, state, tried in made[name]]
    if skipped:
        lines += ["", "## Not exported", "", "| Screen | Size | Why each pose was refused |", "|---|---|---|"]
        lines += [f"| {sc} | {label} | {passed(tried)} |" for sc, label, tried in skipped]
    used = {sc.casefold() for v in made.values() for _, sc, _, _, _ in v}
    loose = [i for i in issues if pr.text(i.get("screen")).casefold() in used and not i.get("poses")]
    if loose:
        lines += ["", "## Open issues on these screens with no pose", "",
                  "Not visible in one pose, so no file was refused for them; check they do not show in the images."]
        lines += [f"- {pr.text(i.get('id'))} {pr.text(i.get('screen'))}: {pr.text(i.get('what'))}" for i in loose]
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    for name, *_ in SIZES:
        for f, sc, pose, _, tried in made[name]:
            print(f"{rel(f)}  ({sc}, {pose}" + (f"; passed over {passed(tried)}" if tried else "") + ")")
    print(f"{total} file{'' if total == 1 else 's'} and README.md in {out}: check every image for personal content and "
          "the status bar before you upload; nothing was uploaded")
    line = exclude(repo, out)
    if line:
        print(f"{line} is in .git/info/exclude, so the shots stay out of git")


if __name__ == "__main__":
    main()
