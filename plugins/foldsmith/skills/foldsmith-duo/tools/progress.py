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
                                                        open issues and the latest review; exit 1 if anything keeps
                                                        one from done, 2 for a name that is no screen. With no screen
                                                        named, from phase verify on, a missing review counts too
    progress.py controls [<screen>…]                    each control gone from a cell (below) and whether a moved
                                                        record covers it; changes nothing
    progress.py moved <screen> <pose,…|all|inner> "<control>" "<where it went>" <evidence> [--as "<new label>"]
                                                        where a gone control went, one record per pose; <evidence> is
                                                        a snapshot of that cell (<screen>-<pose>.json, or
                                                        <screen>-<words>-<pose>.json for a probe, under
                                                        .duo/captures/, not a before one) showing a control (or a menu
                                                        item: a menu the capture opened) with its label or
                                                        identifier, or the --as label when it was relabelled (never an
                                                        overflow button, nor a label the before snapshot has), or
                                                        <file>:<line> of a file of the app's source that git tracks,
                                                        the line that puts it there (a menuRepresentation,
                                                        additionalOverflowItems, a menu); anything else is refused,
                                                        and so is a pose it is not gone from
    progress.py moved --remove <screen> <pose,…> "<control>"   take a moved record back
    progress.py waive <screen> <pose,…|all|inner> <id> <why>   a detector line the shot does not bear out, and why; the
                                                        id `unchanged` for a fine-as-is cell where only live content
                                                        moved (a toast, content still loading), `stale` for an after
                                                        shot from older code that the changes since cannot reach (it
                                                        keeps the code identity it was given at, and holds only until
                                                        a file outside .duo/ changes after that: given on uncommitted
                                                        code, it ends at the next commit, so commit first)
    progress.py issue add <screen> <pose,…|all|inner|-> <high|medium|low> <what happens> [--regression]
                [--found-by detector|eye|review|test] [--where <file:line>]
                                                        what review, a look or a test found that no detector
                                                        table shows, on a screen of the file (- for no pose; found
                                                        by review unless said); prints its id. A regression added in
                                                        phase done sets the phase back to verify
    progress.py issue fix <id> <how>                    the issue is fixed, and how
    progress.py issue wontfix <id> <why>                left as it is, and why (never a regression)
    progress.py review <subagent|session|none> <summary>   the independent review, with the code identity it saw:
                                                        subagent, a fresh subagent given the diff and the captures,
                                                        not the run's conclusions; session, /foldsmith-review in a
                                                        new session; none, no review could be started, and why
    progress.py codeid                                  the app repository's code identity (below); reads no file
    progress.py log <text>                              one line, timestamped, newest last
    progress.py show                                    the file, summarised: each screen's cells, the cells by
                                                        state, every waiver, moved control and review (a moved
                                                        record whose control is back is marked no longer needed)

