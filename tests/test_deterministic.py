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


def test_cid_artifact_and_health_plan_false_positive_hardening():
    engine = DeterministicRedactionEngine()
    noisy_form_text = (
        "(cid:115)(cid:123)(cid:402) Part II Made to a Qualified Health Plan following the marketplace rules. "
        "Account Type: Checking. Valid CVV: 842 and Member ID: W99482011."
    )
    entities = engine.scan_text(noisy_form_text, page_number=1)
    by_cat = {e.category: [x.text for x in entities if x.category == e.category] for e in entities}

    # PDF (cid:XXX) font placeholders must never be misclassified as CVV codes
    assert by_cat.get("cvv_code") == ["842"]
    # English prose "Health Plan following" must never be misclassified as a health_plan_id
    assert by_cat.get("health_plan_id") == ["W99482011"]
    # "Account Type: Checking" must not match as a bank_account number
    assert "bank_account" not in by_cat


def test_comb_box_and_underline_interleaved_tax_form_extraction():
    engine = DeterministicRedactionEngine()
    tax_form_text = (
        "Form 1040 U.S. Individual Income Tax Return\n"
        "Alex Rivera   223  45  6789\n"
        "Routing number 0 2 1 0 0 0 0 2 1\n"
        "Account number 1 2 3 4 5 6 7 8 9 0 1 2\n"
        "RTN#: _0_2_1 _0_0_0 _0_2_1   ACCOUNT #: _9_8_7 _6_5_4 _3_2_1_0\n"
        "Your Birth Date 0 5 - 1 4 - 1 9 8 6\n"
        "Employer ID number 54-1234567\n"
    )
    entities = engine.scan_text(tax_form_text, page_number=1)
    cats = {e.category for e in entities}
    texts = {e.text for e in entities}

    assert "ssn" in cats
    assert "223  45  6789" in texts
    assert "routing_aba" in cats
    assert "0 2 1 0 0 0 0 2 1" in texts
    assert "021000021" in texts
    assert "bank_account" in cats
    assert "1 2 3 4 5 6 7 8 9 0 1 2" in texts
    assert "9876543210" in texts
    assert "dob" in cats
    assert "0 5 - 1 4 - 1 9 8 6" in texts
    assert "ein" in cats
    assert "54-1234567" in texts


def test_comb_box_and_split_column_stream_sanitization(tmp_path):
    import pikepdf
    from redact_gov.pipeline import RedactionPipeline

    input_pdf = tmp_path / "comb_form_test.pdf"
    output_pdf = tmp_path / "comb_form_sanitized.pdf"

    # Build a 2-page PDF using raw BT / Td / Tj single-character comb cells and split-column names
    pdf = pikepdf.Pdf.new()
    for page_num in (1, 2):
        page = pdf.add_blank_page(page_size=(612, 792))
        font = pdf.make_indirect(
            pikepdf.Dictionary(
                Type=pikepdf.Name("/Font"),
                Subtype=pikepdf.Name("/Type1"),
                BaseFont=pikepdf.Name("/Courier"),
                Encoding=pikepdf.Name("/WinAnsiEncoding"),
            )
        )
        page.Resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font))

        if page_num == 1:
            # Page 1: Split-column First/Last name + comb-box SSN + comb-box ABA routing
            stream_ops = [
                "BT /F1 10 Tf 50 720 Td (Form 1040 Individual Tax Return) Tj ET",
                "BT /F1 10 Tf 50 700 Td (Jordan) Tj 90 0 Td (Mercer) Tj 120 0 Td (223  45  6789) Tj ET",
                "BT /F1 10 Tf 50 670 Td (Routing number) Tj "
                + " ".join(f"{18 if i > 0 else 110} 0 Td ({d}) Tj" for i, d in enumerate("021000021"))
                + " ET",
                "BT /F1 10 Tf 50 640 Td (742 Evergreen Ave Apt 4B) Tj ET",
            ]
        else:
            # Page 2: Continuation schedule with unhyphenated SSN and uppercase name
            stream_ops = [
                "BT /F1 10 Tf 50 720 Td (Schedule Continuation) Tj ET",
                "BT /F1 10 Tf 50 700 Td (JORDAN MERCER) Tj 180 0 Td (223456789) Tj ET",
            ]
        page.Contents = pdf.make_stream("\n".join(stream_ops).encode("latin1"))

    pdf.save(input_pdf)

    pipeline = RedactionPipeline()
    plan = pipeline.create_plan(input_pdf)
    assert any(e.category == "ssn" and e.page_number == 1 for e in plan.entities)
    assert any(e.category == "routing_aba" and e.page_number == 1 for e in plan.entities)
    assert any(e.category == "applicant_name" and e.page_number == 1 for e in plan.entities)
    assert any(e.category == "street_address" and e.page_number == 1 for e in plan.entities)
    # Cross-page propagation to Page 2
    assert any(e.category == "ssn" and e.page_number == 2 for e in plan.entities)
    assert any(e.category == "applicant_name" and e.page_number == 2 for e in plan.entities)
    assert all(len(e.bounding_boxes) > 0 for e in plan.entities)

    res = pipeline.execute_plan(input_pdf, plan, output_pdf)
    assert res.success is True
    assert res.verification_passed is True

