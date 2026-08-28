import Foundation

enum Copy {
    static func speaking(for language: AppLanguage) -> String {
        language.pick(zh: "正在说…", en: "Speaking…", ja: "話しています…", ko: "말하는 중…", th: "กำลังพูด…", vi: "Đang nói…")
    }

    static func listening(for language: AppLanguage) -> String {
        language.pick(zh: "聆听中", en: "Listening", ja: "聞き取り中", ko: "듣는 중", th: "กำลังฟัง", vi: "Đang nghe")
    }

    static func tapToStart(for language: AppLanguage) -> String {
        language.pick(zh: "轻点开始", en: "Tap to start", ja: "タップして開始", ko: "탭하여 시작", th: "แตะเพื่อเริ่ม", vi: "Chạm để bắt đầu")
    }

    static func paused(for language: AppLanguage) -> String {
        language.pick(zh: "已暂停", en: "Paused", ja: "一時停止", ko: "일시 정지", th: "หยุดชั่วคราว", vi: "Đã tạm dừng")
    }

    static func idlePrompt(for language: AppLanguage) -> String {
        language.pick(
            zh: "轻点中间，开始听对面说话。",
            en: "Tap the center to start listening.",
            ja: "中央をタップして、相手の話を聞き始めます。",
            ko: "가운데를 탭하면 상대의 말을 듣기 시작합니다.",
            th: "แตะตรงกลางเพื่อเริ่มฟังอีกฝ่าย",
            vi: "Chạm vào giữa để bắt đầu nghe đối phương."
        )
    }

    static func peerIdlePrompt(for language: AppLanguage) -> String {
        language.pick(
            zh: "把手机放在我们中间。",
            en: "Place the phone between us.",
            ja: "スマホを二人の間に置いてください。",
            ko: "휴대폰을 우리 사이에 두세요.",
            th: "วางโทรศัพท์ไว้ระหว่างเรา",
            vi: "Đặt điện thoại giữa chúng ta."
        )
    }

    static func settingsTitle(for language: AppLanguage) -> String {
        language.pick(zh: "设置", en: "Settings", ja: "設定", ko: "설정", th: "ตั้งค่า", vi: "Cài đặt")
    }

    static func done(for language: AppLanguage) -> String {
        language.pick(zh: "完成", en: "Done", ja: "完了", ko: "완료", th: "เสร็จ", vi: "Xong")
    }

    static func clearCaptions(for language: AppLanguage) -> String {
        language.pick(zh: "清屏", en: "Clear", ja: "消去", ko: "지우기", th: "ล้าง", vi: "Xóa")
    }

    static func iReadSection(for language: AppLanguage) -> String {
        language.pick(zh: "我看的语言", en: "I read", ja: "自分が読む言語", ko: "내가 읽는 언어", th: "ภาษาที่ฉันอ่าน", vi: "Ngôn ngữ tôi đọc")
    }

    static func changeLanguage(for language: AppLanguage) -> String {
        language.pick(zh: "更换语言", en: "Change language", ja: "言語を変更", ko: "언어 변경", th: "เปลี่ยนภาษา", vi: "Đổi ngôn ngữ")
    }

    static func swapLanguages(for language: AppLanguage) -> String {
        language.pick(zh: "对调双方语言", en: "Swap languages", ja: "言語を入れ替え", ko: "언어 맞바꾸기", th: "สลับภาษา", vi: "Đổi chỗ ngôn ngữ")
    }

    static func theyReadSection(for language: AppLanguage) -> String {
        language.pick(zh: "对方看的语言", en: "They read", ja: "相手が読む言語", ko: "상대가 읽는 언어", th: "ภาษาที่อีกฝ่ายอ่าน", vi: "Ngôn ngữ đối phương đọc")
    }

    static func fontStandard(for language: AppLanguage) -> String {
        language.pick(zh: "标准", en: "Regular", ja: "標準", ko: "보통", th: "ปกติ", vi: "Vừa")
    }

    static func fontLarger(for language: AppLanguage) -> String {
        language.pick(zh: "更大", en: "Larger", ja: "大きく", ko: "더 크게", th: "ใหญ่ขึ้น", vi: "Lớn hơn")
    }

