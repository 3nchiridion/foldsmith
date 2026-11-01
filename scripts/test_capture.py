#!/usr/bin/env python3
"""capture-app.sh and capture-corpus-flow.sh against stand-ins for duo.py, xcrun, xcodebuild (the tap runner), swift
(the detectors), df and sleep, so no simulator is needed: each bug a run hit stays fixed (exit 3 on a skipped screen, a
failed shot or a missing snapshot, a SCREEN= recapture that appends, the "lost the screen" line naming the pose whose
round trip lost it, a crash reported rather than counted clean), and so do the lock, the disk guard, the stop on a
signal, the stop when capture-app.sh is killed outright, a wrong call that touches nothing, and RESUME=1. The code
identity (progress.py codeid) on each line of .captured, in small git repositories: RESUME=1 keeps a cell only from the
same code, a SCREEN= recapture replaces only that screen's lines, a capture stopped early leaves the cells it did not
reach readable as from their code, and progress.py check reads what a capture wrote. LAUNCH_ARGS as the tap runner gets
it.

The runner stand-in answers the capture's flag files with canned snapshots (a screen's bars and buttons, the pose's
window), appends TEST_RUNNER_DUO_ARGS to the args file (NUL after each), and follows runner.json: "fail" (taps that
reach nothing), "lose" (taps → the pose whose round trip loses the screen), "crash" (taps → the pose where the app is
gone), "silent" (taps → the pose whose snapshot never comes), "hold" ("<taps>:taps": wait there while the hold file is
there), "deaf" (never let go on release, only on TERM), "fill_disk_after" (taps after whose release the disk is full).
Sleeps run at a fiftieth of their length.

    python3 -m unittest discover -s scripts -p 'test_*.py'
"""
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import tempfile
import time
import unittest

HERE = pathlib.Path(__file__).resolve().parent
CAPTURE_APP = HERE / "capture-app.sh"
CAPTURE_FLOW = HERE / "capture-corpus-flow.sh"
PROGRESS = HERE / "progress.py"
TAP_RUNNER = HERE.parent / "Tap" / "DuoTapUITests" / "DuoTapTests.swift"
PLENTY_KB = 100 * 1024 * 1024
FULL_KB = 2 * 1024 * 1024

DUO_PY = """\
import os, pathlib, struct, sys, zlib
shim = pathlib.Path(os.environ["SHIM"])
args = sys.argv[1:]
if args[:1] == ["--udid"]:
    args = args[2:]
with open(shim / "duo.log", "a") as log:
    log.write(" ".join(args) + "\\n")
if " ".join(args) in (shim / "duo-fails").read_text().splitlines() if (shim / "duo-fails").exists() else []:
    sys.exit("duo.py stand-in: told to fail")
pose = (shim / "pose").read_text().split() if (shim / "pose").exists() else ["close", "sideways"]
if args[0] == "fold":
    pose[0] = args[1]
elif args[0] == "orient":
    pose[1] = args[1]
elif args[0] == "shot":
    out, name = args[args.index("--out") + 1], args[args.index("--name") + 1]
    w, h = (6, 4) if tuple(pose) in {("close", "upright"), ("book", "sideways"), ("open", "sideways")} else (4, 6)
    raw = b"".join(b"\\0" + b"\\x80\\x80\\x80\\xff" * w for _ in range(h))
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    png = (b"\\x89PNG\\r\\n\\x1a\\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    path = pathlib.Path(out) / f"{name}-{'cover' if pose[0] == 'close' else 'inner'}.png"
    path.write_bytes(png)
    print(path)
(shim / "pose").write_text(" ".join(pose))
"""

