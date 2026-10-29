import Foundation
import CoreGraphics

/// A detector turns a record of one screen in one pose into findings. The record is a flat list of elements in
/// window coordinates, captured from the running app on the Duo simulator (the catalog writes one per shot, see
/// `CatalogSnapshot`); the pose supplies the window, insets and reserved regions the app saw. Classes and thresholds
/// are the ones in patterns/TAXONOMY.md.
public struct Element: Codable, Sendable, Hashable {
    public var identifier: String?
    public var label: String?
    /// control, button, text, image (leaf content) · pane, column, cell (side-by-side containers) · sheet · bar (a
    /// navigation bar: where a split view's pane runs, by the bar its column carries)
    public var role: String
    public var frame: CGRect         // window coordinates
    public var isInteractive: Bool
    /// Inside scrolling content. Scrolling content may cross the hinge [tt-111466 9:28], so T1 skips it.
    public var scrolls: Bool
    /// An item of a navigation bar, toolbar or tab bar: the system places it, in the vertical bar and around the camera,
    /// so T2 and T4 skip it. T1 still applies.
    public var inSystemBar: Bool
    /// A button of a navigation bar (the nearest bar above it): what goes vertical with the bar, or should (T10).
    public var inNavigationBar: Bool
    /// A control of a toolbar (the nearest bar above it, no scrolling content in between): a bottom toolbar's items go
    /// into the vertical bar too, unless they are custom views (T10).
    public var inToolbar: Bool
    /// A control drawn from one margin of its pane to the other (a search field, a segmented control): where its
    /// trailing end falls says where the pane's content ends (T14).
    public var spansWidth: Bool

    public init(identifier: String? = nil, label: String? = nil, role: String, frame: CGRect,
                isInteractive: Bool = false, scrolls: Bool = false, inSystemBar: Bool = false,
                inNavigationBar: Bool = false, inToolbar: Bool = false, spansWidth: Bool = false) {
        self.identifier = identifier
        self.label = label
        self.role = role
        self.frame = frame
        self.isInteractive = isInteractive
        self.scrolls = scrolls
        self.inSystemBar = inSystemBar
        self.inNavigationBar = inNavigationBar
        self.inToolbar = inToolbar
        self.spansWidth = spansWidth
    }

    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        identifier = try c.decodeIfPresent(String.self, forKey: .identifier)
        label = try c.decodeIfPresent(String.self, forKey: .label)
        role = try c.decode(String.self, forKey: .role)
        frame = try c.decode(CGRect.self, forKey: .frame)
        isInteractive = try c.decodeIfPresent(Bool.self, forKey: .isInteractive) ?? false
        scrolls = try c.decodeIfPresent(Bool.self, forKey: .scrolls) ?? false
        inSystemBar = try c.decodeIfPresent(Bool.self, forKey: .inSystemBar) ?? false
        inNavigationBar = try c.decodeIfPresent(Bool.self, forKey: .inNavigationBar) ?? false
        inToolbar = try c.decodeIfPresent(Bool.self, forKey: .inToolbar) ?? false
        spansWidth = try c.decodeIfPresent(Bool.self, forKey: .spansWidth) ?? false
    }

    var isContainer: Bool { ["pane", "column", "cell"].contains(role) }
    public var name: String { identifier ?? label ?? role }
}

public struct Finding: Codable, Sendable, Hashable {
    public var classId: String       // T1, T2, T4, T5, T7, T10, T14, T15
    public var pose: String
    public var element: Element?
    public var detail: String
}

public protocol Detector: Sendable {
    static var classId: String { get }
    func run(elements: [Element], pose: Pose) -> [Finding]
}

extension Pose {
    /// Divisions that run top to bottom (the crease in book, flat-sideways and Split View's half).
    func verticalDivisions(activeOnly: Bool) -> [CGRect] {
        divisions.filter { (!activeOnly || $0.isActive) && $0.frame.height > $0.frame.width }.map(\.frame)
    }
}

public enum Detectors {
    /// Overlap below this is layout rounding, not a defect: the system's own sidebar ends 0.2 pt into the division's
    /// frame in book (455.7 against 455.5, measured in the catalog).
    public static let tolerance: CGFloat = 1

