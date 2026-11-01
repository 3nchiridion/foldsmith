#!/usr/bin/env python3
"""sdkguard.py: the CI's Xcode (each file form, matrices, variables, a runner's default), the installed ones, and the
iOS 27 uses a branch adds outside a compile-time guard (the SDK's, Foldsmith's and the branch's own guarded names), the
waivers, and Sources/Patterns wrapped whole in the guard.

Scratch git repositories in a temporary folder and a fake /Applications (SDKGUARD_APPLICATIONS), so no Xcode is needed;
the one test that reads the installed iOS SDK (the curated symbols and their versions) skips without an iOS 27.1 SDK.

    python3 -m unittest discover -s scripts -p 'test_*.py'
"""
import importlib.util
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
SCRIPT = HERE / "sdkguard.py"
_spec = importlib.util.spec_from_file_location("sdkguard", SCRIPT)
sdkguard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sdkguard)

WRAP = "wrap it in #if compiler(>=6.4) … #else <the pre-Duo code> #endif, keeping #available inside"
PLAN = ("Xcode 27.0 ships Swift 6.4 like 27.1, so no supported compile-time check separates them: propose moving CI "
        "to Xcode 27.1 in .duo/PLAN.md")
OPENS = "opens iOS 27 code: put it inside #if compiler(>=6.4) with the code it guards"

BASE_SWIFT = """\
import UIKit

final class Root: UISplitViewController {
    override func viewDidLoad() {
        super.viewDidLoad()
    }
}
"""


