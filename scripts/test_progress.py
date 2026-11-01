#!/usr/bin/env python3
"""progress.py's checks: `done <screen>` and `phase done` refuse a screen worse than it started (a pose the detectors
found clean with a finding after, a class new in a pose that had findings, a verified cell that kept its finding, a cell
marked fine as is whose layout moved, a control gone with no record of where it went, a done line that says more than
the cells, a commit cited that is not on the branch, an after shot from older code, an open regression issue, and for
phase done no review on record), the code identity the captures write, and the issues kept beside the detectors'
tables. Git repositories are made in temporary folders, with no global or system git configuration.

    python3 -m unittest discover -s scripts -p 'test_*.py'
"""
import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
PROGRESS = HERE / "progress.py"
RUNS = HERE.parent / "Tests" / "Fixtures" / "runs"   # the three runs' progress files and detector tables
HEAD = "| config | closed | closed-sideways | book | laptop | tent | flat-sideways | flat-upright |\n|---|---|---|---|---|---|---|---|\n"


def rows(kind, **screens):
    return HEAD + "".join(f"| {kind}/{name.replace('_', '-')} | {' | '.join(cells.split(','))} |\n"
                          for name, cells in screens.items())


CLEAN = "·,·,·,·,·,·,·"
AGAIN = "rebuild and install from the committed tree (step 6), then capture it again (SCREEN=inbox, same after folder)"
GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
           "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com"}


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=GIT_ENV)
    if r.returncode != 0:
        raise AssertionError(f"git {' '.join(args)}: {r.stderr}")
    return r.stdout.strip()


def snapshot(*extra, window=(669, 951), cancel=(124.5, 114, 76.66666666666666, 36), rows=("Row 1",), key_x=0):
    """A tap runner snapshot: a navigation bar with Cancel, a scroll view of rows, a keyboard with a key, and extra
    (type, label, frame) elements at the window's level."""
    w, h = window
    nodes = [{"type": "application", "parent": -1, "frame": [0, 0, w, h], "label": "App"},
             {"type": "window", "parent": 0, "frame": [0, 0, w, h]},
             {"type": "navigationBar", "parent": 1, "frame": [0, 92, w, 58], "identifier": "Add Feed"},
             {"type": "button", "parent": 2, "frame": list(cancel), "label": "Cancel"},
             {"type": "scrollView", "parent": 1, "frame": [0, 150, w, 400]},
             {"type": "keyboard", "parent": 1, "frame": [0, h - 300, w, 300]},
             {"type": "key", "parent": 5, "frame": [key_x, h - 280, 30, 40], "label": "q"}]
    nodes += [{"type": "cell", "parent": 4, "frame": [0, 150 + 44 * i, w, 44], "label": r} for i, r in enumerate(rows)]
    nodes += [{"type": kind, "parent": 1, "frame": list(frame), "label": label} for kind, label, frame in extra]
    return {"bundle": "com.example.app", "window": [w, h], "nodes": nodes}


def add(snap, kind, frame, parent=1, **names):
    """A node added to a snapshot (under the window unless said), with a label, an identifier or neither; its index."""
    snap["nodes"].append({"type": kind, "parent": parent, "frame": list(frame), **names})
    return len(snap["nodes"]) - 1


class Run(unittest.TestCase):
    """A progress file with two screens, inbox and message, in a repository of its own."""

    def setUp(self):
        self.repo = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo)
        self.file = self.repo / ".duo" / "migration.json"
        self.cmd_ok("init", "App")
        for screen in ("inbox", "message"):
            self.cmd_ok("screen", screen)

    def cmd(self, *args, env=None):
        return subprocess.run([sys.executable, str(PROGRESS), "--file", str(self.file), *args],
                              capture_output=True, text=True, cwd=self.repo, env=env or GIT_ENV, encoding="utf-8")

    def cmd_ok(self, *args):
        r = self.cmd(*args)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def tables(self, before, after, folder=".duo/captures/App"):
        for kind, text in (("before", before), ("after", after)):
            if text is not None:
                (self.repo / folder / kind).mkdir(parents=True, exist_ok=True)
                (self.repo / folder / kind / "detectors.md").write_text(text, encoding="utf-8")

    def progress(self):
        return json.loads(self.file.read_text())

    def edit(self, **fields):
        """Fields of the progress file set by hand, as an older version or a person could leave them."""
        m = self.progress()
        m.update(fields)
        self.file.write_text(json.dumps(m))

    def reviewed(self):
        self.cmd_ok("review", "subagent", "given the diff and the captures; found nothing")


class RegressionCheck(Run):
    def test_done_when_clean_poses_stay_clean(self):
        self.tables(rows("before", inbox="·,·,T14 T7,T1,·,·,·"), rows("after", inbox=CLEAN))
        self.cmd_ok("cell", "inbox", "all", "verified")
        self.cmd_ok("done", "inbox: Fold-aligned split, verified in every pose")
        self.assertIn("inbox: Fold-aligned split, verified in every pose", self.progress()["done"])

    def test_done_refused_for_a_finding_in_a_pose_clean_before(self):
        self.tables(rows("before", inbox="·,·,T14,·,·,·,·"), rows("after", inbox="·,·,·,T5,·,·,·"))
        self.cmd_ok("todo", "inbox: verify")
        before = self.file.read_text()
        r = self.cmd("done", "inbox: verified")
        self.assertEqual(r.returncode, 1)
        self.assertIn("inbox laptop: clean before, T5 after", r.stderr)
        self.assertIn("progress.py waive", r.stderr)
        self.assertEqual(self.file.read_text(), before)   # nothing changed: still in todo, not in done

    def test_findings_that_stay_or_shrink_where_there_were_some_are_not_a_regression(self):
        self.tables(rows("before", inbox="·,·,T1 T5,T7,·,T5,·"), rows("after", inbox="·,·,T5,T7,·,·,·"))
        self.cmd_ok("done", "inbox: split")

    def test_a_pose_not_captured_after_is_never_clean(self):
        for after in (rows("after", inbox="·,·,·,·,·,n/a,·"), rows("after", message=CLEAN), None):
            with self.subTest(after=after):
                self.tables(rows("before", inbox=CLEAN), after)
                r = self.cmd("done", "inbox: verified")
                self.assertEqual(r.returncode, 1)
                self.assertIn("not captured after", r.stderr)
                shutil.rmtree(self.repo / ".duo" / "captures")

    def test_no_rotate_after_is_a_regression_no_waiver_lifts(self):
        self.tables(rows("before", inbox=CLEAN), rows("after", inbox="·,·,·,·,·,no-rotate,·"))
        self.cmd_ok("waive", "inbox", "flat-sideways", "no-rotate", "looks fine")
        r = self.cmd("done", "inbox: verified")
        self.assertEqual(r.returncode, 1)
        self.assertIn("inbox flat-sideways: clean before, no-rotate after", r.stderr)

    def test_waived_ids_pass_and_only_those_on_their_own_cell(self):
        self.tables(rows("before", inbox=CLEAN, message=CLEAN),
                    rows("after", inbox="·,·,T1 T5,T5,·,·,·", message="·,·,T5,·,·,·,·"))
        self.cmd_ok("waive", "inbox", "book", "T1", "map pins pan with the map")
        r = self.cmd("done", "inbox: verified")
        self.assertEqual(r.returncode, 1)
        self.assertIn("inbox book: clean before, T5 after", r.stderr)
        self.assertNotIn("T1 T5", r.stderr)
        self.cmd_ok("waive", "Inbox", "book", "T5", "the row's value is a badge, not text")
        r = self.cmd("check")   # a waiver is for its own screen and pose, not the same id elsewhere
        self.assertEqual(r.stdout.split("\n")[:2], ["inbox laptop: clean before, T5 after",
                                                    "message book: clean before, T5 after"])
        self.cmd_ok("waive", "inbox", "laptop", "T5", "the row's value is a badge, not text")
        self.cmd_ok("done", "inbox: verified")
        self.assertEqual(self.cmd("phase", "done").returncode, 1)
        m = self.progress()
        cell = next(s for s in m["screens"] if s["name"] == "inbox")["cells"]["book"]
        self.assertEqual(cell["waived"], {"T1": "map pins pan with the map", "T5": "the row's value is a badge, not text"})
        self.assertTrue(any("waived T1 on inbox / book" in line for line in m["log"]))

    def test_waive_takes_inner_and_all(self):
        self.tables(rows("before", inbox=CLEAN), rows("after", inbox="T7,·,T7,T7,T7,T7,T7"))
        self.cmd_ok("waive", "inbox", "inner", "T7", "an overlay with Close on the cover, inline inside")
        self.assertEqual(self.cmd("check").stdout.strip(), "inbox closed: clean before, T7 after")
        self.cmd_ok("waive", "inbox", "all", "T7", "the same screen in another presentation")
        self.cmd_ok("done", "inbox: verified")

    def test_waive_needs_a_reason(self):
        self.assertEqual(self.cmd("waive", "inbox", "book", "T1", " ").returncode, 1)

    def test_n_a_cannot_be_waived(self):
        self.tables(rows("before", inbox=CLEAN), rows("after", inbox="·,·,n/a,·,·,·,·"))
        self.cmd_ok("waive", "inbox", "book", "n/a", "the pose would not capture")
        self.assertEqual(self.cmd("done", "inbox: verified").returncode, 1)

    def test_phase_done_checks_every_screen_todo_ones_too(self):
        self.tables(rows("before", inbox=CLEAN, message=CLEAN), rows("after", inbox=CLEAN, message="·,·,T7,·,·,·,·"))
        self.cmd_ok("todo", "message: no pattern yet")
        r = self.cmd("phase", "done")
        self.assertEqual(r.returncode, 1)
        self.assertIn("message book: clean before, T7 after", r.stderr)
        self.assertEqual(self.progress()["phase"], "screens")
        self.cmd_ok("phase", "verify")
        self.cmd_ok("waive", "message", "book", "T7", "the same screen is an overlay with Close on the cover")
        self.reviewed()
        self.cmd_ok("phase", "done")

    def test_a_done_line_naming_several_screens_checks_each(self):
        self.tables(rows("before", inbox=CLEAN, message=CLEAN), rows("after", inbox=CLEAN, message="·,·,T5,·,·,·,·"))
        for line in ("inbox, message: Fold-aligned split", "message, inbox: Fold-aligned split"):
            r = self.cmd("done", line)
            self.assertEqual(r.returncode, 1, line)
            self.assertIn("message book", r.stderr)

    def test_screen_names_match_in_any_case(self):
        self.tables(rows("before", Inbox=CLEAN), rows("after", Inbox="·,·,T5,·,·,·,·"))
        self.assertEqual(self.cmd("done", "INBOX: verified").returncode, 1)
        self.assertEqual(self.cmd("check", "inbox").stdout.strip(), "Inbox book: clean before, T5 after")

    def test_a_done_line_names_its_screens_as_the_pane_reads_them(self):
        # The pane reads the words before ": ", split at commas and "and", each a screen's name or its first words
        self.tables(rows("before", inbox=CLEAN, message="·,·,T1,·,·,·,·", settings=CLEAN),
                    rows("after", inbox="·,·,·,T5,·,·,·", message="·,·,T14,·,·,·,·", settings="·,·,T7,·,·,·,·"))
        before = self.file.read_text()
        for line, held in [("inbox and message: verified in every pose", ("inbox laptop", "message book")),
                           ("message from Home: verified", ("message book",)),
                           ("Inbox (sheet rule): verified", ("inbox laptop",)),
                           ("settings: verified", ("settings book",))]:   # a screen only the before table names
            with self.subTest(line=line):
                r = self.cmd("done", line)
                self.assertEqual(r.returncode, 1)
                for words in held:
                    self.assertIn(words, r.stderr)
                self.assertEqual(self.file.read_text(), before)
        for line, words in [("inbox verified", "a done line is `<screen>: <what is finished>`"),
                            ("inbox and mesage: verified", '"mesage" names no screen'),
                            (": verified", '"" names no screen'),
                            ("T13: scene lifecycle adopted", '"T13" names no screen')]:
            with self.subTest(line=line):
                r = self.cmd("done", line)
                self.assertEqual(r.returncode, 1)
                self.assertIn(words, r.stderr)
                self.assertIn("Screens: inbox, message, settings", r.stderr)
                self.assertEqual(self.file.read_text(), before)
        self.cmd_ok("done", "--remove", "inbox")   # taking a line back is never refused
        self.cmd_ok("waive", "message", "book", "T14", "the list's search field ends at the fold")
        self.cmd_ok("done", "message from Home: verified")

    def test_no_before_table_means_no_check_and_says_so(self):
        r = self.cmd_ok("done", "inbox: verified")
        self.assertIn("no detector table", r.stderr)
        r = self.cmd("check")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.splitlines()[1:], ["no regressions"])
        self.assertIn("no detector table", r.stdout.splitlines()[0])

    def test_check_lists_regressions_and_its_exit_code_says_whether_there_are_any(self):
        self.tables(rows("before", inbox=CLEAN, message=CLEAN), rows("after", inbox="T10,·,·,·,·,·,·", message=CLEAN))
        r = self.cmd("check")
        self.assertEqual((r.returncode, r.stdout.strip()), (1, "inbox closed: clean before, T10 after"))
        self.assertEqual(self.cmd("check", "message").stdout.strip(), "no regressions")
        self.assertEqual(self.cmd("check", "message").returncode, 0)
        r = self.cmd("check", "mesage")   # a typo is not a clean pass
        self.assertEqual((r.returncode, r.stdout), (2, ""))
        self.assertIn("no screen named mesage: screens are inbox, message", r.stderr)

    def test_the_capture_folders_come_from_the_cells_shots(self):
        shots = self.repo / "elsewhere"
        self.tables(rows("before", inbox=CLEAN), rows("after", inbox="·,·,T5,·,·,·,·"), folder="elsewhere")
        for kind in ("before", "after"):
            self.cmd_ok("shot", kind, "inbox", "book", str(shots / kind / "inbox-book-inner.png"))
        self.assertIn("inbox book: clean before, T5 after", self.cmd("check").stdout)

    def test_the_tables_read_as_utf8_whatever_the_locale(self):
        self.tables(rows("before", inbox=CLEAN), rows("after", inbox="·,·,T5,·,·,·,·"))
        env = {"PATH": "/usr/bin:/bin", "LC_ALL": "en_US.ISO8859-1", "LANG": "en_US.ISO8859-1", "PYTHONUTF8": "0"}
        r = self.cmd("check", env=env)
        self.assertEqual((r.returncode, r.stdout.strip()), (1, "inbox book: clean before, T5 after"), r.stderr)

    def test_one_shot_recorded_from_another_folder_does_not_hide_the_rest(self):
        self.tables(rows("before", inbox=CLEAN, message=CLEAN), rows("after", inbox=CLEAN, message="·,·,T5,·,·,·,·"))
        for screen in ("inbox", "message"):
            for kind in ("before", "after"):
                for pose in ("book", "laptop"):
                    self.cmd_ok("shot", kind, screen, pose, f".duo/captures/App/{kind}/{screen}-{pose}-inner.png")
        self.tables(rows("before", inbox=CLEAN), None, folder="probe")   # the first cell's shot, from a probe
        self.cmd_ok("shot", "before", "inbox", "book", str(self.repo / "probe" / "before" / "inbox-book-inner.png"))
        self.assertIn("message book: clean before, T5 after", self.cmd("check").stdout)

    def test_rows_from_another_folder_in_the_table_are_ignored(self):
        self.tables(rows("before", inbox=CLEAN), rows("after", inbox=CLEAN) + "| probe/inbox | T5 | T5 | T5 | T5 | T5 | T5 | T5 |\n")
        self.cmd_ok("done", "inbox: verified")


