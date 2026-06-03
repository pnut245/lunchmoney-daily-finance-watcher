import SwiftUI

@main
struct OneNumberTodayApp: App {
    private let store = OneNumberSnapshotStore()

    var body: some Scene {
        WindowGroup {
            OneNumberPhoneRootView(snapshot: store.loadSnapshot() ?? .preview)
        }
    }
}

struct OneNumberPhoneRootView: View {
    let snapshot: LunchboxWidgetSnapshot

    var body: some View {
        TabView {
            OneNumberTodayView(snapshot: snapshot)
                .tabItem {
                    Label("Today", systemImage: "number")
                }

            NavigationStack {
                OneNumberSettingsView(snapshot: snapshot)
            }
            .tabItem {
                Label("Settings", systemImage: "slider.horizontal.3")
            }

            NavigationStack {
                OneNumberVaultView()
            }
            .tabItem {
                Label("Vault", systemImage: "archivebox")
            }
        }
    }
}
