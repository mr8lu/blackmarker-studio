"""PikePDF (QPDF) Low-Level Content Stream Surgery and Metadata Eradication Engine."""

from pathlib import Path
import re
from typing import Dict, List, Set, Tuple
import pikepdf

from redact_gov.core.models import BoundingBox, RedactionEntity
from redact_gov.core.normalizer import DocumentNormalizer, silence_parser_warnings


def _parse_tounicode_cmap(cmap_text: str) -> Dict[str, bytes]:
    """Parse a PDF /ToUnicode CMap stream into a mapping of Unicode characters to raw CID bytes."""
    char_to_cid: Dict[str, bytes] = {}
    for block in re.findall(r"beginbfchar(.*?)endbfchar", cmap_text, flags=re.DOTALL):
        for src_hex, dst_hex in re.findall(
            r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block
        ):
            try:
                cid_bytes = bytes.fromhex(src_hex)
                uni_str = bytes.fromhex(dst_hex).decode("utf-16-be", errors="ignore")
                if len(uni_str) == 1:
                    char_to_cid[uni_str] = cid_bytes
            except Exception:
                pass
    for block in re.findall(r"beginbfrange(.*?)endbfrange", cmap_text, flags=re.DOTALL):
        for m in re.finditer(
            r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block
        ):
            try:
                start_cid = int(m.group(1), 16)
                end_cid = int(m.group(2), 16)
                start_uni = int(m.group(3), 16)
                byte_len = max(1, len(m.group(1)) // 2)
                for offset in range(min(512, end_cid - start_cid + 1)):
                    cid_b = (start_cid + offset).to_bytes(byte_len, "big")
                    uch = chr(start_uni + offset)
                    char_to_cid[uch] = cid_b
            except Exception:
                pass
    if " " not in char_to_cid and "\xa0" in char_to_cid:
        char_to_cid[" "] = char_to_cid["\xa0"]
    return char_to_cid


def _extract_page_tounicode_cmaps(page: pikepdf.Page) -> List[Dict[str, bytes]]:
    """Extract all /ToUnicode character-to-CID maps from a page's Font resources."""
    cmaps: List[Dict[str, bytes]] = []
    try:
        res = page.get("/Resources")
        if not res:
            return cmaps
        fonts = res.get("/Font")
        if isinstance(fonts, pikepdf.Dictionary):
            for _, font_obj in fonts.items():
                if isinstance(font_obj, pikepdf.Dictionary) and "/ToUnicode" in font_obj:
                    tu = font_obj["/ToUnicode"]
                    if isinstance(tu, pikepdf.Stream):
                        cmap_text = tu.read_bytes().decode("latin1", errors="ignore")
                        parsed = _parse_tounicode_cmap(cmap_text)
                        if parsed:
                            cmaps.append(parsed)
    except Exception:
        pass
    return cmaps


def _mul_matrix(m1: List[float], m2: List[float]) -> List[float]:
    """Multiply two 3x3 PDF affine transformation matrices [a, b, c, d, e, f]."""
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return [
        a1 * a2 + b1 * c2,
        a1 * b2 + b1 * d2,
        c1 * a2 + d1 * c2,
        c1 * b2 + d1 * d2,
        e1 * a2 + f1 * c2 + e2,
        e1 * b2 + f1 * d2 + f2,
    ]


class PikePdfSanitizer:
    """
    True PDF redaction engine backed by pikepdf (QPDF).
    Performs content-stream glyph excision (`Tj`/`TJ` operator scrubbing),
    draws opaque black vector rectangles over target coordinates,
    and strips all XMP/DocInfo metadata and incremental revisions.
    """

    def __init__(self, auto_normalize: bool = True):
        self.auto_normalize = auto_normalize
        self.normalizer = DocumentNormalizer()

    def sanitize_document(
        self,
        input_pdf: Path,
        output_pdf: Path,
        entities: List[RedactionEntity],
        eradicate_metadata: bool = True,
        repair_imperfect: bool = True,
    ) -> Tuple[bool, int]:
        """
        Execute true physical sanitization on input_pdf and write clean PDF to output_pdf.
        Automatically repairs structural/font defects in imperfect PDFs prior to stream surgery.
        Returns (success, redacted_entity_count).
        """
        silence_parser_warnings()
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        approved_entities = [e for e in entities if e.approved]

        # Group target strings and bounding boxes by 1-indexed page number
        targets_by_page = {}
        boxes_by_page = {}
        for entity in approved_entities:
            p = entity.page_number
            txt = entity.text.strip()
            # Manual marquee redactions starting with "[Manual" rely on spatial boxes or enriched words
            if txt and not txt.startswith("[Manual") and not txt.startswith("[MANUAL"):
                targets_by_page.setdefault(p, set()).add(txt)
            for box in entity.bounding_boxes:
                boxes_by_page.setdefault(box.page, []).append(box)

        applied_count = 0

        with pikepdf.open(input_pdf, attempt_recovery=True) as pdf:
            # 0. Pre-sanitization normalization for imperfect PDFs (broken FontBBox, unreferenced streams)
            if self.auto_normalize and repair_imperfect:
                self.normalizer.repair_font_descriptors(pdf)

            for page_idx, page in enumerate(pdf.pages, start=1):
                page_targets = list(targets_by_page.get(page_idx, []))
                page_boxes = boxes_by_page.get(page_idx, [])

                if not page_targets and not page_boxes:
                    continue

                # 1. Excise matching text strings and spatially-contained glyphs from page content stream
                excised = self._excise_page_content_streams(
                    pdf, page, page_targets, page_boxes
                )
                applied_count += max(excised, len(page_targets), len(page_boxes))

                # 2. Burn opaque black vector rectangles over bounding boxes
                if page_boxes:
                    self._burn_opaque_rectangles(pdf, page, page_boxes)

                # 3. Remove any interactive annotations / form widgets on the page
                if "/Annots" in page:
                    del page["/Annots"]

            # Also remove AcroForm interactive field values so hidden widget strings don't survive
            if "/AcroForm" in pdf.Root:
                del pdf.Root["/AcroForm"]

            # 4. Eradicate XMP and DocInfo metadata
            if eradicate_metadata:
                self._eradicate_metadata(pdf)

            # 5. Save with linearize/clean options (eliminates incremental revision history)
            pdf.save(
                output_pdf,
                linearize=False,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
                compress_streams=True,
            )

        return True, len(approved_entities)

    def _excise_page_content_streams(
        self,
        pdf: pikepdf.Pdf,
        page: pikepdf.Page,
        target_strings: List[str],
        target_boxes: List[BoundingBox],
    ) -> int:
        """
        Parse PDF page content stream instructions and remove/blank out any `Tj`, `TJ`, `'`, `"`
        text-showing operators whose operands match a target string OR whose rendered page
        coordinates fall inside a target redaction bounding box.
        """
        if not target_strings and not target_boxes:
            return 0

        excised_hits = 0
        instructions = list(pikepdf.parse_content_stream(page))
        new_instructions = []

        # Prepare byte and token sets for fast matching
        targets_bytes: List[bytes] = []
        cid_replacements: List[Tuple[bytes, bytes]] = []
        word_targets_bytes: List[bytes] = []
        word_cid_replacements: List[Tuple[bytes, bytes]] = []
        allowed_spatial_tokens: Set[bytes] = set()
        allowed_spatial_chars: Set[bytes] = set()
        page_cmaps = _extract_page_tounicode_cmaps(page)

        for t in sorted(target_strings, key=len, reverse=True):
            tb = t.encode("latin1", errors="ignore")
            if tb:
                targets_bytes.append(tb)
            # Also add compact (space-stripped) version if multi-spaced
            t_compact = "".join(t.split())
            if len(t_compact) >= 5 and t_compact != t:
                targets_bytes.append(t_compact.encode("latin1", errors="ignore"))
            # Encode target via each font's /ToUnicode CMap on this page (handles /Identity-H Type0 fonts)
            for cmap in page_cmaps:
                space_cid = cmap.get(" ") or cmap.get("\xa0")
                for variant in {t, t.lower(), t.upper(), t.title()}:
                    if variant and all(ch in cmap for ch in variant):
                        enc_cid = b"".join(cmap[ch] for ch in variant)
                        if enc_cid:
                            repl_cid = (
                                space_cid * len(variant)
                                if space_cid and len(space_cid) * len(variant) == len(enc_cid)
                                else b"\x00" * len(enc_cid)
                            )
                            cid_replacements.append((enc_cid, repl_cid))
            # Add individual tokens and characters for spatial bounding-box verification
            for tok in t.split():
                tok_b = tok.encode("latin1", errors="ignore").lower()
                if tok_b:
                    allowed_spatial_tokens.add(tok_b)
                # Strip punctuation (commas, hyphens, periods) for token matching
                tok_clean_str = tok.strip(",.:;#-()")
                tok_clean = tok_clean_str.encode("latin1", errors="ignore").lower()
                if tok_clean:
                    allowed_spatial_tokens.add(tok_clean)
                if len(tok_clean_str) >= 3:
                    word_targets_bytes.append(tok_clean_str.encode("latin1", errors="ignore"))
                    for cmap in page_cmaps:
                        space_cid = cmap.get(" ") or cmap.get("\xa0")
                        if all(ch in cmap for ch in tok_clean_str):
                            w_cid = b"".join(cmap[ch] for ch in tok_clean_str)
                            if w_cid:
                                w_repl = (
                                    space_cid * len(tok_clean_str)
                                    if space_cid and len(space_cid) * len(tok_clean_str) == len(w_cid)
                                    else b"\x00" * len(w_cid)
                                )
                                word_cid_replacements.append((w_cid, w_repl))
            for ch in t_compact.lower():
                allowed_spatial_chars.add(ch.encode("latin1", errors="ignore"))

        # Track ISO 32000-1 graphics CTM and text matrices (Tm, Tlm)
        ctm = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
        ctm_stack: List[List[float]] = []
        tm = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
        tlm = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
        text_leading = 0.0
        in_text_obj = False

        def _current_page_pos() -> Tuple[float, float]:
            m = _mul_matrix(tm, ctm)
            return m[4], m[5]

        def _is_spatially_targeted(op_bytes: bytes, px: float, py: float) -> bool:
            if not target_boxes:
                return False
            in_box = False
            for b in target_boxes:
                if (b.x0 - 4.0) <= px <= (b.x1 + 4.0) and (b.y0 - 3.5) <= py <= (b.y1 + 3.5):
                    in_box = True
                    break
            if not in_box:
                return False

            # If there are no specific target_strings on this page (pure manual box), excise any text in box
            if not target_strings:
                return True

            stripped = op_bytes.strip()
            if not stripped:
                return False
            low = stripped.lower()

            # Check if operator text is a token, substring, or single-character comb cell of a target
            if low in allowed_spatial_tokens:
                return True
            low_clean = low.strip(b",.:;#-()_ ")
            if low_clean and low_clean in allowed_spatial_tokens:
                return True
            if len(low_clean) == 1 and low_clean in allowed_spatial_chars:
                return True
            for tb in targets_bytes:
                if low_clean and len(low_clean) >= 2 and low_clean in tb.lower():
                    return True
            return False

        for operands, operator in instructions:
            op_name = str(operator)

            if op_name == "q":
                ctm_stack.append(list(ctm))
            elif op_name == "Q":
                if ctm_stack:
                    ctm = ctm_stack.pop()
            elif op_name == "cm" and len(operands) == 6:
                try:
                    cm_mat = [float(x) for x in operands]
                    ctm = _mul_matrix(cm_mat, ctm)
                except Exception:
                    pass
            elif op_name == "BT":
                in_text_obj = True
                tm = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
                tlm = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
            elif op_name == "ET":
                in_text_obj = False
            elif op_name in ("Td", "TD") and len(operands) == 2:
                try:
                    tx_d, ty_d = float(operands[0]), float(operands[1])
                    if op_name == "TD":
                        text_leading = -ty_d
                    tlm = _mul_matrix([1.0, 0.0, 0.0, 1.0, tx_d, ty_d], tlm)
                    tm = list(tlm)
                except Exception:
                    pass
            elif op_name == "Tm" and len(operands) == 6:
                try:
                    tlm = [float(x) for x in operands]
                    tm = list(tlm)
                except Exception:
                    pass
            elif op_name == "TL" and len(operands) == 1:
                try:
                    text_leading = float(operands[0])
                except Exception:
                    pass
            elif op_name == "T*":
                tlm = _mul_matrix([1.0, 0.0, 0.0, 1.0, 0.0, -text_leading], tlm)
                tm = list(tlm)

            if op_name in ("Tj", "'", '"') and operands:
                str_idx = -1 if op_name == '"' else 0
                val = operands[str_idx]
                if isinstance(val, pikepdf.String):
                    raw_bytes = bytes(val)
                    cleaned_bytes, hit = self._clean_string_bytes(
                        raw_bytes, targets_bytes, cid_replacements
                    )
                    if not hit and in_text_obj:
                        px, py = _current_page_pos()
                        if _is_spatially_targeted(raw_bytes, px, py):
                            cleaned_bytes = b" " * len(raw_bytes)
                            hit = True
                        elif any((b.y0 - 4.5) <= py <= (b.y1 + 4.5) for b in target_boxes):
                            cleaned_bytes, hit = self._clean_string_bytes(
                                raw_bytes, word_targets_bytes, word_cid_replacements
                            )
                    if hit:
                        excised_hits += 1
                        new_ops = list(operands)
                        new_ops[str_idx] = pikepdf.String(cleaned_bytes)
                        new_instructions.append((new_ops, operator))
                        continue

            elif op_name == "TJ" and operands:
                arr = operands[0]
                if isinstance(arr, pikepdf.Array):
                    combined_bytes = b""
                    string_indices = []
                    for idx, item in enumerate(arr):
                        if isinstance(item, pikepdf.String):
                            b_item = bytes(item)
                            string_indices.append((idx, len(combined_bytes), len(b_item)))
                            combined_bytes += b_item

                    cleaned_combined, hit = self._clean_string_bytes(
                        combined_bytes, targets_bytes, cid_replacements
                    )
                    if not hit and in_text_obj:
                        px, py = _current_page_pos()
                        if _is_spatially_targeted(combined_bytes, px, py):
                            cleaned_combined = b" " * len(combined_bytes)
                            hit = True
                        elif any((b.y0 - 4.5) <= py <= (b.y1 + 4.5) for b in target_boxes):
                            cleaned_combined, hit = self._clean_string_bytes(
                                combined_bytes, word_targets_bytes, word_cid_replacements
                            )
                    if hit:
                        excised_hits += 1
                        new_arr = pikepdf.Array()
                        for idx, item in enumerate(arr):
                            if isinstance(item, pikepdf.String):
                                match_meta = next(
                                    (m for m in string_indices if m[0] == idx), None
                                )
                                if match_meta:
                                    _, start, length = match_meta
                                    segment = cleaned_combined[start : start + length]
                                    new_arr.append(pikepdf.String(segment))
                                else:
                                    new_arr.append(item)
                            else:
                                new_arr.append(item)
                        new_instructions.append(([new_arr], operator))
                        continue

            new_instructions.append((operands, operator))

        if excised_hits > 0:
            new_stream_bytes = pikepdf.unparse_content_stream(new_instructions)
            page.Contents = pdf.make_stream(new_stream_bytes)

        return excised_hits

    def _clean_string_bytes(
        self,
        raw_bytes: bytes,
        targets_bytes: List[bytes],
        cid_replacements: List[Tuple[bytes, bytes]] = (),
    ) -> Tuple[bytes, bool]:
        """
        Replace any occurrence of target bytes (case-insensitive) or ToUnicode CID byte sequences
        with spaces of equal length so adjacent non-redacted text preserves its layout offset.
        """
        modified = raw_bytes
        hit = False
        lower_mod = modified.lower()

        for tb in targets_bytes:
            if not tb:
                continue
            tb_lower = tb.lower()
            start = 0
            while True:
                idx = lower_mod.find(tb_lower, start)
                if idx == -1:
                    break
                replacement = b" " * len(tb)
                modified = modified[:idx] + replacement + modified[idx + len(tb) :]
                lower_mod = modified.lower()
                hit = True
                start = idx + len(tb)

        for enc_cid, repl_cid in cid_replacements:
            if not enc_cid:
                continue
            start = 0
            while True:
                idx = modified.find(enc_cid, start)
                if idx == -1:
                    break
                modified = (
                    modified[:idx] + repl_cid + modified[idx + len(enc_cid) :]
                )
                lower_mod = modified.lower()
                hit = True
                start = idx + len(enc_cid)

        return modified, hit

    def _burn_opaque_rectangles(
        self, pdf: pikepdf.Pdf, page: pikepdf.Page, boxes: List[BoundingBox]
    ) -> None:
        """Append PDF graphics instructions to draw solid black rectangles over excised regions."""
        commands = ["q", "0 0 0 rg", "0 0 0 RG"]
        for box in boxes:
            # Pad slightly to ensure full visual coverage of ascenders/descenders
            x = max(0.0, box.x0 - 1.0)
            y = max(0.0, box.y0 - 1.0)
            w = max(4.0, (box.x1 - box.x0) + 2.0)
            h = max(4.0, (box.y1 - box.y0) + 2.0)
            commands.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re f")
        commands.append("Q")

        overlay_bytes = ("\n".join(commands) + "\n").encode("ascii")
        page.contents_add(pdf.make_stream(overlay_bytes), prepend=False)

    def _eradicate_metadata(self, pdf: pikepdf.Pdf) -> None:
        """Delete all Document Info keys and XMP Metadata streams."""
        if "/Metadata" in pdf.Root:
            del pdf.Root["/Metadata"]

        if pdf.docinfo:
            keys = list(pdf.docinfo.keys())
            for k in keys:
                try:
                    del pdf.docinfo[k]
                except Exception:
                    pass
