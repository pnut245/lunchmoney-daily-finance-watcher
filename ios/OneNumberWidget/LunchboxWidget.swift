import AppIntents
import SwiftUI
import WidgetKit

struct OneNumberEntry: TimelineEntry {
    let date: Date
    let snapshot: LunchboxSnapshot
    let configuration: OneNumberWidgetConfigurationIntent
}

struct OneNumberWidgetProvider: AppIntentTimelineProvider {
    func placeholder(in context: Context) -> OneNumberEntry {
        OneNumberEntry(date: .now, snapshot: .preview, configuration: .init())
    }

    func snapshot(for configuration: OneNumberWidgetConfigurationIntent, in context: Context) async -> OneNumberEntry {
        OneNumberEntry(
            date: .now,
            snapshot: SnapshotStore.loadCachedSnapshot() ?? .preview,
            configuration: configuration
        )
    }

    func timeline(for configuration: OneNumberWidgetConfigurationIntent, in context: Context) async -> Timeline<OneNumberEntry> {
        var snapshot = SnapshotStore.loadCachedSnapshot() ?? .preview

        if let url = SnapshotStore.configuredURL {
            do {
                let fetched = try await SnapshotFetcher.fetch(from: url)
                SnapshotStore.cache(snapshot: fetched)
                snapshot = fetched
            } catch {
                SnapshotStore.saveError(error.localizedDescription)
            }
        }

        let entry = OneNumberEntry(date: .now, snapshot: snapshot, configuration: configuration)
        return Timeline(entries: [entry], policy: .after(.now.addingTimeInterval(60 * 60)))
    }
}

struct OneNumberWidgetView: View {
    let entry: OneNumberWidgetProvider.Entry
    @Environment(\.widgetFamily) private var family

    var body: some View {
        ZStack {
            background
            Text(entry.snapshot.displayNumber)
                .font(numberFont)
                .minimumScaleFactor(0.2)
                .lineLimit(1)
                .tracking(numberTracking)
                .scaleEffect(x: 0.92, y: 1.0)
                .foregroundStyle(foreground)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .containerBackground(background, for: .widget)
    }

    private var background: Color {
        entry.snapshot.isNegative ? Color(red: 0.88, green: 0.02, blue: 0.0) : .white
    }

    private var foreground: Color {
        entry.snapshot.isNegative ? .white : .black
    }

    private var numberFont: Font {
        switch family {
        case .systemMedium:
            return .system(size: 170, weight: .black, design: .default)
        case .systemSmall:
            return .system(size: 118, weight: .black, design: .default)
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
    OneNumberEntry(date: .now, snapshot: .preview, configuration: .init())
}

#Preview(as: .systemSmall) {
    OneNumberWidget()
} timeline: {
    OneNumberEntry(date: .now, snapshot: .negativePreview, configuration: .init())
}
