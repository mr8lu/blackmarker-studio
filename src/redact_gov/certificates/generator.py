"""Virginia FOIA Redaction Certificate and Audit Report Generator powered by Polars & ReportLab."""

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import polars as pl
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from redact_gov.core.models import RedactionEntity
from redact_gov.core.statutes import get_statute


class CertificateGenerator:
    """Generates official Virginia FOIA compliance certificates using Polars for high-speed indexing."""

    def generate_certificate(
        self,
        document_name: str,
        entities: List[RedactionEntity],
        output_path: Path,
        reviewer_name: str = "Authorized FOIA Officer",
        agency_name: str = "Commonwealth of Virginia - Public Records Office",
    ) -> Path:
        """Generate a formal Virginia FOIA Redaction Certificate PDF."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert entities into a Polars DataFrame for fast aggregation
        data = []
        for e in entities:
            if not e.approved:
                continue
            statute = get_statute(e.statute_code)
            citation = statute.legal_citation if statute else e.statute_code
            title = statute.short_title if statute else e.category
            data.append({
                "id": e.id,
                "text": e.text,
                "category": e.category,
                "statute_code": e.statute_code,
                "legal_citation": citation,
                "statute_title": title,
                "page": e.page_number,
                "tier": e.tier,
                "confidence": e.confidence,
            })

        if data:
            df = pl.DataFrame(data)
            # Polars aggregation by statute
            statute_summary = (
                df.group_by(["statute_code", "legal_citation", "statute_title"])
                .agg(pl.len().alias("count"))
                .sort("count", descending=True)
            )
        else:
            df = pl.DataFrame(schema={
                "id": pl.Utf8, "text": pl.Utf8, "category": pl.Utf8,
                "statute_code": pl.Utf8, "legal_citation": pl.Utf8,
                "statute_title": pl.Utf8, "page": pl.Int64,
                "tier": pl.Utf8, "confidence": pl.Float64,
            })
            statute_summary = pl.DataFrame()

        # Build ReportLab PDF
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CertTitle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1e3a8a"),
            alignment=1,  # Center
        )
        subtitle_style = ParagraphStyle(
            "CertSubtitle",
            parent=styles["Normal"],
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#475569"),
            alignment=1,
        )
        section_heading = ParagraphStyle(
            "CertSection",
            parent=styles["Heading2"],
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=12,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "CertBody",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#334155"),
        )
        table_header_style = ParagraphStyle(
            "CertTableHeader",
            parent=styles["Normal"],
            fontSize=9,
            leading=11,
            textColor=colors.white,
            fontName="Helvetica-Bold",
        )

        story = []

        # Header
        story.append(Paragraph("COMMONWEALTH OF VIRGINIA", subtitle_style))
        story.append(Paragraph("VIRGINIA FREEDOM OF INFORMATION ACT (VFOIA)", subtitle_style))
        story.append(Paragraph("STATUTORY REDACTION & COMPLIANCE CERTIFICATE", title_style))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1e3a8a"), spaceAfter=12))

        # Metadata Block
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        meta_data = [
            [Paragraph("<b>Target Document:</b>", body_style), Paragraph(document_name, body_style)],
            [Paragraph("<b>Date of Audit:</b>", body_style), Paragraph(now_str, body_style)],
            [Paragraph("<b>Certifying Agency:</b>", body_style), Paragraph(agency_name, body_style)],
            [Paragraph("<b>FOIA Compliance Officer:</b>", body_style), Paragraph(reviewer_name, body_style)],
            [Paragraph("<b>Total Redacted Items:</b>", body_style), Paragraph(str(len(data)), body_style)],
        ]
        meta_table = Table(meta_data, colWidths=[150, 380])
        meta_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 14))

        # Section 1: Statutory Summary Table
        story.append(Paragraph("1. Statutory Withholding Summary", section_heading))
        summary_rows = [[
            Paragraph("Virginia Statute", table_header_style),
            Paragraph("Statutory Exemption Category", table_header_style),
            Paragraph("Redacted Items", table_header_style),
        ]]

        if not statute_summary.is_empty():
            for row in statute_summary.iter_rows(named=True):
                summary_rows.append([
                    Paragraph(row["legal_citation"], body_style),
                    Paragraph(row["statute_title"], body_style),
                    Paragraph(str(row["count"]), body_style),
                ])
        else:
            summary_rows.append([
                Paragraph("None", body_style),
                Paragraph("No exemptions applied", body_style),
                Paragraph("0", body_style),
            ])

        sum_table = Table(summary_rows, colWidths=[180, 270, 80])
        sum_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
            ("ALIGN", (2, 0), (2, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(sum_table)
        story.append(Spacer(1, 14))

        # Section 2: Detailed Audit Log
        story.append(Paragraph("2. Itemized Redaction Log", section_heading))
        detail_rows = [[
            Paragraph("Item ID", table_header_style),
            Paragraph("Page", table_header_style),
            Paragraph("Legal Citation", table_header_style),
            Paragraph("Category", table_header_style),
            Paragraph("Withheld Token Pattern", table_header_style),
        ]]

        if not df.is_empty():
            for row in df.iter_rows(named=True):
                # Mask text for security in certificate (e.g. 123-**-6789)
                raw_text = row["text"]
                if len(raw_text) > 4:
                    masked = raw_text[:2] + ("*" * (len(raw_text) - 4)) + raw_text[-2:]
                else:
                    masked = "***"

                detail_rows.append([
                    Paragraph(str(row["id"]), body_style),
                    Paragraph(str(row["page"]), body_style),
                    Paragraph(str(row["legal_citation"]), body_style),
                    Paragraph(str(row["category"]), body_style),
                    Paragraph(masked, body_style),
                ])

        det_table = Table(detail_rows, colWidths=[70, 45, 155, 120, 140])
        det_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(det_table)
        story.append(Spacer(1, 20))

        # Certification Signature Block
        story.append(Paragraph("3. Official Attestation", section_heading))
        attestation = (
            "I hereby certify under penalty of law that the redactions documented above have been executed "
            "in strict compliance with the Virginia Freedom of Information Act (Va. Code § 2.2-3700 et seq.) "
            "and all applicable juvenile, victim protection, and law-enforcement confidentiality statutes. "
            "All underlying data layers have been irreversibly purged using air-gapped on-device sanitization."
        )
        story.append(Paragraph(attestation, body_style))
        story.append(Spacer(1, 35))

        sig_data = [
            [
                Paragraph("__________________________________________<br/>Signature of Certifying Official", body_style),
                Paragraph("____________________<br/>Date", body_style),
            ]
        ]
        sig_table = Table(sig_data, colWidths=[360, 170])
        story.append(sig_table)

        doc.build(story)
        return output_path
