import Foundation
import SwiftData

@MainActor
final class SwiftDataTaskStore: TaskStore {
    private let context: ModelContext

    init(container: ModelContainer) {
        context = ModelContext(container)
        context.autosaveEnabled = true
    }

    func activeTask(for feature: FeatureID) async -> TaskSession? {
        let raw = feature.rawValue
        let ended = TaskStatus.ended.rawValue
        var descriptor = FetchDescriptor<TaskEntity>(
            predicate: #Predicate { entity in
                entity.featureRaw == raw && entity.statusRaw != ended
            },
            sortBy: [SortDescriptor(\.startedAt, order: .reverse)]
        )
        descriptor.fetchLimit = 1
        return (try? context.fetch(descriptor))?.first.flatMap(TaskMapping.session(from:))
    }

    func unfinishedTasks() async -> [TaskSession] {
        let ended = TaskStatus.ended.rawValue
        let descriptor = FetchDescriptor<TaskEntity>(
            predicate: #Predicate { entity in
                entity.statusRaw != ended
            },
            sortBy: [SortDescriptor(\.startedAt, order: .reverse)]
        )
        return ((try? context.fetch(descriptor)) ?? []).compactMap(TaskMapping.session(from:))
    }

    func startNew(feature: FeatureID, source: AppLanguage, target: AppLanguage?) async throws -> TaskSession {
        let startedAt = Date()
        let title = TaskTitle.make(
            feature: feature,
            source: source,
            target: target,
            startedAt: startedAt,
            language: target ?? source
        )
        let entity = TaskEntity(
            id: UUID(),
            featureRaw: feature.rawValue,
            statusRaw: TaskStatus.running.rawValue,
            startedAt: startedAt,
            title: title,
            sourceLanguageRaw: source.rawValue,
            targetLanguageRaw: target?.rawValue
        )
        context.insert(entity)
        try context.save()
        guard let session = TaskMapping.session(from: entity) else {
            throw TaskStoreError.notFound
        }
        return session
    }

    func append(taskID: UUID, entries: [TranscriptEntry]) async {
        guard let entity = entity(id: taskID), entity.statusRaw != TaskStatus.ended.rawValue else { return }
        var existing = Dictionary(uniqueKeysWithValues: entity.entries.map { ($0.id, $0) })
        var nextIndex = (entity.entries.map(\.sortIndex).max() ?? -1) + 1
        for entry in entries {
            if let current = existing[entry.id] {
                current.speakerRaw = entry.speaker.rawValue
                current.sourceRaw = entry.source.rawValue
                current.sourceText = entry.sourceText
                current.translatedText = entry.translatedText
                current.isFinal = entry.isFinal
                current.recordedAt = entry.recordedAt
            } else {
                let created = TranscriptEntity(
                    id: entry.id,
                    speakerRaw: entry.speaker.rawValue,
                    sourceRaw: entry.source.rawValue,
                    sourceText: entry.sourceText,
                    translatedText: entry.translatedText,
                    isFinal: entry.isFinal,
                    recordedAt: entry.recordedAt,
                    sortIndex: nextIndex
                )
                created.task = entity
                entity.entries.append(created)
                existing[entry.id] = created
                nextIndex += 1
            }
        }
        try? context.save()
    }

    func setStatus(taskID: UUID, status: TaskStatus) async {
        guard let entity = entity(id: taskID), entity.statusRaw != TaskStatus.ended.rawValue else { return }
        entity.statusRaw = status.rawValue
        try? context.save()
    }

    func saveSummary(taskID: UUID, summary: ConversationSummary) async {
        guard let entity = entity(id: taskID) else { return }
        entity.summaryText = summary.text
        entity.usedAppleIntelligence = summary.usedAppleIntelligence
        try? context.save()
    }

    func end(taskID: UUID, summary: ConversationSummary?) async throws -> TaskSession {
        guard let entity = entity(id: taskID) else { throw TaskStoreError.notFound }
        entity.statusRaw = TaskStatus.ended.rawValue
        entity.endedAt = Date()
        if let summary {
            entity.summaryText = summary.text
            entity.usedAppleIntelligence = summary.usedAppleIntelligence
        }
        if entity.featureRaw == FeatureID.meeting.rawValue, entity.subtitle == nil {
            let session = TaskMapping.session(from: entity)
            entity.subtitle = session.flatMap { TaskTitle.subtitle(from: $0.entries) }
        }
        try context.save()
        guard let session = TaskMapping.session(from: entity) else { throw TaskStoreError.notFound }
        return session
    }

    func list(filter: FeatureID?) async -> [TaskSession] {
        let ended = TaskStatus.ended.rawValue
        let descriptor: FetchDescriptor<TaskEntity>
        if let filter {
            let raw = filter.rawValue
            descriptor = FetchDescriptor<TaskEntity>(
                predicate: #Predicate { entity in
                    entity.statusRaw == ended && entity.featureRaw == raw
                },
                sortBy: [SortDescriptor(\.startedAt, order: .reverse)]
            )
        } else {
            descriptor = FetchDescriptor<TaskEntity>(
                predicate: #Predicate { entity in
                    entity.statusRaw == ended
                },
                sortBy: [SortDescriptor(\.startedAt, order: .reverse)]
            )
        }
        return ((try? context.fetch(descriptor)) ?? []).compactMap(TaskMapping.session(from:))
    }

    func task(id: UUID) async -> TaskSession? {
        entity(id: id).flatMap(TaskMapping.session(from:))
    }

    func delete(id: UUID) async throws {
        guard let entity = entity(id: id) else { throw TaskStoreError.notFound }
        context.delete(entity)
        try context.save()
    }

    private func entity(id: UUID) -> TaskEntity? {
        var descriptor = FetchDescriptor<TaskEntity>(
            predicate: #Predicate { entity in
                entity.id == id
            }
        )
        descriptor.fetchLimit = 1
        return try? context.fetch(descriptor).first
    }
}
