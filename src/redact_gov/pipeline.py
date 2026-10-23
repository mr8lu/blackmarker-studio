"""Complete sovereign redaction pipeline integrating extraction, multi-sector compliance, spatial alignment, and stream sanitization."""

from pathlib import Path
import time
from typing import Any, Dict, Iterable, List, Optional, Union
import pdfplumber
import pikepdf

from redact_gov.certificates.generator import CertificateGenerator
from redact_gov.core.context_assessor import ContextAssessor
from redact_gov.core.criteria import (
    CoordinatePolicy,
    RedactionCriteriaRegistry,
    ReleaseProfile,
)
from redact_gov.core.geometry import (
    extract_words_in_bounding_box,
    find_text_bounding_boxes,
    get_document_page_count,
)
from redact_gov.core.models import (
    BoundingBox,
    CertificateConfig,
    RedactionEntity,
    RedactionPlan,
    RedactionResult,
)
from redact_gov.core.normalizer import DocumentNormalizer, silence_parser_warnings
from redact_gov.core.statutes import get_data_domain_for_category, get_statute_by_category
from redact_gov.engines.contextual import ContextualGemmaEngine
from redact_gov.engines.deterministic import DeterministicRedactionEngine
from redact_gov.engines.sanitization import PikePdfSanitizer


def _coerce_profile(profile: Optional[Union[ReleaseProfile, str]]) -> ReleaseProfile:
    if isinstance(profile, ReleaseProfile):
        return profile
    if isinstance(profile, str) and profile.strip():
        norm = profile.lower().strip().replace("-", "_")
        try:
            return ReleaseProfile(norm)
        except ValueError:
            pass
    return ReleaseProfile.PUBLIC_FOIA


