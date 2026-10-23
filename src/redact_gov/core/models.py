"""Data models and schemas for AI Blackmarker (RedactGov)."""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


class DataDomain(str, Enum):
    """A-la-carte privacy & compliance data domains."""
    PII = "PII"  # Personally Identifiable Information (FOIA, FRCP 5.2, AICPA Privacy)
    PHI = "PHI"  # Protected Health Information (HIPAA 45 CFR § 164.514 Safe Harbor)
    PPI = "PPI"  # Protected / Nonpublic Personal Financial Information (PCI DSS, GLBA, AICPA Confidentiality)


class CertificateConfig(BaseModel):
    """Customizable compliance certificate template configuration for multi-sector deployment."""
    template_preset: str = Field(
        default="generic_compliance",
        description="Template preset identifier (generic_compliance, public_foia, hipaa_healthcare, banking_glba_pci, judicial_frcp, enterprise_aicpa)",
    )
    jurisdiction_banner: str = Field(
        default="SOVEREIGN DATA PRIVACY & COMPLIANCE AUTHORITY",
        description="Top header banner on the certificate (e.g. Agency, Hospital System, Bank, or Court)",
    )
    framework_subtitle: str = Field(
        default="STATUTORY & REGULATORY DATA SANITIZATION STANDARD (FOIA / HIPAA / GLBA / PCI DSS / FRCP 5.2)",
        description="Second header line describing the regulatory framework",
    )
    certificate_title: str = Field(
        default="OFFICIAL REDACTION & COMPLIANCE CERTIFICATE",
        description="Main document title",
    )
    agency_name: str = Field(
        default="Office of Information Privacy & Compliance",
        description="Certifying organization, agency, hospital, or financial institution",
    )
    reviewer_name: str = Field(
        default="Authorized Compliance Officer",
        description="Name or title of the certifying reviewer",
    )
    reviewer_role_label: str = Field(
        default="Certifying Compliance Officer:",
        description="Label for the reviewer row in the metadata table",
    )
    citation_column_header: str = Field(
        default="Regulatory / Statutory Citation",
        description="Column header for the statute/regulation table",
    )
    attestation_statement: str = Field(
        default=(
            "I hereby certify that the redactions documented above have been executed in strict "
            "accordance with applicable federal, state, and industry privacy mandates (including FOIA, "
            "HIPAA 45 CFR § 164.514, GLBA 15 U.S.C. § 6801, PCI DSS v4.0, AICPA Trust Services Criteria, "
            "and Fed. R. Civ. P. 5.2). All underlying PDF glyph streams, hidden annotations, and XMP "
            "metadata layers have been irreversibly excised using air-gapped on-device sanitization."
        ),
        description="Legal attestation paragraph at the bottom of the certificate",
    )


