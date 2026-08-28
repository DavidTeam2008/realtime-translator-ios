import Foundation

struct Utterance: Equatable, Sendable, Identifiable {
    let id: UUID
    let language: AppLanguage
    let text: String
    let isFinal: Bool
    let createdAt: Date

    init(
        id: UUID = UUID(),
        language: AppLanguage,
        text: String,
        isFinal: Bool,
        createdAt: Date = .now
    ) {
        self.id = id
        self.language = language
        self.text = text
        self.isFinal = isFinal
        self.createdAt = createdAt
    }
}