class NewClasses(Run):
    """A1: in a pose that had findings before, a class the after capture has and the before one did not is a regression
    too (Wikipedia's T1 T5 that became T14)."""

    def test_a_new_class_where_there_were_findings_is_refused_until_waived(self):
        self.tables(rows("before", inbox="·,·,T1 T5,·,·,T5,·"), rows("after", inbox="·,·,T14,·,·,T14,·"))
        before = self.file.read_text()
        r = self.cmd("done", "inbox: split")
        self.assertEqual(r.returncode, 1)
        self.assertIn("inbox book: T1 T5 before, T14 after (T14 is new)", r.stderr)
        self.assertIn("inbox flat-sideways: T5 before, T14 after (T14 is new)", r.stderr)
        self.assertIn("progress.py waive", r.stderr)
        self.assertEqual(self.file.read_text(), before)
        self.assertEqual(self.cmd("phase", "done").returncode, 1)
        r = self.cmd("check")
        self.assertEqual((r.returncode, r.stdout.splitlines()),
                         (1, ["inbox book: T1 T5 before, T14 after (T14 is new)",
                              "inbox flat-sideways: T5 before, T14 after (T14 is new)"]))
        self.cmd_ok("waive", "inbox", "book", "T14", "the bar's items sit beside the fold, not on it")
        self.assertEqual(self.cmd("check").stdout.strip(), "inbox flat-sideways: T5 before, T14 after (T14 is new)")
        self.cmd_ok("waive", "inbox", "flat-sideways", "T14", "the bar's items sit beside the fold, not on it")
        self.cmd_ok("done", "inbox: split")
        self.reviewed()
        self.cmd_ok("phase", "done")

    def test_only_the_new_classes_are_named_and_a_kept_one_is_not(self):
        self.tables(rows("before", inbox="·,·,T1,·,·,·,·"), rows("after", inbox="·,·,T1 T7 T14,·,·,·,·"))
        self.assertEqual(self.cmd("check").stdout.strip(), "inbox book: T1 before, T1 T7 T14 after (T7 T14 are new)")
        self.cmd_ok("waive", "inbox", "book", "T7", "the overlay has Close on the cover")
        self.assertEqual(self.cmd("check").stdout.strip(), "inbox book: T1 before, T1 T7 T14 after (T14 is new)")

    def test_a_pose_not_captured_before_blocks_only_a_finding_after(self):
        # no-rotate before is a captured finding (the app kept the other orientation); n/a before is a skipped cell,
        # so a finding after there cannot be told from a regression.
        self.tables(rows("before", inbox="·,·,n/a,no-rotate,n/a,·,·"), rows("after", inbox="·,·,T14,T5,·,·,·"))
        self.assertEqual(self.cmd("check").stdout.strip().splitlines()[0],
                         "inbox book: not captured before, T14 after (capture the pose into before from the commit "
                         "the migration started from, to tell whether it is new)")
        self.assertNotEqual(self.cmd("done", "inbox: split").returncode, 0)
        self.cmd_ok("waive", "inbox", "book", "T14", "the bar's items sit beside the fold, not on it")
        self.cmd_ok("done", "inbox: split")


class Issues(Run):
    """A2: what review, a look or a test found that no detector table shows, kept as issues; an open regression keeps
    its screen from done and the run from phase done."""

    def test_add_fix_and_wontfix_and_ids_never_reused(self):
        r = self.cmd_ok("issue", "add", "Inbox", "book,laptop", "medium", "the search field sits under the fold",
                        "--regression", "--found-by", "review", "--where", "InboxView.swift:42")
        self.assertEqual(r.stdout.strip(), "I1")
        self.assertEqual(self.cmd_ok("issue", "add", "message", "-", "low", "the footer wraps").stdout.strip(), "I2")
        self.assertEqual(self.cmd_ok("issue", "add", "message", "inner", "high", "the list is cut", "--found-by",
                                     "test").stdout.strip(), "I3")
        m = self.progress()
        self.assertEqual(m["issues"][0], {"id": "I1", "screen": "inbox", "poses": ["book", "laptop"],
                                          "severity": "medium", "regression": True, "found_by": "review",
                                          "what": "the search field sits under the fold", "where": "InboxView.swift:42",
                                          "status": "open"})
        self.assertEqual((m["issues"][1]["poses"], m["issues"][1]["regression"], m["issues"][1]["found_by"]),
                         ([], False, "review"))
        self.assertNotIn("where", m["issues"][1])
        self.assertEqual(m["issues"][2]["poses"], ["book", "laptop", "tent", "flat-sideways", "flat-upright"])
        self.assertEqual([s["name"] for s in m["screens"]], ["inbox", "message"])   # an issue adds no screen
        self.assertTrue(any("issue I1 inbox book,laptop: medium regression" in line for line in m["log"]))
        self.cmd_ok("issue", "fix", "i1", "the field moved to the leading pane")
        self.cmd_ok("issue", "wontfix", "I2", "the same wrap on every iPhone; not the fold's")
        m = self.progress()
        self.assertEqual([(i["status"], i.get("note")) for i in m["issues"]],
                         [("fixed", "the field moved to the leading pane"),
                          ("wontfix", "the same wrap on every iPhone; not the fold's"), ("open", None)])
        self.assertEqual(self.cmd_ok("issue", "add", "inbox", "all", "low", "a second look").stdout.strip(), "I4")
        self.assertEqual(self.progress()["issues"][3]["poses"], self.progress()["poses"])

    def test_bad_input_changes_nothing(self):
        before = self.file.read_text()
        for args in (("add", "inbox", "bok", "low", "a typo in the pose"), ("add", "inbox", "book", "low", " "),
                     ("add", "Inbx", "book", "low", "a typo in the screen"),
                     ("add", "inbox", "book", "urgent", "no such severity"), ("fix", "I9", "no such issue"),
                     ("add", "inbox", "book", "low", "x", "--found-by", "luck")):
            with self.subTest(args=args):
                self.assertNotEqual(self.cmd("issue", *args).returncode, 0)
        self.cmd_ok("issue", "add", "inbox", "book", "low", "the badge is clipped")
        self.assertEqual(self.cmd("issue", "fix", "I1", " ").returncode, 1)
        self.assertEqual(self.progress()["issues"][0]["status"], "open")
        self.assertNotEqual(self.file.read_text(), before)

    def test_an_issue_names_a_screen_of_the_file(self):
        r = self.cmd("issue", "add", "Articles", "-", "high", "contents shows the last article", "--regression")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no screen named Articles, nothing changed: screens are inbox, message", r.stderr)
        self.assertNotIn("issues", self.progress())
        self.tables(rows("before", article=CLEAN), None)   # a screen the before table names
        self.assertEqual(self.cmd_ok("issue", "add", "ARTICLE", "-", "high", "contents shows the last article",
                                     "--regression").stdout.strip(), "I1")
        self.cmd_ok("screen", "about")                    # one the flows do not reach, added first
        self.cmd_ok("issue", "add", "about", "-", "low", "the version wraps")
        self.assertEqual([i["screen"] for i in self.progress()["issues"]], ["article", "about"])

    def test_an_open_regression_refuses_done_for_its_screen_and_phase_done(self):
        self.tables(rows("before", inbox=CLEAN, message=CLEAN), rows("after", inbox=CLEAN, message=CLEAN))
        self.cmd_ok("issue", "add", "message", "book", "medium", "the toolbar's Done is gone", "--regression")
        self.cmd_ok("done", "inbox: verified")   # another screen's issue does not hold this one
        line = "I1 message book: open regression (medium, found by review): the toolbar's Done is gone"
        r = self.cmd("check")   # the open regression alone fails the check
        self.assertEqual((r.returncode, r.stdout.splitlines()), (1, [line]))
        before = self.file.read_text()
        for args in (("done", "message: verified"), ("done", "inbox, MESSAGE: verified"), ("phase", "done")):
            with self.subTest(args=args):
                r = self.cmd(*args)
                self.assertEqual(r.returncode, 1)
                self.assertIn("I1 message book: open regression (medium, found by review): the toolbar's Done is gone",
                              r.stderr)
                self.assertIn("progress.py issue fix", r.stderr)
                self.assertEqual(self.file.read_text(), before)
        self.cmd_ok("issue", "fix", "I1", "Done is back in the trailing bar")
        r = self.cmd("check")
        self.assertEqual((r.returncode, r.stdout.splitlines()), (0, ["no regressions"]))
        self.cmd_ok("done", "message: verified")
        self.reviewed()
        self.cmd_ok("phase", "done")

    def test_issues_written_by_hand(self):
        # An entry missing its fields, or its status (so open), and an issues list left null
        self.tables(rows("before", inbox=CLEAN, message=CLEAN), rows("after", inbox=CLEAN, message=CLEAN))
        m = self.progress()
        m["issues"] = None
        self.file.write_text(json.dumps(m))
        self.assertEqual(self.cmd("check").returncode, 0)
        self.assertIn("0 open issues", self.cmd_ok("show").stdout)
        self.assertEqual(self.cmd_ok("issue", "add", "inbox", "-", "low", "the footer wraps").stdout.strip(), "I1")
        m = self.progress()
        m["issues"] += [{"id": "I2", "screen": "message", "regression": True, "what": "the bar is gone"},
                        {"screen": "message"}, "not an issue"]
        self.file.write_text(json.dumps(m))
        r = self.cmd("check")
        self.assertEqual((r.returncode, r.stdout.splitlines()), (1, [
            "I2 message: open regression (no severity, found by review): the bar is gone",
            "I1 inbox: open issue (low, found by review): the footer wraps",
            "(no id) message: open issue (no severity, found by review): "]))
        r = self.cmd("done", "message: verified")
        self.assertEqual(r.returncode, 1)
        self.assertIn("I2 message: open regression", r.stderr)
        self.cmd_ok("issue", "fix", "i2", "the bar is back")
        self.cmd_ok("done", "message: verified")
        self.assertEqual(self.cmd_ok("issue", "add", "inbox", "-", "low", "a third").stdout.strip(), "I3")

    def test_a_regression_is_never_wontfix(self):
        self.cmd_ok("issue", "add", "inbox", "-", "high", "rotating loses the selection", "--regression", "--found-by",
                    "test")
        before = self.file.read_text()
        r = self.cmd("issue", "wontfix", "I1", "rare")
        self.assertEqual(r.returncode, 1)
        self.assertIn("regression", r.stderr)
        self.assertEqual(self.file.read_text(), before)

    def test_check_lists_open_issues_after_the_detectors_and_only_regressions_fail_it(self):
        self.tables(rows("before", inbox=CLEAN), rows("after", inbox="·,·,T5,·,·,·,·"))
        self.cmd_ok("issue", "add", "inbox", "-", "low", "the footer wraps", "--found-by", "eye")
        self.cmd_ok("issue", "add", "inbox", "laptop,tent", "medium", "the sidebar is gone", "--regression",
                    "--where", "Root.swift:12")
        self.cmd_ok("issue", "add", "message", "book", "low", "the title truncates")
        r = self.cmd("check")
        self.assertEqual((r.returncode, r.stdout.splitlines()), (1, [
            "inbox book: clean before, T5 after",
            "I2 inbox laptop tent: open regression (medium, found by review, Root.swift:12): the sidebar is gone",
            "I1 inbox: open issue (low, found by eye): the footer wraps",
            "I3 message book: open issue (low, found by review): the title truncates"]))
        self.assertEqual(self.cmd("check", "message").stdout.splitlines(),
                         ["no regressions", "I3 message book: open issue (low, found by review): the title truncates"])
        self.assertEqual(self.cmd("check", "message").returncode, 0)
        self.cmd_ok("waive", "inbox", "book", "T5", "the row's value is a badge, not text")
        self.cmd_ok("issue", "fix", "I2", "the sidebar shows again in laptop and tent")
        r = self.cmd("check", "inbox")
        self.assertEqual((r.returncode, r.stdout.splitlines()),
                         (0, ["no regressions", "I1 inbox: open issue (low, found by eye): the footer wraps"]))
        self.cmd_ok("done", "inbox: verified")   # an open issue that is not a regression does not hold a screen

    def test_show_counts_the_open_issues(self):
        self.assertIn("0 open issues", self.cmd_ok("show").stdout.splitlines()[0])
        self.cmd_ok("issue", "add", "inbox", "-", "low", "the footer wraps")
        self.cmd_ok("issue", "add", "inbox", "book", "high", "the list is cut", "--regression")
        self.cmd_ok("issue", "add", "message", "book", "low", "the title truncates")
        self.cmd_ok("issue", "fix", "I3", "shorter title")
        self.assertTrue(self.cmd_ok("show").stdout.splitlines()[0].endswith(", 2 open issues (1 regression)"))


