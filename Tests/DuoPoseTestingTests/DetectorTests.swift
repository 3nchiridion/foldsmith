import Testing
import CoreGraphics
import Foundation
@testable import DuoDetectors

// Detector unit tests use synthetic poses so they run anywhere. The division frames are the measured ones
// (raw/metrics.json): 455.5–495.5 pt in book and flat-sideways, active only in book.
private func pose(_ name: String, active: Bool = true, window: CGSize = CGSize(width: 951, height: 669)) -> Pose {
    Pose(name: name, display: "inner", window: window,
         safeArea: .init(top: 24, leading: 0, bottom: 34, trailing: 84),
         hSizeClass: "regular", vSizeClass: "regular", toolbarVerticalEdge: "trailing",
         divisions: [.init(frame: CGRect(x: 455.5, y: 0, width: 40, height: 669), margins: .init(top: 0, leading: 0, bottom: 0, trailing: 0), isActive: active)],
         occlusions: [])
}
private let book = pose("book")
private let flatSideways = pose("flat-sideways", active: false)
private let laptop = Pose(name: "laptop", display: "inner", window: CGSize(width: 669, height: 951),
                          safeArea: .init(top: 0, leading: 0, bottom: 84, trailing: 0),
                          hSizeClass: "regular", vSizeClass: "regular", toolbarVerticalEdge: nil,
                          divisions: [.init(frame: CGRect(x: 0, y: 455.5, width: 669, height: 40), margins: .init(top: 0, leading: 0, bottom: 0, trailing: 0), isActive: true)],
                          occlusions: [])

private func box(_ minX: CGFloat, _ maxX: CGFloat, y: CGFloat = 100, h: CGFloat = 300) -> CGRect {
    CGRect(x: minX, y: y, width: maxX - minX, height: h)
}

// T1
@Test func creaseStraddleFlagsAControlInTheFold() {
    let e = Element(identifier: "save", role: "button", frame: CGRect(x: 440, y: 300, width: 60, height: 44), isInteractive: true)
    #expect(CreaseStraddle().run(elements: [e], pose: book).count == 1)
}

@Test func creaseStraddleFlagsStaticText() {
    let e = Element(identifier: "title", role: "text", frame: box(300, 600, h: 30))
    #expect(CreaseStraddle().run(elements: [e], pose: book).map(\.classId) == ["T1"])
}

@Test func creaseStraddleExemptsScrollingContent() {
    let e = Element(identifier: "row", role: "text", frame: box(300, 600, h: 30), scrolls: true)
    #expect(CreaseStraddle().run(elements: [e], pose: book).isEmpty)
}

@Test func creaseStraddleIgnoresAnInactiveDivision() {
    let e = Element(identifier: "save", role: "button", frame: CGRect(x: 440, y: 300, width: 60, height: 44), isInteractive: true)
    #expect(CreaseStraddle().run(elements: [e], pose: flatSideways).isEmpty)
}

@Test func creaseStraddleAllowsRounding() {   // the system's own sidebar ends at 455.7
    let e = Element(identifier: "label", role: "text", frame: box(300, 455.7, h: 30))
    #expect(CreaseStraddle().run(elements: [e], pose: book).isEmpty)
}

// T4
@Test func underSystemBarFlagsTrailingBand() {
    let e = Element(identifier: "fab", role: "button", frame: CGRect(x: 900, y: 500, width: 44, height: 44), isInteractive: true)
    #expect(UnderSystemBar().run(elements: [e], pose: book).count == 1)
}

@Test func underSystemBarPassesAWideButtonThatOnlyReachesTheBand() {
    // An accessibility frame that runs to the window's edge, past the drawn button (Home Assistant on the cover).
    let e = Element(identifier: "connect", role: "button", frame: box(58, 951, y: 540, h: 48), isInteractive: true)
    let barItem = Element(identifier: "add", role: "button", frame: CGRect(x: 889, y: 130, width: 28, height: 36),
                          isInteractive: true, inSystemBar: true)
    #expect(UnderSystemBar().run(elements: [e, barItem], pose: book).isEmpty)
}

// T5
@Test func stretchedSingleColumnFlagsOneColumnAcrossTheFold() {
    let e = Element(identifier: "article", role: "column", frame: box(20, 931, y: 0, h: 2000), scrolls: true)
    #expect(StretchedSingleColumn().run(elements: [e], pose: book).map(\.classId) == ["T5"])
    #expect(StretchedSingleColumn().run(elements: [e], pose: flatSideways).count == 1)   // inactive counts too
}

