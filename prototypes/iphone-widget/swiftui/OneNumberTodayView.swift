import SwiftUI

struct OneNumberTodayView: View {
    let snapshot: LunchboxWidgetSnapshot

    var body: some View {
        GeometryReader { geometry in
            ZStack {
                background.ignoresSafeArea()

                VStack(spacing: 0) {
                    HStack(alignment: .firstTextBaseline) {
                        Text(statusText)
                        Spacer(minLength: 16)
                        Text(updatedText)
                    }
                    .font(.system(size: 11, weight: .heavy))
                    .tracking(1.7)
                    .foregroundStyle(secondaryColor)
                    .padding(.horizontal, 22)
                    .padding(.top, 18)

                    Spacer(minLength: 0)

                    Text(snapshot.displayNumber)
                        .font(.system(size: numberSize(for: geometry.size), weight: .black, design: .default))
                        .monospacedDigit()
                        .minimumScaleFactor(0.2)
                        .lineLimit(1)
                        .foregroundStyle(primaryColor)
                        .padding(.horizontal, 18)
                        .accessibilityLabel(accessibilityText)

                    Spacer(minLength: 0)
                }
            }
        }
    }

    private var background: Color {
        snapshot.isNegative ? Color(red: 0.84, green: 0.1, blue: 0.13) : .white
    }

    private var primaryColor: Color {
        snapshot.isNegative ? .white : .black
    }

    private var secondaryColor: Color {
        primaryColor.opacity(snapshot.isNegative ? 0.74 : 0.48)
    }

    private var statusText: String {
        snapshot.isNegative ? "OVER TODAY" : "SAFE TO SPEND"
    }

    private var updatedText: String {
        guard let date = Self.snapshotDate(snapshot.lastUpdated) else {
            return "UPDATED"
        }
        return date.formatted(.dateTime.hour().minute())
    }

    private var accessibilityText: String {
        snapshot.isNegative ? "Over today by \(snapshot.displayNumber)" : "Safe to spend \(snapshot.displayNumber)"
    }

    private func numberSize(for size: CGSize) -> CGFloat {
        min(232, max(162, size.width * 0.6))
    }

    private static func snapshotDate(_ value: String) -> Date? {
        if let date = ISO8601DateFormatter().date(from: value) {
            return date
        }

        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return formatter.date(from: value)
    }
}

struct OneNumberSettingsView: View {
    var snapshot: LunchboxWidgetSnapshot

    var body: some View {
        Form {
            Section("Today") {
                LabeledContent("Remaining", value: dollars(snapshot.remainingToday))
                LabeledContent("Spent", value: "$\(Int(snapshot.todayDiscretionarySpend.rounded()))")
                LabeledContent("Daily", value: dollars(snapshot.dailyAllowance))
            }

            Section("Status") {
                LabeledContent("State", value: snapshot.isNegative ? "Over" : "Clear")
                LabeledContent("Updated", value: updatedText)
            }
        }
        .navigationTitle("Settings")
    }

    private var updatedText: String {
        guard let date = ISO8601DateFormatter().date(from: snapshot.lastUpdated) ?? fallbackDate else {
            return "Unknown"
        }
        return date.formatted(.dateTime.month(.abbreviated).day().hour().minute())
    }

    private var fallbackDate: Date? {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return formatter.date(from: snapshot.lastUpdated)
    }

    private func dollars(_ value: Double) -> String {
        "$\(Int(value.rounded()).formatted())"
    }
}

struct OneNumberVaultView: View {
    var body: some View {
        VStack(spacing: 14) {
            Image(systemName: "archivebox")
                .font(.system(size: 34, weight: .semibold))
                .foregroundStyle(.secondary)

            Text("No vault entries yet")
                .font(.headline)
                .foregroundStyle(.primary)

            Text("Month-end results will show up here.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(red: 0.96, green: 0.96, blue: 0.95))
        .navigationTitle("Vault")
    }
}

#Preview("Positive") {
    OneNumberTodayView(snapshot: .preview)
}

#Preview("Negative") {
    OneNumberTodayView(snapshot: .negativePreview)
}