A screen never ends worse than it started, so `done <screen>: …` and `phase done` refuse, changing nothing, while any of
these is left on that screen (on any screen, for `phase done`). A done line names its screens as the pane reads them:
the words before its first ": ", split at commas and "and", each a screen's whole name or its first words, in any case
(`inbox, message: …`, `article and contents from Home: …`); a line with no ": ", or with a part that names no screen
of the file or the before table, is refused too. The checks:
  - a pose the detectors found clean in the before capture that the after capture has a finding in (one not waived on
    its cell), or where no detector ran after (not captured, or no-rotate: neither can be waived);
  - a pose that had findings before where the after capture has a class the before one did not (not waived on its
    cell): T1 T5 before and T14 after is a new problem, not the old one fixed;
  - a pose not captured before (n/a in the before table: a skipped cell) that has a finding after (not waived on its
    cell): nothing tells it from a regression until the pose is captured into before;
  - a cell marked `verified` whose after table still has a class its before table had in that pose (not waived on the
    cell): leave it `finding`, fix it, or waive it with why; and one marked `verified` or `unchanged` whose before
    table had a class there where no detector ran after (n/a, no-rotate, or no row for the screen: never waived);
  - a cell marked `unchanged` whose before and after accessibility snapshots (the <screen>-<pose>.json the tap runner
    writes beside each shot) differ: every element with a label or an identifier outside scrolling content and not a
    system element (same-screen.py's exclusions), as type, label or identifier, and frame in whole points, the rows
    with an identifier and no label of a list that is itself outside scrolling content (a sidebar's), and the
    window's size. Other rows of lists are not compared. What moves on its own is left out: text that changes only in
    its numbers, in place (a clock, a relative date), the keyboard, and on a map the pins at its edge and the card a
    pin opens. Mark it `verified` if the change is right, or waive `unchanged` on it; a missing or unreadable snapshot
    is noted, not counted;
  - a control gone: in a cell neither `unchanged` nor `pending`, with both snapshots, a control of the before snapshot
    (a button, link, switch, toggle, segmented control, slider, stepper, text, secure text or search field, menu or
    pop-up button, with a label or an identifier, among the elements the `unchanged` comparison keeps) for which the
    after snapshot has no control with the same identifier (when it has one) nor the same label (trimmed, in any case),
    and no moved record (`moved`) names it in that pose whose evidence still holds (a shot of that cell; an --as label
    the before snapshot lacks; a line of a tracked file). An inner pose's overflow cannot be opened by the tap runner
    (taps reach only the cover), so a control moved into one is proven by code or brought back. A record whose control
    is back is noted as no longer needed, not counted;
  - a done line that says "every pose" or "all poses" and "verified" (in any case) while a cell of a screen it names is
    not `verified`: say what the cells say (`settings: Fold-aligned split (sheet rule), 1 verified, 6 unchanged`);
  - a commit cited (a word of 7 to 40 hex characters with a digit and a letter a-f) in a done line, an issue's text or
    note, a moved record, or a `made:` line of .duo/PLAN.md (for `phase done`, and `check` with no screen named) that
    is not an ancestor of HEAD (`git merge-base --is-ancestor`): an amended or rebased commit;
  - a `verified` or `unchanged` cell with an after shot whose code identity (the last line for its screen and pose in
    .captured, in the folder that holds the shot: "<flow sha256> <screen> <pose> <code identity>") is not the code's
    now and is stale: its HEAD not an ancestor of HEAD, uncommitted changes in either, or files changed since outside
    .duo/ (`git diff --name-only <its HEAD> HEAD`). Rebuild and install from the committed tree and capture it again,
    or waive `stale` on the cell with why: the waiver holds while nothing outside .duo/ changes after the code it was
    given at. A line with no code identity (a capture before 0.8.1) or no line is noted, not counted, except a cell
    whose after shot is not there while its folder has a .captured (an empty one too: a capture stopped mid-screen
    removes the cell's shot and line first, and a missing shot proves nothing): that one counts;
  - an open issue marked as a regression that names the screen;
  - for `phase done` (and `check` with no screen named, from phase verify on): no review on record (`review`).
Outside a git repository, or before its first commit, cited commits and code identities are noted, not checked; the git
commands are read-only (rev-parse, diff, ls-files, merge-base, log). The detectors' tables are the detectors.md that
capture-app.sh writes in each capture's folder (where most of the cells' shots are, else .duo/captures/<app>/before
or after). Without a before table there is nothing to compare them with, and the check says so.

The code identity (`codeid`; the captures write it on each line of .captured): of the repository holding .duo/ (the
progress file's, else the nearest one above the current folder), else of the current folder's. `<40-hex HEAD>` when
nothing is uncommitted outside .duo/; `<HEAD>+<the first 16 hex of a sha256>` otherwise, the hash over the output of
`git diff HEAD --full-index --binary --no-ext-diff -- . ':(exclude).duo'` (with git's defaults named, so the diff
options its configuration sets do not change the bytes: full blob ids, color and textconv off, the a/ and b/ prefixes,
3 lines of context, no inter-hunk context, no order file, the myers algorithm with the indent heuristic, renames
found, paths not relative and quoted, blank context lines kept, submodules short; so the same tree has the same
identity on every Mac, whatever the size of its object store; core.fileMode and diff.ignoreSubmodules still decide
what counts as changed) followed by, for each untracked file outside .duo/ that git does not ignore (`git ls-files
--others --exclude-standard -z -- . ':(exclude).duo'`, sorted), its path, a NUL and its bytes (a symbolic link's
target); `none` outside a git repository or before the first commit. Always exit 0.

--file <path> names the file (default: .duo/migration.json under the current directory). Paths stored in the file are
relative to the app's repository, the folder that holds .duo/.
"""
import argparse
import collections
import contextlib
import datetime
import fcntl
import hashlib
import importlib.util
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

POSES = ["closed", "closed-sideways", "book", "laptop", "tent", "flat-sideways", "flat-upright"]
INNER = POSES[2:]
PHASES = ["screens", "audit", "classify", "migrate", "verify", "done"]
STATES = ["pending", "unchanged", "finding", "proposed", "migrated", "verified"]
SEVERITIES = ["high", "medium", "low"]
FOUND_BY = ["detector", "eye", "review", "test"]
REVIEWS = ["subagent", "session", "none"]
NOT_CLASSES = {"·", "n/a", "no-rotate"}   # a table cell's words that are not a class id
LISTS = {"table", "collectionView"}        # whose rows with an identifier and no label are compared (a sidebar's)
CARD = (320, 200)   # pt: the largest card a map pin opens that is left out with it (Wikipedia's: 240 x 116-134)
CONTROLS = {"button", "link", "switch", "toggle", "segmentedControl", "slider", "stepper", "textField",
            "secureTextField", "searchField", "menuButton", "popUpButton"}
SHOWN = CONTROLS | {"menuItem"}   # what a snapshot given as a moved record's evidence may show it as (a menu it opened)
SYSTEM = {"statusBar", "keyboard", "key"}   # same-screen.py's, for when it is not beside this file
OUTSIDE = ":(exclude).duo"   # the pathspec, after `-- .`, that leaves .duo/ out of the code identity
CLAIM = re.compile(r"every pose|all (?:\w+ )?poses", re.IGNORECASE)
# A commit cited in text: 7-40 hex characters, a whole word (not part of a UUID, a path segment joined by - or _, or
# the hash after a code identity's +), with a digit and a letter.
CITED = re.compile(r"(?<![0-9A-Za-z_+-])[0-9a-f]{7,40}(?![0-9A-Za-z_-])")
IDENTITY = re.compile(r"[0-9a-f]{40}(\+[0-9a-f]{16})?")

DETECTORS_FIX = ("Fix it or revert the change for that screen, then capture it again into the after folder "
                 "(SCREEN=<screen>). A line the shot does not bear out: `progress.py waive <screen> <pose> <id> "
                 "\"<why>\"`, and say why in the report. A pose with no detector run after (not captured, or "
                 "no-rotate) is never clean and cannot be waived.")
KEPT_FIX = ("A cell is verified when the finding it had is gone. Still there: `progress.py cell <screen> <pose> "
            "finding` (and the screen goes to todo), or fix it and capture again. The shot does not bear the line "
            "out: `progress.py waive <screen> <pose> <class> \"<why>\"`, and say why in the report. No detector ran "
            "after (not captured, or no-rotate) on a pose with a finding before, verified or fine as is: capture it "
            "into the after folder (SCREEN=<screen>), since nothing shows the finding gone or the pose fine; that "
            "cannot be waived.")
UNCHANGED_FIX = ("Look at both shots. The change is right: `progress.py cell <screen> <pose> verified`. It is wrong: "
                 "fix it or revert it, and capture again. Only live content moved (a toast, content still loading, a "
                 "feed's rows): `progress.py waive <screen> <pose> unchanged \"<why>\"`.")
CONTROLS_FIX = ("Bring it back (visibilityPriority, a shorter title, a narrower neighbour), or record where it went "
                "with a shot of that cell or the line of code that puts it there: `progress.py moved <screen> <pose> "
                "\"<control>\" \"<where it went>\" <evidence>`, the evidence being the snapshot's path from the "
                "repository (.duo/captures/<app>/after/<screen>-<pose>.json) or <file>:<line> (`--as \"<new "
                "label>\"` when it was relabelled, to a label the before snapshot lacks). "
                "The overflow of an inner pose cannot be opened by the tap runner (taps reach only the cover), so a "
                "control moved into it is proven by code or brought back; \"the system probably overflows it\" is not "
                "evidence. Each one moved goes in the report, with the taps it now costs.")
CLAIM_FIX = ("Take the line back (`progress.py done --remove \"<its first words>\"`) and say what the cells say, e.g. "
             "`progress.py done \"<screen>: <pattern>, 1 verified, 6 unchanged\"`.")
CITED_FIX = ("Cite the commit on this branch: a done line, `done --remove` and add it again; an issue's note, `issue "
             "fix <id>` again; a moved record, `moved` again; .duo/PLAN.md, edit it. Never amend or rebase a commit "
             "once it is cited.")
STALE_FIX = ("Commit, rebuild and install from the committed tree (step 6: the shots are of the app on the simulator, "
             "which the code identity cannot see), then capture those screens again into the same after folder "
             "(SCREEN=<screen>) and look at the shots: a capture of uncommitted code proves nothing about what is "
             "committed. A change that cannot reach the screen (another target, a comment): commit it, then "
             "`progress.py waive <screen> <pose> stale \"<why>\"`, and say why in the report; it holds until the next "
             "change outside .duo/ (given on uncommitted code, it ends at the commit).")
ISSUES_FIX = ("Fix each one, or revert the change that caused it, then `progress.py issue fix <id> \"<how>\"`. A "
              "regression is never left as it is.")
REVIEW_FIX = ("record the independent review (references/review.md): progress.py review subagent \"…\"; a session "
              "that cannot start a subagent records none with why and tells the person to run /foldsmith-review in a "
              "new session")
NO_GIT = ("(not a git repository, or no commit yet: the commits cited and the shots' code identity are not "
          "checked)")


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


def find_screen(m, name):
    """The file's screen of that name (any case), or None; adds nothing."""
    return next((s for s in m["screens"] if s["name"].casefold() == name.casefold()), None)


def poses(m, spec):
    if spec == "all":
        return m.get("poses") or POSES
    if spec == "inner":
        return [p for p in (m.get("poses") or POSES) if p in INNER]
    return spec.split(",")


def log(m, text):
    m.setdefault("log", []).append(f"{time.strftime('%H:%M')} {text}")


def git(repo, *args):
    """A read-only git command in repo: (exit code, stdout bytes); (None, b"") with no git. It takes no optional lock,
    so it never writes the index."""
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                           env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
    except OSError:
        return None, b""
    return r.returncode, r.stdout


def head_of(repo):
    """HEAD's 40-hex commit, or None outside a git repository or before the first commit."""
    rc, out = git(repo, "rev-parse", "--verify", "-q", "HEAD^{commit}")
    return out.decode().strip() if rc == 0 and out.strip() else None


def untracked(repo):
    """The untracked files outside .duo/ that git does not ignore, as git prints them (bytes, relative to repo),
    sorted."""
    rc, out = git(repo, "ls-files", "--others", "--exclude-standard", "-z", "--", ".", OUTSIDE)
    return sorted(p for p in out.split(b"\0") if p) if rc == 0 else []


def code_identity(repo):
    """The code identity of the repository at repo (the module's docstring says what it is)."""
    head = head_of(repo)
    if not head:
        return "none"
    # Every option of git's configuration that changes the diff's bytes is named, each at git's default.
    # --full-index: full blob ids, whose abbreviation would follow core.abbrev and the size of the object store.
    rc, diff = git(repo, "-c", "diff.suppressBlankEmpty=false", "-c", "core.quotePath=true", "diff", "HEAD",
                   "--full-index", "--binary", "--no-ext-diff", "--no-color", "--no-textconv", "--src-prefix=a/",
                   "--dst-prefix=b/", "-U3", "--inter-hunk-context=0", "-O/dev/null", "--diff-algorithm=myers",
                   "--indent-heuristic", "-M", "--no-relative", "--submodule=short", "--", ".", OUTSIDE)
    if rc != 0:
        return "none"
    paths = untracked(repo)
    if not diff and not paths:
        return head
    digest = hashlib.sha256(diff)
    for p in paths:
        digest.update(p + b"\0")
        f = pathlib.Path(repo) / os.fsdecode(p)
        try:
            if f.is_symlink():
                digest.update(os.fsencode(os.readlink(f)))
            elif f.is_file():
                with open(f, "rb") as data:
                    for chunk in iter(lambda: data.read(1 << 20), b""):
                        digest.update(chunk)
        except OSError:
            pass   # unreadable: its path alone
    return f"{head}+{digest.hexdigest()[:16]}"


def app_repo(path):
    """The repository `codeid` describes: the one holding .duo/ (the progress file's folder, else the nearest .duo/ at
    or above the current folder, up to its git repository's top), else the current folder's git repository, else the
    current folder."""
    if path.parent.is_dir():
        return path.parent.parent
    here = pathlib.Path.cwd().resolve()
    rc, out = git(here, "rev-parse", "--show-toplevel")
    top = pathlib.Path(out.decode().strip()).resolve() if rc == 0 and out.strip() else None
    for folder in [here, *here.parents] if top else [here]:
        if (folder / ".duo").is_dir():
            return folder
        if folder == top:
            break
    return top or here


def short(identity):
    """A code identity in a line: 7 hex of its HEAD, and 7 of its hash after a +."""
    head, plus, rest = identity.partition("+")
    return head[:7] + (f"+{rest[:7]}" if plus else "")


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
            if words in ([], ["n/a"]):
                # Not captured before (a skipped cell): nothing tells an after finding there from a regression.
                left = [w for w in now if w not in NOT_CLASSES and w not in mine]
                if left:
                    found.append(f"{name} {pose}: not captured before, {' '.join(left)} after (capture the pose into "
                                 "before from the commit the migration started from, to tell whether it is new)")
                continue
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


def kept_findings(m, repo, names=None):
    """Each cell marked `verified` whose after table still has a class its before table had in that pose, less the
    class ids waived on the cell, and each one marked `verified` or `unchanged` with a class before where no detector
    ran after (n/a, no-rotate, or no cell for it: nothing shows the finding gone, or the pose fine as is, and no
    waiver lifts that): one line each; names (casefolded) limits it."""
    before = table(captures(m, repo, "before"))
    if not before:
        return []
    after = table(captures(m, repo, "after")) or {}
    order = {p: i for i, p in enumerate(m.get("poses") or POSES)}
    found = []
    for s in m["screens"]:
        key = s["name"].casefold()
        if (names is not None and key not in names) or key not in before:
            continue
        for pose, c in sorted(s["cells"].items(), key=lambda pc: order.get(pc[0], len(order))):
            if c.get("state") not in ("verified", "unchanged"):
                continue
            then = before[key][1].get(pose, [])
            now = after.get(key, ("", {}))[1].get(pose)
            if any(w not in NOT_CLASSES for w in then) and now in (None, [], ["n/a"], ["no-rotate"]):
                found.append(f"{s['name']} {pose} is {c['state']} but no detector ran after: capture it into the "
                             "after folder")
                continue
            if c.get("state") != "verified":
                continue
            still = [w for w in now or [] if w not in NOT_CLASSES and w in then and w not in c.get("waived", {})]
            if still:
                found.append(f"{s['name']} {pose} is verified but {' '.join(still)} "
                             f"{'is' if len(still) == 1 else 'are'} still in the after table: leave it finding, fix "
                             "it, or waive it with why")
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


def controls(d, ss):
    """The snapshot's controls, in its order, as dicts (type, label, identifier, frame): the nodes of a type in
    CONTROLS, with a label or an identifier, that the `unchanged` comparison keeps (same-screen.py's kept(), less what
    moving() leaves out: the keyboard, a map's pins and the card one opens)."""
    nodes = d["nodes"]
    index = {id(n): i for i, n in enumerate(nodes)}
    skip = moving(d, ss)
    out = []
    for n in ss.kept(d):
        label, ident = text(n.get("label")).strip(), text(n.get("identifier")).strip()
        if n["type"] in CONTROLS and (label or ident) and index[id(n)] not in skip:
            out.append({"type": n["type"], "label": label, "identifier": ident, "frame": n["frame"]})
    return out


def control_name(c):
    return c["label"] or c["identifier"]


def names_it(name, c):
    """Whether a control's name as written (a moved record's, trimmed, in any case) is c's label or identifier."""
    name = name.strip().casefold()
    return bool(name) and name in {c["label"].casefold(), c["identifier"].casefold()} - {""}


def gone(before, after, ss):
    """The controls of the before snapshot the after one has no control for: none with the same identifier (when it
    has one) nor the same label, trimmed and in any case."""
    now = controls(after, ss)
    idents = {c["identifier"].casefold() for c in now if c["identifier"]}
    labels = {c["label"].casefold() for c in now if c["label"]}
    return [c for c in controls(before, ss)
            if not (c["identifier"] and c["identifier"].casefold() in idents)
            and not (c["label"] and c["label"].casefold() in labels)]


def cell_gone(repo, s, pose, c, ss):
    """(the controls gone from one cell, a note, the before snapshot's controls): None for the controls when there is
    nothing to compare."""
    paths = [snapshot(repo, c[kind]) for kind in ("before", "after")]
    try:
        before, after = (json.loads(p.read_text(encoding="utf-8")) for p in paths)
        return gone(before, after, ss), None, controls(before, ss)
    except FileNotFoundError:
        return None, f"({s['name']} {pose}: no snapshot, its controls not compared)", []
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError) as err:
        return None, f"({s['name']} {pose}: snapshot unreadable, its controls not compared: {err})", []


def already_there(label, prior):
    """Why an --as label does not hold when a control of the before snapshot (prior) already has it, else None."""
    if any(names_it(label, x) for x in prior):
        return (f"{quoted(label.strip())} was already on the screen before; a relabelled control's new label is one "
                "the before snapshot lacks")
    return None


def cell_names(m, repo, name, pose):
    """(the name a snapshot of the cell is written under, every name it may begin with, casefolded): the screen's as
    the file has it and as the capture wrote its shots."""
    s, out, shown = find_screen(m, name), {name.casefold()}, name
    for kind in ("after", "before"):
        shot = ((s["cells"].get(pose) or {}).get(kind) if s else None)
        hit = shot_screen(shot, pose) if isinstance(shot, str) else None
        if hit:
            out.add(hit.casefold())
            shown = hit if shown == name else shown
    return shown, out


def every_name(m, repo):
    """Every screen name a snapshot may begin with, casefolded: the file's, the before table's and the shots'."""
    out = set(known(m, repo))
    for s in m["screens"]:
        for pose, c in s["cells"].items():
            for kind in ("before", "after"):
                hit = shot_screen(c[kind], pose) if isinstance(c.get(kind), str) else None
                if hit:
                    out.add(hit.casefold())
    return out


def of_cell(path, mine, every, pose):
    """Whether a snapshot's file is of the cell: <screen>-<pose>.json, or <screen>-<words>-<pose>.json (a probe), in
    any case, where no other screen's name fits the stem better (inbox-search-laptop is inbox-search's, not inbox's)."""
    stem, tail = path.stem.casefold(), "-" + pose.casefold()
    if not stem.endswith(tail):
        return False
    head = stem[:-len(tail)]
    owners = [n for n in every | mine if head == n or head.startswith(n + "-")]
    return bool(owners) and max(owners, key=len) in mine


def moved_records(m):
    """The file's moved records, those written by hand too: a list of dicts."""
    return [r for r in m.get("moved") or [] if isinstance(r, dict)]


def resolved(repo, given):
    """A path as given (relative to the repository, or absolute), resolved; None if it is outside the repository."""
    p = pathlib.Path(given)
    p = (p if p.is_absolute() else repo / p).resolve()
    return p if p.is_relative_to(repo.resolve()) else None


def evidence(m, repo, given, shows, ss, name, pose, relabelled=False):
    """A moved record's evidence for the cell (name, pose): (kind, the path or file:line as stored, why it does not
    hold or None). kind is shot for a snapshot of that cell (of_cell: a shot proves only its own pose; another pose's,
    the cover's above all, says nothing about an inner pose's overflow) under .duo/captures/, not a before one, that
    shows a control (or a menu item) named shows, in any case; relabelled (an --as label), never an overflow button
    (identifier *Overflow*, or "More"): that is where controls go, not one relabelled. code is <file>:<line> of the
    app's source outside .duo/ and .git/ (in a git repository, a file git tracks), a line that is there and not blank.
    Anything else does not hold."""
    given, wanted = given.strip(), shows.strip().casefold()
    code = re.fullmatch(r"(.*\S):(\d+)", given)
    if given.endswith(".json"):
        p = resolved(repo, given)
        if p is None or not p.is_relative_to((repo / ".duo" / "captures").resolve()):
            return "shot", given, f"{given} is not under .duo/captures/ in the repository"
        rel = p.relative_to(repo.resolve()).as_posix()
        if not p.is_file():
            return "shot", rel, f"there is no snapshot {rel}"
        befores = {snapshot(repo, c["before"]).resolve() for s in m["screens"] for c in s["cells"].values()
                   if c.get("before")}
        if p in befores or p.parent == captures(m, repo, "before").resolve():
            return "shot", rel, f"{rel} is a before snapshot: it shows where the control was, not where it went"
        shown, mine = cell_names(m, repo, name, pose)
        if not of_cell(p, mine, every_name(m, repo), pose):
            folder = captures(m, repo, "after").resolve()
            folder = folder.relative_to(repo.resolve()).as_posix() if folder.is_relative_to(repo.resolve()) else folder
            return "shot", rel, (f"{rel} is not a snapshot of {name} {pose}: a shot proves only its own pose, so give "
                                 f"{folder}/{shown}-{pose}.json (the after capture), or {shown}-{pose}.json from a "
                                 f"SCREEN={shown} ONLY={pose} probe of that cell, or the line of code that puts it "
                                 "there")
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            nodes = d["nodes"]
            system = [False] * len(nodes)
            for i, n in enumerate(nodes):
                parent = n["parent"]
                system[i] = n["type"] in (ss.SYSTEM if ss else SYSTEM) or (parent >= 0 and system[parent])
            found = [n for i, n in enumerate(nodes) if not system[i] and n["type"] in SHOWN and wanted in
                     {text(n.get("label")).strip().casefold(), text(n.get("identifier")).strip().casefold()} - {""}]
        except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError) as err:
            return "shot", rel, f"{rel} is unreadable ({err})"
        if not found:
            return "shot", rel, f"{rel} shows no control named {quoted(shows.strip())}"
        if relabelled and all("overflow" in text(n.get("identifier")).casefold()
                              or text(n.get("label")).strip().casefold() == "more" for n in found):
            return "shot", rel, (f"{quoted(shows.strip())} in {rel} is an overflow button, where controls go, not one "
                                 "relabelled: prove what it holds with the line of code that puts the control there, "
                                 "or a shot of the open menu")
        return "shot", rel, None
    if code:
        p = resolved(repo, code[1])
        if p is None or p.is_relative_to((repo / ".duo").resolve()) or not p.is_file():
            return "code", given, f"there is no file {code[1]} in the repository (outside .duo/)"
        rel, line = p.relative_to(repo.resolve()).as_posix(), int(code[2])
        if ".git" in pathlib.PurePosixPath(rel).parts:
            return "code", f"{rel}:{line}", (f"{rel} is git's own, not the app's source: cite a line of a tracked "
                                             "source file")
        if git(repo, "rev-parse", "--is-inside-work-tree")[1].strip() == b"true" \
                and git(repo, "ls-files", "--error-unmatch", "--", f":(literal){rel}")[0] != 0:
            return "code", f"{rel}:{line}", (f"{rel} is not tracked by git (a file written as proof is not the app's "
                                             "source): cite a line of a tracked source file")
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as err:
            return "code", f"{rel}:{line}", f"{rel} is unreadable ({err})"
        if not 1 <= line <= len(lines):
            return "code", f"{rel}:{line}", f"{rel} has {len(lines)} lines, not a line {line}"
        if not lines[line - 1].strip():
            return "code", f"{rel}:{line}", f"line {line} of {rel} is blank: cite the line that puts it there"
        return "code", f"{rel}:{line}", None
    return None, given, (f"{given} is neither a snapshot (a .json under .duo/captures/) nor <file>:<line> of the "
                         "app's source")


def record_shows(r):
    """What a moved record's snapshot must show: its --as label, else the control's name."""
    return text(r.get("as") or r.get("control"))


def controls_gone(m, repo, names=None):
    """Each control gone from a cell neither `unchanged` nor `pending` with a before and an after shot: (screen,
    pose, control, the moved record that names it or None, why that record does not hold or None), notes, and the
    moved records of the cells compared that name no control gone from them (the control is back: no longer
    needed); names (casefolded) limits it."""
    found, notes, ss, compared, used = [], [], False, set(), set()
    order = {p: i for i, p in enumerate(m.get("poses") or POSES)}
    records = moved_records(m)
    for s in m["screens"]:
        if names is not None and s["name"].casefold() not in names:
            continue
        for pose, c in sorted(s["cells"].items(), key=lambda pc: order.get(pc[0], len(order))):
            if c.get("state") in ("unchanged", "pending", None) or not c.get("before") or not c.get("after"):
                continue
            if ss is False:
                ss = same_screen()
            if ss is None:
                notes.append(f"(no same-screen.py beside {pathlib.Path(__file__).name}: no control was compared)")
                return found, notes, []
            lost, note, prior = cell_gone(repo, s, pose, c, ss)
            if note:
                notes.append(note)
            if lost is not None:
                compared.add((s["name"].casefold(), pose))
            for control in lost or []:
                r = next((r for r in records if text(r.get("screen")).casefold() == s["name"].casefold()
                          and r.get("pose") == pose and names_it(text(r.get("control")), control)), None)
                why = None
                if r:
                    used.add(id(r))
                    why = (r.get("as") and already_there(text(r["as"]), prior)) or evidence(
                        m, repo, text(r.get("evidence")), record_shows(r), ss, s["name"], pose, bool(r.get("as")))[2]
                found.append((s["name"], pose, control, r, why))
    unneeded = [r for r in records if id(r) not in used
                and (text(r.get("screen")).casefold(), r.get("pose")) in compared]
    for r in unneeded:
        notes.append(f"({unneeded_line(r)})")
    return found, notes, unneeded


def unneeded_line(r, said=True):
    """A moved record whose control is back, in a note's words (said: naming the record first)."""
    screen, pose, control = text(r.get("screen")), text(r.get("pose")), text(r.get("control"))
    return ((f"moved record {screen} {pose} {quoted(control)} " if said else "")
            + f"no longer needed: the control is back; progress.py moved --remove {screen} {pose} \"{control}\"")


def gone_line(name, pose, control):
    x, y, w, h = control["frame"]
    return (f"{name} {pose}: {quoted(control_name(control))} (before at {number(x)},{number(y)} {number(w)}×"
            f"{number(h)}) is gone")


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


def read_done(names, line):
    """The screens a done line names, casefolded, and the parts that name none: the words before its first ": ",
    split at commas and "and", each a screen's whole name or its first words, in any case. None for a line with no
    ": "."""
    head, colon, _ = line.partition(": ")
    if not colon:
        return None, []
    if head.strip().casefold() in names:
        return {head.strip().casefold()}, []
    found, unknown = set(), []
    for part in re.split(r",\s*|\s+and\s+", head):
        words = part.strip().casefold()
        hits = {n for n in names if words == n or words.startswith(n + " ")}
        if words and not hits:
            unknown.append(part.strip())
        found |= hits
    return found, unknown


def done_screens(m, repo, line):
    """The screens a done line names, casefolded, read as the pane reads them (read_done). Exits, changing nothing,
    for a line with no ": " or a part that names no screen."""
    names = known(m, repo)
    listed = ", ".join(sorted(names.values())) or "none yet"
    found, unknown = read_done(names, line)
    if found is None:
        sys.exit(f"done refused, nothing changed: a done line is `<screen>: <what is finished>` (`<screen>, <screen>: "
                 f"…` for several). Screens: {listed}.")
    if unknown or not found:
        head = line.partition(": ")[0]
        parts = ", ".join(f'"{u}"' for u in unknown or [head.strip()])
        sys.exit(f"done refused, nothing changed: {parts} names no screen. Screens: {listed}. A line about something "
                 "other than a screen goes in the log (`progress.py log`).")
    return found


def done_lines(m, repo, names, line=None):
    """The done lines that name one of names (every one, for None), and line, the one being added."""
    known_names = known(m, repo)
    out = [d for d in m.get("done") or [] if isinstance(d, str)
           and (names is None or (read_done(known_names, d)[0] or set()) & names)]
    return out + ([line] if line is not None and line not in out else [])


def cells_say(m, name):
    """What a screen's cells say, in a done line's words: `settings: Fold-aligned split (sheet rule), 1 verified, 6
    unchanged`."""
    s = find_screen(m, name)
    counts = collections.Counter((s["cells"].get(p) or {}).get("state", "pending") if s else "pending"
                                 for p in m.get("poses") or POSES)
    order = ["verified", "unchanged", "finding", "migrated", "proposed", "pending"]
    said = ", ".join(f"{counts[k]} {k}" for k in sorted(counts, key=lambda k: order.index(k) if k in order else 99))
    pattern = s.get("pattern") if s else None
    return f"{s['name'] if s else name}: {pattern + ', ' if pattern else ''}{said}"


def overclaims(m, repo, lines):
    """Each done line that says "verified in every pose" (or all poses) while a cell of a screen it names is not
    `verified`: (the line, what the cells of those screens say)."""
    known_names = known(m, repo)
    out = []
    for line in lines:
        if not (CLAIM.search(line) and re.search("verified", line, re.IGNORECASE)):
            continue
        found = read_done(known_names, line)[0] or set()
        bad = []
        for key in sorted(found):
            s = find_screen(m, key)
            states = [(s["cells"].get(p) or {}).get("state") if s else None for p in m.get("poses") or POSES]
            if any(state != "verified" for state in states):
                bad.append(cells_say(m, known_names[key]))
        if bad:
            out.append((line, bad))
    return out


def clip(line, width=60):
    return line if len(line) <= width else line[:width - 1] + "…"


class Git:
    """The read-only git questions the checks ask of the app's repository, each asked once."""

    def __init__(self, repo):
        self.repo, self.head, self._ancestor, self._now = repo, head_of(repo), {}, None

    def now(self):
        if self._now is None:
            self._now = code_identity(self.repo)
        return self._now

    def ancestor(self, rev):
        if rev not in self._ancestor:
            self._ancestor[rev] = git(self.repo, "merge-base", "--is-ancestor", rev, "HEAD")[0] == 0
        return self._ancestor[rev]

    def same_change(self, rev):
        """The commit on this branch that holds what rev holds (the same tree, else the same subject), as `<short>
        ("<subject>")`; None if there is none or rev is no commit."""
        rc, out = git(self.repo, "log", "-1", "--format=%T%x00%s", rev, "--")
        if rc != 0 or b"\0" not in out:
            return None
        tree, subject = out.decode(errors="replace").strip("\n").split("\0", 1)
        rc, out = git(self.repo, "log", "-n", "2000", "--format=%h%x00%T%x00%s", "HEAD", "--")
        commits = [line.split("\0", 2) for line in out.decode(errors="replace").splitlines() if line.count("\0") == 2]
        hit = next((c for c in commits if c[1] == tree), None) or next((c for c in commits if c[2] == subject), None)
        return f'{hit[0]} ("{hit[2]}")' if hit else None

    def changed(self, since, worktree=False):
        """The files changed outside .duo/ from commit since to HEAD (to the working tree, untracked files too, with
        worktree)."""
        args = ["diff", "--name-only", "--no-renames", since] + ([] if worktree else ["HEAD"]) + ["--", ".", OUTSIDE]
        rc, out = git(self.repo, *args)
        files = out.decode(errors="replace").splitlines() if rc == 0 else []
        if worktree:
            files += [os.fsdecode(p) for p in untracked(self.repo)]
        return sorted(set(files))


def citations(m, repo, names=None, line=None):
    """(where, text) for each text that may cite a commit: done lines, issues' texts and notes, moved records (of
    the screens named, all for None), line (a done line being added), and with no names .duo/PLAN.md's made: lines."""
    out = [(f'done line "{clip(d)}"', d) for d in done_lines(m, repo, names, line)]
    for i in issues_of(m):
        if names is None or text(i.get("screen")).casefold() in names:
            ident = text(i.get("id")) or "(no id)"
            out += [(f"issue {ident}" + ("'s note" if field == "note" else ""), text(i.get(field)))
                    for field in ("what", "where", "note") if i.get(field)]
    for r in moved_records(m):
        if names is None or text(r.get("screen")).casefold() in names:
            where = f'moved record {text(r.get("screen"))} {text(r.get("pose"))} {quoted(text(r.get("control")))}'
            out.append((where, " ".join(text(r.get(k)) for k in ("to", "evidence", "as"))))
    plan = repo / ".duo" / "PLAN.md"
    if names is None and plan.is_file():
        for n, row in enumerate(plan.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if "made:" in row:
                out.append((f".duo/PLAN.md:{n}", row.split("made:", 1)[1]))
    return out


def not_on_branch(m, repo, g, names=None, line=None):
    """Each commit cited (citations) that is not an ancestor of HEAD: one line each."""
    found, seen = [], set()
    for where, said in citations(m, repo, names, line):
        for sha in CITED.findall(said):
            if not (re.search(r"\d", sha) and re.search(r"[a-f]", sha)) or (where, sha) in seen:
                continue
            seen.add((where, sha))
            if not g.ancestor(sha):
                found.append(f"{where} cites {sha}, which is not on this branch (an amended or rebased commit?): cite "
                             f"{g.same_change(sha) or 'the commit on this branch that holds the change'}")
    return found


def shot_screen(shot, pose):
    """The screen's name as the capture wrote it, from a shot's file name (<screen>-<pose>-<cover|inner>.png)."""
    stem = pathlib.Path(shot).stem
    hit = re.fullmatch(rf"(.+)-{re.escape(pose)}(-(cover|inner))?", stem)
    return hit[1] if hit else None


def captured_lines(folder, cache):
    """.captured in folder: (screen, pose) → the code identity on its last line, None for a line with none (a capture
    before 0.8.1, or `none`); lines "<flow sha256> <screen> <pose> [<code identity>]"."""
    if folder not in cache:
        out = {}
        try:
            rows = (folder / ".captured").read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            rows = []
        for row in rows:
            words = row.split()
            if len(words) >= 3 and words[-1] in POSES:
                out[(" ".join(words[1:-1]), words[-1])] = None
            elif len(words) >= 4 and words[-2] in POSES:
                out[(" ".join(words[1:-2]), words[-2])] = words[-1] if IDENTITY.fullmatch(words[-1]) else None
        cache[folder] = out
    return cache[folder]


def stale_shots(m, repo, g, names=None):
    """Each `verified` or `unchanged` cell whose after shot was captured from other code than the code now, and the
    changes since can reach it, less the cells waived `stale` while nothing changed after the code the waiver was
    given at; and each whose after shot is not there while its folder has a .captured, with no line for it or one with
    no code identity (a capture stopped mid-screen removes the cell's shot and line first; a missing shot proves
    nothing): (one line each, notes for the other cells with no code identity); names (casefolded) limits it."""
    found, notes, cache, why = [], [], {}, {}
    now = g.now()
    order = {p: i for i, p in enumerate(m.get("poses") or POSES)}

    def reason(then):
        if then not in why:
            why[then] = staleness(g, then, now)
        return why[then]

    for s in m["screens"]:
        if names is not None and s["name"].casefold() not in names:
            continue
        for pose, c in sorted(s["cells"].items(), key=lambda pc: order.get(pc[0], len(order))):
            if c.get("state") not in ("verified", "unchanged") or not c.get("after"):
                continue
            shot = pathlib.Path(c["after"]) if pathlib.Path(c["after"]).is_absolute() else repo / c["after"]
            lines = captured_lines(shot.parent, cache)
            as_captured = shot_screen(shot, pose) or s["name"]
            key = next(((name, p) for name, p in lines if p == pose and name == as_captured), None) or next(
                ((name, p) for name, p in lines if p == pose and name.casefold() == s["name"].casefold()), None)
            then = lines.get(key) if key else None
            if then is None:
                if not shot.exists() and (shot.parent / ".captured").exists():
                    found.append(f"{s['name']} {pose}: its after shot is not there (a capture stopped mid-screen?): "
                                 f"capture it again (SCREEN={as_captured}, same after folder)")
                else:
                    notes.append(f"(no code identity for {s['name']} {pose})")
                continue
            if then == now or not reason(then):
                continue
            waiver = ""
            if "stale" in c.get("waived", {}):
                at = text((c.get("waived_code") or {}).get("stale"))
                if IDENTITY.fullmatch(at) and (at == now or not reason(at)):
                    continue
                waiver = (f" (waived at {short(at)}; files changed since)" if IDENTITY.fullmatch(at)
                          else " (waived with no code identity: waive it again, with why)")
            found.append(f"{s['name']} {pose}: its after shot is from {reason(then)}: rebuild and install from the "
                         f"committed tree (step 6), then capture it again (SCREEN={key[0]}, same after folder)"
                         + waiver)
    return found, notes


def staleness(g, then, now):
    """Why code identity then is not the code now, in a line's words after "from", or None when nothing that could
    reach a shot changed (the same commit or its ancestor, nothing uncommitted, no file changed outside .duo/)."""
    head = then.partition("+")[0]
    was = head[:7] + (" with uncommitted changes" if "+" in then else "")
    if not g.ancestor(head):
        return f"{was}, which is not on this branch"
    files = g.changed(head, worktree="+" in now)
    if "+" not in then and "+" not in now and not files:
        return None
    if not files:
        return f"{was}, which the code now does not have"
    listed = ", ".join(files[:3]) + (", …" if len(files) > 3 else "")
    return f"{was} and {len(files)} file{'' if len(files) == 1 else 's'} changed since ({listed})"


def review_line(m, g):
    """The latest review in a line, and a note when the code has changed since it; (None, None) with no review."""
    reviews = [r for r in m.get("reviews") or [] if isinstance(r, dict)]
    if not reviews:
        return None, None
    r = reviews[-1]
    saw = text(r.get("codeid")) or "none"
    line = (f"review: {text(r.get('kind'))}, {text(r.get('at'))}, saw {short(saw)}: {text(r.get('summary'))}")
    note = None
    if g.head and saw != g.now():
        note = f"(the last review saw {short(saw)}, the code is now {short(g.now())})"
    return line, note


def gate(m, repo, names=None, line=None, run=False):
    """What keeps the named screens (every screen, for None) from done: ([(heading, lines, fix)], notes). line is a
    done line being added; run adds what keeps the run from phase done (the review)."""
    g = Git(repo)
    found = regressions(m, repo, names)
    changed, notes = changed_cells(m, repo, names)
    lost, more, _ = controls_gone(m, repo, names)
    notes += more
    if found is None:
        notes.insert(0, f"no detector table in {captures(m, repo, 'before')}: the detectors' findings are not compared")
    held_controls = [gone_line(n, p, c) + (f"; its moved record no longer holds: {why}" if r else "")
                     for n, p, c, r, why in lost if r is None or why]
    claims = [f'done line "{clip(d)}" says verified in every pose, but the cells say {"; ".join(said)}'
              for d, said in overclaims(m, repo, done_lines(m, repo, names, line))]
    cited, stale = [], []
    if g.head:
        cited = not_on_branch(m, repo, g, names, line)
        stale, more = stale_shots(m, repo, g, names)
        notes += more
    else:
        notes.append(NO_GIT)
    parts = [
        ("Worse than before where the detectors look:", found or [], DETECTORS_FIX),
        ("Marked verified with the finding it had before, or verified or fine as is with nothing run after:",
         kept_findings(m, repo, names), KEPT_FIX),
        ("Marked fine as is, but the screen changed:", changed, UNCHANGED_FIX),
        ("Controls gone from the screen:", held_controls, CONTROLS_FIX),
        ("Done lines that say more than the cells:", claims, CLAIM_FIX),
        ("Commits cited that are not on this branch:", cited, CITED_FIX),
        ("After shots missing, or from other code than the code now:", stale, STALE_FIX),
        ("Open regressions:", [issue_line(m, i) for i in open_issues(m, names) if i.get("regression")], ISSUES_FIX),
    ]
    if run and not [r for r in m.get("reviews") or [] if isinstance(r, dict)]:
        parts.append(("Before phase done:", [f"no independent review on record: {REVIEW_FIX}"], ""))
    return parts, notes, g


def refuse(m, repo, names, what, line=None, run=False):
    """Exit, changing nothing, while anything keeps the named screens (every screen, for None) from done."""
    parts, notes, _ = gate(m, repo, names, line, run)
    for note in notes:
        print(note, file=sys.stderr)
    held = [f"{heading}\n  " + "\n  ".join(lines) + (f"\n{fix}" if fix else "") for heading, lines, fix in parts
            if lines]
    if held:
        sys.exit(f"{what} refused, nothing changed.\n" + "\n".join(held))


def show(m, repo):
    issues = open_issues(m)
    held = sum(1 for i in issues if i.get("regression"))
    every = m.get("poses") or POSES
    print(f"{m.get('app')}: {m['phase']}, {len(m['screens'])} screens, {len(m.get('done', []))} done, "
          f"{len(m.get('todo', []))} left, {len(issues)} open issue{'' if len(issues) == 1 else 's'}"
          + (f" ({held} regression{'' if held == 1 else 's'})" if held else ""))
    counts = collections.Counter()
    for s in m["screens"]:
        states = [(s["cells"].get(p) or {}).get("state", "pending") for p in every]
        counts.update("left" if state not in ("verified", "unchanged") else state for state in states)
        print(f"  {s['name']} ({s.get('pattern', 'no pattern')}): "
              + " ".join(f"{p}={state}" for p, state in zip(every, states)))
    if m["screens"]:
        print(f"  cells: {counts['verified']} verified, {counts['unchanged']} unchanged, {counts['left']} left")
    for s in m["screens"]:
        for p in every:
            for ident, why in ((s["cells"].get(p) or {}).get("waived") or {}).items():
                print(f"  waived {s['name']} {p} {ident}: {why}")
    records = moved_records(m)
    unneeded = {id(r) for r in controls_gone(m, repo)[2]} if records else set()
    for r in records:
        print(f"  moved {text(r.get('screen'))} {text(r.get('pose'))} {quoted(text(r.get('control')))}"
              + (f" (now {quoted(text(r['as']))})" if r.get("as") else "")
              + f" → {text(r.get('to'))}: {text(r.get('kind'))} {text(r.get('evidence'))}"
              + (f" ({unneeded_line(r, said=False)})" if id(r) in unneeded else ""))
    for r in m.get("reviews") or []:
        if isinstance(r, dict):
            print(f"  review {text(r.get('kind'))}, {text(r.get('at'))}, saw {short(text(r.get('codeid')) or 'none')}"
                  f": {text(r.get('summary'))}")


def record_moved(m, repo, a):
    """`moved`: record where a gone control went (one record per pose, replacing one for the same control), or with
    --remove take records back. Exits, changing nothing, for a screen, pose or evidence that does not hold, or a pose
    the control is not gone from."""
    names = known(m, repo)
    if a.screen.casefold() not in names:
        sys.exit(f"no screen named {a.screen}, nothing changed: screens are "
                 f"{', '.join(sorted(names.values())) or 'none yet'}")
    name, every = names[a.screen.casefold()], m.get("poses") or POSES
    where = poses(m, a.poses)
    unknown = [p for p in where if p not in every]
    if unknown:
        sys.exit(f"no pose {', '.join(unknown)}: name poses from {', '.join(every)}, or all or inner")
    control = a.control.strip()
    if not control:
        sys.exit("moved needs the control's label or identifier, as `progress.py controls` prints it")
    records = moved_records(m)
    here = [r for r in records if text(r.get("screen")).casefold() == name.casefold() and r.get("pose") in where]
    mine = [r for r in here if text(r.get("control")).strip().casefold() == control.casefold()]
    if a.remove:
        if not mine:
            sys.exit(f"no moved record of {quoted(control)} on {name} {','.join(where)}: nothing changed")
        m["moved"] = [r for r in records if r not in mine]
        log(m, f"moved record taken back: {name} {','.join(where)} {control}")
        return
    if not a.to.strip():
        sys.exit("moved needs where the control went (\"the top bar's More\", \"the vertical bar\")")
    relabel = (a.as_label or "").strip()
    taken = [r for r in here
             if r not in mine and relabel and text(r.get("as")).strip().casefold() == relabel.casefold()]
    if taken:
        sys.exit(f"moved refused, nothing changed: {quoted(relabel)} is already {quoted(text(taken[0]['control']))} "
                 f"relabelled in {name} {taken[0]['pose']}, and one control is not two")
    ss = same_screen()
    # A shot proves only its own pose: one snapshot given for several poses holds for none but its own.
    results = [evidence(m, repo, a.evidence, relabel or control, ss, name, pose, bool(relabel)) for pose in where]
    kind, stored, why = next((r for r in results if r[2]), results[0])
    if why:
        sys.exit(f"moved refused, nothing changed: {why}. The evidence is a snapshot of that cell (a .json under "
                 ".duo/captures/) showing the control, or with --as its new label, or <file>:<line> of the app's "
                 "source that puts it there.")
    s, not_gone = find_screen(m, name), []
    for pose in where:
        c = (s["cells"].get(pose) if s else None) or {}
        lost, note, prior = cell_gone(repo, s, pose, c, ss) if ss and c.get("before") and c.get("after") else (
            None, f"({name} {pose}: no snapshots, so whether {quoted(control)} is gone there is not checked)", [])
        if relabel and already_there(relabel, prior):
            sys.exit(f"moved refused, nothing changed: {already_there(relabel, prior)} ({name} {pose}): a control "
                     "that was always there is not the one gone")
        if lost is None:
            print(note, file=sys.stderr)
        elif not any(names_it(control, x) for x in lost):
            not_gone.append(pose)
    if not_gone:
        sys.exit(f"moved refused, nothing changed: {quoted(control)} is not gone from {name} {', '.join(not_gone)} "
                 f"(`progress.py controls {name}` lists what is): name the poses it is gone from, by its label or "
                 "identifier")
    m["moved"] = [r for r in records if r not in mine]
    for pose in where:
        r = {"screen": name, "pose": pose, "control": control, "to": a.to.strip(), "evidence": stored, "kind": kind}
        if relabel:
            r["as"] = relabel
        m["moved"].append(r)
    log(m, f"moved {name} {','.join(where)} {control} → {a.to.strip()} ({kind} {stored})")


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
    p = sub.add_parser("controls"); p.add_argument("screens", nargs="*")
    moved = sub.add_parser("moved"); moved.add_argument("screen"); moved.add_argument("poses")
    moved.add_argument("control"); moved.add_argument("to", nargs="?"); moved.add_argument("evidence", nargs="?")
    moved.add_argument("--as", dest="as_label"); moved.add_argument("--remove", action="store_true")
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
    p = sub.add_parser("review"); p.add_argument("kind", choices=REVIEWS); p.add_argument("summary")
    sub.add_parser("codeid")
    p = sub.add_parser("log"); p.add_argument("text")
    sub.add_parser("show")
    a = ap.parse_args()
    path = a.file.resolve()
    repo = path.parent.parent

    if a.cmd == "codeid":   # reads no progress file and takes no lock: the captures call it
        print(code_identity(app_repo(path)))
        return
    if a.cmd == "moved" and (bool(a.remove) == bool(a.to and a.evidence) or (a.remove and (a.to or a.as_label))):
        moved.error("moved <screen> <pose,…|all|inner> \"<control>\" \"<where it went>\" <evidence> [--as \"<new "
                    "label>\"], or moved --remove <screen> <pose,…> \"<control>\"")

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
            show(m, repo)
            return
        if a.cmd in ("check", "controls"):
            names = {n.casefold() for n in a.screens} if a.screens else None
            names_known = known(m, repo)
            unknown = [n for n in a.screens if n.casefold() not in names_known]
            if unknown:
                print(f"no screen named {', '.join(unknown)}: screens are "
                      f"{', '.join(sorted(names_known.values())) or 'none yet'}", file=sys.stderr)
                sys.exit(2)
        if a.cmd == "controls":
            lost, notes, _ = controls_gone(m, repo, names)
            for n, p, c, r, why in lost:
                if r is None:
                    print(f"{gone_line(n, p, c)}: not recorded")
                else:
                    print(f"{gone_line(n, p, c)}: moved to {text(r.get('to'))} ({text(r.get('kind'))} "
                          f"{text(r.get('evidence'))}" + (f", now {quoted(text(r['as']))}" if r.get("as") else "")
                          + ")" + (f", but the record no longer holds: {why}" if why else ""))
            held = sum(1 for *_, r, why in lost if r is None or why)
            print(f"{len(lost)} gone, {len(lost) - held} recorded" if lost else "no control gone")
            if held:
                print(CONTROLS_FIX)
            for note in notes:
                print(note, file=sys.stderr)
            return
        if a.cmd == "check":
            run = names is None and m.get("phase") in ("verify", "done")
            parts, notes, g = gate(m, repo, names, run=run)
            issues = open_issues(m, names)
            first = [notes.pop(0)] if notes and notes[0].startswith("no detector table") else []
            lines = [line for heading, ls, _ in parts if heading != "Open regressions:" for line in ls]
            held = bool(lines) or any(i.get("regression") for i in issues)
            review, stale_note = review_line(m, g) if names is None else (None, None)
            if names is None and not review and not run:
                notes.append("(no independent review on record yet: phase done needs one, references/review.md)")
            if stale_note:
                notes.append(stale_note)
            for out in first + ([] if held else ["no regressions"]) + lines + [issue_line(m, i) for i in issues] \
                    + ([review] if review else []):
                print(out)
            for note in notes:
                print(note, file=sys.stderr)
            sys.exit(1 if held else 0)
        if a.cmd == "phase":
            if a.phase == "done":
                refuse(m, repo, None, "phase done", run=True)
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
            refuse(m, repo, done_screens(m, repo, a.text), f"done {name}", line=a.text)
            done = m.setdefault("done", [])
            if a.text not in done:
                done.append(a.text)
            m["todo"] = [t for t in m.get("todo", []) if not t.startswith(name + ":")]
            log(m, f"done {a.text}")
        elif a.cmd == "moved":
            record_moved(m, repo, a)
        elif a.cmd == "waive":
            if not a.why.strip():
                sys.exit("waive needs the reason the shot does not bear the line out")
            s = screen(m, a.screen)
            # A stale waiver covers the commits up to now: it keeps the code identity it was given at.
            at = code_identity(repo) if a.id == "stale" else None
            for pose in poses(m, a.poses):
                cell = s["cells"].setdefault(pose, {"state": "pending"})
                cell.setdefault("waived", {})[a.id] = a.why
                if at:
                    cell.setdefault("waived_code", {})["stale"] = at
            log(m, f"waived {a.id} on {a.screen} / {a.poses}: {a.why}" + (f" (at {short(at)})" if at else ""))
            if at and "+" in at:
                print("(the code has uncommitted changes outside .duo/: a stale waiver keeps the code it was given at, "
                      "so it ends at the next commit; commit first (step 6), then waive)", file=sys.stderr)
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
            if a.regression and m.get("phase") == "done":
                m["phase"] = "verify"
                log(m, f"phase verify: regression I{n} found after phase done reopens the run")
                print(f"phase done → verify: regression I{n} reopens the run until it is fixed", file=sys.stderr)
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
        elif a.cmd == "review":
            if not a.summary.strip():
                sys.exit("review needs a summary: what it was given, what it found (none: why no review could be "
                         "started)")
            if not isinstance(m.get("reviews"), list):
                m["reviews"] = []
            at = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
            m["reviews"].append({"kind": a.kind, "summary": a.summary.strip(), "codeid": code_identity(repo), "at": at})
            log(m, f"review {a.kind}: {a.summary.strip()}")
        elif a.cmd == "log":
            log(m, a.text)
        save(path, m)


if __name__ == "__main__":
    main()
