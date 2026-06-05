import AppIntents
import SwiftUI
import WidgetKit

struct OneNumberEntry: TimelineEntry {
    let date: Date
    let snapshot: SyzygySnapshot
    let configuration: OneNumberWidgetConfigurationIntent
    let issueText: String?
}

struct OneNumberWidgetProvider: AppIntentTimelineProvider {
    func placeholder(in context: Context) -> OneNumberEntry {
        OneNumberEntry(date: .now, snapshot: .preview, configuration: .init(), issueText: nil)
    }

    func snapshot(for configuration: OneNumberWidgetConfigurationIntent, in context: Context) async -> OneNumberEntry {
        OneNumberEntry(
            date: .now,
            snapshot: SnapshotStore.loadCachedSnapshot() ?? .preview,
            configuration: configuration,
            issueText: SnapshotStore.loadError()
        )
    }

    func timeline(for configuration: OneNumberWidgetConfigurationIntent, in context: Context) async -> Timeline<OneNumberEntry> {
        var snapshot = SnapshotStore.loadCachedSnapshot() ?? .preview
        var issueText = SnapshotStore.loadError()

        if let url = SnapshotStore.configuredURL {
            do {
                let fetched = try await SnapshotFetcher.fetch(from: url)
                SnapshotStore.cache(snapshot: fetched)
                snapshot = fetched
                issueText = nil
            } catch {
                issueText = error.localizedDescription
                SnapshotStore.saveError(issueText ?? error.localizedDescription)
            }
        }

        let entry = OneNumberEntry(date: .now, snapshot: snapshot, configuration: configuration, issueText: issueText)
        let retryInterval: TimeInterval = issueText == nil && snapshot.freshness == .fresh ? 60 * 60 : 15 * 60
        return Timeline(entries: [entry], policy: .after(.now.addingTimeInterval(retryInterval)))
    }
}

struct OneNumberWidgetView: View {
    let entry: OneNumberWidgetProvider.Entry
    @Environment(\.widgetFamily) private var family

    var body: some View {
        ZStack {
            background
            widgetLayout
        }
        .containerBackground(background, for: .widget)
    }

    @ViewBuilder
    private var widgetLayout: some View {
        switch family {
        case .systemSmall, .systemMedium:
            ZStack(alignment: .topLeading) {
                oversizedObject

                VStack(alignment: .leading, spacing: 0) {
                    if showsStatusFlag {
                        statusFlag
                    }
                    Spacer(minLength: 0)
                    HStack {
                        Text(entry.snapshot.displayNumber)
                            .font(numberFont)
                            .minimumScaleFactor(0.2)
                            .lineLimit(1)
                            .tracking(numberTracking)
                            .scaleEffect(x: 0.92, y: 1.0)
                            .foregroundStyle(foreground)
                        Spacer(minLength: 0)
                    }
                }
                .padding(widgetPadding)
            }
        case .accessoryRectangular:
            HStack(alignment: .lastTextBaseline, spacing: 8) {
                Text(entry.snapshot.displayNumber)
                    .font(numberFont)
                    .tracking(numberTracking)
                    .foregroundStyle(foreground)
                if showsStatusFlag {
                    Text(shortStatusLabel.uppercased())
                        .font(.system(size: 9, weight: .black, design: .rounded))
                        .foregroundStyle(foreground.opacity(0.7))
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
        default:
            Text(entry.snapshot.displayNumber)
                .font(numberFont)
                .minimumScaleFactor(0.2)
                .lineLimit(1)
                .tracking(numberTracking)
                .scaleEffect(x: 0.92, y: 1.0)
                .foregroundStyle(foreground)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private var background: Color {
        SyzygyVisuals.palette(for: entry.snapshot)[1]
    }

    private var foreground: Color {
        SyzygyVisuals.ink(for: entry.snapshot)
    }

    private var showsStatusFlag: Bool {
        entry.issueText != nil || entry.snapshot.freshness != .fresh
    }

    private var shortStatusLabel: String {
        if entry.issueText != nil {
            return "Offline"
        }
        switch entry.snapshot.freshness {
        case .fresh:
            return "Live"
        case .aging:
            return "Aging"
        case .stale:
            return "Stale"
        case .unknown:
            return "Waiting"
        }
    }

    private var widgetPadding: CGFloat {
        family == .systemMedium ? 16 : 12
    }

    @ViewBuilder
    private var oversizedObject: some View {
        if family == .systemSmall || family == .systemMedium {
            SyzygyObjectView(snapshot: entry.snapshot, compact: false)
                .frame(
                    width: family == .systemMedium ? 188 : 136,
                    height: family == .systemMedium ? 188 : 136
                )
                .offset(oversizedObjectOffset)
                .opacity(entry.snapshot.isNegative ? 0.96 : 1.0)
                .allowsHitTesting(false)
        }
    }

    private var oversizedObjectOffset: CGSize {
        if family == .systemMedium {
            if entry.snapshot.isNegative {
                return CGSize(width: 98, height: 70)
            }
            return CGSize(width: 106, height: 70)
        }

        if entry.snapshot.isNegative {
            return CGSize(width: 62, height: 58)
        }
        return CGSize(width: 70, height: 54)
    }

    private var statusFlag: some View {
        Text(shortStatusLabel.uppercased())
            .font(.system(size: 10, weight: .black, design: .rounded))
            .tracking(1.2)
            .foregroundStyle(foreground.opacity(0.74))
    }

    private var numberFont: Font {
        switch family {
        case .systemMedium:
            return .system(size: 152, weight: .black, design: .default)
        case .systemSmall:
            return .system(size: 104, weight: .black, design: .default)
        case .accessoryCircular:
            return .system(size: 34, weight: .black, design: .default)
        case .accessoryRectangular:
            return .system(size: 46, weight: .black, design: .default)
        case .accessoryInline:
            return .system(size: 22, weight: .black, design: .default)
        default:
            return .system(size: 118, weight: .black, design: .default)
        }
    }

    private var numberTracking: CGFloat {
        switch family {
        case .accessoryInline:
            return -1.5
        default:
            return -6
        }
    }
}

struct OneNumberWidget: Widget {
    let kind = "OneNumberWidget"

    var body: some WidgetConfiguration {
        AppIntentConfiguration(
            kind: kind,
            intent: OneNumberWidgetConfigurationIntent.self,
            provider: OneNumberWidgetProvider()
        ) { entry in
            OneNumberWidgetView(entry: entry)
        }
        .configurationDisplayName("One Number")
        .description("Shows only today's remaining discretionary spend.")
        .supportedFamilies([.systemSmall, .systemMedium, .accessoryInline, .accessoryCircular, .accessoryRectangular])
    }
}

#Preview(as: .systemSmall) {
    OneNumberWidget()
} timeline: {
    OneNumberEntry(date: .now, snapshot: .preview, configuration: .init(), issueText: nil)
}

#Preview(as: .systemSmall) {
    OneNumberWidget()
} timeline: {
    OneNumberEntry(date: .now, snapshot: .negativePreview, configuration: .init(), issueText: nil)
}