def workflow(version):
    return f"""\
name: CI
jobs:
  ios:
    runs-on: macos-26
    steps:
      - name: Select Xcode {version}
        run: sudo xcode-select -s /Applications/Xcode_{version}.app/Contents/Developer
      - run: xcodebuild -project App.xcodeproj -scheme App-iOS test
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="sdkguard-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.apps = self.tmp / "Applications"
        self.apps.mkdir()
        self.app = self.tmp / "my app"   # a path with a space
        self.app.mkdir()

    # --- helpers
    def env(self):
        return {"HOME": str(self.home), "PATH": os.environ["PATH"], "GIT_CONFIG_NOSYSTEM": "1", "LANG": "C",
                "GIT_CEILING_DIRECTORIES": str(self.tmp), "SDKGUARD_APPLICATIONS": str(self.apps)}

    def g(self, *args, cwd=None):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                               "-c", "init.defaultBranch=main", *args], cwd=cwd or self.app, capture_output=True,
                              text=True, check=True, env=self.env())

    def write(self, rel, text, root=None):
        path = (root or self.app) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def repo(self, files=None, baseline="duo-baseline"):
        """A repository with the files committed on main, a baseline branch there, and duo-migration checked out."""
        for rel, text in (files or {"App/Root.swift": BASE_SWIFT}).items():
            self.write(rel, text)
        self.g("init", "-q")
        self.g("add", "-A")
        self.g("commit", "-q", "-m", "init")
        if baseline:
            self.g("branch", baseline)
        self.g("switch", "-q", "-c", "duo-migration")

    def commit(self, message="change"):
        self.g("add", "-A")
        self.g("commit", "-q", "-m", message)

    def xcode(self, name, version, build="26F100"):
        contents = self.apps / name / "Contents"
        contents.mkdir(parents=True)
        (contents / "version.plist").write_bytes(plistlib.dumps({"CFBundleShortVersionString": version,
                                                                "ProductBuildVersion": build}))
        return self.apps / name

    def run_guard(self, *args, app=None):
        r = subprocess.run([sys.executable, str(SCRIPT), str(app or self.app), *args], capture_output=True, text=True,
                           env=self.env(), timeout=60)
        r.flagged = re.findall(r"^(\S.*?\.swift):(\d+): (.*)$", r.stdout, re.M)
        return r

    def lines(self, r):
        """{(file, line): message} of the flagged lines."""
        return {(f, int(n)): msg for f, n, msg in r.flagged}


class CIXcode(Base):
    def test_every_ci_file_form_is_read_with_its_line_and_the_lowest_is_the_constraint(self):
        self.write(".github/workflows/ci.yml", workflow("26.6"))
        self.write(".github/workflows/setup.yaml", "steps:\n  - uses: maxim-lobanov/setup-xcode@v1\n"
                                                   "    with:\n      xcode-version: '26.5'\n")
        self.write(".xcode-version", "\n26.4.1\n")
        self.write(".circleci/config.yml", "jobs:\n  build:\n    macos:\n      xcode: \"26.3.0\"\n")
        self.write("bitrise.yml", "meta:\n  bitrise.io:\n    stack: osx-xcode-26.2.x\n")
        self.write(".gitlab-ci.yml", "build:\n  image: macos-15-xcode-26\n")
        self.write(".travis.yml", "language: swift\nosx_image: xcode26.1\n")
        self.write("fastlane/Fastfile", 'lane :ci do\n  xcode_select("/Applications/Xcode-26.0.app")\n'
                                        '  ensure_xcode_version(version: "26.0.1")\nend\n')
        self.write("Makefile", "ci:\n\tDEVELOPER_DIR=/Applications/Xcode_25.4.app/Contents/Developer xcodebuild\n"
                               "select:\n\txcodes select 25.9\n")
        r = self.run_guard("--ci-only")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for at, version in [(".github/workflows/ci.yml:7", "26.6"), (".github/workflows/setup.yaml:4", "26.5"),
                            (".xcode-version:2", "26.4.1"), (".circleci/config.yml:4", "26.3.0"),
                            ("bitrise.yml:3", "26.2"), (".gitlab-ci.yml:2", "26"), (".travis.yml:2", "26.1"),
                            ("fastlane/Fastfile:2", "26.0"), ("fastlane/Fastfile:3", "26.0.1"),
                            ("Makefile:2", "25.4"), ("Makefile:4", "25.9")]:
            self.assertRegex(r.stdout, rf"(?m)^  {re.escape(at)}: Xcode {re.escape(version)} \(", at)
        self.assertNotIn(".github/workflows/ci.yml:6", r.stdout)   # "Select Xcode 26.6", a step's name, is not one
        self.assertIn("lowest, the constraint: Xcode 25.4 (Makefile:2)", r.stdout)
        self.assertIn("schemes the CI builds: App-iOS", r.stdout)
        self.assertRegex(r.stdout, r"(?m)^verdict: CI builds with Xcode 25\.4 \(Makefile:2\), which has no iOS 27 SDK")

    def ci(self, files):
        """--ci-only on a fresh folder holding only these files."""
        shutil.rmtree(self.app)
        self.app.mkdir()
        for rel, text in files.items():
            self.write(rel, text)
        r = self.run_guard("--ci-only")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def test_matrices_variables_actions_and_called_scripts(self):
        job = "jobs:\n  ios:\n    runs-on: macos-26\n"
        cases = {
            "matrix, flow": ({".github/workflows/ci.yml": job + "    strategy:\n      matrix:\n        xcode: ['26.4', "
                              "'27.1']\n    steps:\n      - run: sudo xcode-select -s /Applications/Xcode_${{ "
                              "matrix.xcode }}.app\n"},
                             ["ci.yml:6: Xcode 26.4 (xcode: 26.4)", "ci.yml:6: Xcode 27.1 (xcode: 27.1)",
                              "ci.yml:8: Xcode 26.4 (Xcode_26.4.app, from ${{ matrix.xcode }})",
                              "ci.yml:8: Xcode 27.1 (Xcode_27.1.app, from ${{ matrix.xcode }})"], "26.4"),
            "matrix, block": ({".github/workflows/ci.yml": job + "    strategy:\n      matrix:\n        xcode:\n"
                               "          - \"26.4\"\n          - \"27.1\"\n    steps:\n      - uses: "
                               "maxim-lobanov/setup-xcode@v1\n        with:\n          xcode-version: ${{ matrix.xcode }}\n"},
                              ["ci.yml:7: Xcode 26.4 (xcode: - 26.4)", "ci.yml:12: Xcode 26.4 (xcode-version: 26.4, from ${{ "
                               "matrix.xcode }})"], "26.4"),
            "matrix, include": ({".github/workflows/ci.yml": job + "    strategy:\n      matrix:\n        include:\n"
                                 "          - xcode: \"26.5\"\n          - xcode: \"27.1\"\n    steps:\n      - run: "
                                 "sudo xcode-select -s /Applications/Xcode_${{ matrix.xcode }}.app\n"},
                                ["ci.yml:7: Xcode 26.5 (xcode: \"26.5\")", "ci.yml:10: Xcode 26.5 (Xcode_26.5.app"],
                                "26.5"),
            "a variable": ({".github/workflows/ci.yml": "env:\n  XCODE_VERSION: \"26.6\"\n" + job + "    steps:\n"
                            "      - run: sudo xcode-select -s \"/Applications/Xcode_${XCODE_VERSION}.app\"\n"
                            "      - run: echo /Applications/Xcode_$XCODE_VERSION.app ${{ env.XCODE_VERSION }}\n"},
                           ["ci.yml:7: Xcode 26.6 (Xcode_26.6.app, from ${XCODE_VERSION})",
                            "ci.yml:8: Xcode 26.6 (Xcode_26.6.app, from $XCODE_VERSION)"], "26.6"),
            "a composite action": ({".github/actions/setup/action.yml": "runs:\n  using: composite\n  steps:\n"
                                    "    - uses: maxim-lobanov/setup-xcode@v1\n      with:\n        xcode-version: "
                                    "'26.5'\n"},
                                   [".github/actions/setup/action.yml:6: Xcode 26.5 (xcode-version: '26.5')"], "26.5"),
            "a script the workflow runs": ({".github/workflows/ci.yml": job + "    steps:\n      - run: ./scripts/ci.sh"
                                            " build\n", "scripts/ci.sh": "#!/bin/sh\nsudo xcode-select -s "
                                            "/Applications/Xcode_26.6.app\nxcodebuild -scheme App build\n"},
                                           ["scripts/ci.sh:2: Xcode 26.6 (Xcode_26.6.app)"], "26.6"),
        }
        for name, (files, shown, lowest) in cases.items():
            with self.subTest(name=name):
                got = self.ci(files)
                for line in shown:
                    self.assertIn(line, got)
                self.assertRegex(got, rf"(?m)^verdict: CI builds with Xcode {re.escape(lowest)} ")
                self.assertNotIn("runner image", got)

    def test_comments_cache_keys_and_quotes(self):
        got = self.ci({".github/workflows/ci.yml": "# was Xcode_15.4.app before the move to 27.1\njobs:\n  ios:\n"
                       "    runs-on: macos-26\n    steps:\n      - uses: actions/cache@v4\n        with:\n          key: "
                       "spm-xcode-16-${{ hashFiles('Package.resolved') }}\n      - run: sudo xcode-select -s "
                       "/Applications/Xcode_27.1.app # not Xcode_16.app\n      - uses: maxim-lobanov/setup-xcode@v1\n"
                       "        with:\n          xcode-version: \"27.1\"\n          tag: \"v#2 Xcode_26.0.app\"\n"})
        self.assertIn('ci.yml:12: Xcode 27.1 (xcode-version: "27.1")', got)
        self.assertIn("ci.yml:13: Xcode 26.0", got)   # a # inside quotes is not a comment
        for word in ("15.4", "Xcode 16"):
            self.assertNotIn(word, got)
        # An apostrophe in a word opens no quote: the comment after it is still a comment.
        got = self.ci({".github/workflows/ci.yml": "jobs:\n  ios:\n    runs-on: macos-26\n    steps:\n"
                       "      - name: Build the app's scheme  # was Xcode_15.4.app\n        run: sudo xcode-select -s "
                       "/Applications/Xcode_27.1.app\n"
                       "      - run: xcodebuild -scheme App build --flag='a # Xcode_26.0.app'\n"})
        self.assertNotIn("15.4", got)
        self.assertIn("ci.yml:7: Xcode 26.0", got)   # a # inside a quoted flag is not a comment
        self.assertIn("ci.yml:6: Xcode 27.1 (Xcode_27.1.app)", got)

    def test_a_runners_default_xcode_or_latest_is_said_not_nothing(self):
        build = "    steps:\n      - run: xcodebuild -scheme App build\n"
        got = self.ci({".github/workflows/ci.yml": "jobs:\n  ios:\n    runs-on: macos-15\n" + build})
        self.assertIn("  .github/workflows/ci.yml:3: the runner image's Xcode (runs-on: macos-15), which the repository "
                      "does not name", got)
        self.assertRegex(got, r"(?m)^verdict: no Xcode version is named in the repository: \.github/workflows/ci\.yml:3 "
                              r"builds with the Xcode its runner image picks \(runs-on: macos-15\), which the "
                              r"repository does not name, so check that image's Xcode before trusting a pass; until "
                              r"then sdkguard's lines are notes$")
        self.assertNotIn("nothing says", got)
        got = self.ci({".github/workflows/ci.yml": "jobs:\n  ios:\n    runs-on: macos-15\n    steps:\n      - uses: "
                       "maxim-lobanov/setup-xcode@v1\n        with:\n          xcode-version: latest-stable\n"})
        self.assertIn("ci.yml:7: the runner image's Xcode (setup-xcode's latest-stable)", got)
        got = self.ci({".github/workflows/ci.yml": "jobs:\n  ios:\n    runs-on: macos-26\n" + build,
                       "ci_scripts/ci_post_clone.sh": "#!/bin/sh\n"})
        self.assertIn("ci.yml:3: the runner image's Xcode (runs-on: macos-26)", got)
        self.assertRegex(got, r"(?m)^verdict: no Xcode version is named in the repository: .*before trusting a pass; "
                              r"ci_scripts/ is Xcode Cloud")
        got = self.ci({".github/workflows/lint.yml": "jobs:\n  lint:\n    runs-on: macos-15\n    steps:\n"
                       "      - run: swiftlint\n"})   # builds nothing: not a CI build
        self.assertIn("none found", got)

    def test_a_workflows_scripts_makefile_and_actions_are_read_with_its_variables(self):
        job = "jobs:\n  ios:\n    runs-on: macos-26\n"
        # The workflow sets the variable; the script it runs uses it.
        got = self.ci({".github/workflows/ci.yml": "env:\n  XCODE_VERSION: \"26.6\"\n  XCODE_TIMEOUT: 30\n" + job +
                       "    steps:\n      - run: ./scripts/ci.sh\n",
                       "scripts/ci.sh": "#!/bin/sh\nsudo xcode-select -s \"/Applications/Xcode_${XCODE_VERSION}.app/"
                                        "Contents/Developer\"\nxcodebuild -scheme App build\n"})
        self.assertIn("scripts/ci.sh:2: Xcode 26.6 (Xcode_26.6.app, from ${XCODE_VERSION})", got)
        self.assertIn('ci.yml:2: Xcode 26.6 (XCODE_VERSION: "26.6")', got)   # an xcode variable, where it is set
        self.assertRegex(got, r"(?m)^verdict: CI builds with Xcode 26\.6 ")
        self.assertNotIn("Xcode 30", got)   # a timeout, not a version
        # Makefile syntax: ?=, :=, export and $(NAME).
        for assign in ("XCODE_VERSION ?= 26.6", "XCODE_VERSION := 26.6", "export XCODE_VERSION=26.6"):
            with self.subTest(assign=assign):
                got = self.ci({".github/workflows/ci.yml": job + "    steps:\n      - run: make test\n",
                               "Makefile": f"{assign}\nexport DEVELOPER_DIR := /Applications/Xcode_$(XCODE_VERSION)"
                                           ".app/Contents/Developer\ntest:\n\txcodebuild -scheme App test\n"})
                self.assertIn("Makefile:2: Xcode 26.6 (Xcode_26.6.app, from $(XCODE_VERSION))", got)
                self.assertNotIn("none found", got)
                self.assertNotIn("runner image", got)
        # A local action that names the version is the workflow's: no runner line.
        got = self.ci({".github/workflows/ci.yml": "jobs:\n  ios:\n    runs-on: macos-15\n    steps:\n"
                       "      - uses: ./.github/actions/setup\n      - run: xcodebuild -scheme App build\n",
                       ".github/actions/setup/action.yml": "runs:\n  using: composite\n  steps:\n    - uses: "
                       "maxim-lobanov/setup-xcode@v1\n      with:\n        xcode-version: \"26.5\"\n"})
        self.assertIn(".github/actions/setup/action.yml:6: Xcode 26.5", got)
        self.assertNotIn("runner image", got)
        self.assertNotIn("check the runner", got)
        # .xcode-version, read by xcodes select with no version: no runner line either.
        got = self.ci({".github/workflows/ci.yml": "jobs:\n  ios:\n    runs-on: macos-15\n    steps:\n"
                       "      - run: sudo xcodes select\n      - run: xcodebuild -scheme App build\n",
                       ".xcode-version": "26.6\n"})
        self.assertIn(".xcode-version:1: Xcode 26.6", got)
        self.assertNotIn("runner image", got)

    def test_a_workflow_that_builds_through_a_script_make_or_an_action_on_a_runners_xcode_is_said(self):
        head = "jobs:\n  ios:\n    runs-on: macos-15\n    steps:\n      - uses: actions/checkout@v4\n"
        build = "xcodebuild -scheme App -destination 'generic/platform=iOS Simulator' build\n"
        for name, files in {
            "a script": {".github/workflows/ci.yml": head + "      - run: ./ci/build.sh\n",
                         "ci/build.sh": "#!/bin/sh\n" + build},
            "make": {".github/workflows/ci.yml": head + "      - run: make test\n", "Makefile": "test:\n\t" + build},
            "a local action": {".github/workflows/ci.yml": head + "      - uses: ./.github/actions/build\n",
                               ".github/actions/build/action.yml": "runs:\n  using: composite\n  steps:\n"
                                                                   "    - run: " + build + "      shell: bash\n"},
        }.items():
            with self.subTest(name=name):
                got = self.ci(files)
                self.assertIn("  .github/workflows/ci.yml:3: the runner image's Xcode (runs-on: macos-15), which the "
                              "repository does not name", got)
                self.assertRegex(got, r"(?m)^verdict: no Xcode version is named in the repository: \.github/workflows/"
                                      r"ci\.yml:3 builds with the Xcode its runner image picks")
                self.assertNotIn("none found", got)
        # The script names the Xcode: that, and no runner line.
        got = self.ci({".github/workflows/ci.yml": head + "      - run: ./ci/build.sh\n",
                       "ci/build.sh": "#!/bin/sh\nexport DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer"
                                      "\n" + build})
        self.assertIn("ci/build.sh:2: Xcode 26.6 (Xcode_26.6.app)", got)
        self.assertNotIn("runner image", got)

    def test_a_scripts_shell_default_is_read_under_the_workflows_value(self):
        head = ("jobs:\n  ios:\n    runs-on: macos-15\n    steps:\n      - uses: actions/checkout@v4\n"
                "      - run: ./scripts/ci.sh\n")
        env = 'env:\n  XCODE_VERSION: "27.1"\n'
        select = 'sudo xcode-select -s "/Applications/Xcode_${XCODE_VERSION}.app/Contents/Developer"\n'
        inline = 'sudo xcode-select -s "/Applications/Xcode_${XCODE_VERSION:-26.6}.app/Contents/Developer"\n'
        build = "xcodebuild -scheme App -destination 'generic/platform=iOS Simulator' build\n"
        for name, script, passed, lowest in [
                ("a fallback", 'XCODE_VERSION="${XCODE_VERSION:-26.6}"\n' + select, False, "26.6"),
                ("a fallback, the workflow's value passed in", 'XCODE_VERSION="${XCODE_VERSION:-26.6}"\n' + select,
                 True, "27.1"),
                ("a fallback set with :", ': "${XCODE_VERSION:=26.6}"\n' + select, False, "26.6"),
                ("the script's own value from its argument", "XCODE_VERSION=${1:-26.6}\n" + select, True, "26.6"),
                ("inline", inline, False, "26.6"), ("inline, the workflow's value passed in", inline, True, "27.1")]:
            with self.subTest(name=name):
                got = self.ci({".github/workflows/ci.yml": (env if passed else "") + head,
                               "scripts/ci.sh": "#!/bin/sh\n" + script + build})
                self.assertRegex(got, rf"(?m)^verdict: CI builds with Xcode {re.escape(lowest)} ")
                self.assertNotIn("runner image", got)
                if lowest == "27.1":
                    self.assertNotIn("Xcode 26.6", got)   # a fallback the value passed in overrides is not the CI's
        shutil.rmtree(self.app)
        self.app.mkdir()
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": head,
                   "scripts/ci.sh": '#!/bin/sh\nXCODE_VERSION="${XCODE_VERSION:-26.6}"\n' + select + build})
        self.write("App/One.swift", "import UIKit\nfunc f(_ item: UIBarButtonItem) {\n"
                                    "    item.axisBehavior = .verticalPreferred\n}\n")
        self.commit()
        r = self.run_guard()
        self.assertEqual((r.returncode, sorted(self.lines(r))), (1, [("App/One.swift", 3)]), r.stdout)
        self.assertIn("  scripts/ci.sh:3: Xcode 26.6 (Xcode_26.6.app, from ${XCODE_VERSION})", r.stdout)

    def test_ci_scripts_alone_is_xcode_cloud(self):
        self.write("ci_scripts/ci_post_clone.sh", "#!/bin/sh\nbrew install swiftlint\n")
        r = self.run_guard("--ci-only")
        self.assertEqual(r.returncode, 0)
        self.assertIn("ci_scripts/ is Xcode Cloud, whose Xcode is set in App Store Connect", r.stdout)
        self.assertRegex(r.stdout, r"(?m)^verdict: no CI Xcode found in the repository: ci_scripts/ is Xcode Cloud")

    def test_none_found_says_so(self):
        r = self.run_guard("--ci-only")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("none found", r.stdout)
        self.assertRegex(r.stdout, r"(?m)^verdict: no CI Xcode found in the repository")

    def test_an_app_in_a_subfolder_reads_the_repositorys_ci(self):
        mono = self.tmp / "mono"
        self.write(".github/workflows/ci.yml", workflow("26.6"), root=mono)
        self.write("ios app/.xcode-version", "26.4\n", root=mono)
        self.write("ios app/App/Root.swift", BASE_SWIFT, root=mono)
        self.g("init", "-q", cwd=mono)
        r = self.run_guard("--ci-only", app=mono / "ios app")
        self.assertIn("  ../.github/workflows/ci.yml:7: Xcode 26.6", r.stdout)
        self.assertIn("  .xcode-version:1: Xcode 26.4", r.stdout)
        self.assertIn("lowest, the constraint: Xcode 26.4 (.xcode-version:1)", r.stdout)

    def test_a_matching_installed_xcode_prints_the_build_line(self):
        self.write(".github/workflows/ci.yml", workflow("26.6"))
        self.write("App.xcodeproj/project.pbxproj", "")
        self.xcode("Xcode-27.1.0.app", "27.1", "27A9275")
        xc = self.xcode("Xcode_26.6.app", "26.6.1")
        r = self.run_guard("--ci-only", "--scheme", "App-iOS")
        app = self.app.resolve()
        self.assertIn(f"  {self.apps / 'Xcode-27.1.0.app'}: 27.1 (27A9275)", r.stdout)
        self.assertIn(f"DEVELOPER_DIR={xc}/Contents/Developer xcodebuild -project '{app}/App.xcodeproj' "
                      "-scheme App-iOS -destination 'generic/platform=iOS Simulator' "
                      "-derivedDataPath ~/Library/Caches/duo-build/my-app-ci build", r.stdout)
        # A workspace wins over the project, and without --scheme the line says <scheme>.
        self.write("App.xcworkspace/contents.xcworkspacedata", "")
        r = self.run_guard("--ci-only")
        self.assertIn(f"-workspace '{app}/App.xcworkspace' -scheme <scheme> ", r.stdout)

    def test_no_matching_xcode_says_how_to_get_the_build_line(self):
        self.write(".github/workflows/ci.yml", workflow("26.6"))
        self.xcode("Xcode-27.1.0.app", "27.1")
        self.xcode("Xcode_26.6.1.app", "26.6.1")   # the CI's 26.6 is 26.6.x, but 26.6.1 named exactly is not 26.6.2
        self.write(".github/workflows/ci.yml", workflow("26.6.2"))
        r = self.run_guard("--ci-only")
        self.assertIn("none is the CI's Xcode 26.6.2", r.stdout)
        self.assertNotIn("xcodebuild", r.stdout)


class Uses(Base):
    """The scan, on source text: guards, comments and strings, waivers. Line numbers are 1-based."""

    def scan(self, text, added=None, waived=False):
        lines = text.split("\n")
        hits, quiet = sdkguard.scan_source(text, set(added or range(1, len(lines) + 1)))
        if waived:
            return {n: ([label for label, _, _ in uses], why) for n, uses, why in quiet}
        return {n: ([label for label, _, _ in uses], guarded) for n, uses, guarded in hits}

    def test_compiler_guards_nested_elseif_and_else(self):
        text = """\
