#!/usr/bin/env python3
"""routes.sh: the route inventory a structural change lists first. Skipped where rg (ripgrep) is not installed, outside
Claude Code (whose own rg stands in for it).

    python3 -m unittest discover -s scripts -p 'test_*.py'
"""
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
ROUTES = HERE / "routes.sh"
RG = shutil.which("rg")
CLAUDE = os.environ.get("CLAUDE_CODE_EXECPATH", "")
HAS_RG = bool(RG) or os.access(CLAUDE, os.X_OK)

COORDINATOR = """\
import UIKit

final class RandomCoordinator {
    let navigationController: UINavigationController
    func start() {
        var viewControllers = navigationController.viewControllers
        navigationController.setViewControllers(viewControllers, animated: true)
        navigationController.pushViewController(ArticleViewController(), animated: true)
        navigationController.popToRootViewController(animated: false)
        // navigationController.pushViewController(commented, animated: true)
        navigationController.present(sheet, animated: true)
        show(ArticleViewController(), sender: self)
        Toast.shared.show(message)
        ctx.saveGState(); ctx.restoreGState()
    }
}
"""

APP = """\
import UIKit
import UserNotifications

final class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    func scene(_ scene: UIScene, continue userActivity: NSUserActivity) {}
    func scene(_ scene: UIScene, openURLContexts URLContexts: Set<UIOpenURLContext>) {}
    func windowScene(_ windowScene: UIWindowScene, performActionFor shortcutItem: UIApplicationShortcutItem) {}
    func stateRestorationActivity(for scene: UIScene) -> NSUserActivity? { nil }
    func restoreNavigationState(in tabs: UITabBarController) {
        if let nav = tabs.selectedViewController as? UINavigationController, nav.viewControllers.count > 1 || flag {}
    }
    func route(_ url: URL) -> Bool { true }
}

extension AppDelegate: UNUserNotificationCenterDelegate {
    func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse) {}
}
"""

VIEW = """\
import SwiftUI

struct LibraryView: View {
    @State private var path = NavigationPath()
    var body: some View {
        NavigationStack(path: $path) {
            List { NavigationLink("Saved", value: 1) }
                .navigationDestination(for: Int.self) { _ in Text("Saved") }
                .sheet(isPresented: $adding) { AddView() }
        }
        .onOpenURL { url in open(url) }
    }
    func pick(_ item: Int) { path.append(item) }
    func back() { path.removeLast() }
    func home() {
        path = []
        router.navigate(to: .settings)
        var buffer = [CChar](repeating: 0, count: 8); items.append(1)
    }
}
"""


def line_of(text, needle):
    return next(i for i, line in enumerate(text.splitlines(), 1) if needle in line)


