import AppKit
import PDFKit
import RedactGovKit
import SwiftUI
import UniformTypeIdentifiers

@main
struct RedactGovMacApp: App {
    @StateObject private var viewModel = AppViewModel()

    init() {
        if CommandLine.arguments.contains("--self-test") {
            Self.runHeadlessSelfTestAndExit()
        }
        NSApplication.shared.setActivationPolicy(.regular)
    }

    private static func runHeadlessSelfTestAndExit() -> Never {
        let semaphore = DispatchSemaphore(value: 0)
        nonisolated(unsafe) var exitCode: Int32 = 0

        Task.detached {
            do {
                // 1. Verify SQLite CaseIndexStore
                let tempDir = FileManager.default.temporaryDirectory
                    .appendingPathComponent(UUID().uuidString, isDirectory: true)
                try FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)
                defer { try? FileManager.default.removeItem(at: tempDir) }

                let dbURL = tempDir.appendingPathComponent("selftest_docket.sqlite3")
                let store = CaseIndexStore(databaseURL: dbURL)
                let dummyPlan = RedactionPlanPayload(
                    documentName: "selftest_foia.pdf",
                    totalPages: 1,
                    entities: [
                        RedactionEntityItem(
                            text: "123-45-6789",
                            category: "ssn",
                            statuteCode: "Va. Code § 2.2-3808.1",
                            confidence: 0.99,
                            pageNumber: 1,
                            boundingBoxes: [PDFBoundingBox(page: 1, x0: 72, y0: 680, x1: 160, y1: 694)],
                            tier: "tier1_deterministic",
                            approved: true
                        )
                    ]
                )
                let dummyResult = RedactionResultPayload(
                    success: true,
                    inputPath: "/tmp/selftest_foia.pdf",
                    outputPath: "/tmp/selftest_foia_sanitized.pdf",
                    certificatePath: "/tmp/selftest_foia_cert.pdf",
                    redactedCount: 1,
                    totalPages: 1,
                    executionTimeSeconds: 0.05,
                    verificationPassed: true
                )
                store.recordRedactionRun(plan: dummyPlan, result: dummyResult)
                let entries = store.searchDocket(query: "3808.1")
                guard entries.count == 1, entries.first?.entityText == "123-45-6789" else {
                    throw WorkerError.malformedResponse("CaseIndexStore self-test failed.")
                }

                // 2. Verify WorkerClient <-> Contents/Helpers/redactgov-worker bridge (even when cwd == "/")
                let rootURL = WorkspaceResolver.resolveWorkspaceRoot()
                guard rootURL.path != "/" else {
                    throw WorkerError.malformedResponse("WorkspaceResolver returned '/' instead of valid root.")
                }
                let client = WorkerClient(workspaceRoot: rootURL)
                let samplePDF = rootURL.appendingPathComponent("data/synthetic_corpus/01_police_incident_report.pdf")
                if FileManager.default.fileExists(atPath: samplePDF.path) {
                    let inspection = try await client.inspectDocument(pdfURL: samplePDF)
                    guard inspection.totalPages >= 1 else {
                        throw WorkerError.malformedResponse("Expected >= 1 page in synthetic sample.")
                    }
                    let outDir = WorkspaceResolver.resolveOutputDirectory(for: samplePDF, workspaceRoot: rootURL)
                    let outPDF = outDir.appendingPathComponent("selftest_01_police_sanitized.pdf")
                    let certPDF = outDir.appendingPathComponent("selftest_01_police_cert.pdf")
                    let quickRes = try await client.quickRedact(
                        pdfURL: samplePDF,
                        outputURL: outPDF,
                        certificateURL: certPDF,
                        profile: .publicFoia,
                        coordinatePolicy: .all
                    )
                    guard quickRes.result.success else {
                        throw WorkerError.malformedResponse("quickRedact failed in self-test.")
                    }
                    try? FileManager.default.removeItem(atPath: quickRes.result.outputPath)
                    if let cPath = quickRes.result.certificatePath {
                        try? FileManager.default.removeItem(atPath: cPath)
                    }
                    await client.suspendWorker()
                }

                print("REDACTGOV_NATIVE_SELFTEST_OK")
            } catch {
                fputs("REDACTGOV_NATIVE_SELFTEST_FAILED: \(error)\n", stderr)
                exitCode = 1
            }
            semaphore.signal()
        }

        semaphore.wait()
        Foundation.exit(exitCode)
    }

    var body: some Scene {
        WindowGroup("Blackmarker Studio", id: "studio") {
            SovereignStudioView(viewModel: viewModel)
                .frame(minWidth: 1180, minHeight: 740)
                .preferredColorScheme(.dark)
        }
        .defaultSize(width: 1380, height: 860)

        // Menu Bar Quick-Scrub Droplet
        MenuBarExtra("Blackmarker Studio", systemImage: "highlighter") {
            MenuBarDropletView(viewModel: viewModel)
                .frame(width: 370)
                .preferredColorScheme(.dark)
        }
        .menuBarExtraStyle(.window)
    }
}

// MARK: - Menu Bar Quick-Scrub Droplet

