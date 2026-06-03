// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "OneNumberTodayPhone",
    platforms: [
        .iOS(.v17),
        .macOS(.v14)
    ],
    products: [
        .library(
            name: "OneNumberPhoneKit",
            targets: ["OneNumberPhoneKit"]
        )
    ],
    targets: [
        .target(
            name: "OneNumberPhoneKit",
            path: "prototypes/iphone-widget/swiftui",
            exclude: [
                "LunchboxWidget.swift",
                "LunchboxWidgetBundle.swift",
                "LunchboxWidgetIntent.swift",
                "OneNumberTodayApp.swift"
            ],
            sources: [
                "LunchboxWidgetModels.swift",
                "OneNumberAppIntents.swift",
                "OneNumberSnapshotStore.swift",
                "OneNumberTodayView.swift"
            ]
        ),
        .testTarget(
            name: "OneNumberPhoneKitTests",
            dependencies: ["OneNumberPhoneKit"],
            path: "tests/OneNumberPhoneKitTests"
        )
    ]
)
