"""Phase 0 Architecture Spike: On-Device Extraction + PikePDF Stream Surgery Verification."""

import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from redact_gov.config import settings
from redact_gov.pipeline import RedactionPipeline
from redact_gov.core.statutes import get_statute

console = Console()


def main() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]RedactGov Phase 0 Verification Spike[/bold cyan]\n"
            "Architecture: Sovereign On-Device Inference (Google Gemma 4 E4B) + PikePDF Stream Surgery\n"
            "Target Sponsor: VIPC CCF Launch Grant ($50,000) & Virginia Venture Partners",
            border_style="blue",
        )
    )

    test_pdf = settings.SYNTHETIC_DIR / "police_incident_narrative.pdf"
    if not test_pdf.is_file():
        console.print("[red]Synthetic PDF not found. Run scripts/generate_synthetic_pdfs.py first.[/red]")
        sys.exit(1)

    pipeline = RedactionPipeline()

    console.print(f"\n[bold]Step 1: Document Ingestion & On-Device Entity Discovery[/bold]")
    plan = pipeline.create_plan(test_pdf)

    table = Table(title="Discovered Redaction Targets (Virginia Statutory Mapping)")
    table.add_column("Page", justify="center", style="cyan")
    table.add_column("Target String", style="bold magenta")
    table.add_column("Category", style="yellow")
    table.add_column("Statutory Citation", style="green")
    table.add_column("Tier", style="blue")
    table.add_column("Confidence", justify="right", style="white")

    for entity in plan.entities:
        statute = get_statute(entity.statute_code)
        citation = statute.legal_citation if statute else entity.statute_code
        table.add_row(
            str(entity.page_number),
            entity.text,
            entity.category,
            citation,
            entity.tier,
            f"{entity.confidence:.2f}",
        )

    console.print(table)

    # Verify that Chief of Police is NOT in the redaction list (exclusion heuristic test)
    redacted_strings_lower = [e.text.lower() for e in plan.entities]
    assert "chief of police" not in redacted_strings_lower, "Exclusion failure: Chief of Police was marked for redaction!"
    console.print("[bold green]✓ Public Official Exclusion Test Passed:[/bold green] Chief of Police was properly preserved.")

    console.print(f"\n[bold]Step 2: PikePDF Stream Surgery & Metadata Eradication[/bold]")
    output_pdf = settings.OUTPUT_DIR / "spike_sanitized_police_record.pdf"
    certificate_pdf = settings.OUTPUT_DIR / "spike_vfoia_certificate.pdf"

    result = pipeline.execute_plan(
        input_pdf=test_pdf,
        plan=plan,
        output_pdf=output_pdf,
        certificate_pdf=certificate_pdf,
    )

    console.print(f"Sanitized Document: [bold]{output_pdf}[/bold]")
    console.print(f"Virginia Certificate: [bold]{certificate_pdf}[/bold]")
    console.print(f"Redaction Count: {result.redacted_count} elements burned into canvas")
    console.print(f"Execution Latency: {result.execution_time_seconds:.3f} seconds")

    console.print(f"\n[bold]Step 3: Forensic Extraction & Residual Byte Verification[/bold]")
    if result.verification_passed:
        console.print("[bold green]✓ ZERO RESIDUAL BYTES VERIFIED![/bold green]")
        console.print("  • pdfplumber text extraction returned 0 matches for scrubbed tokens.")
        console.print("  • Content streams decompressed and inspected: Tj/TJ glyphs successfully excised.")
        console.print("  • Metadata streams eradicated: /Metadata, /PieceInfo, /DocInfo stripped.")
    else:
        console.print("[bold red]✗ Verification Failed: Residual strings detected in output.[/bold red]")
        sys.exit(1)

    console.print(
        Panel.fit(
            "[bold green]PHASE 0 SPIKE COMPLETE & VERIFIED[/bold green]\n"
            "Ready for Phase 1 Gemma 4 E4B constrained JSON grammar calibration and Phase 2 Reviewer UI.",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