struct MenuBarDropletView: View {
    @ObservedObject var viewModel: AppViewModel
    @Environment(\.openWindow) private var openWindow

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 8) {
                Image(systemName: "highlighter")
                    .font(.title2)
                    .foregroundStyle(Color(red: 0.22, green: 0.74, blue: 0.98))
                VStack(alignment: .leading, spacing: 2) {
                    Text("Blackmarker Studio")
                        .font(.headline)
                        .foregroundStyle(.white)
                    Text("FOIA • HIPAA • PCI DSS • GLBA • Air-Gapped")
                        .font(.caption)
                        .foregroundStyle(Color(white: 0.78))
                }
                Spacer()
                WorkerBadgeView(state: viewModel.workerState)
            }

            Divider().overlay(Color(white: 0.28))

            VStack(alignment: .leading, spacing: 6) {
                Text("Compliance Release Profile")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(Color(white: 0.80))
                Picker("Release Profile", selection: $viewModel.releaseProfile) {
                    ForEach(ReleaseProfileChoice.allCases) { profile in
                        Text(profile.title).tag(profile)
                    }
                }
                .labelsHidden()
                .pickerStyle(.menu)
                .onChange(of: viewModel.releaseProfile) { _, newProfile in
                    viewModel.applyProfileDefaults(newProfile)
                }

                HStack(spacing: 6) {
                    ForEach(DataDomainChoice.allCases) { domain in
                        DomainTogglePill(
                            domain: domain,
                            isActive: viewModel.isDomainActive(domain),
                            action: { viewModel.toggleDomain(domain) }
                        )
                    }
                }
                .padding(.top, 2)
            }

            // Drag & Drop Sanitization Zone
            VStack(spacing: 8) {
                Image(systemName: viewModel.isDropTargeted ? "arrow.down.doc.fill" : "doc.badge.gearshape")
                    .font(.system(size: 26))
                    .foregroundStyle(
                        viewModel.isDropTargeted
                            ? Color(red: 0.25, green: 0.90, blue: 0.65)
                            : Color(red: 0.48, green: 0.76, blue: 1.0)
                    )
                Text(viewModel.isBusy ? "Sanitizing PDF Stream..." : "Drop PDF to Scrub & Certify")
                    .font(.callout.weight(.semibold))
                    .foregroundStyle(.white)
                Text("Excises Tj/TJ glyphs, wipes XMP, and issues FOIA certificate")
                    .font(.caption2)
                    .foregroundStyle(Color(white: 0.75))
                    .multilineTextAlignment(.center)
                Button("Select PDF File...") {
                    viewModel.openFilePickerAndAnalyze()
                    openWindow(id: "studio")
                    NSApplication.shared.activate(ignoringOtherApps: true)
                }
                .buttonStyle(.borderedProminent)
                .tint(Color(red: 0.14, green: 0.52, blue: 0.88))
                .controlSize(.small)
                .disabled(viewModel.isBusy)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .padding(.horizontal, 10)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .fill(viewModel.isDropTargeted ? Color(red: 0.12, green: 0.30, blue: 0.24) : Color(white: 0.14))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .strokeBorder(
                        viewModel.isDropTargeted
                            ? Color(red: 0.30, green: 0.92, blue: 0.68)
                            : Color(white: 0.32),
                        style: StrokeStyle(lineWidth: 1.5, dash: [5, 3])
                    )
            )
            .onDrop(of: [.fileURL], isTargeted: $viewModel.isDropTargeted) { providers in
                handleDrop(providers: providers)
            }

            if let result = viewModel.lastResult {
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Image(systemName: result.verificationPassed ? "checkmark.seal.fill" : "exclamationmark.triangle.fill")
                            .foregroundStyle(
                                result.verificationPassed
                                    ? Color(red: 0.25, green: 0.90, blue: 0.60)
                                    : Color(red: 1.0, green: 0.75, blue: 0.25)
                            )
                        Text("Redacted \(result.redactedCount) items (\(String(format: "%.2f", result.executionTimeSeconds))s)")
                            .font(.caption.weight(.bold))
                            .foregroundStyle(.white)
                        Spacer()
                        Button("Reveal") {
                            NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath: result.outputPath)])
                        }
                        .controlSize(.mini)
                    }
                    Text(URL(fileURLWithPath: result.outputPath).lastPathComponent)
                        .font(.caption2)
                        .foregroundStyle(Color(white: 0.78))
                        .lineLimit(1)
                        .truncationMode(.middle)
                }
                .padding(8)
                .background(RoundedRectangle(cornerRadius: 8).fill(Color(white: 0.16)))
            }

            Divider().overlay(Color(white: 0.28))

            HStack(spacing: 8) {
                Button {
                    openWindow(id: "studio")
                    NSApplication.shared.activate(ignoringOtherApps: true)
                } label: {
                    Label("Open Studio", systemImage: "macwindow")
                }
                .buttonStyle(.bordered)
                .controlSize(.small)

                Button {
                    Task { await viewModel.suspendEphemeralWorker() }
                } label: {
                    Label("Free RAM", systemImage: "memorychip")
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .help("Terminate the ephemeral Gemma 4 E4B worker to reclaim unified memory immediately")

                Spacer()

                Button("Quit") {
                    NSApplication.shared.terminate(nil)
                }
                .buttonStyle(.plain)
                .font(.caption)
                .foregroundStyle(Color(white: 0.75))
            }
        }
        .padding(14)
        .background(Color(red: 0.09, green: 0.10, blue: 0.12))
    }

    private func handleDrop(providers: [NSItemProvider]) -> Bool {
        guard let provider = providers.first(where: { $0.hasItemConformingToTypeIdentifier(UTType.fileURL.identifier) }) else {
            return false
        }
        provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { item, _ in
            guard let data = item as? Data,
                  let url = URL(dataRepresentation: data, relativeTo: nil),
                  url.pathExtension.lowercased() == "pdf" else {
                return
            }
            Task { @MainActor in
                await viewModel.quickDropSanitize(pdfURL: url)
            }
        }
        return true
    }
}

// MARK: - Sovereign Studio Main Window (2-Column NavigationSplitView + Integrated Inspector)

struct SovereignStudioView: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        NavigationSplitView {
            StudioSidebarView(viewModel: viewModel)
                .navigationSplitViewColumnWidth(min: 270, ideal: 295, max: 340)
        } detail: {
            VStack(spacing: 0) {
                // Main Workspace: Center PDF Canvas + Right Statutory Inspector
                HStack(spacing: 0) {
                    StudioCenterCanvasView(viewModel: viewModel)
                        .frame(minWidth: 540, maxWidth: .infinity, maxHeight: .infinity)
                        .layoutPriority(1)

                    if viewModel.isInspectorVisible {
                        Rectangle()
                            .fill(Color(white: 0.22))
                            .frame(width: 1)

                        StudioInspectorView(viewModel: viewModel)
                            .frame(width: 380)
                            .frame(maxHeight: .infinity)
                            .transition(.move(edge: .trailing))
                    }
                }

                // Bottom Status & Memory Bar
                StudioFooterStatusBar(viewModel: viewModel)
            }
        }
        .toolbar {
            ToolbarItemGroup(placement: .navigation) {
                Button {
                    viewModel.openFilePickerAndAnalyze()
                } label: {
                    Label("Open PDF", systemImage: "folder.badge.plus")
                }
                .help("Open a PDF document for FOIA redaction review")
            }

            ToolbarItemGroup(placement: .primaryAction) {
                if let url = viewModel.selectedPDFURL {
                    Button {
                        viewModel.previewMode = .annotatedSource
                        viewModel.isManualDrawMode.toggle()
                    } label: {
                        Label(
                            viewModel.isManualDrawMode ? "Drawing Blackmarker..." : "Draw Redaction",
                            systemImage: viewModel.isManualDrawMode ? "highlighter" : "rectangle.dashed"
                        )
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(
                        viewModel.isManualDrawMode
                            ? Color(red: 0.08, green: 0.65, blue: 0.92)
                            : Color(white: 0.26)
                    )
                    .help("Drag a rectangle directly on the PDF (or hold Shift + Drag anytime) to add a manual Blackmarker redaction")

                    Button {
                        Task { await viewModel.loadAndAnalyze(pdfURL: url) }
                    } label: {
                        Label("Re-Scan", systemImage: "arrow.trianglehead.2.clockwise")
                    }
                    .disabled(viewModel.isBusy)
                    .help("Re-run Tier 1 Deterministic + Tier 2 Gemma 4 E4B analysis")
                }

                Button {
                    viewModel.isCertificateSheetPresented = true
                } label: {
                    Label("Certificate Template", systemImage: "checkmark.seal.text.page")
                }
                .help("Customize the Redaction & Compliance Certificate template (FOIA, HIPAA, PCI DSS, GLBA, FRCP 5.2, SOC 2)")

                Button {
                    Task { await viewModel.executeCurrentPlan() }
                } label: {
                    Label("Sanitize & Certify", systemImage: "checkmark.shield.fill")
                }
                .buttonStyle(.borderedProminent)
                .tint(Color(red: 0.14, green: 0.68, blue: 0.44))
                .disabled(viewModel.currentPlan == nil || viewModel.isBusy)
                .help("Execute PikePDF stream surgery and issue Compliance Redaction Certificate")

                Button {
                    withAnimation(.easeInOut(duration: 0.18)) {
                        viewModel.isInspectorVisible.toggle()
                    }
                } label: {
                    Label("Toggle Inspector", systemImage: "sidebar.trailing")
                }
                .help("Show or hide the Redaction Plan inspector")
            }
        }
        .sheet(isPresented: $viewModel.isCertificateSheetPresented) {
            CertificateTemplateEditorSheet(viewModel: viewModel)
        }
    }
}