    static func fontLargest(for language: AppLanguage) -> String {
        language.pick(zh: "最大", en: "Largest", ja: "最大", ko: "가장 크게", th: "ใหญ่สุด", vi: "Lớn nhất")
    }

    static func tableHint(for language: AppLanguage) -> String {
        language.pick(
            zh: "请把手机平放在两人中间。",
            en: "Lay the phone flat between you.",
            ja: "スマホを二人の間に平らに置いてください。",
            ko: "휴대폰을 둘 사이에 평평하게 두세요.",
            th: "วางโทรศัพท์ราบระหว่างคุณทั้งคู่",
            vi: "Đặt điện thoại nằm ngang giữa hai người."
        )
    }

    static func openSettings(for language: AppLanguage) -> String {
        language.pick(zh: "去设置", en: "Open Settings", ja: "設定を開く", ko: "설정 열기", th: "เปิดการตั้งค่า", vi: "Mở Cài đặt")
    }

    static func preparing(for language: AppLanguage) -> String {
        language.pick(zh: "正在准备…", en: "Getting ready…", ja: "準備中…", ko: "준비 중…", th: "กำลังเตรียม…", vi: "Đang chuẩn bị…")
    }

    static func useSystemLanguage(for language: AppLanguage) -> String {
        language.pick(
            zh: "跳过，使用系统语言",
            en: "Skip, use system language",
            ja: "スキップしてシステム言語を使う",
            ko: "건너뛰고 시스템 언어 사용",
            th: "ข้าม ใช้ภาษาของระบบ",
            vi: "Bỏ qua, dùng ngôn ngữ hệ thống"
        )
    }

    static func microphoneTitle(for language: AppLanguage) -> String {
        language.pick(zh: "麦克风", en: "Microphone", ja: "マイク", ko: "마이크", th: "ไมโครโฟน", vi: "Micro")
    }

    static func microphoneReason(for language: AppLanguage) -> String {
        language.pick(
            zh: "听见你们说的话。",
            en: "Hears what you both say.",
            ja: "二人の話を拾います。",
            ko: "두 사람의 말을 듣습니다.",
            th: "ได้ยินสิ่งที่ทั้งคู่พูด",
            vi: "Nghe những gì cả hai nói."
        )
    }

    static func speechTitle(for language: AppLanguage) -> String {
        language.pick(zh: "语音识别", en: "Speech Recognition", ja: "音声認識", ko: "음성 인식", th: "การรู้จำเสียงพูด", vi: "Nhận dạng giọng nói")
    }

    static func speechReason(for language: AppLanguage) -> String {
        language.pick(
            zh: "在本机转成文字。语音不会上传。",
            en: "Turns speech into text on this iPhone. Audio is not uploaded.",
            ja: "この iPhone 上で文字にします。音声は送信しません。",
            ko: "이 iPhone에서 글자로 바꿉니다. 음성은 업로드되지 않습니다.",
            th: "แปลงเสียงเป็นข้อความบน iPhone เครื่องนี้ ไม่ได้อัปโหลดเสียง",
            vi: "Chuyển giọng nói thành chữ trên iPhone này. Âm thanh không được tải lên."
        )
    }

    static func speechModelsTitle(for language: AppLanguage) -> String {
        language.pick(zh: "语音模型", en: "Speech models", ja: "音声モデル", ko: "음성 모델", th: "โมเดลเสียง", vi: "Mô hình giọng nói")
    }

    static func translationModelsTitle(for language: AppLanguage) -> String {
        language.pick(zh: "翻译模型", en: "Translation models", ja: "翻訳モデル", ko: "번역 모델", th: "โมเดลแปล", vi: "Mô hình dịch")
    }

    static func downloadModels(for language: AppLanguage) -> String {
        language.pick(zh: "下载模型", en: "Download models", ja: "モデルをダウンロード", ko: "모델 다운로드", th: "ดาวน์โหลดโมเดล", vi: "Tải mô hình")
    }

    static func enterConversation(for language: AppLanguage) -> String {
        language.pick(zh: "进入对话", en: "Start talking", ja: "会話を始める", ko: "대화 시작", th: "เริ่มพูด", vi: "Bắt đầu nói")
    }

