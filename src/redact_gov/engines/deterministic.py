"""Tier 1 Deterministic Regex and Algorithmic Validation Engine across PII, PHI (HIPAA), and PPI (PCI DSS / GLBA / AICPA / FRCP 5.2)."""

import re
from typing import Dict, Iterable, List, Optional, Pattern, Set
from redact_gov.core.models import RedactionEntity
from redact_gov.core.statutes import get_data_domain_for_category, get_statute_by_category


def luhn_checksum_valid(card_number: str) -> bool:
    """Validate credit card number using Luhn mod-10 algorithm."""
    digits = [int(d) for d in card_number if d.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    # Reject trivial all-zero or repeating single-digit sequences
    if len(set(digits)) == 1:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def aba_routing_checksum_valid(routing: str) -> bool:
    """Validate 9-digit US ABA routing transit number using the standard position-weighted mod-10 algorithm."""
    digits = [int(c) for c in routing if c.isdigit()]
    if len(digits) != 9:
        return False
    if len(set(digits)) == 1:
        return False
    # First two digits of valid Federal Reserve routing symbols fall in 00-12, 21-32, 61-72, or 80
    prefix = digits[0] * 10 + digits[1]
    valid_prefix = (
        (0 <= prefix <= 12)
        or (21 <= prefix <= 32)
        or (61 <= prefix <= 72)
        or (prefix == 80)
    )
    if not valid_prefix:
        return False
    weighted_sum = (
        3 * (digits[0] + digits[3] + digits[6])
        + 7 * (digits[1] + digits[4] + digits[7])
        + 1 * (digits[2] + digits[5] + digits[8])
    )
    return weighted_sum % 10 == 0


class DeterministicRedactionEngine:
    """Sub-second regex and algorithmic scanner for structured PII, PHI, and PPI identifiers."""

    def __init__(self):
        self.patterns: Dict[str, Pattern] = {
            # =========================================================================
            # 1. PII (Personally Identifiable Information - FOIA / Privacy / FRCP 5.2)
            # =========================================================================
            # Social Security Number (standard XXX-XX-XXXX, space-grouped, or multi-space comb cells)
            "ssn": re.compile(
                r"\b(?!000|666)\d{3}(?:[- ]|[ \t]{1,4})(?!00)\d{2}(?:[- ]|[ \t]{1,4})(?!0000)\d{4}\b"
            ),
            # Contextual / Labeled / Comb-box SSN (e.g., "Social Security No.: 123456789", "Schedule INC/CG 123456789", "You 123456789")
            "ssn_contextual": re.compile(
                r"(?i)(?:SSN|Social\s+Security(?:\s*(?:No\.?|Number|#))?|Schedule\s+INC/CG|Spouse\s+SSN|\bYou)\b[^\d\n]{0,40}((?!000|666)\d[ \t]*\d[ \t]*\d[ \t-]*(?!0[ \t]*0)\d[ \t]*\d[ \t-]*(?!0[ \t]*0[ \t]*0[ \t]*0)\d[ \t]*\d[ \t]*\d[ \t]*\d)\b"
            ),
            # Virginia Driver's License (1 letter + 8 digits standard format)
            "va_driver_license": re.compile(
                r"\b(?:DL|License|Driver['\u2019]?s?\s*License|VADL)?[\s:#-]*([A-Z]\d{8}|\d{9})\b",
                re.IGNORECASE,
            ),
            # US Phone Number (with optional area code parens/dashes)
            "phone": re.compile(
                r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]\d{4}\b"
            ),
            # Email Address
            "email": re.compile(
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
            ),
            # Date of Birth (when preceded by DOB, Birth, Born, or Your/Spouse's Birth Date, including comb-box spacing)
            "dob": re.compile(
                r"(?i)\b(?:DOB|Date\s+of\s+Birth|(?:Your|Spouse['\u2019]?s)\s+Birth\s+Date|Birth\s*Date)[\s:]*(\d[ \t]*\d?[ \t]*[/-][ \t]*\d[ \t]*\d?[ \t]*[/-][ \t]*\d(?:[ \t]*\d){1,3}|\d{4}-\d{2}-\d{2})\b"
            ),
            # US Passport Number (labeled)
            "passport_us": re.compile(
                r"(?i)\b(?:Passport(?:\s*(?:No|Number|#))?)[\s:#-]*([A-Z0-9]{9})\b"
            ),
            # Employer Identification Number (labeled contiguous/comb-spaced OR standalone XX-XXXXXXX IRS format)
            "ein": re.compile(
                r"(?i)(?:\b(?:EIN|FEIN|Employer\s*ID(?:entification)?(?:\s*(?:No\.?|Number|#))?|Tax\s*ID|TIN)[\s:#-]*((?:\d[ \t-]*){8}\d)\b|(?<!OMB\s)(?<!No\.\s)\b((?!00|07|08|09|17|18|19|28|29|49|69|70|78|79|89|96|97)\d{2}-\d{7})\b)"
            ),
            # Standalone 9-digit single-character comb-box sequence on forms (e.g., Schedule C Box D EIN)
            "comb_9digit": re.compile(
                r"(?m)^[ \t]*(\d(?:[ \t]+\d){8})[ \t]*$"
            ),
            # Coordinates (Decimal Degrees & Degrees/Minutes/Seconds)
            "gps_coordinate": re.compile(
                r"(?:\b[3][6-9]\.\d{3,6}\s*,\s*-?[7-8]\d\.\d{3,6}\b|\b\d{2}°\s*\d{1,2}'\s*\d{1,2}(?:\.\d+)?\"?\s*[NS]\s*,?\s*\d{2,3}°\s*\d{1,2}'\s*\d{1,2}(?:\.\d+)?\"?\s*[EW]\b)",
                re.IGNORECASE,
            ),
            # =========================================================================
            # 2. PHI (Protected Health Information - HIPAA 45 CFR § 164.514(b))
            # =========================================================================
            # Medical Record Number (MRN)
            "mrn": re.compile(
                r"(?i)\b(?:MRN|Medical\s*Record(?:\s*(?:No|Number|#))?|Patient\s*ID|Chart\s*(?:No|Number|#))[\s:#-]*([A-Z0-9]{2,4}-\d{4,10}|\d{6,12})\b"
            ),
            # National Provider Identifier (10-digit NPI starting with 1 or 2, labeled)
            "npi": re.compile(
                r"(?i)\b(?:NPI|National\s*Provider\s*(?:ID|Identifier))[\s:#-]*([12]\d{9})\b"
            ),
            # Health Plan Beneficiary / Member / Subscriber / Policy Number
            # Requires explicit ID/No/Number/# after "Health Plan" to avoid matching prose like "health plan following"
            "health_plan_id": re.compile(
                r"(?i)\b(?:Member\s*ID|Subscriber\s*ID|Health\s*Plan\s*(?:ID|No\.?|Number|#)|Policy\s*(?:No\.?|Number|#))[\s:#-]*([A-Z0-9]{3,4}[- ]?[A-Z0-9]{4,10})\b"
            ),
            # ICD-10-CM Clinical Diagnosis Code (labeled or standard format e.g. J45.909, E11.9, F32.1)
            "icd10_code": re.compile(
                r"(?i)\b(?:ICD-?10(?:-CM)?|Dx|Diagnosis\s*Code)[\s:#-]*([A-TV-Z]\d{2}(?:\.[A-Z0-9]{1,4})?)\b"
            ),
            # =========================================================================
            # 3. PPI (Personal Financial / Payment Information - PCI DSS / GLBA / AICPA)
            # =========================================================================
            # Credit / Debit Card PAN (13-19 digits, validated with Luhn algorithm)
            "credit_card": re.compile(
                r"\b(?:\d{4}[-\s]?){3}\d{1,4}\b"
            ),
            # Card Security Code (CVV / CVC / CVV2 / CID when labeled, excluding PDF (cid:XX) font tags)
            "cvv_code": re.compile(
                r"(?i)(?<![(\w])(?:CVV|CVC|CVV2|CVC2|CSC|(?:Card|Security|Amex)\s+CID)\b[\s:=-]*(\d{3,4})\b"
            ),
            # US ABA Bank Routing Transit Number (labeled, supports contiguous, comb-box spaces, and underline-interleaved digits)
            "routing_aba": re.compile(
                r"(?i)\b(?:RTN|Routing(?:\s+Transit)?(?:\s*(?:No\.?|Number|#))?|ABA(?:\s*Routing)?)[\s:#._-]*((?:\d[ \t_]*){8}\d)\b"
            ),
            # Bank / Checking / Savings / Loan Account Number (labeled, supports contiguous, comb-box spaces, and underline-interleaved digits)
            "bank_account": re.compile(
                r"(?i)\b(?:Bank\s*Account|Checking\s*Account|Savings\s*Account|Loan\s*(?:No\.?|Number|#)|Acct(?:\s*(?:No\.?|Number|#))?|Account(?:\s*(?:No\.?|Number|#)))[\s:#._-]*((?:\d[ \t_]*){4,16}[A-Z0-9](?:[ \t_]*\d)*|[A-Z0-9]{6,17})\b"
            ),
            # International Bank Account Number (IBAN) or SWIFT/BIC (labeled or standard IBAN prefix)
            "iban_swift": re.compile(
                r"\b(?:[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]?){0,16}|(?:SWIFT|BIC)[\s:#-]*[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b"
            ),
        }

    def scan_text(
        self,
        text: str,
        page_number: int = 1,
        enabled_domains: Optional[Iterable[str]] = None,
        profile: Optional[str] = None,
    ) -> List[RedactionEntity]:
        """
        Scan page text and return detected deterministic RedactionEntities
        filtered by `enabled_domains` (e.g. ['PII', 'PHI', 'PPI']).
        """
        active_domains: Optional[Set[str]] = (
            {str(d).upper().strip() for d in enabled_domains}
            if enabled_domains is not None
            else None
        )
        entities: List[RedactionEntity] = []
        seen_spans = set()

        for raw_category, pattern in self.patterns.items():
            category = "ssn" if raw_category == "ssn_contextual" else raw_category
            if raw_category == "comb_9digit":
                category = "ein"

            for match in pattern.finditer(text):
                # Extract first non-None capture group if groups exist
                if match.lastindex:
                    group_idx = next(
                        (i for i in range(1, (match.lastindex or 0) + 1) if match.group(i) is not None),
                        0,
                    )
                    matched_text = match.group(group_idx).strip()
                    span = match.span(group_idx)
                else:
                    matched_text = match.group(0).strip()
                    span = match.span(0)

                if raw_category == "va_driver_license":
                    raw_match = match.group(0)
                    prefix_ctx = text[max(0, match.start() - 24) : match.start()].lower()
                    if any(
                        lbl in prefix_ctx
                        for lbl in ("member", "plan", "policy", "subscriber", "mrn", "patient")
                    ):
                        continue
                    has_prefix = any(
                        k in raw_match.lower() for k in ["dl", "license", "vadl"]
                    )
                    if not has_prefix and not re.match(r"^[A-Z]\d{8}$", matched_text):
                        continue
                    category = "driver_license"

                if raw_category in ("routing_aba", "bank_account") and "_" in matched_text:
                    # Normalize underline-interleaved form fields (e.g. "_1_2 _3_4...") to clean digits
                    matched_text = re.sub(r"[ \t_]+", "", matched_text)

                if raw_category == "routing_aba":
                    if not aba_routing_checksum_valid(matched_text):
                        continue

                if raw_category == "comb_9digit":
                    # Check if already matched as routing_aba or ssn, or if it's an ABA routing number
                    if any(s[0] <= span[0] and span[1] <= s[1] for s in seen_spans):
                        continue
                    if aba_routing_checksum_valid(matched_text) and re.search(
                        r"(?i)\b(?:routing|rtn|direct\s+deposit|account\s+number)\b", text
                    ):
                        category = "routing_aba"
                    else:
                        category = "ein"

                if category == "credit_card":
                    if not luhn_checksum_valid(matched_text):
                        continue

                # Ensure alphanumeric ID categories contain digits (prevents English prose false positives)
                if category in ("mrn", "health_plan_id", "bank_account", "passport_us"):
                    digit_cnt = sum(c.isdigit() for c in matched_text)
                    if digit_cnt < 2:
                        continue

                domain = get_data_domain_for_category(category)
                if active_domains is not None and domain not in active_domains:
                    continue

                if span in seen_spans:
                    continue
                seen_spans.add(span)

                statute = get_statute_by_category(category, profile=profile)
                statute_code = statute.code if statute else "VA-2.2-3705.1(10)"

                entities.append(
                    RedactionEntity(
                        text=matched_text,
                        category=category,
                        statute_code=statute_code,
                        confidence=1.0,
                        page_number=page_number,
                        tier="tier1_regex",
                        data_domain=domain,
                    )
                )

        # Form-context unhyphenated 9-digit SSN / FEIN / Account Number scanner
        # Catches tabular 9-digit SSNs/FEINs and state employer account IDs on tax/withholding schedules
        if (active_domains is None or "PII" in active_domains) and re.search(
            r"(?i)\b(?:SSN|Social\s+Security|Form\s+1040|Form\s+760|Schedule\s+INC|FEIN|Withholding)\b",
            text,
        ):
            for m in re.finditer(r"\b(?!000|666|9\d{2})\d{3}(?!00)\d{2}(?!0000)\d{4}\b", text):
                span = m.span(0)
                if any(s[0] <= span[0] and span[1] <= s[1] for s in seen_spans):
                    continue
                # Exclude 9-digit ZIP+4 codes preceded by a 2-letter US State abbreviation (e.g. "FL 328011234")
                prefix_ctx = text[max(0, span[0] - 12) : span[0]]
                if re.search(r"\b[A-Z]{2}[ \t]+$", prefix_ctx):
                    continue
                val = m.group(0).strip()
                seen_spans.add(span)
                statute = get_statute_by_category("ssn", profile=profile)
                entities.append(
                    RedactionEntity(
                        text=val,
                        category="ssn",
                        statute_code=statute.code if statute else "VA-2.2-3705.1(10)",
                        confidence=0.98,
                        page_number=page_number,
                        tier="tier1_regex",
                        data_domain="PII",
                    )
                )

            # State withholding employer account numbers (e.g. VA Account Number 10-18 alphanumeric with digits)
            if "Account Number" in text or "FEIN" in text:
                for m in re.finditer(r"\b(\d{9,12}[A-Z]\d{2,4})\b", text):
                    span = m.span(1)
                    if any(s[0] <= span[0] and span[1] <= s[1] for s in seen_spans):
                        continue
                    seen_spans.add(span)
                    statute = get_statute_by_category("ein", profile=profile)
                    entities.append(
                        RedactionEntity(
                            text=m.group(1).strip(),
                            category="ein",
                            statute_code=statute.code if statute else "VA-2.2-3705.1(10)",
                            confidence=0.97,
                            page_number=page_number,
                            tier="tier1_regex",
                            data_domain="PII",
                        )
                    )

        return entities