    public static let all: [any Detector] = [
        CreaseStraddle(), ContentUnderOcclusion(), UnderSystemBar(),
        StretchedSingleColumn(), ColumnsOffFold(), PanesOffHorizontalFold(), PaneBoundaryOffFold(), PaneContentShortOfFold(),
        SheetInBook(),
        StrandedHorizontalItem(),
    ]

    public static func runAll(elements: [Element], pose: Pose) -> [Finding] {
        all.flatMap { $0.run(elements: elements, pose: pose) }
    }

    static func horizontalOverlap(_ a: CGRect, _ b: CGRect) -> CGFloat {
        max(0, min(a.maxX, b.maxX) - max(a.minX, b.minX))
    }

    static func overlaps(_ a: CGRect, _ b: CGRect) -> Bool {
        let i = a.intersection(b)
        return !i.isNull && i.width > tolerance && i.height > tolerance
    }
}

/// T1 crease-straddle: a control, text or focal image that does not scroll, intersecting an active division.
/// Region frames already include Apple's margins (api-swiftui.md), so any overlap beyond rounding counts.
public struct CreaseStraddle: Detector {
    public static let classId = "T1"
    public init() {}
    public func run(elements: [Element], pose: Pose) -> [Finding] {
        let active = pose.divisions.filter(\.isActive).map(\.frame)
        guard !active.isEmpty else { return [] }
        let leaves = elements.filter { !$0.scrolls && ($0.isInteractive || ["control", "button", "text", "image"].contains($0.role)) }
        return leaves.compactMap { e in
            active.first { Detectors.overlaps($0, e.frame) }.map { r in
                Finding(classId: Self.classId, pose: pose.name, element: e,
                        detail: "\(e.name) (\(span(e.frame, along: r))) intersects the active division (\(span(r, along: r)))")
            }
        }
    }
}

/// T2 — meaningful content under an active occlusion. Named by Apple; no corpus evidence yet.
public struct ContentUnderOcclusion: Detector {
    public static let classId = "T2"
    public init() {}
    public func run(elements: [Element], pose: Pose) -> [Finding] {
        let active = pose.occlusions.filter(\.isActive).map(\.frame)
        guard !active.isEmpty else { return [] }
        return elements.filter { !$0.scrolls && !$0.inSystemBar && ($0.role == "text" || $0.role == "image" || $0.isInteractive) }.compactMap { e in
            active.first { Detectors.overlaps($0, e.frame) }.map { r in
                Finding(classId: Self.classId, pose: pose.name, element: e, detail: "\(e.name) intersects active occlusion \(r)")
            }
        }
    }
}

/// T4 — interactive element inside the safe-area band on the vertical-bar edge, by at least half its width. Named by Apple;
/// no corpus evidence yet.
public struct UnderSystemBar: Detector {
    public static let classId = "T4"
    public init() {}
    public func run(elements: [Element], pose: Pose) -> [Finding] {
        guard let edge = pose.toolbarVerticalEdge else { return [] }
        let w = pose.window
        let band: CGRect = edge == "trailing"
            ? CGRect(x: w.width - pose.safeArea.trailing, y: 0, width: pose.safeArea.trailing, height: w.height)
            : CGRect(x: 0, y: 0, width: pose.safeArea.leading, height: w.height)
        guard band.width > 0 else { return [] }
        // At least half the element inside the band: an accessibility frame can run to the window's edge past what is
        // drawn (Home Assistant's Connect button on the cover reads 58–466 pt and is drawn to about 408 pt).
        return elements.filter { $0.isInteractive && !$0.inSystemBar }.filter {
            Detectors.overlaps(band, $0.frame) && Detectors.horizontalOverlap(band, $0.frame) >= $0.frame.width / 2
        }.map {
            Finding(classId: Self.classId, pose: pose.name, element: $0, detail: "\($0.name) under the \(edge) system bar band")
        }
    }
}

