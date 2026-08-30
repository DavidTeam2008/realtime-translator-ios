import Foundation

extension Copy {
    static func featureTitle(_ feature: FeatureID, for language: AppLanguage) -> String {
        switch feature {
        case .faceToFace: return modeFaceToFace(for: language)
        case .simultaneous: return modeSimultaneous(for: language)
        case .meeting: return modeMeeting(for: language)
        }
    }

    static func modeMeeting(for language: AppLanguage) -> String {
        language.pick(zh: "会议记录", en: "Meeting notes", ja: "会議記録", ko: "회의 기록", th: "บันทึกประชุม", vi: "Ghi chép họp")
    }

    static func homeTitle(for language: AppLanguage) -> String {
        appTitle(for: language)
    }

    static func homeFaceToFaceSubtitle(for language: AppLanguage) -> String {
        language.pick(
            zh: "两人隔桌，字幕打到各自一侧",
            en: "Two people, captions on each side",
            ja: "向かい合い、字幕はそれぞれの側に",
            ko: "마주 앉아 각자 쪽으로 자막",
            th: "สองคน ซับไตล์คนละฝั่ง",
            vi: "Hai người, phụ đề mỗi bên"
        )
    }

    static func homeSimultaneousSubtitle(for language: AppLanguage) -> String {
        language.pick(
            zh: "听现场，看或听译文",
            en: "Hear the room, read or listen to the translation",
            ja: "現場を聞き、訳を読むか聞く",
            ko: "현장을 듣고 번역을 보거나 들음",
            th: "ฟังสถานที่ ดูหรือฟังคำแปล",
            vi: "Nghe hiện trường, đọc hoặc nghe bản dịch"
        )
    }

    static func homeMeetingSubtitle(for language: AppLanguage) -> String {
        language.pick(
            zh: "把一场会记成完整文字稿",
            en: "Turn a meeting into a full transcript",
            ja: "会議を全文の文字起こしに",
            ko: "회의를 전체 기록으로",
            th: "บันทึกประชุมเป็นข้อความเต็ม",
            vi: "Ghi cả buổi họp thành bản chữ"
        )
    }

    static func historyTitle(for language: AppLanguage) -> String {
        language.pick(zh: "任务历史", en: "History", ja: "履歴", ko: "기록", th: "ประวัติ", vi: "Lịch sử")
    }

    static func historySubtitle(for language: AppLanguage) -> String {
        language.pick(
            zh: "都保存在这台 iPhone 上",
            en: "Kept on this iPhone",
            ja: "この iPhone に保存されます",
            ko: "이 iPhone에 저장됩니다",
            th: "เก็บไว้บน iPhone เครื่องนี้",
            vi: "Lưu trên iPhone này"
        )
    }

    static func historyEmpty(for language: AppLanguage) -> String {
        language.pick(
            zh: "还没有任务。从首页开一个新任务。",
            en: "No tasks yet. Start one from Home.",
            ja: "まだタスクがありません。ホームから新しいタスクを始めてください。",
            ko: "아직 작업이 없습니다. 홈에서 새 작업을 시작하세요.",
            th: "ยังไม่มีงาน เริ่มงานใหม่จากหน้าแรก",
            vi: "Chưa có phiên. Hãy bắt đầu từ Trang chủ."
        )
    }

    static func homeButton(for language: AppLanguage) -> String {
        language.pick(zh: "首页", en: "Home", ja: "ホーム", ko: "홈", th: "หน้าแรก", vi: "Trang chủ")
    }

    static func newTask(for language: AppLanguage) -> String {
        language.pick(zh: "新任务", en: "New task", ja: "新しいタスク", ko: "새 작업", th: "งานใหม่", vi: "Phiên mới")
    }

    static func endTask(for language: AppLanguage) -> String {
        language.pick(zh: "结束任务", en: "End task", ja: "タスク終了", ko: "작업 종료", th: "จบงาน", vi: "Kết thúc")
    }

    static func taskIdle(for language: AppLanguage) -> String {
        language.pick(
            zh: "没有进行中的任务",
            en: "No task in progress",
            ja: "進行中のタスクはありません",
            ko: "진행 중인 작업이 없습니다",
            th: "ไม่มีงานที่กำลังทำ",
            vi: "Không có phiên đang chạy"
        )
    }

