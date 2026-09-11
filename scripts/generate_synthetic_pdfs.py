"""Generates realistic synthetic multi-page PDF documents for RedactGov testbed."""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from redact_gov.config import settings


def text_to_pdf(txt_path: Path, pdf_path: Path, title: str) -> None:
    """Convert formatted text into a structured PDF document."""
    raw_content = txt_path.read_text(encoding="utf-8")
    paragraphs = [p.strip() for p in raw_content.split("\n\n") if p.strip()]

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        "DocHeader",
        parent=styles["Heading1"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#1e293b"),
        alignment=1,
    )
    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#0f172a"),
    )

    story = []
    story.append(Paragraph(title, header_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#64748b"), spaceAfter=14))

    for p in paragraphs:
        cleaned = p.replace("\n", "<br/>")
        story.append(Paragraph(cleaned, body_style))
        story.append(Spacer(1, 12))

    # Add a second page to test multi-page redactions
    story.append(PageBreak())
    story.append(Paragraph(f"{title} - Continuation Sheet (Page 2)", header_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#64748b"), spaceAfter=14))
    continuation_note = (
        "CONFIDENTIAL AUDIT TRAIL & AGENCY TRANSMITTAL<br/><br/>"
        "This secondary page serves as formal receipt under Virginia Code § 2.2-3704. "
        "Records custodian notes confirm dispatch logs and intake interviews are held within local division archives. "
        "Direct FOIA inquiries to the Commonwealth Public Information Officer."
    )
    story.append(Paragraph(continuation_note, body_style))

    doc.build(story)


def main() -> None:
    settings.SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)

    files = [
        (
            settings.SYNTHETIC_DIR / "police_incident_narrative.txt",
            settings.SYNTHETIC_DIR / "police_incident_narrative.pdf",
            "OFFICIAL POLICE DIVISION INCIDENT RECORD",
        ),
        (
            settings.SYNTHETIC_DIR / "school_board_disciplinary_record.txt",
            settings.SYNTHETIC_DIR / "school_board_disciplinary_record.pdf",
            "SCHOLASTIC DISCIPLINARY PROCEEDING TRANSCRIPT",
        ),
        (
            settings.SYNTHETIC_DIR / "municipal_rezoning_dispute.txt",
            settings.SYNTHETIC_DIR / "municipal_rezoning_dispute.pdf",
            "MUNICIPAL PLANNING & REZONING PROTEST DOCKET",
        ),
        (
            settings.SYNTHETIC_DIR / "environmental_impact_assessment.txt",
            settings.SYNTHETIC_DIR / "environmental_impact_assessment.pdf",
            "DCR NATURAL HERITAGE ENVIRONMENTAL REVIEW",
        ),
    ]

    for txt_file, pdf_file, doc_title in files:
        if txt_file.is_file():
            text_to_pdf(txt_file, pdf_file, doc_title)
            print(f"Generated synthetic PDF: {pdf_file.name}")


if __name__ == "__main__":
    main()