/// T5 stretched-single-column: one text column runs across a vertical division, active (book) or not (flat,
/// sideways). The inner display wants two columns reflowing from one [tt-111466 7:34]. A horizontal division (laptop,
/// tent) never triggers it: a column 669 pt wide is ordinary there.
public struct StretchedSingleColumn: Detector {
    public static let classId = "T5"
    public init() {}
    public func run(elements: [Element], pose: Pose) -> [Finding] {
        let folds = pose.verticalDivisions(activeOnly: false)
        let columns = elements.filter { $0.role == "column" }
        guard let fold = folds.first, columns.count == 1, let column = columns.first else { return [] }
        guard column.frame.minX < fold.minX - Detectors.tolerance, column.frame.maxX > fold.maxX + Detectors.tolerance else { return [] }
        let state = pose.verticalDivisions(activeOnly: true).contains(fold) ? "active" : "inactive"
        return [Finding(classId: Self.classId, pose: pose.name, element: column,
                        detail: "single text column \(span(column.frame)) (\(Int(column.frame.width)) pt) runs across the \(state) division (\(span(fold)))")]
    }
}

/// T14 columns-off-fold: a layout of side-by-side containers (panes, text columns, grid columns) while the device is
/// folded like a book, where a container overlaps the division: its edge falls inside the frame or it straddles it.
/// Each half should hold whole containers [hig reserved-regions; tt-111463 5:12]. One finding per distinct column.
public struct ColumnsOffFold: Detector {
    public static let classId = "T14"
    public init() {}
    public func run(elements: [Element], pose: Pose) -> [Finding] {
        guard let fold = pose.verticalDivisions(activeOnly: true).first else { return [] }
        let containers = elements.filter(\.isContainer)
        // Distinct horizontal extents: a grid's cells share their column's extent.
        var extents: [(CGFloat, CGFloat, Element)] = []
        for e in containers.sorted(by: { ($0.frame.minX, $0.frame.minY) < ($1.frame.minX, $1.frame.minY) })
        where !extents.contains(where: { abs($0.0 - e.frame.minX) < 1 && abs($0.1 - e.frame.maxX) < 1 }) {
            extents.append((e.frame.minX, e.frame.maxX, e))
        }
        guard extents.count >= 2 else { return [] }   // one container across the fold is T5's case, not this one
        return extents.compactMap { minX, maxX, e in
            let overlap = Detectors.horizontalOverlap(CGRect(x: minX, y: 0, width: maxX - minX, height: 1), fold)
            guard overlap > Detectors.tolerance else { return nil }
            let kind = minX < fold.minX && maxX > fold.maxX ? "straddles" : "has an edge inside"
            return Finding(classId: Self.classId, pose: pose.name, element: e,
                           detail: "\(e.role) \(span(e.frame)) \(kind) the active division (\(span(fold)))")
        }
    }
}

/// T14 columns-off-fold, turned: panes stacked one above the other while the phone is folded like a laptop or a tent,
/// where a pane's edge falls inside the horizontal division or the pane straddles it. A split arrangement in a window
/// taller than wide stacks its views and moves the boundary onto the fold [tt-111463 12:00]. Only panes count: grid
/// cells and text columns may scroll across a horizontal fold [tt-111466 9:28].
public struct PanesOffHorizontalFold: Detector {
    public static let classId = "T14"
    public init() {}
    public func run(elements: [Element], pose: Pose) -> [Finding] {
        guard let fold = pose.divisions.first(where: { $0.isActive && $0.frame.width > $0.frame.height })?.frame else { return [] }
        // Stacked: another pane above or below it, sharing some width. Panes side by side (a split view's columns,
        // upright) cross the fold together and are left alone.
        let panes = elements.filter { $0.role == "pane" }
        let stacked = panes.filter { e in
            panes.contains { o in
                o != e && Detectors.horizontalOverlap(o.frame, e.frame) > Detectors.tolerance
                    && max(0, min(o.frame.maxY, e.frame.maxY) - max(o.frame.minY, e.frame.minY)) <= Detectors.tolerance
            }
        }
        return stacked.compactMap { e in
            let (minY, maxY) = (e.frame.minY, e.frame.maxY)
            let overlap = max(0, min(maxY, fold.maxY) - max(minY, fold.minY))
            guard overlap > Detectors.tolerance else { return nil }
            let kind = minY < fold.minY && maxY > fold.maxY ? "straddles" : "has an edge inside"
            return Finding(classId: Self.classId, pose: pose.name, element: e,
                           detail: "pane \(span(e.frame, along: fold)) \(kind) the active division (\(span(fold, along: fold)))")
        }
    }
}

