import SwiftUI

// MARK: - P1 Fold-aligned split

struct Article: Identifiable, Hashable {
    let id: Int
    let title: String
    let body: String
}

let articles: [Article] = (0..<24).map { i in
    let p = SampleText.paragraphs
    return Article(id: i, title: SampleText.titles[i % SampleText.titles.count],
                   body: [p[i % p.count], p[(i + 3) % p.count], p[(i + 7) % p.count]].joined(separator: "\n\n"))
}

/// variants: aligned (FoldAlignedSplit), system (plain NavigationSplitView), fixed (a fixed 320 pt sidebar, the shape
/// NetNewsWire uses: SceneCoordinator.swift sets minimum/maximum/preferred column widths), three and three-list (three
/// levels in two panes, `ThreeLevelDemo`), and tiled, tiled-three, tiled-three-list: the same on
/// `FoldAlignedTiledSplit`, which keeps both panes upright.
struct SplitDemo: View {
    let variant: String
    @State private var selection: Article.ID? = 0
    @State private var showSheet: Bool

    init(variant: String, showSheetAtLaunch: Bool) {
        self.variant = variant
        _showSheet = State(initialValue: showSheetAtLaunch)
    }

    var body: some View {
        switch variant {
        case "fixed":
            NavigationSplitView { sidebar.navigationSplitViewColumnWidth(320) } detail: { detail }
        case "system":
            NavigationSplitView { sidebar } detail: { detail }
        case "three", "three-list":
            ThreeLevelDemo(startInList: variant == "three-list", tiled: false)
        case "tiled-three", "tiled-three-list":
            ThreeLevelDemo(startInList: variant == "tiled-three-list", tiled: true)
        case "tiled":
            FoldAlignedTiledSplit(selection: $selection) { sidebar } detail: { detail }
        default:
            FoldAlignedSplit { sidebar } detail: { detail }
        }
    }

    private var sidebar: some View {
        List(articles, selection: $selection) { article in
            Text(article.title).tag(article.id)
        }
        .navigationTitle("Library")
        .toolbar {
            ToolbarItem { Button("New", systemImage: "square.and.pencil") { showSheet = true } }
        }
        .sheet(isPresented: $showSheet) { NewItemSheet(aligned: variant == "aligned" || variant == "tiled") }
        .duoTracked("sidebar", role: "pane")
    }

    @ViewBuilder private var detail: some View {
        let article = articles.first { $0.id == selection } ?? articles[0]
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text(article.title).font(.title2.bold())
                Text(article.body)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
        }
        .navigationTitle(article.title)
        .navigationBarTitleDisplayMode(.inline)
        .duoTracked("detail", role: "pane")
    }
}

struct NewItemSheet: View {
    let aligned: Bool
    @State private var title = ""
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        if aligned { form.foldAwareSheetPlacement() } else { form }
    }

    private var form: some View {
        NavigationStack {
            Form {
                Section("Title") { TextField("Untitled", text: $title) }
                Section("Collection") { Text("Reading list") }
                Section { Text("New items are added to the top of the library.").foregroundStyle(.secondary) }
            }
            .navigationTitle("New Item")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                // Symbols, not text: text-only items stay horizontal where the bar goes vertical (T10).
                ToolbarItem(placement: .cancellationAction) { Button("Cancel", systemImage: "xmark") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) { Button("Add", systemImage: "checkmark") { dismiss() } }
            }
        }
        .duoTracked("sheet", role: "sheet")
    }
}

struct Collection: Identifiable, Hashable {
    let id: Int
    let name: String
}

let collections: [Collection] = ["Reading list", "Science", "History", "Design", "Travel", "Food"].enumerated()
    .map { Collection(id: $0.offset, name: $0.element) }

