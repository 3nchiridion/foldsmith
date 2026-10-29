// FoldAlignedTiledSplit.swift — duo-kit P1 "Fold-aligned split", two panes held upright too
// (patterns/fold-aligned-split.md, "Upright")
//
// Copy this file with FoldAlignedSplit.swift: it uses that file's split and its `duoBookFoldIsActive` for sheets.
//
// FoldAlignedSplit leaves the split to NavigationSplitView, which overlays its sidebar when the open iPhone Duo stands
// upright (laptop, tent, flat upright: a 669 pt window): the detail alone, the sidebar one tap away. With three levels
// that detail is empty at the top level (taxonomy T7). This type keeps both panes there, as Settings does
// [raw/apple-apps/settings/laptop].
//
// Upright on the inner display there is no vertical bar, and there it shows a UIKit two-column UISplitViewController
// that tiles and lets the detail be as narrow as 320 pt (`minimumSecondaryColumnWidth`, iOS 26), with no column width
// set. Everywhere else it is FoldAlignedSplit: on the outer display and folded like a book or lying flat sideways the
// system draws a vertical bar, and it does so only for bars that SwiftUI's own navigation containers provide. A UIKit
// split embedded in a SwiftUI view keeps horizontal bars there (measured in the catalog: the back button stayed in a
// top bar on the outer display), because the system finds the vertical bar from the window's root view controller
// down (`childForPreferredVerticalBarBehavior`) and SwiftUI's root does not hand it on. On an iPhone, iPad or anything
// without a fold it is FoldAlignedSplit, unchanged.
//
// The cost: moving between an upright inner pose and one with a vertical bar replaces one container with the other,
// so the views in the sidebar and the detail are built again. Keep what must survive the fold where the caller owns
// it: the selection (passed here) and any navigation path in the sidebar. Scroll positions start over.
//
// The sidebar and the detail are SwiftUI views. In the UIKit split each sits in a hosting controller in its own column,
// and the column's bar is UIKit's, filled from `.navigationTitle` and `.toolbar`; a sidebar with a NavigationStack of
// its own (three levels: a sidebar, then a list) passes `sidebarNavigates: true` and keeps the stack's bars instead.
// The fold is read from reserved regions, never from the device, idiom or orientation. Where the SDK has none (Xcode
// 27.1's Mac Catalyst, visionOS and macOS SDKs) this type is FoldAlignedSplit and the UIKit part is not compiled.

import SwiftUI
#if os(iOS) && !targetEnvironment(macCatalyst)
import UIKit
#endif

/// A two-column split that keeps the sidebar beside the detail on the inner display, upright included.
public struct FoldAlignedTiledSplit<Selection: Hashable, Sidebar: View, Detail: View>: View {
    @Binding private var selection: Selection?
    private let sidebarNavigates: Bool
    private let sidebar: Sidebar
    private let detail: Detail

    public init(selection: Binding<Selection?>, sidebarNavigates: Bool = false,
                @ViewBuilder sidebar: () -> Sidebar, @ViewBuilder detail: () -> Detail) {
        _selection = selection
        self.sidebarNavigates = sidebarNavigates
        self.sidebar = sidebar()
        self.detail = detail()
    }

    public var body: some View {
        #if os(iOS) && !targetEnvironment(macCatalyst)
        if #available(iOS 27.1, *) {
            FoldAwareTiling(selection: $selection, sidebarNavigates: sidebarNavigates, sidebar: sidebar, detail: detail)
        } else {
            FoldAlignedSplit { sidebar } detail: { detail }
        }
        #else
        FoldAlignedSplit { sidebar } detail: { detail }
        #endif
    }
}

#if os(iOS) && !targetEnvironment(macCatalyst)

/// Picks the container: the UIKit tiled split where the window has a fold and no vertical bar, FoldAlignedSplit elsewhere.
@available(iOS 27.1, *)
private struct FoldAwareTiling<Selection: Hashable, Sidebar: View, Detail: View>: View {
    @Binding var selection: Selection?
    let sidebarNavigates: Bool
    let sidebar: Sidebar
    let detail: Detail
    @Environment(\.toolbarVerticalEdge) private var verticalEdge
    @State private var hasFold = false

    var body: some View {
        Group {
            if hasFold && verticalEdge == nil {
                TiledSplit(selection: $selection, sidebarNavigates: sidebarNavigates, sidebar: sidebar, detail: detail)
            } else {
                FoldAlignedSplit { sidebar } detail: { detail }
            }
        }
        .background {
            GeometryReader { proxy in
                Color.clear.onGeometryChange(for: Bool.self) {
                    !$0.reservedRegions(kind: .division, options: .includeInactive).isEmpty
                } action: { hasFold = $0 }
            }
            .ignoresSafeArea()
        }
    }
}

