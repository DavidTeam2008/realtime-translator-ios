import UIKit

@MainActor
enum ScreenSafeArea {
    static var top: CGFloat {
        inset.top > 0 ? inset.top : 54
    }

    static var bottom: CGFloat {
        inset.bottom > 0 ? inset.bottom : 20
    }

    private static var inset: UIEdgeInsets {
        let scenes = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
        let window = scenes
            .flatMap { $0.windows }
            .first { $0.isKeyWindow }
            ?? scenes.first?.windows.first
        return window?.safeAreaInsets ?? .zero
    }
}
