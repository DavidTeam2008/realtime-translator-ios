import SwiftUI

struct RootView: View {
    @Environment(AppEnvironment.self) private var environment
    @Environment(\.scenePhase) private var scenePhase
    @State private var conversationViewModel: ConversationViewModel?
    @State private var onboardingViewModel: OnboardingViewModel?

    var body: some View {
        Group {
            switch route {
            case .conversation:
                if let conversationViewModel {
                    ConversationView(viewModel: conversationViewModel)
                } else {
                    Tokens.canvas.ignoresSafeArea()
                }
            case .onboarding:
                if let onboardingViewModel {
                    OnboardingView(viewModel: onboardingViewModel)
                } else {
                    Tokens.canvas.ignoresSafeArea()
                }
            }
        }
        .onAppear {
            rebuildViewModelsIfNeeded()
        }
        .onChange(of: environment.preferences.hasCompletedOnboarding) { _, completed in
            if completed {
                conversationViewModel = makeConversationViewModel()
            } else {
                onboardingViewModel = OnboardingViewModel(environment: environment)
            }
        }
        .onChange(of: scenePhase) { _, phase in
            if phase != .active {
                Task { await conversationViewModel?.stop(restoreIdleTimerAfterDelay: false) }
            }
        }
    }

    private var route: AppRoute {
        environment.preferences.hasCompletedOnboarding ? .conversation : .onboarding
    }

    private func rebuildViewModelsIfNeeded() {
        if environment.preferences.hasCompletedOnboarding {
            if conversationViewModel == nil {
                conversationViewModel = makeConversationViewModel()
            }
        } else if onboardingViewModel == nil {
            onboardingViewModel = OnboardingViewModel(environment: environment)
        }
    }

    private func makeConversationViewModel() -> ConversationViewModel {
        ConversationViewModel(
            speech: environment.speechEngine,
            permissions: environment.permissions,
            preferences: environment.preferences,
            summarizer: environment.summarizer
        )
    }
}
