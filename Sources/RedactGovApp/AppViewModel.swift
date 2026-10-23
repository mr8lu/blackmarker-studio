import AppKit
import Foundation
import PDFKit
import RedactGovKit
import SwiftUI

public enum PreviewDocumentMode: String, CaseIterable, Identifiable {
    case annotatedSource = "Source & Plan"
    case sanitizedOutput = "Sanitized PDF"
    case foiaCertificate = "Certificate"

    public var id: String { rawValue }

    public var iconName: String {
        switch self {
        case .annotatedSource:
            return "doc.viewfinder"
        case .sanitizedOutput:
            return "lock.doc.fill"
        case .foiaCertificate:
            return "checkmark.seal.text.page.fill"
        }
    }
}

public enum EntityApprovalFilter: String, CaseIterable, Identifiable {
    case all = "All"
    case approvedOnly = "Approved"
    case skippedOnly = "Skipped"

    public var id: String { rawValue }
}

public enum ManualStatuteOption: String, CaseIterable, Identifiable {
    case federalFoiaPrivacy = "5 U.S.C. § 552(b)(6)"
    case hipaaSafeHarbor = "45 CFR § 164.514(b)"
    case pciDssPan = "PCI DSS v4.0 Req. 3.4"
    case glbaFinancial = "16 CFR Part 314 (GLBA)"
    case frcp52Filing = "Fed. R. Civ. P. 5.2(a)"
    case aicpaSoc2 = "AICPA TSC CC6.1 / P4.2"
    case personnelPrivacy = "Va. Code § 2.2-3705.1(1)"
    case ssnProtection = "Va. Code § 2.2-3808.1"
    case lawEnforcement = "Va. Code § 2.2-3706"
    case juvenileRecords = "Va. Code § 2.2-3705.7(2)"
    case investigative = "Va. Code § 2.2-3705.3"
    case endangeredSpecies = "Va. Code § 2.2-3705.7(26)"

    public var id: String { rawValue }

    public var displayLabel: String {
        switch self {
        case .federalFoiaPrivacy:
            return "5 U.S.C. § 552(b)(6) • Federal FOIA Privacy"
        case .hipaaSafeHarbor:
            return "45 CFR § 164.514(b) • HIPAA Safe Harbor PHI"
        case .pciDssPan:
            return "PCI DSS v4.0 Req. 3.4 • Cardholder PAN / Track"
        case .glbaFinancial:
            return "16 CFR Part 314 (GLBA) • Nonpublic Financial Info"
        case .frcp52Filing:
            return "Fed. R. Civ. P. 5.2(a) • Judicial Privacy Filing"
        case .aicpaSoc2:
            return "AICPA TSC CC6.1 / P4.2 • SOC 2 Confidentiality"
        case .personnelPrivacy:
            return "Va. Code § 2.2-3705.1(1) • Personnel & Privacy"
        case .ssnProtection:
            return "Va. Code § 2.2-3808.1 • SSN & Account IDs"
        case .lawEnforcement:
            return "Va. Code § 2.2-3706 • Law Enforcement & Victims"
        case .juvenileRecords:
            return "Va. Code § 2.2-3705.7(2) • Juvenile Identifiers"
        case .investigative:
            return "Va. Code § 2.2-3705.3 • Administrative Investigation"
        case .endangeredSpecies:
            return "Va. Code § 2.2-3705.7(26) • Critical Habitat / Species"
        }
    }
}

@MainActor
public final class AppViewModel: ObservableObject {
    @Published public var selectedPDFURL: URL?
    @Published public var inspectionReport: DocumentInspectionPayload?
    @Published public var currentPlan: RedactionPlanPayload?
    @Published public var lastResult: RedactionResultPayload?
    @Published public var selectedEntityID: String?
    @Published public var releaseProfile: ReleaseProfileChoice = .publicFoia
    @Published public var activeDomains: Set<DataDomainChoice> = [.pii, .phi, .ppi]
    @Published public var coordinatePolicy: CoordinatePolicyChoice = .all
    @Published public var autoRepairImperfect: Bool = true
    @Published public var useAppleVisionOCR: Bool = true
    @Published public var workerState: WorkerState = .idleUnloaded
    @Published public var isBusy: Bool = false
    @Published public var statusMessage: String = "Ready - Ephemeral worker dormant (0 MB VRAM)"
    @Published public var errorMessage: String?
    @Published public var previewMode: PreviewDocumentMode = .annotatedSource
    @Published public var docketSearchQuery: String = ""
    @Published public var docketEntries: [DocketAuditEntry] = []
    @Published public var entityFilterText: String = ""
    @Published public var approvalFilter: EntityApprovalFilter = .all
    @Published public var syntheticSamples: [URL] = []
    @Published public var visionSpanCount: Int = 0
    @Published public var isDropTargeted: Bool = false
    @Published public var isInspectorVisible: Bool = true
    @Published public var isManualDrawMode: Bool = false
    @Published public var manualStatute: ManualStatuteOption = .federalFoiaPrivacy
    @Published public var certificatePreset: CertificatePresetChoice = .genericCompliance
    @Published public var certificateConfig: CertificateConfigPayload = CertificatePresetChoice.genericCompliance.defaultConfig
    @Published public var isCertificateSheetPresented: Bool = false

