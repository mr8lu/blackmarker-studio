import Foundation

public enum DataDomainChoice: String, CaseIterable, Codable, Sendable, Identifiable {
    case pii = "PII"
    case phi = "PHI"
    case ppi = "PPI"

    public var id: String { rawValue }

    public var shortLabel: String {
        switch self {
        case .pii: return "PII • Identity"
        case .phi: return "PHI • Health"
        case .ppi: return "PPI • Finance"
        }
    }

    public var tooltip: String {
        switch self {
        case .pii:
            return "Personally Identifiable Information (SSN, Driver's License, DOB, Phone, Email, Passport, Juvenile/Victim)"
        case .phi:
            return "Protected Health Information (MRN, NPI, ICD-10 Diagnosis, Medicare HICN/MBI, Health Plan ID)"
        case .ppi:
            return "Payment & Financial Information (Credit/Debit PAN, ABA Routing, IBAN, Bank Account, Tax ID)"
        }
    }
}

public enum CertificatePresetChoice: String, CaseIterable, Codable, Sendable, Identifiable {
    case genericCompliance = "generic_compliance"
    case publicFoia = "public_foia"
    case hipaaHealthcare = "hipaa_healthcare"
    case bankingGlbaPci = "banking_glba_pci"
    case judicialFrcp = "judicial_frcp"
    case enterpriseAicpa = "enterprise_aicpa"

    public var id: String { rawValue }

    public var displayName: String {
        switch self {
        case .genericCompliance:
            return "Multi-Sector Compliance (FOIA / HIPAA / PCI / SOC 2)"
        case .publicFoia:
            return "Government FOIA & Open Records"
        case .hipaaHealthcare:
            return "Healthcare HIPAA Safe Harbor (45 CFR § 164.514)"
        case .bankingGlbaPci:
            return "Banking & Payment Security (GLBA / PCI DSS v4.0)"
        case .judicialFrcp:
            return "Judicial Privacy Filing (Fed. R. Civ. P. 5.2)"
        case .enterpriseAicpa:
            return "Enterprise SOC 2 / AICPA Confidentiality"
        }
    }

