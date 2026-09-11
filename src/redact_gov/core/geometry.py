"""Spatial geometry engine for mapping token offsets to PDF bounding boxes."""

from typing import List, Tuple
from pathlib import Path
import pdfplumber

from redact_gov.core.models import BoundingBox


def extract_page_text_with_char_geometry(
    pdf_path: Path, page_number: int
) -> Tuple[str, List[dict]]:
    """Extract full page text and character-level geometry using pdfplumber."""
    with pdfplumber.open(pdf_path) as pdf:
        if page_number < 1 or page_number > len(pdf.pages):
            raise IndexError(f"Page number {page_number} is out of bounds (1-{len(pdf.pages)})")
        
        page = pdf.pages[page_number - 1]
        text = page.extract_text(layout=False) or ""
        chars = page.chars
        return text, chars


def find_text_bounding_boxes(
    pdf_path: Path, page_number: int, target_text: str
) -> List[BoundingBox]:
    """Locate all spatial occurrences of target_text on a specific page.
    
    Coordinates are normalized to standard PDF point coordinates
    where (0, 0) is at the bottom-left of the page canvas.
    Handles multi-line targets seamlessly by searching per-line segments.
    """
    boxes: List[BoundingBox] = []
    target_clean = target_text.strip()
    if not target_clean:
        return boxes

    with pdfplumber.open(pdf_path) as pdf:
        if page_number < 1 or page_number > len(pdf.pages):
            return boxes
        
        page = pdf.pages[page_number - 1]
        page_height = float(page.height)

        # Build list of search search queries: full string, or lines if multi-line
        queries = [target_clean]
        if "\n" in target_clean:
            queries.extend([line.strip() for line in target_clean.splitlines() if len(line.strip()) > 1])

        seen_coords = set()
        for q in queries:
            matches = page.search(q, regex=False, case=False)
            for match in matches:
                x0 = round(float(match["x0"]), 2)
                x1 = round(float(match["x1"]), 2)
                top = float(match["top"])
                bottom = float(match["bottom"])

                # Convert to standard PDF coordinate system (bottom-left origin)
                y0 = round(page_height - bottom, 2)
                y1 = round(page_height - top, 2)

                coord_key = (x0, y0, x1, y1)
                if coord_key not in seen_coords:
                    seen_coords.add(coord_key)
                    boxes.append(
                        BoundingBox(
                            page=page_number,
                            x0=x0,
                            y0=y0,
                            x1=x1,
                            y1=y1,
                        )
                    )

    return boxes


def get_document_page_count(pdf_path: Path) -> int:
    """Return total number of pages in PDF."""
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)
