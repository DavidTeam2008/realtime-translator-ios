import SwiftUI

struct HistoryView: View {
    @Environment(AppEnvironment.self) private var environment
    @Environment(AppCoordinator.self) private var coordinator
    @Bindable var viewModel: HistoryViewModel

    private var language: AppLanguage { environment.preferences.userLanguage }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            ModuleChrome(
                title: Copy.historyTitle(for: language),
                language: language,
                onHome: { coordinator.popToHome() },
                onHistory: {}
            )

            filterRow
                .padding(.horizontal, Tokens.horizontalPadding)
                .padding(.bottom, 8)

            if viewModel.tasks.isEmpty {
                Text(Copy.historyEmpty(for: language))
                    .font(.body)
                    .foregroundStyle(Tokens.textSecondary)
                    .padding(.horizontal, Tokens.horizontalPadding)
                    .padding(.top, 24)
                Spacer()
            } else {
                List {
                    ForEach(viewModel.tasks) { task in
                        Button {
                            coordinator.open(.taskDetail(task.id))
                        } label: {
                            HistoryRow(task: task, language: language)
                        }
                        .listRowBackground(Tokens.userPane)
                        .listRowSeparatorTint(Tokens.sheetChip)
                        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                            Button(role: .destructive) {
                                Task { await viewModel.delete(id: task.id) }
                            } label: {
                                Text(Copy.delete(for: language))
                            }
                        }
                    }
                }
                .listStyle(.plain)
                .scrollContentBackground(.hidden)
            }
        }
        .background(Tokens.canvas.ignoresSafeArea())
        .toolbar(.hidden, for: .navigationBar)
        .task {
            await viewModel.reload()
        }
        .preferredColorScheme(.dark)
    }

    private var filterRow: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                filterChip(title: Copy.filterAll(for: language), selected: viewModel.filter == nil) {
                    Task { await viewModel.setFilter(nil) }
                }
                ForEach(FeatureID.allCases, id: \.self) { feature in
                    filterChip(title: Copy.featureTitle(feature, for: language), selected: viewModel.filter == feature) {
                        Task { await viewModel.setFilter(feature) }
                    }
                }
            }
        }
    }

    private func filterChip(title: String, selected: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .font(.footnote.weight(selected ? .semibold : .regular))
                .foregroundStyle(selected ? Color(hex: 0x1C1915) : Tokens.textPrimary)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(selected ? Tokens.listen : Tokens.sheetChip, in: Capsule())
        }
        .buttonStyle(.plain)
    }
}

#Preview("History empty") {
    HistoryPreview.empty
}

@MainActor
enum HistoryPreview {
    static var empty: some View {
        let store = InMemoryTaskStore()
        let preferences = PreferencesStore(defaults: UserDefaults(suiteName: "duiyi.history.preview") ?? .standard)
        preferences.userLanguage = .zhHans
        return HistoryView(viewModel: HistoryViewModel(store: store))
            .environment(AppEnvironment(preferences: preferences, taskStore: store))
            .environment(AppCoordinator())
    }
}
