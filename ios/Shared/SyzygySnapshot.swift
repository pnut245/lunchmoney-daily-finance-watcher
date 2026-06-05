import Foundation

struct SyzygySnapshot: Codable, Equatable {
    let dailyAllowance: Double
    let spentToday: Double
    let remainingToday: Double
    let isNegative: Bool
    let state: String
    let spendingState: String
    let moneyObject: String
    let updatedAt: String

    private enum CodingKeys: String, CodingKey {
        case dailyAllowance = "daily_allowance"
        case spentToday = "spent_today"
        case remainingToday = "remaining_today"
        case isNegative = "is_negative"
        case state
        case spendingState = "spending_state"
        case moneyObject = "money_object"
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
        spendingState: String,
        moneyObject: String,
        updatedAt: String
    ) {
        self.dailyAllowance = dailyAllowance
        self.spentToday = spentToday
        self.remainingToday = remainingToday
        self.isNegative = isNegative
        self.state = state
        self.spendingState = spendingState
        self.moneyObject = moneyObject
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
        let spendingState = try container.decodeIfPresent(String.self, forKey: .spendingState)
            ?? (remainingToday < 0 ? "OVERDRAWN" : "OK")
        let moneyObject = try container.decodeIfPresent(String.self, forKey: .moneyObject)
            ?? "Dinner"
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
            spendingState: spendingState,
            moneyObject: moneyObject,
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
        try container.encode(spendingState, forKey: .spendingState)
        try container.encode(moneyObject, forKey: .moneyObject)
        try container.encode(updatedAt, forKey: .updatedAt)
    }
}

extension SyzygySnapshot {
    enum Freshness {
        case fresh
        case aging
        case stale
        case unknown
    }

    var displayNumber: String {
        Int(remainingToday.rounded()).formatted()
    }

    var currencyNumber: String {
        "$\(displayNumber)"
    }

    var spentTodayText: String {
        "$\(Int(spentToday.rounded()).formatted())"
    }

    var dailyAllowanceText: String {
        "$\(Int(dailyAllowance.rounded()).formatted())"
    }

    var updatedDate: Date? {
        ISO8601DateFormatter().date(from: updatedAt)
    }

    var freshness: Freshness {
        guard let updatedDate else {
            return .unknown
        }
        let age = Date().timeIntervalSince(updatedDate)
        if age <= 90 * 60 {
            return .fresh
        }
        if age <= 6 * 60 * 60 {
            return .aging
        }
        return .stale
    }

    static let preview = SyzygySnapshot(
        dailyAllowance: 55,
        spentToday: 18,
        remainingToday: 37,
        isNegative: false,
        state: "positive",
        spendingState: "COMFORTABLE",
        moneyObject: "Dinner",
        updatedAt: "2026-06-02T23:00:00Z"
    )

    static let negativePreview = SyzygySnapshot(
        dailyAllowance: 55,
        spentToday: 67,
        remainingToday: -12,
        isNegative: true,
        state: "negative",
        spendingState: "OVERDRAWN",
        moneyObject: "No Spend",
        updatedAt: "2026-06-02T23:00:00Z"
    )
}