CERTIFICATE_PRESETS: Dict[str, CertificateConfig] = {
    "generic_compliance": CertificateConfig(
        template_preset="generic_compliance",
        jurisdiction_banner="SOVEREIGN DATA PRIVACY & COMPLIANCE AUTHORITY",
        framework_subtitle="STATUTORY & REGULATORY DATA SANITIZATION STANDARD (FOIA / HIPAA / GLBA / PCI DSS / FRCP 5.2)",
        certificate_title="OFFICIAL REDACTION & COMPLIANCE CERTIFICATE",
        agency_name="Office of Information Privacy & Compliance",
        reviewer_name="Authorized Compliance Officer",
        reviewer_role_label="Certifying Compliance Officer:",
        citation_column_header="Regulatory / Statutory Citation",
    ),
    "public_foia": CertificateConfig(
        template_preset="public_foia",
        jurisdiction_banner="OFFICE OF PUBLIC RECORDS & TRANSPARENCY",
        framework_subtitle="FREEDOM OF INFORMATION & PUBLIC RECORDS DISCLOSURE COMPLIANCE",
        certificate_title="PUBLIC RECORDS REDACTION & EXEMPTION CERTIFICATE",
        agency_name="Public Records & FOIA Division",
        reviewer_name="Authorized FOIA Officer",
        reviewer_role_label="FOIA Compliance Officer:",
        citation_column_header="Statutory Exemption Citation",
        attestation_statement=(
            "I hereby certify under penalty of law that the redactions documented above have been executed "
            "in strict compliance with applicable Freedom of Information and Public Records statutes. "
            "All underlying data layers and glyph streams have been irreversibly purged using air-gapped sanitization."
        ),
    ),
    "hipaa_healthcare": CertificateConfig(
        template_preset="hipaa_healthcare",
        jurisdiction_banner="HEALTHCARE PRIVACY & HEALTH INFORMATION MANAGEMENT (HIM)",
        framework_subtitle="HIPAA PRIVACY RULE & SAFE HARBOR DE-IDENTIFICATION (45 CFR § 164.514)",
        certificate_title="PHI DE-IDENTIFICATION & REDACTION CERTIFICATE",
        agency_name="Health System Privacy & Compliance Office",
        reviewer_name="HIPAA Privacy Officer",
        reviewer_role_label="HIPAA Privacy Official:",
        citation_column_header="HIPAA / Regulatory Citation",
        attestation_statement=(
            "I hereby certify that Protected Health Information (PHI) and patient identifiers documented above "
            "have been de-identified and excised in accordance with the HIPAA Privacy Rule Safe Harbor standard "
            "(45 CFR § 164.514(b)). All underlying PDF glyph streams and XMP metadata have been permanently purged."
        ),
    ),
    "banking_glba_pci": CertificateConfig(
        template_preset="banking_glba_pci",
        jurisdiction_banner="FINANCIAL PRIVACY & INFORMATION SECURITY GOVERNANCE",
        framework_subtitle="GLBA SAFEGUARDS (15 U.S.C. § 6801) & PCI DSS v4.0 COMPLIANCE",
        certificate_title="FINANCIAL DATA (PPI / PAN) SANITIZATION CERTIFICATE",
        agency_name="Financial Risk & Compliance Operations",
        reviewer_name="Information Security & Compliance Officer",
        reviewer_role_label="Financial Compliance Officer:",
        citation_column_header="GLBA / PCI DSS Control",
        attestation_statement=(
            "I hereby certify that all Primary Account Numbers (PAN), Sensitive Authentication Data (SAD), "
            "and Nonpublic Personal Financial Information (PPI) documented above have been rendered unreadable "
            "and excised from the PDF byte stream in compliance with PCI DSS v4.0 Req. 3.3/3.4 and GLBA Safeguards."
        ),
    ),
    "judicial_frcp": CertificateConfig(
        template_preset="judicial_frcp",
        jurisdiction_banner="JUDICIAL & LITIGATION PRIVACY COMPLIANCE",
        framework_subtitle="FEDERAL RULES OF CIVIL PROCEDURE RULE 5.2 PRIVACY PROTECTION",
        certificate_title="COURT FILING REDACTION & PRIVACY CERTIFICATE",
        agency_name="Office of Litigation Support & Docketing",
        reviewer_name="Certifying Counsel / Docket Officer",
        reviewer_role_label="Certifying Counsel / Officer:",
        citation_column_header="Court Rule / Citation",
        attestation_statement=(
            "I hereby certify that this filing has been sanitized in accordance with Fed. R. Civ. P. 5.2(a) "
            "(and applicable local court privacy rules) to redact Social Security numbers, taxpayer-identification "
            "numbers, birth dates, minor identifiers, and financial account numbers from all document layers."
        ),
    ),
    "enterprise_aicpa": CertificateConfig(
        template_preset="enterprise_aicpa",
        jurisdiction_banner="ENTERPRISE INFORMATION ASSURANCE & AUDIT GOVERNANCE",
        framework_subtitle="AICPA TRUST SERVICES CRITERIA (CONFIDENTIALITY C1 & PRIVACY P1-P8)",
        certificate_title="CONFIDENTIALITY & PRIVACY SANITIZATION CERTIFICATE",
        agency_name="Enterprise Risk & Assurance Group",
        reviewer_name="Authorized Assurance Reviewer",
        reviewer_role_label="Assurance Reviewer:",
        citation_column_header="AICPA / Regulatory Criterion",
        attestation_statement=(
            "I hereby certify that confidential client, tax, financial, and personal records documented above "
            "have been sanitized in accordance with AICPA Trust Services Criteria for Confidentiality (C1.1) "
            "and Privacy (P1.0-P8.0), with zero residual bytes remaining in the output PDF stream."
        ),
    ),
}


