// EvenGrid.swift — duo-kit P3 "Even grid" (patterns/even-grid.md)
//
// Copy this one file into an app; it depends on nothing in duo-kit.
//
// A scrolling grid for peer content (feeds, galleries, dashboard tiles). Wherever the window has a vertical division,
// active (book) or not (flat, sideways), the grid uses an even column count, half on each side, with equal column
// widths so rows line up; the gutter between the halves is the division plus any spare width, so no column straddles
// the fold and each half keeps its own columns. Without a
// vertical division it is an ordinary grid; across a horizontal fold (laptop) it simply scrolls, because scrolling
// content may cross the hinge.
//
// Why: grids prefer an even column count [HIG, Reserved regions]; Fitness widens the gutter at the hinge so each
// container stays in its region [tech talk 111463, 5:12]; an inactive division is still useful for the column count
// [111463, 7:50]; scrolling content is exempt from hinge avoidance [111466, 9:28]. A grid centred in the safe area
// lands off the fold because the vertical bar makes the safe area asymmetric (Wikipedia's Explore, taxonomy T14).

import SwiftUI

public struct EvenGrid<Data: RandomAccessCollection, Cell: View>: View where Data.Element: Identifiable {
    private let data: Data
    private let minCellWidth: CGFloat
    private let spacing: CGFloat
    private let margin: CGFloat
    private let cell: (Data.Element) -> Cell
    private let onColumns: (([ClosedRange<CGFloat>]) -> Void)?
    @State private var geometry = GridGeometry()

    /// - Parameters:
    ///   - minCellWidth: the narrowest a column may be.
    ///   - margin: outer margin on both sides; the fold supplies the gutter between the halves.
    ///   - onColumns: optional; receives the columns' horizontal extents in window coordinates after each layout.
    public init(_ data: Data, minCellWidth: CGFloat = 150, spacing: CGFloat = 12, margin: CGFloat = 16,
                onColumns: (([ClosedRange<CGFloat>]) -> Void)? = nil,
                @ViewBuilder cell: @escaping (Data.Element) -> Cell) {
        self.data = data
        self.minCellWidth = minCellWidth
        self.spacing = spacing
        self.margin = margin
        self.onColumns = onColumns
        self.cell = cell
    }

    public var body: some View {
        ScrollView {
            LazyVGrid(columns: geometry.items, alignment: .leading, spacing: spacing) {
                ForEach(data) { cell($0) }
            }
            .padding(.horizontal, margin)
            .padding(.vertical, spacing)
        }
        .background {
            GeometryReader { proxy in
                Color.clear.onGeometryChange(for: GridGeometry.self) { [minCellWidth, spacing, margin] proxy in
                    GridGeometry(proxy: proxy, minCellWidth: minCellWidth, spacing: spacing, margin: margin)
                } action: { new in
                    geometry = new
                    onColumns?(new.windowExtents)
                }
            }
        }
    }
}

/// Column widths and the spacing after each, plus where the columns land in the window.
private struct GridGeometry: Equatable, Sendable {
    struct Column: Equatable, Sendable { var width: CGFloat?; var spacingAfter: CGFloat }
    var columns: [Column] = [Column(width: nil, spacingAfter: 0)]
    var windowExtents: [ClosedRange<CGFloat>] = []

    var items: [GridItem] {
        columns.map { c in GridItem(c.width.map { .fixed($0) } ?? .flexible(), spacing: c.spacingAfter) }
    }

    nonisolated init() {}

    nonisolated init(proxy: GeometryProxy, minCellWidth: CGFloat, spacing: CGFloat, margin: CGFloat) {
        let width = proxy.size.width
        func fit(_ available: CGFloat) -> Int { max(1, Int((available + spacing) / (minCellWidth + spacing))) }

        var fold: CGRect?
        #if os(iOS) && !targetEnvironment(macCatalyst)   // reserved regions: iOS 27.1 (not yet in Catalyst, visionOS, macOS)
        if #available(iOS 27.1, *) {
            // Active or inactive: a flat, sideways inner display still splits the column count at the fold.
            fold = proxy.reservedRegions(kind: .division, options: .includeInactive)
                .map(\.frame)
                .first { $0.height > $0.width && $0.minX > margin && $0.maxX < width - margin }
        }
        #endif

        var local: [ClosedRange<CGFloat>] = []
        if let fold {
            let leading = fold.minX - margin
            let trailing = width - margin - fold.maxX
            let perHalf = min(fit(leading), fit(trailing))
            // Equal columns on both sides, so rows line up across the fold. The narrower half (the vertical bar sits
            // on the trailing edge in book) sets the width; the outer margins stay, and the spare width goes into the
            // gutter at the hinge. (Fitness widens its leading columns instead: verification/oracle/even-grid.md.)
            let columnWidth = min(leading, trailing) / CGFloat(perHalf) - spacing * CGFloat(perHalf - 1) / CGFloat(perHalf)
            let leadingEnd = margin + CGFloat(perHalf) * columnWidth + CGFloat(perHalf - 1) * spacing
            let gutter = fold.maxX - leadingEnd
            columns = (0..<perHalf).map { i in
                Column(width: columnWidth, spacingAfter: i == perHalf - 1 ? gutter : spacing)
            } + (0..<perHalf).map { _ in Column(width: columnWidth, spacingAfter: spacing) }
            var x = margin
            for (i, c) in columns.enumerated() {
                local.append(x...(x + (c.width ?? 0)))
                x += (c.width ?? 0) + (i < columns.count - 1 ? c.spacingAfter : 0)
            }
        } else {
            var count = fit(width - 2 * margin)
            // The inner display keeps an even count even without a vertical fold [HIG, Reserved regions].
            if proxy.size.width >= 600, count > 1, count % 2 == 1 { count -= 1 }
            columns = Array(repeating: Column(width: nil, spacingAfter: spacing), count: count)
            let w = (width - 2 * margin - CGFloat(count - 1) * spacing) / CGFloat(count)
            local = (0..<count).map { i in
                let x = margin + CGFloat(i) * (w + spacing)
                return x...(x + w)
            }
        }
        let origin = proxy.frame(in: .global).minX
        windowExtents = local.map { (origin + $0.lowerBound)...(origin + $0.upperBound) }
    }
}
