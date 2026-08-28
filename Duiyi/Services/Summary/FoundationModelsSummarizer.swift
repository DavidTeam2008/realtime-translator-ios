import FoundationModels
import Foundation

struct FoundationModelsSummarizer: ConversationSummarizing {
    func availability() async -> SummaryAvailability {
        switch SystemLanguageModel.default.availability {
        case .available:
            return .available
        case .unavailable(.deviceNotEligible):
            return .deviceNotEligible
        case .unavailable(.appleIntelligenceNotEnabled):
            return .appleIntelligenceOff
        case .unavailable(.modelNotReady):
            return .modelNotReady
        default:
            return .unavailable
        }
    }

    func summarize(
        entries: [TranscriptEntry],
        outputLanguage: AppLanguage
    ) async throws -> ConversationSummary {
        let usable = entries.filter { !$0.sourceText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        guard !usable.isEmpty else {
            throw DuiyiError.summaryEmpty
        }

        if await availability() == .available {
            do {
                let text = try await generateWithFoundationModels(entries: usable, outputLanguage: outputLanguage)
                let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
                if !trimmed.isEmpty {
                    return ConversationSummary(text: trimmed, usedAppleIntelligence: true)
                }
            } catch {
                DuiyiLog.summary.error("Foundation Models summary failed: \(error.localizedDescription, privacy: .public)")
            }
        }

        return ConversationSummary(
            text: Self.digest(entries: usable, outputLanguage: outputLanguage),
            usedAppleIntelligence: false
        )
    }

    private func generateWithFoundationModels(
        entries: [TranscriptEntry],
        outputLanguage: AppLanguage
    ) async throws -> String {
        let session = LanguageModelSession(instructions: Self.instructions(for: outputLanguage))
        let response = try await session.respond(to: Self.prompt(entries: entries, outputLanguage: outputLanguage))
        return response.content
    }

    private static func instructions(for language: AppLanguage) -> String {
        language.pick(
            zh: """
            你是面对面交谈的记录员。只用简体中文写摘要。
            根据对话列出：各自想表达的要点、达成的约定、待办。
            用短句分点，不要标题党，不要编造对话里没有的内容。
            """,
            en: """
            You are a note-taker for a face-to-face conversation.
            Write the summary in English only.
            List each person's points, any agreements, and follow-ups.
            Use short bullets. Do not invent details that are not in the transcript.
            """,
            ja: """
            あなたは対面の会話の記録係です。要約は日本語のみで書いてください。
            各自の要点、合意、次の行動を短く箇条書きにします。
            会話にない内容は作らないでください。
            """,
            ko: """
            당신은 대면 대화의 기록자입니다. 요약은 한국어로만 쓰세요.
            각자의 요점, 합의, 후속 할 일을 짧은 문장으로 적습니다.
            대화에 없는 내용을 만들지 마세요.
            """,
            th: """
            คุณเป็นผู้จดบันทึกการสนทนาแบบพบหน้า เขียนสรุปเป็นภาษาไทยเท่านั้น
            ลิสต์ประเด็นของแต่ละคน ข้อตกลง และสิ่งที่ต้องทำต่อ
            ใช้ข้อความสั้น ๆ อย่าแต่งสิ่งที่ไม่มีในบทสนทนา
            """,
            vi: """
            Bạn là người ghi chép cuộc trò chuyện trực tiếp. Chỉ viết tóm tắt bằng tiếng Việt.
            Liệt kê ý chính của từng người, thỏa thuận, và việc cần làm tiếp.
            Dùng câu ngắn. Không bịa nội dung không có trong bản ghi.
            """
        )
    }

    private static func prompt(entries: [TranscriptEntry], outputLanguage: AppLanguage) -> String {
        let body = entries.map { entry in
            let speaker = label(for: entry.speaker, language: outputLanguage)
            let said = entry.sourceText
            let translated = entry.translatedText
            if translated.isEmpty {
                return "[\(speaker)] \(said)"
            }
            return "[\(speaker)] \(said)\n→ \(translated)"
        }.joined(separator: "\n\n")

        let intro = outputLanguage.pick(
            zh: "请总结下面这次对面交谈：",
            en: "Summarize this face-to-face conversation:",
            ja: "次の対面の会話を要約してください：",
            ko: "다음 대면 대화를 요약하세요:",
            th: "สรุปบทสนทนาแบบพบหน้าต่อไปนี้:",
            vi: "Hãy tóm tắt cuộc trò chuyện trực tiếp sau:"
        )
        return "\(intro)\n\n\(body)"
    }

    static func digest(entries: [TranscriptEntry], outputLanguage: AppLanguage) -> String {
        let peer = entries.filter { $0.speaker == .peer }
        let user = entries.filter { $0.speaker == .user }
        var lines: [String] = []
        lines.append(
            outputLanguage.pick(
                zh: "对话整理",
                en: "Conversation notes",
                ja: "会話メモ",
                ko: "대화 정리",
                th: "บันทึกการสนทนา",
                vi: "Ghi chú cuộc trò chuyện"
            )
        )
        if !peer.isEmpty {
            lines.append(label(for: .peer, language: outputLanguage))
            lines.append(contentsOf: peer.map { "· \($0.readableText(for: outputLanguage))" })
        }
        if !user.isEmpty {
            lines.append(label(for: .user, language: outputLanguage))
            lines.append(contentsOf: user.map { "· \($0.readableText(for: outputLanguage))" })
        }
        return lines.joined(separator: "\n")
    }

    private static func label(for speaker: SpeakerSide, language: AppLanguage) -> String {
        switch speaker {
        case .user:
            return language.pick(zh: "你", en: "You", ja: "あなた", ko: "나", th: "คุณ", vi: "Bạn")
        case .peer:
            return language.pick(zh: "对方", en: "Other person", ja: "相手", ko: "상대", th: "อีกฝ่าย", vi: "Đối phương")
        }
    }
}
