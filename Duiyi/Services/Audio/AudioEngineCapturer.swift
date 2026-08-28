import AVFAudio
import Foundation
import os

actor AudioEngineCapturer: AudioCapturing {
    private let engine = AVAudioEngine()
    private let session = AVAudioSession.sharedInstance()
    private var continuation: AsyncStream<SendablePCMBuffer>.Continuation?

    func start() async throws -> AsyncStream<SendablePCMBuffer> {
        await stop()

        try session.setCategory(.record, mode: .measurement, options: [.duckOthers, .allowBluetoothHFP])
        try session.setActive(true, options: .notifyOthersOnDeactivation)

        let (stream, continuation) = AsyncStream<SendablePCMBuffer>.makeStream()
        self.continuation = continuation

        let inputNode = engine.inputNode
        let format = inputNode.outputFormat(forBus: 0)
        inputNode.removeTap(onBus: 0)
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in
            guard let copy = BufferConverter.copy(buffer) else { return }
            continuation.yield(SendablePCMBuffer(buffer: copy))
        }

        engine.prepare()
        try engine.start()
        DuiyiLog.audio.info("Audio engine started, format \(Int(format.sampleRate), privacy: .public)Hz")
        return stream
    }

    func stop() async {
        continuation?.finish()
        continuation = nil
        if engine.isRunning {
            engine.stop()
        }
        engine.inputNode.removeTap(onBus: 0)
        do {
            try session.setActive(false, options: .notifyOthersOnDeactivation)
        } catch {
            DuiyiLog.audio.error("Failed to deactivate audio session: \(error.localizedDescription, privacy: .public)")
        }
    }
}
