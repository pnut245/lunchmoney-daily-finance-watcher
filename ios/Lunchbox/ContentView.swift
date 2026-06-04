import SwiftUI

struct ContentView: View {
    @StateObject private var model = AppViewModel()
    @State private var portalPresented = false

    var body: some View {
        NavigationStack {
            ZStack {
                backgroundColor
                    .ignoresSafeArea()

                VStack {
                    header
                    Spacer()
                    Text(model.snapshot.displayNumber)
                        .font(.system(size: 220, weight: .black, design: .default))
                        .minimumScaleFactor(0.18)
                        .lineLimit(1)
                        .tracking(-12)
                        .scaleEffect(x: 0.92, y: 1.0)
                        .foregroundStyle(numberColor)
                    Spacer()
                }
                .padding(.horizontal, 20)
                .padding(.vertical, 24)
            }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Portal") {
                        portalPresented = true
                    }
                    .font(.caption.weight(.bold))
                    .foregroundStyle(numberColor.opacity(0.52))
                }
            }
            .task {
                await model.refresh()
            }
            .sheet(isPresented: $portalPresented) {
                PortalSheet(model: model)
            }
        }
    }

    private var backgroundColor: Color {
        model.snapshot.isNegative ? Color(red: 0.88, green: 0.02, blue: 0.0) : .white
    }

    private var numberColor: Color {
        model.snapshot.isNegative ? .white : Color(red: 0.02, green: 0.02, blue: 0.02)
    }

    private var header: some View {
        HStack {
            if let updated = model.updatedText {
                Text(updated)
                    .font(.caption.weight(.bold))
                    .textCase(.uppercase)
                    .tracking(2)
                    .foregroundStyle(numberColor.opacity(0.52))
            }
            Spacer()
        }
    }
}

private struct PortalSheet: View {
    @ObservedObject var model: AppViewModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    Text("Portal")
                        .font(.system(size: 52, weight: .black))
                        .tracking(-3)

                    Text("Use this intentionally. The daily surface stays simple so you only need to hold one number in your head today.")
                        .foregroundStyle(.secondary)

                    VStack(alignment: .leading, spacing: 14) {
                        portalRow(label: "Daily allowance", value: "$\(Int(model.snapshot.dailyAllowance.rounded()))")
                        portalRow(label: "Spent today", value: "$\(Int(model.snapshot.spentToday.rounded()))")
                        portalRow(label: "Remaining today", value: model.snapshot.displayNumber)
                        portalRow(label: "Updated", value: model.updatedText ?? "Unknown")
                    }

                    VStack(alignment: .leading, spacing: 10) {
                        Text("Snapshot Source")
                            .font(.caption.weight(.bold))
                            .textCase(.uppercase)
                            .tracking(1.5)
                            .foregroundStyle(.secondary)

                        TextField("http://...", text: $model.snapshotURLString, axis: .vertical)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .keyboardType(.URL)
                            .padding(16)
                            .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 20, style: .continuous))

                        Button("Use This Mac IP") {
                            model.snapshotURLString = model.suggestedDeviceURLString
                        }
                        .buttonStyle(.bordered)

                        HStack(spacing: 12) {
                            Button("Save URL") {
                                model.saveURL()
                            }
                            .buttonStyle(.bordered)

                            Button {
                                Task {
                                    await model.refresh()
                                }
                            } label: {
                                if model.isRefreshing {
                                    ProgressView()
                                } else {
                                    Text("Refresh")
                                }
                            }
                            .buttonStyle(.borderedProminent)
                            .disabled(model.isRefreshing)
                        }

                        if let errorText = model.errorText {
                            Text(errorText)
                                .font(.footnote)
                                .foregroundStyle(.red)
                        }
                    }
                }
                .padding(24)
            }
            .navigationTitle("Portal")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
        }
    }

    private func portalRow(label: String, value: String) -> some View {
        HStack {
            Text(label)
                .foregroundStyle(.secondary)
            Spacer()
            Text(value)
                .fontWeight(.bold)
        }
        .padding(.vertical, 4)
    }
}

#Preview {
    ContentView()
}