#if compiler(>=6.4)
let a = view.reservedRegions(kind: .division)
#if os(iOS)
let b = item.axisBehavior
#else
let c = item.visibilityPriority
#endif
#elseif os(iOS)
let d = view.reservedRegions(kind: .division)
#else
let e = view.reservedRegions(kind: .division)
#endif
#if compiler(<6.4)
let f = view.reservedRegions(kind: .division)
#elseif os(iOS)
let g = view.reservedRegions(kind: .division)
#else
let h = view.reservedRegions(kind: .division)
#endif
#if !compiler(>=6.4)
let i = view.reservedRegions(kind: .division)
#else
let j = view.reservedRegions(kind: .division)
#endif
#if compiler(>=6.4) && os(iOS) && !targetEnvironment(macCatalyst)
let k = view.reservedRegions(kind: .division)
#endif
#if compiler(>=6.4) || os(visionOS)
let l = view.reservedRegions(kind: .division)
#endif
#if os(iOS)
  #if compiler(>=7.0)
let m = view.reservedRegions(kind: .division)
  #endif
let n = view.reservedRegions(kind: .division)
#endif
#if compiler(>=6.2)
let o = view.reservedRegions(kind: .division)
#endif
"""
        found = self.scan(text)
        guarded = {n for n, (_, g) in found.items() if g}
        lines = text.split("\n")
        names = {lines[n - 1].split()[1] for n in guarded}
        self.assertEqual(names, {"a", "b", "c", "g", "h", "j", "k", "m"})
        unguarded = {lines[n - 1].split()[1] for n, (_, g) in found.items() if not g}
        self.assertEqual(unguarded, {"d", "e", "f", "i", "l", "n", "o"})
        self.assertFalse([n for n in found if lines[n - 1].lstrip().startswith("#")])   # directives are not uses

    def test_comments_and_strings_are_not_uses_but_interpolations_are(self):
        text = '''\
// view.reservedRegions(kind: .division)
let a = 1 /* item.axisBehavior /* nested */ still a comment: toolbarVerticalEdge */
let b = "reservedRegions(kind: .division)"
let c = """
    UIHingeInteraction in a multi-line string
    """
let d = #"raw "axisBehavior" \\(not.interpolated.reservedRegions)"#
let e = "frames: \\(proxy.reservedRegions(kind: .division).count) and \\("text \\(item.axisBehavior)")"
let f = #"raw \\#(view.reservedRegions(kind: .division))"#
let g = "escaped quote \\" then UIHinge" + String(describing: UIHinge.self)
let h = url // a comment naming #available(iOS 27.1, *)
'''
        found = self.scan(text)
        self.assertEqual(sorted(found), [8, 9, 10])
        self.assertEqual(found[8][0], ["reservedRegions", "axisBehavior"])
        self.assertEqual(found[9][0], ["reservedRegions"])
        self.assertEqual(found[10][0], ["UIHinge"])

    def test_availability_checks_naming_ios_27(self):
        text = """\
if #available(iOS 27.1, *) { }
guard #available(iOS 27, *) else { return }
@available(iOS 27.0, macOS 27.0, *)
@available(anyAppleOS 27.1, *)
if #unavailable(iOS 27.1) { }
@available(iOS, introduced: 27.1)
if #available(iOS 26.0, *) { }
@available(*, deprecated, message: "old")
"""
        found = self.scan(text)
        self.assertEqual(found[1][0], ["#available(iOS 27.1)"])
        self.assertEqual(found[2][0], ["#available(iOS 27)"])
        self.assertEqual(found[3][0], ["@available(iOS 27.0)"])
        self.assertEqual(found[4][0], ["@available(anyAppleOS 27.1)"])
        self.assertEqual(found[5][0], ["#unavailable(iOS 27.1)"])
        self.assertEqual(found[6][0], ["@available(iOS 27.1)"])
        self.assertNotIn(7, found)
        self.assertNotIn(8, found)

    def test_foldsmith_types_and_lookalikes(self):
        text = """\
FoldAlignedSplit { sidebar } detail: { detail }
content.foldAwareSheetPlacement()
applyFoldAwareSheetPlacement(to: vc)
Arrangement(.split) { a } secondary: { b }
let arrangement = Arrangement.self
// the Arrangement pattern
let style: ArrangementStyle = .overlay
ArrangementView { a } secondary: { b }
@Environment(\\.duoBookFoldIsActive) var fold
let x = UIArrangementViewController.Arrangement.self
"""
        found = self.scan(text)
        self.assertEqual(found[1][0], ["FoldAlignedSplit (a Foldsmith reference type)"])
        self.assertEqual(found[2][0], ["foldAwareSheetPlacement (a Foldsmith reference type)"])
        self.assertNotIn(3, found)                       # the app's own function
        self.assertEqual(found[4][0], ["Arrangement (a Foldsmith reference type)"])
        self.assertNotIn(5, found)
        self.assertNotIn(6, found)
        self.assertEqual(found[7][0], ["ArrangementStyle (a Foldsmith reference type)"])
        self.assertEqual(found[8][0], ["ArrangementView"])
        self.assertEqual(found[9][0], ["duoBookFoldIsActive (a Foldsmith reference type)"])
        self.assertEqual(found[10][0], ["UIArrangementViewController"])

    def test_dotted_names_and_members(self):
        found = self.scan("let p: UISheetPresentationController . Placement = .trailing\n"
                          "sheet.preferredPlacement = p\nitem.isPaddingRemoved = true\n")
        self.assertEqual(found[1][0], ["UISheetPresentationController.Placement"])
        self.assertEqual(found[2][0], ["preferredPlacement"])
        self.assertEqual(found[3][0], ["isPaddingRemoved"])

    def test_waivers_need_a_why(self):
        text = """\
let a = view.reservedRegions(kind: .division) // sdkguard: ok the app's own reservedRegions(kind:) wrapper
// sdkguard: ok built only by the Duo target, which CI does not build
let b = item.axisBehavior
let c = item.axisBehavior // sdkguard: ok
let d = "// sdkguard: ok a string, not a comment"; let e = item.axisBehavior
"""
        self.assertEqual(sorted(self.scan(text)), [4, 5])
        self.assertEqual(self.scan(text, waived=True), {
            1: (["reservedRegions"], "the app's own reservedRegions(kind:) wrapper"),
            3: (["axisBehavior"], "built only by the Duo target, which CI does not build")})

    def test_a_waiver_after_code_is_that_lines_not_the_next_ones(self):
        text = ("t.preferredPlacement = .sidebarOnly // sdkguard: ok UITab.preferredPlacement is iOS 18\n"
                "_ = v.reservedRegions(kind: .division)\n")
        self.assertEqual(self.scan(text), {2: (["reservedRegions"], False)})
        self.assertEqual(self.scan(text, waived=True), {1: (["preferredPlacement"], "UITab.preferredPlacement is iOS 18")})

    def test_an_availability_check_split_over_lines_counts_on_its_first(self):
        text = "if #available(\n    iOS 27.1, *) {\n}\n@available(\n  iOS 27.0, *)\nfunc f() {}\nif #available (iOS 27.1, *) {}\n"
        self.assertEqual(self.scan(text), {1: (["#available(iOS 27.1)"], False), 4: (["@available(iOS 27.0)"], False),
                                           7: (["#available(iOS 27.1)"], False)})
        self.assertEqual(sorted(self.scan(text, added={2})), [1])   # a line it spans was added: it counts

    def test_the_line_that_declares_a_name_is_not_a_use(self):
        text = ("@MainActor enum FoldAlignedSplit {\n    static func prepare() {}\n}\n"
                "FoldAlignedSplit.prepare()\nstruct Arrangement { }\nlet a = Arrangement()\n"
                "extension FoldAlignedSplit { }\n")
        found = self.scan(text)
        self.assertEqual(sorted(found), [4, 6, 7])   # the scan alone: main() drops a name the app declares itself

    def test_declarations_read_every_level_with_its_scope(self):
        text = """\
#if compiler(>=6.4)
extension UIView {
    var windowHasFold: Bool { reservedRegions(kind: .division).isEmpty == false }
    func updateFoldAwareSheetPlacement() { let local = 1 }
    class func make() -> UIView { UIView() }
}
extension Notification.Name {
    static let windowFoldDidChange = Notification.Name("fold")
}
struct FoldReader { var inner: Int }
func applyFoldAwareSheetPlacement(to vc: UIViewController) {}
typealias Fold = Int
#else
extension UIView { var windowHasFold: Bool { false } }
#endif
let plain = 1
final class VC: UIViewController {
    private var isBookFoldActive = false
    private(set) var count = 0
    #if compiler(>=6.4)
    private var hinge: UIHingeInteraction?
    #endif
    enum Mode { case split, overlay }
    init(frame f: CGRect) { super.init(nibName: nil, bundle: nil) }
    func viewDidLoad() {
        let hasFold = false
        switch mode { case .split: break; default: break }
    }
}
"""
        got = [(d.name, d.line, d.guarded, d.scope) + ((d.first, d.last) if d.scope in ("member", "local") else ())
               + (("private",) if d.private else ()) for d in sdkguard.declarations(text)]
        self.assertEqual(got, [
            ("windowHasFold", 3, True, "extension"), ("updateFoldAwareSheetPlacement", 4, True, "extension"),
            ("local", 4, True, "local", 5, 4), ("make", 5, True, "extension"),   # a let is seen from the next line
            ("windowFoldDidChange", 8, True, "extension"), ("FoldReader", 10, True, "top"),
            ("inner", 10, True, "member", 10, 10), ("applyFoldAwareSheetPlacement", 11, True, "top"),
            ("vc", 11, True, "local", 11, 11), ("Fold", 12, True, "top"), ("windowHasFold", 14, False, "extension"),
            ("plain", 16, False, "top"), ("VC", 17, False, "top"),
            ("isBookFoldActive", 18, False, "member", 17, 29, "private"), ("count", 19, False, "member", 17, 29),
            ("hinge", 21, True, "member", 17, 29, "private"), ("Mode", 23, False, "member", 17, 29),
            ("split", 23, False, "member", 23, 23, "private"), ("overlay", 23, False, "member", 23, 23, "private"),
            ("f", 24, False, "local", 24, 24), ("viewDidLoad", 25, False, "member", 17, 29),
            ("hasFold", 26, False, "local", 27, 28)])
        found = sdkguard.declarations(text)
        types = {d.name: d.type_guarded for d in found if d.scope == "member"}
        self.assertEqual((types["inner"], types["hinge"]), (True, False))   # FoldReader is guarded, VC is not
        owners = {(d.name, d.line): d.owner for d in found if d.scope in ("member", "extension")}
        self.assertEqual([owners[k] for k in (("windowHasFold", 3), ("windowFoldDidChange", 8), ("inner", 10),
                                              ("hinge", 21), ("overlay", 23))],
                         ["UIView", "Name", "FoldReader", "VC", "Mode"])
        self.assertEqual([d.name for d in found if d.listed], ["overlay"])

    def test_bindings_lists_and_closures_in_parentheses(self):
        text = """\