RUNNER = """\
import json, os, pathlib, signal, sys, time
shim = pathlib.Path(os.environ["SHIM"])
flags = pathlib.Path(os.environ["TEST_RUNNER_DUO_FLAGS"])
taps = os.environ["TEST_RUNNER_DUO_TAPS"]
bundle = os.environ["TEST_RUNNER_DUO_BUNDLE"]
cfg = json.loads((shim / "runner.json").read_text()) if (shim / "runner.json").exists() else {}
deaf = taps in cfg.get("deaf", [])

def log(line):
    with open(shim / "runner.log", "a") as f:
        f.write(f"{os.getpid()} {taps} {line}\\n")

def on_term(*_):
    log("terminated")
    sys.exit(143)

signal.signal(signal.SIGTERM, on_term)
log("start " + ("locked" if pathlib.Path(".duo/.capture.lock").is_file() else "unlocked"))
with open(shim / "args", "ab") as f:
    f.write(os.environb.get(b"TEST_RUNNER_DUO_ARGS", b"(not set)") + b"\\0")
POSES = {("close", "sideways"): "closed", ("close", "upright"): "closed-sideways", ("book", "sideways"): "book",
         ("laptop", "upright"): "laptop", ("laptop", "landscape-right"): "tent", ("open", "sideways"): "flat-sideways",
         ("open", "upright"): "flat-upright"}
WINDOWS = {"closed": [420, 912], "closed-sideways": [912, 420], "book": [1000, 700], "laptop": [700, 1000],
           "tent": [700, 1000], "flat-sideways": [1000, 700], "flat-upright": [700, 1000]}

def tree(name, window):
    node = lambda parent, kind, frame, label: {"parent": parent, "type": kind, "frame": frame, "identifier": None,
                                               "label": label, "enabled": True, "selected": False}
    return {"bundle": bundle, "window": window, "nodes": [
        node(-1, "navigationBar", [0, 0, window[0], 50], name), node(0, "button", [10, 10, 40, 30], "Edit"),
        node(-1, "button", [10, 60, 40, 30], "New " + name)]}

def write(name, text=""):
    (flags / (name + ".tmp")).write_text(text)
    (flags / (name + ".tmp")).rename(flags / name)

def released():
    if (flags / "release").exists() and not deaf:
        log("released")
        if taps in cfg.get("fill_disk_after", []):
            (shim / "free_kb").write_text(str(2 * 1024 * 1024))
        sys.exit(0)

if cfg.get("hold") == taps + ":taps":
    (shim / "holding").write_text(str(os.getpid()))
    while (shim / "hold").exists():
        released()
        time.sleep(0.02)
if taps in cfg.get("fail", []):
    write("failed", f"no element matches {taps!r}")
    log("failed")
    sys.exit(65)
write("hierarchy.txt", "Application")
write("tapped")
lost = crashed = False
while True:
    released()
    if (flags / "again").exists():
        (flags / "again").unlink()
        lost = crashed = False
        log("again")
        write("tapped")
    if (flags / "posed").exists():
        (flags / "posed").unlink()
        pose = POSES[tuple((shim / "pose").read_text().split())]
        crashed = crashed or cfg.get("crash", {}).get(taps) == pose
        if cfg.get("silent", {}).get(taps) == pose:
            log("silent in " + pose)
            continue
        if crashed:
            snap = {"bundle": bundle, "window": [0, 0], "nodes": [], "appState": "notRunning"}
        else:
            snap = tree("Home" if lost and pose == "closed" else taps, WINDOWS[pose])
        lost = lost or cfg.get("lose", {}).get(taps) == pose
        write("snapshot.json", json.dumps(snap))
        write("snapped")
    time.sleep(0.01)
"""

SWIFT = """\
import pathlib, sys
args = sys.argv[1:]
out = pathlib.Path(args[args.index("duo-detect") + 1])
pathlib.Path(args[args.index("--markdown") + 1]).write_text("| config | closed |\\n|---|---|\\n")
print("[1/1] Compiling duo-detect")
print(f"{len(list(out.glob('*.json')))} captures, 0 findings")
"""

XCRUN = """\
#!/bin/bash
echo "$*" >> "$SHIM/xcrun.log"
case "$*" in "simctl list devices"*) echo "    iPhone Duo (TEST-UDID) (Booted)";; esac
exit 0
"""

DF = """\
#!/bin/bash
# every path on one disk, with $SHIM/free_kb kilobytes free
free="$(cat "$SHIM/free_kb")"
echo "Filesystem 1024-blocks Used Available Capacity Mounted on"
for a in "$@"; do case "$a" in -*) ;; *) echo "/dev/disk3s5 500000000 400000000 $free 80% /System/Volumes/Data";; esac; done
"""

SLEEP = """\
#!/bin/bash
exec /bin/sleep "$(/usr/bin/awk -v s="$1" 'BEGIN { printf "%.3f", s / 50 }')"
"""

FLOW = """\
BUNDLE=dev.example.Notes
SCREENS=(
  "folders=Folders"
  "settings=Settings"
)
"""


