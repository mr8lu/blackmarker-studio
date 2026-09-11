"""Interactive CLI Trial Harness for RedactGov and Google Gemma 4 E4B."""

import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from redact_gov.config import settings
from redact_gov.core.statutes import get_statute
from redact_gov.pipeline import RedactionPipeline
from redact_gov.engines.deterministic import DeterministicRedactionEngine
from redact_gov.engines.contextual import ContextualGemmaEngine

console = Console()


def try_text_snippet(user_text: str) -> None:
    console.print("\n[bold cyan]─── Analyzing Text with RedactGov Pipeline ───[/bold cyan]")
    
    tier1 = DeterministicRedactionEngine()
    tier2 = ContextualGemmaEngine()

    t1_entities = tier1.scan_text(user_text)
    t2_entities = tier2.analyze_text(user_text)

    all_entities = t1_entities + t2_entities
    if not all_entities:
        console.print("[green]No protected Virginia statutory entities or sensitive locations detected.[/green]")
        return

    table = Table(title="Detected Statutory Redaction Targets")
    table.add_column("Verbatim Text", style="bold magenta")
    table.add_column("Category", style="yellow")
    table.add_column("Statutory Authority", style="green")
    table.add_column("Engine Tier", style="blue")
    table.add_column("Confidence", justify="right")

    for e in all_entities:
        statute = get_statute(e.statute_code)
        citation = statute.legal_citation if statute else e.statute_code
        table.add_row(e.text, e.category, citation, e.tier, f"{e.confidence:.2f}")

    console.print(table)

    # Preview masked output
    masked_text = user_text
    for e in all_entities:
        masked_text = masked_text.replace(e.text, f"[REDACTED: {e.statute_code}]")

    console.print(Panel(masked_text, title="Masked Preview (Virginia FOIA Air-Gapped Clean)", border_style="green"))


def try_pdf_document(pdf_path: Path) -> None:
    console.print(f"\n[bold cyan]─── Processing PDF: {pdf_path.name} ───[/bold cyan]")
    pipeline = RedactionPipeline()

    plan = pipeline.create_plan(pdf_path)
    console.print(f"Entities discovered: [bold magenta]{len(plan.entities)}[/bold magenta] across [bold]{plan.total_pages}[/bold] pages.")

    table = Table(title=f"Redaction Manifest: {pdf_path.name}")
    table.add_column("Page", justify="center", style="cyan")
    table.add_column("Entity Text", style="bold magenta")
    table.add_column("Category", style="yellow")
    table.add_column("Virginia Statute", style="green")

    for e in plan.entities:
        statute = get_statute(e.statute_code)
        citation = statute.legal_citation if statute else e.statute_code
        table.add_row(str(e.page_number), e.text, e.category, citation)

    console.print(table)

    out_pdf = settings.OUTPUT_DIR / f"trial_sanitized_{pdf_path.name}"
    cert_pdf = settings.OUTPUT_DIR / f"trial_cert_{pdf_path.stem}.pdf"

    result = pipeline.execute_plan(pdf_path, plan, out_pdf, cert_pdf)
    if result.success and result.verification_passed:
        console.print(f"[bold green]✓ Document Successfully Sanitized![/bold green]")
        console.print(f"  • Sanitized PDF: [bold]{out_pdf}[/bold]")
        console.print(f"  • VFOIA Certificate: [bold]{cert_pdf}[/bold]")
        console.print(f"  • Execution Latency: {result.execution_time_seconds:.3f}s")
        console.print(f"  • Byte Sanitization: [bold green]100% (Zero Residuals)[/bold green]")


def main():
    console.print(
        Panel.fit(
            "[bold green]RedactGov On-Device Trial Harness[/bold green]\n"
            "Engine: Google Gemma 4 E4B + PikePDF Content Stream Excision\n"
            "Capabilities: Formatted PII, Juveniles, Victims, Informants, Endangered Species & GPS",
            border_style="green",
        )
    )

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        path = Path(arg)
        if path.is_file() and path.suffix.lower() == ".pdf":
            try_pdf_document(path)
            return
        else:
            try_text_snippet(arg)
            return

    console.print("\nChoose an option to try:")
    console.print("  [1] Try Endangered Species Assessment PDF (Caves, GPS, Sensitive Flora/Fauna)")
    console.print("  [2] Try Police Incident Report PDF (Juveniles, Informant, Victim, SSN, VA Driver's License)")
    console.print("  [3] Try School Disciplinary Transcript PDF (Student records, IEP, parents)")
    console.print("  [4] Enter custom text snippet interactively")
    
    choice = Prompt.ask("Select option", choices=["1", "2", "3", "4"], default="1")

    if choice == "1":
        try_pdf_document(settings.SYNTHETIC_DIR / "environmental_impact_assessment.pdf")
    elif choice == "2":
        try_pdf_document(settings.SYNTHETIC_DIR / "police_incident_narrative.pdf")
    elif choice == "3":
        try_pdf_document(settings.SYNTHETIC_DIR / "school_board_disciplinary_record.pdf")
    elif choice == "4":
        sample = Prompt.ask("\nEnter text to redact")
        try_text_snippet(sample)


if __name__ == "__main__":
    main()
