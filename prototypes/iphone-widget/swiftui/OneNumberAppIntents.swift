import AppIntents

struct OpenOneNumberTodayIntent: AppIntent {
    static let title: LocalizedStringResource = "Open One Number Today"
    static let description = IntentDescription("Open the daily spending number.")
    static let openAppWhenRun = true

    @MainActor
    func perform() async throws -> some IntentResult {
        .result()
    }
}

struct OneNumberTodayShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: OpenOneNumberTodayIntent(),
            phrases: [
                "Open \(.applicationName)",
                "Show my one number in \(.applicationName)"
            ],
            shortTitle: "Open Number",
            systemImageName: "number"
        )
    }
}
