// Arrangement.swift — Foldsmith P4 "Arrangement" (patterns/arrangement.md)
//
// Copy this one file into an app; it depends on nothing in Foldsmith.
//
// Two views where one supports the other (a player and its transcript, an article and its contents, a document and
// its inspector), laid out by the system's ArrangementView: as a split, side by side when the window is wider than
// tall and one above the other when it is taller (or the primary alone where the system cannot split, as on the
// turned cover), the boundary moved onto the fold; or as an overlay, the primary over the secondary until the phone is
// part folded, when each takes a side. The system decides from the window's size,
// shape and reserved regions, so the app writes no per-pose layout.
//
// Open flat, the system's split halves the window and the secondary runs across the inactive fold; folding then moves
// the boundary. So while the fold is inactive the split is told where the fold is: the primary ends at the division's
// near edge and the secondary's content starts at its far edge, where both will be once the phone is folded. An
// inactive division is still useful for layout [tech talk 111463, 7:50]; Podcasts' transcript starts past it when
// flat (111463, 9:53).
//
// Why: arrangements are the layout container between navigation and content [111463, 9:20]; split for two views
// neither of which should be obscured, overlay for a foreground over scrollable content [111463, 14:39]; keep
// navigation containers outside and never put one inside a List or ScrollView [111463, 16:09]. A plain HStack keeps
// its boundary where it was, so the wider view straddles the fold in book (taxonomy T14).
//
// Before iOS 27.1 it is the layout an app had: a stack by shape for a split, a ZStack for an overlay.

import SwiftUI

public enum ArrangementStyle: Sendable {
    /// Side by side when wider than tall, one above the other when taller, or the primary alone where the system cannot
    /// split (the turned cover), so make the secondary reachable from the primary; for two views neither may cover.
    case split
    /// The primary over the secondary, side by side when part folded; for controls over scrollable content.
    case overlay
}

public struct Arrangement<Primary: View, Secondary: View>: View {
    private let style: ArrangementStyle
    private let primary: Primary
    private let secondary: Secondary
    @State private var flat = FlatFold()

    public init(_ style: ArrangementStyle = .split,
                @ViewBuilder primary: () -> Primary, @ViewBuilder secondary: () -> Secondary) {
        self.style = style
        self.primary = primary()
        self.secondary = secondary()
    }

    public var body: some View {
        #if os(iOS) && !targetEnvironment(macCatalyst)   // ArrangementView: iOS 27.1 (not yet in Catalyst, visionOS, macOS)
        if #available(iOS 27.1, *) {
            arranged
        } else {
            fallback
        }
        #else
        fallback
        #endif
    }

    #if os(iOS) && !targetEnvironment(macCatalyst)
    /// One ArrangementView for every pose, so the views keep their identity and state from pose to pose.
    @available(iOS 27.1, *)
    @ViewBuilder private var arranged: some View {
        switch style {
        case .split:
            ArrangementView {
                primary.splitArrangementLayoutRatio(idealHorizontal: flat.horizontal, idealVertical: flat.vertical)
            } secondary: {
                secondary.padding(.leading, flat.leading).padding(.top, flat.top)
            }
            .arrangementViewStyle(.split)
            .background {
                GeometryReader { proxy in
                    Color.clear.onGeometryChange(for: FlatFold.self) { FlatFold($0) } action: { flat = $0 }
                }
            }
        case .overlay:
            // Apple draws an overlay's primary smaller and at the foot [HIG, image alt text]; left to itself the
            // system set it at its own size in the top leading corner of its region, so give it the region and align
            // it there. A SwiftUI frame adds no hit area; that the secondary still scrolls beneath it was not tested.
            ArrangementView {
                primary.frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottom)
            } secondary: { secondary }
            .arrangementViewStyle(.overlay)
        }
    }
    #endif

    /// The layout an app had: a stack by shape, its views kept across a change of shape (AnyLayout), or a ZStack.
    @ViewBuilder private var fallback: some View {
        switch style {
        case .split:
            GeometryReader { proxy in
                let layout = proxy.size.width > proxy.size.height
                    ? AnyLayout(HStackLayout(spacing: 0)) : AnyLayout(VStackLayout(spacing: 0))
                layout { primary; secondary }
            }
        case .overlay:
            ZStack(alignment: .bottom) { secondary; primary }
        }
    }
}

/// Where an inactive division would put the split: the primary's share of the width (side by side) or the height
/// (one above the other), and the secondary's inset past the boundary. Nil and zero while the fold is active, when the
/// system puts the boundary on it, and where there is no fold (the cover).
private struct FlatFold: Equatable, Sendable {
    var horizontal: CGFloat?
    var vertical: CGFloat?
    var leading: CGFloat = 0
    var top: CGFloat = 0

    nonisolated init() {}

    nonisolated init(_ proxy: GeometryProxy) {
        #if os(iOS) && !targetEnvironment(macCatalyst)   // reserved regions: iOS 27.1 (not yet in Catalyst, visionOS, macOS)
        if #available(iOS 27.1, *) {
            let size = proxy.size
            for region in proxy.reservedRegions(kind: .division, options: .includeInactive) where !region.isActive {
                let d = region.frame
                if d.height > d.width, d.minX > 0, d.maxX < size.width {
                    horizontal = d.minX / size.width
                    leading = d.width
                } else if d.width > d.height, d.minY > 0, d.maxY < size.height {
                    vertical = d.minY / size.height
                    top = d.height
                }
            }
        }
        #endif
    }
}
