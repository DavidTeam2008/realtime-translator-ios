import Foundation
import Speech

actor SpeechAssetPreparer: SpeechModelPreparing {
    func isDeviceCapable(for languages: [AppLanguage]) async -> Bool {
        guard SpeechTranscriber.isAvailable else { return false }
        for language in unique(languages) {
            if await SpeechTranscriber.supportedLocale(equivalentTo: language.locale) == nil {
                return false
            }
        }
        return true
    }

    func prepare(languages: [AppLanguage], progress: @escaping @Sendable (Double) -> Void) async throws {
        guard await isDeviceCapable(for: languages) else {
            throw DuiyiError.deviceIncapable
        }

        let modules = try await makePlaceholderModules(for: unique(languages))
        if let request = try await AssetInventory.assetInstallationRequest(supporting: modules) {
            let progressReporter = request.progress
            let ticker = Task {
                while !Task.isCancelled {
                    progress(progressReporter.fractionCompleted)
                    try await Task.sleep(for: .milliseconds(200))
                }
            }
            defer { ticker.cancel() }
            DuiyiLog.assets.info("Downloading speech models")
            try await request.downloadAndInstall()
            progress(1)
            DuiyiLog.assets.info("Speech models installed")
        } else {
            progress(1)
        }
    }

    private func makePlaceholderModules(for languages: [AppLanguage]) async throws -> [any SpeechModule] {
        var modules: [any SpeechModule] = []
        for language in languages {
            guard let locale = await SpeechTranscriber.supportedLocale(equivalentTo: language.locale) else {
                throw DuiyiError.languageUnsupported
            }
            modules.append(SpeechTranscriber(locale: locale, preset: .progressiveTranscription))
        }
        guard !modules.isEmpty else {
            throw DuiyiError.languageUnsupported
        }
        return modules
    }

    private func unique(_ languages: [AppLanguage]) -> [AppLanguage] {
        var result: [AppLanguage] = []
        for language in languages where !result.contains(language) {
            result.append(language)
        }
        return result
    }
}
