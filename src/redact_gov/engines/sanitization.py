"""Surgical PDF stream sanitization engine powered by PikePDF and QPDF."""

from pathlib import Path
import re
from typing import List, Tuple
import pikepdf
from pikepdf import Array, Dictionary, Name, Operator, String

from redact_gov.core.models import BoundingBox, RedactionEntity
from redact_gov.core.normalizer import DocumentNormalizer, silence_parser_warnings


class PikePdfSanitizer:
    """Performs true low-level PDF stream surgery: glyph excision, canvas burn-in, and metadata wipe."""

    def __init__(self) -> None:
        silence_parser_warnings()
        self.normalizer = DocumentNormalizer()

    def sanitize_document(
        self,
        input_pdf: Path,
        output_pdf: Path,
        entities: List[RedactionEntity],
        eradicate_metadata: bool = True,
        repair_imperfect: bool = True,
    ) -> Tuple[bool, int]:
        """Perform surgical sanitization on the PDF."""
        silence_parser_warnings()
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        applied_count = 0

        # Group entities by page number (1-based)
        entities_by_page = {}
        for entity in entities:
            if not entity.approved:
                continue
            entities_by_page.setdefault(entity.page_number, []).append(entity)

        with pikepdf.open(input_pdf, attempt_recovery=True, suppress_warnings=True) as pdf:
            # 0. Heal font descriptors & structures if handling imperfect document
            if repair_imperfect:
                self.normalizer.repair_font_descriptors(pdf)

            # 1. Process each page
            for page_idx, page in enumerate(pdf.pages, start=1):
                page_entities = entities_by_page.get(page_idx, [])
                if not page_entities:
                    continue

                # Collect all target strings including sub-lines and coordinate numbers
                target_strings = []
                for e in page_entities:
                    txt = e.text.strip()
                    if txt and not txt.startswith("[Manual"):
                        target_strings.append(txt)
                        if "\n" in txt:
                            for sub in txt.splitlines():
                                if len(sub.strip()) > 1:
                                    target_strings.append(sub.strip())
                        if e.category == "manual_redaction" or e.tier == "manual_blackmarker":
                            for word in txt.split():
                                w_clean = word.strip()
                                if len(w_clean) >= 2 and w_clean not in target_strings:
                                    target_strings.append(w_clean)
                        # Extract numeric coordinates if present (e.g. 37.339070 from 37.339070° LAT.)
                        for num in re.findall(r"\b\d{1,3}\.\d{4,8}\b", txt):
                            if num not in target_strings:
                                target_strings.append(num)
                        # Extract 7-digit local phone if present (e.g. 847-7796 from (434)847-7796)
                        phone_m = re.search(r"\b\d{3}[-.]\d{4}\b", txt)
                        if phone_m and phone_m.group(0) not in target_strings:
                            target_strings.append(phone_m.group(0))

                # Collect all bounding boxes to burn in
                all_boxes: List[BoundingBox] = []
                for e in page_entities:
                    all_boxes.extend(e.bounding_boxes)

                # Step A: Scrub any AcroForm widget annotations on this page
                if "/Annots" in page:
                    for annot in page.Annots:
                        if annot.get("/Subtype") == pikepdf.Name("/Widget"):
                            val = str(annot.get("/V", ""))
                            rect = annot.get("/Rect")
                            is_targeted = False
                            for target in target_strings:
                                if target and (target in val or val in target):
                                    is_targeted = True
                                    break
                            if not is_targeted and rect and len(rect) == 4:
                                rx0, ry0, rx1, ry1 = (
                                    float(rect[0]),
                                    float(rect[1]),
                                    float(rect[2]),
                                    float(rect[3]),
                                )
                                for b in all_boxes:
                                    if not (rx1 < b.x0 or rx0 > b.x1 or ry1 < b.y0 or ry0 > b.y1):
                                        is_targeted = True
                                        break
                            if is_targeted:
                                annot["/V"] = String(b"[REDACTED]")
                                if "/DV" in annot:
                                    annot["/DV"] = String(b"[REDACTED]")
                                if "/AP" in annot:
                                    del annot["/AP"]
                                if rect and len(rect) == 4:
                                    w_box = BoundingBox(
                                        page=page_idx,
                                        x0=round(float(rect[0]), 2),
                                        y0=round(float(rect[1]), 2),
                                        x1=round(float(rect[2]), 2),
                                        y1=round(float(rect[3]), 2),
                                    )
                                    if w_box not in all_boxes:
                                        all_boxes.append(w_box)

                # Step B: Excise glyph operators in content stream (supporting CID and standard fonts)
                self._excise_text_glyphs(pdf, page, target_strings)

                # Step C: Burn opaque black vector polygons directly into canvas
                if all_boxes:
                    self._burn_vector_rectangles(pdf, page, all_boxes)
                    applied_count += len(all_boxes)
                else:
                    applied_count += len(target_strings)

                # Step D: Strip non-widget annotations that might leak text
                if "/Annots" in page:
                    widget_annots = [
                        a for a in page.Annots if a.get("/Subtype") == pikepdf.Name("/Widget")
                    ]
                    if widget_annots:
                        page.Annots = Array(widget_annots)
                    else:
                        del page["/Annots"]

            # 2. Scrub root AcroForm field values if present
            if "/AcroForm" in pdf.Root and "/Fields" in pdf.Root.AcroForm:
                for field in pdf.Root.AcroForm.Fields:
                    val = str(field.get("/V", ""))
                    for entity in entities:
                        if entity.text and (entity.text in val or (len(val) > 2 and val in entity.text)):
                            field["/V"] = String(b"[REDACTED]")
                            if "/DV" in field:
                                field["/DV"] = String(b"[REDACTED]")
                            if "/AP" in field:
                                del field["/AP"]
                            break

            # 3. Eradicate metadata across the document
            if eradicate_metadata:
                self._wipe_metadata(pdf)

            # 4. Save with linearize/clean options
            pdf.save(
                output_pdf,
                linearize=False,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
            )

        return True, applied_count

    def _parse_tounicode_cmap(self, stream_bytes: bytes) -> Tuple[dict, int]:
        """Parse a /ToUnicode CMap stream into a cid->char mapping and space cid."""
        bfchar = {}
        space_cid = None
        try:
            text = stream_bytes.decode("latin1", errors="ignore")
            for line in text.splitlines():
                tokens = re.findall(r"<([0-9a-fA-F]+)>", line)
                if len(tokens) == 2:
                    src = int(tokens[0], 16)
                    dst = chr(int(tokens[1], 16))
                    bfchar[src] = dst
                    if dst == " ":
                        space_cid = src
                elif len(tokens) >= 3:
                    start = int(tokens[0], 16)
                    end = int(tokens[1], 16)
                    dst_start = int(tokens[2], 16)
                    for i in range(end - start + 1):
                        ch = chr(dst_start + i)
                        bfchar[start + i] = ch
                        if ch == " ":
                            space_cid = start + i
        except Exception:
            pass
        if space_cid is None:
            space_cid = 0x0003 if 0x0003 in bfchar else 0x0020
        return bfchar, space_cid

    def _build_font_decoders(self, res: any) -> dict:
        """Build dictionary of font decoders from resources dictionary."""
        decoders = {}
        if not res or not isinstance(res, pikepdf.Dictionary) or "/Font" not in res:
            return decoders

        for alias, font_obj in res["/Font"].items():
            if isinstance(font_obj, pikepdf.Dictionary) and "/ToUnicode" in font_obj:
                tu = font_obj["/ToUnicode"]
                if isinstance(tu, pikepdf.Stream):
                    bfchar, space_cid = self._parse_tounicode_cmap(tu.read_bytes())
                    subtype = str(font_obj.get("/Subtype", ""))
                    encoding = str(font_obj.get("/Encoding", ""))
                    is_two_byte = subtype == "/Type0" or "Identity" in encoding
                    if not is_two_byte and (space_cid is None or space_cid > 255):
                        space_cid = 0x20
                    decoders[str(alias)] = (bfchar, space_cid, is_two_byte)
        return decoders

    def _scrub_cid_bytes(
        self,
        raw: bytes,
        bfchar: dict,
        space_cid: int,
        is_two_byte: bool,
        target_strings: List[str],
    ) -> Tuple[bytes, bool]:
        """Scrub target strings from CID encoded byte sequence."""
        if is_two_byte:
            n = len(raw) // 2
            cids = [int.from_bytes(raw[i * 2 : (i + 1) * 2], "big") for i in range(n)]
            decoded = "".join(bfchar.get(cid, "?") for cid in cids)
        else:
            cids = list(raw)
            decoded = "".join(bfchar.get(cid, chr(cid)) for cid in cids)

        modified = False
        new_cids = list(cids)

        for target in target_strings:
            if not target:
                continue
            start = 0
            while True:
                idx = decoded.find(target, start)
                if idx == -1:
                    break
                for pos in range(idx, min(len(new_cids), idx + len(target))):
                    new_cids[pos] = space_cid
                modified = True
                start = idx + len(target)

        if modified:
            if is_two_byte:
                new_bytes = b"".join(cid.to_bytes(2, "big") for cid in new_cids)
            else:
                new_bytes = bytes(new_cids)
            return new_bytes, True
        return raw, False

    def _scrub_tj_array(
        self,
        array_operand: any,
        bfchar: dict,
        space_cid: int,
        is_two_byte: bool,
        target_strings: List[str],
    ) -> Tuple[list, bool]:
        """Scrub target strings across composite TJ array elements (accounting for kernings)."""
        char_map = []
        decoded_chars = []

        for item_idx, item in enumerate(array_operand):
            if isinstance(item, (pikepdf.String, bytes)):
                raw = bytes(item)
                if is_two_byte:
                    for b_off in range(0, len(raw), 2):
                        cid = int.from_bytes(raw[b_off : b_off + 2], "big")
                        decoded_chars.append(bfchar.get(cid, "?"))
                        char_map.append((item_idx, b_off, 2))
                else:
                    for b_off in range(len(raw)):
                        cid = raw[b_off]
                        decoded_chars.append(bfchar.get(cid, chr(cid)))
                        char_map.append((item_idx, b_off, 1))

        full_text = "".join(decoded_chars)
        modified = False

        replacements = {}
        for target in target_strings:
            if not target:
                continue
            start = 0
            while True:
                idx = full_text.find(target, start)
                if idx == -1:
                    break
                for pos in range(idx, min(len(char_map), idx + len(target))):
                    item_idx, b_off, b_len = char_map[pos]
                    if item_idx not in replacements:
                        replacements[item_idx] = bytearray(bytes(array_operand[item_idx]))
                    if b_len == 2:
                        replacements[item_idx][b_off : b_off + 2] = space_cid.to_bytes(2, "big")
                    else:
                        replacements[item_idx][b_off] = space_cid
                    modified = True
                start = idx + len(target)

        if modified:
            new_array = list(array_operand)
            for item_idx, new_bytes in replacements.items():
                new_array[item_idx] = String(bytes(new_bytes))
            return new_array, True
        return list(array_operand), False

    def _excise_stream_instructions(
        self,
        pdf: pikepdf.Pdf,
        stream_owner: any,
        resources: any,
        target_strings: List[str],
    ) -> bool:
        """Excise target strings from a single content stream (page or Form XObject)."""
        if not target_strings:
            return False

        try:
            instructions = pikepdf.parse_content_stream(stream_owner)
        except Exception:
            return False

        font_decoders = self._build_font_decoders(resources)
        active_font = None
        font_stack = []
        modified = False
        new_instructions = []

        for operands, operator in instructions:
            op_name = str(operator)

            if op_name == "q":
                font_stack.append(active_font)
                new_instructions.append((operands, operator))
                continue
            elif op_name == "Q":
                if font_stack:
                    active_font = font_stack.pop()
                new_instructions.append((operands, operator))
                continue
            elif op_name == "Tf" and operands:
                active_font = str(operands[0])
                new_instructions.append((operands, operator))
                continue

            # Tj operator: show text string
            elif op_name in ("Tj", "'", '"') and operands:
                target_operand = operands[0] if op_name == "Tj" else operands[-1]
                raw_bytes = bytes(target_operand)

                if active_font and active_font in font_decoders:
                    bfchar, space_cid, is_two_byte = font_decoders[active_font]
                    scrubbed_bytes, changed = self._scrub_cid_bytes(
                        raw_bytes, bfchar, space_cid, is_two_byte, target_strings
                    )
                    if changed:
                        new_ops = list(operands)
                        if op_name == "Tj":
                            new_ops[0] = String(scrubbed_bytes)
                        else:
                            new_ops[-1] = String(scrubbed_bytes)
                        new_instructions.append((new_ops, operator))
                        modified = True
                        continue
                else:
                    text_content = self._decode_pdf_string(target_operand)
                    scrubbed_text, changed = self._scrub_string(text_content, target_strings)
                    if changed:
                        new_ops = list(operands)
                        if op_name == "Tj":
                            new_ops[0] = String(scrubbed_text.encode("latin1", errors="replace"))
                        else:
                            new_ops[-1] = String(scrubbed_text.encode("latin1", errors="replace"))
                        new_instructions.append((new_ops, operator))
                        modified = True
                        continue

            # TJ operator: show array of text strings and spacing glyphs
            elif op_name == "TJ" and operands:
                array_operand = operands[0]
                if isinstance(array_operand, (list, Array)):
                    if active_font and active_font in font_decoders:
                        bfchar, space_cid, is_two_byte = font_decoders[active_font]
                        scrubbed_array, changed = self._scrub_tj_array(
                            array_operand, bfchar, space_cid, is_two_byte, target_strings
                        )
                        if changed:
                            new_instructions.append(([Array(scrubbed_array)], operator))
                            modified = True
                            continue
                    else:
                        new_array = []
                        array_changed = False
                        for item in array_operand:
                            if isinstance(item, (pikepdf.String, bytes)):
                                text_content = self._decode_pdf_string(item)
                                scrubbed_text, changed = self._scrub_string(text_content, target_strings)
                                if changed:
                                    new_array.append(String(scrubbed_text.encode("latin1", errors="replace")))
                                    array_changed = True
                                else:
                                    new_array.append(item)
                            else:
                                new_array.append(item)
                        if array_changed:
                            new_instructions.append(([Array(new_array)], operator))
                            modified = True
                            continue

            new_instructions.append((operands, operator))

        if modified:
            new_stream_bytes = pikepdf.unparse_content_stream(new_instructions)
            if isinstance(stream_owner, pikepdf.Page):
                stream_owner.Contents = pdf.make_stream(new_stream_bytes)
            elif hasattr(stream_owner, "write"):
                stream_owner.write(new_stream_bytes)
        return modified

    def _excise_text_glyphs(
        self, pdf: pikepdf.Pdf, page: pikepdf.Page, target_strings: List[str]
    ) -> None:
        """Parse page content stream instructions and any Form XObjects, replacing target text glyphs."""
        if not target_strings:
            return

        page_res = page.get("/Resources", {})
        self._excise_stream_instructions(pdf, page, page_res, target_strings)

        # Also excise Form XObjects referenced on this page
        xobjects = page_res.get("/XObject", {})
        if isinstance(xobjects, pikepdf.Dictionary):
            for _, x_obj in xobjects.items():
                if isinstance(x_obj, pikepdf.Stream) and x_obj.get("/Subtype") == pikepdf.Name("/Form"):
                    x_res = x_obj.get("/Resources") or page_res
                    self._excise_stream_instructions(pdf, x_obj, x_res, target_strings)

    def _burn_vector_rectangles(
        self, pdf: pikepdf.Pdf, page: pikepdf.Page, boxes: List[BoundingBox]
    ) -> None:
        """Append opaque black vector rectangles directly to page content stream."""
        if not boxes:
            return

        stream_commands = ["q", "0 0 0 rg"]
        for box in boxes:
            x = box.x0
            y = box.y0
            w = box.width
            h = box.height
            # Add 1.5pt padding for complete visual glyph coverage
            stream_commands.append(f"{x - 1.5:.2f} {y - 1.5:.2f} {w + 3.0:.2f} {h + 3.0:.2f} re")
        stream_commands.extend(["f", "Q"])
        stream_bytes = " ".join(stream_commands).encode("ascii")

        burn_stream = pdf.make_stream(stream_bytes)

        if isinstance(page.Contents, Array):
            page.Contents.append(burn_stream)
        elif page.Contents is not None:
            page.Contents = Array([page.Contents, burn_stream])
        else:
            page.Contents = burn_stream

    def _wipe_metadata(self, pdf: pikepdf.Pdf) -> None:
        """Strip XMP metadata streams, DocInfo dictionary, PieceInfo, and private trees."""
        if hasattr(pdf, "docinfo") and pdf.docinfo is not None:
            for key in list(pdf.docinfo.keys()):
                del pdf.docinfo[key]

        if "/Metadata" in pdf.Root:
            del pdf.Root["/Metadata"]

        if "/PieceInfo" in pdf.Root:
            del pdf.Root["/PieceInfo"]

        if "/StructTreeRoot" in pdf.Root:
            del pdf.Root["/StructTreeRoot"]

    def _decode_pdf_string(self, item: any) -> str:
        """Safely decode a PDF string operand to unicode."""
        if isinstance(item, pikepdf.String):
            return str(item)
        if isinstance(item, bytes):
            return item.decode("latin1", errors="ignore")
        return str(item)

    def _scrub_string(self, text: str, target_strings: List[str]) -> Tuple[str, bool]:
        """Replace target string occurrences within text with spaces to excise glyphs."""
        changed = False
        result = text
        for target in target_strings:
            if not target:
                continue
            if target in result:
                result = result.replace(target, " " * len(target))
                changed = True
            if "\n" in target:
                for sub in target.splitlines():
                    sub_s = sub.strip()
                    if len(sub_s) > 1 and sub_s in result:
                        result = result.replace(sub_s, " " * len(sub_s))
                        changed = True
        return result, changed
