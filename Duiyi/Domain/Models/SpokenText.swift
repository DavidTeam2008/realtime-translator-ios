import Foundation

enum SpokenText {
    static func isContinuation(_ incoming: String, of previous: String, language: AppLanguage) -> Bool {
        let incomingText = normalized(incoming)
        let previousText = normalized(previous)
        guard !incomingText.isEmpty, !previousText.isEmpty else { return false }
        if incomingText == previousText { return true }
        if incomingText.hasPrefix(previousText) || previousText.hasPrefix(incomingText) {
            return true
        }
        if incomingText.contains(previousText), previousText.count >= minimumStemLength(for: language) {
            return true
        }
        let shared = zip(incomingText, previousText).prefix { $0 == $1 }.count
        let shorter = min(incomingText.count, previousText.count)
        guard shorter > 0 else { return false }
        return shared >= minimumStemLength(for: language) && Double(shared) / Double(shorter) >= 0.55
    }

    static func preferredSource(_ current: String, _ incoming: String) -> String {
        incoming.count >= current.count ? incoming : current
    }

    static func preferredTranslation(_ current: String, _ incoming: String) -> String {
        incoming.isEmpty ? current : incoming
    }

    static func normalized(_ text: String) -> String {
        text.lowercased().filter { $0.isLetter || $0.isNumber }
    }

    private static func minimumStemLength(for language: AppLanguage) -> Int {
        language.usesLatinScript ? 16 : 6
    }
}
