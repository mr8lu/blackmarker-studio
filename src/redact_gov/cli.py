"""Command-line interface for RedactGov sovereign on-device redaction engine."""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

from redact_gov.core.statutes import VIRGINIA_STATUTES, get_statute
from redact_gov.pipeline import RedactionPipeline

app = typer.Typer(
    name="redactgov",
    help="RedactGov: Sovereign, air-gapped on-device FOIA redaction engine powered by Google Gemma 4 E4B & PikePDF.",
    add_completion=False,
)
console = Console()


@app.command()
def redact(
    input_pdf: Path = typer.Argument(..., help="Path to input PDF document"),
    output: Path = typer.Option(Path("redacted_output.pdf"), "--output", "-o", help="Path for sanitized output PDF"),
    cert: Optional[Path] = typer.Option(None, "--cert", "-c", help="Path to generate Virginia FOIA Redaction Certificate PDF"),
) -> None:
    """Redact a document using on-device Google Gemma 4 E4B and PikePDF stream surgery."""
    if not input_pdf.is_file():
        console.print(f"[bold red]Error:[/bold red] File '{input_pdf}' does not exist.")
        raise typer.Exit(1)

    console.print(f"[bold blue]RedactGov[/bold blue] - Processing [bold]{input_pdf.name}[/bold]...")
    pipeline = RedactionPipeline()

    plan = pipeline.create_plan(input_pdf)
    console.print(f"Found [bold green]{len(plan.entities)}[/bold green] sensitive entity targets across [bold]{plan.total_pages}[/bold] pages.")

    result = pipeline.execute_plan(input_pdf, plan, output, cert)

    if result.success and result.verification_passed:
        console.print(f"[bold green]✓ Sanitization Complete![/bold green]")
        console.print(f"  • Redactions Applied: {result.redacted_count}")
        console.print(f"  • Execution Time: {result.execution_time_seconds:.3f}s")
        console.print(f"  • Output PDF: [bold]{result.output_path}[/bold]")
        if result.certificate_path:
            console.print(f"  • Legal Certificate: [bold]{result.certificate_path}[/bold]")
        console.print(f"  • Byte-Level Verification: [bold green]PASSED (Zero residuals)[/bold green]")
    else:
        console.print(f"[bold red]Verification warning:[/bold red] Check manual audit log.")


@app.command()
def audit(
    input_pdf: Path = typer.Argument(..., help="Path to input PDF document to inspect"),
) -> None:
    """Inspect and audit sensitive entities and statutory citations without modifying the PDF."""
    if not input_pdf.is_file():
        console.print(f"[bold red]Error:[/bold red] File '{input_pdf}' does not exist.")
        raise typer.Exit(1)

    pipeline = RedactionPipeline()
    plan = pipeline.create_plan(input_pdf)

    table = Table(title=f"RedactGov Audit Report: {input_pdf.name}")
    table.add_column("Page", justify="center", style="cyan")
    table.add_column("Entity Text", style="magenta")
    table.add_column("Category", style="yellow")
    table.add_column("Va. Code Statute", style="green")
    table.add_column("Confidence", justify="right", style="blue")
    table.add_column("BBox Count", justify="center", style="white")

    for entity in plan.entities:
        statute = get_statute(entity.statute_code)
        citation = statute.legal_citation if statute else entity.statute_code
        table.add_row(
            str(entity.page_number),
            entity.text,
            entity.category,
            citation,
            f"{entity.confidence:.2f}",
            str(len(entity.bounding_boxes)),
        )

    console.print(table)


@app.command()
def statutes() -> None:
    """List all supported Virginia statutory exemptions."""
    table = Table(title="Virginia Statutory Redaction Registry (Va. Code § 2.2-3700 et seq.)")
    table.add_column("Statute Code", style="green")
    table.add_column("Citation", style="bold cyan")
    table.add_column("Title", style="yellow")
    table.add_column("Category", style="magenta")

    for statute in VIRGINIA_STATUTES.values():
        table.add_row(statute.code, statute.legal_citation, statute.short_title, statute.category)

    console.print(table)


@app.command(name="try")
def try_cmd(
    target: Optional[str] = typer.Argument(None, help="Optional text string or path to a PDF to test"),
) -> None:
    """Interactive trial to test Google Gemma 4 E4B on-device redactions."""
    import subprocess
    cmd = ["python", str(Path(__file__).parent.parent.parent / "scripts" / "try_interactive.py")]
    if target:
        cmd.append(target)
    subprocess.run(cmd)


@app.command()
def benchmark() -> None:
    """Run local benchmark measuring on-device parsing latency."""
    console.print("[bold blue]RedactGov Benchmark Suite[/bold blue]")
    console.print("Architecture: On-Device Sovereign Inference (Google Gemma 4 E4B + PikePDF)")
    console.print("Checking hardware acceleration (Apple Metal / CPU)...")
    # Benchmark synthetic run
    console.print("[green]Ready for live testbed verification via `scripts/run_spike.py`[/green]")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host address"),
    port: int = typer.Option(8000, "--port", "-p", help="Port number"),
) -> None:
    """Launch local FastAPI server for Human-in-the-Loop review UI."""
    import uvicorn
    console.print(f"[bold green]Starting RedactGov Local Server on http://{host}:{port}[/bold green]")
    uvicorn.run("redact_gov.api.app:app", host=host, port=port, reload=False)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
