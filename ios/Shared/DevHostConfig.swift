import Foundation

enum DevHostConfig {
    static let currentLANIP = "172.20.10.9"
    static let serverPort = 8422

    static var suggestedDeviceURLString: String {
        "http://\(currentLANIP):\(serverPort)/data/widget_snapshot.json"
    }
}
