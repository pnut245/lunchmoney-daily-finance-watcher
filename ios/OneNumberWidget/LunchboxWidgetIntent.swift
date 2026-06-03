import AppIntents

struct OneNumberWidgetConfigurationIntent: WidgetConfigurationIntent {
    static var title: LocalizedStringResource = "One Number"
    static var description = IntentDescription("Shows the ADHD-first daily budget snapshot.")

    @Parameter(title: "Emphasis", default: .today)
    var emphasis: WidgetFocus

    static var parameterSummary: some ParameterSummary {
        Summary("Show \(\.$emphasis)")
    }
}

enum WidgetFocus: String, AppEnum {
    case today
    case dopamine
    case week

    static var typeDisplayRepresentation: TypeDisplayRepresentation = "Emphasis"
    static var caseDisplayRepresentations: [Self: DisplayRepresentation] = [
        .today: "Today",
        .dopamine: "Dopamine",
        .week: "Week",
    ]
}
