// ReflowingColumns.swift — Foldsmith P2 "Reflowing columns" (patterns/reflowing-columns.md)
//
// Copy this one file into an app; it depends on nothing in Foldsmith. It lays text out with TextKit, so it needs
// UIKit (iOS, iPadOS, Mac Catalyst, visionOS); it reads the fold only on iOS 27.1 and later.
//
// Continuous reading content (an article, a document). Wherever the window is wider than tall and has a vertical
// division, active (book) or not (flat, sideways), the text reflows into two columns, one on each side of the fold,
// and pages sideways one spread at a time; the division is the gutter. Everywhere else it is one column that scrolls,
// including across a horizontal fold (laptop), because scrolling content may cross the hinge and continuous content
// must not be displaced.
//
// Why: on the inner display, use the width with two-column layouts that reflow from one column [tech talk 111466,
// 7:34]; continuously scrolling content must not displace [111463, 2:26]; scrolling content is exempt from hinge
// avoidance [111466, 9:28]. One column across a book fold reads across the spine (Wikipedia's article, taxonomy T5).

import SwiftUI
import UIKit

public struct ReflowingColumns: View {
    private let paragraphs: [String]
    private let margin: CGFloat
    private let onColumns: (([CGRect]) -> Void)?
    @State private var geometry = ColumnGeometry()
    @Environment(\.dynamicTypeSize) private var typeSize

    /// - Parameters:
    ///   - paragraphs: the text, one string per paragraph.
    ///   - margin: outer margin; the fold supplies the gutter between the columns.
    ///   - onColumns: optional; receives the visible columns in window coordinates after each layout.
    public init(paragraphs: [String], margin: CGFloat = 20, onColumns: (([CGRect]) -> Void)? = nil) {
        self.paragraphs = paragraphs
        self.margin = margin
        self.onColumns = onColumns
    }

    public var body: some View {
        Group {
            if geometry.columns.count == 2 {
                PagedColumns(paragraphs: paragraphs, columns: geometry.columns, pageSize: geometry.size, typeSize: typeSize)
            } else {
                ScrollView {
                    Text(paragraphs.joined(separator: "\n\n"))
                        .font(.body)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(margin)
                }
            }
        }
        .background {
            GeometryReader { proxy in
                Color.clear.onGeometryChange(for: ColumnGeometry.self) { [margin] proxy in
                    ColumnGeometry(proxy: proxy, margin: margin)
                } action: { new in
                    geometry = new
                    onColumns?(new.windowColumns)
                }
            }
        }
    }
}

private struct ColumnGeometry: Equatable, Sendable {
    var size: CGSize = .zero
    var columns: [CGRect] = []          // local coordinates, one page
    var windowColumns: [CGRect] = []

    nonisolated init() {}

    nonisolated init(proxy: GeometryProxy, margin: CGFloat) {
        size = proxy.size
        let frame = proxy.frame(in: .global)
        guard size.width > size.height, let fold = Self.verticalFold(in: proxy, margin: margin) else {
            windowColumns = [frame.insetBy(dx: margin, dy: 0)]
            return
        }
        let height = size.height - 2 * margin
        columns = [
            CGRect(x: margin, y: margin, width: fold.minX - margin, height: height),
            CGRect(x: fold.maxX, y: margin, width: size.width - margin - fold.maxX, height: height),
        ]
        windowColumns = columns.map { $0.offsetBy(dx: frame.minX, dy: frame.minY) }
    }

    /// A vertical division clear of the margins, active or not; nil where the SDK has no reserved regions (iOS 27.1;
    /// not yet in Mac Catalyst or visionOS).
    nonisolated static func verticalFold(in proxy: GeometryProxy, margin: CGFloat) -> CGRect? {
        #if os(iOS) && !targetEnvironment(macCatalyst)
        guard #available(iOS 27.1, *) else { return nil }
        return proxy.reservedRegions(kind: .division, options: .includeInactive)
            .map(\.frame)
            .first { $0.height > $0.width && $0.minX > margin && $0.maxX < proxy.size.width - margin }
        #else
        return nil
        #endif
    }
}

/// One TextKit layout manager feeding a chain of column-sized text containers, two per page, paged sideways.
private struct PagedColumns: UIViewRepresentable {
    let paragraphs: [String]
    let columns: [CGRect]
    let pageSize: CGSize
    let typeSize: DynamicTypeSize       // a text size change lays the pages out again

    func makeUIView(context: Context) -> UIScrollView {
        let scroll = UIScrollView()
        scroll.isPagingEnabled = true
        scroll.showsHorizontalScrollIndicator = false
        scroll.alwaysBounceVertical = false
        return scroll
    }

    func updateUIView(_ scroll: UIScrollView, context: Context) {
        let key = Key(paragraphs: paragraphs, columns: columns, pageSize: pageSize, typeSize: typeSize)
        guard context.coordinator.key != key else { return }
        context.coordinator.key = key
        scroll.subviews.forEach { $0.removeFromSuperview() }

        let style = NSMutableParagraphStyle()
        style.paragraphSpacing = UIFont.preferredFont(forTextStyle: .body).lineHeight * 0.6
        let text = NSAttributedString(string: paragraphs.joined(separator: "\n"), attributes: [
            .font: UIFont.preferredFont(forTextStyle: .body),
            .foregroundColor: UIColor.label,
            .paragraphStyle: style,
        ])
        let storage = NSTextStorage(attributedString: text)
        let layout = NSLayoutManager()
        storage.addLayoutManager(layout)
        context.coordinator.storage = storage           // keep TextKit alive with the views

        var page = 0
        laidOut: while page < 500 {
            for column in columns {
                let container = NSTextContainer(size: column.size)
                container.lineFragmentPadding = 0
                layout.addTextContainer(container)
                let view = UITextView(frame: column.offsetBy(dx: CGFloat(page) * pageSize.width, dy: 0),
                                      textContainer: container)
                view.isEditable = false
                view.isScrollEnabled = false
                view.textContainerInset = .zero
                view.backgroundColor = .clear
                scroll.addSubview(view)
                if NSMaxRange(layout.glyphRange(for: container)) >= layout.numberOfGlyphs { break laidOut }
            }
            page += 1
        }
        scroll.contentSize = CGSize(width: CGFloat(page + 1) * pageSize.width, height: pageSize.height)
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    final class Coordinator {
        var key: Key?
        var storage: NSTextStorage?
    }

    struct Key: Equatable {
        var paragraphs: [String]
        var columns: [CGRect]
        var pageSize: CGSize
        var typeSize: DynamicTypeSize
    }
}
