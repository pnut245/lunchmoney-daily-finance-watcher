import SwiftUI

enum SyzygyVisuals {
    static func backgroundGradient(for snapshot: SyzygySnapshot) -> LinearGradient {
        LinearGradient(
            colors: palette(for: snapshot),
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }

    static func palette(for snapshot: SyzygySnapshot) -> [Color] {
        if snapshot.isNegative {
            return [
                Color(red: 0.25, green: 0.03, blue: 0.05),
                Color(red: 0.58, green: 0.05, blue: 0.08),
                Color(red: 0.92, green: 0.12, blue: 0.09)
            ]
        }

        switch snapshot.spendingState.uppercased() {
        case "PLENTY":
            return [
                Color(red: 0.98, green: 0.97, blue: 0.94),
                Color(red: 1.00, green: 1.00, blue: 0.98),
                Color(red: 0.96, green: 0.94, blue: 0.90)
            ]
        case "COMFORTABLE":
            return [
                Color(red: 0.77, green: 0.82, blue: 0.52),
                Color(red: 0.70, green: 0.75, blue: 0.44),
                Color(red: 0.88, green: 0.91, blue: 0.68)
            ]
        case "WATCH IT":
            return [
                Color(red: 1.00, green: 0.76, blue: 0.08),
                Color(red: 1.00, green: 0.80, blue: 0.19),
                Color(red: 0.96, green: 0.62, blue: 0.05)
            ]
        case "TIGHT":
            return [
                Color(red: 1.00, green: 0.44, blue: 0.02),
                Color(red: 1.00, green: 0.58, blue: 0.09),
                Color(red: 0.94, green: 0.27, blue: 0.01)
            ]
        default:
            return [
                Color(red: 0.98, green: 0.97, blue: 0.94),
                Color(red: 1.00, green: 1.00, blue: 0.98),
                Color(red: 0.96, green: 0.94, blue: 0.90)
            ]
        }
    }

    static func ink(for snapshot: SyzygySnapshot) -> Color {
        snapshot.isNegative ? .white : .black
    }

    static func mutedInk(for snapshot: SyzygySnapshot) -> Color {
        snapshot.isNegative ? Color.white.opacity(0.78) : Color.black.opacity(0.64)
    }
}

struct SyzygyObjectView: View {
    let snapshot: SyzygySnapshot
    var compact = false

    var body: some View {
        Image(assetName)
            .resizable()
            .scaledToFit()
            .scaleEffect(compact ? 0.82 : 1.0)
            .shadow(color: .black.opacity(snapshot.isNegative ? 0.26 : 0.18), radius: compact ? 12 : 20, y: compact ? 10 : 18)
    }

    private var assetName: String {
        if snapshot.isNegative {
            return snapshot.remainingToday <= -15 ? "wiltedPlant" : "lighter"
        }

        switch snapshot.spendingState.uppercased() {
        case "PLENTY":
            return "bike"
        case "COMFORTABLE":
            return "plant"
        case "WATCH IT":
            return "book"
        case "TIGHT":
            return "coffee"
        default:
            switch snapshot.moneyObject.lowercased() {
            case "coffee":
                return "coffee"
            case "lunch":
                return "burrito"
            case "groceries":
                return "plant"
            case "day out":
                return "bike"
            case "errands", "big spend", "dinner":
                return "book"
            default:
                return "plant"
            }
        }
    }
}
