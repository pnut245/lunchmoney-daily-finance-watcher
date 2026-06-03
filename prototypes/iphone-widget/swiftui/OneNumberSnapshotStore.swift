import Foundation

struct OneNumberSnapshotStore {
    static let appGroupIdentifier = "group.com.pnut245.one-number-today"
    static let snapshotFileName = "budget_state.json"

    var fileManager: FileManager = .default
    var decoder: JSONDecoder = JSONDecoder()

    func loadSnapshot() -> LunchboxWidgetSnapshot? {
        guard let url = snapshotURL else {
            return nil
        }
        return loadSnapshot(from: url)
    }

    func loadSnapshot(from url: URL) -> LunchboxWidgetSnapshot? {
        guard let data = try? Data(contentsOf: url) else {
            return nil
        }
        return try? decoder.decode(LunchboxWidgetSnapshot.self, from: data)
    }

    var snapshotURL: URL? {
        fileManager
            .containerURL(forSecurityApplicationGroupIdentifier: Self.appGroupIdentifier)?
            .appendingPathComponent(Self.snapshotFileName)
    }
}
