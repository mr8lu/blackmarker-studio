"""Document normalization and repair engine for imperfect government PDFs.

Recovers damaged PDF structures, repairs malformed or missing font descriptors
(e.g., FontBBox=None, missing Ascent/Descent), and suppresses benign parser warnings.
"""

from dataclasses import dataclass, field
import logging
from pathlib import Path
import tempfile
from typing import List, Optional, Set, Tuple
import pikepdf


def silence_parser_warnings() -> None:
    """Suppress noisy, benign warnings from pdfminer and pikepdf when processing non-clean documents."""
    logging.getLogger("pdfminer").setLevel(logging.ERROR)
    logging.getLogger("pikepdf").setLevel(logging.ERROR)


@dataclass
class InspectionReport:
    """Diagnostic report detailing anomalies detected and repaired in an imperfect PDF."""
    is_imperfect: bool = False
    issues: List[str] = field(default_factory=list)
    repaired_fonts_count: int = 0
    total_pages: int = 0


class DocumentNormalizer:
    """Inspects, standardizes, and repairs imperfect or damaged PDFs using PikePDF/QPDF."""

    # Standard typographic fallback bounding box for 1000-unit glyph coordinate systems
    DEFAULT_FONT_BBOX = [-200, -250, 1000, 850]
    DEFAULT_ASCENT = 750
    DEFAULT_DESCENT = -250
    DEFAULT_CAP_HEIGHT = 700

    def __init__(self) -> None:
        silence_parser_warnings()

    def inspect_document(self, pdf_path: Path) -> InspectionReport:
        """Analyze a PDF document to identify imperfections and font descriptor anomalies."""
        report = InspectionReport()
        if not pdf_path.is_file():
            report.is_imperfect = True
            report.issues.append(f"File not found: {pdf_path}")
            return report

        try:
            with pikepdf.open(pdf_path, attempt_recovery=True, suppress_warnings=True) as pdf:
                report.total_pages = len(pdf.pages)

                # Inspect font descriptors across all pages
                for page_idx, page in enumerate(pdf.pages, start=1):
                    res = page.get("/Resources")
                    if not res:
                        continue

                    # Page-level fonts
                    fonts = res.get("/Font")
                    if isinstance(fonts, pikepdf.Dictionary):
                        for font_name, font_obj in fonts.items():
                            self._inspect_font(font_name, font_obj, page_idx, report)

                    # Form XObject fonts
                    xobjects = res.get("/XObject")
                    if isinstance(xobjects, pikepdf.Dictionary):
                        for xname, xobj in xobjects.items():
                            if isinstance(xobj, pikepdf.Stream) and xobj.get("/Subtype") == pikepdf.Name("/Form"):
                                xres = xobj.get("/Resources")
                                if isinstance(xres, pikepdf.Dictionary):
                                    xfonts = xres.get("/Font")
                                    if isinstance(xfonts, pikepdf.Dictionary):
                                        for font_name, font_obj in xfonts.items():
                                            self._inspect_font(f"{xname}:{font_name}", font_obj, page_idx, report)

        except Exception as exc:
            report.is_imperfect = True
            report.issues.append(f"PDF structural or stream error: {exc}")

        if report.issues:
            report.is_imperfect = True

        return report

    def normalize_pdf(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
    ) -> Tuple[Path, InspectionReport]:
        """Repair and normalize an imperfect PDF document.
        
        If output_path is not specified, a temporary normalized file is created.
        Returns the path to the normalized PDF and the inspection/repair report.
        """
        silence_parser_warnings()

        if output_path is None:
            tmp = tempfile.NamedTemporaryFile(suffix=".normalized.pdf", delete=False)
            output_path = Path(tmp.name)
            tmp.close()

        report = InspectionReport()

        with pikepdf.open(input_path, attempt_recovery=True, suppress_warnings=True) as pdf:
            report.total_pages = len(pdf.pages)
            repaired_count = self.repair_font_descriptors(pdf, report)
            report.repaired_fonts_count = repaired_count
            if report.issues:
                report.is_imperfect = True

            # Save normalized PDF with regenerated object streams and standardized xrefs
            pdf.save(
                output_path,
                linearize=False,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
            )

        return output_path, report

    def repair_font_descriptors(
        self,
        pdf: pikepdf.Pdf,
        report: Optional[InspectionReport] = None,
    ) -> int:
        """Traverse all font resources and heal missing or invalid FontBBox and metric entries."""
        repaired_total = 0
        seen_fonts: Set[int] = set()

        def heal_font(font_dict: any, context: str) -> None:
            nonlocal repaired_total
            if not isinstance(font_dict, pikepdf.Dictionary):
                return

            font_id = id(font_dict)
            if font_id in seen_fonts:
                return
            seen_fonts.add(font_id)

            # Check if FontDescriptor exists
            fd = font_dict.get("/FontDescriptor")

            # Check if this font is a composite Type0 font with DescendantFonts
            descendants = font_dict.get("/DescendantFonts")
            if isinstance(descendants, pikepdf.Array):
                for df in descendants:
                    heal_font(df, f"{context}->DescendantFont")

            # If no FontDescriptor exists on a font requiring one, synthesize one
            if fd is None:
                subtype = font_dict.get("/Subtype")
                # Type1, TrueType, and CID fonts benefit from having FontDescriptor
                if subtype in (pikepdf.Name("/TrueType"), pikepdf.Name("/Type1"), pikepdf.Name("/CIDFontType0"), pikepdf.Name("/CIDFontType2")):
                    base_font = font_dict.get("/BaseFont", pikepdf.Name("/SynthesizedFont"))
                    fd = pdf.make_indirect(
                        pikepdf.Dictionary(
                            Type=pikepdf.Name("/FontDescriptor"),
                            FontName=base_font,
                            FontBBox=pikepdf.Array(self.DEFAULT_FONT_BBOX),
                            Ascent=self.DEFAULT_ASCENT,
                            Descent=self.DEFAULT_DESCENT,
                            CapHeight=self.DEFAULT_CAP_HEIGHT,
                        )
                    )
                    font_dict["/FontDescriptor"] = fd
                    repaired_total += 1
                    if report:
                        report.issues.append(f"{context}: Synthesized missing /FontDescriptor")
                    return

            if isinstance(fd, pikepdf.Dictionary):
                font_repaired = False

                # 1. Validate /FontBBox
                fbbox = fd.get("/FontBBox")
                needs_bbox_repair = False

                if fbbox is None:
                    needs_bbox_repair = True
                elif not isinstance(fbbox, (pikepdf.Array, list)) or len(fbbox) != 4:
                    needs_bbox_repair = True
                else:
                    try:
                        floats = [float(x) for x in fbbox]
                        # If bounding box is degenerate (0 area), consider repairing
                        if floats[0] == floats[2] and floats[1] == floats[3]:
                            needs_bbox_repair = True
                    except (ValueError, TypeError):
                        needs_bbox_repair = True

                if needs_bbox_repair:
                    fd["/FontBBox"] = pikepdf.Array(self.DEFAULT_FONT_BBOX)
                    font_repaired = True
                    if report:
                        report.issues.append(f"{context}: Repaired invalid or missing /FontBBox")

                # 2. Validate /Ascent
                ascent = fd.get("/Ascent")
                if ascent is None:
                    fd["/Ascent"] = self.DEFAULT_ASCENT
                    font_repaired = True
                    if report:
                        report.issues.append(f"{context}: Added default /Ascent metric")

                # 3. Validate /Descent
                descent = fd.get("/Descent")
                if descent is None:
                    fd["/Descent"] = self.DEFAULT_DESCENT
                    font_repaired = True
                    if report:
                        report.issues.append(f"{context}: Added default /Descent metric")

                if font_repaired:
                    repaired_total += 1

        # Traverse all pages
        for page_idx, page in enumerate(pdf.pages, start=1):
            res = page.get("/Resources")
            if not res:
                continue

            fonts = res.get("/Font")
            if isinstance(fonts, pikepdf.Dictionary):
                for font_name, font_obj in fonts.items():
                    heal_font(font_obj, f"Page {page_idx} Font {font_name}")

            xobjects = res.get("/XObject")
            if isinstance(xobjects, pikepdf.Dictionary):
                for xname, xobj in xobjects.items():
                    if isinstance(xobj, pikepdf.Stream) and xobj.get("/Subtype") == pikepdf.Name("/Form"):
                        xres = xobj.get("/Resources")
                        if isinstance(xres, pikepdf.Dictionary):
                            xfonts = xres.get("/Font")
                            if isinstance(xfonts, pikepdf.Dictionary):
                                for font_name, font_obj in xfonts.items():
                                    heal_font(font_obj, f"Page {page_idx} XObject {xname} Font {font_name}")

        return repaired_total

    def _inspect_font(
        self, font_name: str, font_obj: any, page_idx: int, report: InspectionReport
    ) -> None:
        """Check an individual font dictionary for known anomalies."""
        if not isinstance(font_obj, pikepdf.Dictionary):
            return

        fd = font_obj.get("/FontDescriptor")
        descendants = font_obj.get("/DescendantFonts")
        if isinstance(descendants, pikepdf.Array):
            for idx, df in enumerate(descendants):
                self._inspect_font(f"{font_name}[CID {idx}]", df, page_idx, report)

        if fd is None:
            subtype = font_obj.get("/Subtype")
            if subtype in (pikepdf.Name("/TrueType"), pikepdf.Name("/Type1")):
                report.issues.append(f"Page {page_idx} ({font_name}): Missing /FontDescriptor dictionary")
            return

        if isinstance(fd, pikepdf.Dictionary):
            fbbox = fd.get("/FontBBox")
            if fbbox is None:
                report.issues.append(
                    f"Page {page_idx} ({font_name}): /FontBBox is None or missing (causes pdfminer 4-float parse warning)"
                )
            elif not isinstance(fbbox, (pikepdf.Array, list)) or len(fbbox) != 4:
                report.issues.append(
                    f"Page {page_idx} ({font_name}): /FontBBox has invalid format ({fbbox})"
                )
            else:
                try:
                    [float(x) for x in fbbox]
                except (ValueError, TypeError):
                    report.issues.append(
                        f"Page {page_idx} ({font_name}): /FontBBox elements cannot be parsed as floats"
                    )

            if fd.get("/Ascent") is None:
                report.issues.append(f"Page {page_idx} ({font_name}): /Ascent metric is missing")
            if fd.get("/Descent") is None:
                report.issues.append(f"Page {page_idx} ({font_name}): /Descent metric is missing")