@unittest.skipUnless(HAS_RG, "rg (ripgrep) is not installed, and this is not Claude Code")
class Routes(unittest.TestCase):
    def setUp(self):
        self.app = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.app)
        self.write("App/RandomCoordinator.swift", COORDINATOR)
        self.write("App/SceneDelegate.swift", APP)
        self.write("App/LibraryView.swift", VIEW)
        # Left out: tests, build folders, other languages.
        self.write("AppTests/RandomCoordinatorTests.swift", "nav.pushViewController(vc, animated: true)\n")
        self.write("App/RandomCoordinatorTests.swift", "nav.pushViewController(vc, animated: true)\n")
        self.write("build/Generated.swift", "nav.pushViewController(vc, animated: true)\n")
        self.write(".build/checkouts/Dep.swift", "nav.pushViewController(vc, animated: true)\n")
        self.write("App/Legacy.m", "[self.navigationController pushViewController:vc animated:YES];\n")

    def write(self, rel, text):
        path = self.app / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run_routes(self, *names, folder=None):
        return subprocess.run(["bash", str(ROUTES), str(folder or self.app), *names],
                              capture_output=True, text=True, encoding="utf-8")

    def table(self, *names):
        r = self.run_routes(*names)
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = {}
        for line in r.stdout.splitlines():
            if line.startswith("| ") and not line.startswith("| file:line"):
                cells = [c.strip() for c in line.strip("|").split(" | ")]
                rows[cells[0]] = (cells[1], cells[2])
        return r.stdout, rows

    def kind(self, rows, rel, text, needle):
        key = f"{rel}:{line_of(text, needle)}"
        self.assertIn(key, rows, f"{key} missing from the table")
        return rows[key][0]

    def test_every_kind(self):
        out, rows = self.table()
        self.assertTrue(out.startswith("| file:line | kind | code |\n|---|---|---|\n"), out)
        c, a, v = "App/RandomCoordinator.swift", "App/SceneDelegate.swift", "App/LibraryView.swift"
        for rel, text, needle, kind in [
            (c, COORDINATOR, "var viewControllers = navigationController.viewControllers", "walk"),
            (c, COORDINATOR, "setViewControllers(", "set"),
            (c, COORDINATOR, "pushViewController(ArticleViewController()", "push"),
            (c, COORDINATOR, "popToRootViewController", "pop"),
            (c, COORDINATOR, "present(sheet", "present"),
            (c, COORDINATOR, "show(ArticleViewController(), sender: self)", "push"),
            (a, APP, "continue userActivity", "restore"),
            (a, APP, "openURLContexts", "url"),
            (a, APP, "performActionFor", "shortcut"),
            (a, APP, "stateRestorationActivity", "restore"),
            (a, APP, "func restoreNavigationState", "restore"),
            (a, APP, "selectedViewController as? UINavigationController", "walk"),
            (a, APP, "func route(_ url: URL)", "url"),
            (a, APP, "UNUserNotificationCenterDelegate {", "notification"),
            (a, APP, "didReceive response", "notification"),
            (v, VIEW, "NavigationPath()", "swiftui"),
            (v, VIEW, "NavigationStack(path:", "swiftui"),
            (v, VIEW, "NavigationLink(", "swiftui"),
            (v, VIEW, ".navigationDestination(", "swiftui"),
            (v, VIEW, ".sheet(", "present"),
            (v, VIEW, ".onOpenURL", "url"),
            (v, VIEW, "path.append(item)", "push"),
            (v, VIEW, "path.removeLast()", "pop"),
            (v, VIEW, "path = []", "set"),
            (v, VIEW, "router.navigate(to:", "push"),
        ]:
            self.assertEqual(self.kind(rows, rel, text, needle), kind, f"{rel}: {needle}")
        # One row per line, paths relative to the app folder, in file and line order.
        keys = list(rows)
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(keys, sorted(keys, key=lambda k: (k.rsplit(":", 1)[0], int(k.rsplit(":", 1)[1]))))
        self.assertFalse(any(k.startswith(("/", "./")) for k in keys), keys)
        # The count by kind adds up.
        summary = out.strip().splitlines()[-1]
        counts = "set 2 · push 4 · pop 2 · present 2 · swiftui 4"
        self.assertTrue(summary.startswith(f"{len(rows)} lines: {counts}"), summary)
        self.assertNotIn("[CChar]", out)   # a path declared, an array appended to: not navigation

    def test_left_out(self):
        out, rows = self.table()
        for rel in ("AppTests/", "App/RandomCoordinatorTests.swift", "build/", ".build/", "App/Legacy.m"):
            self.assertFalse(any(k.startswith(rel) for k in rows), f"{rel} should be left out:\n{out}")
        self.assertNotIn("commented", out)            # a comment line
        self.assertNotIn("Toast.shared.show", out)    # show( without sender: is not UIKit's
        self.assertNotIn("GState", out)               # Core Graphics, not state restoration

    def test_pipe_escaped(self):
        out, rows = self.table()
        row = next(line for line in out.splitlines() if "nav.viewControllers.count" in line)
        self.assertIn("count > 1 \\|\\| flag", row)
        self.assertEqual(row.count(" | "), 2, row)  # three cells, none split by the code's ||

    def test_names(self):
        self.write("App/Router.swift", "func go() {\n    RandomCoordinator(navigationController: nav).start()\n"
                                       "    nav.popViewController(animated: true)\n}\n")
        out, rows = self.table("RandomCoordinator")
        files = {k.rsplit(":", 1)[0] for k in rows}
        self.assertEqual(files, {"App/RandomCoordinator.swift", "App/Router.swift"}, out)
        out, rows = self.table("SceneDelegate.swift")   # a file name
        self.assertEqual({k.rsplit(":", 1)[0] for k in rows}, {"App/SceneDelegate.swift"}, out)
        out, rows = self.table("LibraryView", "Router")  # several
        self.assertEqual({k.rsplit(":", 1)[0] for k in rows}, {"App/LibraryView.swift", "App/Router.swift"}, out)

    def test_nothing_found(self):
        empty = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, empty)
        (empty / "Model.swift").write_text("struct Model { let id: Int }\n", encoding="utf-8")
        r = self.run_routes(folder=empty)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "no routes found"))
        r = self.run_routes("NoSuchType")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.startswith("no routes found"), r.stdout)

    def test_never_reads_stdin(self):
        # rg searches its standard input when given no path and stdin is a pipe: an agent's shell often is one.
        read, write = os.pipe()
        self.addCleanup(os.close, write)
        try:
            r = subprocess.run(["bash", str(ROUTES), str(self.app), "RandomCoordinator"], stdin=read,
                               capture_output=True, text=True, encoding="utf-8", timeout=60)
        finally:
            os.close(read)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("App/RandomCoordinator.swift:", r.stdout)

    def test_claude_codes_rg_stands_in_where_none_is_installed(self):
        # In Claude Code rg is a shell function, which a script cannot call; the script runs the binary as rg itself
        bare = "/usr/bin:/bin"
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_EXECPATH"}
        env["PATH"] = bare
        if not shutil.which("rg", path=bare):
            r = subprocess.run(["bash", str(ROUTES), str(self.app)], capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 2)
            self.assertIn("needs rg (ripgrep)", r.stderr)
        stand_in = CLAUDE
        if RG:   # a stand-in for Claude Code's binary that runs the real rg
            stand_in = str(self.app / "claude")
            pathlib.Path(stand_in).write_text(f'#!/bin/bash\nexec "{RG}" "$@"\n', encoding="utf-8")
            os.chmod(stand_in, 0o755)
        r = subprocess.run(["bash", str(ROUTES), str(self.app)], capture_output=True, text=True, encoding="utf-8",
                           env=dict(env, CLAUDE_CODE_EXECPATH=stand_in))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("| App/RandomCoordinator.swift:", r.stdout)

    def test_wrong_call(self):
        self.assertEqual(subprocess.run(["bash", str(ROUTES)], capture_output=True).returncode, 2)
        r = self.run_routes(folder=self.app / "missing")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no folder", r.stderr)


if __name__ == "__main__":
    unittest.main()
