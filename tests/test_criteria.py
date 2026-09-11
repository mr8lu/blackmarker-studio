"""Unit tests for the centralized RedactionCriteriaRegistry, role constraints, and context criteria."""

from redact_gov.core.criteria import (
    CoordinatePolicy,
    FormFieldCriterion,
    RedactionCriteriaRegistry,
    ReleaseProfile,
    SubjectRole,
)


def test_registry_profiles_and_coordinate_policy():
    reg_foia = RedactionCriteriaRegistry(profile=ReleaseProfile.PUBLIC_FOIA)
    assert reg_foia.active_profile.coordinate_policy == CoordinatePolicy.ALL

    reg_env = RedactionCriteriaRegistry(profile=ReleaseProfile.ENVIRONMENTAL_REVIEW)
    assert reg_env.active_profile.coordinate_policy == CoordinatePolicy.SENSITIVE_ONLY

    reg_strict = RedactionCriteriaRegistry(profile=ReleaseProfile.STRICT_PRIVACY)
    assert reg_strict.active_profile.coordinate_policy == CoordinatePolicy.ALL


def test_form_field_prompt_matching():
    reg = RedactionCriteriaRegistry.get_default()

    crit_app = reg.match_form_field("Legal Names of Applicants")
    assert crit_app is not None
    assert crit_app.target_category == "applicant_name"
    assert crit_app.statute_code == "VA-2.2-3705.1(10)"

    crit_phone = reg.match_form_field("Phone number warea code_2")
    assert crit_phone is not None
    assert crit_phone.target_category == "contact_pii"

    crit_species = reg.match_form_field("Are rare or endangered species present on site?")
    assert crit_species is not None
    assert crit_species.target_category == "endangered_species"
    assert crit_species.statute_code == "VA-2.2-3705.7(2)"


def test_role_allowlisting_constraints():
    reg = RedactionCriteriaRegistry.get_default()

    # Public officials acting in official capacity should be allowlisted from applicant/PII redaction
    assert reg.is_role_allowlisted("Chief of Police John Doe", category="applicant_name") is True
    assert reg.is_role_allowlisted("County Supervisor Jane Smith", category="personnel") is True

    # Commercial entities / consultants acting as organizational applicants
    assert reg.is_role_allowlisted("H&P Engineers Inc.", category="applicant_name") is True

    # Private individuals should NOT be allowlisted
    assert reg.is_role_allowlisted("Johnathan Miller", category="applicant_name") is False


def test_coordinate_context_matching():
    reg_env = RedactionCriteriaRegistry(profile=ReleaseProfile.ENVIRONMENTAL_REVIEW)

    # 1. Species habitat -> redacted under sensitive-only
    c_type, statute, conf, should_redact = reg_env.match_coordinate_context(
        surrounding_text="Nesting colony of big-eared bats observed at 37.338590 N, -79.261030 W"
    )
    assert c_type == "endangered_species_habitat"
    assert statute == "VA-2.2-3705.7(2)"
    assert should_redact is True

    # 2. General title block -> preserved under sensitive-only
    c_type_p, _, _, should_redact_p = reg_env.match_coordinate_context(
        surrounding_text="PROJECT NO. 20221770 SHEET 1 LAT 37.339070 LONG -79.260396"
    )
    assert c_type_p == "project_site_general"
    assert should_redact_p is False


def test_custom_criterion_registration():
    reg = RedactionCriteriaRegistry(profile=ReleaseProfile.PUBLIC_FOIA)
    custom_crit = FormFieldCriterion(
        id="custom_tribal_survey",
        match_keywords=["cultural resource", "tribal historic"],
        target_category="tribal_heritage",
        statute_code="VA-2.2-3705.7(2)",
        statute_title="Cultural & Tribal Resource Exemption",
        confidence=0.98,
    )
    reg.active_profile.field_criteria.append(custom_crit)

    matched = reg.match_form_field("Section 5: Tribal Historic and Cultural Resource Disclosures")
    assert matched is not None
    assert matched.id == "custom_tribal_survey"
    assert matched.statute_code == "VA-2.2-3705.7(2)"
