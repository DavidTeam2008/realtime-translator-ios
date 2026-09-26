import SwiftUI

struct HomeView: View {
    @Environment(AppEnvironment.self) private var environment
    @Environment(AppCoordinator.self) private var coordinator

    @State private var unfinished: [TaskSession] = []
    @State private var isSettingsPresented = false

    private var language: AppLanguage { environment.preferences.userLanguage }

    var body: some View {
        let _ = AppLaunchTracker.shared.beginOnce(.homeBody)
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(Copy.homeTitle(for: language))
                            .font(.largeTitle.weight(.semibold))
                            .foregroundStyle(Tokens.textPrimary)
                    }
                    Spacer()
                    Button {
                        isSettingsPresented = true
                    } label: {
                        Image(systemName: "gearshape")
                            .font(.system(size: 18, weight: .semibold))
                            .foregroundStyle(Tokens.textSecondary)
                            .frame(width: 44, height: 44)
                    }
                    .accessibilityLabel(Copy.settingsTitle(for: language))
                }

                if !unfinished.isEmpty {
                    Text(Copy.unfinishedTasks(for: language))
                        .font(.footnote)
                        .foregroundStyle(Tokens.listen)
                    ForEach(unfinished) { task in
                        Button {
                            environment.preferences.appMode = task.feature.appMode
                            coordinator.open(task.feature.route)
                        } label: {
                            HistoryRow(task: task, language: language)
                        }
                        .buttonStyle(.plain)
                    }
                }

                ForEach(FeatureRegistry.visible) { feature in
                    HomeModuleCard(
                        title: feature.title(language),
                        subtitle: feature.subtitle(language),
                        symbolName: feature.symbolName,
                        background: Tokens.featureCard(feature.id),
                        accent: Tokens.featureAccent(feature.id)
                    ) {
                        environment.preferences.appMode = feature.id.appMode
                        coordinator.open(feature.id.route)
                    }
                    .accessibilityIdentifier("home-module-\(feature.id.rawValue)")
                    .accessibilityLabel(feature.title(language))
                    .accessibilityHint(feature.subtitle(language))
                }

                HomeModuleCard(
                    title: Copy.historyTitle(for: language),
                    subtitle: Copy.historySubtitle(for: language),
                    symbolName: "clock.arrow.circlepath",
                    background: Tokens.sheet,
                    accent: Tokens.textSecondary
                ) {
                    coordinator.open(.history)
                }
                .accessibilityIdentifier("home-history")
                .accessibilityLabel(Copy.historyTitle(for: language))
                .accessibilityHint(Copy.historySubtitle(for: language))
            }
            .padding(.horizontal, 20)
            .padding(.top, 12)
            .padding(.bottom, 32)
        }
        .background(Tokens.canvas.ignoresSafeArea())
        .navigationBarTitleDisplayMode(.inline)
        .toolbar(.hidden, for: .navigationBar)
        .onAppear { AppLaunchTracker.shared.begin(.homeAppear) }
        .task(priority: .utility) {
            // Deferred: let Home paint empty first, then fill unfinished tasks.
            // Triggers DeferredTaskStore resolve off the first-frame transaction.
            AppLaunchTracker.shared.begin(.homeTaskStart)
            unfinished = await environment.taskStore.unfinishedTasks()
            AppLaunchTracker.shared.begin(.homeTaskEnd)
        }
        .sheet(isPresented: $isSettingsPresented) {
            HomeSettingsSheet()
        }
        .preferredColorScheme(.dark)
    }
}

#Preview("Home") {
    HomePreview.root
}

@MainActor
enum HomePreview {
    static var root: some View {
        let preferences = PreferencesStore(defaults: UserDefaults(suiteName: "duiyi.home.preview") ?? .standard)
        preferences.userLanguage = .zhHans
        let environment = AppEnvironment(
            preferences: preferences,
            taskStore: InMemoryTaskStore()
        )
        return NavigationStack {
            HomeView()
        }
        .environment(environment)
        .environment(AppCoordinator())
    }
}
