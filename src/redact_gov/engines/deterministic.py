"""Tier 1 Deterministic Fast Path redaction engine for PII, PHI (HIPAA), and PPI (PCI DSS / GLBA / AICPA / FRCP 5.2)."""

import re
from typing import Iterable, List, Optional, Set
from redact_gov.core.models import RedactionEntity
from redact_gov.core.statutes import get_data_domain_for_category, get_statute_by_category


def luhn_checksum_valid(card_number_str: str) -> bool:
    """Validate credit card Primary Account Number (PAN) using the Luhn algorithm."""
    digits = [int(c) for c in card_number_str if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False

    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = d * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += d
    return checksum % 10 == 0


def aba_routing_checksum_valid(routing_str: str) -> bool:
    """Validate 9-digit US ABA routing transit number using the standard 3-7-1 weighted modulus-10 check."""
    digits = [int(c) for c in routing_str if c.isdigit()]
    if len(digits) != 9:
        return False
    weights = (3, 7, 1, 3, 7, 1, 3, 7, 1)
    total = sum(d * w for d, w in zip(digits, weights))
    return total > 0 and total % 10 == 0


class DeterministicRedactionEngine:
    """Sub-second regex and algorithmic pattern matching engine across PII, PHI, and PPI domains."""

    PATTERNS = [
        # --- PII (Personally Identifiable Information: FOIA, FRCP 5.2, AICPA Privacy) ---
        # Social Security Number (SSN): 3 digits, dash/space, 2 digits, dash/space, 4 digits
        (
            "ssn",
            re.compile(r"\b\d{3}[- ]\d{2}[- ]\d{4}\b"),
            0.99,
        ),
        # State Driver's License (1 letter + 8 digits standard format)
        (
            "driver_license",
            re.compile(r"\b[A-Za-z][-\s]?\d{8}\b"),
            0.98,
        ),
        # Phone Numbers (standard US 10-digit with parens, dashes, or spaces)
        (
            "phone",
            re.compile(
                r"(?:\+?1[-. ]?)?\(?[2-9]\d{2}\)?[-. ]?[2-9]\d{2}[-. ]?\d{4}\b"
            ),
            0.95,
        ),
        # Dates of birth explicitly labeled (PII / FRCP 5.2 / HIPAA)
        (
            "dob",
            re.compile(
                r"(?i)\b(?:DOB|Date of Birth|Birth Date)[\s:]*([0-1]?\d[/-][0-3]?\d[/-](?:19|20)?\d{2})\b"
            ),
            0.97,
        ),
        # Email addresses
        (
            "email",
            re.compile(
                r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b"
            ),
            0.95,
        ),
        # --- PHI (Protected Health Information: HIPAA 45 CFR § 164.514 Safe Harbor) ---
        # Medical Record Number (MRN)
        (
            "mrn",
            re.compile(
                r"(?i)\b(?:MRN|Medical Record(?:\s*(?:No|Number|#))?|Patient ID|Chart(?:\s*(?:No|#))?)[\s:#-]*([A-Z0-9]{2,4}-?\d{4,10}|\d{6,10})\b"
            ),
            0.98,
        ),
        # National Provider Identifier (NPI - 10 digits)
        (
            "npi",
            re.compile(
                r"(?i)\b(?:NPI|Provider NPI)[\s:#-]*([12]\d{9})\b"
            ),
            0.98,
        ),
        # Health Plan Beneficiary / Member / Policy ID
        (
            "health_plan_id",
            re.compile(
                r"(?i)\b(?:Health Plan(?:\s*ID)?|Member ID|Beneficiary ID|Subscriber ID|Policy(?:\s*(?:No|Number|#|ID))?|Medicaid ID|Medicare(?:\s*#|\s*ID)?)[\s:#-]*([A-Z0-9]{3,5}-?[A-Z0-9]{4,10})\b"
            ),
            0.97,
        ),
        # ICD-10 / CPT Clinical Diagnosis Codes
        (
            "icd10_code",
            re.compile(
                r"(?i)\b(?:ICD-?10|Dx|Diagnosis(?:\s*Code)?)[\s:#-]*([A-TV-Z]\d{2}(?:\.[A-Z0-9]{1,4})?)\b"
            ),
            0.96,
        ),
        # Hospital Admission / Discharge / Treatment Dates (HIPAA Safe Harbor § 164.514(b)(2)(i)(C))
        (
            "admission_date",
            re.compile(
                r"(?i)\b(?:Admit(?:ted)?(?:\s*Date)?|Admission Date|Discharge(?:d)?(?:\s*Date)?|Date of Service|DOS)[\s:]*([0-1]?\d[/-][0-3]?\d[/-](?:19|20)\d{2})\b"
            ),
            0.96,
        ),
        # --- PPI (Protected Personal Financial Information: PCI DSS, GLBA, AICPA, FRCP 5.2) ---
        # Credit / Payment Card Primary Account Numbers (PAN - 16-digit and 15-digit Amex)
        (
            "credit_card",
            re.compile(r"\b(?:\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}|\d{4}[- ]?\d{6}[- ]?\d{5})\b"),
            0.97,
        ),
        # PCI DSS Sensitive Authentication Data (CVV / CVC / CID)
        (
            "cvv_code",
            re.compile(r"(?i)\b(?:CVV2?|CVC2?|CID|Security Code)[\s:#-]*(\d{3,4})\b"),
            0.98,
        ),
        # GLBA / FRCP 5.2 ABA Routing Transit Number (9 digits)
        (
            "routing_aba",
            re.compile(r"(?i)\b(?:Routing(?:\s*(?:No|Number|#))?|ABA(?:\s*Routing)?)[\s:#-]*(\d{9})\b"),
            0.98,
        ),
        # GLBA / FRCP 5.2 Bank Checking / Savings / Wire Account Number
        (
            "bank_account",
            re.compile(
                r"(?i)\b(?:Bank\s*Account|Checking\s*Account|Savings\s*Account|Wire\s*Account|Acct(?:\s*(?:No|Number|#))?|Account(?:\s*(?:No|Number|#)))[\s:#-]*([A-Z0-9]{2,4}-?\d{6,14}|\d{8,17})\b"
            ),
            0.97,
        ),
        # International Bank Account Number (IBAN)
        (
            "iban_swift",
            re.compile(
                r"(?i)\b(?:IBAN[\s:#-]*)?([A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]?){0,16})\b"
            ),
            0.97,
        ),
        # Employer Identification Number / Taxpayer ID (EIN / TIN: AICPA & FRCP 5.2)
        (
            "tax_id_ein",
            re.compile(
                r"(?i)\b(?:EIN|TIN|Tax(?:\s*ID|\s*Identification(?:\s*No)?)|FEIN)[\s:#-]*(\d{2}-\d{7})\b"
            ),
            0.98,
        ),
        # Loan / Mortgage / Credit Account Identifier (GLBA)
        (
            "loan_account",
            re.compile(
                r"(?i)\b(?:Loan(?:\s*(?:No|Number|#|ID))?|Mortgage(?:\s*(?:No|Acct|#))?)[\s:#-]*([A-Z]{2,4}-\d{5,12}|\d{7,14})\b"
            ),
            0.96,
        ),
        # --- Geographic / Environmental Coordinates ---
        # DMS GPS Coordinates (e.g. 37°58'42.1"N, 79°49'15.3"W)
        (
            "gps_coordinate",
            re.compile(
                r"""\b\d{1,2}°\s*\d{1,2}['′]\s*(?:\d{1,2}(?:\.\d+)?)?["″]?\s*[NSEW][,\s]+\d{1,3}°\s*\d{1,2}['′]\s*(?:\d{1,2}(?:\.\d+)?)?["″]?\s*[NSEW]\b""",
                re.IGNORECASE,
            ),
            0.98,
        ),
        # Decimal GPS Coordinates with prefix (e.g. GPS: 37.9821, -79.8214 or Coordinates: 38.1245° N, 78.4321° W)
        (
            "gps_coordinate",
            re.compile(
                r"""(?i)\b(?:GPS|Coordinates?|Lat(?:itude)?\/Long(?:itude)?|Location)[\s:]*([+-]?\d{1,2}\.\d{4,8}\s*°?\s*[NS]?[,\s]+[+-]?\d{1,3}\.\d{4,8}\s*°?\s*[EW]?)\b"""
            ),
            0.98,
        ),
        # Standalone Decimal Lat/Long within Virginia and Mid-Atlantic geographic bounds
        (
            "gps_coordinate",
            re.compile(
                r"""\b(3[6-9]\.\d{4,7}\s*°?\s*[Nn]?[,\s]+-?(?:7[5-9]|8[0-3])\.\d{4,7}\s*°?\s*[Ww]?)\b"""
            ),
            0.96,
        ),
        # Labeled or standalone Decimal Latitude in Virginia bounds
        (
            "gps_coordinate",
            re.compile(
                r"""(?i)(?<!\w)(?:LAT(?:ITUDE)?[\s:]+)?([+-]?3[6-9]\.\d{4,8}\s*°?(?:\s*[Nn]|\s*LAT(?:ITUDE)?\.?)?)\b"""
            ),
            0.96,
        ),
        # Labeled or standalone Decimal Longitude in Virginia bounds
        (
            "gps_coordinate",
            re.compile(
                r"""(?i)(?<!\w)(?:LONG(?:ITUDE)?[\s:]+)?([+-]?(?:7[5-9]|8[0-3])\.\d{4,8}\s*°?(?:\s*[Ww]|\s*LONG(?:ITUDE)?\.?)?)\b"""
            ),
            0.96,
        ),
    ]

    def scan_text(
        self,
        text: str,
        page_number: int = 1,
        enabled_domains: Optional[Iterable[str]] = None,
        profile: Optional[str] = None,
    ) -> List[RedactionEntity]:
        """Scan text and return identified RedactionEntity targets filtered by a-la-carte domains."""
        entities: List[RedactionEntity] = []
        seen_spans = set()
        active_domains: Optional[Set[str]] = (
            {str(d).upper().strip() for d in enabled_domains}
            if enabled_domains is not None
            else None
        )

        for category, pattern, confidence in self.PATTERNS:
            domain = get_data_domain_for_category(category)
            if active_domains is not None and domain not in active_domains:
                continue

            for match in pattern.finditer(text):
                # For capture groups (e.g. for DOB/MRN/Bank/GPS with prefix), capture only the value group
                if match.groups() and match.group(1):
                    matched_text = match.group(1)
                    span = match.span(1)
                else:
                    matched_text = match.group(0)
                    span = match.span(0)

                if span in seen_spans:
                    continue

                if category == "credit_card" and not luhn_checksum_valid(matched_text):
                    continue

                seen_spans.add(span)

                statute = get_statute_by_category(category, profile=profile)
                statute_code = statute.code if statute else "VA-2.2-3705.1(10)"

                entities.append(
                    RedactionEntity(
                        text=matched_text.strip(),
                        category=category,
                        statute_code=statute_code,
                        confidence=confidence,
                        page_number=page_number,
                        tier="tier1_deterministic",
                        data_domain=domain,
                    )
                )

        return entities
