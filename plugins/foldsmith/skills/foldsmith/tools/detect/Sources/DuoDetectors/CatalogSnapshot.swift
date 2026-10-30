import Foundation
import CoreGraphics

/// What the pattern catalog (Examples/Catalog) writes to frames-latest.json and scripts/capture-catalog.sh copies
/// next to each shot: the window, insets, size classes and reserved regions the app saw, and the window frame of
/// every view it tags. Measured live, so it carries the pose instead of borrowing one from poses.json.
public struct CatalogSnapshot: Codable, Sendable {
    public struct Region: Codable, Sendable { public var x, y, w, h: Double; public var isActive: Bool }
    public struct Tracked: Codable, Sendable {
        public var id: String
        public var role: String
        public var scrolls: Bool
        public var x, y, w, h: Double
    }

    public var pattern: String
    public var variant: String
    public var window: [Double]
    public var safeArea: [String: Double]
    public var hSizeClass: String
    public var vSizeClass: String
    public var toolbarVerticalEdge: String
    public var divisions: [Region]
    public var occlusions: [Region]
    public var elements: [Tracked]

    /// The seven poses capture-catalog.sh shoots, in the order the matrices show them.
    public static let poseNames = ["closed", "closed-sideways", "book", "laptop", "tent", "flat-sideways", "flat-upright"]

    public static func load(_ url: URL) throws -> CatalogSnapshot {
        try JSONDecoder().decode(CatalogSnapshot.self, from: Data(contentsOf: url))
    }

    /// The pose label from a capture's file name, `<config>-<pose>.json`.
    public static func poseName(of url: URL) -> String? {
        let stem = url.deletingPathExtension().lastPathComponent
        return poseNames.filter { stem.hasSuffix("-" + $0) }.max { $0.count < $1.count }
    }

    public func pose(named name: String) -> Pose {
        func region(_ r: Region) -> Pose.Region {
            .init(frame: CGRect(x: r.x, y: r.y, width: r.w, height: r.h),
                  margins: .init(top: 0, leading: 0, bottom: 0, trailing: 0), isActive: r.isActive)
        }
        // SwiftUI prints the toolbar edge as "Optional(leading)" style descriptions or bare cases; keep the case name.
        let edge = ["leading", "trailing"].first { toolbarVerticalEdge.contains($0) }
        return Pose(name: name, display: name.hasPrefix("closed") ? "outer" : "inner",
                    window: CGSize(width: window[0], height: window[1]),
                    safeArea: .init(top: safeArea["top"] ?? 0, leading: safeArea["leading"] ?? 0,
                                    bottom: safeArea["bottom"] ?? 0, trailing: safeArea["trailing"] ?? 0),
                    hSizeClass: hSizeClass, vSizeClass: vSizeClass, toolbarVerticalEdge: edge,
                    divisions: divisions.map(region), occlusions: occlusions.map(region))
    }

    public var detectorElements: [Element] {
        elements.map {
            Element(identifier: $0.id, role: $0.role, frame: CGRect(x: $0.x, y: $0.y, width: $0.w, height: $0.h),
                    isInteractive: $0.role == "control" || $0.role == "button", scrolls: $0.scrolls)
        }
    }
}
