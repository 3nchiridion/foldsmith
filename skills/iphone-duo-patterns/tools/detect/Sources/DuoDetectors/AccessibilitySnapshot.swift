import Foundation
import CoreGraphics

/// What Tap/DuoTapUITests writes to snapshot.json once the host has the phone in the pose (scripts/capture-corpus-flow.sh
/// with SNAPSHOT=1): the app's accessibility tree as XCTest sees it, flattened in document order with parent links,
/// frames in window points. It is the detectors' input for an app that carries no tracking of its own, such as a corpus
/// app before and after a migration. The pose comes from poses.json, by the name in the file (`<screen>-<pose>.json`).
///
/// The tree says what an element is and where, not how the app meant it, so the mapping to `Element` is a set of rules,
/// checked against the catalog's own frame records (Tests/DuoPoseTestingTests/AccessibilityTests.swift):
/// - Leaves: text (staticText), image (image, icon), control (buttons, links, fields, switches, sliders and the like,
///   interactive). Under a scrolling container they scroll (T1 skips them); under a navigation bar, toolbar or tab bar
///   with no scrolling container in between they belong to the system's bar (T2 and T4 skip them). SwiftUI hosts a
///   whole column inside a window-sized toolbar, so a scrolling container under a bar is content, and so is all it holds.
///   A scrolling container that holds one short item of content or none is a placeholder ("No selection" in an empty
///   detail, a web view inside a pager), not scrolling content: T1 applies to it.
///   The keyboard is the system's: it comes in windows of its own (the input view, the keys and their accessory row
///   with Dictate), and every window holding a keyboard or an input view is left out. The keyboard and the status bar are the system's and are left
///   out, and so is an image that reaches outside the element holding it (a sheet's shadow, a backdrop).
/// - Bars: every navigation bar outside a sheet, as an element of role `bar`; a button under one, with no scrolling
///   container in between, is `inNavigationBar` (T10 reads it; a title menu, IceCubesApp's "Trending", is a pop-up
///   button and the bar's title, which stays horizontal). T14 reads the bars of a split view's panes. A control whose
///   nearest bar is a toolbar, with no scrolling container in between, is `inToolbar` (T10 reads that too).
/// - Maps: a map pans, and so does what lies on it: the map's own place names (its descendants) and the pins, cluster
///   counts and labels an app draws in a layer of its own over the map (Wikipedia's Places: 65 × 65 pt annotations with a
///   17 × 17 pt button, outside the map node). Anything under 100 × 100 pt lying wholly over a map, outside the bars, is
///   map content: scrolling for T1 and T7, never a column. A search field or a panel over the map is larger and stays
///   fixed (Places' search field across the fold is T1).
///   `screenNames` names what stays on screen (the bars, and the controls outside scrolling content): what T7
///   compares across poses.
/// - Sheets: the element after a `PopoverDismissRegion` (the dimming that dismisses a presentation) is the presented
///   sheet, unless it fills the window. While one is up XCTest leaves what is under it out of the tree.
/// - Columns: content inside a scrolling container that is not itself inside one or inside a sheet. The horizontal
///   extents of its visible content (text, images, controls, cells) are merged where they touch; each run separated
///   from the next by a gutter is a column if it holds text or cells, and a run of images or controls alone (an avatar
///   strip) joins its nearest column. One column per distinct extent.
///   The column is the content's extent, not the scroll view's: a split view's detail scrolls under the sidebar, so its
///   scroll view spans the window while its text starts past the sidebar. For the same reason a cell or a control that
///   holds content is measured by what it holds: a list's rows and whole-row buttons there span the window too
///   (IceCubesApp's timeline beside its sidebar), and a cell that holds none (a spacer row) counts only where a list
///   exposes nothing else. What one row holds is one run, from its first content to its last: a settings row's title
///   and its value are one line read across, not two columns, so a row that sets them on either side of the fold is
///   one column across it (Wikipedia's Settings in book, T5).
public struct AccessibilitySnapshot: Codable, Sendable {
    public struct Node: Codable, Sendable {
        public var parent: Int
        public var type: String
        public var frame: [Double]
        public var identifier: String?
        public var label: String?
        public var enabled: Bool
        public var selected: Bool

