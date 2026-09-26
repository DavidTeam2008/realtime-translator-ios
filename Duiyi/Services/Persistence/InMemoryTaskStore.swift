import Foundation

@MainActor
final class InMemoryTaskStore: TaskStore {
    private var tasks: [UUID: TaskSession] = [:]

    func activeTask(for feature: FeatureID) async -> TaskSession? {
        tasks.values
            .filter { $0.feature == feature && $0.status != .ended }
            .sorted { $0.startedAt > $1.startedAt }
            .first
    }

    func unfinishedTasks() async -> [TaskSession] {
        tasks.values
            .filter { $0.status != .ended }
            .sorted { $0.startedAt > $1.startedAt }
    }

    func startNew(
        feature: FeatureID,
        source: AppLanguage,
        target: AppLanguage?,
        multilingual: Bool
    ) async throws -> TaskSession {
        let startedAt = Date()
        let session = TaskSession(
            id: UUID(),
            feature: feature,
            status: .running,
            startedAt: startedAt,
            endedAt: nil,
            title: TaskTitle.make(
                feature: feature,
                source: source,
                target: target,
                startedAt: startedAt,
                language: target ?? source,
                multilingual: multilingual
            ),
            subtitle: nil,
            sourceLanguage: source,
            targetLanguage: target,
            entries: [],
            summary: nil
        )
        tasks[session.id] = session
        return session
    }

    func append(taskID: UUID, entries: [TranscriptEntry]) async {
        guard var task = tasks[taskID], task.status != .ended else { return }
        var map = Dictionary(uniqueKeysWithValues: task.entries.map { ($0.id, $0) })
        for entry in entries {
            map[entry.id] = entry
        }
        var seen = Set<UUID>()
        var ordered: [TranscriptEntry] = []
        for existing in task.entries {
            if let updated = map[existing.id] {
                ordered.append(updated)
                seen.insert(existing.id)
            }
        }
        for entry in entries where !seen.contains(entry.id) {
            ordered.append(entry)
        }
        task.entries = ordered
        tasks[taskID] = task
    }

    func updateTranslations(taskID: UUID, entries: [TranscriptEntry]) async {
        guard var task = tasks[taskID] else { return }
        var translations: [UUID: String] = [:]
        for entry in entries {
            translations[entry.id] = entry.translatedText
        }
        for index in task.entries.indices {
            if let translatedText = translations[task.entries[index].id] {
                task.entries[index].translatedText = translatedText
            }
        }
        tasks[taskID] = task
    }

    func setStatus(taskID: UUID, status: TaskStatus) async {
        guard var task = tasks[taskID], task.status != .ended else { return }
        task.status = status
        tasks[taskID] = task
    }

    func saveSummary(taskID: UUID, summary: ConversationSummary) async {
        guard var task = tasks[taskID] else { return }
        task.summary = summary
        tasks[taskID] = task
    }

    func end(taskID: UUID, summary: ConversationSummary?) async throws -> TaskSession {
        guard var task = tasks[taskID] else { throw TaskStoreError.notFound }
        task.status = .ended
        task.endedAt = Date()
        if let summary {
            task.summary = summary
        }
        if task.feature == .meeting, task.subtitle == nil {
            task.subtitle = TaskTitle.subtitle(from: task.entries)
        }
        tasks[taskID] = task
        return task
    }

    func list(filter: FeatureID?) async -> [TaskSession] {
        tasks.values
            .filter { $0.status == .ended }
            .filter { filter == nil || $0.feature == filter }
            .sorted { $0.startedAt > $1.startedAt }
    }

    func task(id: UUID) async -> TaskSession? {
        tasks[id]
    }

    func delete(id: UUID) async throws {
        guard tasks.removeValue(forKey: id) != nil else { throw TaskStoreError.notFound }
    }
}
