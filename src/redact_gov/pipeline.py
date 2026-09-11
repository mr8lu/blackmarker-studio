"""Complete sovereign redaction pipeline integrating extraction, spatial alignment, and stream sanitization."""

from pathlib import Path
import time
from typing import List, Optional
import pdfplumber
import pikepdf

from redact_gov.certificates.generator import CertificateGenerator
from redact_gov.core.context_assessor import ContextAssessor
from redact_gov.core.criteria import (
    CoordinatePolicy,
    RedactionCriteriaRegistry,
    ReleaseProfile,
)
from redact_gov.core.geometry import find_text_bounding_boxes, get_document_page_count
from redact_gov.core.models import BoundingBox, RedactionEntity, RedactionPlan, RedactionResult
from redact_gov.core.normalizer import DocumentNormalizer, silence_parser_warnings
from redact_gov.engines.contextual import ContextualGemmaEngine
from redact_gov.engines.deterministic import DeterministicRedactionEngine
from redact_gov.engines.sanitization import PikePdfSanitizer


class RedactionPipeline:
    """Orchestrates hybrid on-device extraction and PikePDF surgical stream scrubbing."""

    def __init__(
        self,
        gemma_model_path: Optional[Path] = None,
        profile: ReleaseProfile = ReleaseProfile.PUBLIC_FOIA,
        coordinate_policy: str = "all",
        assess_form_context: bool = True,
        criteria_registry: Optional[RedactionCriteriaRegistry] = None,
    ):
        silence_parser_warnings()
        self.deterministic_engine = DeterministicRedactionEngine()
        self.contextual_engine = ContextualGemmaEngine(model_path=gemma_model_path)
        
        self.criteria_registry = criteria_registry or RedactionCriteriaRegistry(profile=profile)
        if coordinate_policy:
            self.criteria_registry.set_coordinate_policy(coordinate_policy)
        self.criteria_registry.set_assess_form_context(assess_form_context)

        self.context_assessor = ContextAssessor(registry=self.criteria_registry)
        self.sanitizer = PikePdfSanitizer()
        self.certificate_generator = CertificateGenerator()
        self.normalizer = DocumentNormalizer()
        self.assess_form_context = assess_form_context

    def create_plan(
        self,
        input_pdf: Path,
        normalize_imperfect: bool = True,
        coordinate_policy: Optional[str] = None,
        profile: Optional[ReleaseProfile] = None,
    ) -> RedactionPlan:
        """Analyze PDF across all pages and generate a complete RedactionPlan with geometry.

        When normalize_imperfect=True, automatically heals font descriptors (such as missing
        FontBBox or Ascent/Descent) and damaged stream structures before running analysis.
        """
        silence_parser_warnings()
        if profile or coordinate_policy:
            assessor_registry = RedactionCriteriaRegistry(profile=profile or self.criteria_registry.active_profile.profile)
            if coordinate_policy:
                assessor_registry.set_coordinate_policy(coordinate_policy)
            assessor = ContextAssessor(registry=assessor_registry)
        else:
            assessor = self.context_assessor

        # Step 0: Check and pre-normalize imperfect document if needed
        analysis_pdf = input_pdf
        tmp_normalized: Optional[Path] = None

        if normalize_imperfect:
            report = self.normalizer.inspect_document(input_pdf)
            if report.is_imperfect:
                tmp_normalized, _ = self.normalizer.normalize_pdf(input_pdf)
                analysis_pdf = tmp_normalized

        try:
            total_pages = get_document_page_count(analysis_pdf)
            all_entities: List[RedactionEntity] = []

            with (
                pdfplumber.open(analysis_pdf) as pdf,
                pikepdf.open(analysis_pdf, attempt_recovery=True) as pike_doc,
            ):
                for page_idx, page in enumerate(pdf.pages, start=1):
                    page_text = page.extract_text(layout=False) or ""

                    # 1. Tier 1 Deterministic Fast Path on content stream
                    raw_tier1 = (
                        self.deterministic_engine.scan_text(page_text, page_number=page_idx)
                        if page_text.strip()
                        else []
                    )
                    tier1_entities: List[RedactionEntity] = []
                    for e in raw_tier1:
                        if e.category == "gps_coordinate":
                            # Extract surrounding context window (150 chars before and after)
                            idx = page_text.find(e.text)
                            start_ctx = max(0, idx - 150) if idx != -1 else 0
                            end_ctx = min(len(page_text), idx + len(e.text) + 150) if idx != -1 else len(page_text)
                            surrounding = page_text[start_ctx:end_ctx]
                            c_type, statute, conf, should_redact = assessor.assess_coordinate_context(
                                coord_text=e.text,
                                surrounding_text=surrounding,
                            )
                            if not should_redact:
                                continue
                            c_name = c_type.value if hasattr(c_type, "value") else str(c_type)
                            e.statute_code = statute
                            e.category = f"gps_{c_name}"
                            e.context_label = f"Text Context: {c_name}"
                        tier1_entities.append(e)

                    # 2. Tier 2 Contextual Cognitive Path (Google Gemma 4 E4B)
                    tier2_entities = (
                        self.contextual_engine.analyze_text(page_text, page_number=page_idx)
                        if page_text.strip()
                        else []
                    )

                    # 3. Form-filled AcroForm and Widget Annotation Scanning
                    form_entities: List[RedactionEntity] = []
                    if page_idx - 1 < len(pike_doc.pages):
                        pike_page = pike_doc.pages[page_idx - 1]
                        if "/Annots" in pike_page:
                            for annot in pike_page.Annots:
                                if annot.get("/Subtype") == pikepdf.Name("/Widget"):
                                    val = annot.get("/V")
                                    if val is not None:
                                        val_str = str(val).strip()
                                        field_title = str(annot.get("/T", annot.get("/TU", "")))
                                        if (
                                            val_str
                                            and len(val_str) > 1
                                            and val_str not in ("/Yes", "/Off", "/No")
                                        ):
                                            rect = annot.get("/Rect")
                                            w_box = None
                                            if rect and len(rect) == 4:
                                                w_box = BoundingBox(
                                                    page=page_idx,
                                                    x0=round(float(rect[0]), 2),
                                                    y0=round(float(rect[1]), 2),
                                                    x1=round(float(rect[2]), 2),
                                                    y1=round(float(rect[3]), 2),
                                                )

                                            # Contextual evaluation of form box based on prompt/question
                                            if self.assess_form_context and field_title:
                                                assessed = assessor.assess_form_field(
                                                    field_title=field_title,
                                                    field_value=val_str,
                                                    page_number=page_idx,
                                                    bounding_box=w_box,
                                                )
                                                form_entities.extend(assessed)

                                            # Also run deterministic scan on field value
                                            f_ents = self.deterministic_engine.scan_text(
                                                val_str, page_number=page_idx
                                            )
                                            for fe in f_ents:
                                                if w_box:
                                                    fe.bounding_boxes = [w_box]
                                                if field_title:
                                                    fe.context_label = f"Form Field: {field_title}"
                                                if fe.category == "gps_coordinate":
                                                    c_type, statute, conf, should_redact = assessor.assess_coordinate_context(
                                                        coord_text=fe.text,
                                                        surrounding_text=val_str,
                                                        field_title=field_title,
                                                    )
                                                    if not should_redact:
                                                        continue
                                                    c_name = c_type.value if hasattr(c_type, "value") else str(c_type)
                                                    fe.statute_code = statute
                                                    fe.category = f"gps_{c_name}"
                                                form_entities.append(fe)

                    # Merge without duplicates
                    seen_keys = set()
                    page_entities = []
                    for e in tier1_entities + tier2_entities + form_entities:
                        clean_text = e.text.strip()
                        bbox_key = (
                            round(e.bounding_boxes[0].x0, 1),
                            round(e.bounding_boxes[0].y0, 1),
                        ) if e.bounding_boxes else None
                        key = (clean_text.lower(), bbox_key)
                        if clean_text and key not in seen_keys:
                            seen_keys.add(key)
                            page_entities.append(e)

                    # 4. Spatial Geometry Reconciliation (using active page_obj)
                    for entity in page_entities:
                        if not entity.bounding_boxes:
                            bboxes = find_text_bounding_boxes(
                                analysis_pdf, page_idx, entity.text, page_obj=page
                            )
                            entity.bounding_boxes = bboxes

                    all_entities.extend(page_entities)

            return RedactionPlan(
                document_name=input_pdf.name,
                total_pages=total_pages,
                entities=all_entities,
            )
        finally:
            if tmp_normalized is not None and tmp_normalized.is_file():
                try:
                    tmp_normalized.unlink()
                except OSError:
                    pass

    def execute_plan(
        self,
        input_pdf: Path,
        plan: RedactionPlan,
        output_pdf: Path,
        certificate_pdf: Optional[Path] = None,
        repair_imperfect: bool = True,
    ) -> RedactionResult:
        """Execute surgical sanitization based on approved RedactionPlan."""
        silence_parser_warnings()
        start_time = time.time()

        # Execute PikePDF stream excision & canvas burn-in
        success, applied_count = self.sanitizer.sanitize_document(
            input_pdf=input_pdf,
            output_pdf=output_pdf,
            entities=plan.entities,
            eradicate_metadata=True,
            repair_imperfect=repair_imperfect,
        )

        # Verification check: inspect sanitized PDF for target strings
        verification_passed = self.verify_sanitization(output_pdf, plan.entities)

        # Generate official Virginia FOIA Redaction Certificate
        cert_path_str = None
        if certificate_pdf is not None:
            self.certificate_generator.generate_certificate(
                document_name=input_pdf.name,
                entities=plan.entities,
                output_path=certificate_pdf,
            )
            cert_path_str = str(certificate_pdf)

        duration = time.time() - start_time

        return RedactionResult(
            success=success,
            input_path=str(input_pdf),
            output_path=str(output_pdf),
            certificate_path=cert_path_str,
            redacted_count=applied_count,
            total_pages=plan.total_pages,
            execution_time_seconds=round(duration, 3),
            verification_passed=verification_passed,
        )

    def verify_sanitization(self, output_pdf: Path, entities: List[RedactionEntity]) -> bool:
        """Verify that redacted strings do not appear in output text on their targeted pages."""
        entities_by_page = {}
        for e in entities:
            if e.approved and len(e.text.strip()) > 2:
                entities_by_page.setdefault(e.page_number, []).append(e.text.strip())

        # Check 1: Extracted text verification via pdfplumber per page
        with pdfplumber.open(output_pdf) as pdf:
            for page_idx, page in enumerate(pdf.pages, start=1):
                page_targets = entities_by_page.get(page_idx, [])
                if not page_targets:
                    continue
                text = page.extract_text() or ""
                for target in page_targets:
                    if target.lower() in text.lower():
                        return False

        # Check 2: Raw bytes verification for high-entropy unique targets (SSN, DL, phone, email)
        raw_bytes = output_pdf.read_bytes()
        for e in entities:
            if not e.approved:
                continue
            txt = e.text.strip()
            if e.category in ("ssn", "driver_license", "phone", "email", "dob", "credit_card"):
                target_b = txt.encode("latin1", errors="ignore")
                if len(target_b) >= 7 and target_b in raw_bytes:
                    return False

        return True
