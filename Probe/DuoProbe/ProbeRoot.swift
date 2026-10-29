import SwiftUI
import UIKit

/// Snapshot of the SwiftUI environment + reserved regions, taken on every geometry change.
/// Everything below compiles only against the iOS 27.1 SDK; names follow raw/apple-docs/api-swiftui.md
/// and must be re-checked against the real .swiftinterface (raw/sdk/) before trusting a field.
struct ProbeRoot: View {
    @Environment(\.horizontalSizeClass) private var hClass
    @Environment(\.verticalSizeClass) private var vClass
    @Environment(\.toolbarVerticalEdge) private var verticalEdge
    @Environment(\.layoutDirection) private var layoutDirection

    @State private var seq = 0
    @State private var lastChange = Date()
    @State private var hinge: DeviceHinge? = nil
    @State private var latest: Sample? = nil

    private var label: String {
        let args = CommandLine.arguments
        if let i = args.firstIndex(of: "-label"), i + 1 < args.count { return args[i + 1] }
        return "unlabeled"
    }
    private var overlay: Bool {
        let args = CommandLine.arguments
        if let i = args.firstIndex(of: "-overlay"), i + 1 < args.count { return args[i + 1] != "0" }
        return true
    }

    var body: some View {
        GeometryReader { proxy in
            let divisions = proxy.reservedRegions(kind: .division, options: .includeInactive)
            let occlusions = proxy.reservedRegions(kind: .occlusion, options: .includeInactive)
            ZStack(alignment: .topLeading) {
                Color(.systemBackground)
                if overlay {
                    // Safe area as a frame; regions as filled rects. Visual check for the screenshot set.
                    Rectangle().strokeBorder(.blue, lineWidth: 2)
                        .padding(.top, proxy.safeAreaInsets.top).padding(.bottom, proxy.safeAreaInsets.bottom)
                        .padding(.leading, proxy.safeAreaInsets.leading).padding(.trailing, proxy.safeAreaInsets.trailing)
                        .ignoresSafeArea()
                    ForEach(divisions) { r in
                        Rectangle().fill(r.isActive ? .red.opacity(0.35) : .orange.opacity(0.2))
                            .frame(width: r.frame.width, height: r.frame.height)
                            .offset(x: r.frame.minX, y: r.frame.minY)
                    }
                    ForEach(occlusions) { r in
                        Rectangle().fill(r.isActive ? .purple.opacity(0.45) : .purple.opacity(0.15))
                            .frame(width: r.frame.width, height: r.frame.height)
                            .offset(x: r.frame.minX, y: r.frame.minY)
                    }
                }
                readout(proxy: proxy, divisions: divisions, occlusions: occlusions)
                    .padding()
            }
            // Fires on the first layout and every change: this is how first-frame vs settled is measured.
            .onGeometryChange(for: GeometryKey.self) { p in
                GeometryKey(size: p.size, insets: p.safeAreaInsets,
                            regions: p.reservedRegions(kind: .division, options: .includeInactive).map { "\($0.id)|\($0.frame)|\($0.isActive)" }
                                   + p.reservedRegions(kind: .occlusion, options: .includeInactive).map { "\($0.id)|\($0.frame)|\($0.isActive)" })
            } action: { _ in
                record(proxy: proxy, divisions: divisions, occlusions: occlusions)
            }
        }
        .onHingeChange { _, ctx in
            hinge = ctx.hinge
        }
        .ignoresSafeArea(.container, edges: overlay ? .all : [])
    }

    private func readout(proxy: GeometryProxy, divisions: [ReservedRegion], occlusions: [ReservedRegion]) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("label \(label)  seq \(seq)").font(.headline.monospaced())
            Text("size \(fmt(proxy.size.width))×\(fmt(proxy.size.height))  insets t\(fmt(proxy.safeAreaInsets.top)) l\(fmt(proxy.safeAreaInsets.leading)) b\(fmt(proxy.safeAreaInsets.bottom)) tr\(fmt(proxy.safeAreaInsets.trailing))")
            Text("classes h:\(desc(hClass)) v:\(desc(vClass))  verticalEdge:\(desc(verticalEdge))")
            ForEach(divisions) { r in Text("division \(rect(r.frame)) active:\(String(r.isActive))") }
            ForEach(occlusions) { r in Text("occlusion \(rect(r.frame)) active:\(String(r.isActive))") }
            if let hinge { Text("hinge \(fmt(hinge.angle.degrees))° \(statusName(hinge.status))") } else { Text("hinge: none") }
        }
        .font(.caption.monospaced())
        .padding(8)
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 8))
    }

    private func record(proxy: GeometryProxy, divisions: [ReservedRegion], occlusions: [ReservedRegion]) {
        let now = Date()
        seq += 1
        let scene = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first
        let s = Sample(
            label: label, seq: seq,
            t: now.timeIntervalSince(MetricsLog.start),
            sinceLastChange: now.timeIntervalSince(lastChange),
            window: .init(w: proxy.size.width, h: proxy.size.height),
            safeArea: .init(proxy.safeAreaInsets),
            hSizeClass: desc(hClass), vSizeClass: desc(vClass),
            toolbarVerticalEdge: desc(verticalEdge),
            layoutDirection: String(describing: layoutDirection),
            divisions: divisions.map { .init(id: "\($0.id)", frame: .init($0.frame), margins: .init($0.margins), isActive: $0.isActive) },
            occlusions: occlusions.map { .init(id: "\($0.id)", frame: .init($0.frame), margins: .init($0.margins), isActive: $0.isActive) },
            hinge: hinge.map { .init(angleDegrees: $0.angle.degrees, status: statusName($0.status)) },
            scene: .init(
                sceneBounds: scene.map { .init($0.effectiveGeometry.coordinateSpace.bounds) },
                screenBounds: scene.map { .init($0.screen.bounds) },
                displayScale: Double(scene?.screen.scale ?? 0),
                interfaceOrientation: scene.map { String(describing: $0.effectiveGeometry.interfaceOrientation) } ?? "nil",
                windowSafeArea: scene?.keyWindow.map { .init($0.safeAreaInsets) })
        )
        lastChange = now
        latest = s
        MetricsLog.append(s)
    }

    private func fmt(_ v: CGFloat) -> String { String(format: "%.1f", v) }
    private func rect(_ r: CGRect) -> String { "(\(fmt(r.minX)),\(fmt(r.minY)) \(fmt(r.width))×\(fmt(r.height)))" }
    private func desc<T>(_ v: T?) -> String { v.map { String(describing: $0) } ?? "nil" }
    // DeviceHinge.Status is a struct with no description (raw/sdk/DIFF.md), so name its cases here.
    private func statusName(_ s: DeviceHinge.Status) -> String {
        switch s {
        case .closed: "closed"
        case .partiallyOpen: "partiallyOpen"
        case .fullyOpen: "fullyOpen"
        default: "unknown"
        }
    }
}

/// Equatable key so onGeometryChange fires on size, inset or region changes only.
nonisolated struct GeometryKey: Equatable, Sendable {
    var size: CGSize
    var insets: EdgeInsets
    var regions: [String]
}