@Test func stretchedSingleColumnPassesTwoColumnsAndLaptop() {
    let two = [Element(identifier: "c0", role: "column", frame: box(20, 455.5)),
               Element(identifier: "c1", role: "column", frame: box(495.5, 847))]
    #expect(StretchedSingleColumn().run(elements: two, pose: book).isEmpty)
    let tall = Element(identifier: "article", role: "column", frame: CGRect(x: 20, y: 0, width: 629, height: 3000))
    #expect(StretchedSingleColumn().run(elements: [tall], pose: laptop).isEmpty)   // horizontal division
}

// T14
@Test func columnsOffFoldFlagsAFixedSidebarSplit() {   // NetNewsWire's shape: sidebar 320, detail across the fold
    let panes = [Element(identifier: "sidebar", role: "pane", frame: box(0, 320, y: 0, h: 669)),
                 Element(identifier: "detail", role: "pane", frame: box(320, 867, y: 0, h: 669))]
    let f = ColumnsOffFold().run(elements: panes, pose: book)
    #expect(f.map(\.element?.identifier) == ["detail"])
}

@Test func columnsOffFoldPassesTheSystemSplit() {   // measured: sidebar 0–455.7, detail 495.5–867.2
    let panes = [Element(identifier: "sidebar", role: "pane", frame: box(0, 455.7, y: 0, h: 669)),
                 Element(identifier: "detail", role: "pane", frame: box(495.5, 867.2, y: 0, h: 669))]
    #expect(ColumnsOffFold().run(elements: panes, pose: book).isEmpty)
}

@Test func columnsOffFoldReportsAGridColumnOnceAndIgnoresFlat() {
    var cells: [Element] = []
    for row in 0..<3 {
        for (i, x) in [(16.0, 185.4), (197.4, 342.8), (354.8, 512.2), (524.2, 681.6), (693.6, 851.0)].enumerated() {
            cells.append(Element(identifier: "cell-\(row)-\(i)", role: "cell", frame: box(x.0, x.1, y: CGFloat(row) * 160, h: 150), scrolls: true))
        }
    }
    #expect(ColumnsOffFold().run(elements: cells, pose: book).count == 1)
    #expect(ColumnsOffFold().run(elements: cells, pose: flatSideways).isEmpty)
}

// T14 turned: stacked panes against the horizontal fold
@Test func panesOffHorizontalFoldFlagsAnEvenStack() {   // a VStack halving the safe area: boundary at 499.5
    let panes = [Element(identifier: "primary", role: "pane", frame: CGRect(x: 0, y: 82, width: 669, height: 417.5)),
                 Element(identifier: "secondary", role: "pane", frame: CGRect(x: 0, y: 499.5, width: 669, height: 417.5))]
    let f = PanesOffHorizontalFold().run(elements: panes, pose: laptop)
    #expect(f.map(\.element?.identifier) == ["primary"])
}

@Test func panesOffHorizontalFoldPassesTheSplitArrangement() {   // measured: 82–455.5 and 495.5–917
    let panes = [Element(identifier: "primary", role: "pane", frame: CGRect(x: 0, y: 82, width: 669, height: 373.5)),
                 Element(identifier: "secondary", role: "pane", frame: CGRect(x: 0, y: 495.5, width: 669, height: 421.5))]
    #expect(PanesOffHorizontalFold().run(elements: panes, pose: laptop).isEmpty)
}

@Test func panesOffHorizontalFoldLeavesSideBySidePanesAndBookAlone() {
    // A split view upright: two full-height panes side by side cross the fold together, as Settings' do.
    let columns = [Element(identifier: "sidebar", role: "pane", frame: CGRect(x: 0, y: 0, width: 320, height: 951)),
                   Element(identifier: "detail", role: "pane", frame: CGRect(x: 320, y: 0, width: 349, height: 951))]
    #expect(PanesOffHorizontalFold().run(elements: columns, pose: laptop).isEmpty)
    let stacked = [Element(identifier: "a", role: "pane", frame: box(0, 867, y: 0, h: 300)),
                   Element(identifier: "b", role: "pane", frame: box(0, 867, y: 300, h: 369))]
    #expect(PanesOffHorizontalFold().run(elements: stacked, pose: book).isEmpty)   // a vertical fold is T14's own case
}

