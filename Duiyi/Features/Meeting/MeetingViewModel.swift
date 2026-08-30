import Foundation

@MainActor
@Observable
final class MeetingViewModel {
    private let speech: any SpeechRecognizing
    private let permissions: any PermissionGranting
    private let preferences: PreferencesStore
    private let summarizer: any ConversationSummarizing
    private let audioSession: any AudioSessionConfiguring
    private let task: TaskSessionController

    var sessionState: SessionState = .idle
    var sourceLanguage: AppLanguage
    var fontSize: CaptionFontSize
    var pane = PaneState.empty
    var isSettingsPresented = false
    var isSummaryPresented = false
    var holdScreenAfterPause = false
    var transcript: [TranscriptEntry] = []
    var summary: ConversationSummary?
    var summaryError: String?
    var summaryAvailability: SummaryAvailability = .unavailable
    var isSummarizing = false
    var isLengthLimited = false
    var skipsBootstrap = false

    private var speechTask: Task<Void, Never>?
    private var idleRestoreTask: Task<Void, Never>?
    private var persistTask: Task<Void, Never>?
    private var isStopping = false
    private var utteranceAliases: [UUID: UUID] = [:]
    private let idleRestoreDelay: Duration

    init(
        speech: any SpeechRecognizing,
        permissions: any PermissionGranting,
        preferences: PreferencesStore,
        summarizer: any ConversationSummarizing,
        audioSession: any AudioSessionConfiguring = NoOpAudioSession(),
        taskStore: any TaskStore = InMemoryTaskStore(),
        idleRestoreDelay: Duration = .seconds(ConversationLayout.idleRestoreSeconds)
    ) {
        self.speech = speech
        self.permissions = permissions
        self.preferences = preferences
        self.summarizer = summarizer
        self.audioSession = audioSession
        self.task = TaskSessionController(feature: .meeting, store: taskStore)
        self.idleRestoreDelay = idleRestoreDelay
        sourceLanguage = preferences.meetingLanguage
        fontSize = preferences.fontSize
    }

    var hasActiveTask: Bool { task.hasActiveTask }
    var taskStartedAt: Date? { task.startedAt }

