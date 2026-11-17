import Foundation
import Testing
@testable import Duiyi

@MainActor
struct TranscriptExportServiceTests {
    @Test("Preparing changed content preserves the earlier snapshot")
    func changedContentPreservesEarlierSnapshot() throws {
        let directory = try makeDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let exporter = TranscriptExportService(exportDirectory: directory, now: { now })
        let original = makeTask(translatedText: "Old translation")
        var changed = original
        changed.entries[0].translatedText = "New translation"

        let earlierURL = try exporter.makeTranscriptFile(task: original, language: .zhHans)
        let earlierBytes = try Data(contentsOf: earlierURL)
        let laterURL = try exporter.makeTranscriptFile(task: changed, language: .zhHans)

        #expect(earlierURL != laterURL)
        #expect(try Data(contentsOf: earlierURL) == earlierBytes)
        #expect(try String(contentsOf: laterURL, encoding: .utf8).contains("New translation"))
    }

    @Test("Same-minute tasks produce distinct snapshots")
    func sameMinuteTasksProduceDistinctSnapshots() throws {
        let directory = try makeDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let exporter = TranscriptExportService(exportDirectory: directory, now: { now })
        let startedAt = now.addingTimeInterval(-3_600)
        let first = makeTask(startedAt: startedAt, translatedText: "First")
        let second = makeTask(startedAt: startedAt, translatedText: "Second")

        let firstURL = try exporter.makeTranscriptFile(task: first, language: .zhHans)
        let firstBytes = try Data(contentsOf: firstURL)
        let secondURL = try exporter.makeTranscriptFile(task: second, language: .zhHans)

        #expect(firstURL != secondURL)
        #expect(try Data(contentsOf: firstURL) == firstBytes)
    }

    @Test("Fresh generated snapshots survive cleanup")
    func freshGeneratedSnapshotsSurviveCleanup() throws {
        let root = try makeDirectory()
        defer { try? FileManager.default.removeItem(at: root) }
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let snapshot = try makeUnprotectedSnapshot(
            in: root,
            now: now,
            modificationDate: now.addingTimeInterval(-3_600)
        )
        let originalBytes = try Data(contentsOf: snapshot.url)

        _ = try TranscriptExportService(exportDirectory: snapshot.directory, now: { now })
            .makeTranscriptFile(task: makeTask(translatedText: "Later"), language: .zhHans)

        #expect(try Data(contentsOf: snapshot.url) == originalBytes)
    }

    @Test("Expired unprotected generated snapshots are removed")
    func expiredGeneratedSnapshotsAreRemoved() throws {
        let root = try makeDirectory()
        defer { try? FileManager.default.removeItem(at: root) }
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let snapshot = try makeUnprotectedSnapshot(
            in: root,
            now: now,
            modificationDate: now.addingTimeInterval(-(7 * 24 * 3_600 + 1))
        )

        _ = try TranscriptExportService(exportDirectory: snapshot.directory, now: { now })
            .makeTranscriptFile(task: makeTask(translatedText: "Later"), language: .zhHans)

        #expect(!FileManager.default.fileExists(atPath: snapshot.url.path))
    }

    @Test("Snapshots exactly seven days old survive cleanup")
    func snapshotsAtRetentionBoundarySurviveCleanup() throws {
        let root = try makeDirectory()
        defer { try? FileManager.default.removeItem(at: root) }
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let snapshot = try makeUnprotectedSnapshot(
            in: root,
            now: now,
            modificationDate: now.addingTimeInterval(-7 * 24 * 3_600)
        )
        let originalBytes = try Data(contentsOf: snapshot.url)

        _ = try TranscriptExportService(exportDirectory: snapshot.directory, now: { now })
            .makeTranscriptFile(task: makeTask(translatedText: "Later"), language: .zhHans)

        #expect(try Data(contentsOf: snapshot.url) == originalBytes)
    }

