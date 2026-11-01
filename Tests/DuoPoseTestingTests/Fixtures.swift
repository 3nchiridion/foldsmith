import Foundation

// The catalog's frame records and accessibility snapshots, packed by scripts/pack-fixtures.py into one JSON object each
// (path → file text), so a clone holds two files instead of 238, and the NetNewsWire rerun's Add Feed snapshots, packed
// by hand in the same format (not in the evidence repository). Each is unpacked once into a temporary folder, and the
// tests read that folder as they would the evidence repository's.
enum Fixtures {
    private static let root = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("Fixtures")

    /// `<pattern>/<config>-<pose>.json`, as in the evidence repository's verification/matrices/.
    static let matrices = unpack("matrices", from: "python3 scripts/pack-fixtures.py writes it")
    /// `<pattern>-<config>-<pose>.json`, as in the evidence repository's verification/accessibility/catalog/.
    static let accessibilityCatalog = unpack("accessibility-catalog", from: "python3 scripts/pack-fixtures.py writes it")
    /// `before/add-feed-<pose>.json`, `after/…`: NetNewsWire's Add Feed sheet in the four poses with a vertical bar,
    /// the accessibility snapshots of its rerun with Foldsmith 0.8.0 (the run's .duo/captures/NetNewsWire/), byte for
    /// byte. That run is not in the evidence repository, so this file was packed by hand, not by pack-fixtures.py.
    static let netNewsWireRerunAddFeed = unpack("netnewswire-rerun-add-feed",
                                                from: "packed by hand from the rerun's .duo/captures/NetNewsWire")

    private static func unpack(_ name: String, from source: String) -> URL {
        let out = FileManager.default.temporaryDirectory
            .appendingPathComponent("foldsmith-fixtures-\(ProcessInfo.processInfo.processIdentifier)")
            .appendingPathComponent(name)
        do {
            let files = try JSONDecoder().decode([String: String].self,
                                                 from: Data(contentsOf: root.appendingPathComponent("\(name).json")))
            for (path, text) in files {
                let file = out.appendingPathComponent(path)
                try FileManager.default.createDirectory(at: file.deletingLastPathComponent(), withIntermediateDirectories: true)
                try Data(text.utf8).write(to: file)
            }
        } catch {
            fatalError("Tests/Fixtures/\(name).json: \(error) (\(source))")
        }
        return out
    }
}
