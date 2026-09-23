import AVFAudio
import Foundation
import os

actor AudioEngineCapturer: AudioCapturing {
    // Lazy to keep launch fast: AVAudioEngine() + sharedInstance() touch
    // AVFoundation/IOKit and audio hardware. Created on first start(), not init.
    private var engine: AVAudioEngine?
    private var session: AVAudioSession?
    private var continuation: AsyncStream<SendablePCMBuffer>.Continuation?

    func start() async throws -> AsyncStream<SendablePCMBuffer> {
        await stop()

        let session = AVAudioSession.sharedInstance()
        self.session = session
        try session.setActive(true, options: .notifyOthersOnDeactivation)

        let engine = AVAudioEngine()
        self.engine = engine

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
        if let engine, engine.isRunning {
            engine.stop()
            engine.inputNode.removeTap(onBus: 0)
        }
        if let session {
            do {
                try session.setActive(false, options: .notifyOthersOnDeactivation)
            } catch {
                DuiyiLog.audio.error("Failed to deactivate audio session: \(error.localizedDescription, privacy: .public)")
            }
        }
        // Release hardware-backed objects immediately so backgrounded app drops them.
        self.engine = nil
        self.session = nil
    }
}
