import Foundation

enum SpokenText {
    static func isContinuation(_ incoming: String, of previous: String, language: AppLanguage) -> Bool {
        let incomingText = normalized(incoming)
        let previousText = normalized(previous)
        guard !incomingText.isEmpty, !previousText.isEmpty else { return false }
        if incomingText == previousText { return true }
        if incomingText.hasPrefix(previousText) {
            return true
        }
        if previousText.hasPrefix(incomingText) {
            let minimum = max(
                minimumStemLength(for: language),
                Int((Double(previousText.count) * 0.55).rounded(.up))
            )
            return incomingText.count >= minimum
        }
        if incomingText.contains(previousText), previousText.count >= minimumStemLength(for: language) {
            return true
        }
        let shared = zip(incomingText, previousText).prefix { $0 == $1 }.count
        let shorter = min(incomingText.count, previousText.count)
        guard shorter > 0 else { return false }
        return shared >= minimumStemLength(for: language) && Double(shared) / Double(shorter) >= 0.55
    }

    static func preferredSource(_ current: String, _ incoming: String) -> String {
        if isNameSwap(incoming, of: current) {
            return joinDistinctUtterances(current, incoming)
        }
        return incoming.count >= current.count ? incoming : current
    }

    static func preferredTranslation(_ current: String, _ incoming: String) -> String {
        if incoming.isEmpty { return current }
        if current.isEmpty { return incoming }
        if isNameSwap(incoming, of: current) {
            return joinDistinctUtterances(current, incoming)
        }
        if covers(incoming, of: current) { return incoming }
        if covers(current, of: incoming) { return current }
        if isRefinement(incoming, of: current) {
            let incomingText = compact(incoming)
            let currentText = compact(current)
            if currentText.count > incomingText.count, isSubsequence(incomingText, of: currentText) {
                return current
            }
            return incoming
        }
        return incoming.count >= current.count ? incoming : current
    }

    /// Same sentence growing or being lightly revised, e.g. 《幸运》 → 《幸运的日子》.
    static func isRefinement(_ incoming: String, of previous: String) -> Bool {
        let incomingText = compact(incoming)
        let previousText = compact(previous)
        guard !incomingText.isEmpty, !previousText.isEmpty else { return false }
        if incomingText == previousText { return true }
        if incomingText.hasPrefix(previousText) {
            return true
        }
        if previousText.hasPrefix(incomingText) {
            return incomingText.count >= max(8, Int((Double(previousText.count) * 0.55).rounded(.up)))
        }
        if incomingText.contains(previousText), previousText.count >= 8 {
            return true
        }
        if previousText.contains(incomingText), incomingText.count >= max(8, Int((Double(previousText.count) * 0.55).rounded(.up))) {
            return true
        }
        let shorter = min(incomingText.count, previousText.count)
        let longer = max(incomingText.count, previousText.count)
        guard shorter >= 4 else { return false }
        let lcs = longestCommonSubsequenceCount(incomingText, previousText)
        if shorter >= 8, Double(lcs) / Double(shorter) >= 0.82 {
            return true
        }
        let shared = zip(incomingText, previousText).prefix { $0 == $1 }.count
        guard shared > 0 else { return false }
        let shorterRatio = Double(shared) / Double(shorter)
        let longerRatio = Double(shared) / Double(longer)
        guard shorterRatio >= 0.5 else { return false }
        if longerRatio >= 0.75 {
            return true
        }
        let previousTail = previousText.dropFirst(shared)
        let incomingTail = incomingText.dropFirst(shared)
        // "See you later Jack" vs "See you later Lucy" share a stem but swap a name.
        if previousTail.count >= 3, incomingTail.count >= 3 {
            return false
        }
        return true
    }

    static func covers(_ text: String, of other: String) -> Bool {
        let haystack = compact(text)
        let needle = compact(other)
        guard !needle.isEmpty else { return true }
        return haystack.contains(needle)
    }

    /// "嗨，Jack" vs "嗨，Lucy": same greeting, different person — not a revision of one sentence.
    static func isNameSwap(_ incoming: String, of previous: String) -> Bool {
        guard let previousParts = greetingNameParts(previous),
              let incomingParts = greetingNameParts(incoming)
        else {
            return false
        }
        guard previousParts.stem == incomingParts.stem else { return false }
        guard previousParts.name != incomingParts.name else { return false }
        if previousParts.name.hasPrefix(incomingParts.name) || incomingParts.name.hasPrefix(previousParts.name) {
            return false
        }
        return true
    }

