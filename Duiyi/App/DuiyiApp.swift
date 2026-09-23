import SwiftUI

@main
struct DuiyiApp: App {
    @State private var environment: AppEnvironment
    @State private var coordinator = AppCoordinator()

    init() {
        AppLaunchTracker.shared.begin(.appInit)
        // Environment init stays on main but is now cheap: DeferredTaskStore does
        // zero I/O, audio/synthesizer are lazy (see their files).
        let env = AppEnvironment()
        _environment = State(initialValue: env)
        AppLaunchTracker.shared.begin(.environmentReady)
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(environment)
                .environment(coordinator)
                .preferredColorScheme(.dark)
        }
    }
}