final class C {
    private var a = 0, b: Dictionary<String, Int> = [:], c = x < y,
                d = 1
    func f(done: @escaping (Bool) -> Void, g: () -> Void = { }, h: Int) {
        if let p = items.first(where: { $0.ok }), let q = p.next {
            print(p, q)
        }
        guard let r else { return }
        while var s = it.next() {
        }
    }
}
let (t, u) = (1, 2)
"""
        got = [(d.name, d.line, d.scope, d.first, d.last, d.listed) for d in sdkguard.declarations(text)
               if d.scope in ("member", "local")]
        self.assertEqual(got, [
            ("a", 2, "member", 1, 12, False), ("b", 2, "member", 1, 12, True), ("c", 2, "member", 1, 12, True),
            ("d", 3, "member", 1, 12, True), ("f", 4, "member", 1, 12, False),
            ("done", 4, "local", 4, 11, False), ("g", 4, "local", 4, 11, False), ("h", 4, "local", 4, 11, False),
            # an if or while binding is seen in the block it opens, from the line after; a guard's in the rest of
            # its own block
            ("p", 5, "local", 6, 7, False), ("q", 5, "local", 6, 7, False), ("r", 8, "local", 9, 11, False),
            ("s", 9, "local", 10, 10, False)])
        text = "func g() {\n    do {\n        try go()\n    } catch let error {\n        print(error)\n    }\n}\n"
        self.assertEqual([(d.name, d.first, d.last) for d in sdkguard.declarations(text) if d.scope == "local"],
                         [("error", 5, 6)])   # a catch's binding: its block only

    def test_closure_parameters_wrapped_vars_local_owners_and_extension_bodies(self):
        text = """\
final class C {
    @State private var a = 0
    @Published
    var b = 1
    @MainActor var c = 2
    func f() {
        run { [weak self] x, _ in print(x) }
        run { (y: Int, z) -> Void in }
        run { [weak self] in }
    }
}
extension C {
    var d: Int { 0 }
}
"""
        extensions = []
        got = [(d.name, d.line, d.scope, d.first, d.last, d.owner, d.keyword, d.column)
               for d in sdkguard.declarations(text, extensions) if d.scope != "top"]
        self.assertEqual(got, [
            # a wrapped var also declares $x and _x; @MainActor wraps nothing
            ("a", 2, "member", 1, 11, "C", "var", 0), ("$a", 2, "member", 1, 11, "C", "var", 0),
            ("_a", 2, "member", 1, 11, "C", "var", 0), ("b", 4, "member", 1, 11, "C", "var", 0),
            ("$b", 4, "member", 1, 11, "C", "var", 0), ("_b", 4, "member", 1, 11, "C", "var", 0),
            ("c", 5, "member", 1, 11, "C", "var", 0), ("f", 6, "member", 1, 11, "C", "func", 0),
            # a closure's parameters: locals of its block from just after its { (column 13), owned by C
            ("x", 7, "local", 7, 7, "C", "parameter", 13), ("y", 8, "local", 8, 8, "C", "parameter", 13),
            ("z", 8, "local", 8, 8, "C", "parameter", 13), ("d", 13, "extension", None, None, "C", "var", 0)])
        self.assertEqual(extensions, [("C", 12, 14)])

    def test_a_label_named_like_a_guarded_name_is_not_a_use(self):
        app = {"isFolded": (sdkguard.name_pattern("isFolded"), "App/Root.swift:4", None)}
        for line in ["applyColumnWidths(isFolded: false)", "    isFolded: Bool,", "case fold(isFolded: Bool)",
                     "func apply(isFolded folded: Bool)", "f(a: 1, isFolded: 2)", "} isFolded: {",
                     "#selector(mark(isFolded:))", "f(isFolded : true)", "isFolded: for x in xs {"]:
            self.assertEqual(sdkguard.uses(line, [], app), [], line)
        # a ternary's x : y, also continued from a ? at the end of the line above, a dictionary key after [, the value
        for line in ["let a = c ? isFolded : false", "let b = [isFolded: 1]", "apply(isFolded: isFolded)",
                     "    isFolded : false", "if a, isFolded {", "use((isFolded) ? 1 : 2)", "f(isFolded)"]:
            self.assertEqual(sdkguard.uses(line, [], app), [("isFolded", "App/Root.swift:4", "app")], line)
        # a curated symbol as a label is still flagged: an iOS 27 call's label may be the API
        self.assertEqual(sdkguard.uses("UIBarButtonItem(axisBehavior: .verticalPreferred)"),
                         [("axisBehavior", "27.1", "sdk")])

    def test_only_added_lines_count(self):
        text = "let a = item.axisBehavior\nlet b = item.axisBehavior\n"
        self.assertEqual(sorted(self.scan(text, added={2})), [2])


class Verdicts(Base):
    """The whole run on a repository: the three verdicts, base selection, paths."""

    NEW = """\
import UIKit

extension UIView {
    var hasFold: Bool {
        guard #available(iOS 27.1, *) else { return false }
        return !reservedRegions(kind: .division, options: .includeInactive).isEmpty
    }
}

func place(_ sheet: UISheetPresentationController) {
    if #available(iOS 27.0, *) {
        sheet.preferredPlacement = .trailing
    }
}

#if compiler(>=6.4)
@available(iOS 27.1, *)
func hinge(_ view: UIView) {
    view.addInteraction(UIHingeInteraction { _, _ in })
}
@available(iOS 27.0, *)
func later(_ sheet: UISheetPresentationController) { sheet.preferredPlacement = .automatic }
#else
func hinge(_ view: UIView) {}
#endif
"""

    def migrated(self, ci):
        files = {"App/Root.swift": BASE_SWIFT}
        if ci:
            files[".github/workflows/ci.yml"] = workflow(ci)
        self.repo(files)
        self.write("App/Duo/Fold Helpers.swift", self.NEW)   # a path with a space too
        self.commit("Adapt the root to iPhone Duo")

    def test_ci_below_27_every_unguarded_line_is_an_error(self):
        self.migrated("26.6")
        r = self.run_guard()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        f = "App/Duo/Fold Helpers.swift"
        self.assertEqual(self.lines(r), {
            (f, 5): f"#available(iOS 27.1) {OPENS}",   # it compiles anywhere; the code it opens does not
            (f, 6): f"reservedRegions is iOS 27.1: {WRAP}",
            (f, 11): f"#available(iOS 27.0) {OPENS}",
            (f, 12): f"preferredPlacement is iOS 27.0: {WRAP}",
        })
        self.assertIn("errors: 2 lines the CI's Xcode 26.6 does not compile, and 2 availability checks outside #if "
                      "compiler(>=6.4)", r.stdout)
        self.assertIn("4 lines more inside #if compiler(>=6.4): fine", r.stdout)
        self.assertIn("iOS 27 uses added since duo-baseline (", r.stdout)
        self.assertRegex(r.stdout, r"(?m)^verdict: CI builds with Xcode 26\.6 \(\.github/workflows/ci\.yml:7\), which "
                                   r"has no iOS 27 SDK: the 2 lines above do not compile there and 2 availability "
                                   r"checks are outside the guard \(exit 1\)$")

    def test_one_line_reads_as_one(self):
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": workflow("26.6")})
        self.write("App/One.swift", "let a = item.axisBehavior\n")
        self.commit()
        r = self.run_guard()
        self.assertIn("errors: 1 line the CI's Xcode 26.6 does not compile\n", r.stdout)
        self.assertIn("the 1 line above does not compile there (exit 1)", r.stdout)
        self.write("App/One.swift", "if #available(iOS 27.1, *) { }\n")
        self.commit()
        r = self.run_guard()
        self.assertIn("errors: 1 availability check outside #if compiler(>=6.4)\n", r.stdout)
        self.assertIn("which has no iOS 27 SDK: 1 availability check is outside the guard (exit 1)", r.stdout)
        self.write(".github/workflows/ci.yml", workflow("27.0"))
        self.write("App/One.swift", "let a = item.axisBehavior\n")
        self.commit()
        self.assertIn("and 1 line uses iOS 27.1 APIs", self.run_guard().stdout)

    def test_a_helper_wrapped_whole_in_the_guard_needs_its_call_sites_guarded(self):
        # C-R1 again: the run's own helpers wrapped whole in the guard, their call sites not.
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": workflow("26.6")})
        self.write("App/Duo/DuoFold.swift", """\
#if compiler(>=6.4)
import UIKit
extension UIView {
    var windowHasFold: Bool { !reservedRegions(kind: .division, options: .includeInactive).isEmpty }
}
extension Notification.Name {
    static let windowFoldDidChange = Notification.Name("windowFoldDidChange")
}
struct FoldReader {}
#endif
""")
        self.write("App/VC.swift", """\
import UIKit
final class VC: UIViewController {
    func update() {
        let x = view.windowHasFold
        NotificationCenter.default.addObserver(forName: .windowFoldDidChange, object: nil, queue: nil) { _ in }
        _ = FoldReader()
        #if compiler(>=6.4)
        _ = view.windowHasFold
        #endif
    }
}
""")
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(self.lines(r), {
            ("App/VC.swift", 4): "windowHasFold is declared only inside #if compiler(>=6.4) at App/Duo/DuoFold.swift:4: "
                                 "guard this use too",
            ("App/VC.swift", 5): "windowFoldDidChange is declared only inside #if compiler(>=6.4) at "
                                 "App/Duo/DuoFold.swift:7: guard this use too",
            ("App/VC.swift", 6): "FoldReader is declared only inside #if compiler(>=6.4) at App/Duo/DuoFold.swift:9: "
                                 "guard this use too"})
        # An #else stub that declares the same name compiles on the older Xcode: its uses are fine.
        self.write("App/Duo/DuoFold.swift", self.app.joinpath("App/Duo/DuoFold.swift").read_text().replace(
            "struct FoldReader {}\n#endif", "struct FoldReader {}\n#else\nimport UIKit\nextension UIView { var "
            "windowHasFold: Bool { false } }\nextension Notification.Name { static let windowFoldDidChange = "
            "Notification.Name(\"x\") }\nstruct FoldReader {}\n#endif"))
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(r.flagged, [])

    def test_a_member_wrapped_in_the_guard_in_a_type_outside_it_needs_its_uses_guarded(self):
        # sdkguard's own advice ("wrap it in #if compiler(>=6.4)") followed at member level: the type compiles on the
        # older Xcode, its guarded members do not exist there.
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": workflow("26.6")})
        self.write("App/Article.swift", """\
