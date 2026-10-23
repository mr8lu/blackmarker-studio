"""Spatial coordinate extraction and bounding box geometry engine using pdfplumber."""

from pathlib import Path
import re
from typing import Any, List, Optional, Tuple
import pdfplumber

from redact_gov.core.models import BoundingBox
from redact_gov.core.normalizer import silence_parser_warnings


def extract_stream_runs(chars: List[dict], page_height: float) -> List[dict]:
    """
    Group consecutive pdfplumber page.chars in native PDF content-stream order
    into clean horizontal text runs with exact character-level bounding boxes.
    Separates foreground filled-in form fields and comb-box digits from
    background underlines and unmapped (cid:...) template fonts.
    """
    runs: List[dict] = []
    for c in chars:
        t = c.get("text", "")
        if not t or t.startswith("(cid:"):
            continue
        x0, x1 = float(c["x0"]), float(c["x1"])
        top, bottom = float(c["top"]), float(c["bottom"])
        if runs:
            prev = runs[-1]
            same_y = abs(top - prev["top_ref"]) <= 2.5
            dx = x0 - prev["x1"]
            if same_y and -1.5 <= dx <= 25.0:
                if dx > 3.5 and not prev["text"].endswith(" ") and t != " ":
                    prev["text"] += " "
                    prev["char_Map"].append(None)
                prev["text"] += t
                prev["char_Map"].extend([c] * len(t))
                prev["x0"] = min(prev["x0"], x0)
                prev["x1"] = max(prev["x1"], x1)
                prev["top"] = min(prev["top"], top)
                prev["bottom"] = max(prev["bottom"], bottom)
                prev["chars"].append(c)
                continue
        runs.append(
            {
                "text": t,
                "top_ref": top,
                "x0": x0,
                "x1": x1,
                "top": top,
                "bottom": bottom,
                "chars": [c],
                "char_Map": [c] * len(t),
            }
        )
    return runs


def extract_clean_page_text(page: Any) -> str:
    """
    Extract page text while stripping unmapped (cid:...) font placeholders,
    reconstructing underline-interleaved fields, and appending clean content-stream
    runs (comb-box digits and foreground form fields obscured by overlapping fonts).
    """
    raw_text = page.extract_text(layout=False) or ""
    clean_text = re.sub(r"\(cid:\d+\)", "", raw_text)

    extra_lines: List[str] = []
    for line in clean_text.splitlines():
        if "_" in line and sum(ch.isdigit() for ch in line) >= 4:
            deunderlined = re.sub(r"[ \t]*_[ \t]*", "", line).strip()
            if deunderlined and deunderlined != line.strip():
                extra_lines.append(deunderlined)

    try:
        page_height = float(page.height)
        runs = extract_stream_runs(page.chars, page_height)
        for r in runs:
            r_txt = r["text"].strip()
            if len(r_txt) < 3:
                continue
            # Include any stream run that was corrupted/split in spatial extract_text
            # or is a comb-box digit sequence
            digit_count = sum(ch.isdigit() for ch in r_txt)
            if r_txt not in clean_text or (digit_count >= 6 and " " in r_txt):
                if r_txt not in extra_lines:
                    extra_lines.append(r_txt)
    except Exception:
        pass

    if extra_lines:
        return f"{clean_text}\n" + "\n".join(extra_lines)
    return clean_text


def extract_page_text_with_char_geometry(
    pdf_path: Path, page_number: int
) -> Tuple[str, List[dict]]:
    """
    Extract full text of a 1-indexed page along with character-level bounding box metadata.
    """
    silence_parser_warnings()
    with pdfplumber.open(pdf_path) as pdf:
        if page_number < 1 or page_number > len(pdf.pages):
            return "", []
        page = pdf.pages[page_number - 1]
        text = extract_clean_page_text(page)
        return text, page.chars


def _bbox_from_chars(chars: List[dict], page_number: int, page_height: float) -> BoundingBox:
    x0 = min(float(c["x0"]) for c in chars)
    x1 = max(float(c["x1"]) for c in chars)
    top = min(float(c["top"]) for c in chars)
    bottom = max(float(c["bottom"]) for c in chars)
    return BoundingBox(
        page=page_number,
        x0=round(x0, 2),
        y0=round(page_height - bottom, 2),
        x1=round(x1, 2),
        y1=round(page_height - top, 2),
    )


