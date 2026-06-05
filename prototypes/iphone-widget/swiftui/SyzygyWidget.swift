import AppIntents
import SwiftUI
import WidgetKit

struct SyzygyWidgetEntry: TimelineEntry {
    let date: Date
    let snapshot: SyzygyWidgetSnapshot
    let configuration: SyzygyWidgetConfigurationIntent
}

struct SyzygyWidgetProvider: AppIntentTimelineProvider {
    func placeholder(in context: Context) -> SyzygyWidgetEntry {
        SyzygyWidgetEntry(date: .now, snapshot: .preview, configuration: .init())
    }

    func snapshot(for configuration: SyzygyWidgetConfigurationIntent, in context: Context) async -> SyzygyWidgetEntry {
        SyzygyWidgetEntry(date: .now, snapshot: .preview, configuration: configuration)
    }

    func timeline(for configuration: SyzygyWidgetConfigurationIntent, in context: Context) async -> Timeline<SyzygyWidgetEntry> {
        let entry = SyzygyWidgetEntry(date: .now, snapshot: .preview, configuration: configuration)
        return Timeline(entries: [entry], policy: .after(.now.addingTimeInterval(60 * 60)))
    }
}

struct SyzygyWidgetView: View {
    let entry: SyzygyWidgetProvider.Entry
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

    private var fontSize: CGFloat {
        switch family {
        case .systemMedium:
            112
        case .accessoryInline:
            20
        case .accessoryCircular, .accessoryRectangular:
            30
        default:
            88
        }
    }

    @ViewBuilder
    private var content: some View {
        switch family {
        case .systemMedium:
            HStack(alignment: .bottom, spacing: 18) {
                VStack(alignment: .leading, spacing: 8) {
                    Text(entry.snapshot.emphasisLabel(entry.configuration.emphasis).uppercased())
                        .font(.system(size: 14, weight: .bold, design: .rounded))
                        .tracking(0.8)
                    Text(entry.snapshot.displayNumber)
                        .font(.system(size: fontSize, weight: .black, design: .rounded))
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
            .foregroundStyle(entry.snapshot.isNegative ? .white : .black)
        case .accessoryRectangular:
            VStack(alignment: .leading, spacing: 4) {
                Text(entry.snapshot.emphasisLabel(entry.configuration.emphasis))
                Text("\(entry.snapshot.displayNumber) • \(entry.snapshot.spendingState)")
                    .font(.system(size: 16, weight: .bold, design: .rounded))
            }
        case .accessoryInline:
            Text("\(entry.snapshot.emphasisLabel(entry.configuration.emphasis)): \(entry.snapshot.displayNumber)")
        case .accessoryCircular:
            Text(entry.snapshot.displayNumber)
                .font(.system(size: 24, weight: .black, design: .rounded))
                .minimumScaleFactor(0.3)
        default:
            VStack(alignment: .leading, spacing: 8) {
                Text(entry.snapshot.emphasisLabel(entry.configuration.emphasis).uppercased())
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                    .tracking(0.8)
                Text(entry.snapshot.displayNumber)
                    .font(.system(size: fontSize, weight: .black, design: .rounded))
                    .minimumScaleFactor(0.28)
                    .lineLimit(1)
                Text(entry.snapshot.moneyObject.uppercased())
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
            }
            .padding(16)
            .foregroundStyle(entry.snapshot.isNegative ? .white : .black)
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

struct SyzygyWidget: Widget {
    let kind = "SyzygyWidget"

    var body: some WidgetConfiguration {
        AppIntentConfiguration(
            kind: kind,
            intent: SyzygyWidgetConfigurationIntent.self,
            provider: SyzygyWidgetProvider()
        ) { entry in
            SyzygyWidgetView(entry: entry)
        }
        .configurationDisplayName("One Number Today")
        .description("One daily number for spending decisions.")
        .supportedFamilies([.systemSmall, .systemMedium, .accessoryInline, .accessoryCircular, .accessoryRectangular])
    }
}

#Preview(as: .systemSmall) {
    SyzygyWidget()
} timeline: {
    SyzygyWidgetEntry(date: .now, snapshot: .preview, configuration: .init())
}

#Preview(as: .systemSmall) {
    SyzygyWidget()
} timeline: {
    SyzygyWidgetEntry(date: .now, snapshot: .negativePreview, configuration: .init())
}
