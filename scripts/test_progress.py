#!/usr/bin/env python3
"""progress.py's checks: `done <screen>` and `phase done` refuse a screen worse than it started (a pose the detectors
found clean with a finding after, a class new in a pose that had findings, a cell marked fine as is whose layout moved,
an open regression issue), and the issues kept beside the detectors' tables.

    python3 -m unittest discover -s scripts -p 'test_*.py'
"""
import json
import os
import pathlib
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
                              capture_output=True, text=True, cwd=self.repo, env=env, encoding="utf-8")

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


class RegressionCheck(Run):
    def test_done_when_clean_poses_stay_clean(self):
        self.tables(rows("before", inbox="·,·,T14 T7,T1,·,·,·"), rows("after", inbox=CLEAN))
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
        self.cmd_ok("phase", "done")

    def test_only_the_new_classes_are_named_and_a_kept_one_is_not(self):
        self.tables(rows("before", inbox="·,·,T1,·,·,·,·"), rows("after", inbox="·,·,T1 T7 T14,·,·,·,·"))
        self.assertEqual(self.cmd("check").stdout.strip(), "inbox book: T1 before, T1 T7 T14 after (T7 T14 are new)")
        self.cmd_ok("waive", "inbox", "book", "T7", "the overlay has Close on the cover")
        self.assertEqual(self.cmd("check").stdout.strip(), "inbox book: T1 before, T1 T7 T14 after (T14 is new)")

    def test_a_pose_not_captured_before_has_nothing_to_compare(self):
        self.tables(rows("before", inbox="·,·,n/a,no-rotate,·,·,·"), rows("after", inbox="·,·,T14,T5,·,·,·"))
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


WIKIPEDIA_NEW_CLASSES = [   # the six cells where T1 or T5 became T14, which the run marked done
    "article book: T1 T5 T7 before, T14 after (T14 is new)",
    "article flat-sideways: T5 T7 before, T14 after (T14 is new)",
    "saved book: T1 T5 before, T14 after (T14 is new)",
    "saved flat-sideways: T5 before, T14 after (T14 is new)",
    "search book: T1 T5 before, T14 after (T14 is new)",
    "search flat-sideways: T5 before, T14 after (T14 is new)",
]


class FinishedRuns(unittest.TestCase):
    """Every run in Tests/Fixtures/runs (copied from foldsmith-evidence's verification/runs), its progress file and
    detector tables laid out as its capture left them: NetNewsWire and IceCubesApp pass with their published tables;
    Wikipedia is refused for the six cells where a class new to the pose (T14) took the place of T1 or T5. The fixtures
    carry no snapshots, so their cells marked fine as is are only noted."""

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
                                    "check"], capture_output=True, text=True)
                if run.name == "Wikipedia":
                    self.assertEqual((r.returncode, r.stdout.splitlines()), (1, WIKIPEDIA_NEW_CLASSES), r.stderr)
                else:
                    self.assertEqual((r.returncode, r.stdout.strip()), (0, "no regressions"), r.stderr)
                self.assertIn("no snapshot to compare", r.stderr)


if __name__ == "__main__":
    unittest.main()
