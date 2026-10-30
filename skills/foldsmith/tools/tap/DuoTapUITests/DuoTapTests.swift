import UIKit
import XCTest

/// Taps through an installed app on the shut iPhone Duo, then holds it in the foreground while the host folds the
/// phone and takes the picture. No Xcode window, no agent approval: XCTest drives the cover's touchscreen.
///
/// Driven by environment variables; `xcodebuild` forwards any `TEST_RUNNER_<name>` into the test as `<name>`:
///   DUO_BUNDLE    bundle id of the app under test (required)
///   DUO_TAPS      steps in order, separated by `;` (empty: launch only). A plain step taps the element with that
///                 label or identifier (exact, else a case-insensitive substring of a label), waiting up to 15 s for it
///                 to be enabled and failing if it stays disabled. Prefixed steps:
///                 `type:<text>` types into the focused field (`\\n` in the text presses Return), `springboard:<label>` taps a button of a system
///                 alert if one is up (permission prompts, "Open in …?"), `try:<label>` taps only if the element is
///                 there, `wait:<seconds>` pauses, `cell:<n>` taps the n-th hittable cell from the top (for lists whose
///                 rows change from day to day, such as a feed's newest article).
///   DUO_FLAGS     host directory for the hand-off files (required). The test writes `tapped`, or `failed` with the
///                 reason, then holds the app until `release`. While it holds, the host can ask, by writing a file:
///                   `posed`  dump the app's accessibility tree to `snapshot.json`, answer `snapped`: the frames the
///                            detectors read for an app that carries no tracking of its own (DuoDetectors'
///                            AccessibilitySnapshot), and what the host compares to see the screen survived a fold.
///                            When the app is no longer in front (it crashed or quit on the fold) the snapshot has
///                            no nodes and says so in `appState`, so the detectors report it rather than skip the cell
///                   `again`  relaunch the app and run the steps again, answer `tapped` or `failed`: the host saw the
///                            shut phone lose the screen on the way back from a pose
///                 so one test run serves a screen in every pose. DUO_HOLD is how long it waits for the next request
///                 before it gives up, in seconds (default 120).
///   DUO_ARGS      launch arguments for the app, space-separated (optional)
///   DUO_WAIT      seconds to settle after launch (default 6); DUO_TAP_WAIT after each tap (default 2)
///
/// Simulator processes share the Mac's filesystem, which is what makes the flag files work.
///
/// XCTest's own handling of system alerts is off for the app under test: before every tap it would wait for SpringBoard
/// to settle, and on the Duo simulator SpringBoard can keep an animation running (the status bar's Wi-Fi "searching"),
/// so each tap waited 60 s for nothing (IceCubesApp, 2026-10-28). The steps answer system alerts themselves
/// (`springboard:`). DUO_SYSTEM_ALERTS=1 turns XCTest's handling back on.
final class DuoTapTests: XCTestCase {
    func testTapAndHold() throws {
        let env = ProcessInfo.processInfo.environment
        guard let bundle = env["DUO_BUNDLE"], !bundle.isEmpty,
              let flags = env["DUO_FLAGS"], !flags.isEmpty else {
            throw XCTSkip("set DUO_BUNDLE and DUO_FLAGS")
        }
        let taps = (env["DUO_TAPS"] ?? "").split(separator: ";")
            .map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
        let wait = TimeInterval(env["DUO_WAIT"] ?? "") ?? 6
        let tapWait = TimeInterval(env["DUO_TAP_WAIT"] ?? "") ?? 2
        let hold = TimeInterval(env["DUO_HOLD"] ?? "") ?? 120
        let dir = URL(fileURLWithPath: flags, isDirectory: true)
        func flag(_ name: String, _ text: String = "") {
            try? text.write(to: dir.appendingPathComponent(name), atomically: true, encoding: .utf8)
        }

        continueAfterFailure = false
        let app = XCUIApplication(bundleIdentifier: bundle)
        // XCUIApplication's `doesNotHandleUIInterruptions` (not public API; skipped if a later Xcode drops it).
        if env["DUO_SYSTEM_ALERTS"] != "1", app.responds(to: NSSelectorFromString("setDoesNotHandleUIInterruptions:")) {
            app.setValue(true, forKey: "doesNotHandleUIInterruptions")
        }
        // DUO_ARGS: launch arguments, space-separated (an app's own UI-test switches, e.g. Firefox's FIREFOX_SKIP_INTRO).
        let launchArgs = (env["DUO_ARGS"] ?? "").split(separator: " ").map(String.init)
        if !launchArgs.isEmpty { app.launchArguments = launchArgs }
        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")

        // Launches the app (a running one is relaunched), brings the cover upright and runs the steps; returns why a
        // step could not be done, or nil.
        func launchAndTap() -> String? {
            app.launch()
            Thread.sleep(forTimeInterval: wait)
            // XCTest starts the session with the device turned so that the shut Duo's cover comes up landscape.
            // The flows want the cover upright (a tall window): try the orientations until it is.
            var tried: [String] = []
            func windowIsTall() -> Bool {
                let f = app.windows.firstMatch.frame
                return f.height > f.width
            }
            if !windowIsTall() {
                for (name, o) in [("landscapeLeft", UIDeviceOrientation.landscapeLeft),
                                  ("landscapeRight", .landscapeRight), ("portrait", .portrait),
                                  ("portraitUpsideDown", .portraitUpsideDown)] {
                    XCUIDevice.shared.orientation = o
                    Thread.sleep(forTimeInterval: 2.5)
                    tried.append(name)
                    if windowIsTall() { break }
                }
            }
            // Some apps (Wikipedia) launch landscape on the cover after an upright pose and then ignore every
            // orientation posted. A relaunch after the device has sat upright for a moment comes up tall.
            if !windowIsTall() {
                app.terminate()
                Thread.sleep(forTimeInterval: 3)
                app.launch()
                Thread.sleep(forTimeInterval: wait)
                tried.append("relaunch")
            }
            // What the runner sees, for the log: the hierarchy and the cover as XCTest captures it.
            let f = app.windows.firstMatch.frame
            flag("hierarchy.txt", "window \(Int(f.width))x\(Int(f.height)) after orientations \(tried)\n" + app.debugDescription)
            try? XCUIScreen.main.screenshot().pngRepresentation.write(to: dir.appendingPathComponent("screen.png"))

            for step in taps {
                if step.hasPrefix("type:") {
                    // A literal "\n" in the text presses Return (the step list cannot carry a real newline).
                    app.typeText(String(step.dropFirst(5)).replacingOccurrences(of: "\\n", with: "\n"))
                    Thread.sleep(forTimeInterval: tapWait)
                    continue
                }
                if step.hasPrefix("wait:") {
                    Thread.sleep(forTimeInterval: TimeInterval(step.dropFirst(5)) ?? 1)
                    continue
                }
                if step.hasPrefix("cell:") {
                    let n = max(1, Int(step.dropFirst(5)) ?? 1)
                    _ = app.cells.firstMatch.waitForExistence(timeout: 10)
                    let cells = app.cells.allElementsBoundByIndex.filter(\.isHittable).sorted { $0.frame.minY < $1.frame.minY }
                    guard cells.count >= n else { return "only \(cells.count) hittable cells, no cell \(n)" }
                    cells[n - 1].tap()
                    Thread.sleep(forTimeInterval: tapWait)
                    continue
                }
                if step.hasPrefix("springboard:") {
                    // Permission prompts and "Open in …?" are optional by nature: tap if one is up, else move on.
                    let label = String(step.dropFirst(12))
                    // Exact label first, then a label that begins with it ("Don" for "Don’t Allow"), then contains it.
                    let candidates = [
                        springboard.alerts.buttons[label].firstMatch,
                        springboard.alerts.buttons.matching(NSPredicate(format: "label BEGINSWITH[c] %@", label)).firstMatch,
                        springboard.alerts.buttons.matching(NSPredicate(format: "label CONTAINS[c] %@", label)).firstMatch,
                    ]
                    if candidates[0].waitForExistence(timeout: 4) {
                        candidates[0].tap(); Thread.sleep(forTimeInterval: tapWait)
                    } else if let b = candidates.dropFirst().first(where: { $0.exists }) {
                        b.tap(); Thread.sleep(forTimeInterval: tapWait)
                    }
                    continue
                }
                let optional = step.hasPrefix("try:")
                let label = optional ? String(step.dropFirst(4)) : step
                if optional {
                    let exact = NSPredicate(format: "label == %@ OR identifier == %@", label, label)
                    let element = app.descendants(matching: .any).matching(exact).firstMatch
                    if element.waitForExistence(timeout: 3), element.isHittable {
                        element.tap()
                        Thread.sleep(forTimeInterval: tapWait)
                    }
                    continue
                }
                let exact = NSPredicate(format: "label == %@ OR identifier == %@", label, label)
                var element = app.descendants(matching: .any).matching(exact).firstMatch
                if !element.waitForExistence(timeout: 10) {
                    // Same fallback as xcode_device.py tap: a case-insensitive substring of the label.
                    let loose = NSPredicate(format: "label CONTAINS[c] %@", label)
                    element = app.descendants(matching: .any).matching(loose).firstMatch
                    guard element.waitForExistence(timeout: 5) else { return "no element labelled '\(label)'" }
                }
                guard element.isHittable else { return "'\(label)' exists but is not hittable" }
                // A disabled button takes the tap and does nothing, and the capture then shows the screen before it
                // (Wikipedia's Table of Contents until the article has loaded): wait for it, and fail if it never is.
                if !element.isEnabled {
                    let enabled = XCTNSPredicateExpectation(predicate: NSPredicate(format: "isEnabled == true"), object: element)
                    guard XCTWaiter().wait(for: [enabled], timeout: 15) == .completed else {
                        return "'\(label)' stayed disabled for 15 s"
                    }
                }
                element.tap()
                Thread.sleep(forTimeInterval: tapWait)
            }

            // The screen the picture will show, as XCTest sees it on the cover: frames for the detectors later.
            flag("hierarchy-after.txt", app.debugDescription)
            return nil
        }

        if let failure = launchAndTap() {
            flag("failed", failure)
            XCTFail(failure)
            return
        }
        flag("tapped", taps.joined(separator: ";"))
        func path(_ name: String) -> String { dir.appendingPathComponent(name).path }
        // Each request from the host starts the wait again; `release` ends it.
        var deadline = Date().addingTimeInterval(hold)
        while !FileManager.default.fileExists(atPath: path("release")), Date() < deadline {
            if FileManager.default.fileExists(atPath: path("posed")) {
                try? FileManager.default.removeItem(atPath: path("posed"))
                do {
                    let data = try AccessibilityDump(app: app, bundle: bundle).jsonOrNotInFront()
                    try data.write(to: dir.appendingPathComponent("snapshot.json"))
                    flag("snapped")
                } catch {
                    flag("snapped", "snapshot failed: \(error)")
                }
                deadline = Date().addingTimeInterval(hold)
            }
            if FileManager.default.fileExists(atPath: path("again")) {
                try? FileManager.default.removeItem(atPath: path("again"))
                if let failure = launchAndTap() {
                    flag("failed", failure)
                } else {
                    flag("tapped", taps.joined(separator: ";"))
                }
                deadline = Date().addingTimeInterval(hold)
            }
            Thread.sleep(forTimeInterval: 0.5)
        }
    }
}

