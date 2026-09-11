"""Virginia Code statutory exemptions database for FOIA/VFOIA compliance."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class VirginiaStatute:
    code: str
    short_title: str
    category: str
    description: str
    legal_citation: str
    default_confidence: float = 0.95


VIRGINIA_STATUTES: Dict[str, VirginiaStatute] = {
    "VA-2.2-3705.1(1)": VirginiaStatute(
        code="VA-2.2-3705.1(1)",
        short_title="Personnel Records",
        category="Personnel",
        description="Personnel information concerning identifiable individuals held in personnel files.",
        legal_citation="Va. Code § 2.2-3705.1(1)",
    ),
    "VA-2.2-3705.1(10)": VirginiaStatute(
        code="VA-2.2-3705.1(10)",
        short_title="Personal Privacy & PII",
        category="Privacy",
        description="Social Security Numbers, driver's license numbers, and personal contact numbers not held in official capacity.",
        legal_citation="Va. Code § 2.2-3705.1(10)",
    ),
    "VA-2.2-3705.2(1)": VirginiaStatute(
        code="VA-2.2-3705.2(1)",
        short_title="Law Enforcement Tactical Information",
        category="Law Enforcement",
        description="Tactical operations plans, undercover officer identities, and confidential informant records.",
        legal_citation="Va. Code § 2.2-3705.2(1)",
    ),
    "VA-2.2-3705.4(1)": VirginiaStatute(
        code="VA-2.2-3705.4(1)",
        short_title="Scholastic & Disciplinary Records",
        category="Education",
        description="Scholastic records containing information directly related to an identifiable student, including disciplinary proceedings.",
        legal_citation="Va. Code § 2.2-3705.4(1)",
    ),
    "VA-16.1-301": VirginiaStatute(
        code="VA-16.1-301",
        short_title="Juvenile Law-Enforcement Records",
        category="Juvenile",
        description="Law-enforcement records and reports concerning children and juveniles subject to proceedings or investigations.",
        legal_citation="Va. Code § 16.1-301",
    ),
    "VA-19.2-11.2": VirginiaStatute(
        code="VA-19.2-11.2",
        short_title="Crime Victim & Witness Identification",
        category="Victim/Witness",
        description="Names, residential addresses, and telephone numbers of crime victims and witnesses.",
        legal_citation="Va. Code § 19.2-11.2",
    ),
    "VA-2.2-3705.7(2)": VirginiaStatute(
        code="VA-2.2-3705.7(2)",
        short_title="Endangered & Rare Species Locations",
        category="Endangered Species",
        description="Information related to the Virginia Natural Heritage Program database identifying specific locations of rare, threatened, or endangered plant or animal species, natural communities, or cave resources where disclosure would jeopardize species survival or risk unlawful taking.",
        legal_citation="Va. Code § 2.2-3705.7(2)",
    ),
}


def get_statute(code: str) -> Optional[VirginiaStatute]:
    """Retrieve statute metadata by code."""
    return VIRGINIA_STATUTES.get(code)


def list_statutes() -> List[VirginiaStatute]:
    """Return list of all registered Virginia FOIA statutes."""
    return list(VIRGINIA_STATUTES.values())


def get_statute_by_category(category: str) -> Optional[VirginiaStatute]:
    """Retrieve primary statute for a given category."""
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
    }
    code = mapping.get(category.lower())
    return VIRGINIA_STATUTES.get(code) if code else None
