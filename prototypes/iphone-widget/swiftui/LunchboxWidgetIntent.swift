import AppIntents

struct LunchboxWidgetConfigurationIntent: WidgetConfigurationIntent {
    static var title: LocalizedStringResource = "One Number Today"
    static var description = IntentDescription("Shows the daily spending number.")
}
