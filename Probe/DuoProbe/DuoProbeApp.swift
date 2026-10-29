import SwiftUI

/// DuoProbe — logs every layout-relevant fact the system reports, per pose, as JSON.
/// Output: <app container>/Documents/metrics.jsonl (one sample per geometry change) and the same lines on stdout.
/// Pull with: xcrun simctl get_app_container <UDID> dev.enchiridion.duopatterns.probe data
///
/// Launch arguments:
///   -label <name>   tag every sample with a pose label you set from the driving script (e.g. "closed", "book", "laptop", "flat", "flat-upright")
///   -overlay 0|1    draw the region/safe-area overlay (default 1)
@main
struct DuoProbeApp: App {
    var body: some Scene {
        WindowGroup {
            NavigationStack {
                ProbeRoot()
                    .toolbar {
                        // Standard items so the probe also records real vertical-bar behaviour.
                        ToolbarItem(placement: .topBarPinnedTrailing) { Button("Done") {} }
                        ToolbarItem { Button("Share", systemImage: "square.and.arrow.up") {} }
                        ToolbarItem { Button("Filter", systemImage: "line.3.horizontal.decrease.circle") {} }
                        ToolbarItem(placement: .bottomBar) { Button("Compose", systemImage: "square.and.pencil") {} }
                    }
                    .navigationTitle("DuoProbe")
            }
        }
    }
}
