"""Surgical PDF stream sanitization engine powered by PikePDF and QPDF."""

from pathlib import Path
from typing import List, Tuple
import pikepdf
from pikepdf import Array, Dictionary, Name, Operator, String

from redact_gov.core.models import BoundingBox, RedactionEntity


class PikePdfSanitizer:
    """Performs true low-level PDF stream surgery: glyph excision, canvas burn-in, and metadata wipe."""

    def sanitize_document(
        self,
        input_pdf: Path,
        output_pdf: Path,
        entities: List[RedactionEntity],
        eradicate_metadata: bool = True,
    ) -> Tuple[bool, int]:
        """Perform surgical sanitization on the PDF."""
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        applied_count = 0

        # Group entities by page number (1-based)
        entities_by_page = {}
        for entity in entities:
            if not entity.approved:
                continue
            entities_by_page.setdefault(entity.page_number, []).append(entity)

        with pikepdf.open(input_pdf) as pdf:
            # 1. Process each page
            for page_idx, page in enumerate(pdf.pages, start=1):
                page_entities = entities_by_page.get(page_idx, [])
                if not page_entities:
                    continue

                # Collect all target strings including sub-lines
                target_strings = []
                for e in page_entities:
                    txt = e.text.strip()
                    if txt:
                        target_strings.append(txt)
                        if "\n" in txt:
                            for sub in txt.splitlines():
                                if len(sub.strip()) > 1:
                                    target_strings.append(sub.strip())

                # Collect all bounding boxes to burn in
                all_boxes: List[BoundingBox] = []
                for e in page_entities:
                    all_boxes.extend(e.bounding_boxes)

                # Step A: Excise glyph operators in content stream
                self._excise_text_glyphs(pdf, page, target_strings)

                # Step B: Burn opaque black vector polygons directly into canvas
                if all_boxes:
                    self._burn_vector_rectangles(pdf, page, all_boxes)
                    applied_count += len(all_boxes)
                else:
                    applied_count += len(target_strings)

                # Step C: Strip annotations on this page that might leak text
                if "/Annots" in page:
                    del page["/Annots"]

            # 2. Eradicate metadata across the document
            if eradicate_metadata:
                self._wipe_metadata(pdf)

            # 3. Save with linearize/clean options
            pdf.save(
                output_pdf,
                linearize=False,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
            )

        return True, applied_count

    def _excise_text_glyphs(
        self, pdf: pikepdf.Pdf, page: pikepdf.Page, target_strings: List[str]
    ) -> None:
        """Parse page content stream instructions and replace target text glyphs."""
        if not target_strings:
            return

        try:
            instructions = pikepdf.parse_content_stream(page)
        except Exception:
            return

        modified = False
        new_instructions = []

        for operands, operator in instructions:
            op_name = str(operator)

            # Tj operator: show text string
            if op_name == "Tj" and operands:
                operand = operands[0]
                text_content = self._decode_pdf_string(operand)
                scrubbed_text, changed = self._scrub_string(text_content, target_strings)
                if changed:
                    operands[0] = String(scrubbed_text.encode("latin1", errors="replace"))
                    modified = True

            # TJ operator: show array of text strings and spacing glyphs
            elif op_name == "TJ" and operands:
                array_operand = operands[0]
                if isinstance(array_operand, (list, Array)):
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
                        operands[0] = Array(new_array)
                        modified = True

            # ' and " operators: move to next line and show text
            elif op_name in ("'", '"') and operands:
                text_content = self._decode_pdf_string(operands[-1])
                scrubbed_text, changed = self._scrub_string(text_content, target_strings)
                if changed:
                    operands[-1] = String(scrubbed_text.encode("latin1", errors="replace"))
                    modified = True

            new_instructions.append((operands, operator))

        if modified:
            new_stream_bytes = pikepdf.unparse_content_stream(new_instructions)
            page.Contents = pdf.make_stream(new_stream_bytes)

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
