import Testing
import Foundation
import CoreGraphics
@testable import DuoDetectors

// The accessibility adapter against ground truth. The pattern catalog was captured twice: with its own frame records
// (verification/matrices/<pattern>/<config>-<pose>.json, scripts/capture-catalog.sh) and through XCTest's accessibility
// tree in the same poses (verification/accessibility/catalog/<pattern>-<config>-<pose>.json, capture-corpus-flow.sh
// with SNAPSHOT=1). Read through AccessibilitySnapshot, the second must give the detectors the same classes as the
// first, in every pose: that is what lets the detectors judge an app that carries no tracking of its own.
private let repo = URL(fileURLWithPath: #filePath)
    .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()

private func classes(_ elements: [Element], _ pose: Pose) -> Set<String> {
    Set(Detectors.runAll(elements: elements, pose: pose).map(\.classId))
}

@Test func adapterFindsWhatTheCatalogRecordsFind() throws {
    let measured = Dictionary(uniqueKeysWithValues: try Pose.load().map { ($0.name, $0) })
    let dir = repo.appendingPathComponent("verification/accessibility/catalog")
    let files = try FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)
        .filter { $0.pathExtension == "json" }
    #expect(files.count == 119)
    for file in files {
        let pose = try #require(CatalogSnapshot.poseName(of: file))
        let config = file.deletingPathExtension().lastPathComponent.dropLast(pose.count + 1)
        let pattern = config.prefix { $0 != "-" }
        let truthFile = repo.appendingPathComponent("verification/matrices/\(pattern)/\(config.dropFirst(pattern.count + 1))-\(pose).json")
        let truth = try CatalogSnapshot.load(truthFile)
        let snapshot = try AccessibilitySnapshot.load(file)
        let p = try #require(measured[pose])
        #expect(abs(snapshot.windowSize.width - p.window.width) < 1, "\(config) \(pose): window \(snapshot.windowSize)")
        // T10 reads bar items, which the catalog's records do not carry: the catalog has none to find (its sheet's
        // Cancel and Add are symbols), so the adapter must find none either.
        #expect(classes(snapshot.detectorElements, p) == classes(truth.detectorElements, truth.pose(named: pose)),
                "\(config) \(pose)")
    }
}

@Test func acrossPosesOnlyTheTopLevelThreeLevelSplitLosesItsScreenUpright() throws {
    // T7 compares poses, which the catalog's records cannot. SwiftUI shows the detail alone upright, so the top-level
    // three-level config loses the shut phone's collections there (P1, "Three levels"); every other config keeps it,
    // the same three levels on FoldAlignedTiledSplit included.
    let dir = repo.appendingPathComponent("verification/accessibility/catalog")
    var names: [String: [String: Set<String>]] = [:]
    for file in try FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)
    where file.pathExtension == "json" {
        let pose = try #require(CatalogSnapshot.poseName(of: file))
        let config = String(file.deletingPathExtension().lastPathComponent.dropLast(pose.count + 1))
        names[config, default: [:]][pose] = try AccessibilitySnapshot.load(file).screenNames
    }
    var lost: [String: [String]] = [:]
    for (config, poses) in names {
        let found = StateLossOnFold.run(closed: poses["closed"] ?? [], inner: poses).map(\.pose)
        if !found.isEmpty { lost[config] = found }
    }
    #expect(lost == ["split-three": ["flat-upright", "laptop", "tent"]])
}

// The rules on small synthetic trees.
private typealias Node = AccessibilitySnapshot.Node
private func node(_ parent: Int, _ type: String, _ x: Double, _ y: Double, _ w: Double, _ h: Double, id: String? = nil) -> Node {
    Node(parent: parent, type: type, frame: [x, y, w, h], identifier: id, label: nil, enabled: true, selected: false)
}
private func elements(_ nodes: [Node]) -> [Element] {
    AccessibilitySnapshot(bundle: "test", window: [951, 669], nodes: nodes).detectorElements
}

@Test func columnIsTheContentNotTheScrollView() {
    // A split view's detail scrolls under the sidebar: the scroll view spans the window, its text starts past it.
    let columns = elements([
        node(-1, "application", 0, 0, 669, 951), node(0, "window", 0, 0, 951, 669),
        node(1, "scrollView", 0, 0, 951, 669), node(2, "staticText", 511.7, 136, 339.6, 500),
    ]).filter { $0.role == "column" }
    #expect(columns.map(\.frame.minX) == [511.7])
}

