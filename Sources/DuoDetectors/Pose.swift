import Foundation
import CoreGraphics

/// A pose as the harness understands it: the window the app gets and the regions the system reports.
/// Values come from `Resources/poses.json`, which is generated from `raw/metrics.jsonl` by
/// `scripts/metrics-to-poses.py`. Nothing here is hand-typed.
public struct Pose: Codable, Sendable, Hashable {
    public var name: String                 // closed, closed-sideways, book, laptop, tent, flat-sideways, flat-upright, split-half
    public var display: String              // inner | outer
    public var window: CGSize
    public var safeArea: Insets
    public var hSizeClass: String
    public var vSizeClass: String
    public var toolbarVerticalEdge: String? // leading | trailing | nil
    public var divisions: [Region]
    public var occlusions: [Region]

    public struct Insets: Codable, Sendable, Hashable { public var top, leading, bottom, trailing: CGFloat }
    public struct Region: Codable, Sendable, Hashable {
        public var frame: CGRect
        public var margins: Insets
        public var isActive: Bool
    }

    public static func load() throws -> [Pose] {
        guard let url = Bundle.module.url(forResource: "poses", withExtension: "json") else { return [] }
        return try JSONDecoder().decode([Pose].self, from: Data(contentsOf: url))
    }
}

/// What the harness can and cannot do, stated so nobody over-trusts it.
///
/// 1. In-process rendering at a pose's window size + safe-area insets: possible on any simulator, via
///    SnapshotTesting with a custom `ViewImageConfig`. This covers size-class and inset behaviour.
/// 2. Reserved regions and the vertical bar: NOT injectable. The system owns them. A view rendered
///    in-process on a non-Duo simulator will see no division regions, so fold behaviour is only
///    testable when the test host actually runs on the Duo simulator in that pose. CI must therefore
///    drive the Duo simulator (Device Hub automation or the community `duo.py` driver) and take
///    device-level screenshots; the in-process path is a fast pre-check, not the gate.
/// 3. Detectors (T1, T2, T4, T5, T7, T10, T14, T15) run on frame records captured from the running app on the Duo
///    simulator, so they share the same constraint. The pattern catalog writes its own (`CatalogSnapshot`); any other app
///    is read through its accessibility tree, mapped to `Element` by `AccessibilitySnapshot`.
public enum HarnessCapability {
    case inProcessSizeOnly
    case duoSimulatorFullPose
}
