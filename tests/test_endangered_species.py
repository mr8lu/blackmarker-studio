from pathlib import Path
import pdfplumber
import pikepdf

from redact_gov.config import settings
from redact_gov.pipeline import RedactionPipeline
from redact_gov.core.statutes import get_statute


def test_endangered_species_statutory_redaction(tmp_path: Path):
    pipeline = RedactionPipeline()
    pdf_path = settings.SYNTHETIC_DIR / "environmental_impact_assessment.pdf"
    assert pdf_path.is_file(), "Environmental impact assessment PDF must exist."

    # Step 1: Create Plan
    plan = pipeline.create_plan(pdf_path)
    assert len(plan.entities) >= 4

    categories = {e.category for e in plan.entities}
    assert "gps_coordinate" in categories or "endangered_species" in categories

    # Verify statute code
    species_entities = [e for e in plan.entities if e.statute_code == "VA-2.2-3705.7(2)"]
    assert len(species_entities) >= 3

    # Ensure allowlisted officials are not redacted
    redacted_lower = [e.text.lower() for e in plan.entities]
    assert "sandra alvarez" not in redacted_lower
    assert "marcus thornton" not in redacted_lower

    # Step 2: Execute Sanitization
    out_pdf = tmp_path / "sanitized_species.pdf"
    cert_pdf = tmp_path / "cert_species.pdf"

    result = pipeline.execute_plan(pdf_path, plan, out_pdf, cert_pdf)
    assert result.success is True
    assert result.verification_passed is True

    # Step 3: Verify with pdfplumber that GPS and cave names were scrubbed
    sensitive_markers = [
        "37°58'42.1\"N",
        "38°12'14.6\"N",
        "37.9782, -79.8194",
        "Blowing Springs Cave",
    ]
    with pdfplumber.open(out_pdf) as pdf:
        all_text = " ".join(p.extract_text() or "" for p in pdf.pages)
        for marker in sensitive_markers:
            assert marker not in all_text, f"Marker '{marker}' leaked into sanitized text!"

    # Step 4: Verify Metadata Wiped
    with pikepdf.open(out_pdf) as pdf:
        assert "/Metadata" not in pdf.Root
