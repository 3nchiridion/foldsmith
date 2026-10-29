import Testing
import Foundation
@testable import DuoDetectors

// The pattern gate on real captures: every reference implementation is clean in every pose, and each "before"
// variant shows the defect it was built to reproduce, in book (and for T5 flat-sideways, for T1 laptop and tent). The captures are
// verification/matrices/<pattern>/<config>-<pose>.json, written by scripts/capture-catalog.sh on the Duo simulator.
private let matrices = URL(fileURLWithPath: #filePath)
    .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
    .appendingPathComponent("verification/matrices")

/// config ("pattern/stem") → pose → classes found
private func run() throws -> [String: [String: Set<String>]] {
    var out: [String: [String: Set<String>]] = [:]
    let files = FileManager.default.enumerator(at: matrices, includingPropertiesForKeys: nil)?
        .compactMap { $0 as? URL }.filter { $0.pathExtension == "json" } ?? []
    for file in files {
        guard let pose = CatalogSnapshot.poseName(of: file) else { continue }
        let s = try CatalogSnapshot.load(file)
        let stem = file.deletingPathExtension().lastPathComponent.dropLast(pose.count + 1)
        out["\(s.pattern)/\(stem)", default: [:]][pose] =
            Set(Detectors.runAll(elements: s.detectorElements, pose: s.pose(named: pose)).map(\.classId))
    }
    return out
}

private let allPoses = Set(CatalogSnapshot.poseNames)

@Test func everyConfigWasCapturedInEveryPose() throws {
    let results = try run()
    #expect(results.count == 17)
    for (config, poses) in results { #expect(Set(poses.keys) == allPoses, "\(config)") }
}

@Test(arguments: ["split/aligned", "split/aligned-sheet", "split/system", "split/three", "split/three-list", "split/tiled",
                  "split/tiled-three", "split/tiled-three-list", "grid/aligned", "columns/aligned",
                  "arrangement/aligned", "arrangement/overlay"])
func referenceIsCleanInEveryPose(config: String) throws {
    let poses = try #require(try run()[config])
    for (pose, classes) in poses { #expect(classes.isEmpty, "\(config) \(pose): \(classes.sorted())") }
}

@Test(arguments: [
    ("split/fixed", ["book": "T14"]),
    ("split/system-sheet", ["book": "T15"]),
    ("grid/naive", ["book": "T14"]),
    ("columns/single", ["book": "T5", "flat-sideways": "T5"]),
    ("arrangement/inline", ["book": "T5", "laptop": "T1", "tent": "T1", "flat-sideways": "T5"]),
])
func beforeVariantShowsItsDefectAndNothingElse(config: String, expected: [String: String]) throws {
    let poses = try #require(try run()[config])
    for (pose, classes) in poses {
        #expect(classes == Set(expected[pose].map { [$0] } ?? []), "\(config) \(pose): \(classes.sorted())")
    }
}
