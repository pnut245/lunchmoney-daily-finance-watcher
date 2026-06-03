import Testing
import Foundation
@testable import OneNumberPhoneKit

@Test func decodesOneNumberSnapshot() throws {
    let json = """
    {
      "daily_allowance": 55,
      "today_discretionary_spend": 18,
      "remaining_today": 37,
      "is_negative": false,
      "last_updated": "2026-06-02T23:00:00"
    }
    """.data(using: .utf8)!

    let snapshot = try JSONDecoder().decode(LunchboxWidgetSnapshot.self, from: json)

    #expect(snapshot.dailyAllowance == 55)
    #expect(snapshot.todayDiscretionarySpend == 18)
    #expect(snapshot.remainingToday == 37)
    #expect(snapshot.isNegative == false)
    #expect(snapshot.displayNumber == "37")
}

@Test func negativeSnapshotDisplaysSignedNumber() {
    #expect(LunchboxWidgetSnapshot.negativePreview.displayNumber == "-12")
    #expect(LunchboxWidgetSnapshot.negativePreview.isNegative)
}