    public let workerClient: WorkerClient
    public let indexStore: CaseIndexStore
    public let workspaceRoot: URL

    public init() {
        let rootURL = WorkspaceResolver.resolveWorkspaceRoot()
        self.workspaceRoot = rootURL
        self.workerClient = WorkerClient(workspaceRoot: rootURL)
        self.indexStore = CaseIndexStore()
        self.docketEntries = indexStore.searchDocket(query: "")
        discoverSyntheticSamples()
        if syntheticSamples.isEmpty {
            Task { [weak self] in
                guard let self else { return }
                try? await self.workerClient.ping()
                self.discoverSyntheticSamples()
            }
        }
    }

    public var enabledDomainStrings: [String] {
        DataDomainChoice.allCases.filter { activeDomains.contains($0) }.map(\.rawValue)
    }

    public func isDomainActive(_ domain: DataDomainChoice) -> Bool {
        activeDomains.contains(domain)
    }

    public func toggleDomain(_ domain: DataDomainChoice) {
        if activeDomains.contains(domain) {
            if activeDomains.count > 1 {
                activeDomains.remove(domain)
            }
        } else {
            activeDomains.insert(domain)
        }
        if let url = selectedPDFURL {
            Task { await loadAndAnalyze(pdfURL: url) }
        }
    }

    public func applyProfileDefaults(_ profile: ReleaseProfileChoice) {
        activeDomains = profile.defaultDomains
        coordinatePolicy = profile == .environmentalReview ? .sensitiveOnly : .all
        let preset = profile.defaultCertificatePreset
        certificatePreset = preset
        certificateConfig = preset.defaultConfig
    }

    public func applyCertificatePreset(_ preset: CertificatePresetChoice) {
        certificatePreset = preset
        certificateConfig = preset.defaultConfig
    }

    public func discoverSyntheticSamples() {
        let synthDir = workspaceRoot.appendingPathComponent("data/synthetic_corpus", isDirectory: true)
        guard let items = try? FileManager.default.contentsOfDirectory(
            at: synthDir,
            includingPropertiesForKeys: nil
        ) else {
            syntheticSamples = []
            return
        }
        syntheticSamples = items
            .filter { $0.pathExtension.lowercased() == "pdf" }
            .sorted { $0.lastPathComponent < $1.lastPathComponent }
    }

    public var filteredEntities: [RedactionEntityItem] {
        guard let entities = currentPlan?.entities else { return [] }
        let byApproval = entities.filter { item in
            switch approvalFilter {
            case .all: return true
            case .approvedOnly: return item.approved
            case .skippedOnly: return !item.approved
            }
        }
        let q = entityFilterText.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        if q.isEmpty { return byApproval }
        return byApproval.filter {
            $0.text.lowercased().contains(q)
                || $0.category.lowercased().contains(q)
                || $0.statuteCode.lowercased().contains(q)
                || ($0.dataDomain?.lowercased().contains(q) ?? false)
                || ($0.contextLabel?.lowercased().contains(q) ?? false)
        }
    }

    public var hasSanitizedOutput: Bool {
        guard let path = lastResult?.outputPath else { return false }
        return FileManager.default.fileExists(atPath: path)
    }

    public var hasCertificateOutput: Bool {
        guard let path = lastResult?.certificatePath else { return false }
        return FileManager.default.fileExists(atPath: path)
    }

    public var activePreviewURL: URL? {
        switch previewMode {
        case .annotatedSource:
            return selectedPDFURL
        case .sanitizedOutput:
            if let path = lastResult?.outputPath {
                let url = URL(fileURLWithPath: path)
                if FileManager.default.fileExists(atPath: url.path) {
                    return url
                }
            }
            return nil
        case .foiaCertificate:
            if let path = lastResult?.certificatePath {
                let url = URL(fileURLWithPath: path)
                if FileManager.default.fileExists(atPath: url.path) {
                    return url
                }
            }
            return nil
        }
    }

