"""End-to-end redaction pipeline orchestrating Tier 1, Tier 2, Geometry, and PikePDF Sanitization."""

import time
from pathlib import Path
from typing import List, Optional

import pdfplumber

from redact_gov.certificates.generator import CertificateGenerator
from redact_gov.core.geometry import find_text_bounding_boxes, get_document_page_count
from redact_gov.core.models import RedactionEntity, RedactionPlan, RedactionResult
from redact_gov.engines.contextual import ContextualGemmaEngine
from redact_gov.engines.deterministic import DeterministicRedactionEngine
from redact_gov.engines.sanitization import PikePdfSanitizer


class RedactionPipeline:
    """Orchestrates hybrid on-device extraction and PikePDF surgical stream scrubbing."""

    def __init__(self, gemma_model_path: Optional[Path] = None):
        self.deterministic_engine = DeterministicRedactionEngine()
        self.contextual_engine = ContextualGemmaEngine(model_path=gemma_model_path)
        self.sanitizer = PikePdfSanitizer()
        self.certificate_generator = CertificateGenerator()

    def create_plan(self, input_pdf: Path) -> RedactionPlan:
        """Analyze PDF across all pages and generate a complete RedactionPlan with geometry."""
        total_pages = get_document_page_count(input_pdf)
        all_entities: List[RedactionEntity] = []

        with pdfplumber.open(input_pdf) as pdf:
            for page_idx, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text(layout=False) or ""
                if not page_text.strip():
                    continue

                # 1. Tier 1 Deterministic Fast Path
                tier1_entities = self.deterministic_engine.scan_text(page_text, page_number=page_idx)

                # 2. Tier 2 Contextual Cognitive Path (Google Gemma 4 E4B)
                tier2_entities = self.contextual_engine.analyze_text(page_text, page_number=page_idx)

                # Merge without duplicates
                seen_texts = set()
                page_entities = []
                for e in tier1_entities + tier2_entities:
                    clean_text = e.text.strip()
                    if clean_text and clean_text.lower() not in seen_texts:
                        seen_texts.add(clean_text.lower())
                        page_entities.append(e)

                # 3. Spatial Geometry Reconciliation
                for entity in page_entities:
                    bboxes = find_text_bounding_boxes(input_pdf, page_idx, entity.text)
                    entity.bounding_boxes = bboxes

                all_entities.extend(page_entities)

        return RedactionPlan(
            document_name=input_pdf.name,
            total_pages=total_pages,
            entities=all_entities,
        )

    def execute_plan(
        self,
        input_pdf: Path,
        plan: RedactionPlan,
        output_pdf: Path,
        certificate_pdf: Optional[Path] = None,
    ) -> RedactionResult:
        """Execute surgical sanitization based on approved RedactionPlan."""
        start_time = time.time()

        # Execute PikePDF stream excision & canvas burn-in
        success, applied_count = self.sanitizer.sanitize_document(
            input_pdf=input_pdf,
            output_pdf=output_pdf,
            entities=plan.entities,
            eradicate_metadata=True,
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
        """Verify that redacted strings do not appear in output text or uncompressed streams."""
        target_strings = [e.text.strip() for e in entities if e.approved and len(e.text.strip()) > 2]
        if not target_strings:
            return True

        # Check 1: Extracted text verification via pdfplumber
        with pdfplumber.open(output_pdf) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                for target in target_strings:
                    if target.lower() in text.lower():
                        return False

        # Check 2: Raw bytes verification
        raw_bytes = output_pdf.read_bytes()
        for target in target_strings:
            target_b = target.encode("latin1", errors="ignore")
            # If target length is sufficient and appears in raw bytes unencoded, fail verification
            if len(target_b) >= 6 and target_b in raw_bytes:
                return False

        return True