class FineAsIs(Run):
    """A3: a cell marked `unchanged` is proved by the accessibility snapshots beside its before and after shots."""

    def setUp(self):
        super().setUp()
        for kind in ("before", "after"):
            self.cmd_ok("shot", kind, "inbox", "book", f".duo/captures/App/{kind}/inbox-book-inner.png")
        self.cmd_ok("cell", "inbox", "book", "unchanged")

    def snaps(self, before, after, name="inbox-book"):
        for kind, snap in (("before", before), ("after", after)):
            if snap is not None:
                folder = self.repo / ".duo" / "captures" / "App" / kind
                folder.mkdir(parents=True, exist_ok=True)
                (folder / f"{name}.json").write_text(json.dumps(snap), encoding="utf-8")

    def test_a_layout_that_changed_is_refused_until_marked_verified(self):
        self.snaps(snapshot(), snapshot(cancel=(124.5, 112, 40, 40)))
        line = ('inbox book: fine as is, but the screen changed (1 element differs, e.g. "Cancel" button 76.7x36 → '
                '40x40)')
        before = self.file.read_text()
        r = self.cmd("done", "inbox: verified")
        self.assertEqual(r.returncode, 1)
        self.assertIn(line, r.stderr)
        self.assertIn("progress.py waive <screen> <pose> unchanged", r.stderr)
        self.assertEqual(self.file.read_text(), before)
        self.assertEqual(self.cmd("phase", "done").returncode, 1)
        r = self.cmd("check")
        self.assertEqual((r.returncode, r.stdout.splitlines()[1:]), (1, [line]))
        self.cmd_ok("done", "message: verified")   # only the screens a done line names
        self.cmd_ok("cell", "inbox", "book", "verified", "--label", "sheet rule")
        self.cmd_ok("done", "inbox: verified")
        self.reviewed()
        self.cmd_ok("phase", "done")

    def test_the_same_layout_passes_whatever_scrolls_or_the_keyboard_shows(self):
        self.snaps(snapshot(("button", "Edit", (600, 100, 44, 44))),
                   snapshot(("button", "Edit", (600, 100.0000001, 44.4, 43.6)),
                            cancel=(124.5, 114, 76.66666666666669, 36), rows=("Row 2", "Row 3"), key_x=300))
        r = self.cmd("check")
        self.assertEqual((r.returncode, r.stdout.splitlines()[1:]), (0, ["no regressions"]))
        self.cmd_ok("done", "inbox: verified")

    def test_a_frame_read_as_a_float_rounds_as_its_double_does(self):
        self.snaps(snapshot(cancel=(125.5, 114, 76.5, 36)), snapshot(cancel=(125.49999237060547, 114, 76.49999237, 36)))
        self.cmd_ok("done", "inbox: verified")

    def test_a_missing_snapshot_is_noted_and_does_not_hold_the_screen(self):
        for before, after in ((snapshot(), None), (None, snapshot()), (None, None)):
            with self.subTest(before=before is not None, after=after is not None):
                shutil.rmtree(self.repo / ".duo" / "captures", ignore_errors=True)
                self.snaps(before, after)
                r = self.cmd("check")
                self.assertEqual((r.returncode, r.stdout.splitlines()[1:]), (0, ["no regressions"]))
                self.assertIn("(inbox book: no snapshot to compare)", r.stderr)
                self.assertIn("(inbox book: no snapshot to compare)", self.cmd_ok("done", "inbox: verified").stderr)
                self.cmd_ok("done", "--remove", "inbox")

    def test_live_content_is_not_layout(self):
        # NetNewsWire's "Updated 6 minutes ago", IceCubesApp's keyboard placeholder, Wikipedia's pins at the map's edge
        # and the card the selected pin opens: each changed between two captures of a screen nobody changed
        def keyboard(snap, button_x, placeholder_x):
            w, h = snap["window"]
            snap["nodes"] += [{"type": "button", "parent": 5, "frame": [button_x, h - 100, 60, 40], "label": "shift"},
                              {"type": "other", "parent": 1, "frame": [placeholder_x, h - 300, w - 2 * placeholder_x,
                                                                         300], "identifier": "inputView"}]
            return snap

        world = ("map", None, (0, 0, 669, 951))
        cases = [
            ("a relative date", snapshot(("staticText", "Updated 6 minutes ago", (20, 54, 125.3, 14))),
             snapshot(("staticText", "Updated 11 minutes ago", (20, 54, 129, 14)))),
            ("a relative date in other words", snapshot(("staticText", "Updated 6 minutes ago", (20, 54, 125.3, 14))),
             snapshot(("staticText", "Updated 1 hour ago", (20, 54, 108, 14)))),
            ("a centred clock", snapshot(("staticText", "9:41", (300, 10, 40, 20))),
             snapshot(("staticText", "10:02", (296, 10, 48, 20)))),
            ("the keyboard", keyboard(snapshot(), 0, 75), keyboard(snapshot(), 20, 0)),
            ("the map", snapshot(world, ("other", "Anchorage, Alaska", (-63.67, 186.67, 65, 65)),
                                 ("other", "Monterrey", (275.67, 291.33, 65, 65)),
                                 ("link", "Monterrey\nCity in Nuevo León, Mexico", (188.38, 142.31, 240, 115.67))),
             snapshot(world, ("other", "Titanic", (611.67, 402.67, 65, 65)),
                      ("other", "Rio Grande", (297, 289, 65, 65)),
                      ("link", "Rio Grande\nMajor river", (209.81, 122.9, 240, 133.67)))),
        ]
        for what, before, after in cases:
            with self.subTest(what):
                self.snaps(before, after)
                r = self.cmd("check")
                self.assertEqual((r.returncode, r.stdout.splitlines()[1:]), (0, ["no regressions"]))

    def test_what_moves_on_its_own_is_told_apart_from_the_layout(self):
        world = ("map", None, (0, 0, 669, 951))
        cases = [
            (snapshot(("staticText", "Updated 6 minutes ago", (20, 54, 125, 14))),
             snapshot(("staticText", "Updated 6 minutes ago", (20, 80, 125, 14))),
             '"Updated 6 minutes ago" staticText at 20,54 → 20,80'),
            (snapshot(("staticText", "Updated 6 minutes ago", (20, 54, 125, 14))),
             snapshot(("staticText", "Updated 8 minutes ago", (20, 80, 125, 14))),
             '2 elements differ, e.g. "Updated 6 minutes ago" staticText gone'),
            (snapshot(("button", "Edit", (600, 100, 44, 44))), snapshot(("button", "Done", (600, 100, 52, 44))),
             '"Edit" button now "Done"'),
            (snapshot(world), snapshot(world, cancel=(124.5, 112, 40, 40)), '"Cancel" button 76.7x36 → 40x40'),
            (snapshot(world, ("button", "Results in this area", (294.67, 95, 172.67, 40))),
             snapshot(world, ("button", "Results in this area", (248, 95, 172.67, 40))),
             '"Results in this area" button at 294.7,95 → 248,95'),
            (snapshot(world, ("link", "Monterrey\nCity in Nuevo León, Mexico", (188, 142, 240, 116))), snapshot(world),
             '"Monterrey" link gone'),
        ]
        for before, after, words in cases:
            with self.subTest(words=words):
                self.snaps(before, after)
                r = self.cmd("check")
                self.assertEqual(r.returncode, 1)
                self.assertIn(words, r.stdout)

    def test_words_and_numbers_that_change_in_place(self):
        cases = [   # (before, after, what check says, or None for no difference)
            (("staticText", "3 unread", (580, 54, 40, 20)), ("staticText", "12 unread", (572, 54, 48, 20)), None),
            (("staticText", "Inbox", (20, 54, 50, 20)), ("staticText", "Archive", (20, 54, 70, 20)),
             '"Inbox" staticText now "Archive"'),
            (("staticText", "Updated 6 minutes ago", (20, 54, 125, 14)),
             ("staticText", "Updated 8 minutes ago", (20, 54, 125, 28)), '"Updated 6 minutes ago" staticText gone'),
            (("staticText", "Updated 6 minutes ago", (20, 54, 125, 14)),
             ("staticText", "Updated 8 minutes ago", (60, 54, 125, 14)), '"Updated 6 minutes ago" staticText gone'),
            (("staticText", "Add", (600, 100, 44, 20)), ("button", "Add", (600, 100, 44, 20)),
             '2 elements differ, e.g. "Add" staticText gone'),
        ]
        for old, new, words in cases:
            with self.subTest(old=old, new=new):
                self.snaps(snapshot(old), snapshot(new))
                r = self.cmd("check")
                if words is None:
                    self.assertEqual((r.returncode, r.stdout.splitlines()[1:]), (0, ["no regressions"]))
                else:
                    self.assertEqual(r.returncode, 1)
                    self.assertIn(words, r.stdout)

    def test_the_map_leaves_out_only_its_pins_and_their_cards(self):
        def places(*extra, pane=(0, 0, 669, 951)):
            snap = snapshot(("map", None, pane), *extra)
            pin = add(snap, "other", (-40, 300, 65, 65), identifier="pin")   # no label, off the window's edge
            return snap, pin

        before, _ = places()
        after, pin = places()
        after["nodes"][pin]["frame"] = [640, 500, 65, 65]
        self.snaps(before, after)
        r = self.cmd("check")
        self.assertEqual((r.returncode, r.stdout.splitlines()[1:]), (0, ["no regressions"]))
        cases = [
            # a control beside a map in a pane that overlaps its edge is the app's, not a pin
            (places(("button", "Show Sidebar", (310, 60, 44, 44)), pane=(330, 0, 339, 951))[0],
             places(pane=(330, 0, 339, 951))[0], '"Show Sidebar" button gone'),
            # a panel larger than a card that names a pin
            (places(("other", "Paris", (300, 300, 65, 65)), ("other", "Paris\nOpen article", (0, 700, 669, 200)))[0],
             places(("other", "Paris", (300, 300, 65, 65)), ("other", "Paris\nOpen article", (0, 500, 669, 200)))[0],
             '"Paris" other at 0,700 → 0,500'),
        ]
        for before, after, words in cases:
            with self.subTest(words=words):
                self.snaps(before, after)
                r = self.cmd("check")
                self.assertEqual(r.returncode, 1)
                self.assertIn(words, r.stdout)

    def test_the_rows_of_a_list_outside_scrolling_content_with_an_identifier(self):
        # IceCubesApp's sidebar, a list: it lost its empty section row and Timeline and Settings moved up 54 pt
        def sidebar(rows, feed_rows=(), nested=False):
            snap = snapshot()
            holder = add(snap, "scrollView", (0, 0, 476, 669)) if nested else 1
            side = add(snap, "collectionView", (0, 0, 476, 669), parent=holder)
            for y, ident in rows:
                add(snap, "cell", (20, y, 435, 44), parent=side, **({"identifier": ident} if ident else {}))
            feed = add(snap, "collectionView", (476, 0, 475, 669))
            for y, label in feed_rows:   # a feed's rows, with labels: content, never compared
                add(snap, "cell", (476, y, 475, 120), parent=feed, label=label, identifier="post")
            return snap

        self.snaps(sidebar([(91, None), (135, "rectangle.stack"), (179, "gear")], [(0, "Post 1")]),
                   sidebar([(81, "rectangle.stack"), (125, "gear")], [(0, "Post 7"), (120, "Post 8")]))
        r = self.cmd("check")
        self.assertEqual(r.returncode, 1)
        self.assertIn('2 elements differ, e.g. "rectangle.stack" cell at 20,135 → 20,81', r.stdout)
        self.snaps(sidebar([(135, "rectangle.stack")], [(0, "Post 1")]),
                   sidebar([(135, "rectangle.stack")], [(0, "Post 7"), (120, "Post 8")]))
        self.assertEqual(self.cmd("check").returncode, 0)
        self.snaps(sidebar([(135, "rectangle.stack")], nested=True), sidebar([(81, "rectangle.stack")], nested=True))
        self.assertEqual(self.cmd("check").returncode, 0)   # a list inside scrolling content scrolls with it

    def test_an_unreadable_snapshot_is_noted_and_does_not_hold_the_screen(self):
        folder = self.repo / ".duo" / "captures" / "App"
        good = json.dumps(snapshot())
        for text in ("", "[]", '{"window": [669, 951], "nodes": ["a node"]}', '{"window": [669, 951]}',
                     json.dumps(dict(snapshot(), nodes=snapshot()["nodes"][:3] + [{"type": "button", "parent": 99,
                                                                                   "frame": [0, 0, 1, 1]}]))):
            with self.subTest(text=text[:40]):
                for kind, body in (("before", good), ("after", text)):
                    (folder / kind).mkdir(parents=True, exist_ok=True)
                    (folder / kind / "inbox-book.json").write_text(body, encoding="utf-8")
                r = self.cmd("check")
                self.assertEqual((r.returncode, r.stdout.splitlines()[1:]), (0, ["no regressions"]), r.stderr)
                self.assertIn("(inbox book: snapshot unreadable, not compared:", r.stderr)
                self.cmd_ok("done", "inbox: verified")
                self.cmd_ok("done", "--remove", "inbox")
        numbered = [snapshot(), snapshot(cancel=(124.5, 112, 40, 40))]
        for snap in numbered:
            snap["nodes"][3]["label"] = 5   # a label that is a number, as a hand-written snapshot can hold
        self.snaps(*numbered)
        self.assertIn('"5" button 76.7x36 → 40x40', self.cmd("check").stdout)

    def test_a_waived_cell_passes(self):
        self.snaps(snapshot(), snapshot(("staticText", "Feed added", (270, 800, 130, 20))))
        self.assertIn('"Feed added" staticText new', self.cmd("check").stdout)
        self.assertEqual(self.cmd("done", "inbox: verified").returncode, 1)
        self.cmd_ok("waive", "inbox", "book", "unchanged", "a toast still showing from the step before")
        r = self.cmd("check")
        self.assertEqual((r.returncode, r.stdout.splitlines()[1:]), (0, ["no regressions"]))
        self.assertNotIn("inbox book", r.stderr)
        self.cmd_ok("done", "inbox: verified")

    def test_each_kind_of_difference_is_counted_once_and_said_plainly(self):
        cases = [
            (snapshot(("button", "Done", (600, 100, 44, 44))), snapshot(("button", "Done", (560, 100, 44, 44))),
             '1 element differs, e.g. "Done" button at 600,100 → 560,100'),
            (snapshot(("button", "Done", (600, 100, 44, 44))), snapshot(),
             '1 element differs, e.g. "Done" button gone'),
            (snapshot(), snapshot(("button", "Close", (600, 100, 44, 44)), ("image", "xmark", (610, 110, 24, 24))),
             '2 elements differ, e.g. "Close" button new'),
            (snapshot(), snapshot(window=(951, 669)), "elements differ, e.g. the window 669x951 → 951x669"),
            (snapshot(("link", "Monterrey\nCity in Nuevo León, Mexico", (188, 142, 240, 116))), snapshot(),
             '1 element differs, e.g. "Monterrey" link gone'),
        ]
        for before, after, words in cases:
            with self.subTest(words=words):
                self.snaps(before, after)
                r = self.cmd("check")
                self.assertEqual(r.returncode, 1)
                self.assertIn(words, r.stdout)

    def test_a_cover_shot_finds_its_snapshot_and_only_unchanged_cells_are_compared(self):
        for kind in ("before", "after"):
            self.cmd_ok("shot", kind, "inbox", "closed", f".duo/captures/App/{kind}/inbox-closed-cover.png")
        self.cmd_ok("cell", "inbox", "closed", "unchanged")
        self.snaps(snapshot(window=(466, 678)), snapshot(window=(466, 678), cancel=(20, 54, 40, 40)),
                   name="inbox-closed")
        self.snaps(snapshot(), snapshot(cancel=(124.5, 112, 40, 40)))
        self.cmd_ok("cell", "inbox", "book", "migrated")
        r = self.cmd("check")
        self.assertEqual(r.stdout.splitlines()[1:], ['inbox closed: fine as is, but the screen changed (1 element '
                                                     'differs, e.g. "Cancel" button 76.7x36 → 40x40)'])

    def test_nothing_is_written_beside_the_scripts(self):
        # same-screen.py is loaded from beside progress.py, which in the skill is tools/, mirrored into the plugin
        self.snaps(snapshot(), snapshot())
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONDONTWRITEBYTECODE", "PYTHONPYCACHEPREFIX")}
        r = self.cmd("check", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(HERE.glob("__pycache__/same*screen*")), [])