    static func retry(for language: AppLanguage) -> String {
        language.pick(zh: "重试", en: "Try again", ja: "再試行", ko: "다시 시도", th: "ลองอีกครั้ง", vi: "Thử lại")
    }

    static func autoStart(for language: AppLanguage) -> String {
        language.pick(
            zh: "打开后自动聆听",
            en: "Listen automatically",
            ja: "起動したら自動で聞き取る",
            ko: "열면 자동으로 듣기",
            th: "ฟังอัตโนมัติเมื่อเปิด",
            vi: "Tự nghe khi mở"
        )
    }

    static func autoStartOn(for language: AppLanguage) -> String {
        language.pick(zh: "自动开始", en: "Auto start", ja: "自動開始", ko: "자동 시작", th: "เริ่มอัตโนมัติ", vi: "Tự bắt đầu")
    }

    static func autoStartOff(for language: AppLanguage) -> String {
        language.pick(zh: "手动开始", en: "Manual", ja: "手動", ko: "수동", th: "เริ่มเอง", vi: "Bắt đầu tay")
    }

    static func redownloadModels(for language: AppLanguage) -> String {
        language.pick(
            zh: "重新下载语言模型",
            en: "Redownload language models",
            ja: "言語モデルを再ダウンロード",
            ko: "언어 모델 다시 다운로드",
            th: "ดาวน์โหลดโมเดลภาษาอีกครั้ง",
            vi: "Tải lại mô hình ngôn ngữ"
        )
    }

    static func summarize(for language: AppLanguage) -> String {
        language.pick(
            zh: "总结这次对话",
            en: "Summarize conversation",
            ja: "この会話を要約",
            ko: "이 대화 요약",
            th: "สรุปบทสนทนานี้",
            vi: "Tóm tắt cuộc trò chuyện"
        )
    }

    static func summaryTitle(for language: AppLanguage) -> String {
        language.pick(zh: "对话总结", en: "Conversation summary", ja: "会話の要約", ko: "대화 요약", th: "สรุปบทสนทนา", vi: "Tóm tắt cuộc trò chuyện")
    }

    static func summaryLoading(for language: AppLanguage) -> String {
        language.pick(
            zh: "正在用本机模型整理…",
            en: "Summarizing on this iPhone…",
            ja: "この iPhone 上で要約しています…",
            ko: "이 iPhone에서 요약하는 중…",
            th: "กำลังสรุปบน iPhone เครื่องนี้…",
            vi: "Đang tóm tắt trên iPhone này…"
        )
    }

    static func copySummary(for language: AppLanguage) -> String {
        language.pick(zh: "拷贝", en: "Copy", ja: "コピー", ko: "복사", th: "คัดลอก", vi: "Sao chép")
    }

    static func summaryLocalFallback(for language: AppLanguage) -> String {
        language.pick(
            zh: "当前用对话记录整理。打开「Apple 智能」后，可用本机模型生成更完整的摘要。",
            en: "Notes from the transcript. Turn on Apple Intelligence for a fuller on-device summary.",
            ja: "会話記録から整理しています。「Apple Intelligence」をオンにすると、より詳しい要約が作れます。",
            ko: "대화 기록으로 정리했습니다. Apple Intelligence를 켜면 더 풍부한 요약을 만들 수 있습니다.",
            th: "จัดจากบันทึกการสนทนา เปิด Apple Intelligence เพื่อสรุปที่สมบูรณ์กว่าบนเครื่อง",
            vi: "Ghi chú từ bản ghi. Bật Apple Intelligence để có bản tóm tắt đầy đủ hơn trên máy."
        )
    }

    static func appTitle(for language: AppLanguage) -> String {
        language.pick(zh: "对译", en: "Duiyi", ja: "対訳", ko: "대역", th: "Duiyi", vi: "Duiyi")
    }

    static func welcomeBody(for language: AppLanguage) -> String {
        language.pick(
            zh: "把手机平放在中间，对面就能看懂你说的话。",
            en: "Lay the phone between you. The other person will see captions they can read.",
            ja: "スマホを間に置けば、相手は読める字幕で話を理解できます。",
            ko: "휴대폰을 가운데 두면, 상대가 읽을 수 있는 자막으로 말을 이해합니다.",
            th: "วางโทรศัพท์ตรงกลาง อีกฝ่ายจะเห็นคำบรรยายที่อ่านได้",
            vi: "Đặt điện thoại ở giữa. Đối phương sẽ thấy phụ đề họ đọc được."
        )
    }