    public var defaultConfig: CertificateConfigPayload {
        switch self {
        case .genericCompliance:
            return CertificateConfigPayload(
                templateId: rawValue,
                jurisdictionBanner: "DATA PRIVACY & SECURITY COMPLIANCE",
                frameworkSubtitle: "Multi-Sector Information Governance • FOIA • HIPAA • PCI DSS • GLBA • SOC 2",
                certificateTitle: "CERTIFICATE OF REDACTION & STREAM SANITIZATION",
                agencyName: "Information Security & Privacy Office",
                reviewerName: "Blackmarker Studio Sovereign Engine",
                attestationStatement: "The undersigned certifies that the referenced document has been sanitized using deterministic stream-level glyph excision (PikePDF/QPDF). All approved Personally Identifiable Information (PII), Protected Health Information (PHI), and Personal Payment/Financial Information (PPI) have been permanently removed from the underlying PDF content streams, XMP metadata has been eradicated, and zero-residual byte verification has passed."
            )
        case .publicFoia:
            return CertificateConfigPayload(
                templateId: rawValue,
                jurisdictionBanner: "COMMONWEALTH OF VIRGINIA / PUBLIC RECORDS COMPLIANCE",
                frameworkSubtitle: "Freedom of Information Act (5 U.S.C. § 552 / Va. Code § 2.2-3700 et seq.)",
                certificateTitle: "OFFICIAL FOIA REDACTION & SANITIZATION CERTIFICATE",
                agencyName: "Public Records & FOIA Compliance Office",
                reviewerName: "Blackmarker Studio Sovereign Engine",
                attestationStatement: "Pursuant to Va. Code § 2.2-3704.01 and 5 U.S.C. § 552(b), the undersigned certifies that the exemptions cited above apply to the excised portions of this record, and that all non-exempt portions of the public record have been released intact."
            )
        case .hipaaHealthcare:
            return CertificateConfigPayload(
                templateId: rawValue,
                jurisdictionBanner: "HEALTHCARE PRIVACY & DE-IDENTIFICATION COMPLIANCE",
                frameworkSubtitle: "HIPAA Privacy Rule Safe Harbor Standard (45 CFR § 164.514(b)(2))",
                certificateTitle: "HIPAA PHI DE-IDENTIFICATION & SANITIZATION CERTIFICATE",
                agencyName: "Health Information Privacy & Compliance Office",
                reviewerName: "Blackmarker Studio Sovereign Engine",
                attestationStatement: "Pursuant to 45 CFR § 164.514(b)(2) (HIPAA Safe Harbor Method), the undersigned certifies that Protected Health Information (PHI), Medical Record Numbers, NPIs, ICD-10 clinical identifiers, and patient identifiers listed above have been permanently excised from the PDF content streams with zero residual text."
            )
        case .bankingGlbaPci:
            return CertificateConfigPayload(
                templateId: rawValue,
                jurisdictionBanner: "FINANCIAL & PAYMENT CARD DATA SECURITY COMPLIANCE",
                frameworkSubtitle: "PCI DSS v4.0 Req. 3.4 • Gramm-Leach-Bliley Act (15 U.S.C. § 6801 / 16 CFR Part 314)",
                certificateTitle: "PCI DSS / GLBA FINANCIAL SANITIZATION CERTIFICATE",
                agencyName: "Financial Information Security & Risk Governance",
                reviewerName: "Blackmarker Studio Sovereign Engine",
                attestationStatement: "Pursuant to PCI DSS v4.0 Requirement 3.4 and the GLBA Safeguards Rule (16 CFR Part 314), the undersigned certifies that Primary Account Numbers (PAN), routing/IBAN identifiers, and nonpublic personal financial information (NPI/PPI) have been irreversibly removed from the PDF object streams."
            )
        case .judicialFrcp:
            return CertificateConfigPayload(
                templateId: rawValue,
                jurisdictionBanner: "UNITED STATES & STATE JUDICIAL PRIVACY COMPLIANCE",
                frameworkSubtitle: "Federal Rule of Civil Procedure 5.2 / Federal Rule of Criminal Procedure 49.1",
                certificateTitle: "RULE 5.2 PRIVACY REDACTION CERTIFICATE",
                agencyName: "Office of the Clerk / Litigation Compliance",
                reviewerName: "Blackmarker Studio Sovereign Engine",
                attestationStatement: "Pursuant to Fed. R. Civ. P. 5.2(a), the undersigned certifies that Social Security numbers, taxpayer-identification numbers, birth dates, minor initials/names, and financial-account numbers have been redacted prior to public docket filing."
            )
        case .enterpriseAicpa:
            return CertificateConfigPayload(
                templateId: rawValue,
                jurisdictionBanner: "ENTERPRISE TRUST SERVICES & PRIVACY GOVERNANCE",
                frameworkSubtitle: "AICPA Trust Services Criteria (SOC 2 CC6.1 / P4.2 / C1.2)",
                certificateTitle: "CONFIDENTIAL & PII/PHI/PPI SANITIZATION CERTIFICATE",
                agencyName: "Enterprise GRC & Audit Assurance",
                reviewerName: "Blackmarker Studio Sovereign Engine",
                attestationStatement: "In accordance with AICPA Trust Services Criteria for Confidentiality (C1.2) and Privacy (P4.2), the undersigned certifies that sensitive personal, health, and financial data elements have been permanently sanitized and verified free of residual underlying text."
            )
        }
    }
}

public struct CertificateConfigPayload: Codable, Hashable, Sendable {
    public var templateId: String
    public var jurisdictionBanner: String
    public var frameworkSubtitle: String
    public var certificateTitle: String
    public var agencyName: String
    public var reviewerName: String
    public var attestationStatement: String
    public var includeSha256Signature: Bool

    enum CodingKeys: String, CodingKey {
        case templateId = "template_id"
        case jurisdictionBanner = "jurisdiction_banner"
        case frameworkSubtitle = "framework_subtitle"
        case certificateTitle = "certificate_title"
        case agencyName = "agency_name"
        case reviewerName = "reviewer_name"
        case attestationStatement = "attestation_statement"
        case includeSha256Signature = "include_sha256_signature"
    }

    public init(
        templateId: String = "generic_compliance",
        jurisdictionBanner: String,
        frameworkSubtitle: String,
        certificateTitle: String,
        agencyName: String,
        reviewerName: String,
        attestationStatement: String,
        includeSha256Signature: Bool = true
    ) {
        self.templateId = templateId
        self.jurisdictionBanner = jurisdictionBanner
        self.frameworkSubtitle = frameworkSubtitle
        self.certificateTitle = certificateTitle
        self.agencyName = agencyName
        self.reviewerName = reviewerName
        self.attestationStatement = attestationStatement
        self.includeSha256Signature = includeSha256Signature
    }
}

