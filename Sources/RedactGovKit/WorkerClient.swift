import Foundation

public enum WorkspaceResolver {
    public static func resolveWorkspaceRoot() -> URL {
        let fm = FileManager.default

        // 1. Explicit environment variable
        if let envRoot = ProcessInfo.processInfo.environment["REDACTGOV_WORKSPACE_ROOT"],
           !envRoot.isEmpty,
           envRoot != "/",
           fm.fileExists(atPath: envRoot) {
            return URL(fileURLWithPath: envRoot, isDirectory: true)
        }

        // 2. Embedded Info.plist key from build.sh
        if let plistRoot = Bundle.main.infoDictionary?["RedactGovWorkspaceRoot"] as? String,
           !plistRoot.isEmpty,
           plistRoot != "/",
           fm.fileExists(atPath: plistRoot) {
            return URL(fileURLWithPath: plistRoot, isDirectory: true)
        }

        // 3. Relative to build/Blackmarker Studio.app bundle location
        let bundleURL = Bundle.main.bundleURL
        if bundleURL.pathExtension == "app" {
            let candidateRepo = bundleURL
                .deletingLastPathComponent()
                .deletingLastPathComponent()
            let pyproject = candidateRepo.appendingPathComponent("pyproject.toml")
            if fm.fileExists(atPath: pyproject.path) {
                return candidateRepo
            }
        }

        // 4. Current working directory if not "/" (LaunchServices sets cwd to "/")
        let cwd = fm.currentDirectoryPath
        if cwd != "/" && fm.isWritableFile(atPath: cwd) {
            return URL(fileURLWithPath: cwd, isDirectory: true)
        }

        // 5. Fallback to ~/Library/Application Support/RedactGov
        let appSupport = fm.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? URL(fileURLWithPath: NSTemporaryDirectory(), isDirectory: true)
        let fallbackDir = appSupport.appendingPathComponent("RedactGov", isDirectory: true)
        try? fm.createDirectory(at: fallbackDir, withIntermediateDirectories: true)
        return fallbackDir
    }

    public static func resolveOutputDirectory(for inputPDF: URL, workspaceRoot: URL) -> URL {
        let fm = FileManager.default

        // 1. Try <workspaceRoot>/data/output if workspaceRoot is not "/"
        if workspaceRoot.path != "/" {
            let repoOutput = workspaceRoot.appendingPathComponent("data/output", isDirectory: true)
            do {
                try fm.createDirectory(at: repoOutput, withIntermediateDirectories: true)
                if fm.isWritableFile(atPath: repoOutput.path) {
                    return repoOutput
                }
            } catch {
                // Fall through to next candidate
            }
        }

        // 2. Try writing alongside the input PDF if its directory is writable
        let pdfParent = inputPDF.deletingLastPathComponent()
        if pdfParent.path != "/" && fm.isWritableFile(atPath: pdfParent.path) {
            return pdfParent
        }

        // 3. Fallback to ~/Library/Application Support/RedactGov/output
        let appSupport = fm.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? URL(fileURLWithPath: NSTemporaryDirectory(), isDirectory: true)
        let safeOutput = appSupport
            .appendingPathComponent("RedactGov", isDirectory: true)
            .appendingPathComponent("output", isDirectory: true)
        try? fm.createDirectory(at: safeOutput, withIntermediateDirectories: true)
        return safeOutput
    }
}

public enum WorkerState: String, Sendable {
    case idleUnloaded = "Dormant (0 MB VRAM)"
    case spawning = "Warming Engine..."
    case activeReady = "Active (PikePDF + Gemma 4 E4B)"
    case error = "Worker Error"
}

public enum WorkerError: LocalizedError {
    case launchFailed(String)
    case malformedResponse(String)
    case remoteError(type: String, message: String)

    public var errorDescription: String? {
        switch self {
        case .launchFailed(let msg):
            return "Failed to launch redactgov-worker: \(msg)"
        case .malformedResponse(let msg):
            return "Invalid response from redactgov-worker: \(msg)"
        case .remoteError(let type, let message):
            return "\(type): \(message)"
        }
    }
}

