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
        _userToPeer = State(initialValue: Self.makeConfig(from: userLanguage, to: peerLanguage))
        _peerToUser = State(initialValue: Self.makeConfig(from: peerLanguage, to: userLanguage))
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

    private static func makeConfig(from: AppLanguage, to: AppLanguage) -> TranslationSession.Configuration {
        TranslationSession.Configuration(
            source: from.localeLanguage,
            target: to.localeLanguage,
            preferredStrategy: .lowLatency
        )
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
    let onFinished: @MainActor (Result<Void, Error>) -> Void

    @State private var userToPeer: TranslationSession.Configuration
    @State private var peerToUser: TranslationSession.Configuration
    @State private var preparedPairs: Set<String> = []

    init(
        userLanguage: AppLanguage,
        peerLanguage: AppLanguage,
        shouldPrepare: Bool,
        onFinished: @escaping @MainActor (Result<Void, Error>) -> Void
    ) {
        self.userLanguage = userLanguage
        self.peerLanguage = peerLanguage
        self.shouldPrepare = shouldPrepare
        self.onFinished = onFinished
        _userToPeer = State(initialValue: Self.makeConfig(from: userLanguage, to: peerLanguage))
        _peerToUser = State(initialValue: Self.makeConfig(from: peerLanguage, to: userLanguage))
    }

    var body: some View {
        Color.clear
            .frame(width: 0, height: 0)
            .accessibilityHidden(true)
            .translationTask(userToPeer) { session in
                guard shouldPrepare else { return }
                do {
                    try await session.prepareTranslation()
                    await markPrepared("user-to-peer")
                } catch {
                    await onFinished(.failure(error))
                }
            }
            .translationTask(peerToUser) { session in
                guard shouldPrepare else { return }
                do {
                    try await session.prepareTranslation()
                    await markPrepared("peer-to-user")
                } catch {
                    await onFinished(.failure(error))
                }
            }
            .onChange(of: shouldPrepare) { _, prepare in
                guard prepare else { return }
                preparedPairs = []
                userToPeer.invalidate()
                peerToUser.invalidate()
            }
    }

    @MainActor
    private func markPrepared(_ pair: String) {
        preparedPairs.insert(pair)
        if preparedPairs.count == 2 {
            onFinished(.success(()))
        }
    }

    private static func makeConfig(from: AppLanguage, to: AppLanguage) -> TranslationSession.Configuration {
        TranslationSession.Configuration(
            source: from.localeLanguage,
            target: to.localeLanguage,
            preferredStrategy: .lowLatency
        )
    }
}