import UIKit
final class ArticleViewController: UIViewController {
    #if compiler(>=6.4)
    private var hinge: UIHingeInteraction?
    private func configureVerticalBarBehavior(for item: UIBarButtonItem) {
        item.axisBehavior = .verticalPreferred
    }
    var foldLabel: String { "fold" }
    #endif
    #if compiler(>=6.4)
    override func viewDidLayoutSubviews() { super.viewDidLayoutSubviews() }
    #endif
    override func viewDidLoad() {
        super.viewDidLoad()
        view.setNeedsLayout(); viewDidLayoutSubviews()
        configureVerticalBarBehavior(for: navigationItem.rightBarButtonItem!)
        title = self.foldLabel
    }
    override func viewDidDisappear(_ animated: Bool) {
        hinge = nil
        #if compiler(>=6.4)
        hinge = nil
        #endif
    }
}
#if compiler(>=6.4)
final class FoldPanel: UIView {
    var panelHinge: UIHingeInteraction?
}
#endif
""")
        self.write("App/Other.swift", "import UIKit\nfunc other(_ a: ArticleViewController, _ p: Any) {\n"
                                      "    configureVerticalBarBehavior(for: UIBarButtonItem())\n"
                                      "    print(a.foldLabel)\n}\n")
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 1, r.stdout)
        at = "is declared only inside #if compiler(>=6.4) at App/Article.swift"
        self.assertEqual(self.lines(r), {
            ("App/Article.swift", 16): f"configureVerticalBarBehavior {at}:5: guard this use too",
            ("App/Article.swift", 17): f"foldLabel {at}:8: guard this use too",
            ("App/Article.swift", 20): f"hinge {at}:4: guard this use too",
            # a private member is seen from its own file only; an internal one from every file
            ("App/Other.swift", 4): f"foldLabel {at}:8: guard this use too"})
        self.assertNotIn("panelHinge", r.stdout)   # a member of a guarded type: the type's name covers it
        self.assertNotIn("viewDidLayoutSubviews", r.stdout)   # an override's name is its superclass's
        # A stub in the same type's #else compiles on the older Xcode: its uses are fine.
        self.write("App/Article.swift", self.app.joinpath("App/Article.swift").read_text().replace(
            '    var foldLabel: String { "fold" }\n    #endif', '    var foldLabel: String { "fold" }\n    #else\n'
            '    private var hinge: Any?\n    private func configureVerticalBarBehavior(for item: UIBarButtonItem) {}\n'
            '    var foldLabel: String { "" }\n    #endif'))
        self.commit()
        r = self.run_guard()
        self.assertEqual((r.returncode, r.flagged), (0, []), r.stdout)

    def test_an_enum_case_wrapped_in_the_guard_counts_in_its_own_file(self):
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": workflow("26.6")})
        self.write("App/Side.swift", "enum SheetSide {\n    case leading\n    #if compiler(>=6.4)\n    case trailing\n"
                                     "    #endif\n}\nlet side: SheetSide = .trailing\n")
        self.write("App/Label.swift", "import SwiftUI\nlet alignment: HorizontalAlignment = .trailing\n")
        self.commit()
        r = self.run_guard()
        self.assertEqual(self.lines(r), {("App/Side.swift", 7): "trailing is declared only inside #if compiler(>=6.4) "
                                                                "at App/Side.swift:4: guard this use too"}, r.stdout)

    def test_a_name_the_type_or_block_declares_itself_outside_the_guard_is_its_own(self):
        # NetNewsWire's RootSplitViewController: its own private isBookFoldActive beside a guarded UIView member of
        # the same name; WebViewController's own @objc windowFoldDidChange beside a guarded Notification.Name.
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": workflow("26.6")})
        self.write("App/Duo/DuoFold.swift", """\
#if compiler(>=6.4)
import UIKit
extension UIView {
    var isBookFoldActive: Bool { !reservedRegions(kind: .division, options: .includeInactive).isEmpty }
}
extension Notification.Name {
    static let windowFoldDidChange = Notification.Name("windowFoldDidChange")
}
#endif
""")
        self.write("App/Split.swift", """\
import UIKit
final class Split: UISplitViewController {
    private var isBookFoldActive = false
    override func viewDidLayoutSubviews() {
        #if compiler(>=6.4)
        let bookFold = view.isBookFoldActive
        #else
        let bookFold = false
        #endif
        if bookFold != isBookFoldActive {
            self.isBookFoldActive = bookFold
            DispatchQueue.main.async { [weak self] in self?.isBookFoldActive = bookFold }
            NotificationCenter.default.addObserver(self, selector: #selector(windowFoldDidChange(_:)), name: nil,
                                                   object: nil)
        }
    }
    @objc func windowFoldDidChange(_ note: Notification) {}
}
func outside(_ s: Split) {
    let isBookFoldActive = true
    print(isBookFoldActive)
}
""")
        self.commit()
        r = self.run_guard()
        self.assertEqual((r.returncode, r.flagged), (0, []), r.stdout)
        # Another receiver's, an implicit member's, or a use outside the type's body is the guarded one.
        self.write("App/Split.swift", self.app.joinpath("App/Split.swift").read_text().replace(
            "        if bookFold != isBookFoldActive {", "        let x = view.isBookFoldActive\n"
            "        let n: Notification.Name = .windowFoldDidChange\n        if bookFold != isBookFoldActive {"))
        self.write("App/Free.swift", "import UIKit\nfunc free() {\n    print(isBookFoldActive)\n}\n")
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(sorted(self.lines(r)), [("App/Free.swift", 3), ("App/Split.swift", 10),
                                                 ("App/Split.swift", 11)])

    def test_a_local_or_parameter_is_the_bare_name_only_and_not_before_its_own_line_ends(self):
        # self.name is always the member; `let x = self.x`, `if let x = x` and the shorthand `if let x {` read the x
        # outside; an if let's name ends with its block. Each flagged line here fails swiftc with the guard false.
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": workflow("26.6")})
        self.write("App/Split.swift", """\
import UIKit
final class SplitController: UIViewController {
    #if compiler(>=6.4)
    private var hinge: (any UIInteraction)?
    private var isBookFoldActive = false
    private var foldInset: CGFloat {
        guard #available(iOS 27.1, *) else { return 0 }
        return view.reservedRegions(kind: .division).first?.frame.width ?? 0
    }
    #endif
    func foldDidChange(_ isBookFoldActive: Bool) {
        guard self.isBookFoldActive != isBookFoldActive else { return }
        self.isBookFoldActive = isBookFoldActive
    }
    override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        if let hinge {
            view.removeInteraction(hinge)
        }
        hinge = nil
    }
    func detach() {
        if let hinge = hinge {
            view.removeInteraction(hinge)
        }
        hinge = nil
    }
    func check() {
        guard let hinge else { return }
        print(hinge)
    }
    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        let foldInset = self.foldInset
        additionalSafeAreaInsets.left = foldInset
    }
    func measure(_ other: UIView?) {
        if let isBookFoldActive = other.map({ $0.bounds.width > 600 }) {
            print(isBookFoldActive)
        }
    }
}
""")
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(sorted(n for f, n in self.lines(r)), [12, 13, 17, 20, 23, 26, 29, 34], r.stdout)
        self.assertIn("every iOS 27 use added", self.run_guard("--base", "HEAD").stdout)   # nothing added: none

    def test_a_guarded_member_beside_another_types_extension_of_that_name(self):
        # The NetNewsWire rerun's names: DuoFold's unguarded UIView.isBookFoldActive, the guard inside its body, and
        # RootSplitViewController's own private isBookFoldActive inside the guard.
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": workflow("26.6")})
        self.write("App/DuoFold.swift", """\
import UIKit
extension UIView {
    var isBookFoldActive: Bool {
        #if compiler(>=6.4)
        if #available(iOS 27.1, *) { return !reservedRegions(kind: .division, options: .includeInactive).isEmpty }
        #endif
        return false
    }
}
""")
        self.write("App/Split.swift", """\
import UIKit
final class Split: UISplitViewController {
    #if compiler(>=6.4)
    private var hinge: (any UIInteraction)?
    private var isBookFoldActive = false
    #endif
    override func viewWillLayoutSubviews() {
        let bookFold = view.isBookFoldActive
        if bookFold != isBookFoldActive {
            isBookFoldActive = bookFold
        }
        super.viewWillLayoutSubviews()
    }
}
final class Panel: UIViewController {
    var folded: Bool { view.isBookFoldActive }
}
""")
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 1, r.stdout)
        # view.isBookFoldActive is the extension's, in Split's body and in Panel's
        self.assertEqual(sorted(self.lines(r)), [("App/Split.swift", 9), ("App/Split.swift", 10)], r.stdout)
        # The same type's #else stub, or a top-level declaration a bare use reaches, compiles on the older Xcode.
        self.write("App/Split.swift", self.app.joinpath("App/Split.swift").read_text()
                   + "#if !compiler(>=6.4)\nextension Split {\n    var isBookFoldActive: Bool {\n"
                     "        get { false }\n        set {}\n    }\n}\n#endif\n")
        self.commit()
        r = self.run_guard()
        self.assertEqual((r.returncode, r.flagged), (0, []), r.stdout)
        self.g("checkout", "-q", "HEAD~1", "--", "App/Split.swift")
        self.write("App/Globals.swift", "var isBookFoldActive = false\n")
        self.commit()
        r = self.run_guard()
        self.assertEqual((r.returncode, r.flagged), (0, []), r.stdout)

    def test_every_name_of_a_guarded_list_and_an_enum_case_named_with_its_enum(self):
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": workflow("26.6")})
        self.write("App/Layout.swift", """\
import UIKit
enum PaneLayout {
    case single
    case sideBySide
    #if compiler(>=6.4)
    case foldAligned, foldTiled
    #endif
}
final class Panes: UIView {
    #if compiler(>=6.4)
    private var foldWidth: CGFloat = 0, foldHeight: CGFloat = 0
    #endif
    func describe(_ l: PaneLayout) -> String {
        switch l {
        case .single, .sideBySide: return "plain"
        case .foldTiled: return "tiled"
        default: return "other"
        }
    }
    func size() -> CGFloat { foldHeight }
}
""")
        self.write("App/Root2.swift", """\
import UIKit
final class Root2: UIViewController {
    var layout = PaneLayout.single
    override func viewDidLoad() {
        super.viewDidLoad()
        layout = .foldAligned
        if case .foldTiled = layout { print("tiled") }
        layout = PaneLayout.foldTiled
    }
}
""")
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(sorted(self.lines(r)), [("App/Layout.swift", 16), ("App/Layout.swift", 20),
                                                 ("App/Root2.swift", 8)], r.stdout)
        self.assertNotIn("more inside", r.stdout)   # :6 and :11 declare foldTiled and foldHeight: not uses

    ROOT_LOCALS = """\
import UIKit
final class Root: UISplitViewController {
    override func viewWillLayoutSubviews() {
        #if compiler(>=6.4)
        let folded: Bool
        if #available(iOS 27.1, *) {
            folded = !view.reservedRegions(kind: .division, options: .includeInactive).isEmpty
        } else {
            folded = false
        }
        #endif
        preferredSplitBehavior = folded ? .tile : .automatic
        super.viewWillLayoutSubviews()
    }
    override func viewDidLoad() {
        super.viewDidLoad()
        #if compiler(>=6.4)
        func foldWidth() -> CGFloat { 455 }
        #endif
        preferredPrimaryColumnWidth = foldWidth()
    }
    func measure() {
        #if compiler(>=6.4)
        var hinge = false
        if #available(iOS 27.1, *) { hinge = true }
        #endif
        print(hinge)
    }
}
"""
    PROBE = """\
