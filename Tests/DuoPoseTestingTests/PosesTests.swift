import Testing
import CoreGraphics
@testable import DuoDetectors

// poses.json is generated from the probe run; this pins its shape and the facts the decision table cites.
@Test func posesJSONDecodesEveryMeasuredPose() throws {
    let poses = try Pose.load()
    let names = Set(poses.map(\.name))
    #expect(names == ["closed", "closed-sideways", "book", "laptop", "tent", "flat-sideways", "flat-upright"])
}

@Test func partFoldedPosesHaveAnActiveDivisionAndFlatOnesAnInactiveOne() throws {
    let poses = Dictionary(uniqueKeysWithValues: try Pose.load().map { ($0.name, $0) })
    for name in ["book", "laptop", "tent"] {
        #expect(poses[name]?.divisions.first?.isActive == true, "\(name)")
    }
    for name in ["flat-sideways", "flat-upright"] {
        #expect(poses[name]?.divisions.first?.isActive == false, "\(name)")
    }
    #expect(poses["closed"]?.divisions.isEmpty == true)
    #expect(poses["book"]?.divisions.first?.frame == CGRect(x: 455.5, y: 0, width: 40, height: 669))
}
