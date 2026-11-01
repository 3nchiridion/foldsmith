#!/usr/bin/env python3
"""appstore.py: the App Store's iPhone Duo set from shots already taken. Only cells verified or unchanged, with a clean
detector table, no open issue in the pose and Apple's size, flattened to JPEGs with no alpha, listed in a README that
says to check every image; never resized, never uploaded. Skipped where macOS's sips is not installed.

    python3 -m unittest discover -s scripts -p 'test_*.py'
"""
import json
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

HERE = pathlib.Path(__file__).resolve().parent
APPSTORE = HERE / "appstore.py"
POSES = ["closed", "closed-sideways", "book", "laptop", "tent", "flat-sideways", "flat-upright"]
SIZE = {"closed": (1398, 2034), "closed-sideways": (2034, 1398), "book": (2853, 2007), "flat-sideways": (2853, 2007),
        "laptop": (2007, 2853), "tent": (2007, 2853), "flat-upright": (2007, 2853)}
HEAD = "| config | closed | closed-sideways | book | laptop | tent | flat-sideways | flat-upright |\n|---|---|---|---|---|---|---|---|\n"
CLEAN = ["·"] * 7


MADE = {}   # (size, rgba) → the PNG's bytes, made once


def png(path, size, rgba=(30, 60, 90, 255)):
    """A one-colour PNG with an alpha channel, as the captures are (colour type 6), at the size given."""
    if (size, rgba) not in MADE:
        w, h = size
        raw = (b"\x00" + bytes(rgba) * w) * h

        def chunk(kind, data):
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

        MADE[size, rgba] = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(MADE[size, rgba])


def props(path):
    r = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", "-g", "hasAlpha", "-g", "format", str(path)],
                       capture_output=True, text=True, check=True)
    return dict(line.strip().split(": ", 1) for line in r.stdout.splitlines()[1:])


