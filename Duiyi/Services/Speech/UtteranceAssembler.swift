import Foundation

struct UtteranceAssembler: Equatable, Sendable {
    var lastLanguage: AppLanguage?
    private var utteranceID = UUID()
    private var texts: [AppLanguage: String] = [:]
    private var finals: [AppLanguage: Bool] = [:]
    private var lockedLanguage: AppLanguage?
    private var suppressOtherUntil = Date.distantPast

    mutating func ingest(language: AppLanguage, text: String, isFinal: Bool) -> Utterance? {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        guard Self.matchesClaimedLanguage(trimmed, claimed: language) else { return nil }

        if Date() < suppressOtherUntil, let held = lastLanguage, language != held {
            return nil
        }
        if Date() >= suppressOtherUntil, lockedLanguage != nil, texts.values.allSatisfy(\.isEmpty) {
            lockedLanguage = nil
        }

        if let locked = lockedLanguage, language != locked {
            let incumbent = textFor(locked)
            guard Self.shouldPreempt(
                challenger: trimmed,
                challengerLanguage: language,
                incumbent: incumbent,
                incumbentLanguage: locked
            ) else {
                return nil
            }
            clearText(for: locked)
            lockedLanguage = language
        }

        if let locked = lockedLanguage, language == locked {
            let previous = textFor(locked)
            if !previous.isEmpty,
               isWinnerFinal(locked),
               SpokenText.isNameSwap(trimmed, of: previous)
                || (
                    !SpokenText.isContinuation(trimmed, of: previous, language: language)
                    && !SpokenText.isRefinement(trimmed, of: previous)
                ) {
                beginNextUtterance(keeping: locked)
                lockedLanguage = language
            }
        }

        texts[language] = trimmed
        finals[language] = isFinal

        if lockedLanguage == nil {
            lockedLanguage = inferredLock()
        }

        guard let winner = lockedLanguage ?? winningLanguage() else { return nil }
        let winnerText = textFor(winner)
        guard !winnerText.isEmpty else { return nil }

        return Utterance(
            id: utteranceID,
            language: winner,
            text: winnerText,
            isFinal: isWinnerFinal(winner)
        )
    }

    mutating func silenceTimedOut() -> Utterance? {
        guard let winner = lockedLanguage ?? winningLanguage() else { return nil }
        let winnerText = textFor(winner)
        guard !winnerText.isEmpty else { return nil }
        let utterance = Utterance(
            id: utteranceID,
            language: winner,
            text: winnerText,
            isFinal: true
        )
        beginNextUtterance(keeping: winner)
        hold(winner, for: 0.8)
        return utterance
    }

    mutating func acknowledgeFinal(language: AppLanguage) {
        hold(language, for: 1.0)
    }

    mutating func finalizeCurrentIfNeeded() -> Utterance? {
        silenceTimedOut()
    }

    mutating func reset() {
        lastLanguage = nil
        lockedLanguage = nil
        suppressOtherUntil = .distantPast
        beginNextUtterance(keeping: nil)
    }

    private mutating func hold(_ language: AppLanguage, for seconds: TimeInterval) {
        lockedLanguage = language
        lastLanguage = language
        suppressOtherUntil = Date().addingTimeInterval(seconds)
    }

    private mutating func beginNextUtterance(keeping language: AppLanguage?) {
        if let language {
            lastLanguage = language
        }
        utteranceID = UUID()
        texts = [:]
        finals = [:]
        lockedLanguage = nil
    }

    private mutating func clearText(for language: AppLanguage) {
        texts[language] = ""
        finals[language] = false
    }

    private func textFor(_ language: AppLanguage) -> String {
        texts[language] ?? ""
    }

    private func isWinnerFinal(_ language: AppLanguage) -> Bool {
        finals[language] ?? false
    }

    func winningLanguage() -> AppLanguage? {
        if let lockedLanguage {
            return lockedLanguage
        }
        return inferredLock() ?? weakerGuess()
    }

    private func inferredLock() -> AppLanguage? {
        Self.lock(texts: texts, lastLanguage: lastLanguage)
    }

    private func weakerGuess() -> AppLanguage? {
        let present = texts.compactMap { language, text -> (AppLanguage, String)? in
            text.isEmpty ? nil : (language, text)
        }
        if present.isEmpty {
            return lastLanguage
        }
        if present.count == 1 {
            return present[0].0
        }
        return lastLanguage
    }

    static func lock(
        chinese: String,
        english: String,
        lastLanguage: AppLanguage?
    ) -> AppLanguage? {
        lock(texts: [.zhHans: chinese, .english: english], lastLanguage: lastLanguage)
    }

    static func lock(
        texts: [AppLanguage: String],
        lastLanguage: AppLanguage?
    ) -> AppLanguage? {
        let confident = AppLanguage.allCases.filter { language in
            isConfident(texts[language] ?? "", language: language)
        }
        if confident.count == 1 {
            return confident[0]
        }
        if confident.count > 1 {
            return confident.max { lhs, rhs in
                score(texts[lhs] ?? "", as: lhs) < score(texts[rhs] ?? "", as: rhs)
            } ?? lastLanguage
        }
        return nil
    }

    static func shouldPreempt(
        challenger: String,
        challengerLanguage: AppLanguage,
        incumbent: String,
        incumbentLanguage: AppLanguage
    ) -> Bool {
        guard isConfident(challenger, language: challengerLanguage) else { return false }
        return !isConfident(incumbent, language: incumbentLanguage)
    }

