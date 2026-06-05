import AppIntents

struct SyzygyWidgetConfigurationIntent: WidgetConfigurationIntent {
    static var title: LocalizedStringResource = "Syzygy Budget"
    static var description = IntentDescription("Shows the ADHD-first daily budget snapshot.")

    @Parameter(title: "Emphasis", default: .today)
    var emphasis: WidgetEmphasis

    static var parameterSummary: some ParameterSummary {
        Summary("Show \(\.$emphasis)")
    }
}

enum WidgetEmphasis: String, AppEnum {
    case today
    case dopamine
    case week

    static var typeDisplayRepresentation: TypeDisplayRepresentation = "Emphasis"
    static var caseDisplayRepresentations: [Self: DisplayRepresentation] = [
        .today: "Today",
        .dopamine: "Dopamine",
        .week: "Week"
    ]
}
