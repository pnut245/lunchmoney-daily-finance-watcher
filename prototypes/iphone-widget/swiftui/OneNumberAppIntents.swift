import AppIntents

struct OpenOneNumberTodayIntent: AppIntent {
    static var title: LocalizedStringResource = "Open One Number Today"
    static var description = IntentDescription("Open the daily spending number.")
    static var openAppWhenRun = true

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
