import AppIntents

struct LunchboxWidgetConfigurationIntent: WidgetConfigurationIntent {
    static let title: LocalizedStringResource = "One Number Today"
    static let description = IntentDescription("Shows the daily spending number.")
}
