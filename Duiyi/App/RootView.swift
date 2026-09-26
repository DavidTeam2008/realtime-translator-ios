import SwiftUI

struct RootView: View {
    @Environment(AppEnvironment.self) private var environment
    @Environment(AppCoordinator.self) private var coordinator
    @Environment(\.scenePhase) private var scenePhase
    @State private var conversationViewModel: ConversationViewModel?
    @State private var interpretationViewModel: InterpretationViewModel?
    @State private var meetingViewModel: MeetingViewModel?
    @State private var historyViewModel: HistoryViewModel?
    @State private var onboardingViewModel: OnboardingViewModel?

    var body: some View {
        let _ = AppLaunchTracker.shared.beginOnce(.rootBody)
        @Bindable var coordinator = coordinator
        NavigationStack(path: $coordinator.path) {
            HomeView()
                .navigationDestination(for: AppRoute.self) { route in
                    destination(for: route)
                }
        }
        .fullScreenCover(isPresented: onboardingPresented) {
            if let onboardingViewModel {
                OnboardingView(viewModel: onboardingViewModel)
            } else {
                Tokens.canvas.ignoresSafeArea()
            }
        }
        .onAppear {
            AppLaunchTracker.shared.begin(.rootAppear)
            ensureOnboardingViewModel()
            // Defer one runloop turn so we measure post-commit, approximating
            // CA::Transaction::commit (see Douyin实战篇无侵入方案).
            DispatchQueue.main.async {
                AppLaunchTracker.shared.markFirstFrame()
            }
        }
        .task(priority: .utility) {
            // Post-first-frame prewarm (off critical path):
            // VMs themselves are cheap, but touching their code pages + store
            // should not happen before Home paints.
            if let deferred = environment.taskStore as? DeferredTaskStore {
                await deferred.warm()
            }
            rebuildViewModelsIfNeeded()
            AppLaunchTracker.shared.begin(.viewModelsReady)
        }
        .onChange(of: environment.preferences.hasCompletedOnboarding) { _, completed in
            if completed {
                rebuildViewModelsIfNeeded()
            } else {
                onboardingViewModel = OnboardingViewModel(environment: environment)
            }
        }
        .onChange(of: scenePhase) { _, phase in
            if phase != .active {
                Task {
                    await conversationViewModel?.stop(restoreIdleTimerAfterDelay: false)
                    await interpretationViewModel?.stop(restoreIdleTimerAfterDelay: false)
                    await meetingViewModel?.stop(restoreIdleTimerAfterDelay: false)
                }
            }
        }
    }

    private var onboardingPresented: Binding<Bool> {
        Binding(
            get: { !environment.preferences.hasCompletedOnboarding },
            set: { presented in
                if !presented {
                    environment.preferences.hasCompletedOnboarding = true
                }
            }
        )
    }

    @ViewBuilder
    private func destination(for route: AppRoute) -> some View {
        switch route {
        case .conversation:
            if let conversationViewModel {
                ConversationView(viewModel: conversationViewModel)
            } else {
                // Lazy fallback: user navigated before post-frame prewarm finished.
                Tokens.canvas.ignoresSafeArea()
                    .task { conversationViewModel = makeConversationViewModel() }
            }
        case .interpretation:
            if let interpretationViewModel {
                InterpretationView(viewModel: interpretationViewModel)
            } else {
                Tokens.userPane.ignoresSafeArea()
                    .task { interpretationViewModel = makeInterpretationViewModel() }
            }
        case .meeting:
            if let meetingViewModel {
                MeetingView(viewModel: meetingViewModel)
            } else {
                Tokens.userPane.ignoresSafeArea()
                    .task { meetingViewModel = makeMeetingViewModel() }
            }
        case .history:
            if let historyViewModel {
                HistoryView(viewModel: historyViewModel)
            } else {
                Tokens.canvas.ignoresSafeArea()
                    .task { historyViewModel = HistoryViewModel(store: environment.taskStore) }
            }
        case .taskDetail(let id):
            TaskDetailView(taskID: id)
        }
    }

    private func ensureOnboardingViewModel() {
        if !environment.preferences.hasCompletedOnboarding, onboardingViewModel == nil {
            onboardingViewModel = OnboardingViewModel(environment: environment)
        }
    }

    /// Post-first-frame only. VM inits are cheap but page in feature code;
    /// keep them off the first-frame transaction.
    private func rebuildViewModelsIfNeeded() {
        if environment.preferences.hasCompletedOnboarding {
            if conversationViewModel == nil {
                conversationViewModel = makeConversationViewModel()
            }
            if interpretationViewModel == nil {
                interpretationViewModel = makeInterpretationViewModel()
            }
            if meetingViewModel == nil {
                meetingViewModel = makeMeetingViewModel()
            }
            if historyViewModel == nil {
                historyViewModel = HistoryViewModel(store: environment.taskStore)
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
            summarizer: environment.summarizer,
            audioSession: environment.audioSession,
            taskStore: environment.taskStore
        )
    }

    private func makeInterpretationViewModel() -> InterpretationViewModel {
        InterpretationViewModel(
            speech: environment.speechEngine,
            permissions: environment.permissions,
            preferences: environment.preferences,
            summarizer: environment.summarizer,
            audioSession: environment.audioSession,
            synthesizer: environment.synthesizer,
            taskStore: environment.taskStore
        )
    }

    private func makeMeetingViewModel() -> MeetingViewModel {
        MeetingViewModel(
            speech: environment.speechEngine,
            permissions: environment.permissions,
            preferences: environment.preferences,
            summarizer: environment.summarizer,
            audioSession: environment.audioSession,
            taskStore: environment.taskStore
        )
    }
}