    static func isDistinctGreeting(
        incomingSource: String,
        incomingDisplay: String,
        previousSource: String,
        previousDisplay: String
    ) -> Bool {
        if covers(incomingSource, of: previousSource) || covers(previousSource, of: incomingSource) {
            return false
        }
        if !incomingDisplay.isEmpty, !previousDisplay.isEmpty,
           covers(incomingDisplay, of: previousDisplay) || covers(previousDisplay, of: incomingDisplay) {
            return false
        }
        return isNameSwap(incomingSource, of: previousSource)
            || isNameSwap(incomingDisplay, of: previousDisplay)
    }

    static func joinDistinctUtterances(_ current: String, _ incoming: String) -> String {
        if covers(incoming, of: current) { return incoming }
        if covers(current, of: incoming) { return current }
        let head = current.trimmingCharacters(in: .whitespacesAndNewlines)
        let tail = incoming.trimmingCharacters(in: .whitespacesAndNewlines)
        if head.isEmpty { return tail }
        if tail.isEmpty { return head }
        if let last = head.last, "。.!！?？".contains(last) {
            return head + tail
        }
        return head + "。" + tail
    }

    static func isRewrite(_ current: String, incoming: String) -> Bool {
        guard !current.isEmpty, !incoming.isEmpty else { return false }
        return !covers(incoming, of: current) && !covers(current, of: incoming)
    }

    static func isShortRewrite(_ current: String, incoming: String) -> Bool {
        guard isRewrite(current, incoming: incoming) else { return false }
        return compact(incoming).count <= compact(current).count + 6
    }

    static func compact(_ text: String) -> String {
        text.lowercased().filter { $0.isLetter || $0.isNumber }
    }

    static func normalized(_ text: String) -> String {
        compact(text)
    }

    /// Only replace a scheduled reading when the new text is the same sentence growing or revised,
    /// never when a short follow-up would discard a longer sentence still waiting to be spoken.
    static func shouldReplaceScheduledSpeech(_ current: String, with incoming: String) -> Bool {
        if incoming.isEmpty { return false }
        if current.isEmpty { return true }
        if covers(incoming, of: current) { return true }
        if isRefinement(incoming, of: current), compact(incoming).count >= compact(current).count {
            return true
        }
        return false
    }

    static func containsCompact(_ haystack: String, clause: String) -> Bool {
        let needle = compact(clause)
        guard needle.count >= 2 else { return false }
        return compact(haystack).contains(needle)
    }

    private static func minimumStemLength(for language: AppLanguage) -> Int {
        language.usesLatinScript ? 16 : 6
    }

    private static let greetingStems = ["hello", "hey", "你好", "您好", "哈喽", "hi", "yo", "嗨"]

    private static func greetingNameParts(_ text: String) -> (stem: String, name: String)? {
        let compactText = compact(text)
        guard let stem = greetingStems.sorted(by: { $0.count > $1.count }).first(where: {
            compactText.hasPrefix($0)
        }) else {
            return nil
        }
        let name = String(compactText.dropFirst(stem.count))
        guard (2...14).contains(name.count) else { return nil }
        return (stem, name)
    }

    static func isSubsequence(_ needle: String, of haystack: String) -> Bool {
        guard !needle.isEmpty else { return true }
        var needleIndex = needle.startIndex
        for character in haystack {
            if character == needle[needleIndex] {
                needleIndex = needle.index(after: needleIndex)
                if needleIndex == needle.endIndex {
                    return true
                }
            }
        }
        return false
    }

    private static func longestCommonSubsequenceCount(_ left: String, _ right: String) -> Int {
        let first = Array(left)
        let second = Array(right)
        guard !first.isEmpty, !second.isEmpty else { return 0 }
        var previous = Array(repeating: 0, count: second.count + 1)
        for index in 1...first.count {
            var current = Array(repeating: 0, count: second.count + 1)
            for other in 1...second.count {
                if first[index - 1] == second[other - 1] {
                    current[other] = previous[other - 1] + 1
                } else {
                    current[other] = max(previous[other], current[other - 1])
                }
            }
            previous = current
        }
        return previous[second.count]
    }
}