    var canSummarize: Bool {
        transcript.contains { !$0.sourceText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
    }

    var keepsScreenAwake: Bool {
        sessionState == .listening || holdScreenAfterPause
    }

    var controlLabel: String {
        if !hasActiveTask {
            return Copy.needNewTask(for: sourceLanguage)
        }
        switch sessionState {
        case .listening:
            return Copy.recording(for: sourceLanguage)
        case .paused:
            return Copy.paused(for: sourceLanguage)
        case .preparing:
            return Copy.preparing(for: sourceLanguage)
        case .ready, .idle, .failed:
            return Copy.tapToStart(for: sourceLanguage)
        }
    }

    var errorText: String? {
        if isLengthLimited {
            return Copy.meetingTooLong(for: sourceLanguage)
        }
        if case let .failed(error) = sessionState {
            return error.userMessage(for: sourceLanguage)
        }
        return nil
    }

    var exportableSession: TaskSession {
        TaskSession(
            id: task.taskID ?? UUID(),
            feature: .meeting,
            status: hasActiveTask ? .running : .ended,
            startedAt: task.startedAt ?? .now,
            endedAt: nil,
            title: TaskTitle.make(
                feature: .meeting,
                source: sourceLanguage,
                target: nil,
                startedAt: task.startedAt ?? .now,
                language: sourceLanguage
            ),
            subtitle: TaskTitle.subtitle(from: transcript),
            sourceLanguage: sourceLanguage,
            targetLanguage: nil,
            entries: transcript,
            summary: summary
        )
    }

    func bootstrap() async {
        guard !skipsBootstrap else { return }
        sessionState = .preparing
        if let existing = await task.restore() {
            restore(from: existing)
        }
        let status = await permissions.currentStatus()
        if let error = status.asDuiyiError() {
            sessionState = .failed(error)
            return
        }
        sessionState = .ready
    }

    func beginTask() async {
        if hasActiveTask {
            _ = await task.finish(entries: transcript, summary: summary)
        }
        resetCaptions()
        isLengthLimited = false
        _ = await task.beginNew(source: sourceLanguage, target: nil)
        sessionState = .ready
    }

    func endTask() async -> TaskSession? {
        await stop(restoreIdleTimerAfterDelay: false)
        let saved = await task.finish(entries: transcript, summary: summary)
        resetCaptions()
        isLengthLimited = false
        sessionState = .ready
        return saved
    }

    func toggleListening() async {
        guard hasActiveTask, !isLengthLimited else { return }
        if sessionState == .listening {
            await stop()
        } else {
            await start()
        }
    }

    func start() async {
        guard hasActiveTask, !isLengthLimited, sessionState != .listening else { return }
        isStopping = false
        idleRestoreTask?.cancel()
        holdScreenAfterPause = false

        var status = await permissions.currentStatus()
        if status != .granted {
            status = await permissions.requestAccess()
        }
        if let error = status.asDuiyiError() {
            sessionState = .failed(error)
            return
        }

        do {
            try await audioSession.activate(.interpretationCaptions)
            let stream = try await speech.start(
                languages: [sourceLanguage],
                fallbackLanguage: sourceLanguage
            )
            sessionState = .listening
            await task.setListening(true)
            speechTask?.cancel()
            speechTask = Task { [weak self] in
                for await utterance in stream {
                    self?.accept(utterance)
                }
                await self?.handleStreamEnded()
            }
        } catch let error as DuiyiError {
            sessionState = .failed(error)
        } catch {
            sessionState = .failed(.recognitionInterrupted)
        }
    }

    func stop(restoreIdleTimerAfterDelay: Bool = true) async {
        isStopping = true
        speechTask?.cancel()
        speechTask = nil
        await speech.stop()
        let wasListening = sessionState == .listening
        if wasListening {
            sessionState = .paused
            await task.setListening(false)
            await persistNow()
            if restoreIdleTimerAfterDelay {
                holdScreenAfterPause = true
                scheduleIdleRestore()
            } else {
                holdScreenAfterPause = false
                idleRestoreTask?.cancel()
            }
        }
        pane.speakingHint = nil
    }

    func resetCaptions() {
        pane.resetCaptions()
        transcript = []
        utteranceAliases.removeAll()
        summary = nil
        summaryError = nil
        isLengthLimited = false
    }

    func setSourceLanguage(_ language: AppLanguage) {
        guard language != sourceLanguage else { return }
        sourceLanguage = language
        preferences.meetingLanguage = language
        pane.archiveLive()
        pane.speakingHint = nil
        if sessionState == .listening || sessionState == .paused {
            sessionState = .ready
        }
    }

    func setFontSize(_ size: CaptionFontSize) {
        fontSize = size
        preferences.fontSize = size
    }

    func enterPreparing() {
        idleRestoreTask?.cancel()
        holdScreenAfterPause = false
        sessionState = .preparing
    }

    func restoreReady() {
        guard sessionState == .preparing else { return }
        sessionState = .ready
    }

    func fail(_ error: DuiyiError) {
        sessionState = .failed(error)
        holdScreenAfterPause = false
        idleRestoreTask?.cancel()
    }

    func accept(_ utterance: Utterance) {
        guard hasActiveTask, !isLengthLimited else { return }
        let text = utterance.text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        if utterance.isFinal {
            pane.speakingHint = nil
        } else {
            pane.speakingHint = Copy.speaking(for: sourceLanguage)
        }

        let existing = pane.live
        let captionID: UUID
        if let existing,
           SpokenText.isDistinctGreeting(
            incomingSource: text,
            incomingDisplay: text,
            previousSource: existing.sourceText,
            previousDisplay: existing.displayText
           ) {
            captionID = UUID()
            utteranceAliases[utterance.id] = captionID
        } else if let existing,
                  SpokenText.isContinuation(text, of: existing.sourceText, language: existing.source)
                    || SpokenText.isRefinement(text, of: existing.sourceText) {
            captionID = existing.id
            utteranceAliases[utterance.id] = existing.id
        } else {
            captionID = utterance.id
        }

        let line = CaptionLine(
            id: captionID,
            side: .user,
            source: sourceLanguage,
            sourceText: text,
            translatedText: "",
            phase: utterance.isFinal ? .settled : .streaming
        )
        let applied = pane.applyLive(line)
        upsertTranscript(line: applied)
        if applied.phase == .settled {
            schedulePersist()
            if transcriptCharacterCount() >= MeetingLayout.transcriptCharacterLimit {
                isLengthLimited = true
                Task { await stop(restoreIdleTimerAfterDelay: false) }
            }
        }
    }

    func requestSummary() async {
        summaryAvailability = await summarizer.availability()
        guard canSummarize else {
            summaryError = DuiyiError.summaryEmpty.userMessage(for: sourceLanguage)
            isSummaryPresented = true
            return
        }
        isSettingsPresented = false
        isSummaryPresented = true
        isSummarizing = true
        summaryError = nil
        if summaryAvailability == .available {
            do {
                summary = try await summarizer.summarize(entries: transcript, outputLanguage: sourceLanguage)
                if let summary {
                    await task.saveSummary(summary)
                }
            } catch let error as DuiyiError {
                summary = nil
                summaryError = error.userMessage(for: sourceLanguage)
            } catch {
                summary = nil
                summaryError = DuiyiError.summaryEmpty.userMessage(for: sourceLanguage)
            }
        } else {
            summary = nil
        }
        isSummarizing = false
    }

    private func restore(from session: TaskSession) {
        transcript = session.entries
        summary = session.summary
        pane = .empty
        for entry in session.entries {
            pane.history.append(
                CaptionLine(
                    id: entry.id,
                    side: .user,
                    source: entry.source,
                    sourceText: entry.sourceText,
                    translatedText: entry.translatedText,
                    phase: .settled
                )
            )
        }
    }

    private func upsertTranscript(line: CaptionLine) {
        if let index = transcript.firstIndex(where: { $0.id == line.id }) {
            transcript[index].sourceText = SpokenText.preferredSource(transcript[index].sourceText, line.sourceText)
            transcript[index].isFinal = line.phase == .settled
            return
        }
        if let last = transcript.last,
           SpokenText.isContinuation(line.sourceText, of: last.sourceText, language: line.source)
            || SpokenText.isRefinement(line.sourceText, of: last.sourceText) {
            var updated = last
            updated.sourceText = SpokenText.preferredSource(last.sourceText, line.sourceText)
            updated.isFinal = line.phase == .settled
            transcript[transcript.count - 1] = updated
            return
        }
        transcript.append(
            TranscriptEntry(
                id: line.id,
                speaker: .user,
                source: line.source,
                sourceText: line.sourceText,
                translatedText: line.translatedText,
                isFinal: line.phase == .settled
            )
        )
    }

    private func transcriptCharacterCount() -> Int {
        transcript.reduce(0) { $0 + $1.sourceText.count }
    }

    private func schedulePersist() {
        persistTask?.cancel()
        persistTask = Task { [weak self] in
            try? await Task.sleep(for: .milliseconds(250))
            guard !Task.isCancelled else { return }
            await self?.persistNow()
        }
    }

    private func persistNow() async {
        await task.persist(transcript)
    }

    private func handleStreamEnded() async {
        guard !isStopping, sessionState == .listening else { return }
        sessionState = .failed(.recognitionInterrupted)
        holdScreenAfterPause = false
        idleRestoreTask?.cancel()
        pane.speakingHint = nil
        await persistNow()
    }

    private func scheduleIdleRestore() {
        idleRestoreTask?.cancel()
        idleRestoreTask = Task { [weak self] in
            let delay = self?.idleRestoreDelay ?? .seconds(ConversationLayout.idleRestoreSeconds)
            try? await Task.sleep(for: delay)
            guard !Task.isCancelled else { return }
            self?.holdScreenAfterPause = false
        }
    }
}