    static func languageQuestion(for language: AppLanguage) -> String {
        language.pick(
            zh: "你们各自看哪种语言？",
            en: "Which languages do you each read?",
            ja: "それぞれどの言語を読みますか？",
            ko: "각자 어떤 언어를 읽나요?",
            th: "แต่ละคนอ่านภาษาอะไร?",
            vi: "Mỗi người đọc ngôn ngữ nào?"
        )
    }

    static func languageBody(for language: AppLanguage) -> String {
        language.pick(
            zh: "选你看的语言，再选对方看的。一次只翻译这一对。",
            en: "Choose the language you read, then theirs. We translate this pair only.",
            ja: "自分が読む言語と、相手が読む言語を選びます。この組み合わせだけを翻訳します。",
            ko: "내가 읽는 언어와 상대가 읽는 언어를 고르세요. 이 한 쌍만 번역합니다.",
            th: "เลือกภาษาที่คุณอ่าน แล้วเลือกของอีกฝ่าย แปลเฉพาะคู่นี้",
            vi: "Chọn ngôn ngữ bạn đọc, rồi chọn của đối phương. Chỉ dịch cặp này."
        )
    }

    static func permissionTitle(for language: AppLanguage) -> String {
        language.pick(zh: "需要两样许可", en: "Two permissions", ja: "許可が2つ必要です", ko: "권한이 두 가지 필요합니다", th: "ต้องการสิทธิ์สองอย่าง", vi: "Cần hai quyền")
    }

    static func permissionBody(for language: AppLanguage) -> String {
        language.pick(
            zh: "一次说清要什么、为什么。拒绝时可以去系统设置打开。",
            en: "We’ll explain what we need and why. If you decline, you can allow access in Settings.",
            ja: "何が必要か、なぜかを説明します。拒否した場合は設定で許可できます。",
            ko: "무엇이 왜 필요한지 설명합니다. 거절했다면 설정에서 허용할 수 있습니다.",
            th: "เราจะอธิบายว่าต้องการอะไรและทำไม หากปฏิเสธ เปิดได้ในการตั้งค่า",
            vi: "Chúng tôi sẽ giải thích cần gì và vì sao. Nếu từ chối, có thể bật trong Cài đặt."
        )
    }

    static func assetsTitle(for language: AppLanguage) -> String {
        language.pick(zh: "准备离线模型", en: "Prepare offline models", ja: "オフラインモデルを準備", ko: "오프라인 모델 준비", th: "เตรียมโมเดลออฟไลน์", vi: "Chuẩn bị mô hình ngoại tuyến")
    }

    static func assetsBody(for language: AppLanguage) -> String {
        language.pick(
            zh: "下载只需一次，之后可完全离线。",
            en: "Download once, then it works fully offline.",
            ja: "ダウンロードは一度だけ。その後は完全にオフラインで使えます。",
            ko: "한 번만 다운로드하면 이후에는 완전히 오프라인으로 쓸 수 있습니다.",
            th: "ดาวน์โหลดครั้งเดียว แล้วใช้แบบออฟไลน์ได้เต็มที่",
            vi: "Tải một lần, sau đó dùng hoàn toàn ngoại tuyến."
        )
    }

    static func getStarted(for language: AppLanguage) -> String {
        language.pick(zh: "开始", en: "Get started", ja: "始める", ko: "시작하기", th: "เริ่มต้น", vi: "Bắt đầu")
    }

    static func continueButton(for language: AppLanguage) -> String {
        language.pick(zh: "继续", en: "Continue", ja: "続ける", ko: "계속", th: "ดำเนินการต่อ", vi: "Tiếp tục")
    }

    static func allow(for language: AppLanguage) -> String {
        language.pick(zh: "允许", en: "Allow", ja: "許可", ko: "허용", th: "อนุญาต", vi: "Cho phép")
    }
}