/// Actor-isolated client for the ephemeral `redactgov-worker` helper process.
/// Follows DigUp's `Contents/Helpers/digup` pattern:
/// Spawns the worker on demand over stdio pipes and lets it exit when idle so the
/// menu bar app consumes near-zero memory while waiting in the macOS status bar.
public actor WorkerClient {
    private var process: Process?
    private var stdinHandle: FileHandle?
    private var stdoutBuffer = Data()
    private var requestCounter: Int = 0
    private let workspaceRoot: URL

    public init(workspaceRoot: URL? = nil) {
        if let workspaceRoot, workspaceRoot.path != "/" {
            self.workspaceRoot = workspaceRoot
        } else {
            self.workspaceRoot = WorkspaceResolver.resolveWorkspaceRoot()
        }
    }

    public func isRunning() -> Bool {
        guard let process else { return false }
        return process.isRunning
    }

    public func ping() async throws {
        _ = try await sendRequest(method: "ping", params: [:])
    }

    public func inspectDocument(pdfURL: URL) async throws -> DocumentInspectionPayload {
        let params: [String: Any] = ["input_pdf": pdfURL.path]
        let data = try await sendRequest(method: "inspect", params: params)
        return try JSONDecoder().decode(DocumentInspectionPayload.self, from: data)
    }

    public func createPlan(
        pdfURL: URL,
        profile: ReleaseProfileChoice,
        coordinatePolicy: CoordinatePolicyChoice,
        enabledDomains: [String] = ["PII", "PHI", "PPI"],
        repair: Bool = true,
        visionSpans: [VisionOCRSpan] = []
    ) async throws -> RedactionPlanPayload {
        let encodedSpans: [[String: Any]] = visionSpans.map { span in
            [
                "page": span.page,
                "text": span.text,
                "x0": span.x0,
                "y0": span.y0,
                "x1": span.x1,
                "y1": span.y1
            ]
        }
        let params: [String: Any] = [
            "input_pdf": pdfURL.path,
            "profile": profile.rawValue,
            "coordinate_policy": coordinatePolicy.rawValue,
            "enabled_domains": enabledDomains,
            "repair": repair,
            "vision_ocr_spans": encodedSpans
        ]
        let data = try await sendRequest(method: "plan", params: params)
        return try JSONDecoder().decode(RedactionPlanPayload.self, from: data)
    }

    public func executePlan(
        pdfURL: URL,
        plan: RedactionPlanPayload,
        outputURL: URL,
        certificateURL: URL?,
        certificateConfig: CertificateConfigPayload? = nil,
        repair: Bool = true
    ) async throws -> RedactionResultPayload {
        let planData = try JSONEncoder().encode(plan)
        let planObject = try JSONSerialization.jsonObject(with: planData)
        var params: [String: Any] = [
            "input_pdf": pdfURL.path,
            "output_pdf": outputURL.path,
            "plan": planObject,
            "repair": repair
        ]
        if let certificateURL {
            params["certificate_pdf"] = certificateURL.path
        }
        if let certificateConfig,
           let certData = try? JSONEncoder().encode(certificateConfig),
           let certObj = try? JSONSerialization.jsonObject(with: certData) {
            params["certificate_config"] = certObj
        }
        let data = try await sendRequest(method: "execute", params: params)
        return try JSONDecoder().decode(RedactionResultPayload.self, from: data)
    }

    public func quickRedact(
        pdfURL: URL,
        outputURL: URL,
        certificateURL: URL,
        profile: ReleaseProfileChoice,
        coordinatePolicy: CoordinatePolicyChoice,
        enabledDomains: [String] = ["PII", "PHI", "PPI"],
        certificateConfig: CertificateConfigPayload? = nil,
        repair: Bool = true,
        visionSpans: [VisionOCRSpan] = []
    ) async throws -> QuickRedactResponse {
        let encodedSpans: [[String: Any]] = visionSpans.map { span in
            [
                "page": span.page,
                "text": span.text,
                "x0": span.x0,
                "y0": span.y0,
                "x1": span.x1,
                "y1": span.y1
            ]
        }
        var params: [String: Any] = [
            "input_pdf": pdfURL.path,
            "output_pdf": outputURL.path,
            "certificate_pdf": certificateURL.path,
            "profile": profile.rawValue,
            "coordinate_policy": coordinatePolicy.rawValue,
            "enabled_domains": enabledDomains,
            "repair": repair,
            "vision_ocr_spans": encodedSpans
        ]
        if let certificateConfig,
           let certData = try? JSONEncoder().encode(certificateConfig),
           let certObj = try? JSONSerialization.jsonObject(with: certData) {
            params["certificate_config"] = certObj
        }
        let data = try await sendRequest(method: "quick_redact", params: params)
        return try JSONDecoder().decode(QuickRedactResponse.self, from: data)
    }

    public func suspendWorker() async {
        guard let process, process.isRunning else {
            cleanupProcess()
            return
        }
        _ = try? await sendRequest(method: "shutdown", params: [:])
        process.terminate()
        cleanupProcess()
    }

    private func ensureWorkerRunning() throws {
        if let process, process.isRunning {
            return
        }
        cleanupProcess()

        let proc = Process()
        let (executableURL, arguments, workingDir) = try resolveHelperCommand()
        proc.executableURL = executableURL
        proc.arguments = arguments
        proc.currentDirectoryURL = workingDir

        let inPipe = Pipe()
        let outPipe = Pipe()
        proc.standardInput = inPipe
        proc.standardOutput = outPipe
        proc.standardError = FileHandle.nullDevice

        do {
            try proc.run()
        } catch {
            throw WorkerError.launchFailed(error.localizedDescription)
        }

        self.process = proc
        self.stdinHandle = inPipe.fileHandleForWriting
    }

    private func resolveHelperCommand() throws -> (URL, [String], URL) {
        // 1. Check bundled Contents/Helpers/redactgov-worker inside Blackmarker Studio.app
        if let execURL = Bundle.main.executableURL {
            let contentsDir = execURL.deletingLastPathComponent().deletingLastPathComponent()
            let bundledHelper = contentsDir
                .appendingPathComponent("Helpers", isDirectory: true)
                .appendingPathComponent("redactgov-worker")
            if FileManager.default.isExecutableFile(atPath: bundledHelper.path) {
                return (bundledHelper, ["--idle-timeout", "180"], workspaceRoot)
            }
        }

        // 2. Check workspace .venv/bin/redactgov directly (zero uv startup overhead)
        let venvBinary = workspaceRoot
            .appendingPathComponent(".venv/bin/redactgov")
        if FileManager.default.isExecutableFile(atPath: venvBinary.path) {
            return (venvBinary, ["worker", "--idle-timeout", "180"], workspaceRoot)
        }

        // 3. Fallback to uv run redactgov worker
        let candidateUVPaths = [
            "/opt/homebrew/bin/uv",
            "/usr/local/bin/uv",
            "\(NSHomeDirectory())/.local/bin/uv",
            "\(NSHomeDirectory())/.cargo/bin/uv"
        ]
        for uvPath in candidateUVPaths where FileManager.default.isExecutableFile(atPath: uvPath) {
            return (
                URL(fileURLWithPath: uvPath),
                ["run", "redactgov", "worker", "--idle-timeout", "180"],
                workspaceRoot
            )
        }

        throw WorkerError.launchFailed("Could not locate bundled redactgov-worker, .venv/bin/redactgov, or uv.")
    }

    private func sendRequest(method: String, params: [String: Any]) async throws -> Data {
        try ensureWorkerRunning()
        guard
            let proc = process,
            let stdinHandle,
            let outPipe = proc.standardOutput as? Pipe
        else {
            throw WorkerError.launchFailed("Worker pipes unavailable.")
        }

        requestCounter += 1
        let reqID = requestCounter
        let payload: [String: Any] = [
            "id": reqID,
            "method": method,
            "params": params
        ]

        var lineData = try JSONSerialization.data(withJSONObject: payload)
        lineData.append(0x0A) // newline
        try stdinHandle.write(contentsOf: lineData)

        let outHandle = outPipe.fileHandleForReading
        while true {
            if let newlineRange = stdoutBuffer.range(of: Data([0x0A])) {
                let line = stdoutBuffer.subdata(in: 0..<newlineRange.lowerBound)
                stdoutBuffer.removeSubrange(0...newlineRange.lowerBound)

                if line.isEmpty { continue }
                guard let root = try JSONSerialization.jsonObject(with: line) as? [String: Any] else {
                    throw WorkerError.malformedResponse("Non-JSON object from worker.")
                }

                let ok = (root["ok"] as? Bool) ?? false
                if !ok {
                    let errDict = root["error"] as? [String: Any]
                    let errType = (errDict?["type"] as? String) ?? "WorkerException"
                    let errMsg = (errDict?["message"] as? String) ?? "Unknown worker failure"
                    throw WorkerError.remoteError(type: errType, message: errMsg)
                }

                guard let resultObj = root["result"] else {
                    throw WorkerError.malformedResponse("Missing 'result' key in worker payload.")
                }
                return try JSONSerialization.data(withJSONObject: resultObj)
            }

            let chunk = outHandle.availableData
            if chunk.isEmpty {
                cleanupProcess()
                throw WorkerError.malformedResponse("Worker closed stdout unexpectedly.")
            }
            stdoutBuffer.append(chunk)
        }
    }

    private func cleanupProcess() {
        stdinHandle = nil
        stdoutBuffer.removeAll(keepingCapacity: false)
        process = nil
    }
}