// MARK: - Left Sidebar (Scrollable Cards - Zero Truncation)

struct StudioSidebarView: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                // 1. Primary Action + Sample Dockets
                SidebarCard(title: "DOCUMENTS & SAMPLES", icon: "doc.on.doc.fill") {
                    Button {
                        viewModel.openFilePickerAndAnalyze()
                    } label: {
                        HStack(spacing: 8) {
                            Image(systemName: "plus.rectangle.on.folder.fill")
                            Text("Open Custom PDF...")
                                .font(.callout.weight(.semibold))
                            Spacer()
                        }
                        .padding(.vertical, 6)
                        .padding(.horizontal, 10)
                        .frame(maxWidth: .infinity)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(Color(red: 0.15, green: 0.48, blue: 0.85))
                        )
                        .foregroundStyle(.white)
                    }
                    .buttonStyle(.plain)
                    .disabled(viewModel.isBusy)

                    if !viewModel.syntheticSamples.isEmpty {
                        Text("Multi-Sector Synthetic Corpus")
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(Color(white: 0.65))
                            .padding(.top, 4)

                        VStack(spacing: 4) {
                            ForEach(viewModel.syntheticSamples, id: \.self) { sampleURL in
                                let isSelected = viewModel.selectedPDFURL?.standardizedFileURL == sampleURL.standardizedFileURL
                                Button {
                                    Task { await viewModel.loadAndAnalyze(pdfURL: sampleURL) }
                                } label: {
                                    HStack(spacing: 8) {
                                        Image(systemName: isSelected ? "doc.fill" : "doc.text")
                                            .font(.caption)
                                            .foregroundStyle(
                                                isSelected
                                                    ? Color(red: 0.40, green: 0.82, blue: 1.0)
                                                    : Color(white: 0.72)
                                            )
                                        VStack(alignment: .leading, spacing: 1) {
                                            Text(humanReadableSampleName(sampleURL))
                                                .font(.caption.weight(isSelected ? .bold : .medium))
                                                .foregroundStyle(.white)
                                                .lineLimit(1)
                                            Text(sampleURL.lastPathComponent)
                                                .font(.system(size: 10, design: .monospaced))
                                                .foregroundStyle(Color(white: 0.62))
                                                .lineLimit(1)
                                                .truncationMode(.middle)
                                        }
                                        Spacer()
                                        if isSelected {
                                            Circle()
                                                .fill(Color(red: 0.35, green: 0.85, blue: 0.65))
                                                .frame(width: 7, height: 7)
                                        }
                                    }
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 6)
                                    .background(
                                        RoundedRectangle(cornerRadius: 7)
                                            .fill(
                                                isSelected
                                                    ? Color(red: 0.14, green: 0.25, blue: 0.38)
                                                    : Color(white: 0.14)
                                            )
                                    )
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 7)
                                            .strokeBorder(
                                                isSelected
                                                    ? Color(red: 0.38, green: 0.75, blue: 1.0)
                                                    : Color.clear,
                                                lineWidth: 1
                                            )
                                    )
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }
                }

                // 2. Compliance Policy & A-La-Carte Redaction Scope
                SidebarCard(title: "COMPLIANCE & REDACTION SCOPE", icon: "building.columns.fill") {
                    VStack(alignment: .leading, spacing: 10) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Sector Release Profile")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(Color(white: 0.85))
                            Picker("Release Profile", selection: $viewModel.releaseProfile) {
                                ForEach(ReleaseProfileChoice.allCases) { option in
                                    Text(option.title).tag(option)
                                }
                            }
                            .labelsHidden()
                            .pickerStyle(.menu)
                            .onChange(of: viewModel.releaseProfile) { _, newValue in
                                viewModel.applyProfileDefaults(newValue)
                                if let url = viewModel.selectedPDFURL {
                                    Task { await viewModel.loadAndAnalyze(pdfURL: url) }
                                }
                            }
                            Text(viewModel.releaseProfile.subtitle)
                                .font(.system(size: 11))
                                .foregroundStyle(Color(white: 0.68))
                                .fixedSize(horizontal: false, vertical: true)
                        }

                        Divider().overlay(Color(white: 0.22))

                        VStack(alignment: .leading, spacing: 6) {
                            Text("A-La-Carte Data Domains")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(Color(white: 0.85))
                            HStack(spacing: 6) {
                                ForEach(DataDomainChoice.allCases) { domain in
                                    DomainTogglePill(
                                        domain: domain,
                                        isActive: viewModel.isDomainActive(domain),
                                        action: { viewModel.toggleDomain(domain) }
                                    )
                                }
                            }
                            Text("Toggle Identity (PII), Healthcare (PHI), or Financial (PPI) detectors independently.")
                                .font(.system(size: 10))
                                .foregroundStyle(Color(white: 0.65))
                                .fixedSize(horizontal: false, vertical: true)
                        }

                        Divider().overlay(Color(white: 0.22))

                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text("Certificate Template")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(Color(white: 0.85))
                                Spacer()
                                Button("Customize...") {
                                    viewModel.isCertificateSheetPresented = true
                                }
                                .buttonStyle(.link)
                                .font(.system(size: 11, weight: .semibold))
                            }
                            Text(viewModel.certificateConfig.certificateTitle)
                                .font(.system(size: 10, weight: .bold, design: .monospaced))
                                .foregroundStyle(Color(red: 0.48, green: 0.84, blue: 1.0))
                                .lineLimit(1)
                            Text(viewModel.certificateConfig.agencyName)
                                .font(.system(size: 10))
                                .foregroundStyle(Color(white: 0.68))
                                .lineLimit(1)
                        }

                        Divider().overlay(Color(white: 0.22))

                        VStack(alignment: .leading, spacing: 4) {
                            Text("GPS Coordinate Policy")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(Color(white: 0.85))
                            Picker("GPS Coordinates", selection: $viewModel.coordinatePolicy) {
                                ForEach(CoordinatePolicyChoice.allCases) { option in
                                    Text(option.title).tag(option)
                                }
                            }
                            .labelsHidden()
                            .pickerStyle(.menu)
                            .onChange(of: viewModel.coordinatePolicy) { _, _ in
                                if let url = viewModel.selectedPDFURL {
                                    Task { await viewModel.loadAndAnalyze(pdfURL: url) }
                                }
                            }
                        }

                        Divider().overlay(Color(white: 0.22))

                        Toggle(isOn: $viewModel.autoRepairImperfect) {
                            VStack(alignment: .leading, spacing: 1) {
                                Text("Auto-Heal Imperfect PDFs")
                                    .font(.caption.weight(.medium))
                                    .foregroundStyle(.white)
                                Text("Linearize & repair missing ToUnicode maps")
                                    .font(.system(size: 10))
                                    .foregroundStyle(Color(white: 0.65))
                            }
                        }
                        .toggleStyle(.switch)
                        .controlSize(.small)

                        Toggle(isOn: $viewModel.useAppleVisionOCR) {
                            VStack(alignment: .leading, spacing: 1) {
                                Text("Apple Vision Neural OCR")
                                    .font(.caption.weight(.medium))
                                    .foregroundStyle(.white)
                                Text("Recover bounding boxes on scanned pages")
                                    .font(.system(size: 10))
                                    .foregroundStyle(Color(white: 0.65))
                            }
                        }
                        .toggleStyle(.switch)
                        .controlSize(.small)
                    }
                }

                // 3. Sovereign Engine & Memory Lifecycle
                SidebarCard(title: "EPHEMERAL WORKER ENGINE", icon: "cpu.fill") {
                    HStack(spacing: 8) {
                        WorkerBadgeView(state: viewModel.workerState)
                        Spacer()
                        Button {
                            Task { await viewModel.suspendEphemeralWorker() }
                        } label: {
                            Label("Free RAM", systemImage: "memorychip")
                                .font(.caption.weight(.semibold))
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                    }

                    Text("Spawns on demand over stdio JSON-RPC and auto-unloads Gemma 4 E4B after inactivity.")
                        .font(.system(size: 11))
                        .foregroundStyle(Color(white: 0.68))
                        .fixedSize(horizontal: false, vertical: true)
                }

                // 4. FOIA Docket Index (SQLite)
                SidebarCard(title: "FOIA DOCKET HISTORY", icon: "externaldrive.fill.badge.checkmark") {
                    HStack(spacing: 6) {
                        Image(systemName: "magnifyingglass")
                            .font(.caption)
                            .foregroundStyle(Color(white: 0.65))
                        TextField("Search statute, entity, file...", text: $viewModel.docketSearchQuery)
                            .textFieldStyle(.plain)
                            .font(.caption)
                            .onChange(of: viewModel.docketSearchQuery) { _, _ in
                                viewModel.refreshDocketSearch()
                            }
                        if !viewModel.docketSearchQuery.isEmpty {
                            Button {
                                viewModel.docketSearchQuery = ""
                                viewModel.refreshDocketSearch()
                            } label: {
                                Image(systemName: "xmark.circle.fill")
                                    .font(.caption)
                                    .foregroundStyle(Color(white: 0.65))
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding(.horizontal, 8)
                    .padding(.vertical, 6)
                    .background(RoundedRectangle(cornerRadius: 6).fill(Color(white: 0.10)))
                    .overlay(RoundedRectangle(cornerRadius: 6).strokeBorder(Color(white: 0.25), lineWidth: 1))

                    if viewModel.docketEntries.isEmpty {
                        Text("No sanitized items recorded yet.")
                            .font(.caption)
                            .foregroundStyle(Color(white: 0.62))
                            .padding(.vertical, 4)
                    } else {
                        VStack(spacing: 6) {
                            ForEach(viewModel.docketEntries.prefix(12)) { entry in
                                VStack(alignment: .leading, spacing: 3) {
                                    HStack {
                                        Text(entry.statuteCode)
                                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                                            .foregroundStyle(Color(red: 0.45, green: 0.85, blue: 1.0))
                                        Spacer()
                                        Text("p.\(entry.pageNumber)")
                                            .font(.system(size: 10, weight: .semibold, design: .monospaced))
                                            .foregroundStyle(Color(white: 0.72))
                                    }
                                    Text("\(entry.category.uppercased()): \(entry.entityText)")
                                        .font(.caption.weight(.medium))
                                        .foregroundStyle(.white)
                                        .lineLimit(1)
                                    HStack {
                                        Text(entry.documentName)
                                            .font(.system(size: 10))
                                            .foregroundStyle(Color(white: 0.62))
                                            .lineLimit(1)
                                            .truncationMode(.middle)
                                        Spacer()
                                        Button("Reveal") {
                                            NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath: entry.outputPath)])
                                        }
                                        .buttonStyle(.link)
                                        .font(.system(size: 10, weight: .semibold))
                                    }
                                }
                                .padding(7)
                                .background(RoundedRectangle(cornerRadius: 6).fill(Color(white: 0.13)))
                            }
                        }
                    }
                }
            }
            .padding(12)
        }
        .background(Color(red: 0.09, green: 0.10, blue: 0.12))
    }

    private func humanReadableSampleName(_ url: URL) -> String {
        let stem = url.deletingPathExtension().lastPathComponent
        let cleaned = stem
            .replacingOccurrences(of: "_", with: " ")
            .replacingOccurrences(of: "-", with: " ")
        return cleaned.capitalized
    }
}

