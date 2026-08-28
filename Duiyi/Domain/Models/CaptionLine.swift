import Foundation

struct CaptionLine: Identifiable, Equatable, Sendable {
    enum Phase: String, Equatable, Sendable {
        case streaming
        case settled
    }

    var id: UUID
    var side: SpeakerSide
    var source: AppLanguage
    var sourceText: String
    var translatedText: String
    var phase: Phase
    var updatedAt: Date

    init(
        id: UUID = UUID(),
        side: SpeakerSide,
        source: AppLanguage,
        sourceText: String,
        translatedText: String = "",
        phase: Phase = .streaming,
        updatedAt: Date = .now
    ) {
        self.id = id
        self.side = side
        self.source = source
        self.sourceText = sourceText
        self.translatedText = translatedText
        self.phase = phase
        self.updatedAt = updatedAt
    }

    var displayText: String {
        translatedText.isEmpty ? sourceText : translatedText
    }

    func visibleText(forViewer language: AppLanguage) -> String {
        if !translatedText.isEmpty {
            return translatedText
        }
        if source == language {
            return sourceText
        }
        return "…"
    }
}

struct PaneState: Equatable, Sendable {
    var history: [CaptionLine] = []
    var live: CaptionLine?
    var speakingHint: String?

    static let empty = PaneState()

    mutating func applyLive(_ line: CaptionLine) {
        if live?.id == line.id || shouldMerge(line, into: live) {
            mergeLive(line)
            if let live {
                dropPrefixHistory(of: live)
            }
            return
        }
        dropPrefixHistory(of: line)
        archiveLive()
        live = line
        dropPrefixHistory(of: line)
    }

    mutating func applyTranslation(utteranceID: UUID, text: String, settle: Bool) {
        if live?.id == utteranceID {
            live?.translatedText = text
            if settle {
                live?.phase = .settled
            }
            return
        }
        guard let index = history.firstIndex(where: { $0.id == utteranceID }) else { return }
        history[index].translatedText = text
        if settle {
            history[index].phase = .settled
        }
    }

    mutating func archiveLive() {
        guard let current = live, !current.sourceText.isEmpty else { return }
        var archived = current
        if archived.phase != .settled {
            archived.phase = .settled
        }
        if history.last?.id == archived.id {
            history[history.count - 1] = archived
        } else {
            history.append(archived)
        }
        live = nil
    }

    mutating func resetCaptions() {
        history = []
        live = nil
        speakingHint = nil
    }

    private mutating func mergeLive(_ line: CaptionLine) {
        guard var current = live else {
            live = line
            return
        }
        current.sourceText = SpokenText.preferredSource(current.sourceText, line.sourceText)
        if !line.translatedText.isEmpty {
            current.translatedText = SpokenText.preferredTranslation(
                current.translatedText,
                line.translatedText
            )
        }
        current.phase = line.phase
        current.updatedAt = line.updatedAt
        current.source = line.source
        current.side = line.side
        live = current
    }

    private mutating func dropPrefixHistory(of line: CaptionLine) {
        while let last = history.last, shouldMerge(line, into: last) {
            history.removeLast()
        }
    }

    private func shouldMerge(_ line: CaptionLine, into existing: CaptionLine?) -> Bool {
        guard let existing, existing.source == line.source, existing.side == line.side else {
            return false
        }
        return SpokenText.isContinuation(line.sourceText, of: existing.sourceText, language: line.source)
    }
}