        var rect: CGRect { CGRect(x: frame[0], y: frame[1], width: frame[2], height: frame[3]) }
    }

    public var bundle: String
    public var window: [Double]
    public var nodes: [Node]
    /// Set only when the app was not in front when the snapshot was asked for (it crashed or quit on the way to the
    /// pose): `notRunning`, `runningBackground`, `runningBackgroundSuspended`, `lostConnection` or `unknown`. Such a
    /// snapshot has no nodes.
    public var appState: String?

    public static func load(_ url: URL) throws -> AccessibilitySnapshot {
        try JSONDecoder().decode(AccessibilitySnapshot.self, from: Data(contentsOf: url))
    }

    /// Whether a JSON file is one of these (it has `nodes`) rather than a catalog record.
    public static func matches(_ data: Data) -> Bool {
        (try? JSONSerialization.jsonObject(with: data) as? [String: Any])?["nodes"] != nil
    }

    static let scrolling: Set<String> = ["scrollView", "table", "collectionView", "webView", "textView"]
    /// Content that pans rather than scrolls: it moves under the fold like scrolling content, but makes no column.
    static let panning: Set<String> = ["map"]
    /// The largest thing that counts as lying on a map (a pin, a cluster count, a label) rather than over it.
    static let mapItemSize: Double = 100
    static let bars: Set<String> = ["navigationBar", "toolbar", "tabBar"]
    static let system: Set<String> = ["keyboard", "statusBar"]
    static let controls: Set<String> = [
        "button", "link", "textField", "secureTextField", "searchField", "switch", "toggle", "slider", "stepper",
        "segmentedControl", "picker", "datePicker", "menuButton", "popUpButton", "tab", "pageIndicator",
    ]
    static let texts: Set<String> = ["staticText", "textView"]
    static let images: Set<String> = ["image", "icon"]
    /// What a column's extent is measured from; text and cells make a run a column.
    static let content: Set<String> = controls.union(texts).union(images).union(["cell"])
    static let columnMakers: Set<String> = texts.union(["cell", "link"])

    public var windowSize: CGSize { CGSize(width: window[0], height: window[1]) }

    /// Scrolling containers that hold one item of content or none, a short one (under a quarter of the container's
    /// height): a placeholder, not scrolling content. A long article held as one text still scrolls.
    func placeholderWebViews(children: [[Int]]) -> Set<Int> {
        var count = [Int](repeating: 0, count: nodes.count)
        var tallest = [Double](repeating: 0, count: nodes.count)
        for (i, n) in nodes.enumerated().reversed() {
            count[i] += children[i].reduce(0) { $0 + count[$1] } + (Self.content.contains(n.type) ? 1 : 0)
            tallest[i] = max(children[i].map { tallest[$0] }.max() ?? 0, Self.content.contains(n.type) ? n.frame[3] : 0)
        }
        return Set(nodes.indices.filter {
            Self.scrolling.contains(nodes[$0].type) && nodes[$0].type != "textView" && count[$0] <= 1
                && tallest[$0] < nodes[$0].frame[3] / 4
        })
    }

    /// What stays on screen, by identifier or label: the navigation bars, and the controls outside scrolling content
    /// (back buttons aside, every screen has one). The screen the person is on, for T7; a bar's name alone can stay
    /// the root's on the cover (NetNewsWire's article reads "Feeds").
    public var screenNames: Set<String> {
        Set(detectorElements.compactMap { e -> String? in
            if e.role == "bar" { return e.identifier ?? e.label }
            guard e.isInteractive, !e.scrolls, e.identifier != "BackButton" else { return nil }
            return e.label ?? e.identifier
        })
    }

