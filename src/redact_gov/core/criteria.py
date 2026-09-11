"""Centralized registry for role and context constraints governing redaction criteria."""

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Dict, List, Optional, Set, Tuple


class SubjectRole(str, Enum):
    """Subject/Actor role in the document establishing statutory protection or exemption."""
    PUBLIC_OFFICIAL = "public_official"      # Elected officials, agency heads in official duties (EXEMPT from PII redaction)
    PUBLIC_EMPLOYEE = "public_employee"      # General government staff (business info public, private PII protected)
    PRIVATE_CITIZEN = "private_citizen"      # Applicants, landowners, residents (Full privacy under VA-2.2-3705.1(10))
    JUVENILE = "juvenile"                    # Minors, students, children (Mandatory withholding under VA-16.1-301)
    VICTIM_WITNESS = "victim_witness"        # Crime victims, reporting witnesses (Safeguarded under VA-19.2-11.2)
    CONFIDENTIAL_SOURCE = "confidential_source"  # Informants, undercover officers (Withheld under VA-2.2-3705.2(1))
    COMMERCIAL_ENTITY = "commercial_entity"  # Businesses, consultants, contractors


class ReleaseProfile(str, Enum):
    """Contextual redaction release profile defining the statutory posture."""
    PUBLIC_FOIA = "public_foia"                    # Standard Virginia FOIA public release
    STRICT_PRIVACY = "strict_privacy"              # Redact all coordinates, drawing blocks, and private names
    ENVIRONMENTAL_REVIEW = "environmental_review"  # Protect species habitats, impact sites, and private parcels
    LAW_ENFORCEMENT = "law_enforcement"            # Strict tactical, informant, juvenile, and victim safeguarding


class CoordinatePolicy(str, Enum):
    """Policy governing geographic coordinate redactions."""
    ALL = "all"
    SENSITIVE_ONLY = "sensitive-only"
    NONE = "none"


class CoordinateContextType(str, Enum):
    """Semantic context categories for geographic coordinates."""
    ENDANGERED_SPECIES_HABITAT = "endangered_species_habitat"
    ENVIRONMENTAL_IMPACT_SITE = "environmental_impact_site"
    PRIVATE_PROPERTY = "private_property"
    CRITICAL_INFRASTRUCTURE = "critical_infrastructure"
    PROJECT_SITE_GENERAL = "project_site_general"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FormFieldCriterion:
    """Rule defining how an AcroForm field or table box prompt triggers redaction."""
    id: str
    match_keywords: List[str]
    target_category: str
    statute_code: str
    statute_title: str
    target_role: SubjectRole = SubjectRole.PRIVATE_CITIZEN
    confidence: float = 0.95
    description: str = ""

    def matches_title(self, field_title: str) -> bool:
        """Check if a form field title or prompt matches this criterion."""
        title_lower = field_title.lower()
        return any(kw.lower() in title_lower for kw in self.match_keywords)


@dataclass(frozen=True)
class CoordinateContextCriterion:
    """Rule defining how surrounding semantic context classifies a coordinate."""
    context_type: str
    statute_code: str
    statute_title: str
    keywords: Set[str]
    confidence: float = 0.95
    redact_in_sensitive_only: bool = True
    description: str = ""

    def matches_context(self, context_text: str) -> bool:
        """Check if surrounding text contains any defining keywords."""
        ctx_lower = context_text.lower()
        return any(kw in ctx_lower for kw in self.keywords)


@dataclass
class RoleConstraint:
    """Role-based allowlisting and exemption constraints."""
    role: SubjectRole
    allowlisted_titles: Set[str] = field(default_factory=set)
    exempt_from_categories: Set[str] = field(default_factory=set)


# --- Centralized Default Definitions ---

