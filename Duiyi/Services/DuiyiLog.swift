import Foundation
import os

enum DuiyiLog {
    static let audio = Logger(subsystem: "com.david.Duiyi", category: "audio")
    static let speech = Logger(subsystem: "com.david.Duiyi", category: "speech")
    static let translation = Logger(subsystem: "com.david.Duiyi", category: "translation")
    static let assets = Logger(subsystem: "com.david.Duiyi", category: "assets")
    static let summary = Logger(subsystem: "com.david.Duiyi", category: "summary")
    static let session = Logger(subsystem: "com.david.Duiyi", category: "session")
}
