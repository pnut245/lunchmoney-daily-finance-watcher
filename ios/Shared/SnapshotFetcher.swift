import Foundation

enum SnapshotFetcher {
    static func fetch(from url: URL) async throws -> LunchboxSnapshot {
        let request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 15)
        let config = URLSessionConfiguration.ephemeral
        config.waitsForConnectivity = true
        let session = URLSession(configuration: config)
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, (200 ... 299).contains(http.statusCode) else {
            throw SnapshotError.invalidResponse
        }
        return try JSONDecoder().decode(LunchboxSnapshot.self, from: data)
    }
}

enum SnapshotError: LocalizedError {
    case invalidURL
    case invalidResponse
    case lanAccessHint

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Snapshot URL is invalid."
        case .invalidResponse:
            return "Snapshot endpoint returned an invalid response."
        case .lanAccessHint:
            return "If this is a real iPhone, allow Local Network access and use this Mac's LAN IP instead of localhost."
        }
    }
}
