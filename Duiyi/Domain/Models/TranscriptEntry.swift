import Foundation

struct TranscriptEntry: Identifiable, Equatable, Sendable, Codable {
    var id: UUID
    var speaker: SpeakerSide
    var source: AppLanguage
    var sourceText: String
    var translatedText: String
    var isFinal: Bool
    var recordedAt: Date = .now

    func readableText(for language: AppLanguage) -> String {
        if !translatedText.isEmpty {
            return translatedText
        }
        if source == language {
            return sourceText
        }
        return sourceText
    }
}

enum SummaryAvailability: Equatable, Sendable {
    case available
    case deviceNotEligible
    case appleIntelligenceOff
    case modelNotReady
    case unavailable
}

struct ConversationSummary: Equatable, Sendable, Codable {
    var text: String
    var usedAppleIntelligence: Bool
}

protocol ConversationSummarizing: Sendable {
    func availability() async -> SummaryAvailability
    func summarize(
        entries: [TranscriptEntry],
        outputLanguage: AppLanguage
    ) async throws -> ConversationSummary
}
