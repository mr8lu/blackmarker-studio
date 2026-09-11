"""Tests for imperfect, non-clean, and damaged PDF processing and normalization."""

import io
from pathlib import Path
import pikepdf
import pdfplumber
import pytest
from typer.testing import CliRunner

from redact_gov.cli import app
from redact_gov.core.normalizer import DocumentNormalizer
from redact_gov.pipeline import RedactionPipeline


@pytest.fixture
def imperfect_pdf(tmp_path: Path) -> Path:
    """Generate a synthetic imperfect PDF with defective font descriptors (FontBBox=None, missing Ascent)."""
    pdf = pikepdf.new()
    page = pdf.add_blank_page(page_size=(612.0, 792.0))

    # Font 1: FontDescriptor with FontBBox = None (causes pdfminer 4-float parse warning)
    # and missing /Ascent and /Descent
    font_desc = pdf.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name("/FontDescriptor"),
            FontName=pikepdf.Name("/ImperfectSans"),
            # FontBBox is intentionally omitted / None
        )
    )
    font = pdf.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name("/Font"),
            Subtype=pikepdf.Name("/TrueType"),
            BaseFont=pikepdf.Name("/ImperfectSans"),
            FontDescriptor=font_desc,
            FirstChar=32,
            LastChar=126,
            Widths=pdf.make_indirect(pikepdf.Array([600] * 95)),
        )
    )

    page.Resources = pikepdf.Dictionary(
        Font=pikepdf.Dictionary(F1=font)
    )
    # Stream with sensitive data that requires FOIA redactions
    page.Contents = pdf.make_stream(
        b"BT /F1 12 Tf 50 700 Td (Commonwealth of Virginia - Department of Corrections) Tj "
        b"0 -25 Td (Subject SSN: 987-65-4321 DOB: 05/12/1988) Tj "
        b"0 -25 Td (Juvenile Witness: Tommy Jenkins) Tj ET"
    )

    file_path = tmp_path / "imperfect_record.pdf"
    pdf.save(file_path)
    return file_path


def test_document_normalizer_detection_and_repair(imperfect_pdf: Path, tmp_path: Path):
    """Test that DocumentNormalizer diagnoses and repairs font descriptor defects."""
    normalizer = DocumentNormalizer()

    # 1. Inspection should flag the document as imperfect
    report = normalizer.inspect_document(imperfect_pdf)
    assert report.is_imperfect is True
    assert any("FontBBox" in issue for issue in report.issues)
    assert report.total_pages == 1

    # 2. Normalization should repair the document
    normalized_path = tmp_path / "normalized_record.pdf"
    out_path, repair_report = normalizer.normalize_pdf(imperfect_pdf, normalized_path)
    assert out_path.is_file()
    assert repair_report.repaired_fonts_count >= 1

    # 3. Re-inspecting the normalized document should report clean status
    recheck = normalizer.inspect_document(out_path)
    assert recheck.is_imperfect is False
    assert len(recheck.issues) == 0

    # 4. Verify pdfplumber can open the normalized document and extract text
    with pdfplumber.open(out_path) as pdf:
        text = pdf.pages[0].extract_text()
        assert "987-65-4321" in text
        assert "Tommy Jenkins" in text


def test_redaction_pipeline_on_imperfect_document(imperfect_pdf: Path, tmp_path: Path):
    """Test that RedactionPipeline processes imperfect document end-to-end with zero errors."""
    pipeline = RedactionPipeline()

    # Create plan with automatic imperfect normalization enabled
    plan = pipeline.create_plan(imperfect_pdf, normalize_imperfect=True)
    assert len(plan.entities) >= 1

    # Check that bounding boxes were calculated with valid positive dimensions
    for entity in plan.entities:
        for box in entity.bounding_boxes:
            assert box.width > 0
            assert box.height > 0

    # Execute plan
    output_pdf = tmp_path / "redacted_imperfect.pdf"
    cert_pdf = tmp_path / "cert_imperfect.pdf"

    result = pipeline.execute_plan(
        input_pdf=imperfect_pdf,
        plan=plan,
        output_pdf=output_pdf,
        certificate_pdf=cert_pdf,
        repair_imperfect=True,
    )

    assert result.success is True
    assert result.verification_passed is True
    assert output_pdf.is_file()
    assert cert_pdf.is_file()

    # Verify sensitive text is scrubbed from output text
    with pdfplumber.open(output_pdf) as pdf:
        out_text = pdf.pages[0].extract_text() or ""
        assert "987-65-4321" not in out_text

    # Verify output PDF has clean, repaired font descriptors
    normalizer = DocumentNormalizer()
    out_report = normalizer.inspect_document(output_pdf)
    assert out_report.is_imperfect is False


def test_cli_inspect_command(imperfect_pdf: Path):
    """Test CLI inspect command on imperfect PDF."""
    runner = CliRunner()
    res = runner.invoke(app, ["inspect", str(imperfect_pdf)])
    assert res.exit_code == 0
    assert "Imperfect" in res.output or "Defective" in res.output
    assert "FontBBox" in res.output