    static func taskRunning(for language: AppLanguage) -> String {
        language.pick(zh: "进行中", en: "In progress", ja: "進行中", ko: "진행 중", th: "กำลังทำ", vi: "Đang chạy")
    }

    static func needNewTask(for language: AppLanguage) -> String {
        language.pick(
            zh: "先开一个新任务",
            en: "Start a new task first",
            ja: "先に新しいタスクを始めてください",
            ko: "먼저 새 작업을 시작하세요",
            th: "เริ่มงานใหม่ก่อน",
            vi: "Hãy mở một phiên mới trước"
        )
    }

    static func endTaskConfirm(for language: AppLanguage) -> String {
        language.pick(
            zh: "结束并保存这条记录？",
            en: "End and save this record?",
            ja: "終了してこの記録を保存しますか？",
            ko: "종료하고 이 기록을 저장할까요?",
            th: "จบและบันทึกรายการนี้?",
            vi: "Kết thúc và lưu bản ghi này?"
        )
    }

    static func replaceTaskConfirm(for language: AppLanguage) -> String {
        language.pick(
            zh: "结束当前任务并开始新的？",
            en: "End the current task and start a new one?",
            ja: "現在のタスクを終了して新しく始めますか？",
            ko: "현재 작업을 종료하고 새로 시작할까요?",
            th: "จบงานปัจจุบันแล้วเริ่มใหม่?",
            vi: "Kết thúc phiên hiện tại và bắt đầu phiên mới?"
        )
    }

    static func deleteTaskConfirm(for language: AppLanguage) -> String {
        language.pick(
            zh: "删除这条记录？",
            en: "Delete this record?",
            ja: "この記録を削除しますか？",
            ko: "이 기록을 삭제할까요?",
            th: "ลบรายการนี้?",
            vi: "Xóa bản ghi này?"
        )
    }

    static func delete(for language: AppLanguage) -> String {
        language.pick(zh: "删除", en: "Delete", ja: "削除", ko: "삭제", th: "ลบ", vi: "Xóa")
    }

    static func cancel(for language: AppLanguage) -> String {
        language.pick(zh: "取消", en: "Cancel", ja: "キャンセル", ko: "취소", th: "ยกเลิก", vi: "Hủy")
    }

    static func filterAll(for language: AppLanguage) -> String {
        language.pick(zh: "全部", en: "All", ja: "すべて", ko: "전체", th: "ทั้งหมด", vi: "Tất cả")
    }

    static func unfinishedTasks(for language: AppLanguage) -> String {
        language.pick(zh: "未结束的任务", en: "Unfinished tasks", ja: "未完了のタスク", ko: "끝나지 않은 작업", th: "งานที่ยังไม่จบ", vi: "Phiên chưa kết thúc")
    }

    static func recordTitle(for language: AppLanguage) -> String {
        language.pick(zh: "记录", en: "Record", ja: "記録", ko: "기록", th: "บันทึก", vi: "Bản ghi")
    }

    static func exportShare(for language: AppLanguage) -> String {
        language.pick(
            zh: "导出文字稿并分享",
            en: "Export transcript and share",
            ja: "文字起こしを書き出して共有",
            ko: "기록 내보내기 및 공유",
            th: "ส่งออกข้อความแล้วแชร์",
            vi: "Xuất bản ghi và chia sẻ"
        )
    }

    static func transcriptSection(for language: AppLanguage) -> String {
        language.pick(zh: "文字稿", en: "Transcript", ja: "文字起こし", ko: "기록", th: "ข้อความ", vi: "Bản ghi")
    }

    static func justNow(for language: AppLanguage) -> String {
        language.pick(zh: "刚刚", en: "Just now", ja: "たった今", ko: "방금", th: "เมื่อกี้", vi: "Vừa xong")
    }

    static func underOneMinute(for language: AppLanguage) -> String {
        language.pick(zh: "不到 1 分钟", en: "Under 1 min", ja: "1分未満", ko: "1분 미만", th: "ไม่ถึง 1 นาที", vi: "Dưới 1 phút")
    }