class Capture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        self.app, self.bin, self.shim, self.home = root / "app", root / "bin", root / "shim", root / "home"
        for d in (self.app / ".duo" / "flows", self.bin, self.shim, self.home / "Library" / "Caches" / "duo-detect",
                  self.home / "Library" / "Caches" / "duo-tap"):
            d.mkdir(parents=True)
        (self.home / "Library" / "Caches" / "duo-detect" / "build.bin").write_bytes(b"\1" * (2 << 20))
        (self.home / "Library" / "Caches" / "duo-tap" / "build.bin").write_bytes(b"\1" * (1 << 20))
        self.flow = self.app / ".duo" / "flows" / "Notes.flow"
        self.flow.write_text(FLOW)
        self.out = self.app / ".duo" / "captures" / "Notes" / "probe"
        self.lock = self.app / ".duo" / ".capture.lock"
        shims = {"xcrun": XCRUN, "df": DF, "sleep": SLEEP, "python3": f'#!/bin/bash\nexec "{sys.executable}" "$@"\n',
                 "xcodebuild": f"#!{sys.executable}\n{RUNNER}", "swift": f"#!{sys.executable}\n{SWIFT}"}
        for name, text in shims.items():
            (self.bin / name).write_text(text)
            (self.bin / name).chmod(0o755)
        (self.bin / "duo.py").write_text(DUO_PY)
        (root / "x.xctestrun").write_text("")
        (self.shim / "free_kb").write_text(str(PLENTY_KB))
        self.env = {
            "PATH": f"{self.bin}:/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(self.home), "SHIM": str(self.shim),
            "DUO_UDID": "TEST-UDID", "DUO_PY": str(self.bin / "duo.py"), "DUO_TAP_XCTESTRUN": str(root / "x.xctestrun"),
            "XCODE_OUT": str(root / "xcode"), "TMPDIR": str(root), "WAIT": "1", "TAP_WAIT": "1",
            # git finds no repository above the temporary folder, and commits need no configuration
            "GIT_CEILING_DIRECTORIES": os.path.realpath(root), "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
        }

    def tearDown(self):
        self.tmp.cleanup()

    def runner(self, **cfg):
        (self.shim / "runner.json").write_text(json.dumps(cfg))

    def capture(self, out=None, **env):
        return subprocess.run(["bash", str(CAPTURE_APP), str(self.flow), str(out or self.out)], cwd=self.app,
                              env={**self.env, **env}, capture_output=True, text=True, timeout=120)

    def text(self, name, out=None):
        return ((out or self.out) / name).read_text()

    def runner_log(self):
        return (self.shim / "runner.log").read_text().splitlines()

    def starts(self):
        return [line.split()[1] for line in self.runner_log() if " start " in line]

    def git(self, *args):
        done = subprocess.run(["git", "-C", str(self.app), *args], env=self.env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.strip()

    def commit(self, source="let version = 1\n"):
        """The app as a git repository, App.swift holding source, committed: the new HEAD (.duo/ stays untracked)."""
        if not (self.app / ".git").exists():
            self.git("init", "-q")
        (self.app / "App.swift").write_text(source)
        self.git("add", "App.swift")
        self.git("commit", "-q", "-m", "Change the app")
        return self.git("rev-parse", "HEAD")

    def progress(self, *args):
        return subprocess.run([sys.executable, str(PROGRESS), "--file", str(self.app / ".duo" / "migration.json"),
                               *args], cwd=self.app, env=self.env, capture_output=True, text=True, timeout=60)

    def sha(self):
        return subprocess.run(["shasum", "-a", "256", str(self.flow)], capture_output=True, text=True).stdout.split()[0]

    def test_a_clean_capture_records_every_cell_and_keeps_the_lock_only_while_it_runs(self):
        progress = self.app / ".duo" / "migration.json"
        progress.write_text(json.dumps({"app": "Notes", "phase": "audit", "screens": []}))
        before = self.app / ".duo" / "captures" / "Notes" / "before"
        done = self.capture(out=before, ONLY="closed book")
        self.assertEqual(done.returncode, 0, done.stderr)
        for cell in ("folders-closed-cover.png", "folders-book-inner.png", "settings-closed.json", "settings-book.json"):
            self.assertTrue((before / cell).exists(), cell)
        sha = self.sha()
        # Outside git the code identity is none.
        self.assertEqual(sorted(self.text(".captured", before).splitlines()),
                         sorted(f"{sha} {s} {p} none" for s in ("folders", "settings") for p in ("closed", "book")))
        self.assertIn(f"flow: {self.flow} sha256 {sha}\ncode: none\n", self.text("capture.txt", before))
        self.assertEqual(self.text("findings.txt", before).strip(), "4 captures, 0 findings")
        # The runner only ever ran under the lock, and the lock went with the capture.
        self.assertTrue(all(line.endswith("start locked") for line in self.runner_log() if " start " in line))
        self.assertFalse(self.lock.exists())
        cells = json.loads(progress.read_text())["screens"][0]["cells"]
        self.assertEqual(cells["book"]["before"], ".duo/captures/Notes/before/folders-book-inner.png")

    def test_a_screen_skipped_in_every_pose_exits_3(self):
        self.runner(fail=["Settings"])
        done = self.capture(ONLY="closed book")
        self.assertEqual(done.returncode, 3, done.stderr)
        self.assertIn("settings: skipped in every pose: no element matches 'Settings'", done.stderr)
        self.assertIn("settings: skipped in every pose", self.text("findings.txt"))
        self.assertIn("not captured in this run (no line in", done.stderr)
        self.assertIn(".captured): settings closed, settings book\n", self.text("findings.txt"))
        self.assertIn("those cells are not clean, they are missing", done.stderr)
        self.assertFalse(self.lock.exists())

    def test_the_lost_screen_line_names_the_pose_whose_round_trip_lost_it(self):
        self.runner(lose={"Settings": "book"})
        done = self.capture(ONLY="closed book laptop tent")
        self.assertEqual(done.returncode, 0, done.stderr)
        lost = [line for line in self.text("capture.txt").splitlines() if "lost the screen" in line]
        self.assertEqual(len(lost), 1, lost)
        self.assertRegex(lost[0], r"^  settings: the shut phone lost the screen after book \(similarity 0\.\d+\): relaunched before laptop$")
        self.assertIn("Settings again", " ".join(self.runner_log()))

    def test_a_screen_recapture_appends_to_capture_txt(self):
        self.runner(lose={"Settings": "book"})
        self.assertEqual(self.capture(ONLY="closed book laptop").returncode, 0)
        first = self.text("capture.txt")
        self.runner()
        again = self.capture(SCREEN="settings", ONLY="closed book laptop")
        self.assertEqual(again.returncode, 0, again.stderr)
        after = self.text("capture.txt")
        self.assertTrue(after.startswith(first), "the first pass's lines are kept, in order")
        added = after[len(first):].splitlines()
        self.assertRegex(added[0], r"^recaptured: settings, \S+, flow sha256 [0-9a-f]{64}$")
        self.assertIn("== settings", added)
        self.assertNotIn("== folders", added)

    def test_a_crash_is_reported_not_counted_clean(self):
        self.runner(crash={"Settings": "tent"})
        done = self.capture(ONLY="closed tent flat-sideways")
        self.assertEqual(done.returncode, 0, done.stderr)
        log = self.text("capture.txt")
        self.assertIn("  settings: the app was not in front in tent (notRunning): it crashed or quit on the way there, T7 in that cell", log)
        # Back on the shut phone the app is gone, so the screen is lost after tent and tapped to again.
        self.assertIn("settings: the shut phone lost the screen after tent (similarity 0.00): relaunched before flat-sideways", log)
        line = "settings tent: the app was not in front (notRunning): it crashed or quit on the way, T7 in that cell, not a clean one"
        self.assertIn(line, self.text("findings.txt"))
        self.assertIn(line, done.stderr)
        self.assertNotIn("folders", self.text("findings.txt").split("findings", 1)[1])

    def test_an_interrupt_stops_the_runner_leaves_no_lock_and_resume_takes_the_rest(self):
        (self.shim / "hold").write_text("")
        self.runner(hold="Settings:taps", deaf=["Settings"])
        env = {**self.env, "ONLY": "closed book", "TAP_TIMEOUT": "6000"}
        first = subprocess.Popen(["bash", str(CAPTURE_APP), str(self.flow), str(self.out)], cwd=self.app, env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            for _ in range(600):
                if (self.shim / "holding").exists():
                    break
                time.sleep(0.05)
            self.assertTrue((self.shim / "holding").exists(), "the capture reached the held screen")
            held = self.lock.read_text()
            sha = subprocess.run(["shasum", "-a", "256", str(self.flow)], capture_output=True, text=True).stdout.split()[0]
            self.assertIn(f"pid {first.pid}\n", held)
            self.assertIn(f"flow sha256 {sha}\n", held)
            self.assertRegex(held, r"started \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ\n")

            # A second capture while the first runs refuses and touches nothing.
            log = self.text("capture.txt")
            second = self.capture(ONLY="closed book")
            self.assertEqual(second.returncode, 5, second.stderr)
            self.assertIn(f"another capture is running: pid {first.pid}", second.stderr)
            self.assertEqual(self.text("capture.txt"), log)
            self.assertEqual(self.lock.read_text(), held)

            first.send_signal(signal.SIGINT)
            first.communicate(timeout=60)
        finally:
            if first.poll() is None:
                first.kill()
        self.assertEqual(first.returncode, 130)
        self.assertFalse(self.lock.exists())
        last = self.text("capture.txt").splitlines()[-1]
        # The capture's line names the signal the person sent (capture-app.sh passes INT on as USR1).
        self.assertRegex(last, r"^stopped: interrupted \(SIGINT\) at settings, on its way in \(launch and taps\), \S+\. "
                               r"The cells captured before it are kept: the same command with RESUME=1 carries on")
        # The runner would not let go, so it was terminated; nothing of it is left running.
        held_runner = int((self.shim / "holding").read_text())
        self.assertIn(f"{held_runner} Settings terminated", self.runner_log())
        with self.assertRaises(ProcessLookupError):
            os.kill(held_runner, 0)

        (self.shim / "hold").unlink()
        done = self.capture(ONLY="closed book", RESUME="1")
        self.assertEqual(done.returncode, 0, done.stderr)
        starts = [line.split()[1] for line in self.runner_log() if " start " in line]
        self.assertEqual(starts, ["Folders", "Settings", "Settings"], "folders is not captured again")
        log = self.text("capture.txt")
        self.assertRegex(log, r"\nresumed: every screen, \S+, flow sha256 [0-9a-f]{64}\n")
        self.assertIn("== folders\n  every pose asked for was captured before (RESUME=1)\n", log)
        self.assertTrue((self.out / "settings-book-inner.png").exists())

    def test_a_failure_mid_screen_says_where_and_resume_keeps_the_cells_before_it(self):
        (self.shim / "duo-fails").write_text("fold laptop\n")
        done = self.capture(ONLY="closed book laptop")
        self.assertEqual(done.returncode, 1, done.stderr)
        self.assertFalse(self.lock.exists())
        self.assertRegex(self.text("capture.txt").splitlines()[-1], r"^stopped: exit 1 at folders in laptop, ")

        (self.shim / "duo-fails").unlink()
        (self.shim / "duo.log").unlink()
        done = self.capture(ONLY="closed book laptop", RESUME="1")
        self.assertEqual(done.returncode, 0, done.stderr)
        shots = [line.split()[-1] for line in (self.shim / "duo.log").read_text().splitlines() if line.startswith("shot")]
        self.assertEqual(shots, ["folders-laptop", "settings-closed", "settings-book", "settings-laptop"])
        log = self.text("capture.txt")
        self.assertIn("  closed: kept from the earlier capture (RESUME=1)\n  book: kept from the earlier capture (RESUME=1)\n", log)

    def test_resume_with_a_changed_flow_captures_every_cell(self):
        self.assertEqual(self.capture(ONLY="closed").returncode, 0)
        self.flow.write_text(FLOW + 'LAUNCH_ARGS="-Demo YES"\n')
        done = self.capture(ONLY="closed", RESUME="1")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("holds no capture of this flow", done.stderr)
        self.assertEqual([line.split()[1] for line in self.runner_log() if " start " in line],
                         ["Folders", "Settings", "Folders", "Settings"])

    def test_each_line_carries_the_code_and_resume_keeps_a_cell_only_from_the_same_code(self):
        head = self.commit()
        sha = self.sha()
        self.assertEqual(self.capture(ONLY="closed book").returncode, 0)
        self.assertEqual(sorted(self.text(".captured").splitlines()),
                         sorted(f"{sha} {s} {p} {head}" for s in ("folders", "settings") for p in ("closed", "book")))
        self.assertIn(f"flow: {self.flow} sha256 {sha}\ncode: {head}\ncaptured: ", self.text("capture.txt"))

        # The same code: every cell is kept, nothing is said about the code.
        done = self.capture(ONLY="closed book", RESUME="1")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.starts(), ["Folders", "Settings"])
        self.assertEqual(self.text("capture.txt").count("every pose asked for was captured before (RESUME=1)"), 2)
        self.assertNotIn("code changed", self.text("capture.txt"))
        self.assertRegex(self.text("capture.txt"), rf"\nresumed: every screen, \S+, flow sha256 {sha}\ncode: {head}\n")

        # An edit not committed is other code too: every cell is taken again, and said so once.
        (self.app / "App.swift").write_text("let version = 2\n")
        code = self.progress("codeid").stdout.strip()
        self.assertRegex(code, rf"^{head}\+[0-9a-f]{{16}}$")
        done = self.capture(ONLY="closed book", RESUME="1")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.starts(), ["Folders", "Settings", "Folders", "Settings"])
        said = "code changed since the earlier capture: taking every cell again\n"
        self.assertEqual(self.text("capture.txt").count(said), 1)
        self.assertNotIn("kept from the earlier capture", self.text("capture.txt"))
        self.assertEqual(sorted(self.text(".captured").splitlines()),
                         sorted(f"{sha} {s} {p} {code}" for s in ("folders", "settings") for p in ("closed", "book")),
                         "the lines from the other code went with their shots")

    def test_resume_never_keeps_a_line_with_no_code(self):
        self.commit()
        sha = self.sha()
        self.assertEqual(self.capture(ONLY="closed").returncode, 0)
        record = self.out / ".captured"
        record.write_text("".join(f"{sha} {s} closed\n" for s in ("folders", "settings")))   # as 0.8.0 wrote it
        done = self.capture(ONLY="closed", RESUME="1")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.starts(), ["Folders", "Settings", "Folders", "Settings"])
        self.assertIn("the earlier capture recorded no code (it was taken before 0.8.1): taking every cell again\n",
                      self.text("capture.txt"))
        self.assertFalse([line for line in record.read_text().splitlines() if len(line.split()) != 4])

    def test_a_resume_after_a_commit_takes_the_cells_again_and_check_reads_the_code(self):
        progress = self.app / ".duo" / "migration.json"
        progress.write_text(json.dumps({"app": "Notes", "phase": "verify", "screens": []}))
        after = self.app / ".duo" / "captures" / "Notes" / "after"
        head = self.commit()
        self.assertEqual(self.capture(out=after, ONLY="closed book").returncode, 0)
        for s in ("folders", "settings"):
            self.assertEqual(self.progress("cell", s, "closed,book", "verified").returncode, 0)
        check = self.progress("check", "folders", "settings")
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertNotIn("code identity", check.stderr)
        self.assertNotIn("after shot is from", check.stdout)

        self.commit("let version = 2\n")
        check = self.progress("check", "folders", "settings")
        self.assertEqual(check.returncode, 1, check.stdout + check.stderr)
        self.assertIn(f"settings book: its after shot is from {head[:7]} and 1 file changed since (App.swift): rebuild "
                      "and install from the committed tree (step 6), then capture it again (SCREEN=settings, same "
                      "after folder)\n", check.stdout)
        self.assertEqual(check.stdout.count("its after shot is from"), 4)

        # The shims stand in for the rebuild and install a run makes first: the code identity cannot see the app.
        done = self.capture(out=after, ONLY="closed book", RESUME="1")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.starts(), ["Folders", "Settings", "Folders", "Settings"])
        self.assertEqual(self.text("capture.txt", after).count("code changed since the earlier capture"), 1)
        check = self.progress("check", "folders", "settings")
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertNotIn("code identity", check.stderr)

    def test_a_screen_recapture_replaces_that_screens_lines_and_keeps_the_others(self):
        first = self.commit()
        sha = self.sha()
        self.assertEqual(self.capture(ONLY="closed book").returncode, 0)
        folders = [line for line in self.text(".captured").splitlines() if " folders " in line]
        then = self.commit("let version = 2\n")
        done = self.capture(SCREEN="settings", ONLY="closed book")
        self.assertEqual(done.returncode, 0, done.stderr)
        lines = self.text(".captured").splitlines()
        self.assertEqual([line for line in lines if " folders " in line], folders)
        self.assertEqual(folders, [f"{sha} folders closed {first}", f"{sha} folders book {first}"])
        self.assertEqual(sorted(line for line in lines if " settings " in line),
                         sorted(f"{sha} settings {p} {then}" for p in ("closed", "book")))
        # A resume of the whole flow keeps settings, taken from this code, and takes folders again.
        done = self.capture(ONLY="closed book", RESUME="1")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.starts(), ["Folders", "Settings", "Settings", "Folders"])
        self.assertIn("code changed since the earlier capture, for 2 cells: taking those again (2 kept)\n",
                      self.text("capture.txt"))
        self.assertEqual(sorted(self.text(".captured").splitlines()),
                         sorted(f"{sha} {s} {p} {then}" for s in ("folders", "settings") for p in ("closed", "book")))

    def test_a_capture_stopped_early_leaves_the_cells_it_did_not_reach_on_record_as_from_their_code(self):
        progress = self.app / ".duo" / "migration.json"
        progress.write_text(json.dumps({"app": "Notes", "phase": "verify", "screens": []}))
        after = self.app / ".duo" / "captures" / "Notes" / "after"
        first = self.commit()
        self.assertEqual(self.capture(out=after, ONLY="closed").returncode, 0)
        self.assertEqual(self.progress("cell", "settings", "closed", "verified").returncode, 0)
        self.commit("let version = 2\n")
        (self.shim / "hold").write_text("")
        self.runner(hold="Folders:taps")
        env = {**self.env, "ONLY": "closed", "TAP_TIMEOUT": "6000"}
        stopped = subprocess.Popen(["bash", str(CAPTURE_APP), str(self.flow), str(after)], cwd=self.app, env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            for _ in range(600):
                if (self.shim / "holding").exists():
                    break
                time.sleep(0.05)
            self.assertTrue((self.shim / "holding").exists(), "the capture reached the held screen")
            stopped.send_signal(signal.SIGINT)
            stopped.communicate(timeout=60)
        finally:
            if stopped.poll() is None:
                stopped.kill()
        self.assertEqual(stopped.returncode, 130)
        # folders' line went with its shot; settings, not reached, keeps the code its shot came from, and RESUME=1
        # would not keep it.
        self.assertEqual(self.text(".captured", after).splitlines(), [f"retaking settings closed {first}"])
        check = self.progress("check", "settings")
        self.assertEqual(check.returncode, 1, check.stdout + check.stderr)
        self.assertIn(f"settings closed: its after shot is from {first[:7]} and 1 file changed since", check.stdout)
        self.assertNotIn("code identity", check.stderr)

        (self.shim / "hold").unlink()
        done = self.capture(out=after, ONLY="closed", RESUME="1")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.starts(), ["Folders", "Settings", "Folders", "Folders", "Settings"])
        self.assertEqual(self.progress("check", "settings").returncode, 0)

    def test_a_one_screen_flow_stopped_mid_screen_after_a_commit_refuses_done(self):
        # The stop removes the screen's only lines and shots: .captured is left empty, and that proves nothing.
        self.flow.write_text(FLOW.replace('  "settings=Settings"\n', ""))
        progress = self.app / ".duo" / "migration.json"
        progress.write_text(json.dumps({"app": "Notes", "phase": "verify", "screens": []}))
        after = self.app / ".duo" / "captures" / "Notes" / "after"
        self.commit()
        self.assertEqual(self.capture(out=after, ONLY="closed book").returncode, 0)
        self.assertEqual(self.progress("cell", "folders", "closed,book", "verified").returncode, 0)
        self.assertEqual(self.progress("check", "folders").returncode, 0)
        self.commit("let version = 2\n")
        self.assertEqual(self.progress("check", "folders").returncode, 1)
        (self.shim / "hold").write_text("")
        self.runner(hold="Folders:taps")
        env = {**self.env, "ONLY": "closed book", "TAP_TIMEOUT": "6000"}
        stopped = subprocess.Popen(["bash", str(CAPTURE_APP), str(self.flow), str(after)], cwd=self.app, env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            for _ in range(600):
                if (self.shim / "holding").exists():
                    break
                time.sleep(0.05)
            self.assertTrue((self.shim / "holding").exists(), "the capture reached the held screen")
            stopped.send_signal(signal.SIGINT)
            stopped.communicate(timeout=60)
        finally:
            if stopped.poll() is None:
                stopped.kill()
        self.assertEqual(stopped.returncode, 130)
        self.assertEqual(self.text(".captured", after), "")
        self.assertFalse((after / "folders-closed-cover.png").exists())
        done = self.progress("done", "folders: Fold-aligned split")
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        for pose in ("closed", "book"):
            self.assertIn(f"folders {pose}: its after shot is not there (a capture stopped mid-screen?): capture it "
                          "again (SCREEN=folders, same after folder)", done.stderr)

    def launch_args(self, value):
        """What the runner's environment gets as TEST_RUNNER_DUO_ARGS from a flow file's LAUNCH_ARGS line, as bytes."""
        self.flow.write_text(f'BUNDLE=dev.example.Notes\nLAUNCH_ARGS="{value}"\nSCREENS=(\n  "folders=Folders"\n)\n')
        done = self.capture(ONLY="closed")
        self.assertEqual(done.returncode, 0, done.stderr)
        return (self.shim / "args").read_bytes().split(b"\0")[0]

    def runner_splits(self, value):
        """The app's launch arguments from DUO_ARGS as the tap runner makes them: split at each space and nowhere
        else, empty pieces dropped (Swift's split(separator:)); the test fails if the runner stops doing that."""
        self.assertRegex(TAP_RUNNER.read_text(),
                         r'let launchArgs = \(env\["DUO_ARGS"\] \?\? ""\)\.split\(separator: " "\)\.map\(String\.init\)')
        return [piece for piece in value.split(" ") if piece]

    def test_launch_args_reach_the_runner_byte_for_byte(self):
        got = self.launch_args("-ShowArticle <false/> -Count 2")
        self.assertEqual(got, b"-ShowArticle <false/> -Count 2")
        self.assertEqual(self.runner_splits(got.decode()), ["-ShowArticle", "<false/>", "-Count", "2"])

    def test_single_quotes_inside_launch_args_reach_the_runner_as_characters(self):
        got = self.launch_args("-ShowArticle '<false/>' -Count 2")
        self.assertEqual(got, b"-ShowArticle '<false/>' -Count 2")
        self.assertEqual(self.runner_splits(got.decode()), ["-ShowArticle", "'<false/>'", "-Count", "2"])

    def test_low_disk_before_the_capture_exits_4_and_deletes_nothing(self):
        (self.shim / "free_kb").write_text(str(FULL_KB))
        done = self.capture()
        self.assertEqual(done.returncode, 4, done.stderr)
        self.assertRegex(done.stderr, r"^stopped: only 2\.0 GB free on the disk \(a capture needs 3 GB\), before the capture, ")
        self.assertRegex(done.stderr, r"largest ~/Library/Caches/duo-\* folders: 2 MB ~/Library/Caches/duo-detect, "
                                      r"1 MB ~/Library/Caches/duo-tap\. Nothing was deleted")
        self.assertTrue((self.home / "Library" / "Caches" / "duo-detect" / "build.bin").exists())
        self.assertFalse((self.out / "capture.txt").exists())
        self.assertFalse((self.shim / "runner.log").exists())
        self.assertFalse(self.lock.exists())

    def test_low_disk_between_screens_stops_there_and_resume_carries_on(self):
        self.runner(fill_disk_after=["Folders"])
        done = self.capture(ONLY="closed book")
        self.assertEqual(done.returncode, 4, done.stderr)
        self.assertRegex(self.text("capture.txt").splitlines()[-1], r"^stopped: only 2\.0 GB free on the disk .*, before settings, ")
        self.assertFalse((self.out / "findings.txt").exists(), "no detectors' build on a full disk")
        self.assertFalse(self.lock.exists())

        (self.shim / "free_kb").write_text(str(PLENTY_KB))
        done = self.capture(ONLY="closed book", RESUME="1")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual([line.split()[1] for line in self.runner_log() if " start " in line], ["Folders", "Settings"])
        self.assertEqual(self.text("findings.txt").strip(), "4 captures, 0 findings")

    def test_a_failed_shot_is_missing_and_the_earlier_passs_shot_goes(self):
        progress = self.app / ".duo" / "migration.json"
        progress.write_text(json.dumps({"app": "Notes", "phase": "verify", "screens": []}))
        after = self.app / ".duo" / "captures" / "Notes" / "after"
        self.assertEqual(self.capture(out=after, ONLY="closed book").returncode, 0)
        png = after / "settings-book-inner.png"
        self.assertTrue(png.exists())
        (self.shim / "duo-fails").write_text(f"shot --out {after} --name settings-book\n")
        done = self.capture(out=after, ONLY="closed book")
        self.assertEqual(done.returncode, 3, done.stderr)
        self.assertFalse(png.exists(), "the first pass's shot is not left standing for this pass's")
        self.assertNotIn("settings book", self.text(".captured", after))
        log = self.text("capture.txt", after)
        self.assertIn("  settings: skipped in book: no shot (duo.py shot failed, or saved no inner panel, twice)\n", log)
        self.assertNotIn("app did not rotate", log)
        self.assertIn(".captured): settings book\n", self.text("findings.txt", after))
        self.assertIn("settings: skipped in book: no shot", done.stderr)
        # The other cells of the pass are recorded as before.
        self.assertIn("settings closed", self.text(".captured", after))

    def test_a_missing_snapshot_is_missing_not_clean(self):
        self.runner(silent={"Settings": "book"})
        done = self.capture(ONLY="closed book")
        self.assertEqual(done.returncode, 3, done.stderr)
        self.assertIn("  settings: skipped in book: no snapshot (no answer from the runner in 60 s)\n", self.text("capture.txt"))
        self.assertFalse((self.out / "settings-book.json").exists())
        self.assertIn(".captured): settings book\n", self.text("findings.txt"))

    def test_a_wrong_call_exits_2_and_touches_nothing(self):
        self.assertEqual(self.capture(ONLY="closed").returncode, 0)
        log = self.text("capture.txt")
        for env, said in (({"DUO_UDID": ""}, "DUO_UDID is not set: source .duo/env first"),
                          ({"DUO_PY": str(self.bin / "nowhere.py")}, "is not a file: source .duo/env first"),
                          ({"DUO_TAP_XCTESTRUN": ""}, "build the tap runner"),
                          ({"ONLY": "clsoed"}, 'ONLY="clsoed": clsoed is not a pose'),
                          ({"ONLY": "closed bok"}, "bok is not a pose"),
                          ({"SCREEN": "setings"}, "names none of the flow's screens")):
            done = self.capture(**env)
            self.assertEqual(done.returncode, 2, (env, done.stderr))
            self.assertIn(said, done.stderr)
            self.assertEqual(self.text("capture.txt"), log, env)
            self.assertFalse(self.lock.exists())
        alone = subprocess.run(["bash", str(CAPTURE_FLOW), "Notes", "dev.example.Notes", "folders=Folders"], cwd=self.app,
                               env={**self.env, "OUT": str(self.app / "shots"), "ONLY": "tnet"}, capture_output=True,
                               text=True, timeout=60)
        self.assertEqual(alone.returncode, 2, alone.stderr)
        self.assertFalse((self.app / "shots").exists())

    def test_capture_app_killed_outright_stops_its_flow_and_frees_the_lock(self):
        (self.shim / "hold").write_text("")
        self.runner(hold="Settings:taps")
        env = {**self.env, "ONLY": "closed book", "TAP_TIMEOUT": "6000"}
        first = subprocess.Popen(["bash", str(CAPTURE_APP), str(self.flow), str(self.out)], cwd=self.app, env=env,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            for _ in range(600):
                if (self.shim / "holding").exists():
                    break
                time.sleep(0.05)
            self.assertTrue((self.shim / "holding").exists(), "the capture reached the held screen")
            self.assertRegex(self.lock.read_text(), rf"pid {first.pid}\n(.*\n)*flow pid \d+\n")
            os.kill(first.pid, signal.SIGKILL)   # no trap runs: the flow script is left on its own
            first.wait(timeout=10)
            for _ in range(600):
                if not self.lock.exists():
                    break
                time.sleep(0.05)
            self.assertFalse(self.lock.exists(), "the flow script removed the lock its killed parent left")
            held_runner = int((self.shim / "holding").read_text())
            self.assertIn(f"{held_runner} Settings released", self.runner_log())
            for _ in range(200):
                if self.text("capture.txt").rstrip().splitlines()[-1].startswith("stopped:"):
                    break
                time.sleep(0.05)
            self.assertRegex(self.text("capture.txt").splitlines()[-1],
                             rf"^stopped: capture-app\.sh \(pid {first.pid}\) was killed without stopping the capture at "
                             r"settings, on its way in \(launch and taps\), ")
            (self.shim / "hold").unlink()
            done = self.capture(ONLY="closed book", RESUME="1")
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertNotIn("stale", done.stderr)
        finally:
            try:
                os.killpg(first.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def test_a_lock_whose_flow_script_still_runs_is_live(self):
        fake = self.app.parent / "fake" / "capture-corpus-flow.sh"   # a flow script left running, its parent gone
        fake.parent.mkdir()
        fake.write_text("/bin/sleep 60\n")
        orphan = subprocess.Popen(["bash", str(fake)])
        dead = subprocess.Popen(["true"])
        dead.wait()
        try:
            self.lock.write_text(f"pid {dead.pid}\nstarted 2026-10-31T00:00:00Z\nflow sha256 0\nout /nowhere\n"
                                 f"flow pid {orphan.pid}\n")
            done = self.capture(SCREEN="folders", ONLY="closed")
            self.assertEqual(done.returncode, 5, done.stderr)
            self.assertIn(f"another capture is running: pid {orphan.pid}", done.stderr)
        finally:
            orphan.kill()
            orphan.wait()
        done = self.capture(SCREEN="folders", ONLY="closed")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(f"names pid {dead.pid} (and flow pid {orphan.pid}), which is no running capture", done.stderr)

    def test_a_stale_lock_is_replaced(self):
        dead = subprocess.Popen(["true"])
        dead.wait()
        for pid in (dead.pid, os.getpid()):   # a pid that is gone, and one that is alive but no capture
            self.lock.write_text(f"pid {pid}\nstarted 2026-10-31T00:00:00Z\nflow sha256 0\nout /nowhere\n")
            done = self.capture(SCREEN="folders", ONLY="closed")
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIn(f"replacing a stale capture lock: .duo/.capture.lock names pid {pid}, which is no running capture",
                          done.stderr)
            self.assertFalse(self.lock.exists())

    def test_the_flow_script_alone_takes_the_lock_and_gives_it_back(self):
        out = self.app / "shots"
        head = self.commit()
        done = subprocess.run(["bash", str(CAPTURE_FLOW), "Notes", "dev.example.Notes", "folders=Folders"], cwd=self.app,
                              env={**self.env, "OUT": str(out), "ONLY": "closed"}, capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((out / "folders-closed-cover.png").exists())
        self.assertTrue(self.runner_log()[0].endswith("start locked"))
        self.assertFalse(self.lock.exists())
        # Alone, it takes the code identity itself, once, before the first shot lands.
        self.assertEqual(done.stdout.splitlines()[0], f"code: {head}")
        self.assertEqual((out / ".captured").read_text().split()[1:], ["folders", "closed", head])


class SharedCode(unittest.TestCase):
    def test_every_capture_script_carries_the_same_lock_and_disk_guard(self):
        def functions(path):
            text = path.read_text()
            return [re.search(rf"^{name}\(\) {{(?: [^\n]*}}$|.*?^}}$)", text, re.M | re.S).group(0)
                    for name in ("lock_field", "take_lock", "drop_lock", "low_disk")]
        self.assertEqual(functions(CAPTURE_APP), functions(CAPTURE_FLOW))
        self.assertEqual(functions(CAPTURE_APP), functions(HERE / "capture-corpus-app.sh"))


if __name__ == "__main__":
    unittest.main()
