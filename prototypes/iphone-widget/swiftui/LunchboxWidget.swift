import AppIntents
import SwiftUI
import WidgetKit

struct LunchboxWidgetEntry: TimelineEntry {
    let date: Date
    let snapshot: LunchboxWidgetSnapshot
    let configuration: LunchboxWidgetConfigurationIntent
}

struct LunchboxWidgetProvider: AppIntentTimelineProvider {
    func placeholder(in context: Context) -> LunchboxWidgetEntry {
        LunchboxWidgetEntry(date: .now, snapshot: .preview, configuration: .init())
    }

    func snapshot(for configuration: LunchboxWidgetConfigurationIntent, in context: Context) async -> LunchboxWidgetEntry {
        LunchboxWidgetEntry(date: .now, snapshot: .preview, configuration: configuration)
    }

    func timeline(for configuration: LunchboxWidgetConfigurationIntent, in context: Context) async -> Timeline<LunchboxWidgetEntry> {
        let entry = LunchboxWidgetEntry(date: .now, snapshot: .preview, configuration: configuration)
        return Timeline(entries: [entry], policy: .after(.now.addingTimeInterval(15 * 60)))
    }
}

struct LunchboxWidgetView: View {
    let entry: LunchboxWidgetProvider.Entry
    @Environment(\.widgetFamily) private var family

    var body: some View {
        ZStack {
            background
            Text(entry.snapshot.displayNumber)
                .font(.system(size: fontSize, weight: .black, design: .default))
                .minimumScaleFactor(0.28)
                .lineLimit(1)
                .foregroundStyle(entry.snapshot.isNegative ? .white : .black)
                .fontDesign(.default)
        }
        .containerBackground(background, for: .widget)
    }

    private var background: Color {
        entry.snapshot.isNegative ? Color(red: 0.84, green: 0.1, blue: 0.13) : .white
    }

    private var fontSize: CGFloat {
        switch family {
        case .systemMedium:
            126
        case .accessoryInline:
            20
        case .accessoryCircular, .accessoryRectangular:
            30
        default:
            88
        }
    }
}

struct LunchboxWidget: Widget {
    let kind = "LunchboxWidget"

    var body: some WidgetConfiguration {
        AppIntentConfiguration(
            kind: kind,
            intent: LunchboxWidgetConfigurationIntent.self,
            provider: LunchboxWidgetProvider()
        ) { entry in
            LunchboxWidgetView(entry: entry)
        }
        .configurationDisplayName("One Number Today")
        .description("One daily number for spending decisions.")
        .supportedFamilies([.systemSmall, .systemMedium, .accessoryInline, .accessoryCircular, .accessoryRectangular])
    }
}

#Preview(as: .systemSmall) {
    LunchboxWidget()
} timeline: {
    LunchboxWidgetEntry(date: .now, snapshot: .preview, configuration: .init())
}

#Preview(as: .systemSmall) {
    LunchboxWidget()
} timeline: {
    LunchboxWidgetEntry(date: .now, snapshot: .negativePreview, configuration: .init())
}
