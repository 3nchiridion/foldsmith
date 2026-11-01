#!/usr/bin/env python3
"""preflight.sh: what a run needs on the Mac, read before anything changes, and .duo/env when nothing blocks.

Hermetic: PATH holds only shims for xcodebuild, xcrun, df, claude and rg (canned answers, every call logged), links to
the few system tools the script uses, and the real git on scratch repositories, so no Xcode, simulator or network is
needed and nothing outside a temporary folder is touched.

    python3 -m unittest discover -s scripts -p 'test_*.py'
"""
import json
import os
import pathlib
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPT = HERE / "preflight.sh"
SKILL_COPY = ROOT / "skills/foldsmith-duo/tools/preflight.sh"
SYSTEM = ["bash", "sh", "sed", "awk", "grep", "head", "tail", "tr", "wc", "ls", "find", "mkdir", "mv", "rm", "cat",
          "date", "dirname", "perl", "plutil"]
RT_ID = "com.apple.CoreSimulator.SimRuntime.iOS-27-1"
DT_ID = "com.apple.CoreSimulator.SimDeviceType.iPhone-Duo"
UDID_A = "E271EE52-72AE-44CD-A2D1-3290C5104761"
UDID_B = "0B0B0B0B-1111-2222-3333-444455556666"


def real_git():
    """The git binary itself: /usr/bin/git is a stub that follows DEVELOPER_DIR, which a test points at a fake Xcode."""
    git = shutil.which("git")
    if git == "/usr/bin/git":
        found = subprocess.run(["xcrun", "-f", "git"], capture_output=True, text=True).stdout.strip()
        git = found or git
    return git


def runtime(version="27.1", ident=RT_ID):
    return {"identifier": ident, "version": version, "buildversion": "24A94425", "isAvailable": True,
            "platform": "iOS", "name": f"iOS {version}"}


def device(name, udid, state="Shutdown", dtype=DT_ID):
    return {"name": name, "udid": udid, "state": state, "isAvailable": True, "deviceTypeIdentifier": dtype}


def simctl(devices=None, runtimes=None):
    runtimes = [runtime()] if runtimes is None else runtimes
    devices = {RT_ID: [device("iPhone Duo", UDID_A, "Booted")]} if devices is None else devices
    return {"devicetypes": [{"identifier": DT_ID, "name": "iPhone Duo"},
                            {"identifier": "com.apple.CoreSimulator.SimDeviceType.iPhone-17", "name": "iPhone 17"}],
            "runtimes": runtimes, "devices": devices}


SHIMS = {
    "xcodebuild": r"""#!/bin/bash
echo "xcodebuild $*" >> "$FAKE_LOG"
if [ -n "$DEVELOPER_DIR" ] && [ -f "$DEVELOPER_DIR/fake-version" ]; then cat "$DEVELOPER_DIR/fake-version"; exit 0; fi
case "$FAKE_XCODE" in
  none) echo "xcode-select: error: tool 'xcodebuild' requires Xcode, but active developer directory" \
          "'/Library/Developer/CommandLineTools' is a command line tools instance" >&2; exit 1 ;;
  license) echo "You have not agreed to the Xcode license agreements. Please run 'sudo xcodebuild -license'" >&2
           exit 69 ;;
  *) printf 'Xcode %s\nBuild version 27A9275\n' "$FAKE_XCODE" ;;
esac
""",
    "xcrun": r"""#!/bin/bash
echo "xcrun $*" >> "$FAKE_LOG"
if [ "$1" = simctl ] && [ "$2" = list ]; then cat "$FAKE_SIMCTL"; exit 0; fi
echo "xcrun shim: unexpected $*" >&2; exit 64
""",
    "df": r"""#!/bin/bash
echo "df $*" >> "$FAKE_LOG"
echo "Filesystem   1024-blocks      Used Available Capacity  Mounted on"
echo "/dev/disk3s1   482797652 414908976 $FAKE_DF_KB    98%    /System/Volumes/Data"
""",
    "claude": r"""#!/bin/bash
echo "claude $*" >> "$FAKE_LOG"
[ "$1" = --version ] && echo "$FAKE_CLAUDE (Claude Code)"
""",
    "rg": r"""#!/bin/bash
[ "$1" = --version ] && echo "ripgrep 14.1.1"
""",
}


