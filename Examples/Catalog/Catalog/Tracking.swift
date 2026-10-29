import SwiftUI
import UIKit

/// Records what the detectors need, from inside the app: the regions the system reports, the pose's classes and
/// insets, and the window frame of every view the catalog tags with `.duoTracked`. The latest snapshot is written to
/// Documents/frames-latest.json shortly after each change; scripts/capture-catalog.sh copies it next to each shot.
/// The catalog only — the copy-in pattern files carry no tracking.
struct TrackedElement: Codable, Equatable {
    var id: String
    var role: String          // control, text, image, pane, cell, column, sheet
    var scrolls: Bool         // inside scrolling content (exempt from T1)
    var x, y, w, h: Double
}

struct TrackedRegion: Codable, Equatable {
    var x, y, w, h: Double
    var isActive: Bool
}

struct Snapshot: Codable {
    var pattern: String
    var variant: String
    var window: [Double]
    var safeArea: [String: Double]
    var hSizeClass: String
    var vSizeClass: String
    var toolbarVerticalEdge: String
    var divisions: [TrackedRegion]
    var occlusions: [TrackedRegion]
    var elements: [TrackedElement]
}

@MainActor
final class Tracker {
    static let shared = Tracker()
    var pattern = "", variant = ""
    var window: CGSize = .zero
    var safeArea = EdgeInsets()
    var classes = ("nil", "nil", "nil")
    var divisions: [TrackedRegion] = []
    var occlusions: [TrackedRegion] = []
    private var elements: [String: TrackedElement] = [:]
    private var pending: Task<Void, Never>?

    func record(_ id: String, role: String, scrolls: Bool, frame: CGRect) {
        elements[id] = TrackedElement(id: id, role: role, scrolls: scrolls,
                                      x: frame.minX, y: frame.minY, w: frame.width, h: frame.height)
        scheduleWrite()
    }

    func forget(_ id: String) {
        elements[id] = nil
        scheduleWrite()
    }

    func scheduleWrite() {
        pending?.cancel()
        pending = Task { @MainActor in
            try? await Task.sleep(for: .milliseconds(400))
            guard !Task.isCancelled else { return }
            write()
        }
    }

    private func write() {
        let snapshot = Snapshot(
            pattern: pattern, variant: variant,
            window: [window.width, window.height],
            safeArea: ["top": safeArea.top, "leading": safeArea.leading, "bottom": safeArea.bottom, "trailing": safeArea.trailing],
            hSizeClass: classes.0, vSizeClass: classes.1, toolbarVerticalEdge: classes.2,
            divisions: divisions, occlusions: occlusions,
            elements: elements.values.sorted { $0.id < $1.id })
        guard let data = try? JSONEncoder().encode(snapshot),
              let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else { return }
        try? data.write(to: dir.appendingPathComponent("frames-latest.json"), options: .atomic)
    }
}

extension View {
    /// Tag a view for the detectors: its window frame is logged under `id` while it is on screen.
    func duoTracked(_ id: String, role: String, scrolls: Bool = false) -> some View {
        onGeometryChange(for: CGRect.self) { $0.frame(in: .global) } action: { frame in
            Tracker.shared.record(id, role: role, scrolls: scrolls, frame: frame)
        }
        .onDisappear { Tracker.shared.forget(id) }
    }
}

/// Window-filling probe at the root: regions, insets and size classes, as DuoProbe logs them.
struct RegionRecorder: View {
    @Environment(\.horizontalSizeClass) private var hClass
    @Environment(\.verticalSizeClass) private var vClass
    @Environment(\.toolbarVerticalEdge) private var verticalEdge

    var body: some View {
        GeometryReader { proxy in
            Color.clear.onGeometryChange(for: RegionKey.self) { proxy in
                RegionKey(proxy: proxy)
            } action: { key in
                let t = Tracker.shared
                t.window = key.size
                t.safeArea = key.insets
                t.divisions = key.divisions
                t.occlusions = key.occlusions
                t.classes = (describe(hClass), describe(vClass), describe(verticalEdge))
                t.scheduleWrite()
            }
        }
        .ignoresSafeArea()
    }

    private func describe<T>(_ v: T?) -> String { v.map { String(describing: $0) } ?? "nil" }
}

private struct RegionKey: Equatable, Sendable {
    var size: CGSize
    var insets: EdgeInsets
    var divisions: [TrackedRegion]
    var occlusions: [TrackedRegion]

    nonisolated init(proxy: GeometryProxy) {
        size = proxy.size
        insets = proxy.safeAreaInsets
        let convert: (ReservedRegion) -> TrackedRegion = {
            TrackedRegion(x: $0.frame.minX, y: $0.frame.minY, w: $0.frame.width, h: $0.frame.height, isActive: $0.isActive)
        }
        divisions = proxy.reservedRegions(kind: .division, options: .includeInactive).map(convert)
        occlusions = proxy.reservedRegions(kind: .occlusion, options: .includeInactive).map(convert)
    }
}