/// Three levels (collections → articles → article) in two panes, the owner's rule on the P1 page ("Three levels"):
/// a two-column split whose sidebar column holds a NavigationStack. Unfolded at the top level the collections sit beside
/// the detail; a picked collection pushes its articles into the sidebar's place. variant three opens at the
/// collections with no article; three-list with the first collection and its first article picked. `tiled` puts the
/// same columns in `FoldAlignedTiledSplit`.
struct ThreeLevelDemo: View {
    let tiled: Bool
    @State private var path: [Collection.ID]
    @State private var selection: Article.ID?

    init(startInList: Bool, tiled: Bool) {
        self.tiled = tiled
        _path = State(initialValue: startInList ? [0] : [])
        _selection = State(initialValue: startInList ? 0 : nil)
    }

    var body: some View {
        if tiled {
            FoldAlignedTiledSplit(selection: $selection, sidebarNavigates: true) { sidebar } detail: { detailPane }
        } else {
            FoldAlignedSplit { sidebar } detail: { detailPane }
        }
    }

    private var detailPane: some View {
        detail.duoTracked("detail", role: "pane")
    }

    private var sidebar: some View {
            NavigationStack(path: $path) {
                List(collections) { collection in
                    NavigationLink(collection.name, value: collection.id)
                }
                .navigationTitle("Collections")
                .navigationDestination(for: Collection.ID.self) { id in
                    List(articles.filter { $0.id % collections.count == id }, selection: $selection) { article in
                        Text(article.title).tag(article.id)
                    }
                    .navigationTitle(collections[id].name)
                }
            }
            .duoTracked("sidebar", role: "pane")
    }

    @ViewBuilder private var detail: some View {
        if let article = articles.first(where: { $0.id == selection }) {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    Text(article.title).font(.title2.bold())
                    Text(article.body)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
            }
            .navigationTitle(article.title)
            .navigationBarTitleDisplayMode(.inline)
        } else {
            // An empty detail's placeholder sits high in its pane: centred, it lands on the fold held upright (T1).
            Text("No selection")
                .foregroundStyle(.secondary)
                .duoTracked("placeholder", role: "text")
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
                .padding(.top, 120)
        }
    }
}

// MARK: - P3 Even grid

struct Tile: Identifiable {
    let id: Int
    let name: String
    let hue: Double
}

let tiles: [Tile] = (0..<40).map { Tile(id: $0, name: SampleText.titles[$0 % SampleText.titles.count], hue: Double($0 % 12) / 12) }

/// variants: aligned (EvenGrid), naive (an adaptive LazyVGrid centred in the safe area, Wikipedia's Explore shape).
struct GridDemo: View {
    let variant: String

    var body: some View {
        NavigationStack {
            Group {
                if variant == "naive" {
                    ScrollView {
                        LazyVGrid(columns: [GridItem(.adaptive(minimum: 150), spacing: 12)], spacing: 12) {
                            ForEach(tiles) { TileView(tile: $0) }
                        }
                        .padding(16)
                    }
                } else {
                    EvenGrid(tiles, minCellWidth: 150) { TileView(tile: $0) }
                }
            }
            .navigationTitle("Gallery")
            .toolbar { ToolbarItem { Button("Add", systemImage: "plus") {} } }
        }
    }
}

struct TileView: View {
    let tile: Tile
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(hue: tile.hue, saturation: 0.45, brightness: 0.9))
                .aspectRatio(4 / 3, contentMode: .fit)
            Text(tile.name).font(.subheadline).lineLimit(1)
        }
        .duoTracked("cell-\(tile.id)", role: "cell", scrolls: true)
    }
}

// MARK: - P2 Reflowing columns

/// variants: aligned (ReflowingColumns), single (one scrolling column across the whole width, Wikipedia's article).
struct ColumnsDemo: View {
    let variant: String