    public var detectorElements: [Element] {
        let bounds = CGRect(origin: .zero, size: windowSize)
        var children = [[Int]](repeating: [], count: nodes.count)
        for (i, n) in nodes.enumerated() where n.parent >= 0 { children[n.parent].append(i) }

        // Ancestry facts, top-down (parents come before their children in document order).
        var skipped = [Bool](repeating: false, count: nodes.count)
        var scrolls = skipped, inBar = skipped, inSheet = skipped, inControl = skipped, inNavigationBar = skipped
        var inToolbar = skipped, pans = skipped
        let maps = nodes.filter { Self.panning.contains($0.type) }.map(\.rect)
        func liesOnMap(_ r: CGRect) -> Bool {
            r.width <= Self.mapItemSize && r.height <= Self.mapItemSize
                && maps.contains { $0.insetBy(dx: -Detectors.tolerance, dy: -Detectors.tolerance).contains(r) }
        }
        let placeholder = placeholderWebViews(children: children)
        func scrollsHere(_ i: Int) -> Bool { Self.scrolling.contains(nodes[i].type) && !placeholder.contains(i) }
        var scrollRoot = [Int?](repeating: nil, count: nodes.count)
        var sheets: Set<Int> = []
        for (i, n) in nodes.enumerated() {
            if n.identifier == "PopoverDismissRegion", n.parent >= 0,
               let next = children[n.parent].first(where: { $0 > i }),
               nodes[next].rect.width < bounds.width - Detectors.tolerance {
                sheets.insert(next)
            }
        }
        var systemWindows: Set<Int> = []
        for (i, n) in nodes.enumerated() where n.type == "keyboard" || n.identifier == "inputView" {
            var w = i
            while w >= 0, nodes[w].type != "window" { w = nodes[w].parent }
            if w >= 0 { systemWindows.insert(w) }
        }
        for (i, n) in nodes.enumerated() {
            let p = n.parent
            if systemWindows.contains(i) { skipped[i] = true }
            if p >= 0 {
                skipped[i] = skipped[i] || skipped[p]
                pans[i] = pans[p] || Self.panning.contains(nodes[p].type)
                inBar[i] = !Self.scrolling.contains(nodes[p].type) && (inBar[p] || Self.bars.contains(nodes[p].type))
                inNavigationBar[i] = !Self.scrolling.contains(nodes[p].type)
                    && (nodes[p].type == "navigationBar" || (inNavigationBar[p] && !Self.bars.contains(nodes[p].type)))
                inToolbar[i] = !Self.scrolling.contains(nodes[p].type)
                    && (nodes[p].type == "toolbar" || (inToolbar[p] && !Self.bars.contains(nodes[p].type)))
                inSheet[i] = inSheet[p] || sheets.contains(p)
                pans[i] = pans[i] || (!inBar[i] && !inSheet[i] && !Self.panning.contains(n.type) && liesOnMap(n.rect))
                scrolls[i] = scrolls[p] || scrollsHere(p) || pans[i]
                inControl[i] = inControl[p] || Self.controls.contains(nodes[p].type)
                scrollRoot[i] = scrollRoot[p] ?? (scrollsHere(p) && !inSheet[i] ? p : nil)
            }
            if Self.system.contains(n.type) || n.identifier == "PopoverDismissRegion" { skipped[i] = true }
            if Self.images.contains(n.type), p >= 0,
               !nodes[p].rect.insetBy(dx: -Detectors.tolerance, dy: -Detectors.tolerance).contains(n.rect) {
                skipped[i] = true
            }
        }

        func visible(_ r: CGRect, in clip: CGRect) -> Bool { r.width > 1 && r.height > 1 && r.intersects(clip) }

        var elements: [Element] = []
        for (i, n) in nodes.enumerated() where !skipped[i] && visible(n.rect, in: bounds) {
            let role: String? = Self.texts.contains(n.type) ? "text"
                : Self.images.contains(n.type) ? "image"
                : Self.controls.contains(n.type) ? "control" : nil
            // A control's own image and title are the control, not separate content.
            if let role, !inControl[i], children[i].isEmpty || role == "control" || n.type == "textView" {
                elements.append(Element(identifier: n.identifier, label: n.label, role: role, frame: n.rect,
                                        isInteractive: role == "control", scrolls: scrolls[i] || n.type == "textView",
                                        inSystemBar: inBar[i], inNavigationBar: inNavigationBar[i] && n.type == "button",
                                        inToolbar: inToolbar[i] && role == "control",
                                        spansWidth: n.type == "searchField" || n.type == "segmentedControl"))
            }
            if n.type == "navigationBar", !inSheet[i], !sheets.contains(i) {
                elements.append(Element(identifier: n.identifier, label: n.label, role: "bar", frame: n.rect))
            }
            if sheets.contains(i) {
                elements.append(Element(identifier: "sheet", label: n.label, role: "sheet", frame: n.rect))
            }
        }

        // Columns, per top-level scrolling container outside any sheet.
        var holdsContent = [Bool](repeating: false, count: nodes.count)
        for (i, n) in nodes.enumerated().reversed() where n.parent >= 0 && (holdsContent[i] || Self.content.contains(n.type)) {
            holdsContent[n.parent] = true
        }
        var runsByRoot: [Int: [(minX: CGFloat, maxX: CGFloat, makesColumn: Bool)]] = [:]
        var emptyCellsByRoot = runsByRoot
        // The row each node sits in: its nearest cell that holds content.
        var row = [Int?](repeating: nil, count: nodes.count)
        for (i, n) in nodes.enumerated() where n.parent >= 0 {
            row[i] = nodes[n.parent].type == "cell" && holdsContent[n.parent] ? n.parent : row[n.parent]
        }
        var rowRuns: [Int: (root: Int, minX: CGFloat, maxX: CGFloat, makesColumn: Bool)] = [:]
        for (i, n) in nodes.enumerated() where !skipped[i] && Self.content.contains(n.type) {
            if holdsContent[i], n.type == "cell" || Self.controls.contains(n.type) { continue }
            guard let root = scrollRoot[i] else { continue }
            let clip = nodes[root].rect.intersection(bounds)
            let r = n.rect.intersection(clip)
            guard !r.isNull, visible(r, in: clip) else { continue }
            let makes = Self.columnMakers.contains(n.type)
            if n.type == "cell" && !children[i].isEmpty {
                emptyCellsByRoot[root, default: []].append((r.minX, r.maxX, true))
            } else if let cell = row[i] {
                let run = rowRuns[cell] ?? (root, r.minX, r.maxX, makes)
                rowRuns[cell] = (root, min(run.minX, r.minX), max(run.maxX, r.maxX), run.makesColumn || makes)
            } else {
                runsByRoot[root, default: []].append((r.minX, r.maxX, makes))
            }
        }
        for run in rowRuns.values {
            runsByRoot[run.root, default: []].append((run.minX, run.maxX, run.makesColumn))
        }
        for (root, cells) in emptyCellsByRoot where runsByRoot[root] == nil { runsByRoot[root] = cells }
        var extents: [(CGFloat, CGFloat)] = []
        for root in runsByRoot.keys.sorted() {
            let clip = nodes[root].rect.intersection(bounds)
            var runs: [(minX: CGFloat, maxX: CGFloat, makesColumn: Bool)] = []
            for s in runsByRoot[root]!.sorted(by: { $0.minX < $1.minX }) {
                if let last = runs.last, s.minX <= last.maxX + Detectors.tolerance {
                    runs[runs.count - 1] = (last.minX, max(last.maxX, s.maxX), last.makesColumn || s.makesColumn)
                } else {
                    runs.append(s)
                }
            }
            var columns = runs.filter(\.makesColumn).map { ($0.minX, $0.maxX) }
            if columns.isEmpty { columns = runs.isEmpty ? [] : [(runs.map(\.minX).min()!, runs.map(\.maxX).max()!)] }
            for run in runs where !run.makesColumn && !columns.isEmpty {
                let mid = (run.minX + run.maxX) / 2
                let j = columns.indices.min { abs((columns[$0].0 + columns[$0].1) / 2 - mid) < abs((columns[$1].0 + columns[$1].1) / 2 - mid) }!
                columns[j] = (min(columns[j].0, run.minX), max(columns[j].1, run.maxX))
            }
            for (minX, maxX) in columns where !extents.contains(where: { abs($0.0 - minX) < 1 && abs($0.1 - maxX) < 1 }) {
                extents.append((minX, maxX))
                elements.append(Element(identifier: "column-\(extents.count - 1)", role: "column",
                                        frame: CGRect(x: minX, y: clip.minY, width: maxX - minX, height: clip.height),
                                        scrolls: true))
            }
        }
        return elements
    }
}
