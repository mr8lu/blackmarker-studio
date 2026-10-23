"""Generates realistic synthetic multi-page PDF documents for Blackmarker Studio testbed."""

from pathlib import Path
from redact_gov.config import SYNTHETIC_DOCUMENTS, _render_synthetic_pdf, settings


def text_to_pdf(txt_path: Path, pdf_path: Path, title: str) -> None:
    """Convert formatted text file into a structured PDF document."""
    raw_content = txt_path.read_text(encoding="utf-8")
    _render_synthetic_pdf(raw_content, pdf_path, title)


def main() -> None:
    settings.SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)
    for filename, doc_title, raw_text in SYNTHETIC_DOCUMENTS:
        pdf_file = settings.SYNTHETIC_DIR / filename
        _render_synthetic_pdf(raw_text, pdf_file, doc_title)
        print(f"Generated synthetic PDF: {pdf_file.name}")


if __name__ == "__main__":
    main()