struct SidebarCard<Content: View>: View {
    let title: String
    let icon: String
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.caption.weight(.bold))
                    .foregroundStyle(Color(red: 0.42, green: 0.78, blue: 1.0))
                Text(title)
                    .font(.system(size: 11, weight: .bold))
                    .tracking(0.5)
                    .foregroundStyle(Color(white: 0.78))
            }
            content
        }
        .padding(11)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(Color(red: 0.13, green: 0.14, blue: 0.17))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .strokeBorder(Color(white: 0.22), lineWidth: 1)
        )
    }
}

// MARK: - Center PDF Canvas & Responsive Header Bar

struct StudioCenterCanvasView: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        VStack(spacing: 0) {
            if let pdfURL = viewModel.selectedPDFURL {
                // Single-line, zero-clipping top bar
                HStack(spacing: 12) {
                    // Document Icon + Title + Metadata Pills
                    HStack(spacing: 10) {
                        ZStack {
                            RoundedRectangle(cornerRadius: 8)
                                .fill(Color(red: 0.16, green: 0.28, blue: 0.44))
                                .frame(width: 34, height: 34)
                            Image(systemName: "doc.text.fill")
                                .font(.system(size: 16, weight: .semibold))
                                .foregroundStyle(Color(red: 0.48, green: 0.84, blue: 1.0))
                        }

                        VStack(alignment: .leading, spacing: 3) {
                            Text(pdfURL.lastPathComponent)
                                .font(.system(size: 13, weight: .bold))
                                .foregroundStyle(.white)
                                .lineLimit(1)
                                .truncationMode(.middle)
                                .help(pdfURL.path)

                            HStack(spacing: 6) {
                                if let report = viewModel.inspectionReport {
                                    Text("\(report.totalPages) \(report.totalPages == 1 ? "Page" : "Pages")")
                                        .font(.system(size: 10, weight: .semibold))
                                        .foregroundStyle(Color(white: 0.78))

                                    Text("•")
                                        .font(.system(size: 10))
                                        .foregroundStyle(Color(white: 0.45))

                                    StatusPill(
                                        label: !report.isImperfect ? "Clean PDF Structure" : "Imperfect PDF (Auto-Healed)",
                                        icon: !report.isImperfect ? "checkmark.circle.fill" : "wrench.and.screwdriver.fill",
                                        tint: !report.isImperfect
                                            ? Color(red: 0.20, green: 0.78, blue: 0.48)
                                            : Color(red: 0.92, green: 0.58, blue: 0.14)
                                    )
                                }

                                if viewModel.visionSpanCount > 0 {
                                    StatusPill(
                                        label: "Vision OCR: \(viewModel.visionSpanCount) spans",
                                        icon: "eye.fill",
                                        tint: Color(red: 0.28, green: 0.65, blue: 0.98)
                                    )
                                }
                            }
                        }
                    }
                    .frame(minWidth: 180, maxWidth: .infinity, alignment: .leading)

                    // Custom High-Contrast View Mode Pill Switcher (Never Clips!)
                    HStack(spacing: 4) {
                        ForEach(PreviewDocumentMode.allCases) { mode in
                            let isSelected = viewModel.previewMode == mode
                            let isReady = isModeReady(mode)
                            Button {
                                viewModel.previewMode = mode
                            } label: {
                                HStack(spacing: 5) {
                                    Image(systemName: mode.iconName)
                                        .font(.system(size: 11, weight: .semibold))
                                    Text(mode.rawValue)
                                        .font(.system(size: 11, weight: isSelected ? .bold : .medium))
                                        .lineLimit(1)
                                        .fixedSize(horizontal: true, vertical: false)
                                    if mode != .annotatedSource && isReady {
                                        Circle()
                                            .fill(Color(red: 0.28, green: 0.92, blue: 0.58))
                                            .frame(width: 6, height: 6)
                                    }
                                }
                                .padding(.horizontal, 10)
                                .padding(.vertical, 6)
                                .background(
                                    RoundedRectangle(cornerRadius: 6)
                                        .fill(
                                            isSelected
                                                ? Color(red: 0.18, green: 0.48, blue: 0.86)
                                                : Color.clear
                                        )
                                )
                                .foregroundStyle(
                                    isSelected
                                        ? .white
                                        : (isReady ? Color(white: 0.85) : Color(white: 0.55))
                                )
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding(3)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color(red: 0.08, green: 0.09, blue: 0.11))
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .strokeBorder(Color(white: 0.25), lineWidth: 1)
                    )
                    .fixedSize(horizontal: true, vertical: false)
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .background(Color(red: 0.12, green: 0.13, blue: 0.16))

                Rectangle()
                    .fill(Color(white: 0.22))
                    .frame(height: 1)

                // Interactive Manual Blackmarker Bar (Always accessible on Source & Plan view)
                if viewModel.previewMode == .annotatedSource {
                    HStack(spacing: 10) {
                        Button {
                            viewModel.isManualDrawMode.toggle()
                        } label: {
                            HStack(spacing: 6) {
                                Image(systemName: viewModel.isManualDrawMode ? "checkmark.circle.fill" : "highlighter")
                                    .font(.system(size: 11, weight: .bold))
                                Text(viewModel.isManualDrawMode ? "Manual Blackmarker: ON (Drag on PDF)" : "Manual Blackmarker")
                                    .font(.system(size: 11, weight: .bold))
                            }
                            .padding(.horizontal, 10)
                            .padding(.vertical, 5)
                            .background(
                                RoundedRectangle(cornerRadius: 6)
                                    .fill(
                                        viewModel.isManualDrawMode
                                            ? Color(red: 0.08, green: 0.62, blue: 0.90)
                                            : Color(white: 0.18)
                                    )
                            )
                            .foregroundStyle(.white)
                        }
                        .buttonStyle(.plain)

                        Text("Statute:")
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundStyle(Color(white: 0.72))

                        Picker("Manual Statute", selection: $viewModel.manualStatute) {
                            ForEach(ManualStatuteOption.allCases) { statute in
                                Text(statute.displayLabel).tag(statute)
                            }
                        }
                        .labelsHidden()
                        .pickerStyle(.menu)
                        .controlSize(.small)
                        .frame(maxWidth: 270)

                        Spacer()

                        Text("Tip: Hold Shift + Drag anytime on the PDF to draw a redaction box")
                            .font(.system(size: 10, weight: .medium))
                            .foregroundStyle(Color(white: 0.65))
                            .lineLimit(1)
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 6)
                    .background(Color(red: 0.09, green: 0.11, blue: 0.14))

                    Rectangle()
                        .fill(Color(white: 0.20))
                        .frame(height: 1)
                }
            }

            // Main PDF Content Area
            ZStack {
                if let previewURL = viewModel.activePreviewURL {
                    PDFKitCanvasView(
                        pdfURL: previewURL,
                        entities: viewModel.previewMode == .annotatedSource ? (viewModel.currentPlan?.entities ?? []) : [],
                        selectedEntityID: viewModel.selectedEntityID,
                        showAnnotations: viewModel.previewMode == .annotatedSource,
                        isManualDrawMode: viewModel.previewMode == .annotatedSource && viewModel.isManualDrawMode,
                        onSelectEntity: { id in
                            viewModel.selectedEntityID = id
                        },
                        onManualBoxDrawn: { page, rect, text in
                            viewModel.addManualRedaction(page: page, rect: rect, extractedText: text)
                        }
                    )
                } else if viewModel.selectedPDFURL != nil && viewModel.previewMode != .annotatedSource {
                    // User selected "Sanitized PDF" or "FOIA Certificate" before running Sanitize & Certify
                    VStack(spacing: 14) {
                        Image(systemName: viewModel.previewMode == .sanitizedOutput ? "lock.doc" : "checkmark.seal.text.page")
                            .font(.system(size: 44))
                            .foregroundStyle(Color(red: 0.45, green: 0.78, blue: 1.0))
                        Text("\(viewModel.previewMode.rawValue) Not Generated Yet")
                            .font(.title3.weight(.bold))
                            .foregroundStyle(.white)
                        Text("Review the detected statutory exemptions on the right, then click \"Sanitize & Certify PDF\" to execute PikePDF stream surgery and generate the certificate.")
                            .font(.callout)
                            .foregroundStyle(Color(white: 0.75))
                            .multilineTextAlignment(.center)
                            .frame(maxWidth: 420)
                        HStack(spacing: 10) {
                            Button("Back to Source & Plan") {
                                viewModel.previewMode = .annotatedSource
                            }
                            .buttonStyle(.bordered)

                            Button {
                                Task { await viewModel.executeCurrentPlan() }
                            } label: {
                                Label("Sanitize & Certify Now", systemImage: "checkmark.shield.fill")
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(Color(red: 0.14, green: 0.68, blue: 0.44))
                            .disabled(viewModel.currentPlan == nil || viewModel.isBusy)
                        }
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color(red: 0.08, green: 0.09, blue: 0.11))
                } else {
                    // Empty State with Drag & Drop + Quick Start (HIG Branding: clean, content-focused)
                    VStack(spacing: 16) {
                        ZStack {
                            RoundedRectangle(cornerRadius: 20, style: .continuous)
                                .fill(Color(red: 0.13, green: 0.16, blue: 0.22))
                                .frame(width: 76, height: 76)
                            Image(systemName: "highlighter")
                                .font(.system(size: 34, weight: .semibold))
                                .foregroundStyle(Color(red: 0.22, green: 0.74, blue: 0.98))
                        }

                        Text("Blackmarker Studio")
                            .font(.title2.weight(.bold))
                            .foregroundStyle(.white)

                        Text("Air-Gapped Multi-Sector (FOIA • HIPAA • PCI DSS • GLBA • FRCP 5.2 • SOC 2) Redaction & PikePDF Stream Sanitization.\nSelect a sample docket from the left sidebar, open a PDF, or draw manual Blackmarker boxes.")
                            .font(.callout)
                            .foregroundStyle(Color(white: 0.76))
                            .multilineTextAlignment(.center)
                            .frame(maxWidth: 480)

                        HStack(spacing: 12) {
                            Button {
                                viewModel.openFilePickerAndAnalyze()
                            } label: {
                                Label("Open PDF Document...", systemImage: "folder.badge.plus")
                                    .padding(.horizontal, 6)
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(Color(red: 0.15, green: 0.52, blue: 0.90))
                            .controlSize(.large)

                            if let firstSample = viewModel.syntheticSamples.first {
                                Button {
                                    Task { await viewModel.loadAndAnalyze(pdfURL: firstSample) }
                                } label: {
                                    Label("Load Sample Police Report", systemImage: "doc.text.magnifyingglass")
                                        .padding(.horizontal, 6)
                                }
                                .buttonStyle(.bordered)
                                .controlSize(.large)
                            }
                        }
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color(red: 0.08, green: 0.09, blue: 0.11))
                }

                // Busy Overlay
                if viewModel.isBusy {
                    VStack(spacing: 12) {
                        ProgressView()
                            .controlSize(.large)
                            .tint(.white)
                        Text(viewModel.statusMessage)
                            .font(.callout.weight(.semibold))
                            .foregroundStyle(.white)
                            .multilineTextAlignment(.center)
                    }
                    .padding(24)
                    .frame(maxWidth: 380)
                    .background(
                        RoundedRectangle(cornerRadius: 14)
                            .fill(Color.black.opacity(0.86))
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 14)
                            .strokeBorder(Color(red: 0.38, green: 0.78, blue: 1.0), lineWidth: 1.5)
                    )
                    .shadow(color: .black.opacity(0.5), radius: 16)
                }
            }
        }
    }

    private func isModeReady(_ mode: PreviewDocumentMode) -> Bool {
        switch mode {
        case .annotatedSource:
            return viewModel.selectedPDFURL != nil
        case .sanitizedOutput:
            return viewModel.hasSanitizedOutput
        case .foiaCertificate:
            return viewModel.hasCertificateOutput
        }
    }
}

struct StatusPill: View {
    let label: String
    let icon: String
    let tint: Color