/// The app's accessibility tree, flattened in document order with parent links, as XCTest sees it in the current
/// pose. Frames are in the app's coordinate space (the window, for a full-screen app), in points.
///
/// Whatever scrolls is third-party content in most corpus apps (posts, names, articles; a timeline's rows are often
/// buttons), so no label inside scrolling content is kept: the detectors need the frame and the kind of element, not
/// the words.
struct AccessibilityDump {
    let app: XCUIApplication
    let bundle: String

    struct Node: Encodable {
        var parent: Int
        var type: String
        var frame: [Double]
        var identifier: String?
        var label: String?
        var enabled: Bool
        var selected: Bool
    }

    struct Dump: Encodable {
        var bundle: String
        var window: [Double]
        var nodes: [Node]
        /// Only when the app is not in front: notRunning, runningBackground, runningBackgroundSuspended, lostConnection
        /// or unknown.
        var appState: String?
    }

    /// The tree, or, when the app is no longer on screen (it crashed or quit on the fold), a snapshot with no window
    /// and no nodes that says why. The app can go between the state check and the snapshot: XCTest then reports
    /// "Lost connection to the application" (10009) while `state` may still read foreground for a moment.
    func jsonOrNotInFront() throws -> Data {
        if app.state == .runningForeground {
            do { return try json() } catch {
                Thread.sleep(forTimeInterval: 1)
                guard app.state != .runningForeground || (error as NSError).code == 10009 else { throw error }
            }
        }
        let name = switch app.state {
        case .notRunning: "notRunning"
        case .runningBackground: "runningBackground"
        case .runningBackgroundSuspended: "runningBackgroundSuspended"
        case .runningForeground: "lostConnection"
        default: "unknown"
        }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(Dump(bundle: bundle, window: [0, 0], nodes: [], appState: name))
    }