def first_pixel(path, scratch):
    """The top-left pixel of an image as (r, g, b), read from a BMP copy sips makes."""
    bmp = scratch / (path.stem + ".bmp")
    subprocess.run(["sips", "-s", "format", "bmp", str(path), "--out", str(bmp)], capture_output=True, check=True)
    d = bmp.read_bytes()
    offset, height, bpp = struct.unpack_from("<I", d, 10)[0], struct.unpack_from("<i", d, 22)[0], struct.unpack_from("<H", d, 28)[0]
    width = struct.unpack_from("<i", d, 18)[0]
    stride = (width * bpp // 8 + 3) & ~3
    row = offset if height < 0 else offset + stride * (height - 1)   # bottom-up unless the height is negative
    b, g, r = d[row:row + 3]
    return r, g, b


@unittest.skipUnless(shutil.which("sips"), "sips (macOS) is not installed")
class AppStore(unittest.TestCase):
    """A repository with a progress file, an after and a before capture, each with its detectors.md."""

    def setUp(self):
        self.repo = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo)
        self.m = {"app": "App", "phase": "done", "poses": POSES, "screens": [], "done": [], "todo": [], "log": []}
        self.tables = {"before": {}, "after": {}}

    def add(self, name, states, kinds=("before", "after"), sizes=None, rgba=(30, 60, 90, 255), table=None):
        """A screen with a cell per pose (states: pose → state, the rest unchanged), a shot of each kind at Apple's
        size (sizes: pose → another size) and a row in each kind's detector table (table: kind → [words per pose])."""
        cells = {}
        for pose in POSES:
            cell = {"state": states.get(pose, "unchanged")}
            for kind in kinds:
                panel = "cover" if pose.startswith("closed") else "inner"
                rel = f".duo/captures/App/{kind}/{name}-{pose}-{panel}.png"
                png(self.repo / rel, (sizes or {}).get(pose, SIZE[pose]), rgba)
                cell[kind] = rel
            cells[pose] = cell
        self.m["screens"].append({"name": name, "cells": cells})
        for kind in kinds:
            self.tables[kind][name] = (table or {}).get(kind, CLEAN)
        return cells

    def write(self):
        (self.repo / ".duo").mkdir(exist_ok=True)
        (self.repo / ".duo" / "migration.json").write_text(json.dumps(self.m, indent=2))
        for kind, rows in self.tables.items():
            if rows:
                (self.repo / ".duo/captures/App" / kind).mkdir(parents=True, exist_ok=True)
                (self.repo / ".duo/captures/App" / kind / "detectors.md").write_text(
                    HEAD + "".join(f"| {kind}/{n} | {' | '.join(w)} |\n" for n, w in rows.items()))

    def run_it(self, *args, write=True):
        if write:
            self.write()
        return subprocess.run([sys.executable, str(APPSTORE), *args], cwd=self.repo, capture_output=True, text=True)

    def out(self, *parts):
        return self.repo.joinpath(".duo", "appstore", *parts)

    def files(self):
        return sorted(p.relative_to(self.out()).as_posix() for p in self.out().rglob("*.jpg"))

    def test_one_shot_per_size_flattened_at_apples_sizes_with_a_readme(self):
        self.add("inbox", {"book": "verified", "flat-upright": "verified"})
        self.add("message", {})
        r = self.run_it()
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(self.files(), [
            "inner-landscape/01-inbox-book.jpg", "inner-landscape/02-message-book.jpg",
            "inner-portrait/01-inbox-flat-upright.jpg", "inner-portrait/02-message-flat-upright.jpg",
            "outer-landscape/01-inbox-closed-sideways.jpg", "outer-landscape/02-message-closed-sideways.jpg",
            "outer-portrait/01-inbox-closed.jpg", "outer-portrait/02-message-closed.jpg"])
        want = {"outer-portrait": (1398, 2034), "outer-landscape": (2034, 1398), "inner-portrait": (2007, 2853),
                "inner-landscape": (2853, 2007)}
        for rel in self.files():
            p = props(self.out(rel))
            self.assertEqual((p["format"], p["hasAlpha"]), ("jpeg", "no"), rel)
            self.assertEqual((int(p["pixelWidth"]), int(p["pixelHeight"])), want[rel.split("/")[0]], rel)
        readme = self.out("README.md").read_text()
        for rel in self.files():
            self.assertIn(f"`{rel}`", readme)
        self.assertIn("personal content", readme)
        self.assertIn("status bar", readme)
        self.assertIn("Nothing was uploaded", readme)

    def test_transparency_is_flattened_onto_white(self):
        self.add("inbox", {}, rgba=(200, 30, 30, 0))
        self.assertEqual(self.run_it().returncode, 0)
        jpg = self.out("outer-portrait", "01-inbox-closed.jpg")
        self.assertEqual(props(jpg)["hasAlpha"], "no")
        self.assertTrue(all(v >= 250 for v in first_pixel(jpg, self.repo)), first_pixel(jpg, self.repo))

    def test_only_verified_or_unchanged_cells_and_the_next_pose_stands_in(self):
        self.add("inbox", {"closed": "finding", "closed-sideways": "migrated", "book": "proposed",
                           "flat-sideways": "verified", "flat-upright": "pending", "laptop": "verified"})
        r = self.run_it()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.files(), ["inner-landscape/01-inbox-flat-sideways.jpg",
                                        "inner-portrait/01-inbox-laptop.jpg"])
        self.assertIn("closed: state finding", r.stdout)
        readme = self.out("README.md").read_text()
        self.assertIn("## Not exported", readme)
        self.assertIn("closed-sideways: state migrated", readme)

    def test_a_detector_finding_refuses_the_cell_waived_or_not(self):
        cells = self.add("inbox", {"book": "verified"},
                         table={"after": ["T7", "·", "T14", "·", "·", "no-rotate", "·"]})
        cells["book"]["waived"] = {"T14": "a hidden column"}
        r = self.run_it()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("outer-portrait/01-inbox-closed.jpg", self.files())
        self.assertFalse(any(f.startswith("inner-landscape/") for f in self.files()))
        self.assertIn("detector table: T7", r.stdout)
        self.assertIn("T14 (waived: a hidden column)", r.stdout)
        self.assertIn("flat-sideways: detector table: no-rotate", r.stdout)

    def test_no_detector_table_refuses_every_cell(self):
        self.add("inbox", {})
        self.write()
        (self.repo / ".duo/captures/App/after/detectors.md").unlink()
        r = self.run_it(write=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("no detector table", r.stdout)
        self.assertEqual(self.files(), [])

    def test_an_open_issue_in_the_pose_refuses_it(self):
        self.add("inbox", {"book": "verified"})
        self.m["issues"] = [
            {"id": "I1", "screen": "inbox", "poses": ["book"], "severity": "medium", "what": "Reply in the list pane",
             "status": "open"},
            {"id": "I2", "screen": "inbox", "poses": ["closed"], "severity": "low", "what": "fixed", "status": "fixed"},
            {"id": "I3", "screen": "inbox", "poses": [], "severity": "low", "what": "state restoration",
             "status": "open"}]
        r = self.run_it()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("inner-landscape/01-inbox-flat-sideways.jpg", self.files())
        self.assertIn("outer-portrait/01-inbox-closed.jpg", self.files())
        self.assertIn("book: open issue I1 (Reply in the list pane)", r.stdout)
        self.assertIn("I3 inbox: state restoration", self.out("README.md").read_text())

    def test_a_shot_of_another_size_is_refused_never_resized(self):
        self.add("inbox", {}, sizes={"closed": (1206, 2622), "book": (2007, 2853), "flat-sideways": (2007, 2853)})
        r = self.run_it()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("outer-portrait/01-inbox-closed.jpg", self.files())
        self.assertFalse(any(f.startswith("inner-landscape/") for f in self.files()))
        self.assertIn("1206 x 2622, not the 1398 x 2034", r.stdout)
        self.assertIn("not resized", r.stdout)

    def test_before_takes_the_before_shots_of_unchanged_cells_only(self):
        self.add("inbox", {"book": "verified", "closed": "finding"})
        r = self.run_it("--kind", "before")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.files(), ["inner-landscape/01-inbox-flat-sideways.jpg",
                                        "inner-portrait/01-inbox-flat-upright.jpg",
                                        "outer-landscape/01-inbox-closed-sideways.jpg"])
        self.assertIn("book: state verified (its before shot is the layout that was fixed)", r.stdout)
        self.assertIn("from the before capture", self.out("README.md").read_text())

    def test_after_with_no_after_shots_points_to_before(self):
        self.add("inbox", {}, kinds=("before",))
        r = self.run_it()
        self.assertEqual(r.returncode, 1)
        self.assertIn("--kind before", r.stderr)
        self.assertFalse(self.out().exists())

    def test_nothing_usable_exits_1(self):
        self.add("inbox", {p: "finding" for p in POSES})
        r = self.run_it()
        self.assertEqual(r.returncode, 1)
        self.assertIn("nothing could be exported", r.stderr)
        self.assertEqual(self.files(), [])

    def test_a_rerun_replaces_its_own_files_and_keeps_the_rest(self):
        self.add("inbox", {})
        self.assertEqual(self.run_it().returncode, 0)
        mine = self.out("outer-portrait", "notes.txt")
        mine.write_text("kept")
        stale = self.out("outer-portrait", "07-old-closed.jpg")
        stale.write_bytes(b"old")
        self.m["screens"][0]["cells"]["closed"]["state"] = "finding"
        self.assertEqual(self.run_it().returncode, 0)
        self.assertFalse(stale.exists())
        self.assertFalse(self.out("outer-portrait", "01-inbox-closed.jpg").exists())
        self.assertEqual(mine.read_text(), "kept")

    def test_the_output_goes_into_git_info_exclude(self):
        if not shutil.which("git"):
            self.skipTest("git is not installed")
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.add("inbox", {})
        self.assertEqual(self.run_it().returncode, 0)
        self.assertEqual(self.run_it().returncode, 0)
        lines = (self.repo / ".git/info/exclude").read_text().splitlines()
        self.assertEqual(lines.count("/.duo/appstore/"), 1)
        status = subprocess.run(["git", "-C", str(self.repo), "status", "--porcelain", "--untracked-files=all"],
                                capture_output=True, text=True, check=True).stdout
        self.assertNotIn("appstore", status)

    def test_an_out_that_holds_the_app_or_the_progress_file_is_refused(self):
        self.add("inbox", {})
        self.write()
        (self.repo / "README.md").write_text("# The app\n")
        for out in (".", ".duo", "..", str(self.repo)):
            r = self.run_it("--out", out, write=False)
            self.assertEqual(r.returncode, 2, (out, r.stdout, r.stderr))
            self.assertIn("give the screenshots a folder of their own", r.stderr)
        self.assertEqual((self.repo / "README.md").read_text(), "# The app\n")
        self.assertFalse((self.repo / "outer-portrait").exists())

    def test_a_readme_it_did_not_write_stops_it_before_anything_changes(self):
        self.add("inbox", {})
        docs = self.repo / "docs/screenshots"
        docs.mkdir(parents=True)
        (docs / "README.md").write_text("# Our screenshots\n")
        (docs / "outer-portrait").mkdir()
        (docs / "outer-portrait/01-hero.jpg").write_bytes(b"theirs")
        r = self.run_it("--out", "docs/screenshots")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("is not one this script wrote", r.stderr)
        self.assertEqual((docs / "README.md").read_text(), "# Our screenshots\n")
        self.assertEqual((docs / "outer-portrait/01-hero.jpg").read_bytes(), b"theirs")
        # Its own README is replaced on a rerun, and so are its numbered files, however many digits.
        self.assertEqual(self.run_it().returncode, 0)
        stale = self.out("outer-portrait", "100-old-closed.jpg")
        stale.write_bytes(b"old")
        self.assertEqual(self.run_it().returncode, 0)
        self.assertFalse(stale.exists())

    def test_an_app_in_a_subfolder_of_a_repository_is_excluded_from_its_top(self):
        if not shutil.which("git"):
            self.skipTest("git is not installed")
        top = self.repo
        subprocess.run(["git", "init", "-q", str(top)], check=True)
        self.repo = top / "ios app [beta]"
        self.repo.mkdir()
        self.add("inbox", {})
        r = self.run_it()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(r"/ios app \[beta\]/.duo/appstore/", (top / ".git/info/exclude").read_text().splitlines())
        status = subprocess.run(["git", "-C", str(top), "status", "--porcelain", "--untracked-files=all"],
                                capture_output=True, text=True, check=True).stdout
        self.assertNotIn("appstore", status)

    def test_a_shot_outside_the_repository_is_refused_unread(self):
        cells = self.add("inbox", {})
        elsewhere = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, elsewhere)
        png(elsewhere / "secret.png", SIZE["closed"])
        cells["closed"]["after"] = str(elsewhere / "secret.png")
        cells["closed-sideways"]["after"] = "../" + elsewhere.name + "/secret.png"
        r = self.run_it()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("outer-portrait/01-inbox-closed.jpg", self.files())
        self.assertIn("closed: " + str(elsewhere / "secret.png") + " is outside the repository", r.stdout)
        self.assertIn("is outside the repository (the progress file comes with it): not read", r.stdout)

    def test_a_screen_with_no_cells_is_passed_over(self):
        self.add("inbox", {})
        self.m["screens"].append({"name": "later"})
        r = self.run_it()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("later: no shot for the outer display, portrait (closed: not captured)", r.stdout)

    def test_it_uploads_nothing(self):
        source = APPSTORE.read_text()
        for word in ("urllib", "http.client", "socket", "requests", "altool", "iTMSTransporter", "upload-app"):
            self.assertNotIn(word, source)


if __name__ == "__main__":
    unittest.main()
