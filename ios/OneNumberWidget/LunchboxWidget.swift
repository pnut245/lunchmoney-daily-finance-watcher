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
            content
        }
        .containerBackground(background, for: .widget)
    }

    private var background: Color {
        entry.snapshot.isNegative ? Color(red: 0.84, green: 0.1, blue: 0.13) : .white
    }

    private var textColor: Color {
        entry.snapshot.isNegative ? .white : .black
    }

    private var emphasis: WidgetEmphasis {
        switch entry.configuration.emphasis {
        case .today:
            return .today
        case .dopamine:
            return .dopamine
        case .week:
            return .week
        }
    }

    @ViewBuilder
    private var content: some View {
        switch family {
        case .systemMedium:
            HStack(alignment: .bottom, spacing: 18) {
                VStack(alignment: .leading, spacing: 8) {
                    Text(entry.snapshot.emphasisLabel(emphasis).uppercased())
                        .font(.system(size: 14, weight: .bold, design: .rounded))
                        .tracking(0.8)
                    Text(entry.snapshot.displayNumber)
                        .font(.system(size: 112, weight: .black, design: .rounded))
                        .minimumScaleFactor(0.28)
                        .lineLimit(1)
                    Text(entry.snapshot.moneyObject.uppercased())
                        .font(.system(size: 14, weight: .semibold, design: .rounded))
                }
                Spacer(minLength: 0)
                VStack(alignment: .trailing, spacing: 10) {
                    metricPill(title: entry.snapshot.weekLabel, value: entry.snapshot.weekAmount)
                    metricPill(title: entry.snapshot.dopamineLabel, value: entry.snapshot.dopamineAmount)
                    Text(entry.snapshot.spendingState)
                        .font(.system(size: 12, weight: .bold, design: .rounded))
                }
            }
            .padding(18)
            .foregroundStyle(textColor)
        case .accessoryRectangular:
            VStack(alignment: .leading, spacing: 4) {
                Text(entry.snapshot.emphasisLabel(emphasis))
                Text("\(entry.snapshot.displayNumber) • \(entry.snapshot.spendingState)")
                    .font(.system(size: 16, weight: .bold, design: .rounded))
            }
            .foregroundStyle(textColor)
        case .accessoryInline:
            Text("\(entry.snapshot.emphasisLabel(emphasis)): \(entry.snapshot.displayNumber)")
                .foregroundStyle(textColor)
        case .accessoryCircular:
            Text(entry.snapshot.displayNumber)
                .font(.system(size: 24, weight: .black, design: .rounded))
                .minimumScaleFactor(0.3)
                .foregroundStyle(textColor)
        default:
            VStack(alignment: .leading, spacing: 8) {
                Text(entry.snapshot.emphasisLabel(emphasis).uppercased())
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                    .tracking(0.8)
                Text(entry.snapshot.displayNumber)
                    .font(.system(size: 88, weight: .black, design: .rounded))
                    .minimumScaleFactor(0.28)
                    .lineLimit(1)
                Text(entry.snapshot.moneyObject.uppercased())
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
            }
            .padding(16)
            .foregroundStyle(textColor)
        }
    }

    private func metricPill(title: String, value: Double) -> some View {
        VStack(alignment: .trailing, spacing: 2) {
            Text(title.uppercased())
                .font(.system(size: 10, weight: .bold, design: .rounded))
            Text("$\(Int(value.rounded()))")
                .font(.system(size: 18, weight: .black, design: .rounded))
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(Color.black.opacity(entry.snapshot.isNegative ? 0.16 : 0.08), in: Capsule())
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
        .description("One daily number for spending decisions.")
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
