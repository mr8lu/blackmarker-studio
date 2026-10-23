"""Multi-sector statutory and regulatory compliance database (FOIA, HIPAA, PCI DSS, GLBA, FRCP 5.2, AICPA SOC 2)."""

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class VirginiaStatute:
    code: str
    short_title: str
    category: str
    description: str
    legal_citation: str
    default_confidence: float = 0.95
    data_domain: str = "PII"  # "PII", "PHI", or "PPI"

    def model_dump(self) -> dict:
        """Return dictionary representation compatible with Pydantic serialization."""
        return asdict(self)


# Alias for multi-sector callers
ComplianceStatute = VirginiaStatute


VIRGINIA_STATUTES: Dict[str, VirginiaStatute] = {
    # --- Public Records / FOIA & Statutory Exemptions ---
    "VA-2.2-3705.1(1)": VirginiaStatute(
        code="VA-2.2-3705.1(1)",
        short_title="Personnel Records",
        category="Personnel",
        description="Personnel information concerning identifiable individuals held in personnel files.",
        legal_citation="Va. Code § 2.2-3705.1(1)",
        data_domain="PII",
    ),
    "VA-2.2-3705.1(10)": VirginiaStatute(
        code="VA-2.2-3705.1(10)",
        short_title="Personal Privacy & PII",
        category="Privacy",
        description="Social Security Numbers, driver's license numbers, and personal contact numbers not held in official capacity.",
        legal_citation="Va. Code § 2.2-3705.1(10)",
        data_domain="PII",
    ),
    "VA-2.2-3705.2(1)": VirginiaStatute(
        code="VA-2.2-3705.2(1)",
        short_title="Law Enforcement Tactical Information",
        category="Law Enforcement",
        description="Tactical operations plans, undercover officer identities, and confidential informant records.",
        legal_citation="Va. Code § 2.2-3705.2(1)",
        data_domain="PII",
    ),
    "VA-2.2-3705.4(1)": VirginiaStatute(
        code="VA-2.2-3705.4(1)",
        short_title="Scholastic & Disciplinary Records",
        category="Education",
        description="Scholastic records containing information directly related to an identifiable student, including disciplinary proceedings.",
        legal_citation="Va. Code § 2.2-3705.4(1)",
        data_domain="PII",
    ),
    "VA-2.2-3705.6(3)": VirginiaStatute(
        code="VA-2.2-3705.6(3)",
        short_title="Proprietary & Security Exemption",
        category="Proprietary",
        description="Proprietary commercial records, trade secrets, or critical infrastructure security information.",
        legal_citation="Va. Code § 2.2-3705.6(3)",
        data_domain="PPI",
    ),
    "VA-16.1-301": VirginiaStatute(
        code="VA-16.1-301",
        short_title="Juvenile Law-Enforcement Records",
        category="Juvenile",
        description="Law-enforcement records and reports concerning children and juveniles subject to proceedings or investigations.",
        legal_citation="Va. Code § 16.1-301",
        data_domain="PII",
    ),
    "VA-19.2-11.2": VirginiaStatute(
        code="VA-19.2-11.2",
        short_title="Crime Victim & Witness Identification",
        category="Victim/Witness",
        description="Names, residential addresses, and telephone numbers of crime victims and witnesses.",
        legal_citation="Va. Code § 19.2-11.2",
        data_domain="PII",
    ),
    "VA-2.2-3705.7(2)": VirginiaStatute(
        code="VA-2.2-3705.7(2)",
        short_title="Endangered & Rare Species Locations",
        category="Endangered Species",
        description="Information identifying specific locations of rare, threatened, or endangered plant or animal species, natural communities, or cave resources.",
        legal_citation="Va. Code § 2.2-3705.7(2)",
        data_domain="PII",
    ),
    # --- Federal / Generic FOIA ---
    "FOIA-5-USC-552(b)(6)": VirginiaStatute(
        code="FOIA-5-USC-552(b)(6)",
        short_title="FOIA Personal Privacy (Exemption 6)",
        category="Privacy",
        description="Personnel, medical, and similar files the disclosure of which would constitute a clearly unwarranted invasion of personal privacy.",
        legal_citation="5 U.S.C. § 552(b)(6)",
        data_domain="PII",
    ),
    "FOIA-5-USC-552(b)(7)(C)": VirginiaStatute(
        code="FOIA-5-USC-552(b)(7)(C)",
        short_title="FOIA Law Enforcement Privacy (Exemption 7C)",
        category="Law Enforcement",
        description="Records or information compiled for law enforcement purposes protecting personal privacy of witnesses, victims, and subjects.",
        legal_citation="5 U.S.C. § 552(b)(7)(C)",
        data_domain="PII",
    ),
    "FOIA-5-USC-552(b)(4)": VirginiaStatute(
        code="FOIA-5-USC-552(b)(4)",
        short_title="FOIA Trade Secrets & Commercial Financial (Exemption 4)",
        category="Financial/Proprietary",
        description="Trade secrets and commercial or financial information obtained from a person and privileged or confidential.",
        legal_citation="5 U.S.C. § 552(b)(4)",
        data_domain="PPI",
    ),
    # --- HIPAA (Healthcare / Hospitals - PHI) ---
    "HIPAA-164.514(b)": VirginiaStatute(
        code="HIPAA-164.514(b)",
        short_title="HIPAA Safe Harbor PHI (18 Identifiers)",
        category="PHI / HIPAA",
        description="Protected Health Information de-identification under the HIPAA Privacy Rule Safe Harbor method (names, dates, geographic subdivisions, contact identifiers, SSNs).",
        legal_citation="45 CFR § 164.514(b)(2)(i)",
        data_domain="PHI",
    ),
    "HIPAA-164.514(b)-MRN": VirginiaStatute(
        code="HIPAA-164.514(b)-MRN",
        short_title="HIPAA Medical Record, NPI & Health Plan ID",
        category="PHI / Medical ID",
        description="Medical record numbers (MRN), health plan beneficiary numbers, National Provider Identifiers (NPI), and clinical device/serial numbers.",
        legal_citation="45 CFR § 164.514(b)(2)(i)(H)-(M)",
        data_domain="PHI",
    ),
    "HIPAA-164.502-CLINICAL": VirginiaStatute(
        code="HIPAA-164.502-CLINICAL",
        short_title="HIPAA Protected Clinical & Treatment Records",
        category="PHI / Clinical",
        description="Patient diagnoses, ICD-10/CPT codes, admission/discharge dates, and protected clinical care narratives.",
        legal_citation="45 CFR § 164.502(a) / § 164.514(b)",
        data_domain="PHI",
    ),
    # --- PCI DSS v4.0 (Payment Card Industry - PPI) ---
    "PCI-DSS-3.3": VirginiaStatute(
        code="PCI-DSS-3.3",
        short_title="PCI DSS Sensitive Authentication Data (SAD)",
        category="PPI / PCI DSS",
        description="Card verification values (CVV2/CVC2/CID), PIN blocks, and magnetic stripe track data that must never be retained post-authorization.",
        legal_citation="PCI DSS v4.0 Req. 3.3",
        data_domain="PPI",
    ),
    "PCI-DSS-3.4": VirginiaStatute(
        code="PCI-DSS-3.4",
        short_title="PCI DSS Primary Account Number (PAN) & Cardholder Data",
        category="PPI / PCI DSS",
        description="Payment card Primary Account Numbers (PAN), cardholder names, and expiration dates rendered unreadable in storage and disclosures.",
        legal_citation="PCI DSS v4.0 Req. 3.4",
        data_domain="PPI",
    ),
    # --- GLBA (Gramm-Leach-Bliley Act Banking - PPI) ---
    "GLBA-6801-NPI": VirginiaStatute(
        code="GLBA-6801-NPI",
        short_title="GLBA Nonpublic Personal Financial Information (NPI/PPI)",
        category="PPI / GLBA",
        description="Personally identifiable financial information provided by a consumer to a financial institution or resulting from a financial transaction.",
        legal_citation="15 U.S.C. § 6801 / 16 CFR Part 313 (GLBA)",
        data_domain="PPI",
    ),
    "GLBA-6802-ACCT": VirginiaStatute(
        code="GLBA-6802-ACCT",
        short_title="GLBA Consumer Bank, Routing & Loan Account Safeguards",
        category="PPI / Banking",
        description="Bank checking/savings account numbers, ABA routing transit numbers, IBAN/SWIFT codes, wire references, and loan/mortgage account identifiers.",
        legal_citation="15 U.S.C. § 6802(a) / GLBA Safeguards Rule",
        data_domain="PPI",
    ),
    # --- FRCP Rule 5.2 (Federal Court & Litigation Filings - PII / PPI) ---
    "FRCP-5.2(a)": VirginiaStatute(
        code="FRCP-5.2(a)",
        short_title="FRCP Rule 5.2 Court Filing Privacy Protection",
        category="Judicial / FRCP 5.2",
        description="Mandatory redaction in court filings of Social Security numbers, taxpayer-identification numbers, birth dates, minor names, and financial-account numbers.",
        legal_citation="Fed. R. Civ. P. 5.2(a)(1)-(4)",
        data_domain="PII",
    ),
    # --- AICPA SOC 2 / Trust Services Criteria (Enterprise & CPA Audit - PPI / PII) ---
    "AICPA-TSC-C1.1": VirginiaStatute(
        code="AICPA-TSC-C1.1",
        short_title="AICPA Trust Services Confidentiality (C1.1 / C1.2)",
        category="PPI / AICPA Confidentiality",
        description="Confidential commercial, financial, tax (EIN/TIN), and audit workpaper information protected from unauthorized disclosure.",
        legal_citation="AICPA Trust Services Criteria C1.1 / C1.2",
        data_domain="PPI",
    ),
    "AICPA-TSC-P1.0": VirginiaStatute(
        code="AICPA-TSC-P1.0",
        short_title="AICPA Trust Services Privacy Criteria (P1.0-P8.0)",
        category="PII / AICPA Privacy",
        description="Personal information collected, used, retained, and disclosed in accordance with AICPA Generally Accepted Privacy Principles.",
        legal_citation="AICPA Trust Services Criteria P1.0-P8.0",
        data_domain="PII",
    ),
}


