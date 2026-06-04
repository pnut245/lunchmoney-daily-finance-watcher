import Foundation

struct LunchboxSnapshot: Codable, Equatable {
    let dailyAllowance: Double
    let spentToday: Double
    let remainingToday: Double
    let isNegative: Bool
    let state: String
    let updatedAt: String

    private enum CodingKeys: String, CodingKey {
        case dailyAllowance = "daily_allowance"
        case spentToday = "spent_today"
        case remainingToday = "remaining_today"
        case isNegative = "is_negative"
        case state
        case updatedAt = "updated_at"
    }

    private enum LegacyCodingKeys: String, CodingKey {
        case todayDiscretionarySpend = "today_discretionary_spend"
        case lastUpdated = "last_updated"
    }

    init(
        dailyAllowance: Double,
        spentToday: Double,
        remainingToday: Double,
        isNegative: Bool,
        state: String,
        updatedAt: String
    ) {
        self.dailyAllowance = dailyAllowance
        self.spentToday = spentToday
        self.remainingToday = remainingToday
        self.isNegative = isNegative
        self.state = state
        self.updatedAt = updatedAt
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let legacyContainer = try decoder.container(keyedBy: LegacyCodingKeys.self)
        let dailyAllowance = try container.decodeIfPresent(Double.self, forKey: .dailyAllowance) ?? 0
        let spentToday = try container.decodeIfPresent(Double.self, forKey: .spentToday)
            ?? legacyContainer.decodeIfPresent(Double.self, forKey: .todayDiscretionarySpend)
            ?? 0
        let remainingToday = try container.decodeIfPresent(Double.self, forKey: .remainingToday) ?? 0
        let state = try container.decodeIfPresent(String.self, forKey: .state)
            ?? (remainingToday < 0 ? "negative" : "positive")
        let updatedAt = try container.decodeIfPresent(String.self, forKey: .updatedAt)
            ?? legacyContainer.decodeIfPresent(String.self, forKey: .lastUpdated)
            ?? ""
        let decodedIsNegative = try container.decodeIfPresent(Bool.self, forKey: .isNegative)
        let isNegative = decodedIsNegative ?? (remainingToday < 0)

        self.init(
            dailyAllowance: dailyAllowance,
            spentToday: spentToday,
            remainingToday: remainingToday,
            isNegative: isNegative,
            state: state,
            updatedAt: updatedAt
        )
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(dailyAllowance, forKey: .dailyAllowance)
        try container.encode(spentToday, forKey: .spentToday)
        try container.encode(remainingToday, forKey: .remainingToday)
        try container.encode(isNegative, forKey: .isNegative)
        try container.encode(state, forKey: .state)
        try container.encode(updatedAt, forKey: .updatedAt)
    }
}

extension LunchboxSnapshot {
    var displayNumber: String {
        Int(remainingToday.rounded()).formatted()
    }

    var updatedDate: Date? {
        ISO8601DateFormatter().date(from: updatedAt)
    }

    static let preview = LunchboxSnapshot(
        dailyAllowance: 55,
        spentToday: 18,
        remainingToday: 37,
        isNegative: false,
        state: "positive",
        updatedAt: "2026-06-02T23:00:00Z"
    )

    static let negativePreview = LunchboxSnapshot(
        dailyAllowance: 55,
        spentToday: 67,
        remainingToday: -12,
        isNegative: true,
        state: "negative",
        updatedAt: "2026-06-02T23:00:00Z"
    )
}
