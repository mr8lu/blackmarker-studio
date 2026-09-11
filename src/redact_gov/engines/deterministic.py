"""Tier 1 Deterministic Fast Path redaction engine."""

import re
from typing import List, Tuple
from redact_gov.core.models import RedactionEntity
from redact_gov.core.statutes import get_statute_by_category


def luhn_checksum_valid(card_number_str: str) -> bool:
    """Validate credit card number using Luhn algorithm."""
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


class DeterministicRedactionEngine:
    """Sub-second regex and pattern matching engine for high-confidence PII and sensitive coordinates."""

    PATTERNS = [
        # Social Security Number (SSN): 3 digits, dash/space, 2 digits, dash/space, 4 digits
        (
            "ssn",
            re.compile(
                r"\b\d{3}[- ]\d{2}[- ]\d{4}\b"
            ),
            0.99,
        ),
        # Virginia Driver's License: 1 letter + 8 digits (standard format)
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
        # Dates of birth explicitly labeled
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
        # Credit Card Numbers
        (
            "credit_card",
            re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b"),
            0.96,
        ),
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
    ]

    def scan_text(self, text: str, page_number: int = 1) -> List[RedactionEntity]:
        """Scan text and return identified RedactionEntity targets."""
        entities: List[RedactionEntity] = []
        seen_spans = set()

        for category, pattern, confidence in self.PATTERNS:
            for match in pattern.finditer(text):
                # For capture groups (e.g. for DOB/GPS with prefix), capture only the value group
                if match.groups() and match.group(1):
                    matched_text = match.group(1)
                    span = match.span(1)
                else:
                    matched_text = match.group(0)
                    span = match.span(0)

                # Avoid duplicate spans
                if span in seen_spans:
                    continue
                seen_spans.add(span)

                # Extra check for credit card
                if category == "credit_card" and not luhn_checksum_valid(matched_text):
                    continue

                statute = get_statute_by_category(category)
                statute_code = statute.code if statute else "VA-2.2-3705.1(10)"

                entities.append(
                    RedactionEntity(
                        text=matched_text.strip(),
                        category=category,
                        statute_code=statute_code,
                        confidence=confidence,
                        page_number=page_number,
                        tier="tier1_deterministic",
                    )
                )

        return entities