    static func isConfident(_ text: String, language: AppLanguage) -> Bool {
        switch language {
        case .zhHans:
            return hanCount(text) >= 4
        case .english:
            return wordCount(text) >= 3 && letterCount(text) >= 10 && vietnameseMarkCount(text) < 2
        case .japanese:
            return kanaCount(text) >= 2 || (kanaCount(text) >= 1 && hanCount(text) >= 2)
        case .korean:
            return hangulCount(text) >= 4
        case .thai:
            return thaiCount(text) >= 4
        case .vietnamese:
            return wordCount(text) >= 2 && (vietnameseMarkCount(text) >= 1 || letterCount(text) >= 10)
        }
    }

    /// Drop results that do not look like the transcriber's language at all.
    static func matchesClaimedLanguage(_ text: String, claimed: AppLanguage) -> Bool {
        let han = hanCount(text)
        let latin = letterCount(text)
        let kana = kanaCount(text)
        let hangul = hangulCount(text)
        let thai = thaiCount(text)
        let viet = vietnameseMarkCount(text)
        switch claimed {
        case .zhHans:
            return han >= 1 && kana == 0 && hangul == 0 && thai == 0 && han >= latin
        case .english:
            return latin >= 2 && han == 0 && kana == 0 && hangul == 0 && thai == 0 && viet < 2
        case .japanese:
            return kana >= 1 || (han >= 1 && kana >= 1)
        case .korean:
            return hangul >= 1
        case .thai:
            return thai >= 1
        case .vietnamese:
            return (viet >= 1 || latin >= 2) && han == 0 && kana == 0 && hangul == 0 && thai == 0
        }
    }

    static func hanCount(_ text: String) -> Int {
        text.unicodeScalars.filter(isHanScalar).count
    }

    static func kanaCount(_ text: String) -> Int {
        text.unicodeScalars.filter(isKanaScalar).count
    }

    static func hangulCount(_ text: String) -> Int {
        text.unicodeScalars.filter(isHangulScalar).count
    }

    static func thaiCount(_ text: String) -> Int {
        text.unicodeScalars.filter(isThaiScalar).count
    }

    static func vietnameseMarkCount(_ text: String) -> Int {
        text.unicodeScalars.filter(isVietnameseMarkScalar).count
    }

    static func letterCount(_ text: String) -> Int {
        text.unicodeScalars.filter(isLatinScalar).count
    }

    static func wordCount(_ text: String) -> Int {
        text.split(whereSeparator: \.isWhitespace).count
    }

    static func isHanScalar(_ scalar: UnicodeScalar) -> Bool {
        (0x4E00...0x9FFF).contains(scalar.value) || (0x3400...0x4DBF).contains(scalar.value)
    }

    static func isKanaScalar(_ scalar: UnicodeScalar) -> Bool {
        switch scalar.value {
        case 0x3040...0x309F, 0x30A0...0x30FF, 0x31F0...0x31FF, 0xFF66...0xFF9D:
            return true
        default:
            return false
        }
    }

    static func isHangulScalar(_ scalar: UnicodeScalar) -> Bool {
        switch scalar.value {
        case 0xAC00...0xD7AF, 0x1100...0x11FF, 0x3130...0x318F:
            return true
        default:
            return false
        }
    }

    static func isThaiScalar(_ scalar: UnicodeScalar) -> Bool {
        (0x0E00...0x0E7F).contains(scalar.value)
    }

    static func isVietnameseMarkScalar(_ scalar: UnicodeScalar) -> Bool {
        switch scalar.value {
        case 0x00C0...0x00C3, 0x00C8...0x00CA, 0x00CC, 0x00CD, 0x00D2...0x00D5, 0x00D9, 0x00DA, 0x00DD,
             0x00E0...0x00E3, 0x00E8...0x00EA, 0x00EC, 0x00ED, 0x00F2...0x00F5, 0x00F9, 0x00FA, 0x00FD,
             0x0102, 0x0103, 0x0110, 0x0111, 0x0128, 0x0129, 0x0168, 0x0169,
             0x01A0, 0x01A1, 0x01AF, 0x01B0,
             0x1EA0...0x1EF9:
            return true
        default:
            return false
        }
    }

    static func isLatinScalar(_ scalar: UnicodeScalar) -> Bool {
        switch scalar.value {
        case 0x0041...0x005A, 0x0061...0x007A,
             0x00C0...0x00D6, 0x00D8...0x00F6, 0x00F8...0x00FF,
             0x0100...0x024F,
             0x1E00...0x1EFF:
            return true
        default:
            return false
        }
    }

    static func score(_ text: String, as language: AppLanguage) -> Double {
        switch language {
        case .zhHans:
            return Double(hanCount(text))
        case .english:
            return Double(letterCount(text))
        case .japanese:
            return Double(kanaCount(text) * 2 + hanCount(text))
        case .korean:
            return Double(hangulCount(text))
        case .thai:
            return Double(thaiCount(text))
        case .vietnamese:
            return Double(vietnameseMarkCount(text) * 3 + letterCount(text))
        }
    }

    static func isShort(_ text: String, language: AppLanguage) -> Bool {
        !isConfident(text, language: language)
    }
}