class GitRun(Run):
    """A Run whose repository is a git repository with one commit (App.swift), .duo/ excluded as the preflight
    excludes it."""

    def setUp(self):
        super().setUp()
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / ".git" / "info" / "exclude").write_text(".duo/\n")
        self.first = self.commit("Start", **{"App.swift": "import UIKit\n\nlet app = 1\n"})

    def commit(self, message, **files):
        for name, body in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", message)
        return git(self.repo, "rev-parse", "HEAD")

    def codeid(self, cwd=None, *args, env=None):
        r = subprocess.run([sys.executable, str(PROGRESS), *args, "codeid"], capture_output=True, text=True,
                           cwd=cwd or self.repo, env=env or GIT_ENV)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def expected(self):
        """The code identity as section 1a defines it, computed here with git and hashlib alone."""
        head = git(self.repo, "rev-parse", "HEAD")
        run = lambda *args: subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True,
                                           env=GIT_ENV).stdout
        diff = run("diff", "HEAD", "--full-index", "--binary", "--no-ext-diff", "--", ".", ":(exclude).duo")
        files = sorted(p for p in run("ls-files", "--others", "--exclude-standard", "-z", "--", ".",
                                      ":(exclude).duo").split(b"\0") if p)
        if not diff and not files:
            return head
        digest = hashlib.sha256(diff)
        for p in files:
            digest.update(p + b"\0" + (self.repo / os.fsdecode(p)).read_bytes())
        return f"{head}+{digest.hexdigest()[:16]}"

    def grow_object_store(self, count=20000):
        """Adds count unreachable blobs in one pack, as a fetch would: git's abbreviated ids grow past 7 hex."""
        blobs = "".join(f"blob\ndata {len(d)}\n{d}\n" for d in (f"blob number {i}\n" for i in range(count)))
        subprocess.run(["git", "-C", str(self.repo), "fast-import", "--quiet"], input=blobs, text=True, check=True,
                       env=GIT_ENV, capture_output=True)

    def captured(self, *lines, folder=".duo/captures/App/after"):
        (self.repo / folder).mkdir(parents=True, exist_ok=True)
        (self.repo / folder / ".captured").write_text("".join(line + "\n" for line in lines))


class CodeIdentity(GitRun):
    """1a: `progress.py codeid`, the one implementation the captures call."""

    def test_the_head_when_nothing_outside_duo_is_uncommitted(self):
        head = git(self.repo, "rev-parse", "HEAD")
        self.assertRegex(head, r"^[0-9a-f]{40}$")
        self.assertEqual(self.codeid(), head)
        (self.repo / ".duo" / "PLAN.md").write_text("# Plan\n")   # .duo/ is never code
        (self.repo / ".duo" / "captures").mkdir()
        self.assertEqual(self.codeid(), head)

    def test_uncommitted_changes_add_a_hash_of_the_diff_and_the_untracked_files(self):
        head = git(self.repo, "rev-parse", "HEAD")
        (self.repo / "App.swift").write_text("import UIKit\n\nlet app = 2\n")
        changed = self.codeid()
        self.assertRegex(changed, rf"^{head}\+[0-9a-f]{{16}}$")
        self.assertEqual(changed, self.expected())
        git(self.repo, "add", "App.swift")   # staged is uncommitted too
        self.assertEqual(self.codeid(), changed)
        (self.repo / "Duo Fold.swift").write_text("struct Fold {}\n")   # an untracked file, a space in its name
        with_new = self.codeid()
        self.assertNotEqual(with_new, changed)
        self.assertEqual(with_new, self.expected())
        (self.repo / "Duo Fold.swift").write_text("struct Fold { let x = 1 }\n")   # its bytes count, not its name only
        self.assertNotEqual(self.codeid(), with_new)
        self.assertEqual(self.codeid(), self.expected())

    def test_a_binary_file_edited_twice_has_two_identities(self):
        (self.repo / "Icon.png").write_bytes(b"\x89PNG\0\1\2")
        git(self.repo, "add", "Icon.png")
        git(self.repo, "commit", "-q", "-m", "Add the icon")
        (self.repo / "Icon.png").write_bytes(b"\x89PNG\0\3\4")
        one = self.codeid()
        (self.repo / "Icon.png").write_bytes(b"\x89PNG\0\5\6")   # without --binary both read "Binary files differ"
        two = self.codeid()
        self.assertNotEqual(one, two)
        self.assertEqual(two, self.expected())

    def test_the_same_tree_has_the_same_identity_whatever_gits_configuration(self):
        # Two hunks in one file, a blank context line, a staged rename and a path git quotes: what each key changes.
        self.commit("More", **{"Long.swift": "".join(f"line {i}\n\n" for i in range(40)), "Ünï.swift": "x\n"})
        (self.repo / "Long.swift").write_text("".join(f"line {i}{'!' if i in (5, 15) else ''}\n\n"
                                                      for i in range(40)))
        (self.repo / "Ünï.swift").write_text("x\ny\n")
        git(self.repo, "mv", "App.swift", "Main.swift")
        plain = self.codeid()
        self.assertEqual(plain, self.expected())
        order = self.repo / ".duo" / "order"
        order.write_text("Ünï.swift\nLong.swift\n")
        for key, value in (("diff.noprefix", "true"), ("diff.mnemonicPrefix", "true"), ("color.diff", "always"),
                           ("diff.relative", "true"), ("diff.external", "false"), ("diff.context", "10"),
                           ("diff.interHunkContext", "20"), ("diff.orderFile", str(order)),
                           ("diff.suppressBlankEmpty", "true"), ("diff.algorithm", "histogram"),
                           ("diff.renames", "false"), ("diff.indentHeuristic", "false"), ("core.quotePath", "false"),
                           ("core.abbrev", "12")):
            with self.subTest(key=key):
                env = {**GIT_ENV, "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": key, "GIT_CONFIG_VALUE_0": value}
                self.assertEqual(self.codeid(env=env), plain)

    def test_the_same_tree_keeps_its_identity_as_the_object_store_grows(self):
        # git lengthens abbreviated ids as packed objects are added (a fetch): the index lines carry full ids.
        (self.repo / "App.swift").write_text("import UIKit\n\nlet app = 2\n")
        before = self.codeid()
        self.assertEqual(before, self.expected())
        self.grow_object_store()
        short = subprocess.run(["git", "-C", str(self.repo), "diff", "HEAD"], capture_output=True, text=True,
                               env=GIT_ENV).stdout
        self.assertRegex(short, r"(?m)^index [0-9a-f]{8,}\.\.")   # the abbreviation git would print has grown
        self.assertEqual(self.codeid(), before)

    def test_ignored_files_and_duo_never_count(self):
        self.commit("Ignore builds", **{".gitignore": "build/\n"})
        head = git(self.repo, "rev-parse", "HEAD")
        (self.repo / "build").mkdir()
        (self.repo / "build" / "App.o").write_bytes(b"\0\1")
        (self.repo / ".duo" / "REPORT.md").write_text("report\n")
        self.assertEqual(self.codeid(), head)
        git(self.repo, "add", "-f", ".duo/REPORT.md")   # an older run tracked .duo/: its changes are not code either
        head = self.commit("Track the report")
        (self.repo / ".duo" / "REPORT.md").write_text("report, changed\n")
        self.assertEqual(self.codeid(), head)

    def test_none_outside_git_and_before_the_first_commit(self):
        bare = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, bare)
        (bare / ".duo").mkdir()
        self.assertEqual(self.codeid(bare), "none")
        git(bare, "init", "-q")
        (bare / "a.swift").write_text("x\n")
        self.assertEqual(self.codeid(bare), "none")

    def test_the_repository_holding_duo_from_anywhere_inside_it(self):
        (self.repo / "Sources" / "Deep").mkdir(parents=True)
        (self.repo / "App.swift").write_text("changed\n")
        here = self.codeid()
        self.assertEqual(self.codeid(self.repo / "Sources" / "Deep"), here)   # no --file: finds .duo/ above
        self.assertEqual(self.codeid(self.repo / "Sources", "--file", str(self.file)), here)
        shutil.rmtree(self.repo / ".duo")   # no .duo/ at all: the current folder's repository, whole
        self.assertEqual(self.codeid(self.repo / "Sources"), here)


