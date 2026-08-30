import Foundation

@MainActor
@Observable
final class InterpretationViewModel {
    private let speech: any SpeechRecognizing
    private let permissions: any PermissionGranting
    private let preferences: PreferencesStore
    private let summarizer: any ConversationSummarizing
    private let audioSession: any AudioSessionConfiguring
    private let synthesizer: any SpeechSynthesizing

    var sessionState: SessionState = .idle
    var sourceLanguage: AppLanguage
    var targetLanguage: AppLanguage
    var fontSize: CaptionFontSize
    var pane = PaneState.empty
    var isSettingsPresented = false
    var isSummaryPresented = false
    var outboundJob: TranslationJob?
    var holdScreenAfterPause = false
    var transcript: [TranscriptEntry] = []
    var summary: ConversationSummary?
    var summaryError: String?
    var isSummarizing = false
    var voiceOutEnabled: Bool
    var showsSourceLine: Bool
    var canSpeakWithoutEcho = false
    var voiceOutBlockedMessage: String?
    var skipsBootstrap = false

    private var speechTask: Task<Void, Never>?
    private var translationDebounce: Task<Void, Never>?
    private var idleRestoreTask: Task<Void, Never>?
    private var routeTask: Task<Void, Never>?
    private var speakTask: Task<Void, Never>?
    private var isStopping = false
    private var lastAppliedSourceCount: [UUID: Int] = [:]
    private var sentSourceText: [UUID: String] = [:]
    private var utteranceAliases: [UUID: UUID] = [:]
    private var spokenPrefixes: [UUID: String] = [:]
    private var lastSpokenTranslation = ""
    private var spokenCompactTail = ""
    private var pendingJobs: [SynthesisJob] = []
    private var isSpeaking = false
    private var speechGeneration = 0
    private var speechDebounces: [UUID: Task<Void, Never>] = [:]
    private var pendingSettledSpeech: [UUID: String] = [:]
    private let idleRestoreDelay: Duration
    private let speechSettleDelay: Duration

    init(
        speech: any SpeechRecognizing,
        permissions: any PermissionGranting,
        preferences: PreferencesStore,
        summarizer: any ConversationSummarizing,
        audioSession: any AudioSessionConfiguring,
        synthesizer: any SpeechSynthesizing,
        idleRestoreDelay: Duration = .seconds(ConversationLayout.idleRestoreSeconds),
        speechSettleDelay: Duration = .milliseconds(380)
    ) {
        self.speech = speech
        self.permissions = permissions
        self.preferences = preferences
        self.summarizer = summarizer
        self.audioSession = audioSession
        self.synthesizer = synthesizer
        self.idleRestoreDelay = idleRestoreDelay
        self.speechSettleDelay = speechSettleDelay
        sourceLanguage = preferences.sourceLanguage
        targetLanguage = preferences.targetLanguage
        fontSize = preferences.fontSize
        voiceOutEnabled = preferences.voiceOutEnabled
        showsSourceLine = preferences.showsSourceLine
    }

