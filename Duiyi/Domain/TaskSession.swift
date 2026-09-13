import Foundation

enum TaskStatus: String, Codable, Sendable, Hashable {
    case running
    case pausedListening
    case ended
}

struct TaskSession: Identifiable, Equatable, Sendable {
    var id: UUID
    var feature: FeatureID
    var status: TaskStatus
    var startedAt: Date
    var endedAt: Date?
    var title: String
    var subtitle: String?
    var sourceLanguage: AppLanguage
    var targetLanguage: AppLanguage?
    var entries: [TranscriptEntry]
    var summary: ConversationSummary?

    var hasTranscript: Bool {
        entries.contains { !$0.sourceText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
    }

    var duration: TimeInterval {
        (endedAt ?? .now).timeIntervalSince(startedAt)
    }

    func characterCount() -> Int {
        entries.reduce(0) { $0 + $1.sourceText.count + $1.translatedText.count }
    }
}

enum TaskTitle {
    static func make(
        feature: FeatureID,
        source: AppLanguage,
        target: AppLanguage?,
        startedAt: Date,
        language: AppLanguage,
        multilingual: Bool = false
    ) -> String {
        let day = startedAt.formatted(
            Date.FormatStyle(date: .abbreviated, time: .omitted)
                .month()
                .day()
                .locale(language.locale)
        )
        let module = Copy.featureTitle(feature, for: language)
        switch feature {
        case .faceToFace:
            let pair = target ?? source.defaultPeer
            return "\(day) \(module) · \(source.nativeName) ↔ \(pair.nativeName)"
        case .simultaneous:
            let pair = target ?? source.defaultPeer
            return "\(day) \(module) · \(source.nativeName) → \(pair.nativeName)"
        case .meeting:
            let label = multilingual
                ? Copy.meetingMultilingual(for: language)
                : source.nativeName
            return "\(day) \(module) · \(label)"
        }
    }

    static func subtitle(from entries: [TranscriptEntry]) -> String? {
        guard let first = entries.first(where: {
            !$0.sourceText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        }) else {
            return nil
        }
        let text = first.sourceText.trimmingCharacters(in: .whitespacesAndNewlines)
        if text.count <= 16 {
            return text
        }
        return String(text.prefix(16))
    }
}

enum MeetingLayout {
    static let transcriptCharacterLimit = 20_000
}

enum MeetingRecognition {
    static func languages(
        multilingual: Bool,
        pinned: AppLanguage,
        display: AppLanguage
    ) -> [AppLanguage] {
        guard multilingual else { return [pinned] }
        let peer = display.defaultPeer
        if peer == display {
            return [display]
        }
        return [display, peer]
    }
}

enum TaskStoreError: Error, Equatable, Sendable {
    case notFound
}

@MainActor
protocol TaskStore: AnyObject {
    func activeTask(for feature: FeatureID) async -> TaskSession?
    func unfinishedTasks() async -> [TaskSession]
    func startNew(
        feature: FeatureID,
        source: AppLanguage,
        target: AppLanguage?,
        multilingual: Bool
    ) async throws -> TaskSession
    func append(taskID: UUID, entries: [TranscriptEntry]) async
    func setStatus(taskID: UUID, status: TaskStatus) async
    func saveSummary(taskID: UUID, summary: ConversationSummary) async
    func end(taskID: UUID, summary: ConversationSummary?) async throws -> TaskSession
    func list(filter: FeatureID?) async -> [TaskSession]
    func task(id: UUID) async -> TaskSession?
    func delete(id: UUID) async throws
}

protocol ExportSharing: Sendable {
    func makeTranscriptFile(task: TaskSession, language: AppLanguage) throws -> URL
}

@MainActor
final class TaskSessionController {
    let feature: FeatureID
    private let store: any TaskStore
    private(set) var current: TaskSession?

    init(feature: FeatureID, store: any TaskStore) {
        self.feature = feature
        self.store = store
    }

    var hasActiveTask: Bool {
        guard let current else { return false }
        return current.status != .ended
    }

    var taskID: UUID? { current?.id }
    var startedAt: Date? { current?.startedAt }

    func restore() async -> TaskSession? {
        current = await store.activeTask(for: feature)
        return current
    }

    func beginNew(
        source: AppLanguage,
        target: AppLanguage?,
        multilingual: Bool = false
    ) async -> TaskSession? {
        do {
            let session = try await store.startNew(
                feature: feature,
                source: source,
                target: target,
                multilingual: multilingual
            )
            current = session
            return session
        } catch {
            return nil
        }
    }

    func persist(_ entries: [TranscriptEntry]) async {
        guard let id = current?.id else { return }
        await store.append(taskID: id, entries: entries)
    }

    func setListening(_ listening: Bool) async {
        guard let id = current?.id else { return }
        let status: TaskStatus = listening ? .running : .pausedListening
        await store.setStatus(taskID: id, status: status)
        current?.status = status
    }

    func saveSummary(_ summary: ConversationSummary) async {
        guard let id = current?.id else { return }
        await store.saveSummary(taskID: id, summary: summary)
        current?.summary = summary
    }

    func finish(entries: [TranscriptEntry], summary: ConversationSummary?) async -> TaskSession? {
        guard let id = current?.id else { return nil }
        await store.append(taskID: id, entries: entries)
        let usable = entries.contains {
            !$0.sourceText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        }
        if !usable {
            try? await store.delete(id: id)
            current = nil
            return nil
        }
        do {
            let saved = try await store.end(taskID: id, summary: summary)
            current = nil
            return saved
        } catch {
            return nil
        }
    }
}