class VerifiedKeepsItsFinding(Run):
    """1c: a cell marked verified whose after table still has the class it had before."""

    def test_a_verified_cell_with_its_old_class_is_refused_until_waived_or_left_finding(self):
        self.tables(rows("before", inbox="·,·,T7 T14,T7,·,·,·"), rows("after", inbox="·,·,T7,·,·,·,·"))
        self.cmd_ok("cell", "inbox", "book,laptop", "verified")
        line = ("inbox book is verified but T7 is still in the after table: leave it finding, fix it, or waive it "
                "with why")
        r = self.cmd("check")
        self.assertEqual((r.returncode, r.stdout.splitlines()), (1, [line]))
        before = self.file.read_text()
        r = self.cmd("done", "inbox: split")
        self.assertEqual(r.returncode, 1)
        self.assertIn(line, r.stderr)
        self.assertIn("progress.py cell <screen> <pose> finding", r.stderr)
        self.assertEqual(self.file.read_text(), before)
        self.cmd_ok("cell", "inbox", "book", "finding")   # left as a finding: not a claim of verified
        self.cmd_ok("done", "inbox: split")
        self.cmd_ok("done", "--remove", "inbox")
        self.cmd_ok("cell", "inbox", "book", "verified")
        self.cmd_ok("waive", "inbox", "book", "T7", "the overlay has Close on the cover")
        self.cmd_ok("done", "inbox: split")

    def test_several_kept_classes_are_named_together(self):
        self.tables(rows("before", inbox="·,·,T1 T5 T7,·,·,·,·"), rows("after", inbox="·,·,T1 T7,·,·,·,·"))
        self.cmd_ok("cell", "inbox", "book", "verified")
        self.assertEqual(self.cmd("check").stdout.strip(),
                         "inbox book is verified but T1 T7 are still in the after table: leave it finding, fix it, or "
                         "waive it with why")


    def test_a_verified_cell_where_no_detector_ran_after_is_refused_and_never_waived(self):
        self.tables(rows("before", inbox="·,·,T7,T7,T7,·,·"), rows("after", inbox="·,·,n/a,no-rotate,·,·,·"))
        self.cmd_ok("cell", "inbox", "book,laptop,tent", "verified")
        self.cmd_ok("waive", "inbox", "book,laptop", "T7", "the overlay has Close on the cover")
        lines = [f"inbox {pose} is verified but no detector ran after: capture it into the after folder"
                 for pose in ("book", "laptop")]
        r = self.cmd("check")
        self.assertEqual((r.returncode, r.stdout.splitlines()), (1, lines))
        r = self.cmd("done", "inbox: split")
        self.assertEqual(r.returncode, 1)
        self.assertIn("No detector ran after (not captured, or no-rotate) on a pose with a finding before, verified "
                      "or fine as is: capture it into the after folder", r.stderr)
        self.tables(None, rows("after", message=CLEAN))   # no row for inbox at all
        r = self.cmd("check", "inbox")
        self.assertEqual(r.returncode, 1)
        self.assertEqual([line for line in r.stdout.splitlines() if "is verified" in line],
                         lines + ["inbox tent is verified but no detector ran after: capture it into the after "
                                  "folder"])


    def test_a_pose_with_a_finding_before_marked_unchanged_where_no_detector_ran_after_is_refused(self):
        # The audit may mark a cell fine as is when its detector line is not borne out; if the after capture then
        # skips the pose, nothing shows it fine, and leaving it unchanged is no way round the rule above.
        self.tables(rows("before", inbox="T10,·,T7,T7,·,·,·"), rows("after", inbox="n/a,·,no-rotate,·,·,·,·"))
        self.cmd_ok("cell", "inbox", "all", "verified")
        self.cmd_ok("cell", "inbox", "closed,book", "unchanged")
        self.cmd_ok("waive", "inbox", "closed", "unchanged", "the toast moved")
        self.reviewed()
        lines = [f"inbox {pose} is unchanged but no detector ran after: capture it into the after folder"
                 for pose in ("closed", "book")]
        r = self.cmd("check", "inbox")
        self.assertEqual((r.returncode, r.stdout.splitlines()), (1, lines))
        for args in (("done", "inbox: Fold-aligned split, 5 verified, 2 unchanged"), ("phase", "done")):
            r = self.cmd(*args)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn(lines[0], r.stderr)
            self.assertIn("verified or fine as is with nothing run after", r.stderr)
        self.tables(None, rows("after", message=CLEAN))   # no row for inbox at all
        r = self.cmd("check", "inbox")
        self.assertEqual([line for line in r.stdout.splitlines() if "no detector ran after" in line],
                         lines[:1] + ["inbox book is unchanged but no detector ran after: capture it into the after "
                                      "folder", "inbox laptop is verified but no detector ran after: capture it into "
                                      "the after folder"])
        self.tables(None, rows("after", inbox="·,·,·,·,·,·,·"))   # captured after: the clean poses pass
        self.assertEqual(self.cmd("check", "inbox").returncode, 0)


class DoneLineWords(Run):
    """1d: a done line that says verified in every pose says what the cells say."""

    def test_every_pose_verified_needs_every_cell_verified(self):
        self.cmd_ok("screen", "inbox", "--pattern", "Fold-aligned split (sheet rule)")
        self.cmd_ok("cell", "inbox", "all", "unchanged")
        self.cmd_ok("cell", "inbox", "book", "verified")
        before = self.file.read_text()
        for line in ("inbox: sheet rule, verified in every pose", "inbox: Verified in all poses",
                     "inbox: verified in all seven poses", "inbox: EVERY POSE verified"):
            with self.subTest(line=line):
                r = self.cmd("done", line)
                self.assertEqual(r.returncode, 1)
                self.assertIn("the cells say inbox: Fold-aligned split (sheet rule), 1 verified, 6 unchanged", r.stderr)
                self.assertIn("progress.py done --remove", r.stderr)
                self.assertEqual(self.file.read_text(), before)
        for line in ("inbox: Fold-aligned split (sheet rule), 1 verified, 6 unchanged",
                     "inbox: unchanged in every pose", "inbox: verified in book, unchanged in every other pose"):
            with self.subTest(line=line):
                self.cmd_ok("done", line)
        self.cmd_ok("cell", "inbox", "all", "verified")
        self.cmd_ok("done", "inbox: verified in every pose")

    def test_check_lists_a_done_line_already_written_and_phase_done_refuses(self):
        self.cmd_ok("cell", "inbox", "all", "verified")
        self.cmd_ok("cell", "message", "laptop,tent", "finding")
        self.edit(done=["inbox and message: Fold-aligned split, verified in every pose"])
        r = self.cmd("check", "inbox")
        self.assertEqual((r.returncode, r.stdout.splitlines()[1:]), (1, [
            'done line "inbox and message: Fold-aligned split, verified in every po…" says verified in every pose, but '
            "the cells say message: 2 finding, 5 pending"]))
        self.reviewed()
        r = self.cmd("phase", "done")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Done lines that say more than the cells:", r.stderr)
        self.cmd_ok("done", "--remove", "inbox and message")
        self.cmd_ok("phase", "done")


class CitedCommits(GitRun):
    """1e: every commit a done line, an issue, a moved record or PLAN.md's made: lines cite is on the branch."""

    def test_an_amended_commit_is_refused_and_the_one_on_the_branch_named(self):
        old = self.commit("Duo: split", **{"Split.swift": "split\n"})
        git(self.repo, "commit", "-q", "--amend", "-m", "Adapt the split to iPhone Duo")
        new = git(self.repo, "rev-parse", "HEAD")
        # The shortest prefix the gate reads as a commit: 7 or more characters with a digit and a letter (an all-digit
        # 7-character prefix, about 1 in 27, is not read as one).
        cite = next(old[:n] for n in range(7, 41) if re.search(r"\d", old[:n]) and re.search("[a-f]", old[:n]))
        line = f"inbox: split ({cite})"
        before = self.file.read_text()
        r = self.cmd("done", line)
        self.assertEqual(r.returncode, 1)
        self.assertIn(f'done line "{line}" cites {cite}, which is not on this branch (an amended or rebased '
                      f'commit?): cite {new[:7]} ("Adapt the split to iPhone Duo")', r.stderr)
        self.assertIn("Never amend or rebase a commit once it is cited", r.stderr)
        self.assertEqual(self.file.read_text(), before)
        self.cmd_ok("done", f"inbox: split ({new[:7]}, after {self.first})")

    def test_issues_moved_records_and_the_plan_are_read_too(self):
        gone = "0123abcd"   # never a commit here
        self.cmd_ok("issue", "add", "inbox", "-", "low", f"the footer wraps since {gone}")
        self.cmd_ok("issue", "fix", "I1", f"fixed in {self.first[:9]}")
        self.edit(moved=[{"screen": "message", "pose": "book", "control": "Share", "to": f"More ({gone})",
                          "evidence": "App.swift:1", "kind": "code"}])
        (self.repo / ".duo" / "PLAN.md").write_text(f"# Plan\n\n1. **inbox → split** made: {gone}.\n"
                                                    f"2. **message → sheet** made: {self.first[:7]}.\n")
        r = self.cmd("check")
        cites = [line for line in r.stdout.splitlines() if " cites " in line]
        tail = ", which is not on this branch (an amended or rebased commit?): cite the commit on this branch that " \
               "holds the change"
        self.assertEqual(cites, [f"issue I1 cites {gone}{tail}",
                                 f'moved record message book "Share" cites {gone}{tail}',
                                 f".duo/PLAN.md:3 cites {gone}{tail}"])
        self.assertEqual([line for line in self.cmd("check", "inbox").stdout.splitlines() if " cites " in line],
                         [f"issue I1 cites {gone}{tail}"])   # PLAN.md only for the whole run

    def test_what_only_looks_like_a_commit_is_not_read_as_one(self):
        self.cmd_ok("cell", "inbox", "all", "verified")
        words = ("deadbeef", "1234567", "UDID e271ee52-72ae-44cd-a2d1-3290c5104761",
                 f"code {self.first}+0123456789abcdef", "flow " + "ab12" * 16, "pt 44.5", "abc12")
        self.cmd_ok("done", "inbox: " + ", ".join(words))
        self.assertNotIn(" cites ", self.cmd("check").stdout)

    def test_outside_git_a_note(self):
        shutil.rmtree(self.repo / ".git")
        r = self.cmd_ok("done", "inbox: split (0123abcd)")
        self.assertIn("not a git repository", r.stderr)