    var canSummarize: Bool {
        transcript.contains { !$0.sourceText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
    }

    var controlLabel: String {
        switch sessionState {
        case .listening:
            return Copy.listening(for: targetLanguage)
        case .ready:
            return Copy.tapToStart(for: targetLanguage)
        case .paused:
            return Copy.paused(for: targetLanguage)
        case .preparing:
            return Copy.preparing(for: targetLanguage)
        case .failed, .idle:
            return Copy.tapToStart(for: targetLanguage)
        }
    }

    var errorText: String? {
        if case let .failed(error) = sessionState {
            return error.userMessage(for: targetLanguage)
        }
        return nil
    }

    var keepsScreenAwake: Bool {
        sessionState == .listening || holdScreenAfterPause
    }

    var voiceOutLabel: String {
        if let voiceOutBlockedMessage {
            return voiceOutBlockedMessage
        }
        if voiceOutEnabled {
            return Copy.voiceOutSpeaking(for: targetLanguage)
        }
        return Copy.voiceOut(for: targetLanguage)
    }

    var isVoiceOutBlocked: Bool {
        voiceOutBlockedMessage != nil
    }

    var pendingSpeechCount: Int {
        pendingJobs.count
    }

    func bootstrap() async {
        startRouteObserver()
        canSpeakWithoutEcho = await audioSession.currentRoute().canSpeakWithoutEcho
        if voiceOutEnabled, !canSpeakWithoutEcho {
            voiceOutEnabled = false
            preferences.voiceOutEnabled = false
        }
        guard !skipsBootstrap else { return }
        sessionState = .preparing
        let status = await permissions.currentStatus()
        if let error = status.asDuiyiError() {
            sessionState = .failed(error)
            return
        }
        sessionState = .ready
    }

    func toggleListening() async {
        if sessionState == .listening {
            await stop()
        } else {
            await start()
        }
    }

    func start() async {
        guard sessionState != .listening else { return }
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
            if voiceOutEnabled {
                let allowed = await prepareVoiceOutRoute()
                if !allowed {
                    await forceVoiceOutOff(reason: .voiceOutNeedsHeadphones)
                }
            }
            try await audioSession.activate(currentUseCase)
            try await beginSpeechStream()
            sessionState = .listening
            holdScreenAfterPause = false
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
        await clearSpeechQueue()
        await speech.stop()
        let wasListening = sessionState == .listening
        if wasListening {
            sessionState = .paused
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
        outboundJob = nil
        translationDebounce?.cancel()
        lastAppliedSourceCount.removeAll()
        sentSourceText.removeAll()
        utteranceAliases.removeAll()
        spokenPrefixes.removeAll()
        lastSpokenTranslation = ""
        spokenCompactTail = ""
        cancelSpeechDebounces()
        summary = nil
        summaryError = nil
        Task { await clearSpeechQueue() }
    }

    func setSourceLanguage(_ language: AppLanguage) {
        guard language != sourceLanguage else { return }
        if language == targetLanguage {
            targetLanguage = sourceLanguage
            preferences.targetLanguage = targetLanguage
        }
        sourceLanguage = language
        preferences.sourceLanguage = language
        applyDirectionChange()
    }

    func setTargetLanguage(_ language: AppLanguage) {
        guard language != targetLanguage else { return }
        if language == sourceLanguage {
            sourceLanguage = targetLanguage
            preferences.sourceLanguage = sourceLanguage
        }
        targetLanguage = language
        preferences.targetLanguage = language
        applyDirectionChange()
    }

    func swapDirection() {
        guard sourceLanguage != targetLanguage else { return }
        let previousSource = sourceLanguage
        sourceLanguage = targetLanguage
        targetLanguage = previousSource
        preferences.sourceLanguage = sourceLanguage
        preferences.targetLanguage = targetLanguage
        applyDirectionChange()
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
        Task { await clearSpeechQueue() }
    }

    func setFontSize(_ size: CaptionFontSize) {
        fontSize = size
        preferences.fontSize = size
    }

    func setShowsSourceLine(_ enabled: Bool) {
        showsSourceLine = enabled
        preferences.showsSourceLine = enabled
    }

    func setVoiceOutEnabled(_ enabled: Bool) async {
        let wasListening = sessionState == .listening
        if wasListening {
            await pauseCaptureForReroute()
        }

        if !enabled {
            voiceOutEnabled = false
            preferences.voiceOutEnabled = false
            voiceOutBlockedMessage = nil
            canSpeakWithoutEcho = false
            await clearSpeechQueue()
        } else {
            let hasVoice = await synthesizer.hasVoice(for: targetLanguage)
            if !hasVoice {
                await denyVoiceOut(.synthesisVoiceMissing)
            } else if await prepareVoiceOutRoute() {
                voiceOutEnabled = true
                preferences.voiceOutEnabled = true
                voiceOutBlockedMessage = nil
            } else {
                await denyVoiceOut(.voiceOutNeedsHeadphones)
            }
        }

        try? await audioSession.activate(currentUseCase)
        if wasListening {
            do {
                try await beginSpeechStream()
            } catch {
                sessionState = .failed(.recognitionInterrupted)
            }
        }
    }

    func accept(_ utterance: Utterance) {
        guard utterance.language == sourceLanguage else { return }
        let text = utterance.text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        if utterance.isFinal {
            pane.speakingHint = nil
        } else {
            pane.speakingHint = Copy.speaking(for: sourceLanguage)
        }

        let existing = pane.live
        let captionID: UUID
        let carriedTranslation: String
        if let existing, existing.source == utterance.language,
           SpokenText.isContinuation(text, of: existing.sourceText, language: utterance.language)
            || SpokenText.isRefinement(text, of: existing.sourceText) {
            captionID = existing.id
            carriedTranslation = existing.translatedText
            utteranceAliases[utterance.id] = existing.id
        } else {
            captionID = utterance.id
            carriedTranslation = existing?.id == utterance.id ? existing?.translatedText ?? "" : ""
        }

        let line = CaptionLine(
            id: captionID,
            side: .user,
            source: utterance.language,
            sourceText: text,
            translatedText: carriedTranslation,
            phase: utterance.isFinal ? .settled : .streaming
        )
        pane.applyLive(line)
        pane.trimHistory(to: InterpretationLayout.historyLimit)
        upsertTranscript(line: line)
        enqueueTranslation(line, isFinal: utterance.isFinal)
    }

    func fulfill(job: TranslationJob, text: String) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        let utteranceID = canonicalID(job.utteranceID)
        if let applied = lastAppliedSourceCount[utteranceID], applied > job.text.count {
            return
        }
        lastAppliedSourceCount[utteranceID] = max(lastAppliedSourceCount[utteranceID] ?? 0, job.text.count)
        let appliedCaption = applyTranslation(utteranceID: utteranceID, text: trimmed, settle: job.isFinal)
        if appliedCaption {
            scheduleSpeech(
                utteranceID: utteranceID,
                translated: displayedTranslation(for: utteranceID) ?? trimmed,
                settle: job.isFinal
            )
        }
        if outboundJob?.id == job.id {
            outboundJob = nil
        }
    }

    func failTranslation(job: TranslationJob, error: Error) {
        if ConversationViewModel.isTransientTranslationCancellation(error) {
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
        guard canSummarize else {
            summaryError = DuiyiError.summaryEmpty.userMessage(for: targetLanguage)
            isSummaryPresented = true
            return
        }
        isSettingsPresented = false
        isSummaryPresented = true
        isSummarizing = true
        summaryError = nil
        do {
            summary = try await summarizer.summarize(entries: transcript, outputLanguage: targetLanguage)
        } catch let error as DuiyiError {
            summary = nil
            summaryError = error.userMessage(for: targetLanguage)
        } catch {
            summary = nil
            summaryError = DuiyiError.summaryEmpty.userMessage(for: targetLanguage)
        }
        isSummarizing = false
    }

    private var currentUseCase: AudioUseCase {
        voiceOutEnabled && canSpeakWithoutEcho ? .interpretationVoiceOut : .interpretationCaptions
    }

    private func prepareVoiceOutRoute() async -> Bool {
        do {
            try await audioSession.activate(.interpretationVoiceOut)
        } catch {
            canSpeakWithoutEcho = false
            return false
        }
        var snapshot = await audioSession.currentRoute()
        if !snapshot.canSpeakWithoutEcho {
            try? await Task.sleep(for: .milliseconds(200))
            snapshot = await audioSession.currentRoute()
        }
        canSpeakWithoutEcho = snapshot.canSpeakWithoutEcho
        return canSpeakWithoutEcho
    }

    private func beginSpeechStream() async throws {
        let stream = try await speech.start(
            languages: [sourceLanguage],
            fallbackLanguage: sourceLanguage
        )
        speechTask?.cancel()
        speechTask = Task { [weak self] in
            for await utterance in stream {
                self?.accept(utterance)
            }
            await self?.handleStreamEnded()
        }
    }

    private func pauseCaptureForReroute() async {
        isStopping = true
        speechTask?.cancel()
        speechTask = nil
        await speech.stop()
        isStopping = false
    }

    private func rerouteCaptureIfListening() async {
        guard sessionState == .listening else {
            try? await audioSession.activate(currentUseCase)
            return
        }
        await pauseCaptureForReroute()
        do {
            try await audioSession.activate(currentUseCase)
            try await beginSpeechStream()
        } catch {
            sessionState = .failed(.recognitionInterrupted)
        }
    }

    private func applyDirectionChange() {
        pane.archiveLive()
        pane.speakingHint = nil
        outboundJob = nil
        translationDebounce?.cancel()
        lastAppliedSourceCount.removeAll()
        sentSourceText.removeAll()
        utteranceAliases.removeAll()
        spokenPrefixes.removeAll()
        lastSpokenTranslation = ""
        spokenCompactTail = ""
        cancelSpeechDebounces()
        if sessionState == .listening || sessionState == .paused {
            sessionState = .ready
        }
        Task { await clearSpeechQueue() }
    }

    private func enqueueTranslation(_ line: CaptionLine, isFinal: Bool) {
        let text = line.sourceText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        if sentSourceText[line.id] == text, !isFinal {
            return
        }

        let job = TranslationJob(
            utteranceID: line.id,
            source: sourceLanguage,
            target: targetLanguage,
            text: text,
            isFinal: isFinal
        )
        let isFirst = sentSourceText[line.id] == nil
        let shouldFlush = isFinal
            || ConversationViewModel.endsWithClause(text)
            || (isFirst && ConversationViewModel.isWorthTranslating(text, language: line.source))

        translationDebounce?.cancel()
        if shouldFlush {
            sentSourceText[line.id] = text
            outboundJob = job
            return
        }
        let delay = translationDelayMilliseconds(isFirst: isFirst)
        translationDebounce = Task { [weak self] in
            try? await Task.sleep(for: .milliseconds(delay))
            guard !Task.isCancelled else { return }
            self?.sentSourceText[line.id] = text
            self?.outboundJob = job
        }
    }

    @discardableResult
    private func applyTranslation(utteranceID: UUID, text: String, settle: Bool) -> Bool {
        let applied = pane.applyTranslation(utteranceID: utteranceID, text: text, settle: settle)
        if let index = transcript.firstIndex(where: { $0.id == utteranceID }) {
            transcript[index].translatedText = SpokenText.preferredTranslation(
                transcript[index].translatedText,
                text
            )
            if settle {
                transcript[index].isFinal = true
            }
        }
        collapseTranscriptRefinements()
        return applied
    }

    private func displayedTranslation(for utteranceID: UUID) -> String? {
        if pane.live?.id == utteranceID {
            let text = pane.live?.translatedText.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            return text.isEmpty ? nil : text
        }
        if let line = pane.history.first(where: { $0.id == utteranceID }) {
            let text = line.translatedText.trimmingCharacters(in: .whitespacesAndNewlines)
            return text.isEmpty ? nil : text
        }
        return nil
    }

    private func translationDelayMilliseconds(isFirst: Bool) -> UInt64 {
        if voiceOutEnabled {
            return isFirst ? 25 : 50
        }
        return isFirst
            ? ConversationLayout.firstTranslationDebounceMilliseconds
            : ConversationLayout.translationDebounceMilliseconds
    }

    private func scheduleSpeech(utteranceID: UUID, translated: String, settle: Bool) {
        guard voiceOutEnabled, canSpeakWithoutEcho else { return }
        guard settle else { return }
        let slot = speechSlot(for: utteranceID, translated: translated)
        pendingSettledSpeech[slot] = translated
        if speechSettleDelay <= .zero {
            enqueueSpokenClauses(utteranceID: utteranceID, translated: translated, settle: true)
            pendingSettledSpeech[slot] = nil
            return
        }
        speechDebounces[slot]?.cancel()
        speechDebounces[slot] = Task { [weak self] in
            try? await Task.sleep(for: self?.speechSettleDelay ?? .milliseconds(380))
            guard !Task.isCancelled else { return }
            guard let text = self?.pendingSettledSpeech[slot] else { return }
            self?.pendingSettledSpeech[slot] = nil
            self?.speechDebounces[slot] = nil
            self?.enqueueSpokenClauses(utteranceID: utteranceID, translated: text, settle: true)
        }
    }

    private func speechSlot(for utteranceID: UUID, translated: String) -> UUID {
        if let existing = pendingSettledSpeech[utteranceID] {
            if SpokenText.shouldReplaceScheduledSpeech(existing, with: translated) {
                return utteranceID
            }
            return UUID()
        }
        if let match = pendingSettledSpeech.first(where: {
            SpokenText.shouldReplaceScheduledSpeech($0.value, with: translated)
        }) {
            speechDebounces[match.key]?.cancel()
            speechDebounces[match.key] = nil
            pendingSettledSpeech[match.key] = nil
            return match.key
        }
        return utteranceID
    }

    private func enqueueSpokenClauses(utteranceID: UUID, translated: String, settle: Bool) {
        guard voiceOutEnabled, canSpeakWithoutEcho else { return }
        var alreadySpoken = spokenPrefixes[utteranceID] ?? ""
        if alreadySpoken.isEmpty || alreadySpoken.count < lastSpokenTranslation.count,
           ClauseSplitter.shouldCarry(lastSpokenTranslation, into: translated, language: targetLanguage) {
            alreadySpoken = lastSpokenTranslation
        }
        let (clauses, prefix) = ClauseSplitter.consume(
            translated: translated,
            utteranceID: utteranceID,
            language: targetLanguage,
            alreadySpoken: alreadySpoken,
            isSettled: settle
        )
        if !prefix.isEmpty {
            spokenPrefixes[utteranceID] = prefix
            lastSpokenTranslation = prefix
        }
        guard !clauses.isEmpty else { return }
        let queuedCompact = pendingJobs.map { SpokenText.compact($0.text) }.joined()
        let alreadyHeard = alreadySpoken + spokenCompactTail + queuedCompact
        let fresh = clauses.filter { clause in
            !SpokenText.containsCompact(alreadyHeard, clause: clause.text)
        }
        guard !fresh.isEmpty else { return }
        for clause in fresh {
            pendingJobs.append(SynthesisJob(clause: clause))
        }
        dropSurplusShortConfirmations()
        pumpSpeech()
    }

    private func dropSurplusShortConfirmations() {
        while pendingJobs.count > InterpretationLayout.speechQueueLimit {
            guard let index = pendingJobs.firstIndex(where: {
                SpokenText.compact($0.text).count <= InterpretationLayout.speechShortConfirmationLimit
            }) else {
                break
            }
            pendingJobs.remove(at: index)
        }
    }

    private func rememberSpoken(_ text: String) {
        spokenCompactTail += SpokenText.compact(text)
        let limit = 280
        if spokenCompactTail.count > limit {
            spokenCompactTail.removeFirst(spokenCompactTail.count - limit)
        }
    }

    private func pumpSpeech() {
        guard !isSpeaking else { return }
        guard let next = pendingJobs.first else { return }
        pendingJobs.removeFirst()
        isSpeaking = true
        rememberSpoken(next.text)
        let generation = speechGeneration
        speakTask = Task { [weak self] in
            guard let self, !Task.isCancelled, generation == self.speechGeneration else { return }
            await self.synthesizer.speak(next)
            guard !Task.isCancelled, generation == self.speechGeneration else { return }
            self.isSpeaking = false
            self.pumpSpeech()
        }
    }

    private func cancelSpeechDebounces() {
        for task in speechDebounces.values {
            task.cancel()
        }
        speechDebounces.removeAll()
        pendingSettledSpeech.removeAll()
    }

    private func clearSpeechQueue() async {
        speechGeneration += 1
        cancelSpeechDebounces()
        speakTask?.cancel()
        speakTask = nil
        pendingJobs.removeAll()
        isSpeaking = false
        await synthesizer.stopAndClear()
    }

    private func denyVoiceOut(_ reason: DuiyiError) async {
        voiceOutEnabled = false
        preferences.voiceOutEnabled = false
        canSpeakWithoutEcho = false
        voiceOutBlockedMessage = reason.userMessage(for: targetLanguage)
        await clearSpeechQueue()
    }

    private func forceVoiceOutOff(reason: DuiyiError) async {
        await denyVoiceOut(reason)
        await rerouteCaptureIfListening()
    }

    private func startRouteObserver() {
        guard routeTask == nil else { return }
        routeTask = Task { [weak self] in
            guard let self else { return }
            let stream = await self.audioSession.routeChanges()
            for await snapshot in stream {
                self.handleRoute(snapshot)
            }
        }
    }

    private func handleRoute(_ snapshot: AudioRouteSnapshot) {
        canSpeakWithoutEcho = snapshot.canSpeakWithoutEcho
        guard voiceOutEnabled, !canSpeakWithoutEcho else { return }
        Task { await confirmHeadphonesLost() }
    }

    private func confirmHeadphonesLost() async {
        try? await Task.sleep(for: .milliseconds(300))
        let snapshot = await audioSession.currentRoute()
        canSpeakWithoutEcho = snapshot.canSpeakWithoutEcho
        guard voiceOutEnabled, !canSpeakWithoutEcho else { return }
        await forceVoiceOutOff(reason: .voiceOutNeedsHeadphones)
    }

    private func upsertTranscript(line: CaptionLine) {
        if let index = transcript.firstIndex(where: { $0.id == line.id }) {
            transcript[index].sourceText = SpokenText.preferredSource(transcript[index].sourceText, line.sourceText)
            if !line.translatedText.isEmpty {
                transcript[index].translatedText = line.translatedText
            }
            transcript[index].isFinal = line.phase == .settled
            return
        }
        if let last = transcript.last,
           SpokenText.isContinuation(line.sourceText, of: last.sourceText, language: line.source)
            || SpokenText.isRefinement(line.sourceText, of: last.sourceText)
            || SpokenText.isRefinement(line.displayText, of: last.translatedText.isEmpty ? last.sourceText : last.translatedText) {
            var updated = last
            updated.sourceText = SpokenText.preferredSource(last.sourceText, line.sourceText)
            if !line.translatedText.isEmpty {
                updated.translatedText = line.translatedText
            }
            updated.isFinal = line.phase == .settled
            transcript[transcript.count - 1] = updated
            return
        }
        transcript.append(
            TranscriptEntry(
                id: line.id,
                speaker: .peer,
                source: line.source,
                sourceText: line.sourceText,
                translatedText: line.translatedText,
                isFinal: line.phase == .settled
            )
        )
        if transcript.count > InterpretationLayout.historyLimit {
            transcript.removeFirst(transcript.count - InterpretationLayout.historyLimit)
        }
        collapseTranscriptRefinements()
    }

    private func collapseTranscriptRefinements() {
        while transcript.count >= 2 {
            let last = transcript[transcript.count - 1]
            let prior = transcript[transcript.count - 2]
            let related = SpokenText.isContinuation(last.sourceText, of: prior.sourceText, language: last.source)
                || SpokenText.isRefinement(last.sourceText, of: prior.sourceText)
                || SpokenText.isRefinement(last.translatedText, of: prior.translatedText)
            guard related else { break }
            var merged = last
            merged.sourceText = SpokenText.preferredSource(prior.sourceText, last.sourceText)
            merged.translatedText = SpokenText.preferredTranslation(
                prior.translatedText,
                last.translatedText
            )
            merged.isFinal = prior.isFinal || last.isFinal
            transcript.removeLast()
            transcript[transcript.count - 1] = merged
        }
    }

    private func canonicalID(_ id: UUID) -> UUID {
        utteranceAliases[id] ?? id
    }

    private func handleStreamEnded() async {
        guard !isStopping, sessionState == .listening else { return }
        sessionState = .failed(.recognitionInterrupted)
        holdScreenAfterPause = false
        idleRestoreTask?.cancel()
        pane.speakingHint = nil
        await clearSpeechQueue()
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
