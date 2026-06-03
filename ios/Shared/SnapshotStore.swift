import Foundation

enum SnapshotStore {
    static let snapshotURLKey = "snapshot_url"
    static let cachedSnapshotKey = "cached_snapshot_json"
    static let lastErrorKey = "last_snapshot_error"

    static var defaults: UserDefaults {
        .standard
    }

    static var configuredURLString: String {
        get {
            let stored = defaults.string(forKey: snapshotURLKey)
            if let stored, !stored.isEmpty {
                return stored
            }
            return defaultURLString
        }
        set {
            defaults.set(newValue, forKey: snapshotURLKey)
        }
    }

    static var defaultURLString: String {
        #if targetEnvironment(simulator)
        "http://127.0.0.1:8422/data/widget_snapshot.json"
        #else
        DevHostConfig.suggestedDeviceURLString
        #endif
    }

    static var configuredURL: URL? {
        URL(string: configuredURLString.trimmingCharacters(in: .whitespacesAndNewlines))
    }

    static func loadCachedSnapshot() -> LunchboxSnapshot? {
        guard let data = defaults.data(forKey: cachedSnapshotKey) else {
            return nil
        }
        return try? JSONDecoder().decode(LunchboxSnapshot.self, from: data)
    }

    static func cache(snapshot: LunchboxSnapshot) {
        guard let data = try? JSONEncoder().encode(snapshot) else {
            return
        }
        defaults.set(data, forKey: cachedSnapshotKey)
        defaults.removeObject(forKey: lastErrorKey)
    }

    static func saveError(_ message: String) {
        defaults.set(message, forKey: lastErrorKey)
    }

    static func loadError() -> String? {
        defaults.string(forKey: lastErrorKey)
    }
}
