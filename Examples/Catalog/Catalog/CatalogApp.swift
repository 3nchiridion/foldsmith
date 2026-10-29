import SwiftUI

/// The pattern catalog. Launch arguments pick the screen, so a script can capture each one in every pose:
///   -pattern split|grid|columns|arrangement   which pattern (default split)
///   -variant aligned|<before>       the reference implementation, or a "before" variant that reproduces a corpus
///                                   defect: split → system | fixed; grid → naive; columns → single; arrangement →
///                                   inline (arrangement also has overlay, a second reference). split also has
///                                   three and three-list: three levels in two panes (P1 "Three levels")
///   -sheet 1                        (split) present the New Item sheet at launch
@main
struct CatalogApp: App {
    var body: some Scene {
        WindowGroup {
            CatalogRoot()
        }
    }
}

enum Launch {
    static func value(_ name: String) -> String? {
        let args = CommandLine.arguments
        guard let i = args.firstIndex(of: name), i + 1 < args.count else { return nil }
        return args[i + 1]
    }
    static let pattern = value("-pattern") ?? "split"
    static let variant = value("-variant") ?? "aligned"
    static let sheet = value("-sheet") == "1"
}

struct CatalogRoot: View {
    var body: some View {
        content
            .background { RegionRecorder() }
            .onAppear {
                Tracker.shared.pattern = Launch.pattern
                Tracker.shared.variant = Launch.variant
            }
    }

    @ViewBuilder private var content: some View {
        switch Launch.pattern {
        case "grid": GridDemo(variant: Launch.variant)
        case "columns": ColumnsDemo(variant: Launch.variant)
        case "arrangement": ArrangementDemo(variant: Launch.variant)
        default: SplitDemo(variant: Launch.variant, showSheetAtLaunch: Launch.sheet)
        }
    }
}