def get_certificate_preset(preset_id: Optional[str] = None) -> CertificateConfig:
    """Return a copy of a named CertificateConfig preset (defaulting to generic_compliance)."""
    if not preset_id:
        return CERTIFICATE_PRESETS["generic_compliance"].model_copy()
    key = preset_id.lower().strip().replace("-", "_")
    profile_to_preset = {
        "public_foia": "public_foia",
        "strict_privacy": "generic_compliance",
        "hipaa": "hipaa_healthcare",
        "pci_dss": "banking_glba_pci",
        "glba": "banking_glba_pci",
        "frcp_5_2": "judicial_frcp",
        "aicpa_soc2": "enterprise_aicpa",
        "environmental_review": "public_foia",
        "law_enforcement": "public_foia",
    }
    resolved_key = profile_to_preset.get(key, key)
    preset = CERTIFICATE_PRESETS.get(resolved_key, CERTIFICATE_PRESETS["generic_compliance"])
    return preset.model_copy()


class BoundingBox(BaseModel):
    """Spatial bounding box in PDF points (origin at bottom-left or top-left standard)."""
    page: int = Field(description="1-based page index")
    x0: float = Field(description="Left horizontal coordinate")
    y0: float = Field(description="Bottom / Top coordinate depending on convention")
    x1: float = Field(description="Right horizontal coordinate")
    y1: float = Field(description="Top / Bottom coordinate depending on convention")

    @property
    def width(self) -> float:
        return abs(self.x1 - self.x0)

    @property
    def height(self) -> float:
        return abs(self.y1 - self.y0)


class RedactionEntity(BaseModel):
    """An individual token or string target identified for redaction."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    text: str = Field(description="Verbatim text string to redact")
    category: str = Field(description="Categorical entity type (e.g. ssn, mrn, bank_account, juvenile)")
    statute_code: str = Field(description="Mapped statutory or regulatory citation code")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    page_number: int = Field(default=1, description="1-based page index")
    bounding_boxes: List[BoundingBox] = Field(default_factory=list)
    tier: str = Field(default="tier1_deterministic", description="Engine tier (tier1_deterministic, tier2_gemma, or manual_blackmarker)")
    context_label: Optional[str] = Field(default=None, description="Form prompt, question, or surrounding title block label")
    data_domain: Optional[str] = Field(default=None, description="Data domain classification: PII, PHI, or PPI")
    approved: bool = Field(default=True, description="Approval state for human-in-the-loop review")


class AuditRecord(BaseModel):
    """Auditable log entry for a performed redaction."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    page: int
    verbatim_text: str
    statute_code: str
    statute_title: str
    category: str
    confidence: float
    bbox: Optional[BoundingBox] = None


class RedactionPlan(BaseModel):
    """Complete redaction plan for a document before execution."""
    document_name: str
    total_pages: int
    entities: List[RedactionEntity] = Field(default_factory=list)
    profile: str = Field(default="public_foia", description="Compliance profile used to generate the plan")
    enabled_domains: List[str] = Field(
        default_factory=lambda: ["PII", "PHI", "PPI"],
        description="Active a-la-carte data domains (PII, PHI, PPI)",
    )
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RedactionResult(BaseModel):
    """Output summary of document sanitization."""
    success: bool
    input_path: str
    output_path: str
    certificate_path: Optional[str] = None
    redacted_count: int
    total_pages: int
    execution_time_seconds: float
    verification_passed: bool
