#!/usr/bin/env python3
"""progress.py's regression check: `done <screen>` and `phase done` refuse a screen worse than it started.

    python3 -m unittest discover -s scripts -p 'test_*.py'
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
PROGRESS = HERE / "progress.py"
RUNS = HERE.parent / "verification" / "runs"
HEAD = "| config | closed | closed-sideways | book | laptop | tent | flat-sideways | flat-upright |\n|---|---|---|---|---|---|---|---|\n"


def rows(kind, **screens):
    return HEAD + "".join(f"| {kind}/{name.replace('_', '-')} | {' | '.join(cells.split(','))} |\n"
                          for name, cells in screens.items())


CLEAN = "·,·,·,·,·,·,·"


class RegressionCheck(unittest.TestCase):
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

    def test_a_different_finding_where_there_was_one_is_not_a_regression(self):
        self.tables(rows("before", inbox="·,·,T1 T5,·,·,T5,·"), rows("after", inbox="·,·,T14,·,·,T14,·"))
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

    def test_a_done_line_that_names_no_captured_screen_is_not_checked(self):
        self.tables(rows("before", inbox=CLEAN), rows("after", inbox="·,·,T5,·,·,·,·"))
        self.cmd_ok("done", "T13: scene lifecycle adopted")
        self.cmd_ok("done", "--remove", "inbox")   # taking a line back is never refused

    def test_no_before_table_means_no_check_and_says_so(self):
        r = self.cmd_ok("done", "inbox: verified")
        self.assertIn("no regression check", r.stderr)
        self.assertEqual(self.cmd("check").returncode, 0)

    def test_check_lists_regressions_and_its_exit_code_says_whether_there_are_any(self):
        self.tables(rows("before", inbox=CLEAN, message=CLEAN), rows("after", inbox="T10,·,·,·,·,·,·", message=CLEAN))
        r = self.cmd("check")
        self.assertEqual((r.returncode, r.stdout.strip()), (1, "inbox closed: clean before, T10 after"))
        self.assertEqual(self.cmd("check", "message").stdout.strip(), "no regressions")
        self.assertEqual(self.cmd("check", "message").returncode, 0)

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


class FinishedRuns(unittest.TestCase):
    """Every run in verification/runs, its progress file and detector tables laid out as its capture left them, has no
    regression the check would refuse: the screens it finished pass, and Wikipedia's regressions were ones no detector
    sees."""

    def test_no_finished_run_is_refused(self):
        runs = sorted(p for p in RUNS.iterdir() if (p / "migration.json").exists())
        self.assertGreaterEqual(len(runs), 3)
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
                self.assertEqual((r.returncode, r.stdout.strip()), (0, "no regressions"), r.stderr)


if __name__ == "__main__":
    unittest.main()