DEFAULT_ROLE_CONSTRAINTS: Dict[SubjectRole, RoleConstraint] = {
    SubjectRole.PUBLIC_OFFICIAL: RoleConstraint(
        role=SubjectRole.PUBLIC_OFFICIAL,
        allowlisted_titles={
            "chief of police", "police chief", "sheriff", "county supervisor",
            "school board chair", "superintendent", "mayor", "city attorney",
            "commonwealth's attorney", "foia officer", "presiding officer",
            "executive director", "natural heritage director", "county administrator",
            "board chairperson", "city manager", "director of public works",
        },
        exempt_from_categories={
            "applicant_name", "personnel", "victim_witness", "contact_pii"
        },
    ),
    SubjectRole.COMMERCIAL_ENTITY: RoleConstraint(
        role=SubjectRole.COMMERCIAL_ENTITY,
        allowlisted_titles={
            "trustee", "corporation", "inc.", "llc", "company", "associates",
            "consultants", "engineers", "architects", "trustees",
        },
        exempt_from_categories={"applicant_name"},
    ),
}

# Standard form field questions encountered in Virginia municipal & environmental filings
DEFAULT_FORM_FIELD_CRITERIA: List[FormFieldCriterion] = [
    FormFieldCriterion(
        id="applicant_names",
        match_keywords=["legal names of applicants", "applicant name", "owner name", "landowner"],
        target_category="applicant_name",
        statute_code="VA-2.2-3705.1(10)",
        statute_title="Personal Privacy & PII",
        target_role=SubjectRole.PRIVATE_CITIZEN,
        confidence=0.92,
        description="Names of private citizen applicants or landowners.",
    ),
    FormFieldCriterion(
        id="agent_names",
        match_keywords=["agent if applicable", "authorized agent", "primary contact"],
        target_category="applicant_name",
        statute_code="VA-2.2-3705.1(10)",
        statute_title="Personal Privacy & PII",
        target_role=SubjectRole.PRIVATE_CITIZEN,
        confidence=0.92,
        description="Private contact agents acting on behalf of applicants.",
    ),
    FormFieldCriterion(
        id="contact_phones",
        match_keywords=["phone", "telephone", "mobile", "cell phone", "fax"],
        target_category="contact_pii",
        statute_code="VA-2.2-3705.1(10)",
        statute_title="Personal Privacy & PII",
        confidence=0.95,
        description="Direct telephone or cellular numbers.",
    ),
    FormFieldCriterion(
        id="contact_emails",
        match_keywords=["email", "electronic mail", "e-mail"],
        target_category="contact_pii",
        statute_code="VA-2.2-3705.1(10)",
        statute_title="Personal Privacy & PII",
        confidence=0.95,
        description="Direct personal electronic mail addresses.",
    ),
    FormFieldCriterion(
        id="coordinates_impact",
        match_keywords=["impact site", "latitude", "longitude", "lat.", "long."],
        target_category="gps_coordinate",
        statute_code="VA-2.2-3705.7(2)",
        statute_title="Impact Site / Environmental Location",
        confidence=0.94,
        description="Latitude/longitude coordinates in impact or location boxes.",
    ),
    FormFieldCriterion(
        id="species_habitat",
        match_keywords=["endangered", "threatened", "rare species", "natural heritage", "species survey"],
        target_category="endangered_species",
        statute_code="VA-2.2-3705.7(2)",
        statute_title="Endangered & Rare Species Locations",
        confidence=0.96,
        description="Questionnaire disclosures identifying rare or endangered species and habitats.",
    ),
    FormFieldCriterion(
        id="confidential_security",
        match_keywords=["confidential", "proprietary", "trade secret", "security vulnerability", "critical infrastructure"],
        target_category="confidential_proprietary",
        statute_code="VA-2.2-3705.6(3)",
        statute_title="Proprietary & Security Exemption",
        confidence=0.93,
        description="Proprietary commercial records or critical infrastructure security data.",
    ),
    FormFieldCriterion(
        id="private_parcel_address",
        match_keywords=["street address 911", "lotblockparcel", "parcel id", "tax map"],
        target_category="property_location",
        statute_code="VA-2.2-3705.1(10)",
        statute_title="Personal Privacy & Private Property",
        confidence=0.90,
        description="Private parcel 911 street addresses and parcel tax IDs.",
    ),
]