    var body: some View {
        HStack(spacing: 4) {
            Image(systemName: icon)
                .font(.system(size: 9, weight: .bold))
            Text(label)
                .font(.system(size: 10, weight: .bold))
                .lineLimit(1)
        }
        .padding(.horizontal, 7)
        .padding(.vertical, 2)
        .background(Capsule().fill(tint.opacity(0.22)))
        .overlay(Capsule().strokeBorder(tint.opacity(0.75), lineWidth: 1))
        .foregroundStyle(.white)
    }
}

// MARK: - Right Statutory Inspector Panel (Fixed 380pt Width - Zero Clipping)

struct StudioInspectorView: View {
    @ObservedObject var viewModel: AppViewModel

    private var totalCount: Int {
        viewModel.currentPlan?.entities.count ?? 0
    }

    private var approvedCount: Int {
        viewModel.currentPlan?.entities.filter(\.approved).count ?? 0
    }

    private var skippedCount: Int {
        max(0, totalCount - approvedCount)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // 1. Inspector Header + Summary KPIs + Primary Action Button
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Label("Statutory Redaction Plan", systemImage: "checklist.checked")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundStyle(.white)
                    Spacer()
                    if viewModel.currentPlan != nil {
                        HStack(spacing: 6) {
                            Button("Approve All") {
                                viewModel.setAllEntitiesApproval(true)
                            }
                            .controlSize(.mini)
                            .buttonStyle(.bordered)

                            Button("Clear") {
                                viewModel.setAllEntitiesApproval(false)
                            }
                            .controlSize(.mini)
                            .buttonStyle(.bordered)
                        }
                    }
                }