import SwiftUI
struct Probe: View {
    @State private var columns = 1
    var body: some View {
        #if compiler(>=6.4)
        let gutter: CGFloat = 40
        #endif
        HStack(spacing: gutter) {
            Text("a")
        }
        .task {
            #if compiler(>=6.4)
            let hingeCount = 2
            #endif
            columns = hingeCount
        }
    }
    func describe() -> String {
        #if compiler(>=6.4)
        let foldNote = "book"
        #endif
        return "pose: " + foldNote
    }
}
"""

    def test_a_local_declared_inside_the_guard_counts_in_the_rest_of_its_block(self):
        # A fold flag computed in the guard and used below it; a local func with no #else twin. swiftc with the guard
        # false (iOS 17): "cannot find 'folded'/'foldWidth'/'hinge' in scope" at Root.swift:12, :20, :27, and
        # 'gutter'/'hingeCount'/'foldNote' at Probe.swift:8, :15, :22; with the guard true (iOS 27.1) no error.
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": workflow("26.6")})
        self.write("App/Root.swift", self.ROOT_LOCALS)
        self.write("App/Probe.swift", self.PROBE)
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 1, r.stdout)
        at = "is declared only inside #if compiler(>=6.4) at"
        self.assertEqual(self.lines(r), {
            ("App/Root.swift", 12): f"folded {at} App/Root.swift:5: guard this use too",
            ("App/Root.swift", 20): f"foldWidth {at} App/Root.swift:18: guard this use too",
            ("App/Root.swift", 27): f"hinge {at} App/Root.swift:24: guard this use too",
            ("App/Probe.swift", 8): f"gutter {at} App/Probe.swift:6: guard this use too",
            ("App/Probe.swift", 15): f"hingeCount {at} App/Probe.swift:13: guard this use too",
            ("App/Probe.swift", 22): f"foldNote {at} App/Probe.swift:20: guard this use too"})
        # Each with its #else local: swiftc has no error either way, and neither does sdkguard.
        stub = "        #else\n        {}\n        #endif\n"
        self.write("App/Root.swift", self.ROOT_LOCALS.replace(
            "        #endif\n        preferredSplitBehavior",
            stub.format("let folded = false") + "        preferredSplitBehavior").replace(
            "{ 455 }\n        #endif\n", "{ 455 }\n" + stub.format("func foldWidth() -> CGFloat { 320 }"))
            .replace("        #endif\n        print(hinge)", stub.format("let hinge = false") + "        print(hinge)"))
        self.write("App/Probe.swift", self.PROBE.replace(
            "        #endif\n        HStack", stub.format("let gutter: CGFloat = 8") + "        HStack")
            .replace("let hingeCount = 2\n            #endif", "let hingeCount = 2\n            #else\n"
                                                              "            let hingeCount = 1\n            #endif")
            .replace('let foldNote = "book"\n        #endif', 'let foldNote = "book"\n        #else\n'
                                                              '        let foldNote = ""\n        #endif'))
        self.commit()
        r = self.run_guard()
        self.assertEqual((r.returncode, r.flagged), (0, []), r.stdout)
        # Members of those names outside the guard: a bare use below the guard is the member (swiftc: no error).
        self.write("App/Root.swift", self.ROOT_LOCALS.replace(
            "UISplitViewController {\n", "UISplitViewController {\n    private var folded = false, hinge = false\n"
                                         "    private func foldWidth() -> CGFloat { 320 }\n"))
        self.g("rm", "-q", "App/Probe.swift")
        self.commit()
        r = self.run_guard()
        self.assertEqual((r.returncode, r.flagged), (0, []), r.stdout)

    def test_a_label_named_like_a_guarded_member_is_not_a_use_and_its_value_is(self):
        # swiftc with the guard false rejects only Root.swift:36, :37, :38, :40, :41, :42 and Gallery.swift:27 here
        # (cannot find 'isFolded'/'alignment' in scope); every label, parameter, associated value and selector compiles.
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": workflow("26.6")})
        self.write("App/Root.swift", """\
import UIKit
struct FoldConfig {
    #if compiler(>=6.4)
    var isFolded = false
    #endif
    init(isFolded: Bool) {}
}
enum Change {
    case fold(isFolded: Bool)
}
final class Root: UISplitViewController {
    #if compiler(>=6.4)
    private var isFolded: Bool { !view.reservedRegions(kind: .division, options: .includeInactive).isEmpty }
    #endif
    override func viewWillLayoutSubviews() {
        super.viewWillLayoutSubviews()
        #if compiler(>=6.4)
        applyColumnWidths(isFolded: isFolded)
        #else
        applyColumnWidths(isFolded: false)
        #endif
        updateColumns(isFolded: false, animated: true)
        var config = FoldConfig(isFolded: false)
        config = FoldConfig(isFolded: true)
        apply(isFolded: true)
        _ = (Change.fold(isFolded: false), config, #selector(Root.mark(isFolded:)))
    }
    private func applyColumnWidths(isFolded: Bool) {}
    private func updateColumns(
        isFolded: Bool,
        animated: Bool
    ) {}
    func apply(isFolded folded: Bool) {}
    @objc func mark(isFolded: Bool) {}
    func uses() {
        let a = true ? isFolded : false
        let b = [isFolded: 1]
        apply(isFolded: isFolded)
        let c = true ?
            isFolded : false
        if a, isFolded {
            print(b, c, (isFolded: isFolded, n: 1))
        }
    }
}
""")
        self.write("App/Gallery.swift", """\
import SwiftUI
struct GalleryView: View {
    #if compiler(>=6.4)
    private var columns: [GridItem] { [GridItem(.adaptive(minimum: 200))] }
    private var alignment: HorizontalAlignment { .leading }
    #endif
    var body: some View {
        #if compiler(>=6.4)
        LazyVGrid(columns: columns, alignment: alignment) { Text("Duo") }
        #else
        VStack(alignment: .center) {
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 150))]) { Text("pre-Duo") }
        }
        #endif
        HStack(alignment: .firstTextBaseline) { Text("a") }
        LazyVGrid(
            columns: [GridItem(.flexible())],
            spacing: 8
        ) {
            Text("b")
        }
        NavigationSplitView {
            Text("side")
        } detail: {
            Text("detail")
        }
        VStack(alignment: true ? alignment : .center) { Text("c") }
    }
}
""")
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(sorted(self.lines(r)), [("App/Gallery.swift", 27)] + [
            ("App/Root.swift", n) for n in (36, 37, 38, 40, 41, 42)], r.stdout)

    def test_an_override_in_a_guarded_extension_is_its_superclasss(self):
        # A Root+Duo extension wrapped whole in the guard: swiftc with the guard false accepts every super call and
        # root.viewDidLayoutSubviews() elsewhere, and rejects only Other.swift:11 (no member 'foldDidChange').
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": workflow("26.6")})
        self.write("App/Root.swift", """\
import UIKit
final class Root: UISplitViewController {}
#if compiler(>=6.4)
extension Root {
    override func viewDidLayoutSubviews() { super.viewDidLayoutSubviews(); view.setNeedsLayout() }
    override func traitCollectionDidChange(_ previous: UITraitCollection?) {
        super.traitCollectionDidChange(previous)
    }
    func foldDidChange() {}
}
#endif
""")
        self.write("App/Other.swift", """\
import UIKit
final class Other: UIViewController {
    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
    }
    override func traitCollectionDidChange(_ previous: UITraitCollection?) {
        super.traitCollectionDidChange(previous)
    }
    func poke(_ root: Root) {
        root.viewDidLayoutSubviews()
        root.foldDidChange()
    }
}
""")
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(self.lines(r), {("App/Other.swift", 11): "foldDidChange is declared only inside "
                                                                  "#if compiler(>=6.4) at App/Root.swift:9: guard this "
                                                                  "use too"})

    def test_a_shorthand_binding_on_a_continuation_line_is_a_use(self):
        # swift-format's one clause per line. swiftc with the guard false: "cannot find 'hingeOffset' in scope" at :9
        # (`let hingeOffset {`), :13 (`let hingeOffset else`) and :18 (`let offset = hingeOffset {`); :22's binding
        # declares its own and compiles.
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": workflow("26.6")})
        self.write("App/Root.swift", """\
import UIKit
final class Root: UIViewController {
    #if compiler(>=6.4)
    private var hingeOffset: CGFloat?
    #endif
    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        if let window = view.window,
           let hingeOffset {
            print(window, hingeOffset)
        }
        guard let window = view.window,
              let hingeOffset else { return }
        print(window, hingeOffset)
    }
    func other() {
        if let window = view.window,
           let offset = hingeOffset {
            print(window, offset)
        }
        if let window = view.window,
           let hingeOffset = view.window?.frame.width {
            print(window, hingeOffset)
        }
    }
}
""")
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(sorted(n for _, n in self.lines(r)), [9, 13, 18], r.stdout)

    def test_a_closures_parameter_is_a_local_from_its_brace(self):
        # swiftc with the guard false rejects only :17 (print(isFolded)), :18 (the observe(isFolded) before the
        # closure's brace) and :22 (self?.isFolded): each closure parameter named like a guarded member compiles.
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": workflow("26.6")})
        self.write("App/Root.swift", """\
import UIKit
final class Root: UIViewController {
    #if compiler(>=6.4)
    private var isFolded = false
    private var foldFrame: CGRect = .zero
    #endif
    var onFoldChange: ((Bool) -> Void)?
    let label = UILabel()
    override func viewDidLoad() {
        super.viewDidLoad()
        onFoldChange = { [weak self] isFolded in
            self?.label.isHidden = !isFolded
        }
        [CGRect.zero].forEach { foldFrame in
            print(foldFrame)
        }
        print(isFolded)
        observe(isFolded) { _, isFolded in
            print(isFolded)
        }
        observe(true) { (old: Bool, isFolded: Bool) -> Void in print(old, isFolded) }
        onFoldChange = { [weak self] isFolded in self?.label.isHidden = self?.isFolded ?? isFolded }
        let first = [true].first(where: { isFolded in isFolded })
        print(first as Any)
    }
    func observe(_ value: Bool, _ body: (Bool, Bool) -> Void) {}
}
""")
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(sorted(n for _, n in self.lines(r)), [17, 18, 22], r.stdout)

    def test_a_guarded_property_wrapper_is_used_through_its_projection_and_storage(self):
        # swiftc with the guard false: "cannot find '$followsFold'/'$showsFoldTips'/'_ratio'/'_foldSelection' in
        # scope" at :11, :13, :22, :23, and "value of type 'FoldModel' has no member '$isBookFold'" at :35.
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": workflow("26.6")})
        self.write("App/Settings.swift", """\
import SwiftUI
import Combine
struct SettingsView: View {
    #if compiler(>=6.4)
    @State private var followsFold = true
    @State
    private var showsFoldTips = false
    #endif
    var body: some View {
        Form {
            Toggle("Keep panes off the fold", isOn: $followsFold)
        }
        .sheet(isPresented: $showsFoldTips) { Text("Tips") }
    }
}
struct FoldPane: View {
    #if compiler(>=6.4)
    @State private var ratio: CGFloat
    @Binding var foldSelection: Int
    #endif
    init(ratio: CGFloat, foldSelection: Binding<Int>) {
        _ratio = State(initialValue: ratio)
        _foldSelection = foldSelection
    }
    var body: some View { Text("pane") }
}
final class FoldModel: ObservableObject {
    #if compiler(>=6.4)
    @Published var isBookFold = false
    #endif
}
final class Watcher {
    var bag = Set<AnyCancellable>()
    func watch(_ model: FoldModel) {
        model.$isBookFold.sink { print($0) }.store(in: &bag)
    }
}
""")
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 1, r.stdout)
        at = "is declared only inside #if compiler(>=6.4) at App/Settings.swift"
        self.assertEqual(self.lines(r), {
            ("App/Settings.swift", 11): f"$followsFold {at}:5: guard this use too",
            ("App/Settings.swift", 13): f"$showsFoldTips {at}:7: guard this use too",
            ("App/Settings.swift", 22): f"_ratio {at}:18: guard this use too",
            ("App/Settings.swift", 23): f"_foldSelection {at}:19: guard this use too",
            ("App/Settings.swift", 35): f"$isBookFold {at}:29: guard this use too"})
        # An #else @State stub has $x too; an #else let stub has x and not $x (swiftc: :15 only).
        self.write("App/Settings.swift", """\
import SwiftUI
struct StubbedView: View {
    #if compiler(>=6.4)
    @State private var followsFold = true
    #else
    @State private var followsFold = false
    #endif
    #if compiler(>=6.4)
    @State private var showsTips = true
    #else
    private let showsTips = false
    #endif
    var body: some View {
        Toggle(showsTips ? "Tips" : "Fold", isOn: $followsFold)
        Toggle("Tips", isOn: $showsTips)
    }
}
""")
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(sorted(self.lines(r)), [("App/Settings.swift", 15)], r.stdout)

    def test_a_type_whose_pre_duo_twin_is_in_else_keeps_the_members_only_the_guarded_one_has(self):
        # swiftc with the guard false: "value of type 'ReaderContentView' has no member 'foldInset'" at
        # ReaderController.swift:8 and "value of type 'FoldMetrics' has no member 'hingeWidth'" at Metrics.swift:16.
        twin = """\