// T15
// T14 by the bars
@Test func paneBoundaryOffFoldFlagsAFixedSidebar() {   // NetNewsWire before: bars 0–320 and 321–951
    let bars = [Element(identifier: "Timeline", role: "bar", frame: CGRect(x: 0, y: 24, width: 320, height: 58)),
                Element(identifier: "Detail", role: "bar", frame: CGRect(x: 321, y: 24, width: 630, height: 58))]
    #expect(PaneBoundaryOffFold().run(elements: bars, pose: book).count == 1)
    #expect(PaneBoundaryOffFold().run(elements: bars, pose: flatSideways).isEmpty)
}

@Test func paneBoundaryOffFoldPassesTheSystemSplit() {   // NetNewsWire after: bars 0–475 and 476–951
    let bars = [Element(identifier: "Feeds", role: "bar", frame: CGRect(x: 0, y: 24, width: 475, height: 129)),
                Element(identifier: "Detail", role: "bar", frame: CGRect(x: 476, y: 24, width: 475, height: 58))]
    #expect(PaneBoundaryOffFold().run(elements: bars, pose: book).isEmpty)
}

// T10
@Test func strandedHorizontalItemFlagsTextItemsOutsideTheVerticalBar() {
    let cancel = Element(label: "Cancel", role: "control", frame: CGRect(x: 28, y: 40, width: 77, height: 36),
                         isInteractive: true, inSystemBar: true, inNavigationBar: true)
    let symbol = Element(label: "Add", role: "control", frame: CGRect(x: 391, y: 40, width: 40, height: 40),
                         isInteractive: true, inSystemBar: true, inNavigationBar: true)
    let inBand = Element(label: "Done", role: "control", frame: CGRect(x: 880, y: 100, width: 60, height: 36),
                         isInteractive: true, inSystemBar: true, inNavigationBar: true)
    #expect(StrandedHorizontalItem().run(elements: [cancel, symbol, inBand], pose: book).map(\.element?.label) == ["Cancel"])
    #expect(StrandedHorizontalItem().run(elements: [cancel], pose: laptop).isEmpty)   // no vertical bar upright
}

@Test func strandedHorizontalItemFlagsAToolbarItemBesideTheVerticalBarWhateverItsShape() {
    // Wikipedia's article before its migration: custom-view toolbar items in a row along the bottom; NetNewsWire's
    // timeline pane keeps its own bottom toolbar beside the detail, as the system draws it.
    let custom = Element(identifier: "contents", role: "control", frame: CGRect(x: 600, y: 614, width: 33, height: 33),
                         isInteractive: true, inSystemBar: true, inToolbar: true)
    let inBand = Element(identifier: "share", role: "control", frame: CGRect(x: 888, y: 600, width: 38, height: 38),
                         isInteractive: true, inSystemBar: true, inToolbar: true)
    #expect(StrandedHorizontalItem().run(elements: [custom, inBand], pose: book).map(\.element?.identifier) == ["contents"])
    let bars = [Element(identifier: "Timeline", role: "bar", frame: CGRect(x: 0, y: 24, width: 475, height: 58)),
                Element(identifier: "Detail", role: "bar", frame: CGRect(x: 476, y: 24, width: 475, height: 58))]
    let leadingPane = Element(identifier: "Mark All as Read", role: "control", frame: CGRect(x: 25, y: 614, width: 38, height: 38),
                              isInteractive: true, inSystemBar: true, inToolbar: true)
    #expect(StrandedHorizontalItem().run(elements: bars + [leadingPane, custom], pose: book).map(\.element?.identifier) == ["contents"])
}

// T7
@Test func stateLossOnFoldFlagsAnInnerPoseWithoutTheShutPhonesBars() {
    let findings = StateLossOnFold.run(closed: ["Feeds"], inner: ["book": ["Timeline", "Detail"], "laptop": ["Feeds", "Detail"],
                                                                 "closed-sideways": ["Timeline"]])
    #expect(findings.map(\.pose) == ["book"])
    #expect(StateLossOnFold.run(closed: [], inner: ["book": ["Detail"]]).isEmpty)
}

@Test func stateLossOnFoldFlagsAnAppThatIsNoLongerInFront() throws {
    // What the tap runner writes when the app crashed on the fold (IceCubesApp, closing from tent with Settings selected).
    let json = #"{"appState":"notRunning","bundle":"dev.enchiridion.corpus.IceCubesApp","nodes":[],"window":[0,0]}"#
    let snapshot = try JSONDecoder().decode(AccessibilitySnapshot.self, from: Data(json.utf8))
    #expect(StateLossOnFold.notInFront(appState: snapshot.appState, pose: "flat-sideways")?.classId == "T7")
    #expect(StateLossOnFold.notInFront(appState: nil, pose: "book") == nil)
    #expect(StateLossOnFold.notInFront(appState: "runningForeground", pose: "book") == nil)
}

