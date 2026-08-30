import SwiftUI

@main
struct DuiyiApp: App {
    @State private var environment = AppEnvironment()
    @State private var coordinator = AppCoordinator()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(environment)
                .environment(coordinator)
                .preferredColorScheme(.dark)
        }
    }
}