/// T14 columns-off-fold, by the bars: in a split view each pane carries its own navigation bar, and a pane with no text
/// in it (an empty timeline, a detail showing a placeholder) gives the column rule nothing to measure. Where two bars
/// sit side by side while the book fold is active, the boundary between them belongs inside the division: the system
/// split ends one bar and starts the next at the fold's centre (475.5 pt, measured on NetNewsWire after its migration),
/// a fixed sidebar width puts it elsewhere (320.5 pt before).
public struct PaneBoundaryOffFold: Detector {
    public static let classId = "T14"
    public init() {}
    public func run(elements: [Element], pose: Pose) -> [Finding] {
        guard let fold = pose.verticalDivisions(activeOnly: true).first else { return [] }
        var bars: [Element] = []
        for e in elements.filter({ $0.role == "bar" }).sorted(by: { $0.frame.minX < $1.frame.minX })
        where !bars.contains(where: { abs($0.frame.minX - e.frame.minX) < 1 && abs($0.frame.maxX - e.frame.maxX) < 1 }) {
            bars.append(e)
        }
        return zip(bars, bars.dropFirst()).compactMap { leading, trailing in
            // Side by side: the next bar starts where this one ends, on the same row.
            guard abs(trailing.frame.minX - leading.frame.maxX) <= 2,
                  leading.frame.minY < trailing.frame.maxY, trailing.frame.minY < leading.frame.maxY else { return nil }
            let boundary = (leading.frame.maxX + trailing.frame.minX) / 2
            guard boundary < fold.minX - Detectors.tolerance || boundary > fold.maxX + Detectors.tolerance else { return nil }
            let f = boundary == boundary.rounded() ? String(Int(boundary)) : String(format: "%.1f", boundary)
            return Finding(classId: Self.classId, pose: pose.name, element: trailing,
                           detail: "panes \(leading.name) and \(trailing.name) meet at \(f) pt, off the active division (\(span(fold)))")
        }
    }
}

/// T14 columns-off-fold, by what spans a pane: a search field or a segmented control runs from the pane's leading margin
/// to its trailing one. In a leading pane whose bar ends at the fold, one that stops 40 pt or more shorter of the pane's
/// trailing edge than it starts from the leading edge means the pane's content ends off the fold, leaving a blank strip
/// before it: Wikipedia's own split container before its review fixes, where UIKit inset every screen of the list's
/// stack by the vertical bar's 84 pt (search field 20–371, segmented control 16–355 in a pane that ends at 455). The
/// inactive division counts too: a split that keeps the fold flat must keep it whole.
public struct PaneContentShortOfFold: Detector {
    public static let classId = "T14"
    public init() {}
    public func run(elements: [Element], pose: Pose) -> [Finding] {
        guard let fold = pose.verticalDivisions(activeOnly: false).first else { return [] }
        let panes = elements.filter { $0.role == "bar" && $0.frame.minX < fold.minX && abs($0.frame.maxX - fold.minX) <= 2 }
        return elements.filter(\.spansWidth).compactMap { e in
            guard let pane = panes.first(where: { $0.frame.minX - Detectors.tolerance <= e.frame.midX
                                                  && e.frame.midX <= $0.frame.maxX + Detectors.tolerance }) else { return nil }
            // The row ends with the last control beside it (a search field's Cancel button), not with the field.
            let rowEnd = elements.filter {
                $0.isInteractive && $0.frame.minY < e.frame.maxY && e.frame.minY < $0.frame.maxY
                    && $0.frame.minX >= e.frame.minX && $0.frame.maxX <= pane.frame.maxX + Detectors.tolerance
            }.map(\.frame.maxX).max() ?? e.frame.maxX
            let leading = e.frame.minX - pane.frame.minX, trailing = pane.frame.maxX - rowEnd
            guard trailing - leading >= 40 else { return nil }
            return Finding(classId: Self.classId, pose: pose.name, element: e,
                           detail: "\(e.name) (\(span(e.frame))): its row stops \(Int(trailing.rounded())) pt short of its pane's edge at \(Int(pane.frame.maxX.rounded())) pt, against \(Int(leading.rounded())) pt at the leading edge: the pane's content ends off the fold (\(span(fold)))")
        }
    }
}

