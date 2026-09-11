"""Context-aware assessment engine for coordinates, form boxes, and statutory exemptions."""

from typing import List, Optional, Tuple

from redact_gov.core.criteria import (
    CoordinateContextType,
    CoordinatePolicy,
    FormFieldCriterion,
    RedactionCriteriaRegistry,
    ReleaseProfile,
    SubjectRole,
)
from redact_gov.core.models import BoundingBox, RedactionEntity


class ContextAssessor:
    """Evaluates semantic context of coordinates and form fields under Virginia FOIA criteria."""

    def __init__(
        self,
        coordinate_policy: str = "all",
        profile: ReleaseProfile = ReleaseProfile.PUBLIC_FOIA,
        registry: Optional[RedactionCriteriaRegistry] = None,
    ) -> None:
        """Initialize with centralized RedactionCriteriaRegistry and coordinate policy."""
        self.registry = registry or RedactionCriteriaRegistry(profile=profile)
        if coordinate_policy:
            self.registry.set_coordinate_policy(coordinate_policy)

    @property
    def coordinate_policy(self) -> str:
        return self.registry.active_profile.coordinate_policy.value

    @coordinate_policy.setter
    def coordinate_policy(self, value: str) -> None:
        self.registry.set_coordinate_policy(value)

    def assess_coordinate_context(
        self,
        coord_text: str,
        surrounding_text: str,
        field_title: Optional[str] = None,
    ) -> Tuple[str, str, float, bool]:
        """Assess the context of a coordinate to determine category, statute, confidence, and redaction need.

        Delegates to the centralized criteria registry.
        Returns:
            (context_type, statute_code, confidence, should_redact)
        """
        return self.registry.match_coordinate_context(
            surrounding_text=surrounding_text,
            field_title=field_title,
        )

    def assess_form_field(
        self,
        field_title: str,
        field_value: str,
        page_number: int,
        bounding_box: Optional[BoundingBox] = None,
    ) -> List[RedactionEntity]:
        """Assess an AcroForm field or table box using its question/header prompt against centralized criteria."""
        val_clean = field_value.strip()
        if not val_clean or val_clean in ("/Yes", "/No", "/Off"):
            return []

        # Check centralized form field criteria registry
        criterion: Optional[FormFieldCriterion] = self.registry.match_form_field(field_title)
        if criterion is None:
            return []

        # Check role allowlisting (e.g. public official name in applicant/agent box)
        if criterion.target_role == SubjectRole.PRIVATE_CITIZEN:
            if self.registry.is_role_allowlisted(val_clean, criterion.target_category):
                return []

        # If criterion is coordinate-based, check coordinate policy
        if criterion.target_category == "gps_coordinate":
            c_type, statute, conf, should_redact = self.assess_coordinate_context(
                coord_text=val_clean,
                surrounding_text="",
                field_title=field_title,
            )
            if not should_redact:
                return []
            return [
                RedactionEntity(
                    text=val_clean,
                    category=f"gps_{c_type}",
                    statute_code=statute,
                    confidence=conf,
                    page_number=page_number,
                    bounding_boxes=[bounding_box] if bounding_box else [],
                    tier="tier2_context_assessor",
                    context_label=f"Form Question: {field_title}",
                )
            ]

        # Standard statutory criterion match
        return [
            RedactionEntity(
                text=val_clean,
                category=criterion.target_category,
                statute_code=criterion.statute_code,
                confidence=criterion.confidence,
                page_number=page_number,
                bounding_boxes=[bounding_box] if bounding_box else [],
                tier="tier2_context_assessor",
                context_label=f"Form Question: {field_title}",
            )
        ]
