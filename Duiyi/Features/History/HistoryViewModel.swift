import Foundation

@MainActor
@Observable
final class HistoryViewModel {
    private let store: any TaskStore

    var tasks: [TaskSession] = []
    var filter: FeatureID?

    init(store: any TaskStore) {
        self.store = store
    }

    func reload() async {
        tasks = await store.list(filter: filter)
    }

    func setFilter(_ filter: FeatureID?) async {
        self.filter = filter
        await reload()
    }

    func delete(id: UUID) async {
        try? await store.delete(id: id)
        await reload()
    }
}