class RedactionPipeline:
    """Orchestrates hybrid on-device extraction, a-la-carte PII/PHI/PPI domain filtering, and PikePDF surgical stream scrubbing."""

    def __init__(
        self,
        gemma_model_path: Optional[Path] = None,
        model_path: Optional[Path] = None,
        profile: Union[ReleaseProfile, str] = ReleaseProfile.PUBLIC_FOIA,
        coordinate_policy: str = "all",
        assess_form_context: bool = True,
        criteria_registry: Optional[RedactionCriteriaRegistry] = None,
        enabled_domains: Optional[Iterable[str]] = None,
    ):
        silence_parser_warnings()
        resolved_model = gemma_model_path or model_path
        self.deterministic_engine = DeterministicRedactionEngine()
        self.contextual_engine = ContextualGemmaEngine(model_path=resolved_model)

        release_profile = _coerce_profile(profile)
        self.profile = release_profile.value
        self.criteria_registry = criteria_registry or RedactionCriteriaRegistry(
            profile=release_profile,
            enabled_domains=enabled_domains,
        )
        if coordinate_policy:
            self.criteria_registry.set_coordinate_policy(coordinate_policy)
        self.criteria_registry.set_assess_form_context(assess_form_context)

        self.context_assessor = ContextAssessor(registry=self.criteria_registry)
        self.sanitizer = PikePdfSanitizer()
        self.certificate_generator = CertificateGenerator()
        self.normalizer = DocumentNormalizer()
        self.assess_form_context = assess_form_context

    @property
    def enabled_domains(self) -> List[str]:
        """Return ordered list of active a-la-carte data domains (PII, PHI, PPI)."""
        order = ["PII", "PHI", "PPI"]
        active = self.criteria_registry.active_profile.enabled_domains
        return [d for d in order if d in active]

    def create_plan(
        self,
        input_pdf: Optional[Path] = None,
        normalize_imperfect: bool = True,
        coordinate_policy: Optional[str] = None,
        profile: Optional[Union[ReleaseProfile, str]] = None,
        enabled_domains: Optional[Iterable[str]] = None,
        external_ocr_spans: Optional[List[dict]] = None,
        *,
        pdf_path: Optional[Path] = None,
        assess_form_context: Optional[bool] = None,
    ) -> RedactionPlan:
        """Analyze PDF across all pages and generate a complete RedactionPlan with geometry."""
        silence_parser_warnings()
        target_pdf = Path(input_pdf or pdf_path)

        effective_profile_enum = _coerce_profile(
            profile or self.criteria_registry.active_profile.profile
        )
        effective_profile = effective_profile_enum.value

        if profile or coordinate_policy or enabled_domains is not None:
            assessor_registry = RedactionCriteriaRegistry(
                profile=effective_profile_enum,
                enabled_domains=enabled_domains if enabled_domains is not None else self.enabled_domains,
            )
            if coordinate_policy:
                assessor_registry.set_coordinate_policy(coordinate_policy)
            assessor = ContextAssessor(registry=assessor_registry)
        else:
            assessor_registry = self.criteria_registry
            assessor = self.context_assessor

        active_domains = [
            d for d in ["PII", "PHI", "PPI"]
            if d in assessor_registry.active_profile.enabled_domains
        ]
        do_form_assess = (
            assess_form_context if assess_form_context is not None else self.assess_form_context
        )

        ocr_by_page: dict[int, List[dict]] = {}
        if external_ocr_spans:
            for span in external_ocr_spans:
                pg = int(span.get("page", 1))
                ocr_by_page.setdefault(pg, []).append(span)

        # Step 0: Check and pre-normalize imperfect document if needed
        analysis_pdf = target_pdf
        tmp_normalized: Optional[Path] = None

        if normalize_imperfect:
            report = self.normalizer.inspect_document(target_pdf)
            if report.is_imperfect:
                tmp_normalized, _ = self.normalizer.normalize_pdf(target_pdf)
                analysis_pdf = tmp_normalized

        try:
            total_pages = get_document_page_count(analysis_pdf)
            all_entities: List[RedactionEntity] = []

            with (
                pdfplumber.open(analysis_pdf) as pdf,
                pikepdf.open(analysis_pdf, attempt_recovery=True) as pike_doc,
            ):
                for page_idx, page in enumerate(pdf.pages, start=1):
                    digital_text = page.extract_text(layout=False) or ""
                    page_ocr_spans = ocr_by_page.get(page_idx, [])
                    ocr_text = "\n".join(
                        str(s.get("text", "")).strip()
                        for s in page_ocr_spans
                        if str(s.get("text", "")).strip()
                    )
                    page_text = (
                        f"{digital_text}\n{ocr_text}".strip()
                        if ocr_text and ocr_text not in digital_text
                        else digital_text
                    )

                    # 1. Tier 1 Deterministic Fast Path on content stream + Vision OCR
                    raw_tier1 = (
                        self.deterministic_engine.scan_text(
                            page_text,
                            page_number=page_idx,
                            enabled_domains=active_domains,
                            profile=effective_profile,
                        )
                        if page_text.strip()
                        else []
                    )
                    tier1_entities: List[RedactionEntity] = []
                    for e in raw_tier1:
                        if e.category == "gps_coordinate":
                            idx = page_text.find(e.text)
                            start_ctx = max(0, idx - 150) if idx != -1 else 0
                            end_ctx = (
                                min(len(page_text), idx + len(e.text) + 150)
                                if idx != -1
                                else len(page_text)
                            )
                            surrounding = page_text[start_ctx:end_ctx]
                            c_type, statute, conf, should_redact = (
                                assessor.assess_coordinate_context(
                                    coord_text=e.text,
                                    surrounding_text=surrounding,
                                )
                            )
                            if not should_redact:
                                continue
                            c_name = c_type.value if hasattr(c_type, "value") else str(c_type)
                            e.statute_code = statute
                            e.category = f"gps_{c_name}"
                            e.context_label = f"Text Context: {c_name}"
                        tier1_entities.append(e)

                    # 2. Tier 2 Contextual Cognitive Path / Multimodal Vision
                    if len(page_text.strip()) < 20:
                        try:
                            page_img = page.to_image(resolution=72).original
                            img_path = Path(f"/tmp/redact_gov_page_{page_idx}.png")
                            page_img.save(img_path)
                            tier2_entities = self.contextual_engine.analyze_image(
                                img_path,
                                page_number=page_idx,
                                enabled_domains=active_domains,
                                profile=effective_profile,
                            )
                            if img_path.exists():
                                img_path.unlink()
                        except Exception:
                            tier2_entities = []
                    else:
                        tier2_entities = (
                            self.contextual_engine.analyze_text(
                                page_text,
                                page_number=page_idx,
                                enabled_domains=active_domains,
                                profile=effective_profile,
                            )
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
                                        field_title = str(
                                            annot.get("/T", annot.get("/TU", ""))
                                        )
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

                                            if do_form_assess and field_title:
                                                assessed = assessor.assess_form_field(
                                                    field_title=field_title,
                                                    field_value=val_str,
                                                    page_number=page_idx,
                                                    bounding_box=w_box,
                                                )
                                                for ae in assessed:
                                                    ae.data_domain = get_data_domain_for_category(ae.category)
                                                    if ae.data_domain not in active_domains:
                                                        continue
                                                    mapped = get_statute_by_category(
                                                        ae.category, profile=effective_profile
                                                    )
                                                    if mapped:
                                                        ae.statute_code = mapped.code
                                                    form_entities.append(ae)

                                            f_ents = self.deterministic_engine.scan_text(
                                                val_str,
                                                page_number=page_idx,
                                                enabled_domains=active_domains,
                                                profile=effective_profile,
                                            )
                                            for fe in f_ents:
                                                if w_box:
                                                    fe.bounding_boxes = [w_box]
                                                if field_title:
                                                    fe.context_label = f"Form Field: {field_title}"
                                                if fe.category == "gps_coordinate":
                                                    c_type, statute, conf, should_redact = (
                                                        assessor.assess_coordinate_context(
                                                            coord_text=fe.text,
                                                            surrounding_text=val_str,
                                                            field_title=field_title,
                                                        )
                                                    )
                                                    if not should_redact:
                                                        continue
                                                    c_name = (
                                                        c_type.value
                                                        if hasattr(c_type, "value")
                                                        else str(c_type)
                                                    )
                                                    fe.statute_code = statute
                                                    fe.category = f"gps_{c_name}"
                                                form_entities.append(fe)

                    # Merge without duplicates
                    seen_keys = set()
                    page_entities = []
                    for e in tier1_entities + tier2_entities + form_entities:
                        clean_text = e.text.strip()
                        bbox_key = (
                            (
                                round(e.bounding_boxes[0].x0, 1),
                                round(e.bounding_boxes[0].y0, 1),
                            )
                            if e.bounding_boxes
                            else None
                        )
                        key = (clean_text.lower(), bbox_key)
                        if clean_text and key not in seen_keys:
                            seen_keys.add(key)
                            page_entities.append(e)

                    # 4. Spatial Geometry Reconciliation (using active page_obj + Apple Vision OCR fallback)
                    for entity in page_entities:
                        if not entity.bounding_boxes:
                            bboxes = find_text_bounding_boxes(
                                analysis_pdf, page_idx, entity.text, page_obj=page
                            )
                            if not bboxes and page_ocr_spans:
                                target_lower = entity.text.strip().lower()
                                for span in page_ocr_spans:
                                    span_text = str(span.get("text", "")).strip()
                                    if span_text and (
                                        target_lower in span_text.lower()
                                        or span_text.lower() in target_lower
                                    ):
                                        bboxes.append(
                                            BoundingBox(
                                                page=page_idx,
                                                x0=round(float(span["x0"]), 2),
                                                y0=round(float(span["y0"]), 2),
                                                x1=round(float(span["x1"]), 2),
                                                y1=round(float(span["y1"]), 2),
                                            )
                                        )
                                if bboxes and not entity.context_label:
                                    entity.context_label = "Apple Vision Neural OCR"
                            entity.bounding_boxes = bboxes

                    all_entities.extend(page_entities)

            return RedactionPlan(
                document_name=target_pdf.name,
                total_pages=total_pages,
                entities=all_entities,
                profile=effective_profile,
                enabled_domains=active_domains,
            )
        finally:
            if tmp_normalized is not None and tmp_normalized.is_file():
                try:
                    tmp_normalized.unlink()
                except OSError:
                    pass

    def execute_plan(
        self,
        input_pdf: Optional[Path] = None,
        arg2: Optional[Union[RedactionPlan, Path]] = None,
        arg3: Optional[Union[Path, RedactionPlan]] = None,
        arg4: Optional[Path] = None,
        *,
        pdf_path: Optional[Path] = None,
        plan: Optional[RedactionPlan] = None,
        output_pdf: Optional[Path] = None,
        output_path: Optional[Path] = None,
        certificate_pdf: Optional[Path] = None,
        certificate_path: Optional[Path] = None,
        repair_imperfect: bool = True,
        agency_name: Optional[str] = None,
        reviewer_name: Optional[str] = None,
        certificate_config: Optional[Union[CertificateConfig, Dict[str, Any]]] = None,
    ) -> RedactionResult:
        """Execute surgical sanitization based on approved RedactionPlan and issue customizable Certificate."""
        silence_parser_warnings()
        start_time = time.time()

        resolved_input = Path(input_pdf or pdf_path)
        resolved_plan = plan
        resolved_output = output_pdf or output_path
        resolved_cert = certificate_pdf or certificate_path

        if isinstance(arg2, RedactionPlan):
            resolved_plan = arg2
            if isinstance(arg3, Path):
                resolved_output = arg3
        elif isinstance(arg2, Path):
            resolved_output = arg2
            if isinstance(arg3, RedactionPlan):
                resolved_plan = arg3

        if arg4 is not None and resolved_cert is None:
            resolved_cert = arg4

        assert resolved_plan is not None, "RedactionPlan is required"
        assert resolved_output is not None, "output_pdf / output_path is required"
        resolved_output = Path(resolved_output)
        if resolved_cert is not None:
            resolved_cert = Path(resolved_cert)

        # Enrich any manual marquee redactions with underlying PDF text tokens so stream glyphs are excised
        for entity in resolved_plan.entities:
            if not entity.approved:
                continue
            is_manual = (
                entity.category in ("manual_redaction", "manual")
                or entity.tier == "manual_blackmarker"
                or entity.text.strip().startswith("[Manual")
                or entity.text.strip().startswith("[MANUAL")
            )
            if is_manual and entity.bounding_boxes:
                discovered_words: List[str] = []
                for box in entity.bounding_boxes:
                    discovered_words.extend(extract_words_in_bounding_box(resolved_input, box))
                if discovered_words and (
                    entity.text.strip().startswith("[Manual")
                    or entity.text.strip().startswith("[MANUAL")
                ):
                    entity.text = " ".join(discovered_words)

        # Execute PikePDF stream excision & canvas burn-in
        success, applied_count = self.sanitizer.sanitize_document(
            input_pdf=resolved_input,
            output_pdf=resolved_output,
            entities=resolved_plan.entities,
            eradicate_metadata=True,
            repair_imperfect=repair_imperfect,
        )

        # Verification check: inspect sanitized PDF for target strings
        verification_passed = self.verify_sanitization(resolved_output, resolved_plan.entities)

        # Generate official customizable Redaction Certificate
        cert_path_str = None
        if resolved_cert is not None:
            self.certificate_generator.generate_certificate(
                document_name=resolved_input.name,
                entities=resolved_plan.entities,
                output_path=resolved_cert,
                reviewer_name=reviewer_name,
                agency_name=agency_name,
                certificate_config=certificate_config,
            )
            cert_path_str = str(resolved_cert)

        duration = time.time() - start_time

        return RedactionResult(
            success=success,
            input_path=str(resolved_input),
            output_path=str(resolved_output),
            certificate_path=cert_path_str,
            redacted_count=applied_count,
            total_pages=resolved_plan.total_pages,
            execution_time_seconds=round(duration, 3),
            verification_passed=verification_passed,
        )

    def verify_sanitization(self, output_pdf: Path, entities: List[RedactionEntity]) -> bool:
        """Verify that redacted strings do not appear in output text on their targeted pages."""
        entities_by_page = {}
        for e in entities:
            txt = e.text.strip()
            if e.approved and len(txt) > 2 and not txt.startswith("[Manual") and not txt.startswith("[MANUAL"):
                entities_by_page.setdefault(e.page_number, []).append(txt)

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

        # Check 2: Raw bytes verification for high-entropy unique targets (SSN, DL, phone, email, PHI/PPI IDs)
        raw_bytes = output_pdf.read_bytes()
        for e in entities:
            if not e.approved:
                continue
            txt = e.text.strip()
            if e.category in (
                "ssn",
                "driver_license",
                "phone",
                "email",
                "dob",
                "credit_card",
                "mrn",
                "npi",
                "routing_number",
                "bank_account",
                "iban",
            ):
                target_b = txt.encode("latin1", errors="ignore")
                if len(target_b) >= 7 and target_b in raw_bytes:
                    return False

        return True
