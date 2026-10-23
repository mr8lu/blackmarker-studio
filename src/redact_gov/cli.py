"""Command-line interface for RedactGov sovereign on-device redaction engine."""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

from redact_gov.core.criteria import (
    DEFAULT_COORDINATE_CRITERIA,
    DEFAULT_FORM_FIELD_CRITERIA,
    DEFAULT_ROLE_CONSTRAINTS,
    RedactionCriteriaRegistry,
    ReleaseProfile,
)
from redact_gov.core.statutes import VIRGINIA_STATUTES, get_statute
from redact_gov.pipeline import RedactionPipeline

app = typer.Typer(
    name="aiblackmarker",
    help="AI Blackmarker (RedactGov): Sovereign, air-gapped on-device FOIA redaction engine powered by Google Gemma 4 E4B & PikePDF.",
    add_completion=False,
)
console = Console()


def _resolve_profile(profile_str: str) -> ReleaseProfile:
    """Normalize profile string to ReleaseProfile enum."""
    p = profile_str.lower().replace("-", "_")
    try:
        return ReleaseProfile(p)
    except ValueError:
        return ReleaseProfile.PUBLIC_FOIA


@app.command()
def redact(
    input_pdf: Path = typer.Argument(..., help="Path to input PDF document"),
    output: Path = typer.Option(Path("redacted_output.pdf"), "--output", "-o", help="Path for sanitized output PDF"),
    cert: Optional[Path] = typer.Option(None, "--cert", "-c", help="Path to generate Virginia FOIA Redaction Certificate PDF"),
    profile: str = typer.Option("public-foia", "--profile", help="Redaction release profile: 'public-foia', 'strict-privacy', 'environmental-review', 'law-enforcement'"),
    coord_policy: Optional[str] = typer.Option(None, "--coordinate-policy", "-p", help="Override coordinate policy: 'all', 'sensitive-only', or 'none'"),
    form_context: bool = typer.Option(True, "--assess-form-context/--no-assess-form-context", help="Assess form questions and box titles to govern redactions"),
    repair: bool = typer.Option(True, "--repair/--no-repair", help="Automatically heal imperfect fonts and malformed PDF structures"),
) -> None:
    """Redact a document using on-device Google Gemma 4 E4B and PikePDF stream surgery."""
    if not input_pdf.is_file():
        console.print(f"[bold red]Error:[/bold red] File '{input_pdf}' does not exist.")
        raise typer.Exit(1)

    rel_profile = _resolve_profile(profile)
    console.print(f"[bold blue]RedactGov[/bold blue] - Processing [bold]{input_pdf.name}[/bold] (Profile: [cyan]{rel_profile.value}[/cyan])...")
    
    pipeline = RedactionPipeline(
        profile=rel_profile,
        coordinate_policy=coord_policy or ("sensitive-only" if rel_profile == ReleaseProfile.ENVIRONMENTAL_REVIEW else "all"),
        assess_form_context=form_context,
    )

    plan = pipeline.create_plan(input_pdf, normalize_imperfect=repair, profile=rel_profile)
    console.print(f"Found [bold green]{len(plan.entities)}[/bold green] sensitive entity targets across [bold]{plan.total_pages}[/bold] pages.")

    result = pipeline.execute_plan(input_pdf, plan, output, cert, repair_imperfect=repair)

    if result.success and result.verification_passed:
        console.print("[bold green]✓ Sanitization Complete![/bold green]")
        console.print(f"  • Redactions Applied: {result.redacted_count}")
        console.print(f"  • Execution Time: {result.execution_time_seconds:.3f}s")
        console.print(f"  • Output PDF: [bold]{result.output_path}[/bold]")
        if result.certificate_path:
            console.print(f"  • Legal Certificate: [bold]{result.certificate_path}[/bold]")
        console.print("  • Byte-Level Verification: [bold green]PASSED (Zero residuals)[/bold green]")
    else:
        console.print("[bold red]Verification warning:[/bold red] Check manual audit log.")


@app.command()
def audit(
    input_pdf: Path = typer.Argument(..., help="Path to input PDF document to inspect"),
    profile: str = typer.Option("public-foia", "--profile", help="Redaction release profile: 'public-foia', 'strict-privacy', 'environmental-review', 'law-enforcement'"),
    coord_policy: Optional[str] = typer.Option(None, "--coordinate-policy", "-p", help="Override coordinate policy: 'all', 'sensitive-only', or 'none'"),
    form_context: bool = typer.Option(True, "--assess-form-context/--no-assess-form-context", help="Assess form questions and box titles to govern redactions"),
    repair: bool = typer.Option(True, "--repair/--no-repair", help="Automatically heal imperfect fonts and malformed PDF structures"),
) -> None:
    """Inspect and audit sensitive entities and statutory citations without modifying the PDF."""
    if not input_pdf.is_file():
        console.print(f"[bold red]Error:[/bold red] File '{input_pdf}' does not exist.")
        raise typer.Exit(1)

    rel_profile = _resolve_profile(profile)
    effective_coord = coord_policy or ("sensitive-only" if rel_profile == ReleaseProfile.ENVIRONMENTAL_REVIEW else "all")
    pipeline = RedactionPipeline(
        profile=rel_profile,
        coordinate_policy=effective_coord,
        assess_form_context=form_context,
    )
    plan = pipeline.create_plan(input_pdf, normalize_imperfect=repair, profile=rel_profile, coordinate_policy=effective_coord)

    table = Table(title=f"RedactGov Audit Report: {input_pdf.name} (Profile: {rel_profile.value})")
    table.add_column("Page", justify="center", style="cyan")
    table.add_column("Entity Text", style="magenta")
    table.add_column("Category", style="yellow")
    table.add_column("Context / Prompt", style="cyan")
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
            entity.context_label or "-",
            citation,
            f"{entity.confidence:.2f}",
            str(len(entity.bounding_boxes)),
        )

    console.print(table)