class ProofFromFinalCode(GitRun):
    """1f: a verified or unchanged cell's after shot is captured from the code as it is now."""

    def setUp(self):
        super().setUp()
        self.tables(rows("before", inbox=CLEAN), rows("after", inbox=CLEAN))
        for kind in ("before", "after"):
            self.cmd_ok("shot", kind, "inbox", "book", f".duo/captures/App/{kind}/inbox-book-inner.png")
        self.cmd_ok("cell", "inbox", "book", "verified")
        self.sha = "f" * 64

    def stale(self):
        return [line for line in self.cmd("check").stdout.splitlines() if "after shot" in line]

    def test_the_same_code_passes_and_a_commit_since_is_refused(self):
        self.captured(f"{self.sha} inbox book {self.codeid()}")
        self.assertEqual(self.stale(), [])
        self.cmd_ok("done", "inbox: split")
        self.commit("Adapt the inbox", **{"App.swift": "changed\n", "Inbox.swift": "inbox\n"})
        line = (f"inbox book: its after shot is from {self.first[:7]} and 2 files changed since (App.swift, "
                f"Inbox.swift): {AGAIN}")
        self.assertEqual(self.stale(), [line])
        r = self.cmd("done", "inbox: split")
        self.assertEqual(r.returncode, 1)
        self.assertIn(line, r.stderr)
        self.assertIn("waive <screen> <pose> stale", r.stderr)
        self.cmd_ok("waive", "inbox", "book", "stale", "Inbox.swift is the macOS target's")
        self.assertEqual(self.stale(), [])
        self.assertIn("waived inbox book stale: Inbox.swift is the macOS target's", self.cmd_ok("show").stdout)

    def test_a_commit_that_changes_nothing_outside_duo_is_the_same_proof(self):
        self.captured(f"{self.sha} inbox book {self.codeid()}")
        (self.repo / ".duo" / "PLAN.md").write_text("made\n")
        git(self.repo, "add", "-f", ".duo/PLAN.md")
        self.commit("Plan")
        self.commit("Nothing")
        self.assertEqual(self.stale(), [])

    def test_uncommitted_code_then_or_now_is_stale(self):
        (self.repo / "App.swift").write_text("dirty\n")
        self.captured(f"{self.sha} inbox book {self.codeid()}")
        self.assertEqual(self.stale(), [])   # the same uncommitted code: the same identity
        now = self.commit("Adapt")
        self.assertEqual(self.stale(), [f"inbox book: its after shot is from {self.first[:7]} with uncommitted changes "
                                        f"and 1 file changed since (App.swift): {AGAIN}"])
        self.captured(f"{self.sha} inbox book {now}")
        (self.repo / "Extra.swift").write_text("new\n")
        self.assertEqual(self.stale(), [f"inbox book: its after shot is from {now[:7]} and 1 file changed since "
                                        f"(Extra.swift): {AGAIN}"])

    def test_uncommitted_code_keeps_its_proof_while_the_object_store_grows(self):
        (self.repo / "App.swift").write_text("dirty\n")
        self.captured(f"{self.sha} inbox book {self.codeid()}")
        self.grow_object_store()   # nothing edited: the same uncommitted code, the same proof
        self.assertEqual(self.stale(), [])

    def test_a_stale_waiver_holds_only_until_the_next_change(self):
        self.captured(f"{self.sha} inbox book {self.codeid()}")
        self.commit("Fix the message", **{"Message.swift": "message\n"})
        self.cmd_ok("waive", "inbox", "book", "stale", "Message.swift is the message screen's alone")
        at = git(self.repo, "rev-parse", "HEAD")
        self.assertEqual(self.progress()["screens"][0]["cells"]["book"]["waived_code"], {"stale": at})
        self.assertEqual(self.stale(), [])
        self.cmd_ok("done", "inbox: split")
        self.cmd_ok("done", "--remove", "inbox")
        self.commit("Change the inbox", **{"Inbox.swift": "inbox\n"})   # after the waiver: it does not cover this
        line = (f"inbox book: its after shot is from {self.first[:7]} and 2 files changed since (Inbox.swift, "
                f"Message.swift): {AGAIN} (waived at {at[:7]}; files changed since)")
        self.assertEqual(self.stale(), [line])
        self.assertIn(line, self.cmd("done", "inbox: split").stderr)
        self.edit(screens=[{**self.progress()["screens"][0], "cells": {"book": {
            **self.progress()["screens"][0]["cells"]["book"], "waived_code": {}}}}, self.progress()["screens"][1]])
        self.assertIn("(waived with no code identity: waive it again, with why)", self.stale()[0])   # written by hand
        self.cmd_ok("waive", "inbox", "book", "stale", "Inbox.swift and Message.swift are the iPad target's")
        self.assertEqual(self.stale(), [])

    def test_a_stale_waiver_given_on_uncommitted_code_says_it_ends_at_the_commit(self):
        self.captured(f"{self.sha} inbox book {self.codeid()}")
        (self.repo / "Mac.swift").write_text("mac\n")
        r = self.cmd_ok("waive", "inbox", "book", "stale", "Mac.swift is the macOS target's")
        note = ("(the code has uncommitted changes outside .duo/: a stale waiver keeps the code it was given at, so it "
                "ends at the next commit; commit first (step 6), then waive)")
        self.assertIn(note, r.stderr)
        self.assertEqual(self.stale(), [])
        self.commit("Add the macOS file")   # the same files, now committed: the waiver's code is not the code now
        self.assertTrue(self.stale()[0].endswith("; files changed since)"), self.stale())
        r = self.cmd_ok("waive", "inbox", "book", "stale", "Mac.swift is the macOS target's")
        self.assertNotIn("uncommitted", r.stderr)
        self.assertEqual(self.stale(), [])

    def test_a_capture_of_an_edit_then_discarded_is_stale(self):
        (self.repo / "App.swift").write_text("dirty\n")
        self.captured(f"{self.sha} inbox book {self.codeid()}")
        git(self.repo, "checkout", "--", "App.swift")
        self.assertEqual(self.stale(), [f"inbox book: its after shot is from {self.first[:7]} with uncommitted changes, "
                                        f"which the code now does not have: {AGAIN}"])

    def test_a_capture_stopped_mid_screen_leaves_no_proof(self):
        self.captured(f"{self.sha} message book {self.codeid()}")   # the stop removed inbox book's line and shot
        line = ("inbox book: its after shot is not there (a capture stopped mid-screen?): capture it again "
                "(SCREEN=inbox, same after folder)")
        self.assertEqual(self.stale(), [line])
        r = self.cmd("done", "inbox: split")
        self.assertEqual(r.returncode, 1)
        self.assertIn(line, r.stderr)
        shot = self.repo / ".duo/captures/App/after/inbox-book-inner.png"
        shot.write_bytes(b"png")   # the shot is there, from a capture that wrote no line: only noted
        r = self.cmd("check")
        self.assertEqual((r.returncode, self.stale()), (0, []))
        self.assertIn("(no code identity for inbox book)", r.stderr)
        shot.unlink()
        # The screen's only lines went with the stop (a one-screen flow), or the folder's other lines are from before
        # 0.8.1: the missing shot proves nothing all the same.
        for lines in ((), (f"{self.sha} message book",), (f"{self.sha} inbox book",)):
            with self.subTest(lines=lines):
                self.captured(*lines)
                self.assertEqual(self.stale(), [line])
        (self.repo / ".duo/captures/App/after/.captured").unlink()   # no .captured at all: only noted
        r = self.cmd("check")
        self.assertEqual((r.returncode, self.stale()), (0, []))
        self.assertIn("(no code identity for inbox book)", r.stderr)

    def test_a_shot_from_a_commit_no_longer_on_the_branch_is_stale(self):
        old = self.commit("Duo: inbox", **{"Inbox.swift": "inbox\n"})
        self.captured(f"{self.sha} inbox book {old}")
        git(self.repo, "commit", "-q", "--amend", "-m", "Adapt the inbox")
        self.assertEqual(self.stale(), [f"inbox book: its after shot is from {old[:7]}, which is not on this branch: "
                                        f"{AGAIN}"])

    def test_no_identity_is_noted_and_the_last_line_counts(self):
        r = self.cmd("check")   # no .captured
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("(no code identity for inbox book)", r.stderr)
        self.captured(f"{self.sha} inbox book")   # a capture before 0.8.1, its shot there
        (self.repo / ".duo/captures/App/after/inbox-book-inner.png").write_bytes(b"png")
        r = self.cmd("check")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("(no code identity for inbox book)", r.stderr)
        self.captured(f"{self.sha} inbox book {self.first}", f"{self.sha} message book {'0' * 40}",
                      f"{self.sha} inbox book {self.codeid()}")
        self.commit("Adapt", **{"App.swift": "changed\n"})
        self.captured(f"{self.sha} inbox book {self.first}", f"{self.sha} inbox book {self.codeid()}")
        r = self.cmd("check")
        self.assertEqual((r.returncode, self.stale()), (0, []))
        self.assertNotIn("no code identity", r.stderr)

    def test_only_cells_that_claim_a_proof_are_checked_and_a_screen_named_in_another_case(self):
        self.captured(f"{self.sha} inbox book {self.first}")
        self.commit("Adapt", **{"App.swift": "changed\n"})
        self.cmd_ok("cell", "inbox", "book", "finding")
        self.assertEqual(self.stale(), [])
        self.cmd_ok("cell", "inbox", "book", "unchanged")
        self.assertEqual(len(self.stale()), 1)
        m = self.progress()
        m["screens"][0]["name"] = "Inbox"   # the file's name; .captured has the flow's, as the shot's file name does
        self.file.write_text(json.dumps(m))
        self.assertEqual(len(self.stale()), 1)


class Review(GitRun):
    """1g: the independent review is on record before phase done."""

    def setUp(self):
        super().setUp()
        self.tables(rows("before", inbox=CLEAN), rows("after", inbox=CLEAN))

    def test_review_appends_with_the_code_it_saw(self):
        self.cmd_ok("review", "subagent", "given the diff and the captures; two regressions, recorded")
        (self.repo / "App.swift").write_text("changed\n")
        self.cmd_ok("review", "none", "no Agent tool in this session; told the person to run /foldsmith-review")
        reviews = self.progress()["reviews"]
        self.assertEqual([(r["kind"], r["codeid"]) for r in reviews], [("subagent", self.first),
                                                                       ("none", self.codeid())])
        self.assertTrue(reviews[1]["codeid"].startswith(self.first + "+"))
        self.assertEqual(reviews[0]["summary"], "given the diff and the captures; two regressions, recorded")
        datetime.datetime.fromisoformat(reviews[0]["at"])
        self.assertTrue(any("review subagent:" in line for line in self.progress()["log"]))
        self.assertEqual(self.cmd("review", "friend", "looked").returncode, 2)
        self.assertEqual(self.cmd("review", "session", " ").returncode, 1)

    def test_phase_done_is_refused_until_a_review_is_on_record(self):
        before = self.file.read_text()
        r = self.cmd("phase", "done")
        self.assertEqual(r.returncode, 1)
        self.assertIn('record the independent review (references/review.md): progress.py review subagent "…"; a '
                      "session that cannot start a subagent records none with why and tells the person to run "
                      "/foldsmith-review in a new session", r.stderr)
        self.assertEqual(self.file.read_text(), before)
        self.cmd_ok("review", "none", "no subagent could be started")
        self.cmd_ok("phase", "done")

    def test_check_counts_a_missing_review_from_verify_on_and_prints_the_latest(self):
        r = self.cmd("check")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "no regressions"))
        self.assertIn("(no independent review on record yet: phase done needs one", r.stderr)
        self.cmd_ok("phase", "verify")
        r = self.cmd("check")
        self.assertEqual((r.returncode, r.stdout.strip()), (1, NO_REVIEW))
        self.assertEqual(self.cmd("check", "inbox").returncode, 0)   # a screen's done does not wait on it
        self.cmd_ok("review", "subagent", "found nothing")
        r = self.cmd("check")
        self.assertEqual(r.returncode, 0)
        self.assertRegex(r.stdout.splitlines()[-1], rf"^review: subagent, \S+, saw {self.first[:7]}: found nothing$")
        self.assertNotIn("the last review saw", r.stderr)
        now = self.commit("Fix", **{"App.swift": "fixed\n"})
        self.assertIn(f"(the last review saw {self.first[:7]}, the code is now {now[:7]})", self.cmd("check").stderr)

    def test_a_regression_after_phase_done_reopens_the_run(self):
        self.cmd_ok("review", "subagent", "found nothing")
        self.cmd_ok("phase", "done")
        self.cmd_ok("issue", "add", "inbox", "-", "low", "the footer wraps")
        self.assertEqual(self.progress()["phase"], "done")
        r = self.cmd_ok("issue", "add", "inbox", "book", "high", "Share is gone", "--regression", "--found-by",
                        "review")
        self.assertEqual(r.stdout.strip(), "I2")
        self.assertIn("phase done → verify", r.stderr)
        m = self.progress()
        self.assertEqual(m["phase"], "verify")
        self.assertIn("phase verify: regression I2 found after phase done reopens the run", m["log"][-1])
        self.assertEqual(self.cmd("phase", "done").returncode, 1)
        self.cmd_ok("issue", "fix", "I2", "Share keeps a high visibilityPriority")
        self.cmd_ok("phase", "done")


class ShowSummary(Run):
    def test_show_counts_the_cells_and_lists_waivers_moved_controls_and_reviews(self):
        self.cmd_ok("cell", "inbox", "all", "unchanged")
        self.cmd_ok("cell", "inbox", "book", "verified")
        self.cmd_ok("cell", "message", "book,laptop", "finding")
        self.cmd_ok("waive", "inbox", "laptop", "unchanged", "a toast")
        self.edit(moved=[{"screen": "inbox", "pose": "book", "control": "Share", "to": "the top bar's More",
                          "evidence": "App.swift:3", "kind": "code"}])
        self.cmd_ok("review", "none", "no subagent could be started")
        out = self.cmd_ok("show").stdout.splitlines()
        self.assertIn("  cells: 1 verified, 6 unchanged, 7 left", out)
        self.assertIn("  waived inbox laptop unchanged: a toast", out)
        self.assertIn("  moved inbox book \"Share\" → the top bar's More: code App.swift:3", out)
        self.assertRegex(out[-1], r"^  review none, \S+, saw none: no subagent could be started$")


