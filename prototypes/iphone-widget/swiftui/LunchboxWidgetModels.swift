import Foundation

struct LunchboxWidgetSnapshot: Codable, Equatable {
    let dailyAllowance: Double
    let todayDiscretionarySpend: Double
    let remainingToday: Double
    let isNegative: Bool
    let lastUpdated: String

    enum CodingKeys: String, CodingKey {
        case dailyAllowance = "daily_allowance"
        case todayDiscretionarySpend = "today_discretionary_spend"
        case remainingToday = "remaining_today"
        case isNegative = "is_negative"
        case lastUpdated = "last_updated"
    }
}

extension LunchboxWidgetSnapshot {
    var displayNumber: String {
        let rounded = Int(remainingToday.rounded())
        return rounded.formatted()
    }

    static let preview = LunchboxWidgetSnapshot(
        dailyAllowance: 55,
        todayDiscretionarySpend: 18,
        remainingToday: 37,
        isNegative: false,
        lastUpdated: "2026-06-02T23:00:00"
    )

    static let negativePreview = LunchboxWidgetSnapshot(
        dailyAllowance: 55,
        todayDiscretionarySpend: 67,
        remainingToday: -12,
        isNegative: true,
        lastUpdated: "2026-06-02T23:00:00"
    )
}