    static let scrollingTypes: Set<XCUIElement.ElementType> = [.scrollView, .table, .collectionView, .webView, .textView]

    func json() throws -> Data {
        let root = try app.snapshot()
        var nodes: [Node] = []
        func visit(_ s: XCUIElementSnapshot, parent: Int, inScroll: Bool) {
            let f = s.frame
            func clip(_ t: String) -> String? { t.isEmpty ? nil : String(t.prefix(80)) }
            nodes.append(Node(parent: parent, type: Self.name(s.elementType),
                              frame: [f.minX, f.minY, f.width, f.height].map { Double($0) },
                              identifier: clip(s.identifier), label: inScroll ? nil : clip(s.label),
                              enabled: s.isEnabled, selected: s.isSelected))
            let me = nodes.count - 1
            let scrolls = inScroll || Self.scrollingTypes.contains(s.elementType)
            for c in s.children { visit(c, parent: me, inScroll: scrolls) }
        }
        visit(root, parent: -1, inScroll: false)
        let w = app.windows.firstMatch.frame
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(Dump(bundle: bundle, window: [Double(w.width), Double(w.height)], nodes: nodes))
    }

    static func name(_ t: XCUIElement.ElementType) -> String {
        switch t {
        case .application: return "application"
        case .window: return "window"
        case .other: return "other"
        case .group: return "group"
        case .button: return "button"
        case .link: return "link"
        case .staticText: return "staticText"
        case .textField: return "textField"
        case .secureTextField: return "secureTextField"
        case .searchField: return "searchField"
        case .textView: return "textView"
        case .image: return "image"
        case .icon: return "icon"
        case .cell: return "cell"
        case .table: return "table"
        case .collectionView: return "collectionView"
        case .scrollView: return "scrollView"
        case .webView: return "webView"
        case .map: return "map"
        case .navigationBar: return "navigationBar"
        case .toolbar: return "toolbar"
        case .tabBar: return "tabBar"
        case .tab: return "tab"
        case .statusBar: return "statusBar"
        case .switch: return "switch"
        case .toggle: return "toggle"
        case .slider: return "slider"
        case .stepper: return "stepper"
        case .segmentedControl: return "segmentedControl"
        case .picker: return "picker"
        case .pickerWheel: return "pickerWheel"
        case .datePicker: return "datePicker"
        case .menu: return "menu"
        case .menuItem: return "menuItem"
        case .menuButton: return "menuButton"
        case .popUpButton: return "popUpButton"
        case .pageIndicator: return "pageIndicator"
        case .progressIndicator: return "progressIndicator"
        case .activityIndicator: return "activityIndicator"
        case .keyboard: return "keyboard"
        case .key: return "key"
        case .alert: return "alert"
        case .sheet: return "sheet"
        case .popover: return "popover"
        case .scrollBar: return "scrollBar"
        default: return "type\(t.rawValue)"
        }
    }
}