    static func minutesCount(_ minutes: Int, for language: AppLanguage) -> String {
        language.pick(
            zh: "\(minutes) 分钟",
            en: "\(minutes) min",
            ja: "\(minutes)分",
            ko: "\(minutes)분",
            th: "\(minutes) นาที",
            vi: "\(minutes) phút"
        )
    }

    static func recording(for language: AppLanguage) -> String {
        language.pick(zh: "记录中", en: "Recording", ja: "記録中", ko: "기록 중", th: "กำลังบันทึก", vi: "Đang ghi")
    }

    static func meetingLanguage(for language: AppLanguage) -> String {
        language.pick(zh: "记录语言", en: "Meeting language", ja: "記録する言語", ko: "기록 언어", th: "ภาษาที่บันทึก", vi: "Ngôn ngữ ghi")
    }

    static func meetingTooLong(for language: AppLanguage) -> String {
        language.pick(
            zh: "这篇稿已经很长。请结束并再开一条新任务。",
            en: "This transcript is long. End it and start a new task.",
            ja: "文字起こしが長くなりました。終了して新しいタスクを始めてください。",
            ko: "기록이 길어졌습니다. 종료하고 새 작업을 시작하세요.",
            th: "ข้อความยาวแล้ว จบแล้วเริ่มงานใหม่",
            vi: "Bản ghi đã dài. Hãy kết thúc và mở phiên mới."
        )
    }

    static func translateToMine(for language: AppLanguage) -> String {
        language.pick(
            zh: "译成我看的语言",
            en: "Translate into the language I read",
            ja: "自分が読む言語に訳す",
            ko: "내가 읽는 언어로 번역",
            th: "แปลเป็นภาษาที่ฉันอ่าน",
            vi: "Dịch sang ngôn ngữ tôi đọc"
        )
    }

    static func appleIntelligenceGenerated(for language: AppLanguage) -> String {
        language.pick(
            zh: "摘要由 Apple 智能在本机生成。",
            en: "Summary generated on this iPhone by Apple Intelligence.",
            ja: "要約は Apple Intelligence がこの iPhone 上で生成しました。",
            ko: "요약은 Apple Intelligence가 이 iPhone에서 생성했습니다.",
            th: "สรุปสร้างบน iPhone เครื่องนี้โดย Apple Intelligence",
            vi: "Tóm tắt do Apple Intelligence tạo trên iPhone này."
        )
    }

    static func summaryDeviceNotEligible(for language: AppLanguage) -> String {
        language.pick(
            zh: "这台 iPhone 不能使用 Apple 智能。可以把文字稿导出，用元宝等工具总结。",
            en: "This iPhone cannot use Apple Intelligence. Export the transcript and summarize it in another app.",
            ja: "この iPhone では Apple Intelligence を使えません。文字起こしを書き出して、ほかのアプリで要約できます。",
            ko: "이 iPhone에서는 Apple Intelligence를 사용할 수 없습니다. 기록을 내보낸 뒤 다른 앱에서 요약하세요.",
            th: "iPhone เครื่องนี้ใช้ Apple Intelligence ไม่ได้ ส่งออกข้อความแล้วสรุปในแอปอื่นได้",
            vi: "iPhone này không dùng được Apple Intelligence. Hãy xuất bản ghi và tóm tắt bằng ứng dụng khác."
        )
    }

    static func summaryIntelligenceOff(for language: AppLanguage) -> String {
        language.pick(
            zh: "这台设备支持 Apple 智能。请到「设置 → Apple 智能与 Siri」打开后，即可在本机生成摘要。仍可先导出文字稿。",
            en: "This device supports Apple Intelligence. Turn it on in Settings → Apple Intelligence & Siri to summarize on this iPhone. You can still export the transcript.",
            ja: "このデバイスは Apple Intelligence に対応しています。「設定 → Apple IntelligenceとSiri」でオンにすると、この iPhone 上で要約できます。文字起こしの書き出しは今すぐできます。",
            ko: "이 기기는 Apple Intelligence를 지원합니다. 설정 → Apple Intelligence 및 Siri에서 켜면 이 iPhone에서 요약할 수 있습니다. 기록은 지금 내보낼 수 있습니다.",
            th: "อุปกรณ์นี้รองรับ Apple Intelligence เปิดที่การตั้งค่า → Apple Intelligence และ Siri เพื่อสรุปบนเครื่อง ส่งออกข้อความได้ทันที",
            vi: "Máy này hỗ trợ Apple Intelligence. Bật trong Cài đặt → Apple Intelligence & Siri để tóm tắt trên máy. Vẫn có thể xuất bản ghi."
        )
    }

