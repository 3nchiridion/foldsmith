// swift-tools-version: 6.0
// Foldsmith's Swift package: DuoPoseTesting (pose geometry and snapshot helpers) and DuoDetectors (taxonomy detectors)
// for iPhone Duo; duo-detect runs them on catalog captures.
// Pose geometry comes from raw/metrics.jsonl (Resources/poses.json) or from the capture itself, never hand-typed.
import PackageDescription

let package = Package(
    name: "Foldsmith",
    platforms: [.iOS(.v18), .macOS(.v14)],   // the package itself targets 18 so host apps with older deployment targets can depend on it; Duo APIs are gated inside
    products: [
        .library(name: "DuoPoseTesting", targets: ["DuoPoseTesting"]),
        .library(name: "DuoDetectors", targets: ["DuoDetectors"]),
        .executable(name: "duo-detect", targets: ["duo-detect"]),
    ],
    dependencies: [
        .package(url: "https://github.com/pointfreeco/swift-snapshot-testing", from: "1.17.0"),
    ],
    targets: [
        // Pose geometry and taxonomy detectors; Foundation only, so a command-line tool can link it.
        .target(name: "DuoDetectors", resources: [.copy("Resources/poses.json")]),
        .target(
            name: "DuoPoseTesting",
            dependencies: ["DuoDetectors", .product(name: "SnapshotTesting", package: "swift-snapshot-testing")]
        ),
        .executableTarget(name: "duo-detect", dependencies: ["DuoDetectors"]),
        .testTarget(name: "DuoPoseTestingTests", dependencies: ["DuoDetectors", "DuoPoseTesting"]),
    ]
)