class Preflight(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="preflight-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.log = self.tmp / "calls.log"
        self.log.touch()
        self.shims = self.tmp / "shims"
        self.shims.mkdir()
        self.links = self.tmp / "links"
        self.links.mkdir()
        for tool in SYSTEM:
            path = shutil.which(tool)
            if path:
                (self.links / tool).symlink_to(path)
        (self.links / "python3").symlink_to(os.path.realpath(sys.executable))
        self.git = real_git()
        (self.links / "git").symlink_to(self.git)
        for name, body in SHIMS.items():
            (self.shims / name).write_text(body)
            (self.shims / name).chmod(0o755)
        self.app = self.repo(self.tmp / "app")
        self.sims = self.tmp / "simctl.json"
        self.set_sims(simctl())

    # --- helpers
    def g(self, *args, cwd=None):
        return subprocess.run([self.git, "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                              cwd=cwd or self.app, capture_output=True, text=True, check=True,
                              env={"HOME": str(self.home), "PATH": os.environ["PATH"], "GIT_CONFIG_NOSYSTEM": "1"})

    def repo(self, path):
        path.mkdir(parents=True)
        (path / "App.swift").write_text("struct App {}\n")
        self.g("init", "-q", cwd=path)
        self.g("add", "-A", cwd=path)
        self.g("commit", "-q", "-m", "init", cwd=path)
        return path

    def set_sims(self, data):
        self.sims.write_text(json.dumps(data))

    def run_preflight(self, app=None, script=SCRIPT, no=(), **env):
        """Run it; no= leaves those tools off PATH for this run (rg, claude, python3); env adds variables."""
        off = self.tmp / "off"
        off.mkdir(exist_ok=True)
        moved = []
        for tool in no:
            for d in (self.shims, self.links):
                if (d / tool).exists() or (d / tool).is_symlink():
                    (d / tool).rename(off / f"{d.name}-{tool}")
                    moved.append((off / f"{d.name}-{tool}", d / tool))
        base = {"HOME": str(self.home), "PATH": f"{self.shims}:{self.links}", "LANG": "C", "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CEILING_DIRECTORIES": str(self.tmp), "FAKE_LOG": str(self.log), "FAKE_SIMCTL": str(self.sims),
                "FAKE_XCODE": "27.1", "FAKE_DF_KB": str(50 * 10**9 // 1024), "FAKE_CLAUDE": "2.1.308",
                "PREFLIGHT_APPLICATIONS": str(self.tmp / "Applications")}
        base.update({k: str(v) for k, v in env.items()})
        try:
            r = subprocess.run(["bash", str(script), str(app or self.app)], capture_output=True, text=True, env=base,
                               timeout=60)
        finally:
            for src, dst in moved:
                src.rename(dst)
        r.rows = re.findall(r"^(ok|warn|note|missing) +(.*)$", r.stdout, re.M)
        return r

    def tags(self, r):
        return [tag for tag, _ in r.rows]

    def row(self, r, text):
        """The first check line that mentions text, with the lines under it (its fix)."""
        lines = r.stdout.splitlines()
        for i, line in enumerate(lines):
            if re.match(r"^(ok|warn|note|missing) ", line) and text in line:
                j = i + 1
                while j < len(lines) and lines[j].startswith("        "):
                    j += 1
                return "\n".join(lines[i:j])
        self.fail(f"no line mentions {text!r}:\n{r.stdout}")

    def env_file(self, app=None):
        """.duo/env as the shell reads it: source it in bash and print what it set (DUO_*, DEVELOPER_DIR)."""
        return {k: v for k, v in self.sourced(app).items() if not k.startswith("FOLDSMITH_")}

    def sourced(self, app=None):
        """What `source .duo/env` puts in the environment, as the skill does before every tool call."""
        out = subprocess.run(["bash", "-c", 'source "$1" && for k in DUO_UDID DUO_PY DUO_TAP_XCTESTRUN DEVELOPER_DIR FOLDSMITH_ENV FOLDSMITH_ENV_SET; do [ -n "${!k+x}" ] && printf "%s=%s\\0" "$k" "${!k}"; done; true', "-",
                              str((app or self.app) / ".duo/env")],
                             capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"}, check=True).stdout
        return dict(item.split("=", 1) for item in out.split("\0") if item)

    def calls(self):
        return self.log.read_text().splitlines()

    def assert_blocked(self, r):
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("nothing was written", r.stdout)
        self.assertFalse((self.app / ".duo/env").exists())

    # --- the whole pass
    def test_all_ok_writes_env_keeps_it_out_of_git_and_runs_nothing_else(self):
        r = self.run_preflight()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("missing", self.tags(r))
        self.assertNotIn("warn", self.tags(r))
        for text in ("Xcode 27.1 (27A9275)", "iOS 27.1 simulator runtime", f"iPhone Duo ({UDID_A}), booted",
                     "rg 14.1.1", "50.0 GB free", "nothing uncommitted outside .duo/", "Claude Code 2.1.308"):
            self.assertIn(text, r.stdout)
        self.assertIn('duo.py drives only simulators whose name contains "duo"', r.stdout)
        env = self.env_file()
        self.assertEqual(env["DUO_UDID"], UDID_A)
        self.assertEqual(env["DUO_PY"], str(ROOT / "third_party/duo-driver/duo.py"))
        self.assertNotIn("DUO_TAP_XCTESTRUN", env)
        self.assertNotIn("DEVELOPER_DIR", env)
        for key in ("DUO_UDID", "DUO_PY"):
            self.assertIn(f"  {key}={env[key]}", r.stdout)
        exclude = (self.app / ".git/info/exclude").read_text().splitlines()
        self.assertEqual(exclude.count("/.duo/env"), 1)
        self.assertEqual(self.g("status", "--porcelain").stdout, "")
        # Again: the same env, the exclude line not added twice.
        self.assertEqual(self.run_preflight().returncode, 0)
        self.assertEqual((self.app / ".git/info/exclude").read_text().splitlines().count("/.duo/env"), 1)
        # Read-only towards the simulator: it lists, and never creates, boots, renames or erases anything.
        sim_calls = [c for c in self.calls() if c.startswith("xcrun")]
        self.assertTrue(sim_calls)
        self.assertTrue(all(c.startswith("xcrun simctl list") for c in sim_calls), sim_calls)

    def test_the_skill_copy_takes_the_driver_and_tap_project_beside_it(self):
        if not SKILL_COPY.exists():
            self.skipTest("run scripts/sync-skill-references.py first")
        r = self.run_preflight(script=SKILL_COPY)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        tools = SKILL_COPY.parent
        self.assertEqual(self.env_file()["DUO_PY"], str(tools / "driver/duo.py"))
        self.assertIn(f"-project {tools / 'tap/DuoTap.xcodeproj'}", self.row(r, "tap runner"))

    def test_usage(self):
        self.assertEqual(subprocess.run(["bash", str(SCRIPT)], capture_output=True).returncode, 2)
        missing = subprocess.run(["bash", str(SCRIPT), str(self.tmp / "nope")], capture_output=True)
        self.assertEqual(missing.returncode, 2)

    # --- Xcode
    def test_no_xcode_blocks_with_the_install_and_select_fix(self):
        r = self.run_preflight(FAKE_XCODE="none")
        self.assert_blocked(r)
        fix = self.row(r, "Xcode 27.1")
        self.assertTrue(fix.startswith("missing"), fix)
        self.assertIn("xcode-select -s", fix)

    def test_an_unselected_xcode_271_is_used_through_developer_dir(self):
        dev = self.xcode_271()
        r = self.run_preflight(FAKE_XCODE="26.4")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(self.row(r, "Xcode 27.1").startswith("ok"))
        self.assertIn("Xcode 26.4 is selected", r.stdout)
        self.assertEqual(self.env_file()["DEVELOPER_DIR"], str(dev))

    def test_an_older_xcode_with_no_271_installed_blocks(self):
        r = self.run_preflight(FAKE_XCODE="26.4")
        self.assert_blocked(r)
        self.assertIn("Xcode 26.4 is selected", self.row(r, "Xcode 27.1"))

    def xcode_271(self, name="Xcode-27.1.0.app"):
        app = self.tmp / "Applications" / name / "Contents"
        (app / "Developer").mkdir(parents=True)
        (app / "Info.plist").write_bytes(plistlib.dumps({"CFBundleShortVersionString": "27.1"}))
        (app / "Developer/fake-version").write_text("Xcode 27.1\nBuild version 27A9275\n")
        return app / "Developer"

    def test_an_unaccepted_license_says_how_to_accept_it(self):
        r = self.run_preflight(FAKE_XCODE="license")
        self.assert_blocked(r)
        self.assertIn("sudo xcodebuild -license accept", self.row(r, "licence"))
        # The usual case: the selected Xcode is the 27.1 in /Applications. Still the licence fix, not another one.
        self.xcode_271()
        r = self.run_preflight(FAKE_XCODE="license")
        self.assert_blocked(r)
        self.assertIn("sudo xcodebuild -license accept", self.row(r, "licence"))
        self.assertNotIn("runFirstLaunch", r.stdout)

    def test_a_newer_xcode_warns_but_does_not_block(self):
        r = self.run_preflight(FAKE_XCODE="27.2")
        self.assertEqual(r.returncode, 0, r.stdout)
        line = self.row(r, "Xcode 27.2")
        self.assertTrue(line.startswith("warn"), line)
        self.assertNotIn("<Xcode 27.1>", line)

    def test_a_newer_xcode_with_271_installed_uses_271_and_the_build_line_says_so(self):
        dev = self.xcode_271()
        r = self.run_preflight(FAKE_XCODE="27.2")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue(self.row(r, "Xcode 27.1").startswith("ok"))
        self.assertIn("Xcode 27.2 is selected", r.stdout)
        self.assertEqual(self.env_file()["DEVELOPER_DIR"], str(dev))
        self.assertIn(f"DEVELOPER_DIR={dev} xcodebuild build-for-testing", self.row(r, "tap runner"))

    # --- the runtime and the simulator
    def test_no_271_runtime_blocks_with_the_download_line(self):
        self.set_sims(simctl(runtimes=[runtime("27.0", "com.apple.CoreSimulator.SimRuntime.iOS-27-0")], devices={}))
        r = self.run_preflight()
        self.assert_blocked(r)
        self.assertIn("xcodebuild -downloadPlatform iOS", self.row(r, "iOS 27.1 simulator runtime"))

    def test_no_duo_simulator_prints_the_create_line_and_never_runs_it(self):
        self.set_sims(simctl(devices={RT_ID: [device("iPhone 17", UDID_B, dtype="x.iPhone-17")]}))
        r = self.run_preflight()
        self.assert_blocked(r)
        self.assertIn(f'xcrun simctl create "iPhone Duo" {DT_ID} {RT_ID}', self.row(r, "Duo simulator"))
        self.assertFalse([c for c in self.calls() if "create" in c])

    def test_a_duo_renamed_without_duo_explains_the_name_filter(self):
        self.set_sims(simctl(devices={RT_ID: [device("Foldy", UDID_B, "Booted")]}))
        r = self.run_preflight()
        self.assert_blocked(r)
        line = self.row(r, "Duo simulator")
        self.assertIn('"Foldy"', line)
        self.assertIn('name contains "duo"', line)
        self.assertIn(f'xcrun simctl rename {UDID_B} "iPhone Duo"', line)

    def test_a_duo_on_another_runtime_only_still_needs_one_on_271(self):
        other = "com.apple.CoreSimulator.SimRuntime.iOS-27-0"
        self.set_sims(simctl(runtimes=[runtime(), runtime("27.0", other)],
                             devices={other: [device("iPhone Duo", UDID_B)], RT_ID: []}))
        r = self.run_preflight()
        self.assert_blocked(r)
        line = self.row(r, "Duo simulator")
        self.assertIn("iOS-27-0", line)
        self.assertIn(f"{DT_ID} {RT_ID}", line)

    def test_several_duos_take_the_booted_one_unless_duo_udid_names_another(self):
        self.set_sims(simctl(devices={RT_ID: [device("iPhone Duo", UDID_B), device("iPhone Duo 2", UDID_A, "Booted")]}))
        r = self.run_preflight()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.env_file()["DUO_UDID"], UDID_A)
        self.assertIn("2 Duo simulators", r.stdout)
        r = self.run_preflight(DUO_UDID=UDID_B)
        self.assertEqual(self.env_file()["DUO_UDID"], UDID_B)
        self.assertIn("duo.py boots it", self.row(r, "Duo simulator"))
        r = self.run_preflight(DUO_UDID="NOT-A-DUO")
        self.assertEqual(r.returncode, 0, r.stdout)
        line = self.row(r, "DUO_UDID=NOT-A-DUO")
        self.assertTrue(line.startswith("warn"), line)
        # Not the booted one: the one the last .duo/env named, so a run stays on its simulator.
        self.assertIn(f"sets {UDID_B} (the one .duo/env named)", line)
        self.assertEqual(self.env_file()["DUO_UDID"], UDID_B)

    def test_a_resume_takes_the_progress_files_simulator(self):
        self.set_sims(simctl(devices={RT_ID: [device("iPhone Duo", UDID_B), device("iPhone Duo 2", UDID_A, "Booted")]}))
        (self.app / ".duo").mkdir()
        (self.app / ".duo/migration.json").write_text(json.dumps({"app": "App", "simulator": UDID_B, "screens": []}))
        r = self.run_preflight()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.env_file()["DUO_UDID"], UDID_B)
        self.assertIn("the progress file's", self.row(r, "2 Duo simulators"))
        # One the progress file names that is gone: the booted one, and a warning that the shots span two simulators.
        (self.app / ".duo/migration.json").write_text(json.dumps({"simulator": "GONE-UDID", "screens": []}))
        (self.app / ".duo/env").unlink()
        r = self.run_preflight()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.env_file()["DUO_UDID"], UDID_A)
        self.assertTrue(self.row(r, "simulator GONE-UDID").startswith("warn"))

    # --- values inherited from .duo/env
    def skill_copy(self, name, sources_mtime=None):
        """A copy of the skill's tools/ (the preflight, a driver, the tap project) at <tmp>/<name>/tools."""
        tools = self.tmp / name / "tools"
        (tools / "driver").mkdir(parents=True)
        (tools / "tap/DuoTap.xcodeproj").mkdir(parents=True)
        (tools / "tap/DuoTapUITests").mkdir(parents=True)
        shutil.copy(SCRIPT, tools / "preflight.sh")
        for f in ("driver/duo.py", "driver/duo_fold.c", "tap/DuoTap.xcodeproj/project.pbxproj",
                  "tap/DuoTapUITests/DuoTapTests.swift"):
            (tools / f).write_text("")
            if sources_mtime:
                os.utime(tools / f, (sources_mtime, sources_mtime))
        return tools

    def test_values_sourced_from_an_earlier_env_are_derived_again_after_an_update(self):
        products = self.home / "Library/Caches/duo-tap/build/Build/Products"
        products.mkdir(parents=True)
        run = products / "DuoTapUITests_iphonesimulator27.1-arm64.xctestrun"
        run.write_text("")
        os.utime(run, (978307200, 978307200))                     # built in 2001
        old = self.skill_copy("0.8.0", sources_mtime=946684800)  # its sources from 2000
        new = self.skill_copy("0.8.1")                           # the update's, from now
        r = self.run_preflight(script=old / "preflight.sh")
        self.assertEqual(r.returncode, 0, r.stdout)
        env = self.sourced()
        self.assertEqual(env["DUO_PY"], str(old / "driver/duo.py"))
        self.assertEqual(env["DUO_TAP_XCTESTRUN"], str(run))
        self.assertEqual(env["FOLDSMITH_ENV"], str(self.app / ".duo/env"))

        # The update, run after `source .duo/env`: the old copy's driver and the runner built before the new sources
        # are the preflight's own values, so they are derived again, not kept as yours.
        r = self.run_preflight(script=new / "preflight.sh", **env)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("inherited from .duo/env", self.row(r, "DUO_PY"))
        self.assertEqual(self.env_file()["DUO_PY"], str(new / "driver/duo.py"))
        self.assertIn("rebuild it", self.row(r, "tap runner"))
        self.assertNotIn("DUO_TAP_XCTESTRUN", self.env_file())
        self.assertEqual(self.env_file()["DUO_UDID"], UDID_A)

        # A shell that keeps what it sourced (another agent's long-lived one) runs it again after the file was
        # rewritten, the old copy now removed: what it holds is what that file set, so nothing blocks.
        shutil.rmtree(old.parent)
        r = self.run_preflight(script=new / "preflight.sh", **env)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.env_file()["DUO_PY"], str(new / "driver/duo.py"))
        self.assertEqual(self.sourced()["FOLDSMITH_ENV_SET"].splitlines(),
                         [f"DUO_UDID={UDID_A}", f"DUO_PY={new / 'driver/duo.py'}"])

        # A value of your own beside them still wins.
        mine = self.tmp / "mine/duo.py"
        mine.parent.mkdir()
        mine.write_text("")
        r = self.run_preflight(script=new / "preflight.sh", **{**self.sourced(), "DUO_PY": mine})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.env_file()["DUO_PY"], str(mine))
        self.assertIn("(yours", self.row(r, "duo.py: DUO_PY="))

    def test_another_apps_env_sourced_first_is_not_taken_as_yours(self):
        other = self.repo(self.tmp / "other")
        self.assertEqual(self.run_preflight(app=other).returncode, 0)
        # The other app's .duo/env names a skill copy since removed; this app has no .duo/env yet. FOLDSMITH_ENV says
        # where the shell's values came from, so they are that preflight's, not yours.
        gone = str(self.tmp / "removed-copy/tools/driver/duo.py")
        env_path = other / ".duo/env"
        env_path.write_text(env_path.read_text().replace(str(ROOT / "third_party/duo-driver/duo.py"), gone))
        env = self.sourced(other)
        self.assertEqual(env["DUO_PY"], gone)
        r = self.run_preflight(**env)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.env_file()["DUO_PY"], str(ROOT / "third_party/duo-driver/duo.py"))
        # The same path set by you, with no FOLDSMITH_ENV, is yours, and it blocks.
        (self.app / ".duo/env").unlink()
        self.assert_blocked(self.run_preflight(DUO_PY=gone))

    # --- python3, rg
    def test_without_python3_it_blocks_and_says_why(self):
        r = self.run_preflight(no=["python3"])
        self.assert_blocked(r)
        self.assertRegex(r.stdout, r"(?m)^missing +python3$")
        self.assertIn("needs python3", self.row(r, "iOS 27.1 simulator runtime"))
        self.assertFalse([c for c in self.calls() if c.startswith("xcrun")])   # nothing to read the list with

    def test_without_rg_it_blocks_outside_claude_code(self):
        r = self.run_preflight(no=["rg"])
        self.assert_blocked(r)
        self.assertIn("brew install ripgrep", self.row(r, "rg (ripgrep)"))

    def test_in_claude_code_its_own_rg_stands_in(self):
        session = self.shims / "claude-session"
        session.write_text('#!/bin/bash\necho "2.1.309 (Claude Code)"\n')
        session.chmod(0o755)
        r = self.run_preflight(no=["rg", "claude"], CLAUDE_CODE_EXECPATH=session)
        self.assertEqual(r.returncode, 0, r.stdout)
        line = self.row(r, "rg:")
        self.assertTrue(line.startswith("ok"), line)
        self.assertIn("routes.sh runs $CLAUDE_CODE_EXECPATH as rg", line)
        self.assertIn("Claude Code 2.1.309 (this session)", r.stdout)   # the session's own, not claude on PATH

    # --- disk
    def test_under_5_gb_blocks_under_10_warns(self):
        r = self.run_preflight(FAKE_DF_KB=4 * 10**6)
        self.assert_blocked(r)
        self.assertIn("~/Library/Caches/duo-*", self.row(r, "GB free"))
        r = self.run_preflight(FAKE_DF_KB=8 * 10**6)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue(self.row(r, "GB free").startswith("warn"))
        self.assertIn("8.2 GB free", r.stdout)

    # --- the app's repository
    def test_uncommitted_changes_block_but_the_duo_folder_does_not(self):
        (self.app / ".duo/captures").mkdir(parents=True)
        (self.app / ".duo/captures/x.png").write_bytes(b"png")
        (self.app / ".duo/migration.json").write_text("{}")
        self.assertEqual(self.run_preflight().returncode, 0)
        (self.app / "App.swift").write_text("struct App { var x = 1 }\n")
        (self.app / "New.swift").write_text("\n")
        r = self.run_preflight()
        self.assertEqual(r.returncode, 1)
        line = self.row(r, "uncommitted")
        self.assertIn("2 uncommitted change(s)", line)
        self.assertIn("App.swift", line)
        # The printed fix puts the changes aside and leaves the audit's .duo/ where it is.
        stash = re.search(r"put them aside, \.duo/ kept: (git .*)$", line, re.M).group(1)
        self.assertIn("':(exclude).duo'", stash)
        subprocess.run(["bash", "-c", stash], check=True, capture_output=True,
                       env={"HOME": str(self.home), "PATH": os.environ["PATH"], "GIT_CONFIG_NOSYSTEM": "1",
                            "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
                            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"})
        self.assertTrue((self.app / ".duo/migration.json").exists())
        self.assertTrue((self.app / ".duo/captures/x.png").exists())
        self.assertFalse((self.app / "New.swift").exists())
        self.assertEqual(self.run_preflight().returncode, 0)

    def test_on_duo_migration_the_changes_are_the_runs_own(self):
        self.g("switch", "-q", "-c", "duo-migration")
        (self.app / "App.swift").write_text("struct App { var half = 1 }\n")
        r = self.run_preflight()
        self.assert_blocked(r)
        line = self.row(r, "uncommitted")
        self.assertIn("on duo-migration", line)
        self.assertIn("the migration's own", line)
        self.assertIn("stash push --include-untracked -- ':/' ':(exclude).duo'", line)

    def test_nothing_is_written_when_something_blocks(self):
        (self.app / "App.swift").write_text("changed\n")
        r = self.run_preflight()
        self.assert_blocked(r)
        exclude = self.app / ".git/info/exclude"
        self.assertNotIn(".duo/env", exclude.read_text() if exclude.exists() else "")

    def test_a_folder_that_is_not_a_repository_blocks(self):
        plain = self.tmp / "plain"
        plain.mkdir()
        r = self.run_preflight(app=plain)
        self.assertEqual(r.returncode, 1)
        self.assertIn("git init", self.row(r, "not a git repository"))
        self.assertFalse((plain / ".duo").exists())

    def test_an_app_in_a_subfolder_excludes_its_own_duo_folder_only(self):
        root = self.repo(self.tmp / "mono")
        (root / "ios").mkdir()
        (root / "ios/A.swift").write_text("\n")
        self.g("add", "-A", cwd=root)
        self.g("commit", "-q", "-m", "ios", cwd=root)
        (root / "ios/.duo").mkdir()
        (root / "ios/.duo/migration.json").write_text("{}")
        r = self.run_preflight(app=root / "ios")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("/ios/.duo/env", (root / ".git/info/exclude").read_text().splitlines())
        self.assertEqual(self.g("status", "--porcelain", "--untracked-files=all", cwd=root).stdout,
                         "?? ios/.duo/migration.json\n")
        (root / ".duo").mkdir()
        (root / ".duo/stray").write_text("\n")   # another folder's .duo is not the app's
        self.assertEqual(self.run_preflight(app=root / "ios").returncode, 1)

    def test_a_folder_name_with_glob_characters_is_excluded_as_written(self):
        root = self.repo(self.tmp / "mono")
        app = root / "ios app [beta]*"
        app.mkdir()
        (app / "A.swift").write_text("\n")
        self.g("add", "-A", cwd=root)
        self.g("commit", "-q", "-m", "ios", cwd=root)
        r = self.run_preflight(app=app)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("not ignored", r.stdout)
        self.assertIn(r"/ios app \[beta\]\*/.duo/env", (root / ".git/info/exclude").read_text().splitlines())
        self.assertEqual(self.g("status", "--porcelain", "--untracked-files=all", cwd=root).stdout, "")

    # --- Claude Code
    def test_claude_code_absent_is_a_note_and_old_is_a_warning(self):
        r = self.run_preflight(no=["claude"])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue(self.row(r, "Claude Code").startswith("note"))
        r = self.run_preflight(FAKE_CLAUDE="2.1.236")
        self.assertEqual(r.returncode, 0, r.stdout)
        line = self.row(r, "Claude Code 2.1.236")
        self.assertTrue(line.startswith("warn"), line)
        self.assertIn("claude update", line)

    # --- the driver and the tap runner
    def test_a_duo_py_you_set_wins_and_a_wrong_one_blocks(self):
        mine = self.tmp / "my driver's dir" / "duo.py"
        mine.parent.mkdir()
        mine.write_text("")
        r = self.run_preflight(DUO_PY=mine)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.env_file()["DUO_PY"], str(mine))   # quoted so the shell reads it back whole
        (self.app / ".duo/env").unlink()
        r = self.run_preflight(DUO_PY=self.tmp / "gone/duo.py")
        self.assert_blocked(r)
        self.assertIn("unset DUO_PY", self.row(r, "DUO_PY="))

    def test_the_tap_runner_once_built_goes_into_env_and_a_stale_one_is_rebuilt(self):
        r = self.run_preflight()
        line = self.row(r, "tap runner")
        self.assertTrue(line.startswith("note"), line)
        self.assertIn(f"xcodebuild build-for-testing -project {ROOT / 'Tap/DuoTap.xcodeproj'} -scheme DuoTapUITests",
                      line)
        self.assertIn(f"id={UDID_A}", line)
        self.assertIn(str(self.home / "Library/Caches/duo-tap/build"), line)
        products = self.home / "Library/Caches/duo-tap/build/Build/Products"
        products.mkdir(parents=True)
        run = products / "DuoTapUITests_iphonesimulator27.1-arm64.xctestrun"
        run.write_text("")
        r = self.run_preflight()
        self.assertEqual(self.env_file()["DUO_TAP_XCTESTRUN"], str(run))
        self.assertIn(f"  DUO_TAP_XCTESTRUN={run}", r.stdout)
        os.utime(run, (946684800, 946684800))   # built in 2000, before the runner's source last changed
        r = self.run_preflight()
        self.assertIn("rebuild it", self.row(r, "tap runner"))
        self.assertNotIn("DUO_TAP_XCTESTRUN", self.env_file())


if __name__ == "__main__":
    unittest.main()