/// T10 stranded-horizontal-item: a navigation bar item drawn as text stays horizontal where the bar goes vertical
/// [tt-111462 5:56]; symbols move into the vertical bar. Text-shaped (40 % wider than tall; symbols are square) and left outside the
/// vertical bar's band, in a pose that has one. NetNewsWire's Add Feed before its migration: Cancel 77 × 36 and Add
/// 56 × 36 pt in the top bar; after, symbols 38 × 38 pt in the band.
/// A toolbar's items go into the vertical bar whatever their shape, so any toolbar control left outside the band is
/// stranded: a custom-view item, square or not (Wikipedia's article toolbar before its migration: six
/// `UIBarButtonItem(customView:)` buttons in a row along the cover's bottom edge while the navigation items stood in the
/// band; NetNewsWire's Reader View button, a custom view, beside the band on the cover and in the detail pane). In a split
/// each pane keeps its own bottom toolbar and only the pane beside the vertical bar hands its items to it: NetNewsWire's
/// timeline keeps Mark All as Read and Search at the bottom of the leading pane, as the system draws them. An item's pane
/// is the navigation bar over its midpoint; with none, the window.
public struct StrandedHorizontalItem: Detector {
    public static let classId = "T10"
    public init() {}
    public func run(elements: [Element], pose: Pose) -> [Finding] {
        guard let edge = pose.toolbarVerticalEdge else { return [] }
        let w = pose.window
        let band: CGRect = edge == "trailing"
            ? CGRect(x: w.width - pose.safeArea.trailing, y: 0, width: pose.safeArea.trailing, height: w.height)
            : CGRect(x: 0, y: 0, width: pose.safeArea.leading, height: w.height)
        guard band.width > 0 else { return [] }
        func outside(_ e: Element) -> Bool { Detectors.horizontalOverlap(band, e.frame) < e.frame.width / 2 }
        let text = elements.filter {
            $0.inNavigationBar && $0.isInteractive && $0.frame.width >= 1.4 * $0.frame.height && outside($0)
        }.map {
            Finding(classId: Self.classId, pose: pose.name, element: $0,
                    detail: "\($0.name) (\(Int($0.frame.width)) × \(Int($0.frame.height)) pt, text) stays in the horizontal bar while the bar is vertical (\(edge))")
        }
        let paneBars = elements.filter { $0.role == "bar" }
        func besideVerticalBar(_ e: Element) -> Bool {
            guard let pane = paneBars.first(where: { $0.frame.minX - Detectors.tolerance <= e.frame.midX
                                                     && e.frame.midX <= $0.frame.maxX + Detectors.tolerance }) else { return true }
            return edge == "trailing" ? pane.frame.maxX >= band.minX - Detectors.tolerance
                                      : pane.frame.minX <= band.maxX + Detectors.tolerance
        }
        let toolbar = elements.filter {
            $0.inToolbar && $0.isInteractive && !$0.scrolls && outside($0) && besideVerticalBar($0)
        }.map {
            Finding(classId: Self.classId, pose: pose.name, element: $0,
                    detail: "\($0.name) (\(span($0.frame))) stays in a horizontal toolbar while the bar is vertical (\(edge)): a custom-view or text item")
        }
        return text + toolbar
    }
}

/// T7 state-loss-on-fold, across poses: the screen the person was on, named by what stays on the shut phone's screen
/// (its bars and the controls outside scrolling content), should still be on the inner display when the phone opens.
/// None of them there means the fold took the person somewhere else (NetNewsWire before its migration: the feeds list
/// became an empty timeline beside "No selection"). The system preserves state across the hinge [Group Lab #4, #6, #7].
public enum StateLossOnFold {
    public static let classId = "T7"
    public static let innerPoses: Set<String> = ["book", "laptop", "tent", "flat-sideways", "flat-upright"]

