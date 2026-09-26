import Foundation
import SwiftData

/// Defers SwiftData `ModelContainer` creation off the launch critical path.
///
/// `AppEnvironment.init` runs synchronously on the main thread during first-frame
/// construction. Opening the SQLite store there (file I/O, migration checks,
/// model introspection) directly delays `HomeView` paint. This wrapper starts
/// with zero I/O and resolves the real store on first actual use — which happens
/// after the first frame (`HomeView.task`, `HistoryViewModel.reload`, restores).
///
/// A background warm is kicked off at init so the store is usually ready by the
/// time the user navigates, without blocking the first frame.
@MainActor
final class DeferredTaskStore: TaskStore {
    private var real: (any TaskStore)?
    private var containerTask: Task<ModelContainer?, Never>?

    init(warmImmediately: Bool = true) {
        if warmImmediately {
            containerTask = Task.detached(priority: .utility) {
                Self.openContainer()
            }
        }
    }

    /// Explicit warm hook for post-first-frame preheating.
    func warm() async {
        _ = await resolved()
    }

    // MARK: - TaskStore (all delegate after lazy resolve)

    func activeTask(for feature: FeatureID) async -> TaskSession? {
        await resolved().activeTask(for: feature)
    }

    func unfinishedTasks() async -> [TaskSession] {
        await resolved().unfinishedTasks()
    }

    func startNew(
        feature: FeatureID,
        source: AppLanguage,
        target: AppLanguage?,
        multilingual: Bool
    ) async throws -> TaskSession {
        let store = await resolved()
        return try await store.startNew(feature: feature, source: source, target: target, multilingual: multilingual)
    }

    func append(taskID: UUID, entries: [TranscriptEntry]) async {
        await resolved().append(taskID: taskID, entries: entries)
    }

    func updateTranslations(taskID: UUID, entries: [TranscriptEntry]) async {
        await resolved().updateTranslations(taskID: taskID, entries: entries)
    }

    func setStatus(taskID: UUID, status: TaskStatus) async {
        await resolved().setStatus(taskID: taskID, status: status)
    }

    func saveSummary(taskID: UUID, summary: ConversationSummary) async {
        await resolved().saveSummary(taskID: taskID, summary: summary)
    }

    func end(taskID: UUID, summary: ConversationSummary?) async throws -> TaskSession {
        let store = await resolved()
        return try await store.end(taskID: taskID, summary: summary)
    }

    func list(filter: FeatureID?) async -> [TaskSession] {
        await resolved().list(filter: filter)
    }

    func task(id: UUID) async -> TaskSession? {
        await resolved().task(id: id)
    }

    func delete(id: UUID) async throws {
        let store = await resolved()
        try await store.delete(id: id)
    }

    // MARK: - Private

    private func resolved() async -> any TaskStore {
        if let real { return real }
        let container: ModelContainer?
        if let containerTask {
            container = await containerTask.value
            self.containerTask = nil
        } else {
            container = await Task.detached(priority: .utility) {
                Self.openContainer()
            }.value
        }
        AppLaunchTracker.shared.begin(.storeReady)
        if let container {
            let store = SwiftDataTaskStore(container: container)
            real = store
            return store
        }
        DuiyiLog.session.error("SwiftData store unavailable, using memory")
        let fallback = InMemoryTaskStore()
        real = fallback
        return fallback
    }

    /// Blocking file I/O: runs on a detached background task, never on MainActor.
    private nonisolated static func openContainer() -> ModelContainer? {
        do {
            let schema = Schema([TaskEntity.self, TranscriptEntity.self])
            let configuration = ModelConfiguration(schema: schema, isStoredInMemoryOnly: false)
            let t0 = CFAbsoluteTimeGetCurrent()
            let container = try ModelContainer(for: schema, configurations: [configuration])
            let dt = (CFAbsoluteTimeGetCurrent() - t0) * 1000
            DuiyiLog.session.info("STORE open took \(Int(dt), privacy: .public)ms (background task)")
            return container
        } catch {
            return nil
        }
    }
}