# Coordinate context classifications
DEFAULT_COORDINATE_CRITERIA: List[CoordinateContextCriterion] = [
    CoordinateContextCriterion(
        context_type="endangered_species_habitat",
        statute_code="VA-2.2-3705.7(2)",
        statute_title="Endangered & Rare Species Locations",
        keywords={
            "species", "habitat", "nest", "nesting", "roost", "roosting", "cave", "cavern",
            "hibernaculum", "colony", "bat", "woodpecker", "orchid", "pogonia", "salamander",
            "flora", "fauna", "natural heritage", "endangered", "threatened", "rare"
        },
        confidence=0.96,
        redact_in_sensitive_only=True,
        description="Coordinates linked to endangered/threatened flora, fauna, caves, or nests.",
    ),
    CoordinateContextCriterion(
        context_type="environmental_impact_site",
        statute_code="VA-2.2-3705.7(2)",
        statute_title="Impact Site Environmental Exemption",
        keywords={
            "impact", "impact site", "wetland", "stream", "crossing", "excavation", "fill",
            "ordinary high water", "dredging", "rpa", "riparian", "subaqueous", "mitigation"
        },
        confidence=0.93,
        redact_in_sensitive_only=True,
        description="Coordinates marking wetland, stream, or subaqueous impact locations.",
    ),
    CoordinateContextCriterion(
        context_type="private_property",
        statute_code="VA-2.2-3705.1(10)",
        statute_title="Personal Privacy & PII",
        keywords={
            "owner", "landowner", "homeowner", "resident", "residence", "private", "parcel",
            "home", "tax map", "911 address", "personal"
        },
        confidence=0.92,
        redact_in_sensitive_only=True,
        description="Coordinates pinpointing private residential land or private homeowner property.",
    ),
    CoordinateContextCriterion(
        context_type="critical_infrastructure",
        statute_code="VA-2.2-3705.2(1)",
        statute_title="Critical Infrastructure & Public Security",
        keywords={
            "substation", "pipeline", "intake", "water supply", "dam", "reservoir",
            "treatment plant", "utility crossing", "telecom", "security"
        },
        confidence=0.95,
        redact_in_sensitive_only=True,
        description="Coordinates revealing public drinking water supplies, dams, or power grids.",
    ),
    CoordinateContextCriterion(
        context_type="project_site_general",
        statute_code="VA-2.2-3705.7(2)",
        statute_title="Project Site Location Exemption",
        keywords={
            "project", "site", "latitude", "longitude", "lat.", "long.", "sheet", "drawn by",
            "project no", "scale", "title block", "datum", "nad"
        },
        confidence=0.90,
        redact_in_sensitive_only=False,  # Preserved in sensitive-only mode
        description="General drawing sheet title blocks or project area location stamps.",
    ),
]


@dataclass
class RedactionProfileConfig:
    """Configured profile specifying the exact redaction criteria and role constraints."""
    profile: ReleaseProfile
    coordinate_policy: CoordinatePolicy = CoordinatePolicy.ALL
    assess_form_context: bool = True
    field_criteria: List[FormFieldCriterion] = field(default_factory=lambda: list(DEFAULT_FORM_FIELD_CRITERIA))
    coordinate_criteria: List[CoordinateContextCriterion] = field(default_factory=lambda: list(DEFAULT_COORDINATE_CRITERIA))
    role_constraints: Dict[SubjectRole, RoleConstraint] = field(default_factory=lambda: dict(DEFAULT_ROLE_CONSTRAINTS))
    min_confidence: float = 0.75