@Test func aRowIsMeasuredByWhatItHolds() {
    // IceCubesApp's timeline: the list scrolls under the sidebar, so its cells and their whole-row buttons span the
    // window while the post they draw sits in the detail pane.
    let columns = elements([
        node(-1, "application", 0, 0, 669, 951), node(0, "window", 0, 0, 951, 669), node(1, "collectionView", 0, 0, 951, 669),
        node(2, "cell", 0, 82, 951, 20), node(3, "other", 0, 82, 951, 20),   // a spacer row
        node(2, "cell", 0, 102, 951, 848), node(5, "other", 495.7, 102, 371.3, 848), node(6, "button", 0, 102, 951, 848),
        node(7, "button", 515.7, 114, 40, 40), node(7, "staticText", 563.7, 140, 283.3, 536),
    ]).filter { $0.role == "column" }
    #expect(columns.map(\.frame.minX) == [515.7])
    #expect(columns.map(\.frame.maxX) == [847])
}

@Test func aSettingsRowAcrossTheFoldIsOneColumn() throws {
    // Wikipedia's Settings in book: each row's title sits on the leading half, its value and chevron on the trailing
    // one. Read across, a row is one line, so the list is one column over the fold (T5), not two columns beside it.
    var nodes = [node(-1, "application", 0, 0, 669, 951), node(0, "window", 0, 0, 951, 669), node(1, "collectionView", 0, 0, 951, 669)]
    for y in [82.0, 134, 186] {
        let cell = nodes.count
        nodes += [node(2, "cell", 20, y, 847, 52), node(cell, "image", 41, y + 12, 28, 28),
                  node(cell, "staticText", 85, y + 16, 140, 20), node(cell, "staticText", 780, y + 16, 40, 20),
                  node(cell, "image", 832, y + 18, 14, 16)]
    }
    let found = elements(nodes)
    #expect(found.filter { $0.role == "column" }.map { [$0.frame.minX, $0.frame.maxX] } == [[41, 846]])
    let book = try #require(try Pose.load().first { $0.name == "book" })
    #expect(StretchedSingleColumn().run(elements: found, pose: book).count == 1)
}

@Test func gridColumnsAreSeparatedByGutters() {
    var nodes = [node(-1, "application", 0, 0, 669, 951), node(0, "window", 0, 0, 951, 669), node(1, "scrollView", 0, 0, 951, 669)]
    for x in [16.0, 185.4, 354.8, 524.2, 693.6] { nodes.append(node(2, "staticText", x, 220, 120, 18)) }
    #expect(elements(nodes).filter { $0.role == "column" }.count == 5)
}

@Test func anAvatarStripJoinsItsColumn() {
    let columns = elements([
        node(-1, "application", 0, 0, 669, 951), node(0, "window", 0, 0, 951, 669), node(1, "table", 0, 0, 951, 669),
        node(2, "image", 16, 100, 40, 40), node(2, "staticText", 70, 100, 800, 60),
    ]).filter { $0.role == "column" }
    #expect(columns.count == 1)
    #expect(columns.first?.frame.minX == 16)
}

@Test func thePresentationAfterTheDismissRegionIsASheet() {
    let found = elements([
        node(-1, "application", 0, 0, 669, 951), node(0, "window", 0, 0, 951, 669), node(1, "other", 0, 0, 951, 669),
        node(2, "other", -951, -669, 2853, 2007, id: "PopoverDismissRegion"), node(2, "other", 8, 8, 459.3, 661),
        node(4, "image", -142, -142, 760, 960), node(4, "collectionView", 8, 8, 459.3, 661),
        node(6, "staticText", 24, 82, 427, 40),
    ])
    #expect(found.filter { $0.role == "sheet" }.map(\.frame.minX) == [8])
    #expect(found.filter { $0.role == "image" }.isEmpty)     // the sheet's shadow
    #expect(found.filter { $0.role == "column" }.isEmpty)    // a sheet's form is the sheet, not a column
}

