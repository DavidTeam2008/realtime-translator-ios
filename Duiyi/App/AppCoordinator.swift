import SwiftUI

@MainActor
@Observable
final class AppCoordinator {
    var path = NavigationPath()

    func open(_ route: AppRoute) {
        path.append(route)
    }

    func popToHome() {
        path = NavigationPath()
    }

    func pop() {
        guard !path.isEmpty else { return }
        path.removeLast()
    }

    func replaceModule(_ feature: FeatureID) {
        path = NavigationPath()
        path.append(feature.route)
    }

    func showEndedTask(_ id: UUID) {
        path = NavigationPath()
        path.append(AppRoute.history)
        path.append(AppRoute.taskDetail(id))
    }
}

extension FeatureID {
    var route: AppRoute {
        switch self {
        case .faceToFace: return .conversation
        case .simultaneous: return .interpretation
        case .meeting: return .meeting
        }
    }
}
