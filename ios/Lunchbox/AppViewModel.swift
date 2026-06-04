import Foundation
import WidgetKit

@MainActor
final class AppViewModel: ObservableObject {
    @Published var snapshot: LunchboxSnapshot
    @Published var snapshotURLString: String
    @Published var isRefreshing = false
    @Published var errorText: String?

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

    var suggestedDeviceURLString: String {
        DevHostConfig.suggestedDeviceURLString
    }

    func saveURL() {
        SnapshotStore.configuredURLString = snapshotURLString
        WidgetCenter.shared.reloadAllTimelines()
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
        errorText = nil
        defer { isRefreshing = false }

        do {
            let fetched = try await SnapshotFetcher.fetch(from: url)
            snapshot = fetched
            errorText = nil
            SnapshotStore.cache(snapshot: fetched)
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