    /// `closed`: what the shut phone shows by name; `inner`: each inner pose's. One finding per pose that has none of them.
    public static func run(closed: Set<String>, inner: [String: Set<String>]) -> [Finding] {
        guard !closed.isEmpty else { return [] }
        return inner.keys.sorted().filter { innerPoses.contains($0) }.compactMap { pose in
            guard let names = inner[pose], names.isDisjoint(with: closed) else { return nil }
            return Finding(classId: classId, pose: pose, element: nil,
                           detail: "none of the shut phone's \(closed.sorted().prefix(4).joined(separator: ", ")) is on the inner display")
        }
    }

    /// Toolbar items stranded on the shut phone (T10 there: custom views outside the vertical bar) that are nowhere on the
    /// inner display in a pose with a vertical bar: the system drew none of the items (Wikipedia's article toolbar before
    /// its migration, book and flat sideways: six items on the cover, two empty capsules there). `stranded`: their
    /// identifiers or labels on the shut phone; `inner`: every element's identifiers and labels in each inner pose that
    /// has a vertical bar. Any one of them anywhere on the inner display clears the pose.
    /// The shut phone's stranded toolbar items by identifier or label, from its findings; an item with neither cannot
    /// be looked up in another pose and is left out.
    public static func strandedNames(_ findings: [Finding]) -> Set<String> {
        Set(findings.filter { $0.classId == StrandedHorizontalItem.classId && $0.element?.inToolbar == true }
            .compactMap { f in f.element.flatMap { $0.identifier ?? $0.label } })
    }

    /// Every identifier and label on screen in a pose, what `strandedNames` are looked up in.
    public static func names(_ elements: [Element]) -> Set<String> {
        Set(elements.flatMap { [$0.identifier, $0.label].compactMap { $0 } })
    }

    public static func lostBarItems(stranded: Set<String>, inner: [String: Set<String>]) -> [Finding] {
        guard !stranded.isEmpty else { return [] }
        return inner.keys.sorted().filter { innerPoses.contains($0) }.compactMap { pose in
            guard let names = inner[pose], names.isDisjoint(with: stranded) else { return nil }
            let sorted = stranded.sorted()
            let listed = sorted.prefix(4).joined(separator: ", ") + (sorted.count > 4 ? ", … \(sorted.count) in all" : "")
            return Finding(classId: classId, pose: pose, element: nil,
                           detail: "none of the shut phone's toolbar items (\(listed)) is on the inner display")
        }
    }

    /// The app was gone from the screen in a pose (it crashed or quit on the fold): the state is lost with it, in any
    /// pose. The shot shows the Home Screen; the snapshot says why.
    public static func notInFront(appState: String?, pose: String) -> Finding? {
        guard let appState, appState != "runningForeground" else { return nil }
        return Finding(classId: classId, pose: pose, element: nil,
                       detail: "the app was not in front (\(appState)): it crashed or quit on the way to this pose")
    }
}

/// T15 sheet-in-book: a sheet on the leading half while the book fold is active. The system's automatic placement
/// puts it there (6 sheets in 4 corpus apps); alerts go to the trailing side in book [tt-111463 4:00], and
/// `presentationPlacement(.trailing)` does the same for a sheet. The defect is the side: both placements end about
/// 8 pt from the crease, inside the division's margin, as the system's own placement does.
public struct SheetInBook: Detector {
    public static let classId = "T15"
    public init() {}
    public func run(elements: [Element], pose: Pose) -> [Finding] {
        guard let fold = pose.verticalDivisions(activeOnly: true).first else { return [] }
        return elements.filter { $0.role == "sheet" && $0.frame.midX < fold.midX }.map {
            Finding(classId: Self.classId, pose: pose.name, element: $0,
                    detail: "sheet \(span($0.frame)) sits on the leading half while the fold (\(span(fold))) is active")
        }
    }
}

/// "455.5–495.5" for a frame's horizontal extent, the way the taxonomy writes it; across a horizontal division (laptop,
/// tent) the vertical extent, "y 455.5–495.5".
func span(_ r: CGRect, along division: CGRect? = nil) -> String {
    func f(_ v: CGFloat) -> String { v == v.rounded() ? String(Int(v)) : String(format: "%.1f", v) }
    if let d = division, d.width > d.height { return "y \(f(r.minY))–\(f(r.maxY))" }
    return "\(f(r.minX))–\(f(r.maxX))"
}
