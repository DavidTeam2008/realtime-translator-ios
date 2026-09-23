import AVFoundation
import Foundation

@MainActor
final class SystemSpeechSynthesizer: NSObject, SpeechSynthesizing, AVSpeechSynthesizerDelegate {
    // Lazy: AVSpeechSynthesizer() loads voices + spins up synthesis daemon IPC.
    // Must not run during first-frame construction.
    private var synthesizer: AVSpeechSynthesizer?
    private var finish: CheckedContinuation<Void, Never>?

    override init() {
        super.init()
    }

    private func ensureSynthesizer() -> AVSpeechSynthesizer {
        if let synthesizer { return synthesizer }
        let created = AVSpeechSynthesizer()
        created.delegate = self
        synthesizer = created
        return created
    }

    func hasVoice(for language: AppLanguage) async -> Bool {
        AVSpeechSynthesisVoice(language: language.speechVoiceLanguage) != nil
    }

    func speak(_ job: SynthesisJob) async {
        finishPending()
        let trimmed = job.text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        guard let voice = AVSpeechSynthesisVoice(language: job.language.speechVoiceLanguage) else {
            return
        }
        let utterance = AVSpeechUtterance(string: trimmed)
        utterance.voice = voice
        utterance.rate = min(AVSpeechUtteranceDefaultSpeechRate * 1.28, AVSpeechUtteranceMaximumSpeechRate)
        utterance.preUtteranceDelay = 0
        utterance.postUtteranceDelay = 0
        await withCheckedContinuation { continuation in
            finish = continuation
            ensureSynthesizer().speak(utterance)
        }
    }

    func stopAndClear() async {
        synthesizer?.stopSpeaking(at: .immediate)
        finishPending()
    }

    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didFinish utterance: AVSpeechUtterance) {
        Task { @MainActor in
            self.finishPending()
        }
    }

    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didCancel utterance: AVSpeechUtterance) {
        Task { @MainActor in
            self.finishPending()
        }
    }

    private func finishPending() {
        finish?.resume()
        finish = nil
    }
}