@Test func stateLossOnFoldFlagsToolbarItemsThatVanishBesideTheVerticalBar() {
    // Wikipedia's article before its migration: six custom-view items on the cover, none of them drawn in book.
    let stranded: Set<String> = ["Article Save Button", "Article More Button"]
    let lost = StateLossOnFold.lostBarItems(stranded: stranded, inner: ["book": ["Search", "Tabs"],
                                                                         "flat-sideways": ["Article More Button", "More"]])
    #expect(lost.map(\.pose) == ["book"])
    #expect(StateLossOnFold.lostBarItems(stranded: [], inner: ["book": []]).isEmpty)
}

@Test func anUnnamedStrandedItemCannotBeLostAndANamedOneIsFoundByLabel() {
    // A custom view with no identifier and no label: T10 names it "control", which no pose can be searched for.
    let unnamed = Element(role: "control", frame: CGRect(x: 600, y: 614, width: 44, height: 44),
                          isInteractive: true, inSystemBar: true, inToolbar: true)
    let named = Element(identifier: "reader", label: "Reader View", role: "control", frame: CGRect(x: 650, y: 614, width: 44, height: 44),
                        isInteractive: true, inSystemBar: true, inToolbar: true)
    let stranded = StateLossOnFold.strandedNames(StrandedHorizontalItem().run(elements: [unnamed, named], pose: book))
    #expect(stranded == ["reader"])
    let drawn = StateLossOnFold.names([Element(label: "reader", role: "control", frame: .zero)])
    #expect(StateLossOnFold.lostBarItems(stranded: stranded, inner: ["book": drawn]).isEmpty)
}

// T14 by what spans a pane
@Test func paneContentShortOfFoldFlagsAListPaneInsetByTheBarsBand() {
    // Wikipedia's split container before its review fixes: the list pane ends at the fold, its content 84 pt short.
    let bars = [Element(identifier: "Saved", role: "bar", frame: CGRect(x: 0, y: 24, width: 455, height: 112)),
                Element(identifier: "Detail", role: "bar", frame: CGRect(x: 496, y: 24, width: 371, height: 58))]
    let short = Element(identifier: "search", role: "control", frame: CGRect(x: 20, y: 82, width: 351, height: 44),
                        isInteractive: true, spansWidth: true)
    let full = Element(identifier: "picker", role: "control", frame: CGRect(x: 16, y: 144, width: 423, height: 31),
                       isInteractive: true, spansWidth: true)
    #expect(PaneContentShortOfFold().run(elements: bars + [short, full], pose: book).map(\.element?.identifier) == ["search"])
    #expect(PaneContentShortOfFold().run(elements: bars + [short], pose: flatSideways).count == 1)   // inactive counts
    // A field followed by its Cancel button: the row, not the field, reaches the edge.
    let field = Element(identifier: "field", role: "control", frame: CGRect(x: 20, y: 40, width: 360, height: 44),
                        isInteractive: true, spansWidth: true)
    let cancel = Element(identifier: "cancel", role: "control", frame: CGRect(x: 395, y: 40, width: 44, height: 44), isInteractive: true)
    #expect(PaneContentShortOfFold().run(elements: bars + [field, cancel], pose: book).isEmpty)
    // A sidebar that does not end at the fold is not this detector's (NetNewsWire's flat sidebar ends at 320).
    let flatBars = [Element(identifier: "Feeds", role: "bar", frame: CGRect(x: 0, y: 24, width: 320, height: 58))]
    #expect(PaneContentShortOfFold().run(elements: flatBars + [short], pose: flatSideways).isEmpty)
}

@Test func sheetInBookFlagsTheLeadingHalfOnly() {
    let leading = Element(identifier: "sheet", role: "sheet", frame: box(8, 467.3, y: 40, h: 600))
    let trailing = Element(identifier: "sheet", role: "sheet", frame: box(483.5, 867.2, y: 40, h: 600))
    let centred = Element(identifier: "sheet", role: "sheet", frame: box(149, 802, y: 40, h: 600))
    #expect(SheetInBook().run(elements: [leading], pose: book).count == 1)
    #expect(SheetInBook().run(elements: [trailing], pose: book).isEmpty)
    #expect(SheetInBook().run(elements: [centred], pose: flatSideways).isEmpty)
}
