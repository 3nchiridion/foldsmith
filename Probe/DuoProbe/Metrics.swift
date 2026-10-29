import SwiftUI

/// One sample = everything the system reported at one geometry evaluation.
/// Field names are the schema for raw/metrics.jsonl; keep them stable.
nonisolated struct Sample: Codable, Sendable {
    var schema = 2
    var label: String                 // pose label from -label launch argument
    var seq: Int                      // monotonically increasing per launch
    var t: Double                     // seconds since launch
    var sinceLastChange: Double       // seconds since previous sample (first-frame vs settled)
    var window: Size                  // GeometryProxy.size of the root: the content area inside the probe's own bars
    var safeArea: Insets              // GeometryProxy.safeAreaInsets: includes the probe's bars; 0 with -overlay 1
    var hSizeClass: String            // compact | regular | nil
    var vSizeClass: String
    var toolbarVerticalEdge: String   // leading | trailing | nil
    var layoutDirection: String
    var divisions: [Region]           // includeInactive
    var occlusions: [Region]          // includeInactive
    var hinge: Hinge?
    var scene: SceneInfo

    nonisolated struct Size: Codable, Sendable { var w: Double; var h: Double }
    nonisolated struct Insets: Codable, Sendable { var top: Double; var leading: Double; var bottom: Double; var trailing: Double }
    nonisolated struct Region: Codable, Sendable {
        var id: String
        var frame: Rect
        var margins: Insets
        var isActive: Bool
    }
    nonisolated struct Rect: Codable, Sendable { var x: Double; var y: Double; var w: Double; var h: Double }
    nonisolated struct Hinge: Codable, Sendable { var angleDegrees: Double; var status: String }
    nonisolated struct SceneInfo: Codable, Sendable {
        var sceneBounds: Rect?        // UIWindowScene.coordinateSpace.bounds
        var screenBounds: Rect?       // windowScene.screen.bounds (NOT UIScreen.main)
        var displayScale: Double
        var interfaceOrientation: String
        var windowSafeArea: PhysicalInsets?   // the key window's safeAreaInsets: the device's own, no app bars
    }
    nonisolated struct PhysicalInsets: Codable, Sendable { var top: Double; var left: Double; var bottom: Double; var right: Double }
}

nonisolated enum MetricsLog {
    static let start = Date()
    static let encoder: JSONEncoder = { let e = JSONEncoder(); e.outputFormatting = [.sortedKeys]; return e }()
    static let url: URL = {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        return docs.appendingPathComponent("metrics.jsonl")
    }()

    static func append(_ s: Sample) {
        guard let data = try? encoder.encode(s), let line = String(data: data, encoding: .utf8) else { return }
        print("DUOPROBE " + line)
        if let h = try? FileHandle(forWritingTo: url) {
            h.seekToEndOfFile(); h.write((line + "\n").data(using: .utf8)!); try? h.close()
        } else {
            try? (line + "\n").write(to: url, atomically: true, encoding: .utf8)
        }
    }
}

extension Sample.Rect { init(_ r: CGRect) { self.init(x: r.minX, y: r.minY, w: r.width, h: r.height) } }
extension Sample.PhysicalInsets { init(_ i: UIEdgeInsets) { self.init(top: i.top, left: i.left, bottom: i.bottom, right: i.right) } }
extension Sample.Insets { init(_ i: EdgeInsets) { self.init(top: i.top, leading: i.leading, bottom: i.bottom, trailing: i.trailing) } }
