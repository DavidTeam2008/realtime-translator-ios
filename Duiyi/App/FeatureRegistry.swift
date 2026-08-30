import Foundation

enum FeatureRegistry {
    static let modules: [FeatureDescriptor] = [
        FeatureDescriptor(
            id: .faceToFace,
            title: { Copy.modeFaceToFace(for: $0) },
            subtitle: { Copy.homeFaceToFaceSubtitle(for: $0) },
            symbolName: "person.2.fill"
        ),
        FeatureDescriptor(
            id: .simultaneous,
            title: { Copy.modeSimultaneous(for: $0) },
            subtitle: { Copy.homeSimultaneousSubtitle(for: $0) },
            symbolName: "waveform"
        ),
        FeatureDescriptor(
            id: .meeting,
            title: { Copy.modeMeeting(for: $0) },
            subtitle: { Copy.homeMeetingSubtitle(for: $0) },
            symbolName: "text.alignleft"
        )
    ]

    static var visible: [FeatureDescriptor] { modules }
}
