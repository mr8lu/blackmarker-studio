import Foundation

public enum ReleaseProfileChoice: String, CaseIterable, Codable, Sendable, Identifiable {
    case publicFoia = "public-foia"
    case strictPrivacy = "strict-privacy"
    case environmentalReview = "environmental-review"
    case lawEnforcement = "law-enforcement"

    public var id: String { rawValue }

    public var displayName: String {
        switch self {
        case .publicFoia:
            return "Public FOIA (Va. Code § 2.2-3700)"
        case .strictPrivacy:
            return "Strict Privacy (Maximum PII Scrub)"
        case .environmentalReview:
            return "Environmental Review (§ 2.2-3705.7)"
        case .lawEnforcement:
            return "Law Enforcement / CJIS (§ 2.2-3705.2)"
        }
    }

    public var shortLabel: String {
        switch self {
        case .publicFoia: return "Public FOIA"
        case .strictPrivacy: return "Strict Privacy"
        case .environmentalReview: return "Environmental"
        case .lawEnforcement: return "Law Enforcement"
        }
    }

    public var title: String {
        displayName
    }

    public var subtitle: String {
        switch self {
        case .publicFoia:
            return "Standard VFOIA release: redacts citizen PII while preserving public official signatures."
        case .strictPrivacy:
            return "Maximum privacy scrub: redacts all personal names, addresses, phones, SSNs, and coordinates."
        case .environmentalReview:
            return "Redacts critical habitat/endangered species coordinates (§ 2.2-3705.7) while keeping general project locations."
        case .lawEnforcement:
            return "Protects victims, witnesses, juveniles, and tactical personnel under Va. Code § 2.2-3706."
        }
    }
}

public enum CoordinatePolicyChoice: String, CaseIterable, Codable, Sendable, Identifiable {
    case all = "all"
    case sensitiveOnly = "sensitive-only"
    case none = "none"

    public var id: String { rawValue }

    public var displayName: String {
        switch self {
        case .all: return "Redact All Coordinates"
        case .sensitiveOnly: return "Sensitive Habitats & Victims Only"
        case .none: return "Preserve All Coordinates"
        }
    }

    public var title: String {
        displayName
    }
}

public struct PDFBoundingBox: Codable, Hashable, Sendable {
    public var page: Int
    public var x0: Double
    public var y0: Double
    public var x1: Double
    public var y1: Double

    public init(page: Int, x0: Double, y0: Double, x1: Double, y1: Double) {
        self.page = page
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
    }

    public var width: Double { abs(x1 - x0) }
    public var height: Double { abs(y1 - y0) }
}

public struct RedactionEntityItem: Codable, Identifiable, Hashable, Sendable {
    public var id: String
    public var text: String
    public var category: String
    public var statuteCode: String
    public var confidence: Double
    public var pageNumber: Int
    public var boundingBoxes: [PDFBoundingBox]
    public var tier: String
    public var contextLabel: String?
    public var approved: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case text
        case category
        case statuteCode = "statute_code"
        case confidence
        case pageNumber = "page_number"
        case boundingBoxes = "bounding_boxes"
        case tier
        case contextLabel = "context_label"
        case approved
    }

    public init(
        id: String = String(UUID().uuidString.prefix(8)).lowercased(),
        text: String,
        category: String,
        statuteCode: String,
        confidence: Double,
        pageNumber: Int,
        boundingBoxes: [PDFBoundingBox],
        tier: String = "manual_marquee",
        contextLabel: String? = nil,
        approved: Bool = true
    ) {
        self.id = id
        self.text = text
        self.category = category
        self.statuteCode = statuteCode
        self.confidence = confidence
        self.pageNumber = pageNumber
        self.boundingBoxes = boundingBoxes
        self.tier = tier
        self.contextLabel = contextLabel
        self.approved = approved
    }
}

public struct RedactionPlanPayload: Codable, Sendable {
    public var documentName: String
    public var totalPages: Int
    public var entities: [RedactionEntityItem]
    public var createdAt: String

    enum CodingKeys: String, CodingKey {
        case documentName = "document_name"
        case totalPages = "total_pages"
        case entities
        case createdAt = "created_at"
    }

    public init(
        documentName: String,
        totalPages: Int,
        entities: [RedactionEntityItem],
        createdAt: String = ISO8601DateFormatter().string(from: Date())
    ) {
        self.documentName = documentName
        self.totalPages = totalPages
        self.entities = entities
        self.createdAt = createdAt
    }
}

public struct RedactionResultPayload: Codable, Sendable {
    public var success: Bool
    public var inputPath: String
    public var outputPath: String
    public var certificatePath: String?
    public var redactedCount: Int
    public var totalPages: Int
    public var executionTimeSeconds: Double
    public var verificationPassed: Bool

    enum CodingKeys: String, CodingKey {
        case success
        case inputPath = "input_path"
        case outputPath = "output_path"
        case certificatePath = "certificate_path"
        case redactedCount = "redacted_count"
        case totalPages = "total_pages"
        case executionTimeSeconds = "execution_time_seconds"
        case verificationPassed = "verification_passed"
    }

    public init(
        success: Bool,
        inputPath: String,
        outputPath: String,
        certificatePath: String?,
        redactedCount: Int,
        totalPages: Int,
        executionTimeSeconds: Double,
        verificationPassed: Bool
    ) {
        self.success = success
        self.inputPath = inputPath
        self.outputPath = outputPath
        self.certificatePath = certificatePath
        self.redactedCount = redactedCount
        self.totalPages = totalPages
        self.executionTimeSeconds = executionTimeSeconds
        self.verificationPassed = verificationPassed
    }
}

public struct QuickRedactResponse: Codable, Sendable {
    public var plan: RedactionPlanPayload
    public var result: RedactionResultPayload
}

public struct DocumentInspectionPayload: Codable, Sendable {
    public var filePath: String
    public var totalPages: Int
    public var isImperfect: Bool
    public var issues: [String]
    public var repairedFonts: Int
    public var repairedStreams: Int

    enum CodingKeys: String, CodingKey {
        case filePath = "file_path"
        case totalPages = "total_pages"
        case isImperfect = "is_imperfect"
        case issues
        case repairedFonts = "repaired_fonts"
        case repairedStreams = "repaired_streams"
    }
}

public struct VisionOCRSpan: Codable, Sendable {
    public var page: Int
    public var text: String
    public var x0: Double
    public var y0: Double
    public var x1: Double
    public var y1: Double

    public init(page: Int, text: String, x0: Double, y0: Double, x1: Double, y1: Double) {
        self.page = page
        self.text = text
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
    }
}

public struct DocketAuditEntry: Identifiable, Hashable, Sendable {
    public var id: Int64
    public var documentName: String
    public var outputPath: String
    public var certificatePath: String?
    public var entityText: String
    public var category: String
    public var statuteCode: String
    public var pageNumber: Int
    public var verifiedZeroResidual: Bool
    public var createdAt: String
}
