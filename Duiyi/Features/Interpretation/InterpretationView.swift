import SwiftUI
import UIKit

struct InterpretationView: View {
    @Environment(AppEnvironment.self) private var environment
    @Environment(AppCoordinator.self) private var coordinator
    @Bindable var viewModel: InterpretationViewModel

    @State private var isRedownloading = false
    @State private var shouldPrepareTranslation = false
    @State private var speechProgress: Double = 0
    @State private var redownloadError: String?
    @State private var picking: DirectionPick?
    @State private var lastPreparedKey = ""
    @State private var confirmNewTask = false
    @State private var confirmEndTask = false

    var body: some View {
        ZStack(alignment: .bottom) {
            VStack(spacing: 0) {
                ModuleChrome(
                    title: Copy.interpretationTitle(for: viewModel.targetLanguage),
                    language: viewModel.targetLanguage,
                    onHome: { coordinator.popToHome() },
                    onHistory: { coordinator.open(.history) }
                )
                TaskBar(
                    language: viewModel.targetLanguage,
                    statusText: TaskStatusText.make(
                        hasTask: viewModel.hasActiveTask,
                        startedAt: viewModel.taskStartedAt,
                        language: viewModel.targetLanguage
                    ),
                    isActive: viewModel.hasActiveTask,
                    onNewTask: { requestNewTask() },
                    onEndTask: { confirmEndTask = true }
                )
                DirectionBar(
                    sourceLanguage: viewModel.sourceLanguage,
                    targetLanguage: viewModel.targetLanguage,
                    viewerLanguage: viewModel.targetLanguage,
                    picking: picking,
                    onPickSource: { openPicker(.source) },
                    onPickTarget: { openPicker(.target) },
                    onSwap: {
                        picking = nil
                        withAnimation(.easeInOut(duration: 0.25)) {
                            viewModel.swapDirection()
                        }
                    }
                )
                .padding(.bottom, 8)

                if let picking {
                    languagePicker(for: picking)
                } else {
                    captionColumn
                }

                ListeningControl(
                    sessionState: viewModel.sessionState,
                    label: viewModel.controlLabel,
                    swapLabel: Copy.swapDirection(for: viewModel.targetLanguage),
                    settingsLabel: Copy.settingsTitle(for: viewModel.targetLanguage),
                    settingsHint: Copy.settingsHint(for: viewModel.targetLanguage),
                    isEnabled: viewModel.hasActiveTask,
                    onTap: {
                        guard picking == nil else {
                            picking = nil
                            return
                        }
                        guard viewModel.sessionState != .preparing else { return }
                        Task { await viewModel.toggleListening() }
                    },
                    onOpenSettings: {
                        picking = nil
                        withAnimation(.easeOut(duration: 0.22)) {
                            viewModel.isSettingsPresented = true
                        }
                    },
                    onSwap: {
                        picking = nil
                        withAnimation(.easeInOut(duration: 0.25)) {
                            viewModel.swapDirection()
                        }
                    }
                )

                VoiceOutControl(
                    label: viewModel.voiceOutLabel,
                    isEnabled: viewModel.voiceOutEnabled,
                    isBlocked: viewModel.isVoiceOutBlocked,
                    action: {
                        Task { await viewModel.setVoiceOutEnabled(!viewModel.voiceOutEnabled) }
                    }
                )
                .padding(.bottom, max(16, ScreenSafeArea.bottom))
            }
            .padding(.top, ScreenSafeArea.top)
            .frame(maxWidth: .infinity, maxHeight: .infinity)

            if viewModel.isSettingsPresented {
                InterpretationSettingsSheet(
                    viewerLanguage: viewModel.targetLanguage,
                    appMode: environment.preferences.appMode,
                    sourceLanguage: viewModel.sourceLanguage,
                    targetLanguage: viewModel.targetLanguage,
                    fontSize: viewModel.fontSize,
                    voiceOutEnabled: viewModel.voiceOutEnabled,
                    showsSourceLine: viewModel.showsSourceLine,
                    isVoiceOutBlocked: viewModel.isVoiceOutBlocked,
                    isRedownloading: isRedownloading,
                    speechProgress: speechProgress,
                    translationProgress: translationProgress,
                    redownloadError: redownloadError,
                    canSummarize: viewModel.canSummarize,
                    onSelectMode: selectMode,
                    onSelectSourceLanguage: applySourceLanguage,
                    onSelectTargetLanguage: applyTargetLanguage,
                    onSelectFont: viewModel.setFontSize,
                    onToggleVoiceOut: { enabled in
                        Task { await viewModel.setVoiceOutEnabled(enabled) }
                    },
                    onToggleSourceLine: viewModel.setShowsSourceLine,
                    onClear: viewModel.resetCaptions,
                    onSummarize: {
                        Task { await viewModel.requestSummary() }
                    },
                    onRedownload: {
                        Task { await redownloadModels() }
                    },
                    onDone: {
                        withAnimation(.easeOut(duration: 0.18)) {
                            viewModel.isSettingsPresented = false
                        }
                    }
                )
                .transition(.move(edge: .bottom).combined(with: .opacity))
            }

            if viewModel.isSummaryPresented {
                SummarySheet(
                    language: viewModel.targetLanguage,
                    availability: viewModel.summaryAvailability,
                    isLoading: viewModel.isSummarizing,
                    summary: viewModel.summary,
                    errorText: viewModel.summaryError,
                    exportTask: viewModel.exportableSession,
                    exporter: environment.exporter,
                    onCopy: copySummary,
                    onClose: {
                        withAnimation(.easeOut(duration: 0.18)) {
                            viewModel.isSummaryPresented = false
                        }
                    }
                )
                .transition(.move(edge: .bottom).combined(with: .opacity))
            }

            if showsOpenSettings {
                Button(Copy.openSettings(for: viewModel.targetLanguage)) {
                    if let url = URL(string: UIApplication.openSettingsURLString) {
                        UIApplication.shared.open(url)
                    }
                }
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(Color(hex: 0x1C1915))
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
                .background(Tokens.listen, in: Capsule())
                .padding(.bottom, 120)
            } else if showsModelRetry, !viewModel.isSettingsPresented, !viewModel.isSummaryPresented, picking == nil {
                Button(Copy.redownloadModels(for: viewModel.targetLanguage)) {
                    withAnimation(.easeOut(duration: 0.22)) {
                        viewModel.isSettingsPresented = true
                    }
                    Task { await redownloadModels() }
                }
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(Color(hex: 0x1C1915))
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
                .background(Tokens.listen, in: Capsule())
                .padding(.bottom, 120)
            } else if showsSummarizeButton {
                Button(Copy.summarize(for: viewModel.targetLanguage)) {
                    Task { await viewModel.requestSummary() }
                }
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(Color(hex: 0x1C1915))
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
                .background(Tokens.listen, in: Capsule())
                .padding(.bottom, 120)
            }
        }
        .background(Tokens.userPane)
        .ignoresSafeArea()
        .toolbar(.hidden, for: .navigationBar)
        .confirmationDialog(
            Copy.replaceTaskConfirm(for: viewModel.targetLanguage),
            isPresented: $confirmNewTask,
            titleVisibility: .visible
        ) {
            Button(Copy.newTask(for: viewModel.targetLanguage)) {
                Task { await viewModel.beginTask() }
            }
            Button(Copy.cancel(for: viewModel.targetLanguage), role: .cancel) {}
        }
        .confirmationDialog(
            Copy.endTaskConfirm(for: viewModel.targetLanguage),
            isPresented: $confirmEndTask,
            titleVisibility: .visible
        ) {
            Button(Copy.endTask(for: viewModel.targetLanguage)) {
                Task { await finishTask() }
            }
            Button(Copy.cancel(for: viewModel.targetLanguage), role: .cancel) {}
        }
        .overlay {
            OneWayTranslationHostView(
                sourceLanguage: viewModel.sourceLanguage,
                targetLanguage: viewModel.targetLanguage,
                job: viewModel.outboundJob,
                onSuccess: viewModel.fulfill,
                onFailure: viewModel.failTranslation
            )
            .id("\(viewModel.sourceLanguage.rawValue)-\(viewModel.targetLanguage.rawValue)")
        }
        .overlay {
            TranslationPrepareHost(
                userLanguage: viewModel.sourceLanguage,
                peerLanguage: viewModel.targetLanguage,
                shouldPrepare: shouldPrepareTranslation,
                oneWay: true,
                onFinished: handleTranslationPrepared
            )
            .id("prepare-\(viewModel.sourceLanguage.rawValue)-\(viewModel.targetLanguage.rawValue)")
        }
        .task {
            await viewModel.bootstrap()
        }
        .onAppear {
            applyIdleTimer()
            if lastPreparedKey.isEmpty {
                lastPreparedKey = pairKey
            }
        }
        .onChange(of: pairKey) { _, _ in
            Task { await handlePairChange() }
        }
        .onChange(of: viewModel.keepsScreenAwake) { _, _ in
            applyIdleTimer()
        }
        .onChange(of: viewModel.sessionState) { _, _ in
            applyIdleTimer()
        }
        .onChange(of: viewModel.holdScreenAfterPause) { _, _ in
            applyIdleTimer()
        }
        .onDisappear {
            UIApplication.shared.isIdleTimerDisabled = false
            Task { await viewModel.stop(restoreIdleTimerAfterDelay: false) }
        }
        .preferredColorScheme(.dark)
    }