/// The UIKit split, upright on the inner display.
private struct TiledSplit<Selection: Hashable, Sidebar: View, Detail: View>: UIViewControllerRepresentable {
    @Binding var selection: Selection?
    let sidebarNavigates: Bool
    let sidebar: Sidebar
    let detail: Detail

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIViewController(context: Context) -> TiledSplitViewController {
        let split = TiledSplitViewController(style: .doubleColumn)
        let coordinator = context.coordinator
        coordinator.split = split
        split.preferredSplitBehavior = .tile
        split.preferredDisplayMode = .oneBesideSecondary
        split.delegate = coordinator
        split.setViewController(coordinator.sidebarHost, for: .primary)
        split.setViewController(coordinator.detailHost, for: .secondary)
        coordinator.sidebarHost.navigationController?.delegate = coordinator
        split.foldDidChange = { [weak coordinator] in coordinator?.render() }
        return split
    }

    func updateUIViewController(_ split: TiledSplitViewController, context: Context) {
        let coordinator = context.coordinator
        coordinator.update(self)
        // Should the split ever collapse, a selection pushes the detail, as a list row in a navigation stack would.
        if split.isCollapsed, selection != nil, selection != coordinator.lastSelection {
            split.show(.secondary)
        }
        coordinator.lastSelection = selection
    }

    @MainActor final class Coordinator: NSObject, UISplitViewControllerDelegate, UINavigationControllerDelegate {
        weak var split: TiledSplitViewController?
        let sidebarHost = UIHostingController(rootView: AnyView(EmptyView()))
        let detailHost = UIHostingController(rootView: AnyView(EmptyView()))
        var lastSelection: Selection?
        private var parent: TiledSplit?

        func update(_ parent: TiledSplit) {
            self.parent = parent
            render()
        }

        /// The SwiftUI views into their columns, told whether the book fold is active (for sheets).
        func render() {
            guard let parent else { return }
            let foldIsActive = split?.isBookFoldActive ?? false
            sidebarHost.rootView = AnyView(parent.sidebar.environment(\.duoBookFoldIsActive, foldIsActive))
            detailHost.rootView = AnyView(parent.detail.environment(\.duoBookFoldIsActive, foldIsActive))
            updateBars()
        }

        /// A navigating sidebar draws its own bars; the detail, and a plain sidebar, use UIKit's.
        private func updateBars() {
            guard let navigation = sidebarHost.navigationController else { return }
            let hidden = (parent?.sidebarNavigates ?? false) && navigation.topViewController === sidebarHost
            if navigation.isNavigationBarHidden != hidden { navigation.setNavigationBarHidden(hidden, animated: false) }
        }

        func splitViewController(_ svc: UISplitViewController,
                                 topColumnForCollapsingToProposedTopColumn proposedTopColumn: UISplitViewController.Column)
            -> UISplitViewController.Column {
            parent?.selection != nil ? .secondary : .primary
        }

        func splitViewControllerDidCollapse(_ svc: UISplitViewController) { updateBars() }
        func splitViewControllerDidExpand(_ svc: UISplitViewController) { updateBars() }

        func navigationController(_ navigationController: UINavigationController, willShow viewController: UIViewController,
                                  animated: Bool) {
            let hidden = (parent?.sidebarNavigates ?? false) && viewController === sidebarHost
            navigationController.setNavigationBarHidden(hidden, animated: animated)
        }

        /// Back to the sidebar in a collapsed split: nothing is selected any more.
        func navigationController(_ navigationController: UINavigationController, didShow viewController: UIViewController,
                                  animated: Bool) {
            guard split?.isCollapsed == true, viewController === sidebarHost, parent?.selection != nil else { return }
            lastSelection = nil
            parent?.selection = nil
        }
    }
}

/// The split view controller under the tiled split: reads the reserved regions after every layout, and the hinge says
/// when to look again (UIKit has no callback when the regions change).
private final class TiledSplitViewController: UISplitViewController {
    /// Narrowest the detail may be on a display with a fold: two panes fit the 669 pt upright window.
    private static let minimumDetailWidthOnFoldingDisplay: CGFloat = 320

    var foldDidChange: (() -> Void)?
    private(set) var isBookFoldActive = false
    private var hasFold: Bool?

    override func viewDidLoad() {
        super.viewDidLoad()
        if #available(iOS 27.1, *) {
            view.addInteraction(UIHingeInteraction { [weak self] _, _ in self?.view.setNeedsLayout() })
        }
    }

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        guard #available(iOS 27.1, *) else { return }
        let fold = !view.reservedRegions(kind: .division, options: .includeInactive).isEmpty
        if fold != hasFold {
            hasFold = fold
            if #available(iOS 26.0, *) {
                minimumSecondaryColumnWidth = fold ? Self.minimumDetailWidthOnFoldingDisplay : UISplitViewController.automaticDimension
            }
        }
        let book = view.reservedRegions(kind: .division).contains { $0.isActive && $0.frame.height > $0.frame.width }
        if book != isBookFoldActive {
            isBookFoldActive = book
            foldDidChange?()
        }
    }
}
#endif