CATEGORY_DOMAIN_MAP: Dict[str, str] = {
    # PII (Personally Identifiable Information)
    "ssn": "PII",
    "driver_license": "PII",
    "phone": "PII",
    "email": "PII",
    "dob": "PII",
    "applicant_name": "PII",
    "contact_pii": "PII",
    "property_location": "PII",
    "juvenile": "PII",
    "victim_witness": "PII",
    "informant": "PII",
    "tactical": "PII",
    "scholastic": "PII",
    "personnel": "PII",
    "endangered_species": "PII",
    "gps_coordinate": "PII",
    "wildlife_location": "PII",
    "signature": "PII",
    "handwritten": "PII",
    # PHI (Protected Health Information - HIPAA)
    "mrn": "PHI",
    "npi": "PHI",
    "health_plan_id": "PHI",
    "icd10_code": "PHI",
    "clinical_phi": "PHI",
    "patient_name": "PHI",
    "admission_date": "PHI",
    # PPI (Protected / Nonpublic Personal Financial Information - PCI DSS, GLBA, AICPA, FRCP 5.2)
    "credit_card": "PPI",
    "cvv_code": "PPI",
    "bank_account": "PPI",
    "routing_aba": "PPI",
    "iban_swift": "PPI",
    "tax_id_ein": "PPI",
    "loan_account": "PPI",
    "financial_ppi": "PPI",
    "confidential_proprietary": "PPI",
}