import UIKit
#if compiler(>=6.4)
final class ReaderContentView: UIView {
    var foldInset: CGFloat = 0
    var columnWidth: CGFloat = 320
    override func layoutSubviews() { super.layoutSubviews() }
}
#else
final class ReaderContentView: UIView {
    var columnWidth: CGFloat = 320
    override func layoutSubviews() { super.layoutSubviews() }
}
#endif
"""
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": workflow("26.6")})
        self.write("App/ReaderView.swift", twin)
        self.write("App/ReaderController.swift", """\
import UIKit
final class ReaderController: UIViewController {
    let content = ReaderContentView()
    override func viewDidLoad() {
        super.viewDidLoad()
        view.addSubview(content)
        content.columnWidth = 300
        content.foldInset = 40
    }
}
""")
        self.write("App/Metrics.swift", """\
import SwiftUI
#if compiler(>=6.4)
struct FoldMetrics {
    var columnWidth: CGFloat = 320
    var hingeWidth: CGFloat = 20
}
#else
struct FoldMetrics {
    var columnWidth: CGFloat = 320
}
#endif
struct MetricsView: View {
    let metrics = FoldMetrics()
    var body: some View {
        Text("\\(metrics.columnWidth)")
            .padding(.leading, metrics.hingeWidth)
    }
}
""")
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(self.lines(r), {
            ("App/ReaderController.swift", 8): "foldInset is declared only inside #if compiler(>=6.4) at "
                                               "App/ReaderView.swift:4: guard this use too",
            ("App/Metrics.swift", 16): "hingeWidth is declared only inside #if compiler(>=6.4) at "
                                       "App/Metrics.swift:5: guard this use too"})
        # The #else twin declares foldInset too: swiftc has no error, nor sdkguard.
        self.write("App/ReaderView.swift", twin.replace(
            "final class ReaderContentView: UIView {\n    var columnWidth",
            "final class ReaderContentView: UIView {\n    var foldInset: CGFloat = 0\n    var columnWidth"))
        self.g("rm", "-q", "App/Metrics.swift")
        self.commit()
        r = self.run_guard()
        self.assertEqual((r.returncode, r.flagged), (0, []), r.stdout)

    def test_a_types_own_member_is_its_own_in_its_extensions_too(self):
        # An environment key's property under the key's name, its #else stub, subviews in extensions. swiftc with the
        # guard false rejects only Views.swift:23 (env.foldInset); the bare uses in extension DetailView here and in
        # DetailFooter.swift, and SideView's private stub in its own file's extension, compile.
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": workflow("26.6")})
        self.write("App/Env.swift", """\
import SwiftUI
#if compiler(>=6.4)
extension EnvironmentValues {
    @Entry var foldInset: CGFloat = 0
}
#endif
""")
        self.write("App/Views.swift", """\
import SwiftUI
struct DetailView: View {
    #if compiler(>=6.4)
    @Environment(\\.foldInset) var foldInset
    #else
    let foldInset: CGFloat = 0
    #endif
    var body: some View {
        VStack {
            header
            Text("Body").padding(.leading, foldInset)
            footer
        }
    }
}
extension DetailView {
    var header: some View { Text("Header").padding(.leading, foldInset) }
}
struct Plain {
    var foldInset: CGFloat = 0
}
func read(_ plain: Plain, _ env: EnvironmentValues) -> CGFloat {
    plain.foldInset + env.foldInset
}
struct SideView: View {
    #if compiler(>=6.4)
    @Environment(\\.foldInset) private var foldInset
    #else
    private let foldInset: CGFloat = 0
    #endif
    var body: some View { Text("Side").padding(.leading, foldInset) }
}
extension SideView {
    var label: some View { Text("Label").padding(.leading, foldInset) }
}
""")
        self.write("App/DetailFooter.swift", """\
import SwiftUI
extension DetailView {
    var footer: some View { Text("Footer").padding(.leading, foldInset) }
}
""")
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(self.lines(r), {("App/Views.swift", 23): "foldInset is declared only inside "
                                                                  "#if compiler(>=6.4) at App/Env.swift:4: guard this "
                                                                  "use too"})

    def test_a_foldsmith_name_the_app_declares_itself_is_the_apps(self):
        # The first run named its own UIKit helper enum FoldAlignedSplit, unguarded.
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": workflow("26.6")})
        self.write("App/FoldAlignedSplit.swift", "import UIKit\n@MainActor enum FoldAlignedSplit {\n"
                                                 "    static func hasFold(_ v: UIView) -> Bool { false }\n}\n")
        self.write("App/Use.swift", "import UIKit\nlet f = FoldAlignedSplit.hasFold(UIView())\n")
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(r.flagged, [])
        self.assertIn("note: FoldAlignedSplit is declared by the app at App/FoldAlignedSplit.swift:2, not Foldsmith's",
                      r.stdout)

    def test_waived_lines_are_listed_and_the_verdict_says_so(self):
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": workflow("26.6")})
        self.write("App/Tabs.swift", "// sdkguard: ok the Duo target only, which CI does not build\n"
                                     "_ = v.reservedRegions(kind: .division)\n")
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("waived: 1 line with // sdkguard: ok, each with its why (the review reads them):\n"
                      "  App/Tabs.swift:2: reservedRegions is iOS 27.1: the Duo target only, which CI does not build",
                      r.stdout)
        self.assertNotIn("\n  none\n", r.stdout)
        self.assertIn("every iOS 27 use added is inside #if compiler(>=6.4) or waived (1) (exit 0)", r.stdout)

    def test_ci_below_27_with_every_use_guarded_passes(self):
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": workflow("26.6")})
        self.write("App/Duo/Guarded.swift", "#if compiler(>=6.4)\n" + self.NEW + "#endif\n")
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(r.flagged, [])
        self.assertIn("every iOS 27 use added is inside #if compiler(>=6.4) (exit 0)", r.stdout)

    def test_ci_on_27_0_refuses_27_1_symbols_even_guarded_and_passes_27_0(self):
        self.migrated("27.0")
        r = self.run_guard()
        self.assertEqual(r.returncode, 1, r.stdout)
        f = "App/Duo/Fold Helpers.swift"
        got = self.lines(r)
        self.assertEqual(got[(f, 6)], f"reservedRegions is iOS 27.1: {PLAN}")
        self.assertEqual(got[(f, 19)], f"UIHingeInteraction is iOS 27.1: {PLAN}")   # guarded: 27.0 passes the guard
        for n in (5, 11, 12):   # an availability check, and 27.0 symbols: notes, not errors
            self.assertTrue(got[(f, n)].endswith("not inside #if compiler(>=6.4)"), got[(f, n)])
        self.assertNotIn((f, 22), got)   # 27.0 inside the guard: fine
        self.assertIn("errors: 2 lines the CI's Xcode 27.0 does not compile", r.stdout)
        self.assertRegex(r.stdout, r"(?m)^verdict: CI builds with Xcode 27\.0 .*and 2 lines use iOS 27\.1 APIs: "
                                   r"Xcode 27\.0 ships Swift 6\.4 like 27\.1, .*\.duo/PLAN\.md \(exit 1\)$")
        # Only 27.0 symbols: they build there.
        self.write("App/Duo/Fold Helpers.swift", "import UIKit\nfunc place(_ s: UISheetPresentationController) {\n"
                                                 "    s.preferredPlacement = .trailing\n}\n")
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("no iOS 27.1 API is used, and the iOS 27.0 ones build there (exit 0)", r.stdout)
        # A waived 27.1 line: the verdict does not say none is used.
        self.write("App/Duo/Fold Helpers.swift", "import UIKit\nfunc fold(_ v: UIView) -> Bool {\n"
                                                 "    // sdkguard: ok built only by the Duo target, not by this CI\n"
                                                 "    return !v.reservedRegions(kind: .division).isEmpty\n}\n")
        self.commit()
        r = self.run_guard()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("no iOS 27.1 API is used outside the 1 line waived, and the iOS 27.0 ones build there (exit 0)",
                      r.stdout)

    def test_ci_on_27_1_or_none_found_makes_notes(self):
        for ci in ("27.1", None):
            with self.subTest(ci=ci):
                shutil.rmtree(self.app)
                self.app.mkdir()
                self.migrated(ci)
                r = self.run_guard()
                self.assertEqual(r.returncode, 0, r.stdout)
                self.assertEqual(len(r.flagged), 4)
                self.assertTrue(all(msg.endswith("not inside #if compiler(>=6.4)") for _, _, msg in r.flagged))
                self.assertIn("notes: 4 lines outside #if compiler(>=6.4)", r.stdout)
                self.assertIn("which has the iOS 27.1 SDK" if ci else "no CI Xcode found in the repository", r.stdout)

    def test_ci_only_reads_no_code_always_exits_0_and_writes_nothing(self):
        self.migrated("26.6")
        self.write("App/Untracked.swift", "let x = item.axisBehavior\n")
        index = self.app / ".git/index"
        os.utime(index, (946684800, 946684800))
        before = {p: p.stat().st_mtime for p in self.app.rglob("*")}
        r = self.run_guard("--ci-only")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(r.flagged, [])
        self.assertNotIn("uses added", r.stdout)
        self.assertEqual(r.stdout.strip().splitlines()[-1][:9], "verdict: ")
        self.run_guard()
        self.assertEqual({p: p.stat().st_mtime for p in self.app.rglob("*")}, before)

    def test_only_lines_added_since_the_base_count_and_untracked_files_whole(self):
        self.repo({"App/Root.swift": BASE_SWIFT.replace("super.viewDidLoad()",
                                                        "super.viewDidLoad()\n        _ = item.axisBehavior"),
                   ".github/workflows/ci.yml": workflow("26.6")})
        root = self.app / "App/Root.swift"
        root.write_text(root.read_text().replace("super.viewDidLoad()\n",
                                                 "super.viewDidLoad()\n        _ = item.visibilityPriority\n"))
        self.g("mv", "App/Root.swift", "App/Moved Root.swift")             # renamed: only its new line counts
        self.write("App/New.swift", "import UIKit\nlet a = 1\nlet b = item.axisBehavior\n")   # untracked
        self.write(".duo/flows/Example.swift", "let x = item.axisBehavior\n")                  # .duo/ never counts
        self.write("Notes.md", "item.axisBehavior\n")
        r = self.run_guard()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(sorted(self.lines(r)), [("App/Moved Root.swift", 6), ("App/New.swift", 3)])
        self.assertIn("in 2 changed Swift files", r.stdout)

    def test_base_selection(self):
        self.repo({"App/Root.swift": BASE_SWIFT, ".github/workflows/ci.yml": workflow("26.6")}, baseline=None)
        first = self.g("rev-parse", "HEAD").stdout.strip()
        self.write("App/A.swift", "let a = item.axisBehavior\n")
        self.commit("a")
        middle = self.g("rev-parse", "HEAD").stdout.strip()
        self.write("App/B.swift", "let b = item.axisBehavior\n")
        self.commit("b")
        # No duo-baseline: the merge base with main.
        r = self.run_guard()
        self.assertIn("since the merge base with main (", r.stdout)
        self.assertEqual(sorted(f for f, _ in self.lines(r)), ["App/A.swift", "App/B.swift"])
        # duo-baseline wins over main.
        self.g("branch", "duo-baseline", middle)
        r = self.run_guard()
        self.assertIn(f"since duo-baseline ({middle[:7]}", r.stdout)
        self.assertEqual(sorted(f for f, _ in self.lines(r)), ["App/B.swift"])
        # --base wins over both.
        r = self.run_guard("--base", first)
        self.assertEqual(sorted(f for f, _ in self.lines(r)), ["App/A.swift", "App/B.swift"])
        r = self.run_guard("--base", "no-such-rev")
        self.assertEqual(r.returncode, 2)
        self.assertIn("--base no-such-rev: no such commit", r.stderr)

    def test_no_base_asks_for_one_and_a_clone_of_a_run_is_not_its_own_base(self):
        self.repo({"App/Root.swift": BASE_SWIFT}, baseline="duo-baseline")
        clone = self.tmp / "clone of run"
        self.g("clone", "-q", str(self.app), str(clone), cwd=self.tmp)
        # The clone has origin/HEAD → origin/duo-migration and no local duo-baseline, main or master.
        r = self.run_guard(app=clone)
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("Pass --base <rev>", r.stderr)
        self.assertIn("origin/HEAD is origin/duo-migration, a run's own branch", r.stderr)
        self.assertIn("--base origin/duo-baseline", r.stderr)
        self.assertEqual(r.stdout, "")   # nothing printed before a wrong call
        self.assertEqual(self.run_guard("--base", "origin/duo-baseline", app=clone).returncode, 0)

    def test_wrong_calls(self):
        self.assertEqual(self.run_guard(app=self.tmp / "nope").returncode, 2)
        r = self.run_guard()   # not a repository
        self.assertEqual(r.returncode, 2)
        self.assertIn("not a git repository", r.stderr)
        self.assertEqual(self.run_guard("--ci-only").returncode, 0)
        self.assertEqual(self.run_guard("--bogus").returncode, 2)


# --- The curated symbols against the installed SDK

def ios_sdk():
    """The iOS 27.1 (or later) SDK's path, or None."""
    try:
        sdk = subprocess.run(["xcrun", "--sdk", "iphoneos", "--show-sdk-path"], capture_output=True, text=True,
                             timeout=60).stdout.strip()
        version = subprocess.run(["xcrun", "--sdk", "iphoneos", "--show-sdk-version"], capture_output=True, text=True,
                                 timeout=60).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    if not sdk or not pathlib.Path(sdk).is_dir() or sdkguard.vtuple(version or "0") < (27, 1):
        return None
    return pathlib.Path(sdk)