class RedactionCriteriaRegistry:
    """Centralized manager for role and context constraints across all redaction engines."""

    _instances: Dict[str, "RedactionCriteriaRegistry"] = {}

    def __init__(self, profile: ReleaseProfile = ReleaseProfile.PUBLIC_FOIA) -> None:
        self.active_profile = self._build_profile_config(profile)

    @classmethod
    def get_default(cls) -> "RedactionCriteriaRegistry":
        """Get or create the default singleton registry."""
        if "default" not in cls._instances:
            cls._instances["default"] = cls(profile=ReleaseProfile.PUBLIC_FOIA)
        return cls._instances["default"]

    def _build_profile_config(self, profile: ReleaseProfile) -> RedactionProfileConfig:
        """Construct the configuration for a given release profile."""
        if profile == ReleaseProfile.STRICT_PRIVACY:
            return RedactionProfileConfig(
                profile=profile,
                coordinate_policy=CoordinatePolicy.ALL,
                assess_form_context=True,
            )
        elif profile == ReleaseProfile.ENVIRONMENTAL_REVIEW:
            return RedactionProfileConfig(
                profile=profile,
                coordinate_policy=CoordinatePolicy.SENSITIVE_ONLY,
                assess_form_context=True,
            )
        elif profile == ReleaseProfile.LAW_ENFORCEMENT:
            return RedactionProfileConfig(
                profile=profile,
                coordinate_policy=CoordinatePolicy.ALL,
                assess_form_context=True,
            )
        else:  # PUBLIC_FOIA
            return RedactionProfileConfig(
                profile=ReleaseProfile.PUBLIC_FOIA,
                coordinate_policy=CoordinatePolicy.ALL,
                assess_form_context=True,
            )

    def set_coordinate_policy(self, policy: str) -> None:
        """Update active coordinate policy ('all', 'sensitive-only', 'none')."""
        pol = policy.lower().replace("_", "-")
        if pol in ("all", "sensitive-only", "none"):
            self.active_profile.coordinate_policy = CoordinatePolicy(pol)

    def set_assess_form_context(self, enabled: bool) -> None:
        """Toggle form prompt/question assessment."""
        self.active_profile.assess_form_context = enabled

    def is_role_allowlisted(self, entity_text: str, category: str = "") -> bool:
        """Check if an entity name or role matches an allowlisted public official or entity."""
        clean = entity_text.lower().strip()
        for role_constraint in self.active_profile.role_constraints.values():
            if category and category in role_constraint.exempt_from_categories:
                for title in role_constraint.allowlisted_titles:
                    if title in clean or clean in title:
                        return True
            elif not category:
                for title in role_constraint.allowlisted_titles:
                    if title in clean or clean in title:
                        return True
        return False

    def match_form_field(self, field_title: str) -> Optional[FormFieldCriterion]:
        """Find the matching FormFieldCriterion for a given field prompt/title."""
        if not self.active_profile.assess_form_context:
            return None
        for criterion in self.active_profile.field_criteria:
            if criterion.matches_title(field_title):
                return criterion
        return None

    def match_coordinate_context(
        self, surrounding_text: str, field_title: Optional[str] = None
    ) -> Tuple[str, str, float, bool]:
        """Evaluate surrounding context to determine coordinate classification and redaction need.

        Returns:
            (context_type, statute_code, confidence, should_redact)
        """
        combined = f"{field_title or ''} {surrounding_text}".lower()

        # Check in priority order (species -> impact -> private -> critical -> general)
        for criterion in self.active_profile.coordinate_criteria:
            if criterion.matches_context(combined):
                c_type = criterion.context_type
                statute = criterion.statute_code
                conf = criterion.confidence

                policy = self.active_profile.coordinate_policy
                if policy == CoordinatePolicy.ALL:
                    should_redact = True
                elif policy == CoordinatePolicy.NONE:
                    should_redact = False
                else:  # SENSITIVE_ONLY
                    should_redact = criterion.redact_in_sensitive_only

                return c_type, statute, conf, should_redact

        # Default fallback
        policy = self.active_profile.coordinate_policy
        should_redact = (policy == CoordinatePolicy.ALL)
        return "unknown", "VA-2.2-3705.7(2)", 0.85, should_redact
