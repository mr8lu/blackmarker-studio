from pathlib import Path
import pdfplumber
import pikepdf

from redact_gov.config import settings
from redact_gov.pipeline import RedactionPipeline


def test_end_to_end_sanitization_and_byte_erasure(tmp_path: Path):
    pipeline = RedactionPipeline()
    source_pdf = settings.SYNTHETIC_DIR / "police_incident_narrative.pdf"
    assert source_pdf.is_file()

    # Step 1: Create Plan
    plan = pipeline.create_plan(source_pdf)
    assert len(plan.entities) > 0

    # Ensure Chief of Police is excluded
    redacted_texts = [e.text.lower() for e in plan.entities]
    assert "chief of police" not in redacted_texts

    # Step 2: Execute Sanitization
    output_pdf = tmp_path / "sanitized_test.pdf"
    cert_pdf = tmp_path / "cert_test.pdf"

    result = pipeline.execute_plan(
        input_pdf=source_pdf,
        plan=plan,
        output_pdf=output_pdf,
        certificate_pdf=cert_pdf,
    )

    assert result.success is True
    assert result.verification_passed is True
    assert output_pdf.is_file()
    assert cert_pdf.is_file()

    # Step 3: Verify Zero Text Matches with pdfplumber
    sensitive_targets = ["987-65-4320", "CI-9140", "Brandon Miller", "T48192044"]
    with pdfplumber.open(output_pdf) as pdf:
        all_text = " ".join(page.extract_text() or "" for page in pdf.pages)
        for target in sensitive_targets:
            assert target not in all_text, f"Target '{target}' leaked into extracted text!"

    # Step 4: Verify Metadata Wiped with PikePDF
    with pikepdf.open(output_pdf) as pdf:
        assert "/Metadata" not in pdf.Root, "XMP Metadata stream was not stripped!"
        assert "/PieceInfo" not in pdf.Root, "PieceInfo stream was not stripped!"
