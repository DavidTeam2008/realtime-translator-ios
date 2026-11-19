import CoreGraphics

/// Pure decision logic for the leading-edge swipe-back gesture.
enum EdgeSwipeBackPolicy {
    static let edgeWidth: CGFloat = 24
    static let minimumHorizontalTranslation: CGFloat = 60
    static let maximumVerticalDrift: CGFloat = 80

    static func shouldPop(
        hasPreviousPage: Bool,
        startLocation: CGPoint,
        translation: CGSize
    ) -> Bool {
        guard hasPreviousPage else { return false }
        guard startLocation.x >= 0, startLocation.x <= edgeWidth else { return false }
        guard translation.width >= minimumHorizontalTranslation else { return false }
        guard abs(translation.height) < translation.width else { return false }
        guard abs(translation.height) <= maximumVerticalDrift else { return false }
        return true
    }
}