    private var captionColumn: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(liveText)
                .font(liveFont)
                .foregroundStyle(liveIsSecondary ? Tokens.textSecondary : Tokens.textPrimary)
                .lineSpacing(viewModel.fontSize.livePoints * 0.18)
                .frame(maxWidth: .infinity, alignment: .leading)
                .transaction { transaction in
                    transaction.animation = nil
                }
                .accessibilityAddTraits(.isStaticText)

            if !viewModel.pane.history.isEmpty {
                historyBlock
            } else {
                Spacer(minLength: 0)
            }

            if viewModel.showsSourceLine {
                Text(sourceLineText)
                    .font(CaptionTypography.sourceLineFont())
                    .foregroundStyle(Tokens.textSecondary)
                    .frame(maxWidth: .infinity, minHeight: 18, alignment: .leading)
            }
        }
        .padding(.horizontal, Tokens.horizontalPadding)
        .padding(.top, 8)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private var historyBlock: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 10) {
                    ForEach(Array(viewModel.pane.history.reversed())) { line in
                        Text(line.displayText)
                            .font(CaptionTypography.previousFont(size: viewModel.fontSize))
                            .foregroundStyle(Tokens.textSecondary)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .id(line.id)
                    }
                }
            }
            .scrollIndicators(.hidden)
            .onAppear {
                scrollToNewest(proxy)
            }
            .onChange(of: viewModel.pane.history.last?.id) { _, _ in
                scrollToNewest(proxy)
            }
        }
    }

    private func languagePicker(for side: DirectionPick) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(side == .source ? Copy.theySpeak(for: viewModel.targetLanguage) : Copy.iListen(for: viewModel.targetLanguage))
                .font(.footnote)
                .foregroundStyle(Tokens.textSecondary)
            LanguageChipGrid(
                selected: side == .source ? viewModel.sourceLanguage : viewModel.targetLanguage
            ) { language in
                if side == .source {
                    applySourceLanguage(language)
                } else {
                    applyTargetLanguage(language)
                }
            }
            Button(Copy.done(for: viewModel.targetLanguage)) {
                picking = nil
            }
            .font(.subheadline.weight(.semibold))
            .foregroundStyle(Color(hex: 0x1C1915))
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .background(Tokens.listen, in: Capsule())
            Spacer(minLength: 0)
        }
        .padding(.horizontal, Tokens.horizontalPadding)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private var liveFont: Font {
        CaptionTypography.liveFont(size: viewModel.fontSize, settled: liveIsSettled)
    }

    private var liveIsSettled: Bool {
        if viewModel.errorText != nil { return true }
        if viewModel.pane.live?.translatedText.isEmpty ?? true, viewModel.pane.speakingHint != nil {
            return false
        }
        return viewModel.pane.live?.phase == .settled && !(viewModel.pane.live?.translatedText.isEmpty ?? true)
    }

    private var liveText: String {
        if let errorText = viewModel.errorText {
            return errorText
        }
        if let live = viewModel.pane.live, !live.translatedText.isEmpty {
            return live.translatedText
        }
        if let live = viewModel.pane.live, !live.sourceText.isEmpty {
            return live.sourceText
        }
        if let hint = viewModel.pane.speakingHint {
            return hint
        }
        return idlePrompt
    }

    private var liveIsSecondary: Bool {
        if viewModel.errorText != nil { return false }
        if let live = viewModel.pane.live, !live.translatedText.isEmpty {
            return live.phase == .streaming
        }
        if viewModel.pane.speakingHint != nil { return true }
        if let live = viewModel.pane.live {
            return live.phase == .streaming || live.translatedText.isEmpty
        }
        return true
    }

    private var idlePrompt: String {
        if !viewModel.hasActiveTask {
            return Copy.needNewTask(for: viewModel.targetLanguage)
        }
        switch viewModel.sessionState {
        case .ready, .idle, .paused:
            return Copy.interpretationIdle(for: viewModel.targetLanguage)
        case .preparing:
            return Copy.preparing(for: viewModel.targetLanguage)
        default:
            return Copy.listening(for: viewModel.targetLanguage)
        }
    }

    private var sourceLineText: String {
        guard let live = viewModel.pane.live, !live.sourceText.isEmpty else { return " " }
        return "\(Copy.sourceLinePrefix(for: viewModel.targetLanguage))  \(live.sourceText)"
    }

    private var translationProgress: Double {
        if shouldPrepareTranslation { return max(speechProgress, 0.55) }
        return isRedownloading ? 0 : 1
    }

    private var pairKey: String {
        "\(viewModel.sourceLanguage.rawValue)|\(viewModel.targetLanguage.rawValue)"
    }

    private var showsOpenSettings: Bool {
        if case .failed(let error) = viewModel.sessionState {
            return error == .microphoneDenied || error == .speechDenied
        }
        return false
    }

    private var showsModelRetry: Bool {
        if case .failed(let error) = viewModel.sessionState {
            return error == .modelsMissing || error == .languageUnsupported
        }
        return false
    }

    private var showsSummarizeButton: Bool {
        viewModel.sessionState == .paused
            && viewModel.canSummarize
            && !viewModel.isSettingsPresented
            && !viewModel.isSummaryPresented
            && picking == nil
    }

    private func applyIdleTimer() {
        UIApplication.shared.isIdleTimerDisabled = viewModel.keepsScreenAwake
    }

    private func openPicker(_ side: DirectionPick) {
        viewModel.isSettingsPresented = false
        viewModel.isSummaryPresented = false
        withAnimation(.easeOut(duration: 0.18)) {
            picking = picking == side ? nil : side
        }
    }

    private func applySourceLanguage(_ language: AppLanguage) {
        picking = nil
        withAnimation(.easeInOut(duration: 0.25)) {
            viewModel.setSourceLanguage(language)
        }
    }

    private func applyTargetLanguage(_ language: AppLanguage) {
        picking = nil
        withAnimation(.easeInOut(duration: 0.25)) {
            viewModel.setTargetLanguage(language)
        }
    }

    private func selectMode(_ mode: AppMode) {
        guard mode != .simultaneous else { return }
        Task {
            await viewModel.stop(restoreIdleTimerAfterDelay: false)
            environment.preferences.appMode = mode
            coordinator.replaceModule(mode.featureID)
        }
    }

    private func requestNewTask() {
        if viewModel.hasActiveTask {
            confirmNewTask = true
        } else {
            Task { await viewModel.beginTask() }
        }
    }

    private func finishTask() async {
        if let session = await viewModel.endTask() {
            coordinator.showEndedTask(session.id)
        }
    }

    private func handlePairChange() async {
        let needsAssets = pairKey != lastPreparedKey
        await viewModel.stop(restoreIdleTimerAfterDelay: false)
        if needsAssets {
            shouldPrepareTranslation = false
            viewModel.enterPreparing()
            let prepared = await prepareSpeechForCurrentPair(reportFailure: true)
            if !prepared {
                return
            }
            lastPreparedKey = pairKey
            shouldPrepareTranslation = true
        } else {
            lastPreparedKey = pairKey
            if viewModel.sessionState == .preparing {
                viewModel.restoreReady()
            }
        }
    }

    private func redownloadModels() async {
        redownloadError = nil
        isRedownloading = true
        speechProgress = 0
        shouldPrepareTranslation = false
        await viewModel.stop(restoreIdleTimerAfterDelay: false)
        viewModel.enterPreparing()
        let prepared = await prepareSpeechForCurrentPair(reportFailure: false)
        if prepared {
            lastPreparedKey = pairKey
            shouldPrepareTranslation = true
        } else {
            isRedownloading = false
        }
    }

    private func prepareSpeechForCurrentPair(reportFailure: Bool) async -> Bool {
        redownloadError = nil
        speechProgress = 0
        do {
            let languages = [viewModel.sourceLanguage]
            guard await environment.speechModels.isDeviceCapable(for: languages) else {
                throw DuiyiError.deviceIncapable
            }
            try await environment.speechModels.prepare(languages: languages) { value in
                Task { @MainActor in
                    speechProgress = value
                }
            }
            let pair = await environment.translationAvailability.pairStatus(
                from: viewModel.sourceLanguage,
                to: viewModel.targetLanguage
            )
            if pair == .unsupported {
                throw DuiyiError.languageUnsupported
            }
            return true
        } catch let error as DuiyiError {
            redownloadError = error.userMessage(for: viewModel.targetLanguage)
            if reportFailure {
                viewModel.fail(error)
            }
            return false
        } catch {
            redownloadError = DuiyiError.modelsMissing.userMessage(for: viewModel.targetLanguage)
            if reportFailure {
                viewModel.fail(.modelsMissing)
            }
            return false
        }
    }

    private func handleTranslationPrepared(_ result: Result<Void, Error>) {
        switch result {
        case .success:
            isRedownloading = false
            shouldPrepareTranslation = false
            speechProgress = 1
            if viewModel.sessionState == .preparing {
                viewModel.restoreReady()
            }
        case .failure:
            redownloadError = DuiyiError.modelsMissing.userMessage(for: viewModel.targetLanguage)
            isRedownloading = false
            shouldPrepareTranslation = false
            if viewModel.sessionState == .preparing {
                viewModel.fail(.modelsMissing)
            }
        }
    }

    private func copySummary() {
        guard let text = viewModel.summary?.text, !text.isEmpty else { return }
        UIPasteboard.general.string = text
    }

    private func scrollToNewest(_ proxy: ScrollViewProxy) {
        guard let newest = viewModel.pane.history.last?.id else { return }
        var transaction = Transaction()
        transaction.animation = ReduceMotion.allowed ? .easeOut(duration: 0.18) : nil
        withTransaction(transaction) {
            proxy.scrollTo(newest, anchor: .top)
        }
    }
}

#Preview("Idle") {
    InterpretationPreview.idle
}

#Preview("Listening") {
    InterpretationPreview.listening
}

#Preview("Voice out blocked") {
    InterpretationPreview.voiceOutBlocked
}

#Preview("Failed") {
    InterpretationPreview.failed
}
