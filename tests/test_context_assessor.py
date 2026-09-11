"""Tests for context-aware coordinate and form box assessment under Virginia FOIA."""

from redact_gov.core.context_assessor import ContextAssessor, CoordinateContextType
from redact_gov.core.models import BoundingBox


def test_coordinate_context_classification_species():
    assessor = ContextAssessor(coordinate_policy="sensitive_only")
    surrounding = "Observations noted rare small whorled pogonia habitat located near 37.338590 N, -79.261030 W in vernal pool."
    c_type, statute, conf, should_redact = assessor.assess_coordinate_context(
        coord_text="37.338590 N",
        surrounding_text=surrounding,
    )
    assert c_type == CoordinateContextType.ENDANGERED_SPECIES_HABITAT
    assert statute == "VA-2.2-3705.7(2)"
    assert should_redact is True
    assert conf >= 0.95


def test_coordinate_context_classification_impact_site():
    assessor = ContextAssessor(coordinate_policy="sensitive_only")
    field_title = "Impact site number 1Latitude   Longitude in decimal degrees"
    c_type, statute, conf, should_redact = assessor.assess_coordinate_context(
        coord_text="37.338553, 79.260953",
        surrounding_text="",
        field_title=field_title,
    )
    assert c_type == CoordinateContextType.ENVIRONMENTAL_IMPACT_SITE
    assert statute == "VA-2.2-3705.7(2)"
    assert should_redact is True


def test_coordinate_context_classification_title_block():
    # Sensitive-only should preserve general project drawing title blocks
    sensitive_assessor = ContextAssessor(coordinate_policy="sensitive_only")
    surrounding = "PROJECT NO. 20221770 37.339070° LAT. -79.260396° LONG. 08/30/2023 DATE: SHEET NO. 1"
    c_type, statute, conf, should_redact = sensitive_assessor.assess_coordinate_context(
        coord_text="37.339070",
        surrounding_text=surrounding,
    )
    assert c_type == CoordinateContextType.PROJECT_SITE_GENERAL
    assert should_redact is False

    # Strict 'all' policy should redact title blocks
    strict_assessor = ContextAssessor(coordinate_policy="all")
    _, _, _, should_redact_strict = strict_assessor.assess_coordinate_context(
        coord_text="37.339070",
        surrounding_text=surrounding,
    )
    assert should_redact_strict is True


def test_form_field_assessment_applicant_and_agent():
    assessor = ContextAssessor()
    w_box = BoundingBox(page=1, x0=50.0, y0=100.0, x1=200.0, y1=120.0)

    # Private individual applicant -> targeted for redaction under VA-2.2-3705.1(10)
    ents = assessor.assess_form_field(
        field_title="Legal Names of Applicants",
        field_value="Johnathan Miller & Sarah Miller",
        page_number=1,
        bounding_box=w_box,
    )
    assert len(ents) == 1
    assert ents[0].category == "applicant_name"
    assert ents[0].statute_code == "VA-2.2-3705.1(10)"
    assert ents[0].context_label == "Form Question: Legal Names of Applicants"
    assert ents[0].bounding_boxes == [w_box]

    # Institutional / Trustee entity -> role constraint allowlist exempts from personal PII redaction
    exempt_ents = assessor.assess_form_field(
        field_title="Legal Names of Applicants",
        field_value="Timberlake Baptist Church Trustees",
        page_number=1,
        bounding_box=w_box,
    )
    assert len(exempt_ents) == 0


def test_form_field_assessment_sensitive_species_question():
    assessor = ContextAssessor()
    ents = assessor.assess_form_field(
        field_title="Are any endangered or threatened species present on site?",
        field_value="Roost of Northern long-eared bat identified near crossing A",
        page_number=3,
    )
    assert len(ents) == 1
    assert ents[0].category == "endangered_species"
    assert ents[0].statute_code == "VA-2.2-3705.7(2)"