def find_text_bounding_boxes(
    pdf_path: Path,
    page_number: int,
    target_text: str,
    page_obj: Optional[Any] = None,
) -> List[BoundingBox]:
    """
    Locate all spatial bounding boxes for a given target string on a 1-indexed PDF page.
    Converts pdfplumber top-origin coordinates into standard bottom-left PDF point coordinates
    so PikePDF stream excision and PDFKit annotations align to the exact point.

    If `page_obj` is provided from an already-open pdfplumber document, reuses it directly
    to avoid re-opening the PDF per entity.
    """
    silence_parser_warnings()
    q = target_text.strip()
    if not q:
        return []

    def _search_page(page: Any) -> List[BoundingBox]:
        page_height = float(page.height)
        boxes: List[BoundingBox] = []
        seen_box_keys = set()

        def _add_box(b: BoundingBox) -> None:
            key = (round(b.x0, 1), round(b.y0, 1), round(b.x1, 1), round(b.y1, 1))
            if key not in seen_box_keys:
                seen_box_keys.add(key)
                boxes.append(b)

        # 1. Search native content-stream runs first for clean, tight character bounds
        # (handles comb-box digits, underline-interleaved digits, and (cid:)-overlapped fields)
        runs = extract_stream_runs(page.chars, page_height)
        q_lower = q.lower()
        q_compact = re.sub(r"[\s_]+", "", q_lower)
        q_alnum = re.sub(r"[^a-z0-9]+", "", q_lower)

        for r in runs:
            r_text = r["text"]
            r_lower = r_text.lower()
            # Direct substring match within stream run
            start_idx = 0
            while True:
                idx = r_lower.find(q_lower, start_idx)
                if idx == -1:
                    break
                matched_chars = [
                    c for c in r["char_Map"][idx : idx + len(q_lower)] if c is not None
                ]
                if matched_chars:
                    _add_box(_bbox_from_chars(matched_chars, page_number, page_height))
                start_idx = idx + max(1, len(q_lower))

            # Compact match (ignoring spaces and underlines) for comb-box / spaced tokens
            if len(q_compact) >= 4:
                non_space_chars = [
                    c for c in r["chars"] if c.get("text", "").strip() not in ("", "_")
                ]
                r_compact = "".join(c.get("text", "").lower() for c in non_space_chars)
                if q_compact in r_compact:
                    c_idx = r_compact.find(q_compact)
                    # Build char-to-index mapping
                    pos = 0
                    slice_chars = []
                    for c in non_space_chars:
                        clen = len(c.get("text", ""))
                        if pos + clen > c_idx and pos < c_idx + len(q_compact):
                            slice_chars.append(c)
                        pos += clen
                    if slice_chars:
                        _add_box(_bbox_from_chars(slice_chars, page_number, page_height))
                elif len(q_alnum) >= 8 and q_alnum.isdigit():
                    # Pure digit match for comb-box fields where hyphens are in template layer (e.g. DOB / EIN)
                    digit_chars = [
                        c for c in r["chars"] if c.get("text", "").strip().isdigit()
                    ]
                    r_digits = "".join(c.get("text", "").strip() for c in digit_chars)
                    if r_digits == q_alnum and digit_chars:
                        _add_box(_bbox_from_chars(digit_chars, page_number, page_height))

        # 1b. Split-column multi-word match on the same horizontal row (e.g. First Name | Last Name)
        q_words = [w for w in q.split() if len(w) >= 2]
        if not boxes and len(q_words) >= 2:
            for i, r1 in enumerate(runs):
                if r1["text"].strip().lower() == q_words[0].lower():
                    row_runs = [r1]
                    for w in q_words[1:]:
                        w_low = w.lower()
                        for r2 in runs[i + 1 :]:
                            if (
                                abs(r2["top_ref"] - r1["top_ref"]) <= 3.0
                                and 0.0 <= (r2["x0"] - row_runs[-1]["x1"]) <= 220.0
                                and r2["text"].strip().lower() == w_low
                            ):
                                row_runs.append(r2)
                                break
                    if len(row_runs) == len(q_words):
                        for rr in row_runs:
                            _add_box(_bbox_from_chars(rr["chars"], page_number, page_height))

        # 2. Standard pdfplumber spatial search
        matches = page.search(q, regex=False, case=False)
        if not matches and len(q.split()) > 1:
            sep = r"\s+" if "\n" in q else r"[ \t_]+"
            pattern = sep.join(re.escape(w) for w in q.split())
            matches = page.search(pattern, regex=True, case=False)
        if not matches and len(q_compact) >= 6 and q_compact.isdigit():
            # Search for digits interleaved with horizontal spaces or underlines
            pattern = r"[ \t_-]*".join(re.escape(ch) for ch in q_compact)
            matches = page.search(pattern, regex=True, case=False)

        for m in matches:
            x0 = float(m["x0"])
            x1 = float(m["x1"])
            top = float(m["top"])
            bottom = float(m["bottom"])
            _add_box(
                BoundingBox(
                    page=page_number,
                    x0=round(x0, 2),
                    y0=round(page_height - bottom, 2),
                    x1=round(x1, 2),
                    y1=round(page_height - top, 2),
                )
            )
        return boxes

    if page_obj is not None:
        return _search_page(page_obj)

    with pdfplumber.open(pdf_path) as pdf:
        if page_number < 1 or page_number > len(pdf.pages):
            return []
        return _search_page(pdf.pages[page_number - 1])


def extract_words_in_bounding_box(
    pdf_path: Path,
    box: BoundingBox,
) -> List[str]:
    """
    Extract any underlying PDF words that intersect a user-drawn manual bounding box
    (given in standard bottom-left PDF point coordinates).
    """
    silence_parser_warnings()
    found_words: List[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        if box.page < 1 or box.page > len(pdf.pages):
            return []
        page = pdf.pages[box.page - 1]
        page_height = float(page.height)

        # Convert bottom-left PDF coordinates back to top-left pdfplumber coordinates
        target_top = page_height - box.y1
        target_bottom = page_height - box.y0

        words = page.extract_words() or []
        for w in words:
            wx0 = float(w["x0"])
            wx1 = float(w["x1"])
            wtop = float(w["top"])
            wbottom = float(w["bottom"])

            # Check rectangle intersection with generous tolerance
            horiz_overlap = (wx0 <= box.x1 + 2.0) and (wx1 >= box.x0 - 2.0)
            vert_overlap = (wtop <= target_bottom + 2.0) and (wbottom >= target_top - 2.0)
            if horiz_overlap and vert_overlap:
                txt = str(w.get("text", "")).strip()
                if txt:
                    found_words.append(txt)

    return found_words


def get_document_page_count(pdf_path: Path) -> int:
    """Return total page count of the PDF."""
    silence_parser_warnings()
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)
