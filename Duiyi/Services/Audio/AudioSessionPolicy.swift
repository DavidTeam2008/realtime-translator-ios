import AVFAudio
import Foundation

enum AudioUseCase: Equatable, Sendable {
    case faceToFace
    case interpretationCaptions
    case interpretationVoiceOut
}

enum AudioRouteKind: Equatable, Sendable {
    case headphones
    case bluetoothA2DP
    case bluetoothLE
    case bluetoothHFP
    case builtInReceiver
    case builtInSpeaker
    case usbAudio
    case hearingAid
    case external
    case other

    var isHeadphoneLike: Bool {
        switch self {
        case .headphones, .bluetoothA2DP, .bluetoothLE, .bluetoothHFP, .builtInReceiver, .usbAudio, .hearingAid, .external:
            return true
        case .builtInSpeaker, .other:
            return false
        }
    }
}

struct AudioRouteSnapshot: Equatable, Sendable {
    var outputs: [AudioRouteKind]
    var inputs: [AudioRouteKind] = []

    var canSpeakWithoutEcho: Bool {
        AudioEchoPolicy.canSpeakWithoutEcho(outputs: outputs, inputs: inputs)
    }
}

enum AudioEchoPolicy {
    static func canSpeakWithoutEcho(
        outputs: [AudioRouteKind],
        inputs: [AudioRouteKind] = []
    ) -> Bool {
        outputs.contains { $0.isHeadphoneLike } || inputs.contains { $0.isHeadphoneLike }
    }
}

protocol AudioSessionConfiguring: Sendable {
    func activate(_ useCase: AudioUseCase) async throws
    func deactivate() async
    func currentRoute() async -> AudioRouteSnapshot
    func routeChanges() async -> AsyncStream<AudioRouteSnapshot>
}

actor NoOpAudioSession: AudioSessionConfiguring {
    var snapshot = AudioRouteSnapshot(outputs: [.headphones])

    func activate(_ useCase: AudioUseCase) async throws {
        _ = useCase
    }

    func deactivate() async {}

    func currentRoute() async -> AudioRouteSnapshot {
        snapshot
    }

    func routeChanges() async -> AsyncStream<AudioRouteSnapshot> {
        AsyncStream { continuation in
            continuation.finish()
        }
    }
}

actor AudioSessionPolicy: AudioSessionConfiguring {
    private var continuations: [UUID: AsyncStream<AudioRouteSnapshot>.Continuation] = [:]
    private var observer: NSObjectProtocol?

    func activate(_ useCase: AudioUseCase) async throws {
        let session = AVAudioSession.sharedInstance()
        switch useCase {
        case .faceToFace:
            try session.setCategory(.record, mode: .measurement, options: [.duckOthers])
        case .interpretationCaptions:
            try session.setCategory(.record, mode: .measurement, options: [.duckOthers])
        case .interpretationVoiceOut:
            try session.setCategory(
                .playAndRecord,
                mode: .default,
                options: [.duckOthers, .allowBluetoothA2DP]
            )
            try session.overrideOutputAudioPort(.none)
        }
        try session.setActive(true, options: .notifyOthersOnDeactivation)
        preferPhoneMicrophone(on: session)
        startObservingIfNeeded()
        let snapshot = Self.snapshot(from: session)
        DuiyiLog.audio.info(
            "Audio session \(String(describing: useCase), privacy: .public) outputs=\(String(describing: snapshot.outputs), privacy: .public) inputs=\(String(describing: snapshot.inputs), privacy: .public)"
        )
    }

    func deactivate() async {
        do {
            try AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        } catch {
            DuiyiLog.audio.error("Failed to deactivate audio session: \(error.localizedDescription, privacy: .public)")
        }
    }

    func currentRoute() async -> AudioRouteSnapshot {
        Self.snapshot(from: AVAudioSession.sharedInstance())
    }

    func routeChanges() async -> AsyncStream<AudioRouteSnapshot> {
        let id = UUID()
        return AsyncStream { continuation in
            let streamID = id
            Task {
                await self.addContinuation(id: streamID, continuation: continuation)
            }
            continuation.onTermination = { _ in
                Task {
                    await self.removeContinuation(id: streamID)
                }
            }
        }
    }

    private func addContinuation(
        id: UUID,
        continuation: AsyncStream<AudioRouteSnapshot>.Continuation
    ) {
        continuations[id] = continuation
        startObservingIfNeeded()
    }

    private func removeContinuation(id: UUID) {
        continuations[id] = nil
    }

    private func startObservingIfNeeded() {
        guard observer == nil else { return }
        observer = NotificationCenter.default.addObserver(
            forName: AVAudioSession.routeChangeNotification,
            object: AVAudioSession.sharedInstance(),
            queue: .main
        ) { [weak self] _ in
            Task {
                await self?.broadcastRoute()
            }
        }
    }

    private func broadcastRoute() {
        let snapshot = Self.snapshot(from: AVAudioSession.sharedInstance())
        DuiyiLog.audio.info(
            "Route changed outputs=\(String(describing: snapshot.outputs), privacy: .public) inputs=\(String(describing: snapshot.inputs), privacy: .public)"
        )
        for continuation in continuations.values {
            continuation.yield(snapshot)
        }
    }

    private func preferPhoneMicrophone(on session: AVAudioSession) {
        guard let builtIn = session.availableInputs?.first(where: { $0.portType == .builtInMic }) else {
            return
        }
        do {
            try session.setPreferredInput(builtIn)
            if let bottom = builtIn.dataSources?.first(where: { $0.orientation == .bottom }) {
                try builtIn.setPreferredDataSource(bottom)
            }
        } catch {
            DuiyiLog.audio.error("Could not prefer iPhone microphone: \(error.localizedDescription, privacy: .public)")
        }
    }

    nonisolated static func snapshot(from session: AVAudioSession) -> AudioRouteSnapshot {
        let outputs = session.currentRoute.outputs.map { AudioRouteKind($0.portType) }
        var inputs = session.currentRoute.inputs.map { AudioRouteKind($0.portType) }
        if let available = session.availableInputs {
            inputs.append(contentsOf: available.map { AudioRouteKind($0.portType) })
        }
        return AudioRouteSnapshot(outputs: outputs, inputs: inputs)
    }
}

extension AudioRouteKind {
    init(_ port: AVAudioSession.Port) {
        switch port {
        case .headphones:
            self = .headphones
        case .bluetoothA2DP:
            self = .bluetoothA2DP
        case .bluetoothLE:
            self = .bluetoothLE
        case .bluetoothHFP:
            self = .bluetoothHFP
        case .builtInReceiver:
            self = .builtInReceiver
        case .builtInSpeaker:
            self = .builtInSpeaker
        case .usbAudio:
            self = .usbAudio
        default:
            let raw = port.rawValue.lowercased()
            if raw.contains("bluetooth")
                || raw.contains("headphone")
                || raw.contains("headset")
                || raw.contains("hearing") {
                self = .external
            } else {
                self = .other
            }
        }
    }
}
