import Foundation
import WidgetKit

@MainActor
final class AppViewModel: ObservableObject {
    enum StatusTone {
        case neutral
        case positive
        case caution
        case critical
    }

    @Published var snapshot: SyzygySnapshot
    @Published var snapshotURLString: String
    @Published var isRefreshing = false
    @Published var errorText: String?
    @Published var sourceEditorPresented = false
    private var lastRefreshAttempt = Date.distantPast

    init() {
        snapshot = SnapshotStore.loadCachedSnapshot() ?? .preview
        snapshotURLString = SnapshotStore.configuredURLString
        errorText = SnapshotStore.loadError()
    }

    var updatedText: String? {
        guard let updated = snapshot.updatedDate else {
            return nil
        }
        return "Updated \(updated.formatted(date: .omitted, time: .shortened))"
    }

    var freshnessTitle: String {
        switch snapshot.freshness {
        case .fresh:
            return "Live"
        case .aging:
            return "A little old"
        case .stale:
            return "Stale"
        case .unknown:
            return "Unknown"
        }
    }

    var freshnessDetail: String {
        guard let updated = snapshot.updatedDate else {
            return "No source timestamp yet."
        }
        let age = max(Int(Date().timeIntervalSince(updated)), 0)
        if age < 60 {
            return "Updated just now."
        }
        if age < 3600 {
            return "Updated \(age / 60) min ago."
        }
        return "Updated \(age / 3600)h ago."
    }

    var statusTitle: String {
        if isRefreshing {
            return "Refreshing"
        }
        if errorText != nil {
            return "Using last saved number"
        }
        return freshnessTitle
    }

    var statusDetail: String {
        if isRefreshing {
            return "Pulling the latest snapshot from this Mac."
        }
        if let errorText {
            return errorText
        }
        return freshnessDetail
    }

    var statusTone: StatusTone {
        if isRefreshing {
            return .neutral
        }
        if errorText != nil {
            return .critical
        }
        switch snapshot.freshness {
        case .fresh:
            return .positive
        case .aging:
            return .caution
        case .stale, .unknown:
            return .critical
        }
    }

    var heroEyebrow: String {
        snapshot.isNegative ? "Overspent today" : "Safe to spend"
    }

    var heroQualifier: String {
        snapshot.isNegative ? "over today" : "left today"
    }

    var shouldShowStatusPill: Bool {
        isRefreshing || errorText != nil || snapshot.freshness != .fresh
    }

    var statusPillText: String {
        if isRefreshing {
            return "Refreshing"
        }
        if errorText != nil {
            return "Offline"
        }
        switch snapshot.freshness {
        case .fresh:
            return "Live"
        case .aging:
            return "A little old"
        case .stale:
            return "Stale"
        case .unknown:
            return "Waiting"
        }
    }

    var heroSupportText: String {
        if isRefreshing {
            return "Refreshing your number."
        }
        if errorText != nil {
            return "Showing the last saved number."
        }
        switch snapshot.freshness {
        case .fresh:
            return "You can trust this read."
        case .aging:
            return "Still usable, but not fresh."
        case .stale:
            return "Check the portal before making a bigger call."
        case .unknown:
            return "Waiting for a clean timestamp."
        }
    }

    var footerMetrics: [(label: String, value: String)] {
        [
            ("Spent", snapshot.spentTodayText),
            ("Allowance", snapshot.dailyAllowanceText)
        ]
    }

    var sourceSummary: String {
        guard let url = SnapshotStore.configuredURL else {
            return "Source URL needs attention."
        }
        let host = url.host ?? "Unknown host"
        if host == "127.0.0.1" || host == "localhost" {
            return "Simulator source"
        }
        return "Reading from \(host)"
    }

    var helperText: String {
        if let url = SnapshotStore.configuredURL,
           let host = url.host,
           host != "127.0.0.1",
           host != "localhost" {
            return "Keep the phone and Mac on the same Wi-Fi so the number can stay current."
        }
        return "Use localhost only in Simulator. Real phones need this Mac's local network address."
    }

    var suggestedDeviceURLString: String {
        DevHostConfig.suggestedDeviceURLString
    }

    func applySuggestedDeviceURL() {
        snapshotURLString = suggestedDeviceURLString
    }

    func saveURL() {
        SnapshotStore.configuredURLString = snapshotURLString
        WidgetCenter.shared.reloadAllTimelines()
    }

    func refreshIfNeeded(force: Bool = false) async {
        let now = Date()
        if !force, now.timeIntervalSince(lastRefreshAttempt) < 30 {
            return
        }
        if force || errorText != nil || snapshot.freshness != .fresh {
            await refresh()
        }
    }

    func refresh() async {
        guard !isRefreshing else {
            return
        }

        saveURL()
        guard let url = SnapshotStore.configuredURL else {
            errorText = SnapshotError.invalidURL.localizedDescription
            SnapshotStore.saveError(errorText ?? "Invalid URL")
            return
        }

        isRefreshing = true
        lastRefreshAttempt = Date()
        errorText = nil
        defer { isRefreshing = false }

        do {
            let fetched = try await SnapshotFetcher.fetch(from: url)
            snapshot = fetched
            errorText = nil
            SnapshotStore.cache(snapshot: fetched)
            SnapshotStore.saveError("")
            WidgetCenter.shared.reloadAllTimelines()
        } catch {
            let message = userFacingError(for: error, url: url)
            errorText = message
            SnapshotStore.saveError(message)
        }
    }

    private func userFacingError(for error: Error, url: URL) -> String {
        let nsError = error as NSError
        if nsError.domain == NSURLErrorDomain {
            if nsError.code == URLError.notConnectedToInternet.rawValue || nsError.code == URLError.cannotFindHost.rawValue {
                if url.host == "127.0.0.1" || url.host == "localhost" {
                    return "Real iPhone devices cannot use localhost. Switch to this Mac's LAN IP."
                }
            }
            if nsError.code == URLError.appTransportSecurityRequiresSecureConnection.rawValue {
                return "HTTP was blocked. Use the built-in LAN URL button or confirm the app was rebuilt with the latest Info.plist."
            }
        }
        return error.localizedDescription
    }
}