@app.command()
def criteria() -> None:
    """List centralized redaction criteria, role constraints, and form prompts."""
    # 1. Role Constraints Table
    role_table = Table(title="Centralized Role Constraints & Allowlist Rules")
    role_table.add_column("Role", style="cyan")
    role_table.add_column("Exempt From Categories", style="yellow")
    role_table.add_column("Allowlisted Titles Sample", style="white")

    for role, constraint in DEFAULT_ROLE_CONSTRAINTS.items():
        sample_titles = ", ".join(list(constraint.allowlisted_titles)[:4]) + "..."
        role_table.add_row(
            role.value,
            ", ".join(constraint.exempt_from_categories),
            sample_titles,
        )
    console.print(role_table)

    # 2. Form Field Prompts Table
    field_table = Table(title="Centralized Form Question & Field Criteria")
    field_table.add_column("Criterion ID", style="cyan")
    field_table.add_column("Target Category", style="yellow")
    field_table.add_column("Statute Code", style="green")
    field_table.add_column("Sample Keywords / Prompts", style="white")

    for fc in DEFAULT_FORM_FIELD_CRITERIA:
        field_table.add_row(
            fc.id,
            fc.target_category,
            fc.statute_code,
            ", ".join(fc.match_keywords[:3]),
        )
    console.print(field_table)

    # 3. Coordinate Contexts Table
    coord_table = Table(title="Centralized Coordinate Context Classifications")
    coord_table.add_column("Context Type", style="cyan")
    coord_table.add_column("Statute Code", style="green")
    coord_table.add_column("Redacted in Sensitive-Only", justify="center", style="magenta")
    coord_table.add_column("Defining Keywords Sample", style="white")

    for cc in DEFAULT_COORDINATE_CRITERIA:
        sample_kw = ", ".join(list(cc.keywords)[:4]) + "..."
        coord_table.add_row(
            cc.context_type,
            cc.statute_code,
            "Yes" if cc.redact_in_sensitive_only else "No (Preserved)",
            sample_kw,
        )
    console.print(coord_table)


@app.command()
def inspect(
    input_pdf: Path = typer.Argument(..., help="Path to input PDF document to analyze for structural/font defects"),
) -> None:
    """Inspect a PDF document for font descriptor defects (e.g., FontBBox=None) and structural anomalies."""
    if not input_pdf.is_file():
        console.print(f"[bold red]Error:[/bold red] File '{input_pdf}' does not exist.")
        raise typer.Exit(1)

    from redact_gov.core.normalizer import DocumentNormalizer
    normalizer = DocumentNormalizer()
    report = normalizer.inspect_document(input_pdf)

    status_str = "[bold red]Imperfect / Defective[/bold red]" if report.is_imperfect else "[bold green]Clean / Standard[/bold green]"
    console.print(f"[bold blue]Document Inspection:[/bold blue] {input_pdf.name}")
    console.print(f"Status: {status_str} | Total Pages: {report.total_pages}")

    if report.issues:
        table = Table(title="Detected Structural & Font Imperfections")
        table.add_column("Issue Description", style="yellow")
        for issue in report.issues:
            table.add_row(issue)
        console.print(table)
        console.print("[cyan]Hint:[/cyan] RedactGov will automatically heal these imperfections when run with default settings (--repair).")
    else:
        console.print("[green]No font descriptor or structural anomalies detected. Document is clean.[/green]")


@app.command()
def statutes() -> None:
    """List all supported Virginia statutory exemptions."""
    table = Table(title="Virginia Statutory Redaction Registry (Va. Code § 2.2-3700 et seq.)")
    table.add_column("Statute Code", style="green")
    table.add_column("Citation", style="cyan")
    table.add_column("Category", style="yellow")
    table.add_column("Short Title", style="magenta")
    table.add_column("Description", style="white")

    for statute in VIRGINIA_STATUTES.values():
        table.add_row(
            statute.code,
            statute.legal_citation,
            statute.category,
            statute.short_title,
            statute.description,
        )

    console.print(table)


@app.command()
def worker(
    idle_timeout: float = typer.Option(
        180.0,
        "--idle-timeout",
        help="Seconds of inactivity before the ephemeral helper unloads Gemma 4 E4B and exits.",
    ),
) -> None:
    """Run the ephemeral JSON-RPC stdio worker for the native macOS utility (DigUp pattern)."""
    from redact_gov.worker import EphemeralRedactWorker

    helper = EphemeralRedactWorker(idle_timeout=idle_timeout)
    helper.serve_stdio()


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address for local review server"),
    port: int = typer.Option(8000, "--port", help="Bind port for local review server"),
) -> None:
    """Launch the local FastAPI Human-in-the-Loop web server."""
    import uvicorn

    uvicorn.run("redact_gov.api.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    app()