                // 3-Column KPI Summary Strip
                HStack(spacing: 8) {
                    InspectorStatTile(
                        title: "DETECTED",
                        value: "\(totalCount)",
                        tint: Color(red: 0.45, green: 0.78, blue: 1.0)
                    )
                    InspectorStatTile(
                        title: "TO REDACT",
                        value: "\(approvedCount)",
                        tint: Color(red: 0.25, green: 0.88, blue: 0.58)
                    )
                    InspectorStatTile(
                        title: "EXEMPTED",
                        value: "\(skippedCount)",
                        tint: Color(red: 0.98, green: 0.74, blue: 0.24)
                    )
                }

                // Prominent Primary Action Button inside Inspector
                Button {
                    Task { await viewModel.executeCurrentPlan() }
                } label: {
                    HStack(spacing: 8) {
                        Image(systemName: "checkmark.shield.fill")
                            .font(.system(size: 14, weight: .bold))
                        Text("Sanitize & Certify PDF (\(approvedCount) items)")
                            .font(.system(size: 13, weight: .bold))
                        Spacer()
                        Image(systemName: "arrow.right.circle.fill")
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 9)
                    .frame(maxWidth: .infinity)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(
                                (viewModel.currentPlan == nil || viewModel.isBusy)
                                    ? Color(white: 0.22)
                                    : Color(red: 0.12, green: 0.64, blue: 0.40)
                            )
                    )
                    .foregroundStyle(.white)
                }
                .buttonStyle(.plain)
                .disabled(viewModel.currentPlan == nil || viewModel.isBusy)

                // Post-Sanitization Success Banner (when result exists)
                if let result = viewModel.lastResult {
                    VStack(alignment: .leading, spacing: 6) {
                        HStack(spacing: 6) {
                            Image(systemName: result.verificationPassed ? "checkmark.seal.fill" : "exclamationmark.triangle.fill")
                                .foregroundStyle(
                                    result.verificationPassed
                                        ? Color(red: 0.28, green: 0.92, blue: 0.58)
                                        : Color(red: 1.0, green: 0.75, blue: 0.25)
                                )
                            Text(result.verificationPassed ? "Zero-Residual Verification Passed" : "Verification Warning")
                                .font(.caption.weight(.bold))
                                .foregroundStyle(.white)
                            Spacer()
                            Text(String(format: "%.2fs", result.executionTimeSeconds))
                                .font(.system(size: 10, weight: .semibold, design: .monospaced))
                                .foregroundStyle(Color(white: 0.75))
                        }

                        HStack(spacing: 6) {
                            Button {
                                viewModel.previewMode = .sanitizedOutput
                            } label: {
                                Label("Sanitized PDF", systemImage: "lock.doc.fill")
                                    .font(.system(size: 11, weight: .semibold))
                            }
                            .buttonStyle(.bordered)
                            .controlSize(.small)

                            Button {
                                viewModel.previewMode = .foiaCertificate
                            } label: {
                                Label("Certificate", systemImage: "checkmark.seal.text.page.fill")
                                    .font(.system(size: 11, weight: .semibold))
                            }
                            .buttonStyle(.bordered)
                            .controlSize(.small)

                            Spacer()

                            Button("Reveal") {
                                NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath: result.outputPath)])
                            }
                            .buttonStyle(.link)
                            .font(.system(size: 11, weight: .semibold))
                        }
                    }
                    .padding(9)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color(red: 0.10, green: 0.24, blue: 0.18))
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .strokeBorder(Color(red: 0.25, green: 0.80, blue: 0.52), lineWidth: 1)
                    )
                }

                // Search & Filter Controls
                HStack(spacing: 6) {
                    Image(systemName: "line.3.horizontal.decrease.circle")
                        .font(.caption)
                        .foregroundStyle(Color(white: 0.68))
                    TextField("Filter by text, statute, or category...", text: $viewModel.entityFilterText)
                        .textFieldStyle(.plain)
                        .font(.caption)
                    if !viewModel.entityFilterText.isEmpty {
                        Button {
                            viewModel.entityFilterText = ""
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .font(.caption)
                                .foregroundStyle(Color(white: 0.65))
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 9)
                .padding(.vertical, 6)
                .background(RoundedRectangle(cornerRadius: 7).fill(Color(white: 0.09)))
                .overlay(RoundedRectangle(cornerRadius: 7).strokeBorder(Color(white: 0.24), lineWidth: 1))

                // Filter Tabs (All / Approved / Skipped)
                HStack(spacing: 4) {
                    ForEach(EntityApprovalFilter.allCases) { filter in
                        let isSelected = viewModel.approvalFilter == filter
                        Button {
                            viewModel.approvalFilter = filter
                        } label: {
                            Text(filterLabel(for: filter))
                                .font(.system(size: 11, weight: isSelected ? .bold : .medium))
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 4)
                                .background(
                                    RoundedRectangle(cornerRadius: 5)
                                        .fill(isSelected ? Color(white: 0.24) : Color.clear)
                                )
                                .foregroundStyle(isSelected ? .white : Color(white: 0.70))
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(3)
                .background(RoundedRectangle(cornerRadius: 7).fill(Color(white: 0.09)))
            }
            .padding(14)
            .background(Color(red: 0.12, green: 0.13, blue: 0.16))

            Rectangle()
                .fill(Color(white: 0.22))
                .frame(height: 1)

            // 2. Scrollable Entity Cards
            if viewModel.filteredEntities.isEmpty {
                VStack(spacing: 10) {
                    Image(systemName: viewModel.currentPlan == nil ? "doc.text.magnifyingglass" : "checkmark.circle")
                        .font(.system(size: 28))
                        .foregroundStyle(Color(white: 0.55))
                    Text(viewModel.currentPlan == nil ? "No Document Loaded" : "No Matching Entities")
                        .font(.callout.weight(.semibold))
                        .foregroundStyle(Color(white: 0.82))
                    Text(
                        viewModel.currentPlan == nil
                            ? "Load a PDF document from the sidebar to inspect statutory redactions."
                            : "Try clearing the filter or switching the approval tab above."
                    )
                    .font(.caption)
                    .foregroundStyle(Color(white: 0.65))
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 24)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(Color(red: 0.09, green: 0.10, blue: 0.12))
            } else {
                ScrollView {
                    LazyVStack(spacing: 8) {
                        ForEach(viewModel.filteredEntities) { entity in
                            EntityInspectorRow(
                                entity: entity,
                                isSelected: viewModel.selectedEntityID == entity.id,
                                onToggle: { viewModel.toggleEntityApproval(id: entity.id) },
                                onSelect: {
                                    viewModel.selectedEntityID = entity.id
                                    viewModel.previewMode = .annotatedSource
                                },
                                onDelete: {
                                    viewModel.deleteEntity(id: entity.id)
                                }
                            )
                        }
                    }
                    .padding(12)
                }
                .background(Color(red: 0.09, green: 0.10, blue: 0.12))
            }
        }
    }

    private func filterLabel(for filter: EntityApprovalFilter) -> String {
        switch filter {
        case .all:
            return "All (\(totalCount))"
        case .approvedOnly:
            return "Redact (\(approvedCount))"
        case .skippedOnly:
            return "Exempt (\(skippedCount))"
        }
    }
}

