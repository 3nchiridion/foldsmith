// FoldAlignedSplit.swift — duo-kit P1 "Fold-aligned split" (patterns/fold-aligned-split.md)
//
// Copy this one file into an app; it depends on nothing in duo-kit.
//
// One pane on the outer display and in Split View; two panes on the inner display held sideways. While the iPhone Duo
// is folded like a book, the sidebar ends where the fold begins and the detail starts where it ends, so neither pane
// straddles it. Sheets presented from inside move to the trailing half while the fold is active.
//
// The split itself is the system's: a NavigationSplitView with no column width set already keeps both panes clear of
// the fold (measured on the 27.1 simulator: sidebar 0–455.7 pt, detail from 495.5 pt, the fold's frame 455.5–495.5),
// as Settings does [raw/apple-apps/settings/book]. Setting any sidebar width turns that off: a fixed 320 pt sidebar
// leaves the detail across the fold (NetNewsWire, taxonomy T14), and even a width equal to the fold's edge starts the
// detail inside the fold. So this type sets none, on purpose. Switching a width on and off with the pose is no way
// out either: the conditional rebuilds the sidebar view on every fold (seen in the catalog), which puts its state at
// risk (T7).
//
// Held upright (laptop, tent, flat upright: 669 pt wide) the split shows the detail with the sidebar one tap away, the
// system's choice for a window taller than wide. Settings, a UIKit split, keeps both panes there
// [raw/apple-apps/settings/laptop]; NavigationSplitView overlays its sidebar at that width even with the balanced style,
// every column visible and a 250 pt sidebar (measured in the catalog), and forcing it brings the sidebar up over the
// detail at launch. So this type leaves that alone too; FoldAlignedTiledSplit.swift keeps both panes there.
//
// What it adds is the sheet rule: the system places sheets on the leading half, ending inside the fold's margin (T15);
// Apple sends alerts to the trailing side in book [tech talk 111463, 4:00]. `foldAwareSheetPlacement()` does that.
// It reads `duoBookFoldIsActive`, which FoldAlignedSplit sets for everything inside it. An app whose split is another
// system container (a TabView sidebar, IceCubesApp [verification/runs/IceCubesApp]) puts `readsBookFold()` once on the
// window's root instead.
//
// The fold is read only where the SDK has reserved regions: iOS 27.1 and later. Xcode 27.1's Mac Catalyst, visionOS and
// macOS SDKs do not have them, and `PresentationPlacement.trailing` is unavailable on visionOS and macOS, so there the
// file compiles to a plain NavigationSplitView and both modifiers leave the view as it is.

import SwiftUI

public extension EnvironmentValues {
    /// True while a vertical division is active around this view: the device is folded like a book.
    @Entry var duoBookFoldIsActive: Bool = false
}

/// A `NavigationSplitView` that leaves the fold to the system and tells presentations whether the book fold is active.
public struct FoldAlignedSplit<Sidebar: View, Detail: View>: View {
    private let sidebar: Sidebar
    private let detail: Detail

    public init(@ViewBuilder sidebar: () -> Sidebar, @ViewBuilder detail: () -> Detail) {
        self.sidebar = sidebar()
        self.detail = detail()
    }

    public var body: some View {
        // No navigationSplitViewColumnWidth here: any fixed width stops the system from splitting at the fold.
        NavigationSplitView {
            sidebar
        } detail: {
            detail
        }
        .readsBookFold()
    }
}

public extension View {
    /// Sets `duoBookFoldIsActive` for this view and all it presents. FoldAlignedSplit applies it to itself; an app
    /// whose split is another container applies it once, on the window's root view.
    func readsBookFold() -> some View { modifier(BookFoldReader()) }

    /// Apply to a sheet's content: trailing half while the book fold is active, the system's placement otherwise.
    @ViewBuilder func foldAwareSheetPlacement() -> some View {
        #if os(iOS) && !targetEnvironment(macCatalyst)
        if #available(iOS 27.1, *) { modifier(FoldAwareSheetPlacement()) } else { self }
        #else
        self
        #endif
    }
}

private struct BookFoldReader: ViewModifier {
    /// The active vertical fold in window coordinates, or nil.
    @State private var fold: CGRect?

    func body(content: Content) -> some View {
        content
            .environment(\.duoBookFoldIsActive, fold != nil)
            .background {
                GeometryReader { proxy in
                    Color.clear.onGeometryChange(for: CGRect?.self, of: activeVerticalFold) { fold = $0 }
                }
                .ignoresSafeArea()
            }
    }
}

/// The first active division that runs top to bottom, in the proxy's coordinates (the window, here).
nonisolated private func activeVerticalFold(in proxy: GeometryProxy) -> CGRect? {
    #if os(iOS) && !targetEnvironment(macCatalyst)
    guard #available(iOS 27.1, *) else { return nil }
    return proxy.reservedRegions(kind: .division)      // active regions only
        .map(\.frame)
        .first { $0.height > $0.width }
    #else
    return nil
    #endif
}

#if os(iOS) && !targetEnvironment(macCatalyst)
@available(iOS 27.1, *)
private struct FoldAwareSheetPlacement: ViewModifier {
    @Environment(\.duoBookFoldIsActive) private var foldIsActive
    func body(content: Content) -> some View {
        content.presentationPlacement(foldIsActive ? .trailing : .automatic)
    }
}
#endif