    @Test("Future-dated snapshots survive cleanup")
    func futureDatedSnapshotsSurviveCleanup() throws {
        let root = try makeDirectory()
        defer { try? FileManager.default.removeItem(at: root) }
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let snapshot = try makeUnprotectedSnapshot(
            in: root,
            now: now,
            modificationDate: now.addingTimeInterval(3_600)
        )
        let originalBytes = try Data(contentsOf: snapshot.url)

        _ = try TranscriptExportService(exportDirectory: snapshot.directory, now: { now })
            .makeTranscriptFile(task: makeTask(translatedText: "Later"), language: .zhHans)

        #expect(try Data(contentsOf: snapshot.url) == originalBytes)
    }

    @Test("Cleanup preserves unrelated files directories and broken links")
    func cleanupPreservesNonSnapshotEntries() throws {
        let directory = try makeDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let notes = directory.appendingPathComponent("Duiyi-notes.txt")
        try Data("keep".utf8).write(to: notes)
        let folder = directory.appendingPathComponent("Duiyi-folder.txt", isDirectory: true)
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: false)
        let nested = folder.appendingPathComponent("nested.txt")
        try Data("keep".utf8).write(to: nested)
        let brokenLink = directory.appendingPathComponent("Duiyi-broken.txt")
        try FileManager.default.createSymbolicLink(
            at: brokenLink,
            withDestinationURL: directory.appendingPathComponent("missing.txt")
        )
        for url in [notes, folder] {
            try FileManager.default.setAttributes(
                [.modificationDate: now.addingTimeInterval(-30 * 24 * 3_600)],
                ofItemAtPath: url.path
            )
        }

        _ = try TranscriptExportService(exportDirectory: directory, now: { now })
            .makeTranscriptFile(task: makeTask(), language: .zhHans)

        #expect(FileManager.default.fileExists(atPath: notes.path))
        #expect(FileManager.default.fileExists(atPath: nested.path))
        #expect((try? FileManager.default.destinationOfSymbolicLink(atPath: brokenLink.path)) != nil)
    }

    @Test("Expired snapshots prepared in this process remain protected")
    func expiredPreparedSnapshotsRemainProtected() throws {
        let directory = try makeDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let firstExporter = TranscriptExportService(exportDirectory: directory, now: { now })
        let snapshotURL = try firstExporter.makeTranscriptFile(task: makeTask(), language: .zhHans)
        let originalBytes = try Data(contentsOf: snapshotURL)
        try FileManager.default.setAttributes(
            [.modificationDate: now.addingTimeInterval(-30 * 24 * 3_600)],
            ofItemAtPath: snapshotURL.path
        )

        let secondExporter = TranscriptExportService(exportDirectory: directory, now: { now })
        _ = try secondExporter.makeTranscriptFile(task: makeTask(translatedText: "Later"), language: .zhHans)

        #expect(try Data(contentsOf: snapshotURL) == originalBytes)
    }

    private func makeUnprotectedSnapshot(
        in root: URL,
        now: Date,
        modificationDate: Date
    ) throws -> (directory: URL, url: URL) {
        let source = root.appendingPathComponent("source", isDirectory: true)
        let cleanup = root.appendingPathComponent("cleanup", isDirectory: true)
        try FileManager.default.createDirectory(at: source, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: cleanup, withIntermediateDirectories: true)
        let sourceURL = try TranscriptExportService(exportDirectory: source, now: { now })
            .makeTranscriptFile(task: makeTask(), language: .zhHans)
        let snapshotURL = cleanup.appendingPathComponent(sourceURL.lastPathComponent)
        try FileManager.default.copyItem(at: sourceURL, to: snapshotURL)
        try FileManager.default.setAttributes(
            [.modificationDate: modificationDate],
            ofItemAtPath: snapshotURL.path
        )
        return (cleanup, snapshotURL)
    }

    private func makeDirectory() throws -> URL {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("TranscriptExportServiceTests-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        return url
    }

    private func makeTask(
        id: UUID = UUID(),
        startedAt: Date = Date(timeIntervalSince1970: 1_800_000_000),
        translatedText: String = "六点见"
    ) -> TaskSession {
        TaskSession(
            id: id,
            feature: .simultaneous,
            status: .ended,
            startedAt: startedAt,
            endedAt: startedAt.addingTimeInterval(60),
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
                    translatedText: translatedText,
                    isFinal: true
                )
            ],
            summary: nil
        )
    }
}
