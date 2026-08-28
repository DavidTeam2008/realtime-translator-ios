import Foundation

struct TranslationJob: Equatable, Sendable, Identifiable {
    let id: UUID
    let utteranceID: UUID
    let source: AppLanguage
    let target: AppLanguage
    let text: String
    let isFinal: Bool

    init(
        id: UUID = UUID(),
        utteranceID: UUID,
        source: AppLanguage,
        target: AppLanguage,
        text: String,
        isFinal: Bool
    ) {
        self.id = id
        self.utteranceID = utteranceID
        self.source = source
        self.target = target
        self.text = text
        self.isFinal = isFinal
    }
}