public enum ReleaseProfileChoice: String, CaseIterable, Codable, Sendable, Identifiable {
    case publicFoia = "public-foia"
    case strictPrivacy = "strict-privacy"
    case hipaa = "hipaa"
    case pciDss = "pci-dss"
    case glba = "glba"
    case frcp52 = "frcp-5-2"
    case aicpaSoc2 = "aicpa-soc2"
    case environmentalReview = "environmental-review"
    case lawEnforcement = "law-enforcement"

    public var id: String { rawValue }

    public var displayName: String {
        switch self {
        case .publicFoia:
            return "Government FOIA & Open Records"
        case .strictPrivacy:
            return "Strict Maximum Privacy (All PII/PHI/PPI)"
        case .hipaa:
            return "Healthcare HIPAA Safe Harbor (45 CFR § 164.514)"
        case .pciDss:
            return "Payment Card PCI DSS v4.0 (Req. 3.4)"
        case .glba:
            return "Banking & Finance GLBA (16 CFR Part 314)"
        case .frcp52:
            return "Judicial Filing (Fed. R. Civ. P. 5.2)"
        case .aicpaSoc2:
            return "Enterprise AICPA SOC 2 Confidentiality"
        case .environmentalReview:
            return "Environmental & Critical Habitat Review"
        case .lawEnforcement:
            return "Law Enforcement & Victim Protection"
        }
    }

    public var shortLabel: String {
        switch self {
        case .publicFoia: return "Gov FOIA"
        case .strictPrivacy: return "Strict Privacy"
        case .hipaa: return "HIPAA Safe Harbor"
        case .pciDss: return "PCI DSS v4.0"
        case .glba: return "Banking GLBA"
        case .frcp52: return "FRCP Rule 5.2"
        case .aicpaSoc2: return "AICPA SOC 2"
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
            return "Federal & State FOIA release: redacts citizen PII, PHI, and PPI while preserving official roles."
        case .strictPrivacy:
            return "Maximum cross-sector scrub: redacts all personal, healthcare, financial, and location identifiers."
        case .hipaa:
            return "HIPAA 45 CFR § 164.514(b) Safe Harbor: excises MRNs, NPIs, ICD-10 codes, Medicare IDs, and patient PII."
        case .pciDss:
            return "PCI DSS v4.0 Req. 3.4: targets Primary Account Numbers (PAN), ABA routing, IBAN, and financial accounts."
        case .glba:
            return "Gramm-Leach-Bliley Act Safeguards: redacts nonpublic personal financial information (PPI) and customer PII."
        case .frcp52:
            return "Fed. R. Civ. P. 5.2: redacts SSNs, taxpayer IDs, birth dates, minor names, and financial accounts in court filings."
        case .aicpaSoc2:
            return "AICPA Trust Services Criteria (CC6.1 / P4.2): sanitizes customer PII and financial PPI for audit artifacts."
        case .environmentalReview:
            return "Redacts critical habitat/endangered species coordinates while keeping general project locations."
        case .lawEnforcement:
            return "Protects victims, witnesses, juveniles, medical notes, and tactical personnel."
        }
    }

    public var defaultDomains: Set<DataDomainChoice> {
        switch self {
        case .publicFoia, .strictPrivacy:
            return [.pii, .phi, .ppi]
        case .hipaa, .lawEnforcement:
            return [.pii, .phi]
        case .pciDss:
            return [.ppi]
        case .glba, .frcp52, .aicpaSoc2:
            return [.pii, .ppi]
        case .environmentalReview:
            return [.pii]
        }
    }

    public var defaultCertificatePreset: CertificatePresetChoice {
        switch self {
        case .publicFoia, .environmentalReview, .lawEnforcement:
            return .publicFoia
        case .strictPrivacy:
            return .genericCompliance
        case .hipaa:
            return .hipaaHealthcare
        case .pciDss, .glba:
            return .bankingGlbaPci
        case .frcp52:
            return .judicialFrcp
        case .aicpaSoc2:
            return .enterpriseAicpa
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
    public var dataDomain: String?
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
        case dataDomain = "data_domain"
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
        dataDomain: String? = "PII",
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
        self.dataDomain = dataDomain
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
