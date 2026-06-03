import SwiftUI
import WidgetKit

struct ContentView: View {
    @StateObject private var model = AppViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    heroCard
                    controlsCard
                    instructionsCard
                }
                .padding(20)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Syzygy")
            .task {
                await model.refresh()
            }
        }
    }

    private var heroCard: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("SAFE TO SPEND")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(.secondary)
                    Text(model.snapshot.displayNumber)
                        .font(.system(size: 92, weight: .black, design: .rounded))
                        .minimumScaleFactor(0.4)
                        .lineLimit(1)
                    Text(model.snapshot.moneyObject.uppercased())
                        .font(.footnote.weight(.semibold))
                        .foregroundStyle(model.snapshot.isNegative ? .white.opacity(0.9) : .secondary)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 10) {
                    metricPill(title: model.snapshot.weekLabel, value: model.snapshot.weekAmount)
                    metricPill(title: model.snapshot.dopamineLabel, value: model.snapshot.dopamineAmount)
                    Text(model.snapshot.spendingState)
                        .font(.caption.weight(.bold))
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(.thinMaterial, in: Capsule())
                }
            }

            if let updated = model.updatedText {
                Text(updated)
                    .font(.footnote)
                    .foregroundStyle(model.snapshot.isNegative ? .white.opacity(0.85) : .secondary)
            }
        }
        .padding(22)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(model.snapshot.isNegative ? Color.red.opacity(0.88) : Color.white, in: RoundedRectangle(cornerRadius: 28, style: .continuous))
        .foregroundStyle(model.snapshot.isNegative ? .white : .black)
        .shadow(color: .black.opacity(0.08), radius: 24, y: 10)
    }

    private var controlsCard: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Snapshot Source")
                .font(.headline)

            TextField("http://...", text: $model.snapshotURLString, axis: .vertical)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .keyboardType(.URL)
                .padding(14)
                .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 16, style: .continuous))

            HStack(spacing: 12) {
                Button("Use Simulator Localhost") {
                    model.snapshotURLString = SnapshotStore.defaultURLString
                }
                .buttonStyle(.bordered)

                Button("Use This Mac IP") {
                    model.snapshotURLString = model.suggestedDeviceURLString
                }
                .buttonStyle(.bordered)

                Button("Save URL") {
                    model.saveURL()
                }
                .buttonStyle(.borderedProminent)
            }

            VStack(alignment: .leading, spacing: 6) {
                Text("Suggested iPhone URL")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.secondary)
                Text(model.suggestedDeviceURLString)
                    .font(.footnote.monospaced())
                    .textSelection(.enabled)
            }

            Button {
                Task {
                    await model.refresh()
                }
            } label: {
                if model.isRefreshing {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                } else {
                    Text("Fetch Now")
                        .frame(maxWidth: .infinity)
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(model.isRefreshing)

            if let errorText = model.errorText {
                Text(errorText)
                    .font(.footnote)
                    .foregroundStyle(.red)
            }
        }
        .padding(20)
        .background(Color.white, in: RoundedRectangle(cornerRadius: 24, style: .continuous))
    }

    private var instructionsCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("How To Use It")
                .font(.headline)
            Text("For Simulator, localhost works. For a real iPhone, replace localhost with this Mac's LAN IP and keep the snapshot file hosted here.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Text("Current Mac IP: \(DevHostConfig.currentLANIP)")
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Text("The widget reloads hourly and the app can force a fresh pull immediately.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .padding(20)
        .background(Color.white, in: RoundedRectangle(cornerRadius: 24, style: .continuous))
    }

    private func metricPill(title: String, value: Double) -> some View {
        VStack(alignment: .trailing, spacing: 2) {
            Text(title.uppercased())
                .font(.caption2.weight(.bold))
            Text("$\(Int(value.rounded()))")
                .font(.headline.weight(.black))
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(.thinMaterial, in: Capsule())
    }
}

#Preview {
    ContentView()
}
