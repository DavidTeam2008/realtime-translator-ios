import AVFAudio
import Foundation
import Speech

actor BilingualSpeechEngine: SpeechRecognizing {
    private let capturer: AudioCapturing
    private var assembler = UtteranceAssembler()
    private var utteranceContinuation: AsyncStream<Utterance>.Continuation?
    private var analyzer: SpeechAnalyzer?
    private var inputContinuation: AsyncStream<AnalyzerInput>.Continuation?
    private var consumeTasks: [Task<Void, Never>] = []
    private var audioTask: Task<Void, Never>?
    private var silenceTask: Task<Void, Never>?
    private var reservedLocales: [Locale] = []
    private var lastFinalSignature: String?
    private var ignoreTranscriptionUntil: Date = .distantPast
    private var converter = BufferConverter()
    private var analyzerFormat: AVAudioFormat?
    private var usingDual = true
    private var pairLanguages: [AppLanguage] = [.zhHans, .english]
    private var singleLanguage: AppLanguage = .english
    private var style: SpeechRecognitionStyle = .liveCaptions

    init(capturer: AudioCapturing = AudioEngineCapturer()) {
        self.capturer = capturer
    }

    func start(
        languages: [AppLanguage],
        fallbackLanguage: AppLanguage,
        style: SpeechRecognitionStyle
    ) async throws -> AsyncStream<Utterance> {
        await stop()
        assembler.reset()
        lastFinalSignature = nil
        self.style = style
        let requested = Array(
            Self.normalizedLanguages(languages: languages, fallback: fallbackLanguage).prefix(2)
        )
        pairLanguages = requested
        singleLanguage = fallbackLanguage

        let (stream, continuation) = AsyncStream<Utterance>.makeStream()
        utteranceContinuation = continuation
        continuation.onTermination = { [weak self] _ in
            Task { await self?.stop() }
        }

        do {
            try await startBestPipeline(languages: requested, fallback: fallbackLanguage)
        } catch {
            throw error
        }

        return stream
    }

    func stop() async {
        silenceTask?.cancel()
        silenceTask = nil
        audioTask?.cancel()
        audioTask = nil
        for task in consumeTasks {
            task.cancel()
        }
        consumeTasks.removeAll()
        inputContinuation?.finish()
        inputContinuation = nil
        await capturer.stop()
        if let analyzer {
            await analyzer.cancelAndFinishNow()
        }
        analyzer = nil
        converter = BufferConverter()
        utteranceContinuation?.finish()
        utteranceContinuation = nil
        for locale in reservedLocales {
            _ = await AssetInventory.release(reservedLocale: locale)
        }
        reservedLocales.removeAll()
    }

    private func startBestPipeline(languages: [AppLanguage], fallback: AppLanguage) async throws {
        var remaining = languages
        while !remaining.isEmpty {
            do {
                if remaining.count >= 2 {
                    try await startMultiPipeline(languages: remaining)
                    usingDual = true
                    pairLanguages = Array(remaining.prefix(2))
                    return
                }
                try await startSinglePipeline(language: remaining[0])
                usingDual = false
                return
            } catch {
                guard Self.isResourceLimit(error), remaining.count > 1 else {
                    throw error
                }
                DuiyiLog.speech.error(
                    "Locale set of \(remaining.count, privacy: .public) failed, dropping \(remaining.last?.rawValue ?? "", privacy: .public)"
                )
                remaining.removeLast()
                await resetPipelineKeepingStream()
            }
        }
        DuiyiLog.speech.error("Dual transcribers unavailable, falling back to single locale")
        try await startSinglePipeline(language: fallback)
        usingDual = false
    }

    private func startMultiPipeline(languages: [AppLanguage]) async throws {
        let pair = Array(languages.prefix(2))
        pairLanguages = pair
        guard pair.count == 2 else {
            try await startSinglePipeline(language: pair[0])
            return
        }
        try await startDualPipeline()
    }

    private func resetPipelineKeepingStream() async {
        silenceTask?.cancel()
        silenceTask = nil
        audioTask?.cancel()
        audioTask = nil
        for task in consumeTasks {
            task.cancel()
        }
        consumeTasks.removeAll()
        inputContinuation?.finish()
        inputContinuation = nil
        await capturer.stop()
        if let analyzer {
            await analyzer.cancelAndFinishNow()
        }
        analyzer = nil
        converter = BufferConverter()
        for locale in reservedLocales {
            _ = await AssetInventory.release(reservedLocale: locale)
        }
        reservedLocales.removeAll()
    }

    private func startDualPipeline() async throws {
        let firstLanguage = pairLanguages[0]
        let secondLanguage = pairLanguages[1]
        let firstLocale = try await resolvedLocale(for: firstLanguage)
        let secondLocale = try await resolvedLocale(for: secondLanguage)
        try await reserve([firstLocale, secondLocale])

        let first = Self.makeTranscriber(locale: firstLocale)
        let second = Self.makeTranscriber(locale: secondLocale)
        let detector = SpeechDetector(
            detectionOptions: SpeechDetector.DetectionOptions(sensitivityLevel: .medium),
            reportResults: true
        )
        var modules: [any SpeechModule] = [first, second, detector]

        do {
            try await run(modules: modules)
        } catch {
            if Self.isResourceLimit(error) {
                DuiyiLog.speech.error("Detector plus dual transcribers failed, retrying without detector")
                modules = [first, second]
                try await run(modules: modules)
            } else {
                throw error
            }
        }

        consume(transcriber: first, language: firstLanguage)
        consume(transcriber: second, language: secondLanguage)
        consume(detector: detector)
    }

    private func startSinglePipeline(language: AppLanguage) async throws {
        singleLanguage = language
        let locale = try await resolvedLocale(for: language)
        try await reserve([locale])
        let transcriber = Self.makeTranscriber(locale: locale)
        try await run(modules: [transcriber])
        consume(transcriber: transcriber, language: language)
    }

    private func run(modules: [any SpeechModule]) async throws {
        guard let format = await SpeechAnalyzer.bestAvailableAudioFormat(compatibleWith: modules) else {
            throw DuiyiError.deviceIncapable
        }
        analyzerFormat = format
        let options = style == .meetingNotes
            ? SpeechAnalyzer.Options(priority: .userInitiated, modelRetention: .whileInUse)
            : nil
        let analyzer = SpeechAnalyzer(modules: modules, options: options)
        self.analyzer = analyzer
        try await analyzer.prepareToAnalyze(in: format)

        let (input, continuation) = AsyncStream<AnalyzerInput>.makeStream()
        inputContinuation = continuation

        let audioStream = try await capturer.start()
        audioTask = Task { [weak self] in
            guard let self else { return }
            for await packet in audioStream {
                await self.ingest(packet.buffer)
            }
        }

        consumeTasks.append(
            Task { [weak self] in
                do {
                    try await analyzer.start(inputSequence: input)
                } catch is CancellationError {
                    return
                } catch {
                    DuiyiLog.speech.error("Analyzer failed: \(error.localizedDescription, privacy: .public)")
                    await self?.fail(.recognitionInterrupted)
                }
            }
        )
    }

    private func ingest(_ buffer: AVAudioPCMBuffer) async {
        guard let format = analyzerFormat, let inputContinuation else { return }
        do {
            let converted = try converter.convert(buffer, to: format)
            inputContinuation.yield(AnalyzerInput(buffer: converted))
        } catch {
            DuiyiLog.audio.error("Audio convert failed: \(error.localizedDescription, privacy: .public)")
        }
    }

    private func consume(transcriber: SpeechTranscriber, language: AppLanguage) {
        consumeTasks.append(
            Task { [weak self] in
                do {
                    for try await result in transcriber.results {
                        let text = String(result.text.characters)
                        await self?.handleTranscription(
                            language: language,
                            text: text,
                            isFinal: result.isFinal
                        )
                    }
                } catch is CancellationError {
                    return
                } catch {
                    DuiyiLog.speech.error("Transcriber failed: \(error.localizedDescription, privacy: .public)")
                    await self?.fail(.recognitionInterrupted)
                }
            }
        )
    }

    private func consume(detector: SpeechDetector) {
        consumeTasks.append(
            Task { [weak self] in
                do {
                    for try await result in detector.results {
                        await self?.handleVoiceActivity(result.speechDetected)
                    }
                } catch is CancellationError {
                    return
                } catch {
                    DuiyiLog.speech.error("Detector failed: \(error.localizedDescription, privacy: .public)")
                }
            }
        )
    }

    private func handleTranscription(language: AppLanguage, text: String, isFinal: Bool) {
        if Date() < ignoreTranscriptionUntil {
            return
        }
        guard let utterance = assembler.ingest(language: language, text: text, isFinal: isFinal) else {
            return
        }
        publish(utterance)
        if utterance.isFinal {
            assembler.acknowledgeFinal(language: utterance.language)
            scheduleSingleLocaleSwitchIfNeeded(to: utterance.language)
        }
        pingSilenceTimer()
    }

    private func handleVoiceActivity(_ speechDetected: Bool) {
        if speechDetected {
            silenceTask?.cancel()
            silenceTask = nil
        } else {
            pingSilenceTimer()
        }
    }

    private func pingSilenceTimer() {
        silenceTask?.cancel()
        silenceTask = Task { [weak self] in
            try? await Task.sleep(for: .milliseconds(ConversationLayout.silenceCommitMilliseconds))
            guard !Task.isCancelled else { return }
            await self?.finalizeFromSilence()
        }
    }

    private func finalizeFromSilence() {
        guard let utterance = assembler.silenceTimedOut() else { return }
        publish(utterance)
        scheduleSingleLocaleSwitchIfNeeded(to: utterance.language)
    }

    private func publish(_ utterance: Utterance) {
        if utterance.isFinal {
            let signature = Self.signature(utterance)
            if signature == lastFinalSignature {
                return
            }
            lastFinalSignature = signature
        }
        utteranceContinuation?.yield(utterance)
    }

    private func fail(_ error: DuiyiError) {
        utteranceContinuation?.finish()
    }

    private func scheduleSingleLocaleSwitchIfNeeded(to language: AppLanguage) {
        guard !usingDual, language != singleLanguage else { return }
        Task { [weak self] in
            await self?.restartSingle(language: language)
        }
    }

    private func restartSingle(language: AppLanguage) async {
        DuiyiLog.speech.info("Switching single transcriber to \(language.rawValue, privacy: .public)")
        await resetPipelineKeepingStream()
        assembler.reset()
        do {
            try await startSinglePipeline(language: language)
            usingDual = false
        } catch {
            DuiyiLog.speech.error("Single locale restart failed: \(error.localizedDescription, privacy: .public)")
            fail(.recognitionInterrupted)
        }
    }

    private func resolvedLocale(for language: AppLanguage) async throws -> Locale {
        guard let locale = await SpeechTranscriber.supportedLocale(equivalentTo: language.locale) else {
            throw DuiyiError.languageUnsupported
        }
        return locale
    }

    private func reserve(_ locales: [Locale]) async throws {
        for locale in locales {
            do {
                _ = try await AssetInventory.reserve(locale: locale)
                reservedLocales.append(locale)
            } catch {
                if Self.isResourceLimit(error) {
                    throw error
                }
                DuiyiLog.speech.error("Locale reserve failed: \(error.localizedDescription, privacy: .public)")
            }
        }
    }

    private static func makeTranscriber(locale: Locale) -> SpeechTranscriber {
        SpeechTranscriber(
            locale: locale,
            transcriptionOptions: [.etiquetteReplacements],
            reportingOptions: [.volatileResults, .fastResults],
            attributeOptions: [.transcriptionConfidence]
        )
    }

    private static func signature(_ utterance: Utterance) -> String {
        let filtered = utterance.text.lowercased().filter { $0.isLetter || $0.isNumber || $0.isWhitespace }
        return "\(utterance.language.rawValue)-\(filtered)"
    }

    static func normalizedLanguages(languages: [AppLanguage], fallback: AppLanguage) -> [AppLanguage] {
        var unique: [AppLanguage] = []
        for language in languages where !unique.contains(language) {
            unique.append(language)
        }
        if unique.isEmpty {
            unique.append(fallback)
        }
        return unique
    }

    private static func isResourceLimit(_ error: Error) -> Bool {
        if let speechError = error as? SFSpeechError {
            switch speechError.code {
            case .insufficientResources, .tooManyAssetLocalesAllocated:
                return true
            default:
                return false
            }
        }
        let nsError = error as NSError
        return nsError.domain.contains("Speech") && [
            SFSpeechError.Code.insufficientResources.rawValue,
            SFSpeechError.Code.tooManyAssetLocalesAllocated.rawValue
        ].contains(nsError.code)
    }
}