    var body: some View {
        NavigationStack {
            Group {
                if variant == "single" {
                    ScrollView {
                        Text(SampleText.paragraphs.joined(separator: "\n\n"))
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(20)
                            .duoTracked("article", role: "column", scrolls: true)
                    }
                } else {
                    ReflowingColumns(paragraphs: SampleText.paragraphs) { columns in
                        for (i, column) in columns.enumerated() {
                            Tracker.shared.record("column-\(i)", role: "column", scrolls: true, frame: column)
                        }
                        if columns.count < 2 { Tracker.shared.forget("column-1") }
                    }
                }
            }
            .navigationTitle("Reading")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

// MARK: - P4 Arrangement

/// variants: aligned (Arrangement, split: a player and its transcript, Podcasts' shape), overlay (Arrangement,
/// overlay: the player's controls over the text, Accessibility Reader's shape, the text in ReflowingColumns), inline
/// (before: the player in a fixed third of the width beside the transcript in an HStack, the shape of Wikipedia's
/// inline contents).
struct ArrangementDemo: View {
    let variant: String

    var body: some View {
        NavigationStack {
            Group {
                switch variant {
                case "inline":
                    GeometryReader { proxy in
                        HStack(spacing: 0) {
                            PlayerPane().frame(width: proxy.size.width / 3)
                            TranscriptPane()
                        }
                    }
                case "overlay":
                    Arrangement(.overlay) {
                        PlayerControls().padding(.bottom, 16)
                    } secondary: {
                        // The text under the controls is itself continuous content, so it reflows (P2).
                        ReflowingColumns(paragraphs: SampleText.paragraphs) { columns in
                            for (i, column) in columns.enumerated() {
                                Tracker.shared.record("column-\(i)", role: "column", scrolls: true, frame: column)
                            }
                            if columns.count < 2 { Tracker.shared.forget("column-1") }
                        }
                        .duoTracked("secondary", role: "pane")
                    }
                default:
                    // The reference's two views are recorded as panes, so T14 checks the boundary in every folded
                    // pose; the before variant records only what accessibility reads (its leaves and its text).
                    Arrangement(.split) {
                        PlayerPane().duoTracked("primary", role: "pane")
                    } secondary: {
                        TranscriptPane().duoTracked("secondary", role: "pane")
                    }
                }
            }
            .navigationTitle("Now Playing")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem { Button("Queue", systemImage: "list.bullet") {} } }
        }
    }
}

/// The primary: artwork, title and controls, centred in whatever region the arrangement gives it.
struct PlayerPane: View {
    var body: some View {
        VStack(spacing: 16) {
            RoundedRectangle(cornerRadius: 16)
                .fill(LinearGradient(colors: [.orange, .pink], startPoint: .topLeading, endPoint: .bottomTrailing))
                .aspectRatio(1, contentMode: .fit)
                .accessibilityElement()
                .accessibilityLabel("Artwork")
                .accessibilityAddTraits(.isImage)
                .duoTracked("artwork", role: "image")
                .frame(maxWidth: 220, maxHeight: 220)
            Text(SampleText.titles[0]).font(.headline).lineLimit(1)
                .duoTracked("episode", role: "text")
            PlayerControls()
        }
        .padding(20)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct PlayerControls: View {
    var body: some View {
        HStack(spacing: 28) {
            Button("Back 15 seconds", systemImage: "gobackward.15") {}
            Button("Play", systemImage: "play.fill") {}.font(.title)
            Button("Forward 30 seconds", systemImage: "goforward.30") {}
        }
        .labelStyle(.iconOnly)
        .padding(.horizontal, 24).padding(.vertical, 12)
        .background(.regularMaterial, in: Capsule())
        .duoTracked("controls", role: "control")
    }
}

/// The secondary: the transcript, one text column that scrolls.
struct TranscriptPane: View {
    var body: some View {
        ScrollView {
            Text(SampleText.paragraphs.joined(separator: "\n\n"))
                .frame(maxWidth: .infinity, alignment: .leading)
                .duoTracked("transcript", role: "column", scrolls: true)
                .padding(20)
        }
    }
}
