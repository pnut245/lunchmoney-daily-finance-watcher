import SwiftUI

struct ContentView: View {
    @StateObject private var model = AppViewModel()
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        ZStack {
            backgroundGradient
                .ignoresSafeArea()

            VStack(alignment: .leading, spacing: 0) {
                topBar
                Spacer(minLength: 18)
                heroBlock
                Spacer(minLength: 20)
                footerBlock
            }
            .padding(.horizontal, 22)
            .padding(.top, 18)
            .padding(.bottom, 22)
        }
        .task {
            await model.refreshIfNeeded(force: true)
        }
        .onChange(of: scenePhase) { _, newPhase in
            guard newPhase == .active else {
                return
            }
            Task {
                await model.refreshIfNeeded()
            }
        }
    }

    private var backgroundGradient: LinearGradient {
        SyzygyVisuals.backgroundGradient(for: model.snapshot)
    }

    private var ink: Color {
        SyzygyVisuals.ink(for: model.snapshot)
    }

    private var mutedInk: Color {
        SyzygyVisuals.mutedInk(for: model.snapshot)
    }

    private var topBar: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(model.heroEyebrow.uppercased())
                .font(.system(size: 13, weight: .black, design: .rounded))
                .tracking(1.6)

            RoundedRectangle(cornerRadius: 999)
                .fill(model.snapshot.isNegative ? Color.white : Color.red)
                .frame(width: 28, height: 5)
        }
        .foregroundStyle(ink)
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var heroBlock: some View {
        ZStack(alignment: .bottom) {
            Text(model.snapshot.displayNumber)
                .font(.system(size: 340, weight: .black, design: .default))
                .minimumScaleFactor(0.22)
                .lineLimit(1)
                .tracking(-16)
                .scaleEffect(x: 0.88, y: 1.0)
                .foregroundStyle(ink)
                .frame(maxWidth: .infinity, alignment: .center)

            SyzygyObjectView(snapshot: model.snapshot)
                .frame(width: 255, height: 220)
                .offset(x: objectOffset.width, y: objectOffset.height)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
    }

    private var footerBlock: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(model.snapshot.moneyObject.uppercased())
                .font(.system(size: 30, weight: .black, design: .rounded))
                .tracking(-0.8)
                .foregroundStyle(ink)

            if model.shouldShowStatusPill {
                Text(statusPillText.uppercased())
                    .font(.system(size: 11, weight: .black, design: .rounded))
                    .tracking(1.4)
                    .foregroundStyle(statusPillInk)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(statusPillBackground)
                    .clipShape(Capsule())
            }
        }
    }

    private var objectOffset: CGSize {
        if model.snapshot.isNegative {
            return CGSize(width: 24, height: 50)
        }
        switch model.snapshot.spendingState.uppercased() {
        case "PLENTY":
            return CGSize(width: -4, height: 52)
        case "COMFORTABLE":
            return CGSize(width: -6, height: 48)
        case "WATCH IT":
            return CGSize(width: 18, height: 44)
        case "TIGHT":
            return CGSize(width: 32, height: 46)
        default:
            return CGSize(width: 8, height: 48)
        }
    }

    private var statusPillText: String {
        if let updated = model.updatedText, !model.isRefreshing, model.errorText == nil {
            return "\(model.statusPillText) • \(updated)"
        }
        if let errorText = model.errorText {
            return "\(model.statusPillText) • \(errorText)"
        }
        return model.statusPillText
    }

    private var statusPillBackground: Color {
        if model.snapshot.isNegative {
            return Color.white.opacity(0.14)
        }
        if model.errorText != nil || model.snapshot.freshness == .stale || model.snapshot.freshness == .unknown {
            return Color.black.opacity(0.10)
        }
        return Color.black.opacity(0.06)
    }

    private var statusPillInk: Color {
        model.snapshot.isNegative ? .white : .black.opacity(0.7)
    }
}