class ControlsGone(Run):
    """1b: a control the before snapshot has and the after one lost is brought back or recorded with `moved`."""

    def setUp(self):
        super().setUp()
        for kind in ("before", "after"):
            self.cmd_ok("shot", kind, "inbox", "laptop", f".duo/captures/App/{kind}/inbox-laptop-inner.png")
        self.cmd_ok("cell", "inbox", "laptop", "verified")
        (self.repo / "Sources").mkdir()
        (self.repo / "Sources" / "Article.swift").write_text("import UIKit\n\n    share.menuRepresentation = menu\n")
        self.share = ("button", "Share", (600, 880, 44, 38))
        self.line = 'inbox laptop: "Share" (before at 600,880 44×38) is gone'

    def snaps(self, before, after, name="inbox-laptop", folder=".duo/captures/App"):
        for kind, snap in (("before", before), ("after", after)):
            if snap is not None:
                (self.repo / folder / kind).mkdir(parents=True, exist_ok=True)
                (self.repo / folder / kind / f"{name}.json").write_text(json.dumps(snap), encoding="utf-8")

    def probe(self, *extra, name="inbox-laptop.json"):
        """A snapshot of a probe capture of the cell (SCREEN=inbox ONLY=laptop); its path in the repository."""
        folder = self.repo / ".duo" / "captures" / "App" / "probe"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(json.dumps(snapshot(*extra)), encoding="utf-8")
        return f".duo/captures/App/probe/{name}"

    def test_a_control_gone_is_refused_until_it_is_back(self):
        self.snaps(snapshot(self.share), snapshot())
        r = self.cmd("check")
        self.assertEqual((r.returncode, r.stdout.splitlines()[1:]), (1, [self.line]))
        before = self.file.read_text()
        for args in (("done", "inbox: split"), ("phase", "done")):
            with self.subTest(args=args):
                r = self.cmd(*args)
                self.assertEqual(r.returncode, 1)
                self.assertIn("Controls gone from the screen:\n  " + self.line, r.stderr)
                self.assertIn("Bring it back (visibilityPriority, a shorter title, a narrower neighbour)", r.stderr)
                self.assertIn('"the system probably overflows it" is not evidence', r.stderr)
                self.assertEqual(self.file.read_text(), before)
        self.snaps(snapshot(self.share), snapshot(("button", "Share", (300, 880, 44, 38))))   # back, elsewhere
        self.cmd_ok("done", "inbox: split")

    def test_the_fix_lines_evidence_path_is_one_moved_takes(self):
        self.snaps(snapshot(self.share), snapshot())
        out = self.cmd("controls").stdout
        given = re.search(r"the snapshot's path from the repository \((\S+)\)", out).group(1)
        self.assertEqual(given, ".duo/captures/<app>/after/<screen>-<pose>.json")
        (self.repo / ".duo/captures/App/after/inbox-laptop.json").write_text(
            json.dumps(snapshot(("menuItem", "Share", (20, 300, 200, 44)))))
        given = given.replace("<app>", "App").replace("<screen>", "inbox").replace("<pose>", "laptop")
        self.cmd_ok("moved", "inbox", "laptop", "Share", "the More menu", given)
        r = self.cmd("moved", "inbox", "laptop", "Share", "the More menu", "inbox-laptop.json")   # a bare name
        self.assertIn("inbox-laptop.json is not under .duo/captures/ in the repository", r.stderr)

    def test_the_same_identifier_or_label_is_the_same_control(self):
        cases = [
            ({"label": "Share", "identifier": "share"}, {"label": "Share Article", "identifier": "SHARE"}),
            ({"label": "Share", "identifier": "share"}, {"label": " share ", "identifier": "share.alt"}),
            ({"label": "Share"}, {"label": "SHARE"}),
            ({"identifier": "reader"}, {"identifier": "reader", "label": "Reader View"}),
        ]
        for old, new in cases:
            with self.subTest(old=old, new=new):
                before, after = snapshot(), snapshot()
                add(before, "button", (600, 880, 44, 38), **old)
                add(after, "button", (20, 880, 44, 38), **new)
                self.snaps(before, after)
                self.assertEqual(self.cmd("check").returncode, 0, self.cmd("check").stdout)
        before, after = snapshot(), snapshot()
        add(before, "button", (600, 880, 44, 38), label="Share", identifier="share")
        add(after, "button", (600, 880, 44, 38), label="Send", identifier="send")
        self.snaps(before, after)
        self.assertIn('inbox laptop: "Share" (before at 600,880 44×38) is gone', self.cmd("check").stdout)

    def test_only_controls_outside_scrolling_content_and_the_keyboard_count(self):
        before = snapshot(("staticText", "Title", (20, 100, 200, 20)), ("image", "star", (20, 130, 20, 20)))
        add(before, "button", (0, 150, 44, 44), parent=4, label="Row action")   # in the scroll view
        add(before, "button", (600, 880, 44, 38))                              # no label, no identifier
        add(before, "button", (0, 700, 60, 40), parent=5, label="shift")        # the keyboard's
        add(before, "link", (0, 200, 200, 20), parent=4, label="A link in the text")
        self.snaps(before, snapshot())
        r = self.cmd("check")
        self.assertEqual((r.returncode, r.stdout.splitlines()[1:]), (0, ["no regressions"]))
        for kind in ("switch", "segmentedControl", "searchField", "textField", "link", "menuButton", "popUpButton",
                     "slider", "stepper", "toggle", "secureTextField"):
            with self.subTest(kind=kind):
                self.snaps(snapshot((kind, "Mode", (20, 100, 200, 30))), snapshot())
                self.assertIn('inbox laptop: "Mode" (before at 20,100 200×30) is gone', self.cmd("check").stdout)

    def test_only_cells_neither_unchanged_nor_pending_are_compared(self):
        self.snaps(snapshot(self.share), snapshot())
        for state, gone in (("pending", False), ("unchanged", False), ("finding", True), ("migrated", True),
                            ("proposed", True), ("verified", True)):
            with self.subTest(state=state):
                self.cmd_ok("cell", "inbox", "laptop", state)
                out = self.cmd_ok("controls").stdout.splitlines()
                self.assertEqual(out, [f"{self.line}: not recorded", "1 gone, 0 recorded", out[-1]] if gone
                                 else ["no control gone"])

    def test_moved_with_a_shot_or_a_line_of_code(self):
        self.snaps(snapshot(self.share, ("button", "Next", (500, 880, 44, 38))), snapshot())
        shot = self.probe(("menuItem", "Share", (20, 300, 200, 44)))
        self.cmd_ok("moved", "inbox", "laptop", "share", "the toolbar's More", shot)
        self.cmd_ok("moved", "inbox", "laptop", "Next", "the toolbar's More", "Sources/Article.swift:3")
        self.assertEqual(self.progress()["moved"], [
            {"screen": "inbox", "pose": "laptop", "control": "share", "to": "the toolbar's More", "evidence": shot,
             "kind": "shot"},
            {"screen": "inbox", "pose": "laptop", "control": "Next", "to": "the toolbar's More",
             "evidence": "Sources/Article.swift:3", "kind": "code"}])
        r = self.cmd("check")
        self.assertEqual((r.returncode, r.stdout.splitlines()[1:]), (0, ["no regressions"]))
        self.assertEqual(self.cmd_ok("controls", "inbox").stdout.splitlines(), [
            f"{self.line}: moved to the toolbar's More (shot {shot})",
            'inbox laptop: "Next" (before at 500,880 44×38) is gone: moved to the toolbar\'s More (code '
            "Sources/Article.swift:3)",
            "2 gone, 2 recorded"])
        self.cmd_ok("done", "inbox: split")
        self.cmd_ok("moved", "inbox", "laptop", "Share", "the bar", str(self.repo / "Sources" / "Article.swift") + ":1")
        self.assertEqual([r["evidence"] for r in self.progress()["moved"]],   # replaced, stored relative
                         ["Sources/Article.swift:3", "Sources/Article.swift:1"])
        self.assertTrue(any("moved inbox laptop Share → the bar" in line for line in self.progress()["log"]))

    def test_a_relabelled_control_is_proven_by_its_new_label(self):
        self.snaps(snapshot(("button", "split view horizontally left", (24, 28, 40, 40))),
                   snapshot(("button", "enter full screen", (365, 28, 40, 40)),
                            ("button", "More", (481, 28, 40, 40))))
        self.snaps(None, snapshot(("button", "enter full screen", (365, 28, 40, 40)),
                                  ("button", "More", (481, 28, 40, 40))), name="inbox-tent")
        after = ".duo/captures/App/after/inbox-laptop.json"
        r = self.cmd("moved", "inbox", "laptop", "split view horizontally left", "relabelled", after)
        self.assertEqual(r.returncode, 1)
        self.assertIn('shows no control named "split view horizontally left"', r.stderr)
        r = self.cmd("moved", "inbox", "laptop", "split view horizontally left", "relabelled", after, "--as", "More")
        self.assertIn('"More" in .duo/captures/App/after/inbox-laptop.json is an overflow button', r.stderr)
        self.cmd_ok("moved", "inbox", "laptop", "split view horizontally left", "the same button, relabelled", after,
                    "--as", "enter full screen")
        self.assertEqual(self.progress()["moved"][0]["as"], "enter full screen")
        self.assertEqual(self.cmd("check").returncode, 0)
        before = snapshot(("button", "split view horizontally left", (24, 28, 40, 40)), self.share)
        self.snaps(before, None)
        r = self.cmd("moved", "inbox", "laptop", "Share", "relabelled", after, "--as", "enter full screen")
        self.assertIn('"enter full screen" is already "split view horizontally left" relabelled in inbox laptop, and '
                      "one control is not two", r.stderr)

    def test_evidence_that_does_not_hold_is_refused(self):
        self.snaps(snapshot(self.share), snapshot())
        (self.repo / "elsewhere").mkdir()
        (self.repo / "elsewhere" / "a.json").write_text(json.dumps(snapshot(self.share)))
        (self.repo / ".duo" / "notes.txt").write_text("one\ntwo\n")
        empty = self.probe(name="inbox-empty-laptop.json")
        outside = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside)
        (outside / "Article.swift").write_text("share\n")
        cases = [(".duo/captures/App/probe/none.json", "there is no snapshot"),
                 ("elsewhere/a.json", "is not under .duo/captures/"),
                 (".duo/captures/App/before/inbox-laptop.json", "is a before snapshot"),
                 (empty, 'shows no control named "Share"'),
                 ("Sources/Missing.swift:1", "there is no file Sources/Missing.swift"),
                 ("Sources/Article.swift:4", "has 3 lines, not a line 4"),
                 ("Sources/Article.swift:0", "has 3 lines, not a line 0"),
                 ("Sources/Article.swift:2", "line 2 of Sources/Article.swift is blank"),
                 (".duo/notes.txt:1", "there is no file .duo/notes.txt"),
                 (f"{outside}/Article.swift:1", "there is no file"),
                 ("Sources/Article.swift", "is neither a snapshot"),
                 ("probably in More", "is neither a snapshot")]
        before = self.file.read_text()
        for given, words in cases:
            with self.subTest(given=given):
                r = self.cmd("moved", "inbox", "laptop", "Share", "the toolbar's More", given)
                self.assertEqual(r.returncode, 1)
                self.assertIn("moved refused, nothing changed: ", r.stderr)
                self.assertIn(words, r.stderr)
                self.assertEqual(self.file.read_text(), before)

    def test_a_shot_proves_only_its_own_cell(self):
        # NetNewsWire's rerun: the cover's after snapshot, where Share still sits on the toolbar, passed for proof that
        # Share moved into the inner poses' More, which the tap runner cannot open.
        self.cmd_ok("screen", "inbox-search")
        self.snaps(snapshot(self.share), snapshot())
        self.snaps(snapshot(self.share), snapshot(), name="inbox-tent")
        for kind in ("before", "after"):
            self.cmd_ok("shot", kind, "inbox", "tent", f".duo/captures/App/{kind}/inbox-tent-inner.png")
        self.cmd_ok("cell", "inbox", "tent", "verified")
        after = self.repo / ".duo" / "captures" / "App" / "after"
        (after / "inbox-closed.json").write_text(json.dumps(snapshot(self.share)))   # the cover: Share on its bar
        (after / "message-laptop.json").write_text(json.dumps(snapshot(self.share)))
        other = self.probe(("menuItem", "Share", (20, 300, 200, 44)), name="inbox-search-laptop.json")
        before = self.file.read_text()
        for given in (".duo/captures/App/after/inbox-closed.json", ".duo/captures/App/after/message-laptop.json", other):
            with self.subTest(given=given):
                r = self.cmd("moved", "inbox", "laptop", "Share", "the top bar's More", given)
                self.assertEqual(r.returncode, 1)
                self.assertIn(f"{given} is not a snapshot of inbox laptop: a shot proves only its own pose, so give "
                              ".duo/captures/App/after/inbox-laptop.json (the after capture), or inbox-laptop.json "
                              "from a SCREEN=inbox ONLY=laptop probe of that cell", r.stderr)
                self.assertEqual(self.file.read_text(), before)
        shot = self.probe(("menuItem", "Share", (20, 300, 200, 44)), name="Inbox-Share-Menu-LAPTOP.json")
        r = self.cmd("moved", "inbox", "laptop,tent", "Share", "the top bar's More", shot)   # one shot for two poses
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"{shot} is not a snapshot of inbox tent", r.stderr)
        self.cmd_ok("moved", "inbox", "laptop", "Share", "the top bar's More", shot)
        self.edit(moved=self.progress()["moved"] + [
            {"screen": "inbox", "pose": "tent", "control": "Share", "to": "More",
             "evidence": ".duo/captures/App/after/inbox-closed.json", "kind": "shot"}])   # written by hand
        out = self.cmd("check").stdout
        self.assertIn('inbox tent: "Share" (before at 600,880 44×38) is gone; its moved record no longer holds: '
                      ".duo/captures/App/after/inbox-closed.json is not a snapshot of inbox tent", out)
        self.assertNotIn("inbox laptop", out)

    def test_a_relabelled_control_takes_a_label_the_before_snapshot_lacks(self):
        # NetNewsWire's rerun: Next Article "relabelled" as Reader View, a neighbour that was there before.
        self.snaps(snapshot(self.share, ("button", "Reader View", (545, 881, 44, 44))),
                   snapshot(("button", "Reader View", (600, 881, 44, 44))))
        after = ".duo/captures/App/after/inbox-laptop.json"
        before = self.file.read_text()
        r = self.cmd("moved", "inbox", "laptop", "Share", "relabelled", after, "--as", "reader view")
        self.assertEqual(r.returncode, 1)
        self.assertIn('"reader view" was already on the screen before; a relabelled control\'s new label is one the '
                      "before snapshot lacks (inbox laptop)", r.stderr)
        self.assertEqual(self.file.read_text(), before)
        self.edit(moved=[{"screen": "inbox", "pose": "laptop", "control": "Share", "to": "relabelled",
                          "evidence": after, "kind": "shot", "as": "Reader View"}])   # written by hand
        self.assertIn(f'{self.line}; its moved record no longer holds: "Reader View" was already on the screen '
                      "before", self.cmd("check").stdout)

    def test_an_overflow_button_by_its_identifier_is_never_a_relabelled_control(self):
        after = snapshot()
        add(after, "button", (481, 28, 40, 40), label="Actions", identifier="TopOverflowBarButtonItem")
        self.snaps(snapshot(self.share), after)
        r = self.cmd("moved", "inbox", "laptop", "Share", "relabelled", ".duo/captures/App/after/inbox-laptop.json",
                     "--as", "Actions")
        self.assertEqual(r.returncode, 1)
        self.assertIn('"Actions" in .duo/captures/App/after/inbox-laptop.json is an overflow button', r.stderr)

    def test_a_copy_of_a_before_snapshot_in_the_before_folder_is_refused(self):
        self.snaps(snapshot(self.share), snapshot())
        copy = ".duo/captures/App/before/inbox-share-laptop.json"   # a name of the cell, the before folder's
        (self.repo / copy).write_text(json.dumps(snapshot(self.share)))
        r = self.cmd("moved", "inbox", "laptop", "Share", "More", copy)
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"{copy} is a before snapshot", r.stderr)

    def test_code_evidence_is_a_line_of_a_file_git_tracks(self):
        self.snaps(snapshot(self.share), snapshot())
        git(self.repo, "init", "-q")
        (self.repo / ".git" / "info" / "exclude").write_text(".duo/\n")
        git(self.repo, "add", "Sources")
        git(self.repo, "commit", "-q", "-m", "Start")
        (self.repo / "proof.txt").write_text("Share is in More\n")
        before = self.file.read_text()
        for given, words in ((".git/config:1", ".git/config is git's own, not the app's source"),
                             ("proof.txt:1", "proof.txt is not tracked by git")):
            with self.subTest(given=given):
                r = self.cmd("moved", "inbox", "laptop", "Share", "More", given)
                self.assertEqual(r.returncode, 1)
                self.assertIn(words, r.stderr)
                self.assertIn("cite a line of a tracked source file", r.stderr)
                self.assertEqual(self.file.read_text(), before)
        self.cmd_ok("moved", "inbox", "laptop", "Share", "More", "Sources/Article.swift:3")

    def test_a_record_whose_control_is_back_is_noted_as_no_longer_needed(self):
        self.snaps(snapshot(self.share), snapshot())
        self.cmd_ok("moved", "inbox", "laptop", "Share", "the top bar's More", "Sources/Article.swift:3")
        self.snaps(None, snapshot(self.share))   # the control is back
        tail = 'no longer needed: the control is back; progress.py moved --remove inbox laptop "Share"'
        r = self.cmd_ok("controls")
        self.assertEqual(r.stdout.strip(), "no control gone")
        self.assertIn(f'(moved record inbox laptop "Share" {tail})', r.stderr)
        self.assertIn(f"  moved inbox laptop \"Share\" → the top bar's More: code Sources/Article.swift:3 ({tail})",
                      self.cmd_ok("show").stdout.splitlines())
        r = self.cmd("check")
        self.assertEqual(r.returncode, 0, r.stdout)   # a note, not counted
        self.assertIn(tail, r.stderr)

    def test_moved_names_a_control_gone_from_each_pose_it_names(self):
        self.snaps(snapshot(self.share), snapshot())
        self.snaps(snapshot(self.share), snapshot(self.share), name="inbox-book")
        for kind in ("before", "after"):
            self.cmd_ok("shot", kind, "inbox", "book", f".duo/captures/App/{kind}/inbox-book-inner.png")
        before = self.file.read_text()
        for args, words in [(("book,laptop", "Share"), '"Share" is not gone from inbox book'),
                            (("laptop", "Shar"), '"Shar" is not gone from inbox laptop'),
                            (("lap", "Share"), "no pose lap"), (("laptop", " "), "needs the control's label")]:
            with self.subTest(args=args):
                r = self.cmd("moved", "inbox", *args, "More", "Sources/Article.swift:3")
                self.assertEqual(r.returncode, 1)
                self.assertIn(words, r.stderr)
                self.assertEqual(self.file.read_text(), before)
        self.assertEqual(self.cmd("moved", "inbx", "laptop", "Share", "More", "Sources/Article.swift:3").returncode, 1)
        r = self.cmd_ok("moved", "inbox", "closed", "Share", "More", "Sources/Article.swift:3")   # no shots: said
        self.assertIn("no snapshots, so whether \"Share\" is gone there is not checked", r.stderr)

    def test_moved_remove_takes_a_record_back(self):
        self.snaps(snapshot(self.share), snapshot())
        self.cmd_ok("moved", "inbox", "laptop", "Share", "More", "Sources/Article.swift:3")
        self.assertEqual(self.cmd("check").returncode, 0)
        self.cmd_ok("moved", "--remove", "inbox", "laptop", "SHARE")
        self.assertEqual(self.progress()["moved"], [])
        self.assertIn(self.line, self.cmd("check").stdout)
        before = self.file.read_text()
        r = self.cmd("moved", "--remove", "inbox", "laptop", "Share")
        self.assertEqual(r.returncode, 1)
        self.assertIn('no moved record of "Share" on inbox laptop', r.stderr)
        self.assertEqual(self.file.read_text(), before)
        for args in (("inbox", "laptop", "Share"), ("inbox", "laptop", "Share", "More"),
                     ("--remove", "inbox", "laptop", "Share", "More", "Sources/Article.swift:3")):
            with self.subTest(args=args):
                self.assertEqual(self.cmd("moved", *args).returncode, 2)

    def test_a_record_whose_evidence_is_gone_no_longer_covers_it(self):
        self.snaps(snapshot(self.share), snapshot())
        shot = self.probe(("menuItem", "Share", (20, 300, 200, 44)))
        self.cmd_ok("moved", "inbox", "laptop", "Share", "More", "Sources/Article.swift:3")
        (self.repo / "Sources" / "Article.swift").write_text("import UIKit\n")
        self.assertIn(f"{self.line}; its moved record no longer holds: Sources/Article.swift has 1 lines, not a line 3",
                      self.cmd("check").stdout)
        self.cmd_ok("moved", "inbox", "laptop", "Share", "More", shot)
        (self.repo / shot).write_text(json.dumps(snapshot()))
        self.assertIn("its moved record no longer holds", self.cmd("check").stdout)
        r = self.cmd_ok("controls")
        self.assertIn("but the record no longer holds", r.stdout)

    def test_controls_changes_nothing_and_checks_its_screen_names(self):
        self.snaps(snapshot(self.share), snapshot())
        before = self.file.read_text()
        out = self.cmd_ok("controls", "Inbox").stdout.splitlines()
        self.assertEqual(out[:2], [f"{self.line}: not recorded", "1 gone, 0 recorded"])
        self.assertTrue(out[2].startswith("Bring it back"))
        self.assertEqual(self.cmd_ok("controls", "message").stdout.strip(), "no control gone")
        self.assertEqual(self.cmd("controls", "inbx").returncode, 2)
        self.assertEqual(self.file.read_text(), before)
        shutil.rmtree(self.repo / ".duo" / "captures")
        self.assertIn("(inbox laptop: no snapshot, its controls not compared)", self.cmd_ok("controls").stderr)


