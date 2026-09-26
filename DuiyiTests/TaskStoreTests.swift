import Foundation
import SwiftData
import Testing
@testable import Duiyi

@MainActor
struct TaskStoreTests {
    @Test("Ending a task with captions writes history")
    func endWritesHistory() async throws {
        let store = InMemoryTaskStore()
        let session = try await store.startNew(feature: .simultaneous, source: .english, target: .zhHans, multilingual: false)
        await store.append(
            taskID: session.id,
            entries: [
                TranscriptEntry(
                    id: UUID(),
                    speaker: .peer,
                    source: .english,
                    sourceText: "See you at six",
                    translatedText: "六点见",
                    isFinal: true
                )
            ]
        )
        let saved = try await store.end(taskID: session.id, summary: nil)
        #expect(saved.status == .ended)
        let listed = await store.list(filter: .simultaneous)
        #expect(listed.count == 1)
        #expect(listed.first?.entries.first?.translatedText == "六点见")
    }

    @Test("Deleting one task leaves the other")
    func deleteDoesNotAffectOther() async throws {
        let store = InMemoryTaskStore()
        let first = try await store.startNew(feature: .faceToFace, source: .zhHans, target: .english, multilingual: false)
        await store.append(
            taskID: first.id,
            entries: [
                TranscriptEntry(
                    id: UUID(),
                    speaker: .user,
                    source: .zhHans,
                    sourceText: "好的",
                    translatedText: "Okay",
                    isFinal: true
                )
            ]
        )
        _ = try await store.end(taskID: first.id, summary: nil)
        let second = try await store.startNew(feature: .meeting, source: .zhHans, target: nil, multilingual: true)
        await store.append(
            taskID: second.id,
            entries: [
                TranscriptEntry(
                    id: UUID(),
                    speaker: .user,
                    source: .zhHans,
                    sourceText: "预算确认一下",
                    translatedText: "",
                    isFinal: true
                )
            ]
        )
        _ = try await store.end(taskID: second.id, summary: nil)
        try await store.delete(id: first.id)
        let remaining = await store.list(filter: nil)
        #expect(remaining.count == 1)
        #expect(remaining.first?.id == second.id)
    }

    @Test("Unfinished tasks survive as running")
    func unfinishedStayActive() async throws {
        let store = InMemoryTaskStore()
        let session = try await store.startNew(feature: .faceToFace, source: .zhHans, target: .english, multilingual: false)
        let active = await store.activeTask(for: .faceToFace)
        #expect(active?.id == session.id)
        #expect(active?.status == .running)
        let unfinished = await store.unfinishedTasks()
        #expect(unfinished.count == 1)
    }

    @Test("Ended task translation backfill survives reload in memory")
    func endedTaskTranslationBackfillInMemory() async throws {
        try await assertEndedTranslationBackfill(InMemoryTaskStore())
    }

    @Test("Ended task translation backfill survives reload in SwiftData")
    func endedTaskTranslationBackfillInSwiftData() async throws {
        let schema = Schema([TaskEntity.self, TranscriptEntity.self])
        let configuration = ModelConfiguration(schema: schema, isStoredInMemoryOnly: true)
        let container = try ModelContainer(for: schema, configurations: [configuration])
        try await assertEndedTranslationBackfill(SwiftDataTaskStore(container: container))
    }

    private func assertEndedTranslationBackfill(_ store: any TaskStore) async throws {
        let session = try await store.startNew(
            feature: .simultaneous,
            source: .english,
            target: .zhHans,
            multilingual: false
        )
        let entry = TranscriptEntry(
            id: UUID(),
            speaker: .peer,
            source: .english,
            sourceText: "See you at six",
            translatedText: "",
            isFinal: true
        )
        await store.append(taskID: session.id, entries: [entry])
        _ = try await store.end(taskID: session.id, summary: nil)

        var ignoredMutation = entry
        ignoredMutation.sourceText = "must not mutate ended transcript"
        await store.append(taskID: session.id, entries: [ignoredMutation])
        let afterAppend = await store.task(id: session.id)
        #expect(afterAppend?.entries.first?.sourceText == "See you at six")

        var translated = entry
        translated.translatedText = "六点见"
        await store.updateTranslations(taskID: session.id, entries: [translated])

        let reloaded = await store.task(id: session.id)
        #expect(reloaded?.entries.first?.translatedText == "六点见")
    }

}
