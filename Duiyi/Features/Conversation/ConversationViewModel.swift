import Foundation

@MainActor
@Observable
final class ConversationViewModel {
    private let speech: any SpeechRecognizing
    private let permissions: any PermissionGranting
    private let preferences: PreferencesStore
    private let summarizer: any ConversationSummarizing
    private let audioSession: any AudioSessionConfiguring
    private let task: TaskSessionController

    var sessionState: SessionState = .idle
    var userLanguage: AppLanguage
    var peerLanguage: AppLanguage
    var fontSize: CaptionFontSize
    var userPane = PaneState.empty
    var peerPane = PaneState.empty
    var isSettingsPresented = false
    var isSummaryPresented = false
    var outboundJob: TranslationJob?
    var autoStartListening: Bool
    var holdScreenAfterPause = false
    var transcript: [TranscriptEntry] = []
    var summary: ConversationSummary?
    var summaryError: String?
    var summaryAvailability: SummaryAvailability = .unavailable
    var isSummarizing = false

    private var speechTask: Task<Void, Never>?
    private var translationDebounce: Task<Void, Never>?
    private var idleRestoreTask: Task<Void, Never>?
    private var isStopping = false
    private var routedSideByUtterance: [UUID: SpeakerSide] = [:]
    private var lastCommittedLanguage: AppLanguage?
    private var lastCommittedAt = Date.distantPast
    private var lastAppliedSourceCount: [UUID: Int] = [:]
    private var sentSourceText: [UUID: String] = [:]
    private var utteranceAliases: [UUID: UUID] = [:]
    private var persistTask: Task<Void, Never>?
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
        self.task = TaskSessionController(feature: .faceToFace, store: taskStore)
        self.idleRestoreDelay = idleRestoreDelay
        userLanguage = preferences.userLanguage
        peerLanguage = preferences.peerLanguage
        fontSize = preferences.fontSize
        autoStartListening = preferences.autoStartListening
    }

    var hasActiveTask: Bool { task.hasActiveTask }
    var taskStartedAt: Date? { task.startedAt }

    var canSummarize: Bool {
        transcript.contains { !$0.sourceText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
    }

    var exportableSession: TaskSession {
        TaskSession(
            id: task.taskID ?? UUID(),
            feature: .faceToFace,
            status: hasActiveTask ? .running : .ended,
            startedAt: task.startedAt ?? .now,
            endedAt: nil,
            title: TaskTitle.make(
                feature: .faceToFace,
                source: userLanguage,
                target: peerLanguage,
                startedAt: task.startedAt ?? .now,
                language: userLanguage
            ),
            subtitle: nil,
            sourceLanguage: userLanguage,
            targetLanguage: peerLanguage,
            entries: transcript,
            summary: summary
        )
    }

    var controlLabel: String {
        if !hasActiveTask {
            return Copy.needNewTask(for: userLanguage)
        }
        switch sessionState {
        case .listening:
            return Copy.listening(for: userLanguage)
        case .ready:
            return Copy.tapToStart(for: userLanguage)
        case .paused:
            return Copy.paused(for: userLanguage)
        case .preparing:
            return Copy.preparing(for: userLanguage)
        case .failed, .idle:
            return Copy.tapToStart(for: userLanguage)
        }
    }

    var userErrorText: String? {
        if case let .failed(error) = sessionState {
            return error.userMessage(for: userLanguage)
        }
        return nil
    }

    var keepsScreenAwake: Bool {
        sessionState == .listening || holdScreenAfterPause
    }

    var skipsBootstrap = false

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
        _ = await task.beginNew(source: userLanguage, target: peerLanguage)
        if autoStartListening {
            await start()
        } else {
            sessionState = .ready
        }
    }

    func endTask() async -> TaskSession? {
        await stop(restoreIdleTimerAfterDelay: false)
        let saved = await task.finish(entries: transcript, summary: summary)
        resetCaptions()
        sessionState = .ready
        return saved
    }

    func toggleListening() async {
        guard hasActiveTask else { return }
        if sessionState == .listening {
            await stop()
        } else {
            await start()
        }
    }

    func start() async {
        guard hasActiveTask, sessionState != .listening else { return }
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
            try await audioSession.activate(.faceToFace)
            let stream = try await speech.start(
                languages: [userLanguage, peerLanguage],
                fallbackLanguage: peerLanguage
            )
            sessionState = .listening
            holdScreenAfterPause = false
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
        mutatePane(.user) { $0.speakingHint = nil }
        mutatePane(.peer) { $0.speakingHint = nil }
    }

    func resetCaptions() {
        userPane.resetCaptions()
        peerPane.resetCaptions()
        transcript = []
        outboundJob = nil
        translationDebounce?.cancel()
        routedSideByUtterance.removeAll()
        lastCommittedLanguage = nil
        lastCommittedAt = .distantPast
        lastAppliedSourceCount.removeAll()
        sentSourceText.removeAll()
        utteranceAliases.removeAll()
        summary = nil
        summaryError = nil
    }

    func setUserLanguage(_ language: AppLanguage) {
        guard language != userLanguage else { return }
        if language == peerLanguage {
            peerLanguage = userLanguage
            preferences.peerLanguage = peerLanguage
        }
        userLanguage = language
        preferences.userLanguage = language
        resetCaptions()
    }

    func setPeerLanguage(_ language: AppLanguage) {
        guard language != peerLanguage else { return }
        if language == userLanguage {
            userLanguage = peerLanguage
            preferences.userLanguage = userLanguage
        }
        peerLanguage = language
        preferences.peerLanguage = language
        resetCaptions()
    }

    func swapLanguages() {
        guard userLanguage != peerLanguage else { return }
        let previousUser = userLanguage
        userLanguage = peerLanguage
        peerLanguage = previousUser
        preferences.userLanguage = userLanguage
        preferences.peerLanguage = peerLanguage
        resetCaptions()
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

    func markPaused() {
        sessionState = .paused
    }

    func fail(_ error: DuiyiError) {
        sessionState = .failed(error)
        holdScreenAfterPause = false
        idleRestoreTask?.cancel()
    }

    func setFontSize(_ size: CaptionFontSize) {
        fontSize = size
        preferences.fontSize = size
    }

    func setAutoStartListening(_ enabled: Bool) {
        autoStartListening = enabled
        preferences.autoStartListening = enabled
    }

    func accept(_ utterance: Utterance) {
        if shouldIgnoreCrosstalk(utterance) {
            return
        }

        let listener: SpeakerSide
        if let pinned = routedSideByUtterance[utterance.id] {
            let detectedSide = LanguageRouter.targetSide(detected: utterance.language, userLanguage: userLanguage)
            if detectedSide != pinned {
                return
            }
            listener = pinned
        } else {
            listener = LanguageRouter.targetSide(detected: utterance.language, userLanguage: userLanguage)
            routedSideByUtterance[utterance.id] = listener
        }

        let speaker = listener.opposite
        let speaking = Copy.speaking(for: speaker == .user ? userLanguage : peerLanguage)

        if utterance.isFinal {
            mutatePane(speaker) { $0.speakingHint = nil }
            lastCommittedLanguage = utterance.language
            lastCommittedAt = .now
        } else {
            mutatePane(speaker) { $0.speakingHint = speaking }
            mutatePane(listener) { $0.speakingHint = nil }
        }

        let existing = pane(listener).live
        let captionID: UUID
        let carriedTranslation: String
        if let existing, existing.source == utterance.language,
           SpokenText.isDistinctGreeting(
            incomingSource: utterance.text,
            incomingDisplay: utterance.text,
            previousSource: existing.sourceText,
            previousDisplay: existing.displayText
           ) {
            captionID = UUID()
            carriedTranslation = ""
            utteranceAliases[utterance.id] = captionID
        } else if let existing, existing.source == utterance.language,
           SpokenText.isContinuation(utterance.text, of: existing.sourceText, language: utterance.language) {
            captionID = existing.id
            carriedTranslation = existing.translatedText
            utteranceAliases[utterance.id] = existing.id
        } else {
            captionID = utterance.id
            carriedTranslation = existing?.id == utterance.id ? existing?.translatedText ?? "" : ""
        }

        let line = CaptionLine(
            id: captionID,
            side: listener,
            source: utterance.language,
            sourceText: utterance.text,
            translatedText: carriedTranslation,
            phase: utterance.isFinal ? .settled : .streaming
        )
        var applied = line
        mutatePane(listener) { applied = $0.applyLive(line) }
        upsertTranscript(line: applied, speaker: speaker)
        enqueueTranslation(applied, isFinal: utterance.isFinal)
    }

    func fulfill(job: TranslationJob, text: String) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        if !job.isFinal, let applied = lastAppliedSourceCount[canonicalID(job.utteranceID)], applied > job.text.count {
            return
        }
        let utteranceID = canonicalID(job.utteranceID)
        lastAppliedSourceCount[utteranceID] = max(lastAppliedSourceCount[utteranceID] ?? 0, job.text.count)
        applyTranslation(utteranceID: utteranceID, text: trimmed, settle: job.isFinal)
        if outboundJob?.id == job.id {
            outboundJob = nil
        }
    }

    func failTranslation(job: TranslationJob, error: Error) {
        if Self.isTransientTranslationCancellation(error) {
            if outboundJob?.id == job.id {
                outboundJob = nil
            }
            return
        }
        if outboundJob?.id == job.id {
            outboundJob = nil
        }
    }

    func requestSummary() async {
        summaryAvailability = await summarizer.availability()
        guard canSummarize else {
            summaryError = DuiyiError.summaryEmpty.userMessage(for: userLanguage)
            isSummaryPresented = true
            return
        }
        isSettingsPresented = false
        isSummaryPresented = true
        isSummarizing = true
        summaryError = nil
        if summaryAvailability == .available {
            do {
                summary = try await summarizer.summarize(entries: transcript, outputLanguage: userLanguage)
                if let summary {
                    await task.saveSummary(summary)
                }
            } catch let error as DuiyiError {
                summary = nil
                summaryError = error.userMessage(for: userLanguage)
            } catch {
                summary = nil
                summaryError = DuiyiError.summaryEmpty.userMessage(for: userLanguage)
            }
        } else {
            summary = nil
        }
        isSummarizing = false
    }

    private func enqueueTranslation(_ line: CaptionLine, isFinal: Bool) {
        let text = line.sourceText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        if sentSourceText[line.id] == text, !isFinal {
            return
        }

        let job = TranslationJob(
            utteranceID: line.id,
            source: line.source,
            target: LanguageRouter.targetLanguage(
                detected: line.source,
                userLanguage: userLanguage,
                peerLanguage: peerLanguage
            ),
            text: text,
            isFinal: isFinal
        )
        let isFirst = sentSourceText[line.id] == nil
        let shouldFlush = isFinal
            || Self.endsWithClause(text)
            || (isFirst && Self.isWorthTranslating(text, language: line.source))

        translationDebounce?.cancel()
        if shouldFlush {
            sentSourceText[line.id] = text
            outboundJob = job
            return
        }
        let delay = isFirst
            ? ConversationLayout.firstTranslationDebounceMilliseconds
            : ConversationLayout.translationDebounceMilliseconds
        translationDebounce = Task { [weak self] in
            try? await Task.sleep(for: .milliseconds(delay))
            guard !Task.isCancelled else { return }
            self?.sentSourceText[line.id] = text
            self?.outboundJob = job
        }
    }

    private func applyTranslation(utteranceID: UUID, text: String, settle: Bool) {
        mutatePane(.user) { $0.applyTranslation(utteranceID: utteranceID, text: text, settle: settle) }
        mutatePane(.peer) { $0.applyTranslation(utteranceID: utteranceID, text: text, settle: settle) }
        if let index = transcript.firstIndex(where: { $0.id == utteranceID }) {
            transcript[index].translatedText = text
            if settle {
                transcript[index].isFinal = true
                schedulePersist()
            }
        }
    }

    private func upsertTranscript(line: CaptionLine, speaker: SpeakerSide) {
        if let index = transcript.firstIndex(where: { $0.id == line.id }) {
            transcript[index].sourceText = SpokenText.preferredSource(transcript[index].sourceText, line.sourceText)
            if !line.translatedText.isEmpty {
                transcript[index].translatedText = line.translatedText
            }
            transcript[index].isFinal = line.phase == .settled
            dropPrefixTranscript(after: index, speaker: speaker, language: line.source)
            if line.phase == .settled {
                schedulePersist()
            }
            return
        }
        if let last = transcript.last,
           last.speaker == speaker,
           SpokenText.isContinuation(line.sourceText, of: last.sourceText, language: line.source) {
            var updated = last
            updated.sourceText = SpokenText.preferredSource(last.sourceText, line.sourceText)
            if !line.translatedText.isEmpty {
                updated.translatedText = line.translatedText
            }
            updated.isFinal = line.phase == .settled
            transcript[transcript.count - 1] = updated
            dropPrefixTranscript(after: transcript.count - 1, speaker: speaker, language: line.source)
            if line.phase == .settled {
                schedulePersist()
            }
            return
        }
        transcript.append(
            TranscriptEntry(
                id: line.id,
                speaker: speaker,
                source: line.source,
                sourceText: line.sourceText,
                translatedText: line.translatedText,
                isFinal: line.phase == .settled
            )
        )
        if line.phase == .settled {
            schedulePersist()
        }
    }

    private func dropPrefixTranscript(after index: Int, speaker: SpeakerSide, language: AppLanguage) {
        let current = transcript[index]
        var cursor = index
        while cursor > 0 {
            let prior = transcript[cursor - 1]
            guard prior.speaker == speaker,
                  SpokenText.isContinuation(current.sourceText, of: prior.sourceText, language: language) else {
                break
            }
            transcript.remove(at: cursor - 1)
            cursor -= 1
        }
    }

    private func canonicalID(_ id: UUID) -> UUID {
        utteranceAliases[id] ?? id
    }

    private func shouldIgnoreCrosstalk(_ utterance: Utterance) -> Bool {
        guard let lastCommittedLanguage else { return false }
        guard Date().timeIntervalSince(lastCommittedAt) < 1.0 else { return false }
        guard utterance.language != lastCommittedLanguage else { return false }
        return !UtteranceAssembler.isConfident(utterance.text, language: utterance.language)
    }

    private func pane(_ side: SpeakerSide) -> PaneState {
        switch side {
        case .user: return userPane
        case .peer: return peerPane
        }
    }

    private func mutatePane(_ side: SpeakerSide, _ body: (inout PaneState) -> Void) {
        switch side {
        case .user:
            body(&userPane)
        case .peer:
            body(&peerPane)
        }
    }

    private func handleStreamEnded() async {
        guard !isStopping, sessionState == .listening else { return }
        sessionState = .failed(.recognitionInterrupted)
        holdScreenAfterPause = false
        idleRestoreTask?.cancel()
        mutatePane(.user) { $0.speakingHint = nil }
        mutatePane(.peer) { $0.speakingHint = nil }
    }

    private func restore(from session: TaskSession) {
        transcript = session.entries
        summary = session.summary
        userPane = .empty
        peerPane = .empty
        for entry in session.entries {
            let listener = entry.speaker.opposite
            mutatePane(listener) {
                $0.history.append(
                    CaptionLine(
                        id: entry.id,
                        side: listener,
                        source: entry.source,
                        sourceText: entry.sourceText,
                        translatedText: entry.translatedText,
                        phase: .settled
                    )
                )
            }
        }
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

    private func scheduleIdleRestore() {
        idleRestoreTask?.cancel()
        idleRestoreTask = Task { [weak self] in
            let delay = self?.idleRestoreDelay ?? .seconds(ConversationLayout.idleRestoreSeconds)
            try? await Task.sleep(for: delay)
            guard !Task.isCancelled else { return }
            self?.holdScreenAfterPause = false
        }
    }

    static func isTransientTranslationCancellation(_ error: Error) -> Bool {
        if error is CancellationError {
            return true
        }
        let nsError = error as NSError
        if nsError.domain == "TranslationErrorDomain", [14, 20].contains(nsError.code) {
            return true
        }
        return false
    }

    static func endsWithClause(_ text: String) -> Bool {
        guard let last = text.last else { return false }
        return last.unicodeScalars.allSatisfy { ClauseSplitter.terminators.contains($0) }
    }

    static func isWorthTranslating(_ text: String, language: AppLanguage) -> Bool {
        switch language {
        case .zhHans:
            return UtteranceAssembler.hanCount(text) >= 2
        case .english:
            return UtteranceAssembler.wordCount(text) >= 2 || text.count >= 8
        case .japanese:
            return UtteranceAssembler.kanaCount(text) + UtteranceAssembler.hanCount(text) >= 2
        case .korean:
            return UtteranceAssembler.hangulCount(text) >= 2
        case .thai:
            return UtteranceAssembler.thaiCount(text) >= 2
        case .vietnamese:
            return UtteranceAssembler.wordCount(text) >= 2
                || UtteranceAssembler.vietnameseMarkCount(text) >= 1
                || text.count >= 8
        }
    }
}