WIKIPEDIA_NEW_CLASSES = [   # the six cells where T1 or T5 became T14, which the run marked done
    "article book: T1 T5 T7 before, T14 after (T14 is new)",
    "article flat-sideways: T5 T7 before, T14 after (T14 is new)",
    "saved book: T1 T5 before, T14 after (T14 is new)",
    "saved flat-sideways: T5 before, T14 after (T14 is new)",
    "search book: T1 T5 before, T14 after (T14 is new)",
    "search flat-sideways: T5 before, T14 after (T14 is new)",
]
WIKIPEDIA_KEPT = [   # contents marked verified upright with the T7 it had before still in the after table
    f"contents {pose} is verified but T7 is still in the after table: leave it finding, fix it, or waive it with why"
    for pose in ("laptop", "tent", "flat-upright")]
CLAIMED = re.compile(r'done line ".+" says verified in every pose, but the cells say ([^:]+): Fold-aligned split, (.+)')
FINISHED_CLAIMS = {   # each done line "verified in every pose", and what that screen's cells say
    "NetNewsWire": [("timeline", "5 verified, 2 unchanged"), ("article", "5 verified, 2 unchanged"),
                    ("settings", "1 verified, 6 unchanged"), ("add-feed", "3 verified, 4 unchanged"),
                    ("feeds", "5 verified, 2 unchanged")],
    "IceCubesApp": [("add-account", "1 verified, 6 unchanged"), ("timeline", "7 unchanged"),
                    ("status", "1 verified, 6 unchanged"), ("settings", "4 verified, 3 unchanged"),
                    ("settings-display", "2 verified, 5 unchanged")],
    "Wikipedia": [],
}
NO_REVIEW = ('no independent review on record: record the independent review (references/review.md): progress.py '
             'review subagent "…"; a session that cannot start a subagent records none with why and tells the person '
             'to run /foldsmith-review in a new session')


class FinishedRuns(unittest.TestCase):
    """Every run in Tests/Fixtures/runs (copied from foldsmith-evidence's verification/runs), its progress file and
    detector tables laid out as its capture left them, in phase done. Their detectors still pass where they passed;
    since 0.8.1 each is refused for no review on record, NetNewsWire and IceCubesApp for done lines that say "verified
    in every pose" over cells left unchanged, and Wikipedia for the six cells where a class new to the pose (T14) took
    the place of T1 or T5 and the three contents cells marked verified with their T7 kept. The fixtures carry no
    snapshots, so their cells marked fine as is are only noted, and no git repository, so no commit is checked."""

    def test_the_finished_runs_against_their_tables(self):
        runs = sorted(p for p in RUNS.iterdir() if (p / "migration.json").exists())
        self.assertGreaterEqual(len(runs), 3)
        self.assertIn("Wikipedia", [run.name for run in runs])
        for run in runs:
            with self.subTest(run=run.name):
                repo = pathlib.Path(tempfile.mkdtemp())
                self.addCleanup(shutil.rmtree, repo)
                m = json.loads((run / "migration.json").read_text())
                (repo / ".duo").mkdir()
                (repo / ".duo" / "migration.json").write_text(json.dumps(m))
                for kind in ("before", "after"):
                    folder = repo / ".duo" / "captures" / m["app"] / kind
                    folder.mkdir(parents=True)
                    shutil.copy(run / f"detectors-{kind}.md", folder / "detectors.md")
                r = subprocess.run([sys.executable, str(PROGRESS), "--file", str(repo / ".duo" / "migration.json"),
                                    "check"], capture_output=True, text=True, env=GIT_ENV)
                lines = r.stdout.splitlines()
                self.assertEqual((r.returncode, lines[-1]), (1, NO_REVIEW), r.stderr)
                claims = [CLAIMED.fullmatch(line) for line in lines if line.startswith("done line ")]
                self.assertEqual([c.groups() for c in claims if c], FINISHED_CLAIMS.get(run.name, []))
                self.assertEqual(len(claims), len(FINISHED_CLAIMS.get(run.name, [])))
                rest = [line for line in lines[:-1] if not line.startswith("done line ")]
                self.assertEqual(rest, WIKIPEDIA_NEW_CLASSES + WIKIPEDIA_KEPT if run.name == "Wikipedia" else [])
                self.assertIn("no snapshot to compare", r.stderr)
                self.assertIn("not a git repository", r.stderr)


if __name__ == "__main__":
    unittest.main()
