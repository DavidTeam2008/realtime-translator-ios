import Foundation

enum DuiyiError: Equatable, Sendable, Error {
    case microphoneDenied
    case speechDenied
    case modelsMissing
    case languageUnsupported
    case recognitionInterrupted
    case translationUnavailable
    case deviceIncapable
    case summaryEmpty

    func userMessage(for language: AppLanguage) -> String {
        switch self {
        case .microphoneDenied:
            return language.pick(
                zh: "请在设置中允许麦克风。",
                en: "Allow the microphone in Settings.",
                ja: "設定でマイクを許可してください。",
                ko: "설정에서 마이크를 허용해 주세요.",
                th: "อนุญาตไมโครโฟนในการตั้งค่า",
                vi: "Hãy cho phép micro trong Cài đặt."
            )
        case .speechDenied:
            return language.pick(
                zh: "请在设置中允许语音识别。",
                en: "Allow Speech Recognition in Settings.",
                ja: "設定で音声認識を許可してください。",
                ko: "설정에서 음성 인식을 허용해 주세요.",
                th: "อนุญาตการรู้จำเสียงพูดในการตั้งค่า",
                vi: "Hãy cho phép Nhận dạng giọng nói trong Cài đặt."
            )
        case .modelsMissing:
            return language.pick(
                zh: "需要先下载语音和翻译模型。",
                en: "Download the speech and translation models first.",
                ja: "先に音声と翻訳のモデルをダウンロードしてください。",
                ko: "먼저 음성 및 번역 모델을 다운로드하세요.",
                th: "ต้องดาวน์โหลดโมเดลเสียงและแปลก่อน",
                vi: "Hãy tải mô hình giọng nói và dịch trước."
            )
        case .languageUnsupported, .deviceIncapable:
            return language.pick(
                zh: "这台设备暂时不能离线识别这对语言。",
                en: "This device cannot transcribe this language pair offline yet.",
                ja: "このデバイスでは、この言語の組み合わせをオフライン認識できません。",
                ko: "이 기기는 아직 이 언어 쌍을 오프라인으로 인식할 수 없습니다.",
                th: "อุปกรณ์นี้ยังถอดเสียงคู่ภาษานี้แบบออฟไลน์ไม่ได้",
                vi: "Thiết bị này chưa nhận dạng được cặp ngôn ngữ này khi ngoại tuyến."
            )
        case .recognitionInterrupted:
            return language.pick(
                zh: "识别暂停了，轻点继续。",
                en: "Listening paused. Tap to continue.",
                ja: "聞き取りが止まりました。タップして続けます。",
                ko: "듣기가 멈췄습니다. 탭하여 계속하세요.",
                th: "การฟังหยุดแล้ว แตะเพื่อต่อ",
                vi: "Đã tạm dừng nghe. Chạm để tiếp tục."
            )
        case .translationUnavailable:
            return language.pick(
                zh: "听清了，但译文还没好。",
                en: "Heard you, but the translation is not ready.",
                ja: "聞こえましたが、訳がまだありません。",
                ko: "듣기는 했지만 번역이 아직 없습니다.",
                th: "ได้ยินแล้ว แต่คำแปลยังไม่พร้อม",
                vi: "Đã nghe, nhưng bản dịch chưa sẵn sàng."
            )
        case .summaryEmpty:
            return language.pick(
                zh: "还没有可总结的对话。",
                en: "There is no conversation to summarize yet.",
                ja: "要約できる会話がまだありません。",
                ko: "요약할 대화가 아직 없습니다.",
                th: "ยังไม่มีบทสนทนาให้สรุป",
                vi: "Chưa có cuộc trò chuyện để tóm tắt."
            )
        }
    }
}
