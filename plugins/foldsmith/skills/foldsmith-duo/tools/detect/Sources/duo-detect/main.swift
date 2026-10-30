// duo-detect — run the taxonomy detectors on captures: the pattern catalog's frame records, or the accessibility
// snapshots of any app (scripts/capture-corpus-flow.sh with SNAPSHOT=1, scripts/capture-poses.sh).
//
//   swift run duo-detect Tests/Fixtures/matrices                  # every <pattern>/<config>-<pose>.json below it
//   swift run duo-detect ../foldsmith-evidence/verification/ab/baseline   # every <app>/<screen>-<pose>.json below it
//   swift run duo-detect <dir> --markdown FILE                    # also write the config × pose table
//
// A catalog record carries its own pose; an accessibility snapshot takes the measured pose of its name from
// poses.json, and only when the app's window has that pose's size (otherwise the cell reads "no-rotate": the app
// stayed in the other orientation, so the pose's regions do not apply).
// T7 compares poses: what stays on screen in each inner pose (bars, controls) against the shut phone's; a snapshot taken
// while the app was not in front (it crashed or quit on the fold) is T7 in its pose; and toolbar items stranded on the
// shut phone (T10 there) that are nowhere in an inner pose with a vertical bar are T7 in that pose.
// Prints one line per finding and exits 0; the expectations (reference variants clean, "before" variants flagged)
// live in Tests/DuoPoseTestingTests/MatrixTests.swift so `swift test` is the gate.
import Foundation
import DuoDetectors

var args = Array(CommandLine.arguments.dropFirst())
var markdown: String?
if let i = args.firstIndex(of: "--markdown"), i + 1 < args.count { markdown = args[i + 1]; args.removeSubrange(i...(i + 1)) }
guard !args.isEmpty else {
    FileHandle.standardError.write(Data("usage: duo-detect <dir|file.json>... [--markdown out.md]\n".utf8)); exit(2)
}

var files: [URL] = []
for a in args {
    let url = URL(fileURLWithPath: a)
    var isDir: ObjCBool = false
    FileManager.default.fileExists(atPath: url.path, isDirectory: &isDir)
    if isDir.boolValue, let e = FileManager.default.enumerator(at: url, includingPropertiesForKeys: nil) {
        files += e.compactMap { $0 as? URL }.filter { $0.pathExtension == "json" }
    } else {
        files.append(url)
    }
}
files.sort { $0.path < $1.path }

let measured = Dictionary(uniqueKeysWithValues: ((try? Pose.load()) ?? []).map { ($0.name, $0) })

// config ("pattern/variant[-sheet]" or "app/screen") → pose → classes
var table: [String: [String: [String]]] = [:]
// config → pose → what stays on screen, for T7
var bars: [String: [String: Set<String>]] = [:]
// config → the toolbar items stranded on the shut phone; config → pose → every name on screen where there is a vertical bar
var strandedBarItems: [String: Set<String>] = [:]
var namesBesideVerticalBar: [String: [String: Set<String>]] = [:]
var total = 0
for file in files {
    guard let pose = CatalogSnapshot.poseName(of: file), let data = try? Data(contentsOf: file) else { continue }
    let stem = file.deletingPathExtension().lastPathComponent
    let elements: [Element], posed: Pose, config: String
    var isSnapshot = false
    do {
        if AccessibilitySnapshot.matches(data) {
            let snapshot = try JSONDecoder().decode(AccessibilitySnapshot.self, from: data)
            config = "\(file.deletingLastPathComponent().lastPathComponent)/\(stem.dropLast(pose.count + 1))"
            guard let p = measured[pose] else { continue }
            if let f = StateLossOnFold.notInFront(appState: snapshot.appState, pose: pose) {
                table[config, default: [:]][pose] = [f.classId]
                print("\(config) \(pose): \(f.classId) \(f.detail)")
                total += 1
                continue
            }
            let w = snapshot.windowSize
            guard abs(w.width - p.window.width) < 1, abs(w.height - p.window.height) < 1 else {
                table[config, default: [:]][pose] = ["no-rotate"]
                print("\(config) \(pose): window \(Int(w.width))×\(Int(w.height)), not the pose's \(Int(p.window.width))×\(Int(p.window.height)); detectors skipped")
                continue
            }
            (elements, posed) = (snapshot.detectorElements, p)
            bars[config, default: [:]][pose] = snapshot.screenNames
            isSnapshot = true
        } else {
            let snapshot = try JSONDecoder().decode(CatalogSnapshot.self, from: data)
            config = "\(snapshot.pattern)/\(stem.dropLast(pose.count + 1))"
            (elements, posed) = (snapshot.detectorElements, snapshot.pose(named: pose))
        }
    } catch { print("\(file.lastPathComponent): unreadable (\(error))"); continue }
    let findings = Detectors.runAll(elements: elements, pose: posed)
    if isSnapshot, pose == "closed" {
        strandedBarItems[config] = StateLossOnFold.strandedNames(findings)
    }
    if isSnapshot, posed.toolbarVerticalEdge != nil {
        namesBesideVerticalBar[config, default: [:]][pose] = StateLossOnFold.names(elements)
    }
    table[config, default: [:]][pose] = Array(Set(findings.map(\.classId))).sorted()
    for f in findings { print("\(config) \(pose): \(f.classId) \(f.detail)") }
    total += findings.count
}
for config in bars.keys.sorted() {
    guard let closed = bars[config]?["closed"] else { continue }
    let lost = StateLossOnFold.lostBarItems(stranded: strandedBarItems[config] ?? [], inner: namesBesideVerticalBar[config] ?? [:])
    for f in StateLossOnFold.run(closed: closed, inner: bars[config] ?? [:]) + lost {
        table[config, default: [:]][f.pose] = Array(Set((table[config]?[f.pose] ?? []) + [f.classId])).sorted()
        print("\(config) \(f.pose): \(f.classId) \(f.detail)")
        total += 1
    }
}
print("\(files.count) captures, \(total) findings")

if let markdown {
    let poses = CatalogSnapshot.poseNames
    var out = "| config | " + poses.joined(separator: " | ") + " |\n|---|" + String(repeating: "---|", count: poses.count) + "\n"
    for config in table.keys.sorted() {
        let cells = poses.map { p in table[config]?[p].map { $0.isEmpty ? "·" : $0.joined(separator: " ") } ?? "n/a" }
        out += "| \(config) | " + cells.joined(separator: " | ") + " |\n"
    }
    try out.write(toFile: markdown, atomically: true, encoding: .utf8)
}
