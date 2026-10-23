"""Multi-Sector Compliance & Redaction Certificate generator powered by Polars and ReportLab."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import polars as pl
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from redact_gov.core.models import (
    AuditRecord,
    CertificateConfig,
    RedactionEntity,
    RedactionPlan,
    get_certificate_preset,
)
from redact_gov.core.statutes import get_statute


class CertificateGenerator:
    """Generates customizable compliance & redaction audit certificates and Polars ledger summaries."""

    def build_polars_dataframe(self, plan: RedactionPlan) -> pl.DataFrame:
        """Convert approved redaction entities into a Polars DataFrame for high-speed aggregation."""
        records = []
        for entity in plan.entities:
            if not entity.approved:
                continue
            statute = get_statute(entity.statute_code)
            records.append(
                {
                    "id": entity.id,
                    "page": entity.page_number,
                    "category": entity.category,
                    "data_domain": entity.data_domain or (statute.data_domain if statute else "PII"),
                    "statute_code": entity.statute_code,
                    "legal_citation": statute.legal_citation if statute else entity.statute_code,
                    "short_title": statute.short_title if statute else "Statutory / Regulatory Exemption",
                    "tier": entity.tier,
                    "confidence": round(entity.confidence, 3),
                    "instance_count": max(1, len(entity.bounding_boxes)),
                }
            )

        if not records:
            return pl.DataFrame(
                schema={
                    "id": pl.Utf8,
                    "page": pl.Int64,
                    "category": pl.Utf8,
                    "data_domain": pl.Utf8,
                    "statute_code": pl.Utf8,
                    "legal_citation": pl.Utf8,
                    "short_title": pl.Utf8,
                    "tier": pl.Utf8,
                    "confidence": pl.Float64,
                    "instance_count": pl.Int64,
                }
            )

        return pl.DataFrame(records)

    def summarize_by_statute(self, df: pl.DataFrame) -> pl.DataFrame:
        """Aggregate redaction counts grouped by statutory/regulatory citation and page numbers."""
        if df.is_empty():
            return pl.DataFrame(
                schema={
                    "legal_citation": pl.Utf8,
                    "short_title": pl.Utf8,
                    "total_redactions": pl.Int64,
                    "pages_affected": pl.Utf8,
                }
            )

        summary = (
            df.group_by(["legal_citation", "short_title"])
            .agg(
                [
                    pl.col("instance_count").sum().alias("total_redactions"),
                    pl.col("page").unique().sort().cast(pl.Utf8).str.join(", ").alias("pages_affected"),
                ]
            )
            .sort("legal_citation")
        )
        return summary

    def resolve_certificate_config(
        self,
        plan: RedactionPlan,
        agency_name: Optional[str] = None,
        reviewer_name: Optional[str] = None,
        certificate_config: Optional[Union[CertificateConfig, Dict[str, Any]]] = None,
    ) -> CertificateConfig:
        """Resolve the effective CertificateConfig from preset, plan profile, and explicit overrides."""
        if isinstance(certificate_config, CertificateConfig):
            cfg = certificate_config.model_copy()
        elif isinstance(certificate_config, dict):
            preset_base = get_certificate_preset(
                certificate_config.get("template_preset") or getattr(plan, "profile", None)
            )
            merged = preset_base.model_dump()
            for k, v in certificate_config.items():
                if v is not None and str(v).strip() != "" and k in merged:
                    merged[k] = v
            cfg = CertificateConfig(**merged)
        else:
            cfg = get_certificate_preset(getattr(plan, "profile", None))

        if agency_name and agency_name.strip():
            cfg.agency_name = agency_name.strip()
        if reviewer_name and reviewer_name.strip():
            cfg.reviewer_name = reviewer_name.strip()
        return cfg

    def generate_pdf_certificate(
        self,
        plan: RedactionPlan,
        output_path: Path,
        agency_name: Optional[str] = None,
        reviewer_name: Optional[str] = None,
        certificate_config: Optional[Union[CertificateConfig, Dict[str, Any]]] = None,
    ) -> Path:
        """Render a formal PDF Compliance & Redaction Certificate using customizable template settings."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cfg = self.resolve_certificate_config(
            plan=plan,
            agency_name=agency_name,
            reviewer_name=reviewer_name,
            certificate_config=certificate_config,
        )

        df = self.build_polars_dataframe(plan)
        summary_df = self.summarize_by_statute(df)

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CertTitle",
            parent=styles["Heading1"],
            fontSize=15,
            leading=19,
            spaceAfter=6,
            textColor=colors.HexColor("#1B365D"),
        )
        subtitle_style = ParagraphStyle(
            "CertSub",
            parent=styles["Normal"],
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#4A5568"),
        )
        body_style = styles["BodyText"]

        elements = []

        # Customizable Header Banner
        elements.append(Paragraph(cfg.jurisdiction_banner, title_style))
        elements.append(Paragraph(cfg.framework_subtitle, subtitle_style))
        elements.append(Spacer(1, 0.18 * inch))
        elements.append(Paragraph(f"<b>{cfg.certificate_title}</b>", styles["Heading2"]))
        elements.append(Spacer(1, 0.1 * inch))

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        domains_str = ", ".join(getattr(plan, "enabled_domains", None) or ["PII", "PHI", "PPI"])
        profile_str = (getattr(plan, "profile", None) or "public_foia").upper().replace("_", " ")

        meta_data = [
            ["Document Name:", plan.document_name],
            ["Total Pages:", str(plan.total_pages)],
            ["Certifying Organization:", cfg.agency_name],
            [cfg.reviewer_role_label, cfg.reviewer_name],
            ["Compliance Profile & Domains:", f"{profile_str} ({domains_str})"],
            ["Timestamp (UTC):", now_str],
            ["Execution Mode:", "100% Air-Gapped On-Device (Blackmarker Studio)"],
        ]

        meta_table = Table(meta_data, colWidths=[2.3 * inch, 4.7 * inch])
        meta_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#2D3748")),
                ]
            )
        )
        elements.append(meta_table)
        elements.append(Spacer(1, 0.25 * inch))

        # Exemption Summary Table
        elements.append(Paragraph("<b>1. Regulatory & Statutory Redaction Summary</b>", styles["Heading3"]))
        elements.append(Spacer(1, 0.08 * inch))

        if summary_df.is_empty():
            elements.append(
                Paragraph("No redactions were required or applied to this document.", body_style)
            )
        else:
            table_rows = [[cfg.citation_column_header, "Domain", "Exemption / Control Category", "Redactions", "Pages"]]
            for row in summary_df.iter_rows(named=True):
                table_rows.append(
                    [
                        row["legal_citation"],
                        row.get("data_domain", "PII"),
                        row["short_title"],
                        str(row["total_redactions"]),
                        row["pages_affected"],
                    ]
                )

            summary_table = Table(
                table_rows, colWidths=[2.0 * inch, 0.7 * inch, 2.3 * inch, 0.9 * inch, 1.1 * inch]
            )
            summary_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B365D")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F7FAFC")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -1), 8),
                        ("ALIGN", (1, 1), (1, -1), "CENTER"),
                        ("ALIGN", (3, 1), (3, -1), "CENTER"),
                    ]
                )
            )
            elements.append(summary_table)

        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph("<b>2. Legal & Compliance Attestation</b>", styles["Heading3"]))
        elements.append(
            Paragraph(
                cfg.attestation_statement,
                body_style,
            )
        )

        doc.build(elements)
        return output_path

    def generate_certificate(
        self,
        document_name: str,
        entities: List[RedactionEntity],
        output_path: Path,
        reviewer_name: Optional[str] = None,
        agency_name: Optional[str] = None,
        total_pages: int = 1,
        profile: str = "public_foia",
        enabled_domains: Optional[List[str]] = None,
        certificate_config: Optional[Union[CertificateConfig, Dict[str, Any]]] = None,
    ) -> Path:
        """Generate a customizable Compliance Redaction Certificate from document_name and entities list."""
        max_page = max([total_pages] + [e.page_number for e in entities]) if entities else total_pages
        domains = enabled_domains or sorted({getattr(e, "data_domain", "PII") or "PII" for e in entities}) or ["PII", "PHI", "PPI"]
        plan = RedactionPlan(
            document_name=document_name,
            total_pages=max_page,
            entities=entities,
            profile=profile,
            enabled_domains=domains,
        )
        return self.generate_pdf_certificate(
            plan=plan,
            output_path=output_path,
            agency_name=agency_name,
            reviewer_name=reviewer_name,
            certificate_config=certificate_config,
        )
