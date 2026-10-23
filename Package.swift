// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "RedactGov",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .library(
            name: "RedactGovKit",
            targets: ["RedactGovKit"]
        ),
        .executable(
            name: "RedactGovApp",
            targets: ["RedactGovApp"]
        )
    ],
    targets: [
        .target(
            name: "RedactGovKit",
            path: "Sources/RedactGovKit",
            linkerSettings: [
                .linkedLibrary("sqlite3"),
                .linkedFramework("PDFKit"),
                .linkedFramework("Vision"),
                .linkedFramework("AppKit")
            ]
        ),
        .executableTarget(
            name: "RedactGovApp",
            dependencies: ["RedactGovKit"],
            path: "Sources/RedactGovApp",
            linkerSettings: [
                .linkedFramework("SwiftUI"),
                .linkedFramework("PDFKit"),
                .linkedFramework("AppKit")
            ]
        )
    ]
)
