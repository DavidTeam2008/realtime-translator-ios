@preconcurrency import Translation
import SwiftUI

struct TranslationHostView: View {
    let userLanguage: AppLanguage
    let peerLanguage: AppLanguage
    let job: TranslationJob?
    let onSuccess: @MainActor (TranslationJob, String) -> Void
    let onFailure: @MainActor (TranslationJob, Error) -> Void

    @State private var userToPeer: TranslationSession.Configuration
    @State private var peerToUser: TranslationSession.Configuration
    @State private var userJobs = TranslationJobBridge()
    @State private var peerJobs = TranslationJobBridge()

    init(
        userLanguage: AppLanguage,
        peerLanguage: AppLanguage,
        job: TranslationJob?,
        onSuccess: @escaping @MainActor (TranslationJob, String) -> Void,
        onFailure: @escaping @MainActor (TranslationJob, Error) -> Void
    ) {
        self.userLanguage = userLanguage
        self.peerLanguage = peerLanguage
        self.job = job
        self.onSuccess = onSuccess
        self.onFailure = onFailure
        _userToPeer = State(initialValue: translationConfiguration(from: userLanguage, to: peerLanguage))
        _peerToUser = State(initialValue: translationConfiguration(from: peerLanguage, to: userLanguage))
    }

    var body: some View {
        Color.clear
            .frame(width: 0, height: 0)
            .accessibilityHidden(true)
            .translationTask(userToPeer) { session in
                await pump(session: session, jobs: userJobs)
            }
            .translationTask(peerToUser) { session in
                await pump(session: session, jobs: peerJobs)
            }
            .onChange(of: job) { _, newJob in
                submit(newJob)
            }
            .onAppear {
                submit(job)
            }
    }

    private func submit(_ job: TranslationJob?) {
        guard let job else { return }
        if job.source == userLanguage {
            userJobs.yield(job)
        } else if job.source == peerLanguage {
            peerJobs.yield(job)
        }
    }

    private func pump(session: TranslationSession, jobs: TranslationJobBridge) async {
        for await job in jobs.stream() {
            let text = job.text.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !text.isEmpty else { continue }
            do {
                let response = try await session.translate(text)
                await onSuccess(job, response.targetText)
            } catch {
                await onFailure(job, error)
            }
        }
    }
}

struct OneWayTranslationHostView: View {
    let sourceLanguage: AppLanguage
    let targetLanguage: AppLanguage
    let job: TranslationJob?
    let onSuccess: @MainActor (TranslationJob, String) -> Void
    let onFailure: @MainActor (TranslationJob, Error) -> Void

    @State private var configuration: TranslationSession.Configuration
    @State private var jobs = TranslationJobBridge()

    init(
        sourceLanguage: AppLanguage,
        targetLanguage: AppLanguage,
        job: TranslationJob?,
        onSuccess: @escaping @MainActor (TranslationJob, String) -> Void,
        onFailure: @escaping @MainActor (TranslationJob, Error) -> Void
    ) {
        self.sourceLanguage = sourceLanguage
        self.targetLanguage = targetLanguage
        self.job = job
        self.onSuccess = onSuccess
        self.onFailure = onFailure
        _configuration = State(initialValue: translationConfiguration(from: sourceLanguage, to: targetLanguage))
    }

    var body: some View {
        Color.clear
            .frame(width: 0, height: 0)
            .accessibilityHidden(true)
            .translationTask(configuration) { session in
                for await job in jobs.stream() {
                    let text = job.text.trimmingCharacters(in: .whitespacesAndNewlines)
                    guard !text.isEmpty else { continue }
                    do {
                        let response = try await session.translate(text)
                        await onSuccess(job, response.targetText)
                    } catch {
                        await onFailure(job, error)
                    }
                }
            }
            .onChange(of: job) { _, newJob in
                submit(newJob)
            }
            .onAppear {
                submit(job)
            }
    }

    private func submit(_ job: TranslationJob?) {
        guard let job else { return }
        guard job.source == sourceLanguage, job.target == targetLanguage else { return }
        jobs.yield(job)
    }
}

final class TranslationJobBridge: @unchecked Sendable {
    private let lock = NSLock()
    private var continuation: AsyncStream<TranslationJob>.Continuation?
    private var pending: TranslationJob?

    func stream() -> AsyncStream<TranslationJob> {
        AsyncStream { continuation in
            lock.lock()
            self.continuation = continuation
            if let pending {
                continuation.yield(pending)
                self.pending = nil
            }
            lock.unlock()
            continuation.onTermination = { [weak self] _ in
                self?.lock.lock()
                self?.continuation = nil
                self?.lock.unlock()
            }
        }
    }

    func yield(_ job: TranslationJob) {
        lock.lock()
        defer { lock.unlock() }
        if let continuation {
            continuation.yield(job)
        } else {
            pending = job
        }
    }
}

struct TranslationPrepareHost: View {
    let userLanguage: AppLanguage
    let peerLanguage: AppLanguage
    let shouldPrepare: Bool
    var oneWay = false
    let onFinished: @MainActor (Result<Void, Error>) -> Void

    @State private var userToPeer: TranslationSession.Configuration
    @State private var peerToUser: TranslationSession.Configuration
    @State private var preparedPairs: Set<String> = []

    init(
        userLanguage: AppLanguage,
        peerLanguage: AppLanguage,
        shouldPrepare: Bool,
        oneWay: Bool = false,
        onFinished: @escaping @MainActor (Result<Void, Error>) -> Void
    ) {
        self.userLanguage = userLanguage
        self.peerLanguage = peerLanguage
        self.shouldPrepare = shouldPrepare
        self.oneWay = oneWay
        self.onFinished = onFinished
        _userToPeer = State(initialValue: translationConfiguration(from: userLanguage, to: peerLanguage))
        _peerToUser = State(initialValue: translationConfiguration(from: peerLanguage, to: userLanguage))
    }

    var body: some View {
        prepareRoot
            .onChange(of: shouldPrepare) { _, prepare in
                guard prepare else { return }
                preparedPairs = []
                userToPeer.invalidate()
                if !oneWay {
                    peerToUser.invalidate()
                }
            }
    }

    @ViewBuilder
    private var prepareRoot: some View {
        if oneWay {
            Color.clear
                .frame(width: 0, height: 0)
                .accessibilityHidden(true)
                .translationTask(userToPeer) { session in
                    await prepare(session, pair: "forward")
                }
        } else {
            Color.clear
                .frame(width: 0, height: 0)
                .accessibilityHidden(true)
                .translationTask(userToPeer) { session in
                    await prepare(session, pair: "user-to-peer")
                }
                .translationTask(peerToUser) { session in
                    await prepare(session, pair: "peer-to-user")
                }
        }
    }

    private func prepare(_ session: TranslationSession, pair: String) async {
        guard shouldPrepare else { return }
        do {
            try await session.prepareTranslation()
            await markPrepared(pair)
        } catch {
            await onFinished(.failure(error))
        }
    }

    @MainActor
    private func markPrepared(_ pair: String) {
        preparedPairs.insert(pair)
        let required = oneWay ? 1 : 2
        if preparedPairs.count >= required {
            onFinished(.success(()))
        }
    }
}

private func translationConfiguration(from: AppLanguage, to: AppLanguage) -> TranslationSession.Configuration {
    TranslationSession.Configuration(
        source: from.localeLanguage,
        target: to.localeLanguage,
        preferredStrategy: .lowLatency
    )
}
