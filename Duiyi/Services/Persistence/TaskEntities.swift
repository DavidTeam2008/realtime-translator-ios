import Foundation
import SwiftData

@Model
final class TaskEntity {
    var id: UUID
    var featureRaw: String
    var statusRaw: String
    var startedAt: Date
    var endedAt: Date?
    var title: String
    var subtitle: String?
    var sourceLanguageRaw: String
    var targetLanguageRaw: String?
    var summaryText: String?
    var usedAppleIntelligence: Bool
    var schemaVersion: Int
    @Relationship(deleteRule: .cascade, inverse: \TranscriptEntity.task)
    var entries: [TranscriptEntity]

    init(
        id: UUID,
        featureRaw: String,
        statusRaw: String,
        startedAt: Date,
        endedAt: Date? = nil,
        title: String,
        subtitle: String? = nil,
        sourceLanguageRaw: String,
        targetLanguageRaw: String? = nil,
        summaryText: String? = nil,
        usedAppleIntelligence: Bool = false,
        schemaVersion: Int = 1,
        entries: [TranscriptEntity] = []
    ) {
        self.id = id
        self.featureRaw = featureRaw
        self.statusRaw = statusRaw
        self.startedAt = startedAt
        self.endedAt = endedAt
        self.title = title
        self.subtitle = subtitle
        self.sourceLanguageRaw = sourceLanguageRaw
        self.targetLanguageRaw = targetLanguageRaw
        self.summaryText = summaryText
        self.usedAppleIntelligence = usedAppleIntelligence
        self.schemaVersion = schemaVersion
        self.entries = entries
    }
}

@Model
final class TranscriptEntity {
    var id: UUID
    var speakerRaw: String
    var sourceRaw: String
    var sourceText: String
    var translatedText: String
    var isFinal: Bool
    var recordedAt: Date
    var sortIndex: Int
    var task: TaskEntity?

    init(
        id: UUID,
        speakerRaw: String,
        sourceRaw: String,
        sourceText: String,
        translatedText: String,
        isFinal: Bool,
        recordedAt: Date,
        sortIndex: Int
    ) {
        self.id = id
        self.speakerRaw = speakerRaw
        self.sourceRaw = sourceRaw
        self.sourceText = sourceText
        self.translatedText = translatedText
        self.isFinal = isFinal
        self.recordedAt = recordedAt
        self.sortIndex = sortIndex
    }
}

enum TaskMapping {
    static func session(from entity: TaskEntity) -> TaskSession? {
        guard let feature = FeatureID(rawValue: entity.featureRaw),
              let status = TaskStatus(rawValue: entity.statusRaw),
              let source = AppLanguage(rawValue: entity.sourceLanguageRaw) else {
            return nil
        }
        let target = entity.targetLanguageRaw.flatMap(AppLanguage.init(rawValue:))
        let entries = entity.entries
            .sorted { $0.sortIndex < $1.sortIndex }
            .compactMap(entry(from:))
        let summary: ConversationSummary?
        if let text = entity.summaryText, !text.isEmpty {
            summary = ConversationSummary(text: text, usedAppleIntelligence: entity.usedAppleIntelligence)
        } else {
            summary = nil
        }
        return TaskSession(
            id: entity.id,
            feature: feature,
            status: status,
            startedAt: entity.startedAt,
            endedAt: entity.endedAt,
            title: entity.title,
            subtitle: entity.subtitle,
            sourceLanguage: source,
            targetLanguage: target,
            entries: entries,
            summary: summary
        )
    }

    static func entry(from entity: TranscriptEntity) -> TranscriptEntry? {
        guard let speaker = SpeakerSide(rawValue: entity.speakerRaw),
              let source = AppLanguage(rawValue: entity.sourceRaw) else {
            return nil
        }
        return TranscriptEntry(
            id: entity.id,
            speaker: speaker,
            source: source,
            sourceText: entity.sourceText,
            translatedText: entity.translatedText,
            isFinal: entity.isFinal,
            recordedAt: entity.recordedAt
        )
    }
}