struct InspectorStatTile: View {
    let title: String
    let value: String
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title)
                .font(.system(size: 9, weight: .bold))
                .tracking(0.4)
                .foregroundStyle(Color(white: 0.70))
            Text(value)
                .font(.system(size: 16, weight: .bold, design: .rounded))
                .foregroundStyle(tint)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 7).fill(Color(white: 0.09)))
        .overlay(RoundedRectangle(cornerRadius: 7).strokeBorder(tint.opacity(0.35), lineWidth: 1))
    }
}

struct EntityInspectorRow: View {
    let entity: RedactionEntityItem
    let isSelected: Bool
    let onToggle: () -> Void
    let onSelect: () -> Void
    let onDelete: () -> Void

    private var isManual: Bool {
        entity.tier == "manual_blackmarker" || entity.category == "manual_redaction"
    }

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Button(action: onToggle) {
                Image(systemName: entity.approved ? "checkmark.square.fill" : "square")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(
                        entity.approved
                            ? (isManual ? Color(red: 0.22, green: 0.74, blue: 0.98) : Color(red: 0.98, green: 0.36, blue: 0.38))
                            : Color(white: 0.55)
                    )
            }
            .buttonStyle(.plain)
            .padding(.top, 2)
            .help(entity.approved ? "Approved for surgical stream excision" : "Exempted from redaction")

            VStack(alignment: .leading, spacing: 5) {
                // Top Row: Domain Badge + Category Badge + Page + Confidence + Delete
                HStack(spacing: 6) {
                    let dom = (entity.dataDomain ?? "PII").uppercased()
                    Text(isManual ? "MANUAL" : dom)
                        .font(.system(size: 9, weight: .bold))
                        .padding(.horizontal, 5)
                        .padding(.vertical, 2)
                        .background(
                            Capsule().fill(
                                isManual
                                    ? Color(red: 0.08, green: 0.46, blue: 0.72)
                                    : (dom == "PHI"
                                        ? Color(red: 0.52, green: 0.22, blue: 0.78)
                                        : (dom == "PPI"
                                            ? Color(red: 0.68, green: 0.48, blue: 0.08)
                                            : Color(red: 0.12, green: 0.48, blue: 0.76)))
                            )
                        )
                        .foregroundStyle(.white)

                    Text(isManual ? "BLACKMARKER" : entity.category.replacingOccurrences(of: "_", with: " ").uppercased())
                        .font(.system(size: 10, weight: .bold))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(
                            Capsule().fill(
                                entity.approved
                                    ? (isManual ? Color(red: 0.08, green: 0.46, blue: 0.72) : Color(red: 0.65, green: 0.16, blue: 0.20))
                                    : Color(red: 0.45, green: 0.35, blue: 0.12)
                            )
                        )
                        .foregroundStyle(.white)
                        .lineLimit(1)

                    Spacer()

                    Text("Page \(entity.pageNumber)")
                        .font(.system(size: 10, weight: .semibold, design: .monospaced))
                        .foregroundStyle(Color(white: 0.78))

                    Text("\(Int(entity.confidence * 100))%")
                        .font(.system(size: 10, weight: .bold, design: .monospaced))
                        .foregroundStyle(Color(red: 0.38, green: 0.90, blue: 0.62))

                    Button(action: onDelete) {
                        Image(systemName: "trash")
                            .font(.system(size: 10, weight: .semibold))
                            .foregroundStyle(Color(white: 0.62))
                    }
                    .buttonStyle(.plain)
                    .help("Remove this redaction box from the plan")
                }

                // Detected Token Text
                Text(entity.text)
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(.white)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)

                // Statute Citation Row
                HStack(spacing: 6) {
                    Image(systemName: "text.book.closed.fill")
                        .font(.system(size: 10))
                        .foregroundStyle(Color(red: 0.48, green: 0.82, blue: 1.0))
                    Text(entity.statuteCode)
                        .font(.system(size: 11, weight: .semibold, design: .monospaced))
                        .foregroundStyle(Color(red: 0.52, green: 0.84, blue: 1.0))
                        .lineLimit(1)
                    Spacer()
                    Text(entity.tier.replacingOccurrences(of: "_", with: " "))
                        .font(.system(size: 9, weight: .medium))
                        .foregroundStyle(Color(white: 0.58))
                }

                if let contextLabel = entity.contextLabel, !contextLabel.isEmpty {
                    Text(contextLabel)
                        .font(.system(size: 11))
                        .foregroundStyle(Color(white: 0.75))
                        .lineLimit(2)
                }
            }
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(isSelected ? Color(red: 0.16, green: 0.27, blue: 0.42) : Color(white: 0.13))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(
                    isSelected ? Color(red: 0.42, green: 0.80, blue: 1.0) : Color(white: 0.22),
                    lineWidth: isSelected ? 1.5 : 1.0
                )
        )
        .contentShape(Rectangle())
        .onTapGesture(perform: onSelect)
    }
}

