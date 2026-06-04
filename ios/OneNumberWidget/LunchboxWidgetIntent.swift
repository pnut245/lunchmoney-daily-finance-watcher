import AppIntents

struct OneNumberWidgetConfigurationIntent: WidgetConfigurationIntent {
    static var title: LocalizedStringResource = "One Number"
    static var description = IntentDescription("Shows only today's remaining discretionary spend.")
}
