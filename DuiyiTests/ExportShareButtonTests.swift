import Foundation
import SwiftUI
import Testing
import UIKit
@testable import Duiyi

@MainActor
struct ExportShareButtonTests {
    @Test("Translation changes prepare a new share snapshot for the same task")
    func translationChangesPrepareNewSnapshot() async {
        let fixture = makeFixture()
        defer { fixture.window.isHidden = true }
        await waitForCallCount(1, exporter: fixture.exporter)
        var changed = fixture.task
        changed.entries[0].translatedText = "Updated translation"

        fixture.host.rootView = makeButton(task: changed, language: .zhHans, exporter: fixture.exporter)

        await waitForCallCount(2, exporter: fixture.exporter)
        #expect(fixture.exporter.callCount == 2)
    }

    @Test("Summary changes prepare a new share snapshot for the same task")
    func summaryChangesPrepareNewSnapshot() async {
        let fixture = makeFixture()
        defer { fixture.window.isHidden = true }
        await waitForCallCount(1, exporter: fixture.exporter)
        var changed = fixture.task
        changed.summary = ConversationSummary(text: "New summary", usedAppleIntelligence: false)

        fixture.host.rootView = makeButton(task: changed, language: .zhHans, exporter: fixture.exporter)

        await waitForCallCount(2, exporter: fixture.exporter)
        #expect(fixture.exporter.callCount == 2)
    }

    @Test("Language changes prepare a new share snapshot for the same task")
    func languageChangesPrepareNewSnapshot() async {
        let fixture = makeFixture()
        defer { fixture.window.isHidden = true }
        await waitForCallCount(1, exporter: fixture.exporter)

        fixture.host.rootView = makeButton(task: fixture.task, language: .english, exporter: fixture.exporter)

        await waitForCallCount(2, exporter: fixture.exporter)
        #expect(fixture.exporter.callCount == 2)
    }

    private func makeFixture() -> (
        window: UIWindow,
        host: UIHostingController<ExportShareButton>,
        exporter: RecordingExporter,
        task: TaskSession
    ) {
        let task = makeTask()
        let exporter = RecordingExporter()
        let host = UIHostingController(rootView: makeButton(task: task, language: .zhHans, exporter: exporter))
        let window = UIWindow(frame: CGRect(x: 0, y: 0, width: 390, height: 844))
        window.rootViewController = host
        window.makeKeyAndVisible()
        host.loadViewIfNeeded()
        return (window, host, exporter, task)
    }

    private func makeButton(
        task: TaskSession,
        language: AppLanguage,
        exporter: RecordingExporter
    ) -> ExportShareButton {
        ExportShareButton(task: task, language: language, exporter: exporter)
    }

    private func waitForCallCount(_ expected: Int, exporter: RecordingExporter) async {
        for _ in 0..<50 {
            if exporter.callCount >= expected { return }
            await Task.yield()
        }
    }

    private func makeTask() -> TaskSession {
        TaskSession(
            id: UUID(),
            feature: .simultaneous,
            status: .ended,
            startedAt: Date(timeIntervalSince1970: 1_800_000_000),
            endedAt: Date(timeIntervalSince1970: 1_800_000_060),
            title: "同声传译",
            subtitle: nil,
            sourceLanguage: .english,
            targetLanguage: .zhHans,
            entries: [
                TranscriptEntry(
                    id: UUID(),
                    speaker: .peer,
                    source: .english,
                    sourceText: "See you at six",
                    translatedText: "六点见",
                    isFinal: true
                )
            ],
            summary: nil
        )
    }
}

private final class RecordingExporter: ExportSharing, @unchecked Sendable {
    private let lock = NSLock()
    private var count = 0

    var callCount: Int {
        lock.lock()
        defer { lock.unlock() }
        return count
    }

    func makeTranscriptFile(task: TaskSession, language: AppLanguage) throws -> URL {
        lock.lock()
        count += 1
        let invocation = count
        lock.unlock()
        return FileManager.default.temporaryDirectory.appendingPathComponent("recording-\(invocation).txt")
    }
}