// MARK: - Bottom Status & Memory Footer Bar

struct StudioFooterStatusBar: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        HStack(spacing: 12) {
            WorkerBadgeView(state: viewModel.workerState)

            Text(viewModel.statusMessage)
                .font(.caption)
                .foregroundStyle(
                    viewModel.errorMessage != nil
                        ? Color(red: 1.0, green: 0.45, blue: 0.45)
                        : Color(white: 0.82)
                )
                .lineLimit(1)
                .truncationMode(.tail)

            Spacer()

            Text("Profile: \(viewModel.releaseProfile.title)")
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(Color(white: 0.72))

            Text("•")
                .foregroundStyle(Color(white: 0.40))

            Text("PikePDF QPDF + Gemma 4 E4B")
                .font(.system(size: 11, design: .monospaced))
                .foregroundStyle(Color(white: 0.65))
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 7)
        .background(Color(red: 0.07, green: 0.08, blue: 0.10))
        .overlay(alignment: .top) {
            Rectangle()
                .fill(Color(white: 0.20))
                .frame(height: 1)
        }
    }
}

// MARK: - Section 508 High-Contrast Worker Badge

struct WorkerBadgeView: View {
    let state: WorkerState

    var badgeColor: Color {
        switch state {
        case .idleUnloaded:
            return Color(red: 0.22, green: 0.52, blue: 0.36)
        case .spawning:
            return Color(red: 0.72, green: 0.48, blue: 0.10)
        case .activeReady:
            return Color(red: 0.14, green: 0.46, blue: 0.78)
        case .error:
            return Color(red: 0.75, green: 0.18, blue: 0.18)
        }
    }

    var dotColor: Color {
        switch state {
        case .idleUnloaded:
            return Color(red: 0.45, green: 0.98, blue: 0.68)
        case .spawning:
            return Color(red: 1.0, green: 0.84, blue: 0.32)
        case .activeReady:
            return Color(red: 0.48, green: 0.84, blue: 1.0)
        case .error:
            return Color(red: 1.0, green: 0.45, blue: 0.45)
        }
    }

    var body: some View {
        HStack(spacing: 5) {
            Circle()
                .fill(dotColor)
                .frame(width: 7, height: 7)
            Text(state.rawValue)
                .font(.system(size: 10, weight: .bold))
                .foregroundStyle(.white)
                .lineLimit(1)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 3)
        .background(Capsule().fill(badgeColor))
    }
}

// MARK: - A-La-Carte Domain Toggle Pill (PII / PHI / PPI)

struct DomainTogglePill: View {
    let domain: DataDomainChoice
    let isActive: Bool
    let action: () -> Void

    private var tintColor: Color {
        switch domain {
        case .pii:
            return Color(red: 0.22, green: 0.74, blue: 0.98)
        case .phi:
            return Color(red: 0.68, green: 0.36, blue: 0.98)
        case .ppi:
            return Color(red: 0.94, green: 0.72, blue: 0.16)
        }
    }

    var body: some View {
        Button(action: action) {
            HStack(spacing: 4) {
                Image(systemName: isActive ? "checkmark.circle.fill" : "circle")
                    .font(.system(size: 10, weight: .bold))
                Text(domain.shortLabel)
                    .font(.system(size: 10, weight: .bold))
                    .lineLimit(1)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 5)
            .padding(.horizontal, 6)
            .background(
                RoundedRectangle(cornerRadius: 6)
                    .fill(isActive ? tintColor.opacity(0.24) : Color(white: 0.11))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 6)
                    .strokeBorder(isActive ? tintColor : Color(white: 0.26), lineWidth: 1)
            )
            .foregroundStyle(isActive ? .white : Color(white: 0.65))
        }
        .buttonStyle(.plain)
        .help(domain.tooltip)
    }
}

// MARK: - Customizable Certificate Template Sheet

struct CertificateTemplateEditorSheet: View {
    @ObservedObject var viewModel: AppViewModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Customize Redaction Certificate Template")
                        .font(.title3.weight(.bold))
                        .foregroundStyle(.white)
                    Text("Configure headers, organization/agency name, and compliance attestation for FOIA, HIPAA, PCI DSS, GLBA, FRCP 5.2, or SOC 2.")
                        .font(.caption)
                        .foregroundStyle(Color(white: 0.75))
                }
                Spacer()
                Button("Done") {
                    dismiss()
                }
                .buttonStyle(.borderedProminent)
                .tint(Color(red: 0.14, green: 0.55, blue: 0.90))
            }

            Divider().overlay(Color(white: 0.25))

            VStack(alignment: .leading, spacing: 10) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Industry / Regulatory Preset")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(Color(white: 0.82))
                    Picker("Preset", selection: $viewModel.certificatePreset) {
                        ForEach(CertificatePresetChoice.allCases) { preset in
                            Text(preset.displayName).tag(preset)
                        }
                    }
                    .labelsHidden()
                    .pickerStyle(.menu)
                    .onChange(of: viewModel.certificatePreset) { _, newPreset in
                        viewModel.applyCertificatePreset(newPreset)
                    }
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text("Top Header Banner (Jurisdiction / Sector)")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(Color(white: 0.82))
                    TextField("e.g. HEALTHCARE PRIVACY & DE-IDENTIFICATION COMPLIANCE", text: $viewModel.certificateConfig.jurisdictionBanner)
                        .textFieldStyle(.roundedBorder)
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text("Regulatory Framework Subtitle")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(Color(white: 0.82))
                    TextField("e.g. HIPAA Privacy Rule Safe Harbor Standard (45 CFR § 164.514(b)(2))", text: $viewModel.certificateConfig.frameworkSubtitle)
                        .textFieldStyle(.roundedBorder)
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text("Certificate Document Title")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(Color(white: 0.82))
                    TextField("e.g. CERTIFICATE OF REDACTION & STREAM SANITIZATION", text: $viewModel.certificateConfig.certificateTitle)
                        .textFieldStyle(.roundedBorder)
                }

                HStack(spacing: 12) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Certifying Organization / Agency / Hospital / Bank")
                            .font(.caption.weight(.bold))
                            .foregroundStyle(Color(white: 0.82))
                        TextField("Organization Name", text: $viewModel.certificateConfig.agencyName)
                            .textFieldStyle(.roundedBorder)
                    }
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Certifying Officer / System")
                            .font(.caption.weight(.bold))
                            .foregroundStyle(Color(white: 0.82))
                        TextField("Reviewer Name", text: $viewModel.certificateConfig.reviewerName)
                            .textFieldStyle(.roundedBorder)
                    }
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text("Formal Legal / Compliance Attestation Statement")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(Color(white: 0.82))
                    TextEditor(text: $viewModel.certificateConfig.attestationStatement)
                        .font(.system(size: 12))
                        .frame(height: 90)
                        .padding(4)
                        .background(RoundedRectangle(cornerRadius: 6).fill(Color(white: 0.10)))
                        .overlay(RoundedRectangle(cornerRadius: 6).strokeBorder(Color(white: 0.28), lineWidth: 1))
                }
            }
        }
        .padding(20)
        .frame(width: 600)
        .background(Color(red: 0.10, green: 0.11, blue: 0.14))
        .preferredColorScheme(.dark)
    }
}