def get_data_domain_for_category(category: str) -> str:
    """Return the data domain ('PII', 'PHI', or 'PPI') for a given entity category."""
    cat_lower = category.lower().strip()
    if cat_lower in CATEGORY_DOMAIN_MAP:
        return CATEGORY_DOMAIN_MAP[cat_lower]
    if cat_lower.startswith("gps_"):
        return "PII"
    if any(k in cat_lower for k in ("mrn", "npi", "phi", "hipaa", "patient", "clinical", "health", "icd")):
        return "PHI"
    if any(k in cat_lower for k in ("card", "cvv", "bank", "routing", "aba", "iban", "loan", "glba", "pci", "ein", "tax", "financial", "ppi")):
        return "PPI"
    return "PII"


def get_statute(code: str) -> Optional[VirginiaStatute]:
    """Retrieve statute metadata by code."""
    return VIRGINIA_STATUTES.get(code)


def list_statutes() -> List[VirginiaStatute]:
    """Return list of all registered compliance statutes and regulations."""
    return list(VIRGINIA_STATUTES.values())


def get_statute_by_category(category: str, profile: Optional[str] = None) -> Optional[VirginiaStatute]:
    """Retrieve primary statute/regulation for a given category and optional compliance profile."""
    cat = category.lower().strip()

    # Profile-specific regulatory overrides
    if profile:
        prof = profile.lower().strip().replace("-", "_")
        if prof == "hipaa":
            hipaa_map = {
                "mrn": "HIPAA-164.514(b)-MRN",
                "npi": "HIPAA-164.514(b)-MRN",
                "health_plan_id": "HIPAA-164.514(b)-MRN",
                "icd10_code": "HIPAA-164.502-CLINICAL",
                "clinical_phi": "HIPAA-164.502-CLINICAL",
                "patient_name": "HIPAA-164.514(b)",
                "admission_date": "HIPAA-164.502-CLINICAL",
                "ssn": "HIPAA-164.514(b)",
                "dob": "HIPAA-164.514(b)",
                "phone": "HIPAA-164.514(b)",
                "email": "HIPAA-164.514(b)",
                "driver_license": "HIPAA-164.514(b)",
                "applicant_name": "HIPAA-164.514(b)",
                "contact_pii": "HIPAA-164.514(b)",
            }
            if cat in hipaa_map:
                return VIRGINIA_STATUTES.get(hipaa_map[cat])
        elif prof == "pci_dss":
            pci_map = {
                "credit_card": "PCI-DSS-3.4",
                "cvv_code": "PCI-DSS-3.3",
                "bank_account": "GLBA-6802-ACCT",
                "routing_aba": "GLBA-6802-ACCT",
                "iban_swift": "GLBA-6802-ACCT",
                "loan_account": "GLBA-6802-ACCT",
                "financial_ppi": "PCI-DSS-3.4",
            }
            if cat in pci_map:
                return VIRGINIA_STATUTES.get(pci_map[cat])
        elif prof == "glba":
            glba_map = {
                "bank_account": "GLBA-6802-ACCT",
                "routing_aba": "GLBA-6802-ACCT",
                "iban_swift": "GLBA-6802-ACCT",
                "loan_account": "GLBA-6802-ACCT",
                "credit_card": "PCI-DSS-3.4",
                "cvv_code": "PCI-DSS-3.3",
                "tax_id_ein": "GLBA-6801-NPI",
                "financial_ppi": "GLBA-6801-NPI",
                "ssn": "GLBA-6801-NPI",
                "dob": "GLBA-6801-NPI",
                "phone": "GLBA-6801-NPI",
                "email": "GLBA-6801-NPI",
                "applicant_name": "GLBA-6801-NPI",
            }
            if cat in glba_map:
                return VIRGINIA_STATUTES.get(glba_map[cat])
        elif prof == "frcp_5_2":
            frcp_map = {
                "ssn": "FRCP-5.2(a)",
                "tax_id_ein": "FRCP-5.2(a)",
                "dob": "FRCP-5.2(a)",
                "juvenile": "FRCP-5.2(a)",
                "bank_account": "FRCP-5.2(a)",
                "routing_aba": "FRCP-5.2(a)",
                "credit_card": "FRCP-5.2(a)",
                "loan_account": "FRCP-5.2(a)",
                "financial_ppi": "FRCP-5.2(a)",
            }
            if cat in frcp_map:
                return VIRGINIA_STATUTES.get(frcp_map[cat])
        elif prof == "aicpa_soc2":
            aicpa_map = {
                "tax_id_ein": "AICPA-TSC-C1.1",
                "bank_account": "AICPA-TSC-C1.1",
                "routing_aba": "AICPA-TSC-C1.1",
                "iban_swift": "AICPA-TSC-C1.1",
                "loan_account": "AICPA-TSC-C1.1",
                "financial_ppi": "AICPA-TSC-C1.1",
                "confidential_proprietary": "AICPA-TSC-C1.1",
                "credit_card": "PCI-DSS-3.4",
                "ssn": "AICPA-TSC-P1.0",
                "dob": "AICPA-TSC-P1.0",
                "phone": "AICPA-TSC-P1.0",
                "email": "AICPA-TSC-P1.0",
                "applicant_name": "AICPA-TSC-P1.0",
            }
            if cat in aicpa_map:
                return VIRGINIA_STATUTES.get(aicpa_map[cat])

    # Default mapping (preserves backwards compatibility with all existing FOIA/VFOIA tests)
    mapping = {
        "ssn": "VA-2.2-3705.1(10)",
        "driver_license": "VA-2.2-3705.1(10)",
        "phone": "VA-2.2-3705.1(10)",
        "email": "VA-2.2-3705.1(10)",
        "dob": "VA-2.2-3705.1(10)",
        "credit_card": "VA-2.2-3705.1(10)",
        "juvenile": "VA-16.1-301",
        "victim_witness": "VA-19.2-11.2",
        "informant": "VA-2.2-3705.2(1)",
        "tactical": "VA-2.2-3705.2(1)",
        "scholastic": "VA-2.2-3705.4(1)",
        "personnel": "VA-2.2-3705.1(1)",
        "endangered_species": "VA-2.2-3705.7(2)",
        "gps_coordinate": "VA-2.2-3705.7(2)",
        "wildlife_location": "VA-2.2-3705.7(2)",
        # PHI defaults
        "mrn": "HIPAA-164.514(b)-MRN",
        "npi": "HIPAA-164.514(b)-MRN",
        "health_plan_id": "HIPAA-164.514(b)-MRN",
        "icd10_code": "HIPAA-164.502-CLINICAL",
        "clinical_phi": "HIPAA-164.502-CLINICAL",
        "patient_name": "HIPAA-164.514(b)",
        "admission_date": "HIPAA-164.502-CLINICAL",
        # PPI defaults
        "cvv_code": "PCI-DSS-3.3",
        "bank_account": "GLBA-6802-ACCT",
        "routing_aba": "GLBA-6802-ACCT",
        "iban_swift": "GLBA-6802-ACCT",
        "tax_id_ein": "AICPA-TSC-C1.1",
        "loan_account": "GLBA-6802-ACCT",
        "financial_ppi": "GLBA-6801-NPI",
        "confidential_proprietary": "AICPA-TSC-C1.1",
    }
    code = mapping.get(cat)
    return VIRGINIA_STATUTES.get(code) if code else None
