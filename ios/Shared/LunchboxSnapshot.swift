import Foundation

struct LunchboxSnapshot: Codable, Equatable {
    let dailyAllowance: Double
    let todayDiscretionarySpend: Double
    let remainingToday: Double
    let isNegative: Bool
    let lastUpdated: String
    let todayLabel: String
    let todayAmount: Double
    let weekLabel: String
    let weekAmount: Double
    let dopamineLabel: String
    let dopamineAmount: Double
    let spendingState: String
    let moneyObject: String
    let vaultState: String
    let warningAlarms: Int
    let criticalAlarms: Int

    enum CodingKeys: String, CodingKey {
        case dailyAllowance = "daily_allowance"
        case todayDiscretionarySpend = "today_discretionary_spend"
        case remainingToday = "remaining_today"
        case isNegative = "is_negative"
        case lastUpdated = "last_updated"
        case todayLabel = "today_label"
        case todayAmount = "today_amount"
        case weekLabel = "week_label"
        case weekAmount = "week_amount"
        case dopamineLabel = "dopamine_label"
        case dopamineAmount = "dopamine_amount"
        case spendingState = "spending_state"
        case moneyObject = "money_object"
        case vaultState = "vault_state"
        case warningAlarms = "warning_alarms"
        case criticalAlarms = "critical_alarms"
    }
}

extension LunchboxSnapshot {
    var displayNumber: String {
        let rounded = Int(remainingToday.rounded())
        return rounded.formatted()
    }

    var updatedDate: Date? {
        ISO8601DateFormatter().date(from: lastUpdated)
    }

    func emphasisAmount(_ emphasis: WidgetEmphasis) -> Double {
        switch emphasis {
        case .today:
            return todayAmount
        case .dopamine:
            return dopamineAmount
        case .week:
            return weekAmount
        }
    }

    func emphasisLabel(_ emphasis: WidgetEmphasis) -> String {
        switch emphasis {
        case .today:
            return todayLabel
        case .dopamine:
            return dopamineLabel
        case .week:
            return weekLabel
        }
    }

    static let preview = LunchboxSnapshot(
        dailyAllowance: 55,
        todayDiscretionarySpend: 18,
        remainingToday: 37,
        isNegative: false,
        lastUpdated: "2026-06-02T23:00:00Z",
        todayLabel: "Today",
        todayAmount: 37,
        weekLabel: "Week",
        weekAmount: 185,
        dopamineLabel: "Dopamine",
        dopamineAmount: 31,
        spendingState: "OK",
        moneyObject: "Dinner",
        vaultState: "SAFE",
        warningAlarms: 1,
        criticalAlarms: 0
    )

    static let negativePreview = LunchboxSnapshot(
        dailyAllowance: 55,
        todayDiscretionarySpend: 67,
        remainingToday: -12,
        isNegative: true,
        lastUpdated: "2026-06-02T23:00:00Z",
        todayLabel: "Today",
        todayAmount: -12,
        weekLabel: "Week",
        weekAmount: 0,
        dopamineLabel: "Dopamine",
        dopamineAmount: 0,
        spendingState: "NEGATIVE",
        moneyObject: "No Spend",
        vaultState: "LOW",
        warningAlarms: 0,
        criticalAlarms: 2
    )
}

enum WidgetEmphasis: String, Codable, CaseIterable {
    case today
    case dopamine
    case week
}