@Test func barItemsAndTheKeyboardAreTheSystems() {
    // The keyboard comes in a window of its own, with its accessory row (Dictate) beside the keys (Home Assistant).
    let found = elements([
        node(-1, "application", 0, 0, 669, 951), node(0, "window", 0, 0, 951, 669),
        node(1, "navigationBar", 0, 24, 951, 58), node(2, "button", 891, 30, 44, 44),
        node(0, "window", 0, 0, 951, 669), node(4, "other", 0, 449, 951, 220),
        node(5, "button", 874, 603, 68, 69, id: "dictation"), node(5, "keyboard", 75, 449, 801, 219),
        node(7, "key", 460, 500, 40, 40),
    ])
    #expect(found.map(\.role) == ["bar", "control"])
    #expect(found.last?.inSystemBar == true)
    #expect(found.last?.inNavigationBar == true)
}

@Test func aWebViewWithOneTextIsAPlaceholder() {
    // NetNewsWire's empty detail: "No selection", alone in a web view, sits on the laptop fold and is not scrolling
    // content; an article in the same web view is.
    let placeholder = elements([
        node(-1, "application", 0, 0, 669, 951), node(0, "window", 0, 0, 669, 951),
        node(1, "webView", 0, 0, 669, 951), node(2, "webView", 0, 0, 669, 951), node(3, "staticText", 269, 444, 117, 25),
    ])
    #expect(placeholder.filter { $0.role == "text" }.map(\.scrolls) == [false])
    let article = elements([
        node(-1, "application", 0, 0, 669, 951), node(0, "window", 0, 0, 669, 951), node(1, "webView", 0, 0, 669, 951),
        node(2, "staticText", 40, 100, 500, 40), node(2, "link", 40, 160, 300, 23), node(2, "staticText", 40, 444, 500, 200),
    ])
    let texts = article.filter { $0.role == "text" }
    #expect(texts.count == 2 && texts.allSatisfy { $0.scrolls })
}

@Test func navigationBarsAreBarsAndNameTheScreen() {
    let snapshot = AccessibilitySnapshot(bundle: "test", window: [951, 669], nodes: [
        node(-1, "application", 0, 0, 669, 951), node(0, "window", 0, 0, 951, 669),
        node(1, "navigationBar", 0, 24, 320, 58, id: "Timeline"), node(1, "navigationBar", 321, 24, 630, 58, id: "Detail"),
    ])
    #expect(snapshot.detectorElements.filter { $0.role == "bar" }.map(\.frame.minX) == [0, 321])
    #expect(snapshot.screenNames == ["Timeline", "Detail"])
}

@Test func toolbarControlsAreToolbarItemsAndWhatLiesOnAMapPans() {
    // Wikipedia's article on the cover: its custom-view toolbar sits in a window-sized toolbar like the vertical bar's
    // items. Places: the pins and cluster counts sit in a layer of their own beside the map node, not inside it; what is
    // small and wholly over the map pans with it and makes no column, the search field over it stays fixed.
    let found = AccessibilitySnapshot(bundle: "test", window: [951, 669], nodes: [
        node(-1, "application", 0, 0, 669, 951), node(0, "window", 0, 0, 951, 669),
        node(1, "toolbar", 0, 0, 951, 669), node(2, "other", 0, 600, 382, 60), node(3, "button", 28, 614, 33, 33, id: "contents"),
        node(1, "other", 0, 0, 951, 669), node(5, "map", 0, 0, 951, 669),
        node(1, "other", 0, 0, 951, 669), node(7, "other", 456, 321, 65, 65, id: "Dallas"), node(8, "button", 480, 345, 17, 17, id: "pin"),
        node(7, "staticText", 462, 290, 32, 32, id: "10"),
        node(1, "searchField", 20, 82, 847, 44, id: "Search"),
    ]).detectorElements
    #expect(found.first { $0.identifier == "contents" }?.inToolbar == true)
    #expect(found.first { $0.identifier == "pin" }?.scrolls == true)
    #expect(found.first { $0.identifier == "10" }?.scrolls == true)
    #expect(found.first { $0.identifier == "Search" }?.scrolls == false)
    #expect(found.first { $0.identifier == "Search" }?.spansWidth == true)
    #expect(found.filter { $0.role == "column" }.isEmpty)
}