SWIFT_DECL = re.compile(r"\b(?:func|var|let|case|class|struct|enum|protocol|typealias|actor|associatedtype)\s+`?"
                        r"([A-Za-z_]\w*)")
AVAILABLE = re.compile(r"@available\(\s*(?:iOS|anyAppleOS)\s*(?:,\s*introduced\s*:\s*)?(\d+(?:\.\d+)*)")
IOS = re.compile(r"\bios\((\d+(?:\.\d+)*)\)")
ATTRIBUTES = re.compile(r"^(?:@[\w:]+(?:\((?:[^()]|\([^()]*\))*\))?\s*)+")


class SDK:
    """Where the iOS SDK declares a name, and from which iOS version: SwiftUI, SwiftUICore and UIKit's
    swiftinterfaces, UIKit's headers (the Objective-C-only API: UIHingeInteraction, the vertical bar)."""

    def __init__(self, sdk):
        frameworks = sdk / "System/Library/Frameworks"
        self.swift = {}
        for fw in ("SwiftUI", "SwiftUICore", "UIKit"):
            module = frameworks / f"{fw}.framework/Modules/{fw}.swiftmodule"
            for f in sorted(module.glob("*-apple-ios.swiftinterface")):
                self.read_swift(f.read_text(errors="replace").split("\n"))
                break
        self.statements, self.where = [], {}
        for h in sorted((frameworks / "UIKit.framework/Headers").glob("*.h")):
            self.read_header(h.read_text(errors="replace"))

    def read_swift(self, lines):
        def indent(s):
            return len(s) - len(s.lstrip())

        def version(i):
            j = i
            while True:
                k = j - 1
                block = [lines[j]]
                while k >= 0 and lines[k].lstrip().startswith("@"):
                    block.append(lines[k])
                    k -= 1
                for line in block:
                    m = AVAILABLE.search(line)
                    if m:
                        return m.group(1)
                own = indent(lines[j])   # none here: the enclosing declaration's
                k = j - 1
                while k >= 0 and not (lines[k].strip() and indent(lines[k]) < own and lines[k].rstrip().endswith("{")):
                    k -= 1
                if k < 0 or own == 0:
                    return None
                j = k

        for i, line in enumerate(lines):
            s = ATTRIBUTES.sub("", line.strip())   # @preconcurrency @MainActor public protocol ArrangementViewStyle
            if not s or s.startswith(("#", "//")):
                continue
            for name in SWIFT_DECL.findall(s.split("(")[0]):   # the declaration, not its parameters
                self.swift.setdefault(name, []).append(version(i))

    def read_header(self, text):
        text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
        text = re.sub(r"//[^\n]*", " ", text)
        scope = None
        for chunk in re.split(r";|@end\b|(?=^\s*[-+]\s*\()|(?=@property\b)", text, flags=re.M):
            if re.search(r"@interface\s+\w+", chunk):
                head = chunk[:chunk.index("@interface")]
                m = IOS.search(head)
                scope = m.group(1) if m else None
            self.statements.append((chunk, scope))
            for name in set(re.findall(r"[A-Za-z_]\w*", chunk)):
                self.where.setdefault(name, []).append(len(self.statements) - 1)
            if "@end" in chunk:
                scope = None

    def header_versions(self, name):
        last = name.split(".")[-1]
        found = []
        for index in self.where.get(last, []):
            chunk, scope = self.statements[index]
            n = re.escape(last)
            outside = chunk[chunk.rindex("}"):] if "}" in chunk else chunk   # an enum's cases have names of their own
            swift_names = re.findall(r"NS_SWIFT_NAME\(\s*([\w.]+)", outside)
            declares = (re.search(rf"@(?:interface|protocol)\s+{n}\b(?!\s*\()", chunk)
                        or re.search(rf"typedef\s+NS_\w+\s*\(\s*\w+\s*,\s*{n}\s*\)", chunk)
                        or re.search(rf"typedef\s+\w+\s+{n}\b", chunk)
                        or re.search(rf"getter\s*=\s*{n}\b", chunk)
                        or re.search(rf"@property\s*(?:\([^)]*\))?[^;]*?\b{n}\s*(?:API_|NS_|UI_|__|$)", chunk)
                        or re.search(rf"^\s*[-+]\s*\([^)]*\)\s*{n}\b", chunk, re.M)
                        or re.search(rf"UIKIT_EXTERN\s+(?:const\s+)?\w+\s+(?:const\s+)?{n}\b", chunk))
            if "." in name:   # a Swift-only spelling: UISheetPresentationController.Placement
                declares = name in swift_names
            elif swift_names:   # renamed for Swift: childViewControllerFor… NS_SWIFT_NAME(childFor…), so only that
                declares = any(s.split("(")[0].split(".")[-1] == last for s in swift_names)
            if not declares:
                continue
            tail = chunk[chunk.rindex("}"):] if "}" in chunk else chunk
            m = IOS.search(tail) or (IOS.search(chunk) if "@interface" not in chunk else IOS.search(
                chunk[:chunk.index("@interface")]))
            found.append(m.group(1) if m else scope)
        return found

    def versions(self, name):
        swift = [] if "." in name else self.swift.get(name, [])
        return swift + self.header_versions(name)


_SDK = None


def sdk_or_skip(test):
    global _SDK
    if _SDK is None:
        path = ios_sdk()
        if path is None:
            test.skipTest("no iOS 27.1 SDK (xcrun --sdk iphoneos): the curated versions are checked where there is one")
        _SDK = SDK(path)
    return _SDK


# iOS 27-only names the patterns and references use that are not flagged on their own: an argument or member of a
# curated call (reservedRegions(kind: .division, options: .includeInactive), axisBehavior = .verticalPreferred,
# arrangementViewStyle(.split), setViewProperties(_: ViewProperties…)), whose line is flagged already; a generic
# parameter's name (Arrangement<Primary, Secondary>); `available` from #available, flagged by its version. As bare words
# they would catch an app's own.
NOT_FLAGGED = {"division", "occlusion", "includeInactive", "verticalPreferred", "horizontalOnly", "split", "overlay",
               "ViewProperties", "Primary", "Secondary", "available", "unavailable"}


class CuratedSymbols(unittest.TestCase):
    def test_each_curated_symbol_is_declared_at_its_version_and_no_earlier(self):
        sdk = sdk_or_skip(self)
        wrong = []
        for name, version in sdkguard.SDK_SYMBOLS.items():
            found = sdk.versions(name)
            if name in sdkguard.SHARED:   # an older API of the same name, named in sdkguard.py: that one is known
                older = sdkguard.SHARED[name][0]
                self.assertIn(older, found, f"{name}: SHARED says {older}, the SDK says {found}")
                found = [v for v in found if v != older]
            known = [v for v in found if v is not None]
            if not known:
                wrong.append(f"{name}: not declared in the SDK")
            elif min(known, key=sdkguard.vtuple) != version or None in found:
                wrong.append(f"{name}: listed as {version}, the SDK says {sorted(set(map(str, found)))}")
        self.assertEqual(wrong, [], "fix SDK_SYMBOLS in sdkguard.py (a name older than 27.0 somewhere is too broad)")

    def test_the_patterns_and_references_name_no_ios_27_symbol_left_out(self):
        sdk = sdk_or_skip(self)
        names = set()
        for f in sorted((ROOT / "Sources/Patterns").glob("*.swift")):
            code, _ = sdkguard.lex(f.read_text())
            names |= set(re.findall(r"[A-Za-z_]\w*", code))
        references = ROOT / "skills/foldsmith-duo/references"
        for f in sorted(references.glob("*.md")) + sorted(references.glob("patterns/*.md")):
            for quoted in re.findall(r"`([^`\n]+)`", f.read_text()):   # API names, not prose: camelCase or Capitalised
                names |= {w for w in re.findall(r"[A-Za-z_]\w*", quoted) if re.search(r"[A-Z]", w)}
        curated = set(sdkguard.SDK_SYMBOLS) | {n.split(".")[-1] for n in sdkguard.SDK_SYMBOLS} | set(sdkguard.FOLDSMITH)
        missing = []
        for name in sorted(names - curated - NOT_FLAGGED):
            found = sdk.versions(name)
            if found and None not in found and all(sdkguard.vtuple(v) >= (27,) for v in found):
                missing.append(f"{name} ({', '.join(sorted(set(found)))})")
        self.assertEqual(missing, [], "add these to SDK_SYMBOLS in sdkguard.py, or to NOT_FLAGGED here")

    def test_the_foldsmith_list_is_the_patterns_public_api(self):
        declared = set()
        for f in sorted((ROOT / "Sources/Patterns").glob("*.swift")):
            code, _ = sdkguard.lex(f.read_text())
            declared |= set(re.findall(r"\bpublic\s+(?:struct|enum|class|func)\s+(\w+)", code))
            declared |= set(re.findall(r"@Entry\s+var\s+(\w+)", code))
            for body in re.findall(r"\bpublic\s+extension\b[^{]*\{(.*?)^\s*\}\s*$", code, re.S | re.M):
                declared |= set(re.findall(r"^(?!.*\b(?:private|fileprivate)\b).*?\bfunc\s+(\w+)", body, re.M))
        self.assertEqual(set(sdkguard.FOLDSMITH), declared)


class ReferenceFiles(unittest.TestCase):
    """`swift build` and `swift test` never compile Sources/Patterns (only the catalog's build does, with Xcode 27.1,
    where the guard is true), so nothing else notices a reference file that is not wrapped whole."""

    def test_each_reference_file_sits_whole_inside_the_compiler_guard(self):
        files = sorted((ROOT / "Sources/Patterns").glob("*.swift"))
        self.assertTrue(files)
        for f in files:
            code, _ = sdkguard.lex(f.read_text())
            guarded, directive = sdkguard.guarded_lines(code)
            loose = [n for n, line in enumerate(code.split("\n"), 1) if line.strip() and not directive[n]
                     and not guarded[n]]
            self.assertEqual(loose, [], f"Sources/Patterns/{f.name}: lines outside #if compiler(>=6.4)")


if __name__ == "__main__":
    unittest.main()
