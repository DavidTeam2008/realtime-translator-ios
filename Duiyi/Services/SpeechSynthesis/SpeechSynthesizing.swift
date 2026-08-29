import Foundation

protocol SpeechSynthesizing: Sendable {
    func hasVoice(for language: AppLanguage) async -> Bool
    func speak(_ job: SynthesisJob) async
    func stopAndClear() async
}

struct PreviewSynthesizer: SpeechSynthesizing {
    func hasVoice(for language: AppLanguage) async -> Bool {
        _ = language
        return true
    }

    func speak(_ job: SynthesisJob) async {
        _ = job
    }

    func stopAndClear() async {}
}
