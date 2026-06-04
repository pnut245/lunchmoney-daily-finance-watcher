import Foundation

enum DevHostConfig {
    static let currentLANIP = "192.168.0.217"
    static let serverPort = 8422

    static var suggestedDeviceURLString: String {
        "http://\(currentLANIP):\(serverPort)/data/widget_snapshot.json"
    }
}
