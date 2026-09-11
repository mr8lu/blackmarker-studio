"""Spatial geometry engine for mapping token offsets to PDF bounding boxes."""

import re
from typing import List, Optional, Tuple
from pathlib import Path
import pdfplumber

from redact_gov.core.models import BoundingBox
from redact_gov.core.normalizer import silence_parser_warnings

# Ensure pdfminer warnings are suppressed whenever geometry engine is loaded
silence_parser_warnings()


def extract_page_text_with_char_geometry(
    pdf_path: Path, page_number: int
) -> Tuple[str, List[dict]]:
    """Extract full page text and character-level geometry using pdfplumber."""
    silence_parser_warnings()
    with pdfplumber.open(pdf_path) as pdf:
        if page_number < 1 or page_number > len(pdf.pages):
            raise IndexError(f"Page number {page_number} is out of bounds (1-{len(pdf.pages)})")
        
        page = pdf.pages[page_number - 1]
        text = page.extract_text(layout=False) or ""
        chars = page.chars
        return text, chars


def find_text_bounding_boxes(
    pdf_path: Path,
    page_number: int,
    target_text: str,
    page_obj: Optional[pdfplumber.page.Page] = None,
) -> List[BoundingBox]:
    """Locate all spatial occurrences of target_text on a specific page.
    
    Coordinates are normalized to standard PDF point coordinates
    where (0, 0) is at the bottom-left of the page canvas.
    Handles multi-line targets seamlessly by searching per-line segments.
    Provides robust fallbacks for imperfect documents with non-standard spacing
    or degenerate font bounding box metrics.
    """
    silence_parser_warnings()
    boxes: List[BoundingBox] = []
    target_clean = target_text.strip()
    if not target_clean:
        return boxes

    def _search_page(page: pdfplumber.page.Page) -> List[BoundingBox]:
        page_boxes: List[BoundingBox] = []
        page_height = float(page.height)

        # Build list of search queries: full string, lines if multi-line, or numeric coordinates
        queries = [target_clean]
        if "\n" in target_clean:
            queries.extend([line.strip() for line in target_clean.splitlines() if len(line.strip()) > 1])

        # Add coordinate numeric tokens as fallbacks if label/degree symbols prevent exact match
        coord_nums = re.findall(r"\b\d{1,3}\.\d{4,8}\b", target_clean)
        for num in coord_nums:
            if num not in queries:
                queries.append(num)

        seen_coords = set()
        for q in queries:
            # First attempt: exact substring match
            matches = page.search(q, regex=False, case=False)

            # Fallback for imperfect PDFs: flexible whitespace regex match
            if not matches and len(q.split()) > 1:
                pattern = r"\s+".join(re.escape(w) for w in q.split())
                matches = page.search(pattern, regex=True, case=False)

            for match in matches:
                x0 = round(float(match["x0"]), 2)
                x1 = round(float(match["x1"]), 2)
                top = float(match["top"])
                bottom = float(match["bottom"])

                # Guard against degenerate font bounding boxes in imperfect documents
                if abs(bottom - top) < 1.0:
                    bottom = top + 12.0
                if abs(x1 - x0) < 1.0:
                    x1 = x0 + max(12.0, len(q) * 6.5)

                # Convert to standard PDF coordinate system (bottom-left origin)
                y0 = round(page_height - bottom, 2)
                y1 = round(page_height - top, 2)

                coord_key = (x0, y0, x1, y1)
                if coord_key not in seen_coords:
                    seen_coords.add(coord_key)
                    page_boxes.append(
                        BoundingBox(
                            page=page_number,
                            x0=x0,
                            y0=y0,
                            x1=x1,
                            y1=y1,
                        )
                    )
        return page_boxes

    if page_obj is not None:
        return _search_page(page_obj)

    with pdfplumber.open(pdf_path) as pdf:
        if page_number < 1 or page_number > len(pdf.pages):
            return boxes
        return _search_page(pdf.pages[page_number - 1])


def get_document_page_count(pdf_path: Path) -> int:
    """Return total number of pages in PDF."""
    silence_parser_warnings()
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)