    public func openFilePickerAndAnalyze() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.pdf]
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        panel.prompt = "Analyze PDF"
        if panel.runModal() == .OK, let url = panel.url {
            Task {
                await loadAndAnalyze(pdfURL: url)
            }
        }
    }

    public func loadAndAnalyze(pdfURL: URL) async {
        let isSameDocument = selectedPDFURL?.standardizedFileURL == pdfURL.standardizedFileURL
        let preservedManualItems: [RedactionEntityItem] = isSameDocument
            ? (currentPlan?.entities.filter { $0.tier == "manual_blackmarker" || $0.category == "manual_redaction" } ?? [])
            : []

        selectedPDFURL = pdfURL
        previewMode = .annotatedSource
        lastResult = nil
        errorMessage = nil
        isBusy = true
        workerState = .spawning
        statusMessage = "Scanning \(pdfURL.lastPathComponent) [\(enabledDomainStrings.joined(separator: "+"))]..."

        let shouldUseVision = useAppleVisionOCR
        let extractedSpans: [VisionOCRSpan] = await Task.detached(priority: .userInitiated) {
            guard shouldUseVision else { return [] }
            return VisionOCRReader.extractScannedPageSpans(from: pdfURL)
        }.value
        visionSpanCount = extractedSpans.count

        do {
            let inspection = try await workerClient.inspectDocument(pdfURL: pdfURL)
            inspectionReport = inspection

            var plan = try await workerClient.createPlan(
                pdfURL: pdfURL,
                profile: releaseProfile,
                coordinatePolicy: coordinatePolicy,
                enabledDomains: enabledDomainStrings,
                repair: autoRepairImperfect,
                visionSpans: extractedSpans
            )
            if !preservedManualItems.isEmpty {
                plan.entities = preservedManualItems + plan.entities
            }
            currentPlan = plan
            selectedEntityID = plan.entities.first?.id
            workerState = .activeReady
            let approvedCount = plan.entities.filter(\.approved).count
            statusMessage = "Detected \(approvedCount) targets (\(enabledDomainStrings.joined(separator: ", "))) across \(plan.totalPages) page(s)."
        } catch {
            workerState = .error
            errorMessage = error.localizedDescription
            statusMessage = "Analysis failed: \(error.localizedDescription)"
        }

        isBusy = false
    }

    public func toggleEntityApproval(id: String) {
        guard var plan = currentPlan else { return }
        if let idx = plan.entities.firstIndex(where: { $0.id == id }) {
            plan.entities[idx].approved.toggle()
            currentPlan = plan
        }
    }

    public func setAllEntitiesApproval(_ approved: Bool) {
        guard var plan = currentPlan else { return }
        for idx in plan.entities.indices {
            plan.entities[idx].approved = approved
        }
        currentPlan = plan
    }

    public func addManualRedaction(page: Int, rect: CGRect, extractedText: String?) {
        guard let pdfURL = selectedPDFURL else { return }
        let cleanedText = (extractedText ?? "")
            .replacingOccurrences(of: "\n", with: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        let displayText = cleanedText.isEmpty
            ? "[Manual Blackmarker Region (\(Int(rect.width))×\(Int(rect.height))pt)]"
            : cleanedText

        let bbox = PDFBoundingBox(
            page: page,
            x0: Double(round(rect.minX * 100) / 100),
            y0: Double(round(rect.minY * 100) / 100),
            x1: Double(round(rect.maxX * 100) / 100),
            y1: Double(round(rect.maxY * 100) / 100)
        )

        let manualItem = RedactionEntityItem(
            text: displayText,
            category: "manual_redaction",
            dataDomain: "PII",
            statuteCode: manualStatute.rawValue,
            confidence: 1.0,
            pageNumber: page,
            boundingBoxes: [bbox],
            tier: "manual_blackmarker",
            contextLabel: "Manual Blackmarker (\(manualStatute.displayLabel))",
            approved: true
        )

        if var plan = currentPlan {
            plan.entities.insert(manualItem, at: 0)
            currentPlan = plan
        } else {
            let pageCount = PDFDocument(url: pdfURL)?.pageCount ?? 1
            currentPlan = RedactionPlanPayload(
                documentName: pdfURL.lastPathComponent,
                totalPages: pageCount,
                entities: [manualItem]
            )
        }

        selectedEntityID = manualItem.id
        statusMessage = "Added manual Blackmarker redaction on page \(page) (\(manualStatute.rawValue))."
    }

    public func deleteEntity(id: String) {
        guard var plan = currentPlan else { return }
        plan.entities.removeAll { $0.id == id }
        currentPlan = plan
        if selectedEntityID == id {
            selectedEntityID = plan.entities.first?.id
        }
        statusMessage = "Removed redaction item from plan."
    }

    public func executeCurrentPlan() async {
        guard let pdfURL = selectedPDFURL, let plan = currentPlan else { return }
        isBusy = true
        errorMessage = nil
        workerState = .spawning
        statusMessage = "Executing PikePDF content stream surgery & issuing compliance certificate..."

        let outDir = WorkspaceResolver.resolveOutputDirectory(
            for: pdfURL,
            workspaceRoot: workspaceRoot
        )

        let stem = pdfURL.deletingPathExtension().lastPathComponent
        let outputURL = outDir.appendingPathComponent("\(stem)_sanitized.pdf")
        let certURL = outDir.appendingPathComponent("\(stem)_certificate.pdf")

        do {
            let result = try await workerClient.executePlan(
                pdfURL: pdfURL,
                plan: plan,
                outputURL: outputURL,
                certificateURL: certURL,
                certificateConfig: certificateConfig,
                repair: autoRepairImperfect
            )
            lastResult = result
            workerState = .activeReady
            indexStore.recordRedactionRun(plan: plan, result: result)
            refreshDocketSearch()

            if result.verificationPassed {
                statusMessage = "Sanitized \(result.redactedCount) items in \(String(format: "%.2f", result.executionTimeSeconds))s - Zero residual bytes verified."
                previewMode = .sanitizedOutput
            } else {
                statusMessage = "Sanitization finished with verification warning. Inspect output manually."
            }
        } catch {
            workerState = .error
            errorMessage = error.localizedDescription
            statusMessage = "Sanitization error: \(error.localizedDescription)"
        }

        isBusy = false
    }

    public func quickDropSanitize(pdfURL: URL) async {
        isBusy = true
        errorMessage = nil
        workerState = .spawning
        statusMessage = "Quick-scrubbing \(pdfURL.lastPathComponent)..."

        let shouldUseVision = useAppleVisionOCR
        let extractedSpans: [VisionOCRSpan] = await Task.detached(priority: .userInitiated) {
            guard shouldUseVision else { return [] }
            return VisionOCRReader.extractScannedPageSpans(from: pdfURL)
        }.value
        visionSpanCount = extractedSpans.count

        let outDir = WorkspaceResolver.resolveOutputDirectory(
            for: pdfURL,
            workspaceRoot: workspaceRoot
        )
        let stem = pdfURL.deletingPathExtension().lastPathComponent
        let outputURL = outDir.appendingPathComponent("\(stem)_sanitized.pdf")
        let certURL = outDir.appendingPathComponent("\(stem)_certificate.pdf")

        do {
            let response = try await workerClient.quickRedact(
                pdfURL: pdfURL,
                outputURL: outputURL,
                certificateURL: certURL,
                profile: releaseProfile,
                coordinatePolicy: coordinatePolicy,
                enabledDomains: enabledDomainStrings,
                certificateConfig: certificateConfig,
                repair: autoRepairImperfect,
                visionSpans: extractedSpans
            )
            selectedPDFURL = pdfURL
            currentPlan = response.plan
            lastResult = response.result
            workerState = .activeReady
            indexStore.recordRedactionRun(plan: response.plan, result: response.result)
            refreshDocketSearch()
            previewMode = .sanitizedOutput
            statusMessage = "Quick Scrub complete: \(response.result.redactedCount) redactions certified."
        } catch {
            workerState = .error
            errorMessage = error.localizedDescription
            statusMessage = "Quick Scrub failed: \(error.localizedDescription)"
        }

        isBusy = false
    }

    public func suspendEphemeralWorker() async {
        await workerClient.suspendWorker()
        workerState = .idleUnloaded
        statusMessage = "Worker suspended - Gemma 4 E4B unloaded from unified memory (0 MB VRAM)."
    }

    public func refreshDocketSearch() {
        docketEntries = indexStore.searchDocket(query: docketSearchQuery)
    }

    public func revealInFinder(path: String) {
        let url = URL(fileURLWithPath: path)
        NSWorkspace.shared.activateFileViewerSelecting([url])
    }
}
