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
        } else {
            archiveLive()
            live = line
        }
        absorbRefinementHistory()
    }

    @discardableResult
    mutating func applyTranslation(utteranceID: UUID, text: String, settle: Bool) -> Bool {
        if live?.id == utteranceID {
            applyTranslationText(toLive: text, settle: settle)
            absorbRefinementHistory()
            return true
        }
        guard let index = history.firstIndex(where: { $0.id == utteranceID }) else { return false }
        applyTranslationText(toHistory: index, text: text, settle: settle)
        absorbRefinementHistory()
        return true
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

    mutating func trimHistory(to maxCount: Int) {
        guard history.count > maxCount else { return }
        history.removeFirst(history.count - maxCount)
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

    private mutating func applyTranslationText(toLive text: String, settle: Bool) {
        guard var current = live else { return }
        current.translatedText = SpokenText.preferredTranslation(current.translatedText, text)
        if settle {
            current.phase = .settled
        }
        live = current
    }

    private mutating func applyTranslationText(toHistory index: Int, text: String, settle: Bool) {
        history[index].translatedText = SpokenText.preferredTranslation(history[index].translatedText, text)
        if settle {
            history[index].phase = .settled
        }
    }

    private mutating func absorbRefinementHistory() {
        guard var current = live else { return }
        while let last = history.last, shouldCollapse(last, into: current) {
            current.sourceText = SpokenText.preferredSource(last.sourceText, current.sourceText)
            current.translatedText = SpokenText.preferredTranslation(
                last.translatedText,
                current.translatedText
            )
            if last.phase == .settled, current.phase != .settled {
                current.phase = .settled
            }
            current.updatedAt = max(last.updatedAt, current.updatedAt)
            history.removeLast()
        }
        live = current
    }

    private func shouldMerge(_ line: CaptionLine, into existing: CaptionLine?) -> Bool {
        guard let existing, existing.source == line.source, existing.side == line.side else {
            return false
        }
        return SpokenText.isContinuation(line.sourceText, of: existing.sourceText, language: line.source)
            || SpokenText.isRefinement(line.displayText, of: existing.displayText)
            || SpokenText.isRefinement(line.sourceText, of: existing.sourceText)
    }

    private func shouldCollapse(_ older: CaptionLine, into newer: CaptionLine) -> Bool {
        guard older.source == newer.source, older.side == newer.side else {
            return false
        }
        return shouldMerge(newer, into: older)
            || SpokenText.isRefinement(newer.displayText, of: older.displayText)
            || SpokenText.isRefinement(newer.sourceText, of: older.sourceText)
    }
}
