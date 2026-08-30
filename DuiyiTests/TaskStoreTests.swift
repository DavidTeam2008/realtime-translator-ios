import Foundation
import Testing
@testable import Duiyi

@MainActor
struct TaskStoreTests {
    @Test("Ending a task with captions writes history")
    func endWritesHistory() async throws {
        let store = InMemoryTaskStore()
        let session = try await store.startNew(feature: .simultaneous, source: .english, target: .zhHans)
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
        let first = try await store.startNew(feature: .faceToFace, source: .zhHans, target: .english)
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
        let second = try await store.startNew(feature: .meeting, source: .zhHans, target: nil)
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
        let session = try await store.startNew(feature: .faceToFace, source: .zhHans, target: .english)
        let active = await store.activeTask(for: .faceToFace)
        #expect(active?.id == session.id)
        #expect(active?.status == .running)
        let unfinished = await store.unfinishedTasks()
        #expect(unfinished.count == 1)
    }
}
