import SwiftUI

struct OneNumberTodayView: View {
    let snapshot: LunchboxWidgetSnapshot

    var body: some View {
        ZStack {
            background.ignoresSafeArea()

            VStack(spacing: 0) {
                HStack {
                    Text("SAFE TO SPEND")
                    Spacer()
                    Text(updatedText)
                }
                .font(.system(size: 12, weight: .heavy))
                .tracking(1.8)
                .foregroundStyle(snapshot.isNegative ? .white.opacity(0.72) : .black.opacity(0.48))
                .padding(.horizontal, 22)
                .padding(.top, 18)

                Spacer(minLength: 0)

                Text(snapshot.displayNumber)
                    .font(.system(size: 228, weight: .black, design: .default))
                    .minimumScaleFactor(0.2)
                    .lineLimit(1)
                    .foregroundStyle(snapshot.isNegative ? .white : .black)
                    .padding(.horizontal, 18)
                    .accessibilityLabel("Safe to spend \(snapshot.displayNumber)")

                Spacer(minLength: 0)
            }
        }
    }

    private var background: Color {
        snapshot.isNegative ? Color(red: 0.84, green: 0.1, blue: 0.13) : .white
    }

    private var updatedText: String {
        guard let date = ISO8601DateFormatter().date(from: snapshot.lastUpdated) else {
            return "UPDATED"
        }
        return "UPDATED " + date.formatted(.dateTime.hour().minute())
    }
}

struct OneNumberSettingsView: View {
    var snapshot: LunchboxWidgetSnapshot

    var body: some View {
        Form {
            Section("Daily Allowance") {
                Text("$\(Int(snapshot.dailyAllowance.rounded()))")
            }
            Section("Today") {
                LabeledContent("Spent", value: "$\(Int(snapshot.todayDiscretionarySpend.rounded()))")
                LabeledContent("Remaining", value: snapshot.displayNumber)
            }
            Section("Data") {
                Text("Settings are generated from config/budget.yaml for this prototype.")
            }
        }
        .navigationTitle("Settings")
    }
}

struct OneNumberVaultView: View {
    var body: some View {
        List {
            Text("Month-end results will appear here after the ledger is synced into the app group.")
        }
        .navigationTitle("Vault")
    }
}

#Preview("Positive") {
    OneNumberTodayView(snapshot: .preview)
}

#Preview("Negative") {
    OneNumberTodayView(snapshot: .negativePreview)
}