    static func summaryModelNotReady(for language: AppLanguage) -> String {
        language.pick(
            zh: "本机摘要模型还在准备，请稍后再试。现在可以先导出文字稿。",
            en: "The on-device summary model is still preparing. Try again later. You can export the transcript now.",
            ja: "要約モデルを準備中です。しばらくしてから再試行してください。文字起こしは今すぐ書き出せます。",
            ko: "온디바이스 요약 모델이 아직 준비 중입니다. 나중에 다시 시도하세요. 기록은 지금 내보낼 수 있습니다.",
            th: "โมเดลสรุปบนเครื่องยังไม่พร้อม ลองใหม่ภายหลัง ส่งออกข้อความได้ตอนนี้",
            vi: "Mô hình tóm tắt trên máy chưa sẵn. Thử lại sau. Có thể xuất bản ghi ngay."
        )
    }

    static func summaryUnavailable(for language: AppLanguage) -> String {
        language.pick(
            zh: "现在无法在本机生成摘要，请导出后用其他工具。",
            en: "A summary cannot be generated on this iPhone right now. Export and use another tool.",
            ja: "現在この iPhone では要約を作れません。書き出してほかのツールを使ってください。",
            ko: "지금은 이 iPhone에서 요약을 만들 수 없습니다. 내보낸 뒤 다른 도구를 사용하세요.",
            th: "ตอนนี้สรุปบนเครื่องไม่ได้ ส่งออกแล้วใช้เครื่องมืออื่น",
            vi: "Hiện không tạo được tóm tắt trên máy. Hãy xuất và dùng công cụ khác."
        )
    }

    static func summaryAvailabilityMessage(_ availability: SummaryAvailability, for language: AppLanguage) -> String {
        switch availability {
        case .available:
            return appleIntelligenceGenerated(for: language)
        case .deviceNotEligible:
            return summaryDeviceNotEligible(for: language)
        case .appleIntelligenceOff:
            return summaryIntelligenceOff(for: language)
        case .modelNotReady:
            return summaryModelNotReady(for: language)
        case .unavailable:
            return summaryUnavailable(for: language)
        }
    }

    static func exportHeader(app: String, feature: String, range: String, direction: String) -> String {
        "\(app) · \(feature)\n\(range)\n\(direction)"
    }

    static func languageUnavailable(for language: AppLanguage) -> String {
        language.pick(
            zh: "这台 iPhone 还没有这个语言模型",
            en: "This iPhone does not have this language model yet",
            ja: "この iPhone には、この言語モデルがまだありません",
            ko: "이 iPhone에는 아직 이 언어 모델이 없습니다",
            th: "iPhone เครื่องนี้ยังไม่มีโมเดลภาษานี้",
            vi: "iPhone này chưa có mô hình ngôn ngữ này"
        )
    }
}

enum TaskFormatting {
    static func durationText(seconds: TimeInterval, language: AppLanguage) -> String {
        if seconds < 60 {
            return Copy.underOneMinute(for: language)
        }
        return Copy.minutesCount(Int(seconds / 60), for: language)
    }

    static func startedText(date: Date, language: AppLanguage) -> String {
        if Calendar.current.isDateInToday(date) {
            let time = date.formatted(Date.FormatStyle(time: .shortened).locale(language.locale))
            return time
        }
        return date.formatted(
            Date.FormatStyle(date: .abbreviated, time: .shortened).locale(language.locale)
        )
    }

    static func historyMeta(task: TaskSession, language: AppLanguage) -> String {
        let when = startedText(date: task.startedAt, language: language)
        let length = durationText(seconds: task.duration, language: language)
        return "\(when) · \(length)"
    }
}
