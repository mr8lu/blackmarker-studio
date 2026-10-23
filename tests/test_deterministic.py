from redact_gov.engines.deterministic import (
    DeterministicRedactionEngine,
    aba_routing_checksum_valid,
    luhn_checksum_valid,
)


def test_deterministic_patterns():
    engine = DeterministicRedactionEngine()
    sample = (
        "Subject details: SSN 123-45-6789, Virginia Driver's License T98765432. "
        "Contact phone (804) 555-1234, DOB: 05/12/1984. "
        "Email address test.user@richmondgov.org."
    )

    entities = engine.scan_text(sample, page_number=1)
    categories = {e.category: e.text for e in entities}

    assert "ssn" in categories
    assert categories["ssn"] == "123-45-6789"

    assert "driver_license" in categories
    assert categories["driver_license"] == "T98765432"

    assert "phone" in categories
    assert "(804) 555-1234" in categories["phone"]

    assert "dob" in categories
    assert categories["dob"] == "05/12/1984"

    assert "email" in categories
    assert categories["email"] == "test.user@richmondgov.org"


def test_phi_healthcare_patterns_and_domain_filtering():
    engine = DeterministicRedactionEngine()
    clinical_note = (
        "Discharge Summary: MRN: MRN-84920144, Attending NPI: 1234567893. "
        "Primary Diagnosis ICD-10: J45.909, Policy #: HPN-99887766. "
        "Patient SSN 123-45-6789."
    )

    # 1. Scan only PHI domain (a-la-carte)
    phi_only = engine.scan_text(clinical_note, page_number=1, enabled_domains=["PHI"])
    phi_cats = {e.category for e in phi_only}
    assert "mrn" in phi_cats
    assert "npi" in phi_cats
    assert "icd10_code" in phi_cats
    assert "health_plan_id" in phi_cats
    assert "ssn" not in phi_cats  # SSN is PII, excluded when only PHI is enabled
    assert all(e.data_domain == "PHI" for e in phi_only)


def test_ppi_financial_patterns_and_domain_filtering():
    engine = DeterministicRedactionEngine()
    financial_doc = (
        "Wire Transfer Authorization: Card 4532-0151-1283-0366, "
        "ABA Routing: 021000021, Account #: 987654321012, "
        "IBAN DE89370400440532013000. Contact: john@bank.com"
    )

    # 1. Scan only PPI domain (a-la-carte)
    ppi_only = engine.scan_text(financial_doc, page_number=1, enabled_domains=["PPI"])
    ppi_cats = {e.category for e in ppi_only}
    assert "credit_card" in ppi_cats
    assert "routing_aba" in ppi_cats
    assert "bank_account" in ppi_cats
    assert "iban_swift" in ppi_cats
    assert "email" not in ppi_cats  # Email is PII
    assert all(e.data_domain == "PPI" for e in ppi_only)


def test_luhn_and_aba_checksums():
    # Valid test visa card
    assert luhn_checksum_valid("4532015112830366") is True
    # Invalid card
    assert luhn_checksum_valid("4532015112830367") is False
    # Valid JPMorgan Chase ABA routing number
    assert aba_routing_checksum_valid("021000021") is True
    assert aba_routing_checksum_valid("021000022") is False
