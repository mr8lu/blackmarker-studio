"""Ephemeral JSON-RPC stdio worker for the RedactGov macOS native utility.

Modeled after DigUp's `Contents/Helpers/digup` worker architecture:
- Spawns on demand when the user inspects or redacts a PDF.
- Keeps Google Gemma 4 E4B warm during an active batch session.
- Automatically terminates after `idle_timeout` seconds of inactivity so the
  menu bar utility consumes zero unified memory / VRAM while idle.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from redact_gov.core.criteria import ReleaseProfile
from redact_gov.core.models import RedactionPlan
from redact_gov.core.normalizer import DocumentNormalizer, silence_parser_warnings
from redact_gov.core.statutes import list_statutes
from redact_gov.pipeline import RedactionPipeline


def _resolve_profile(profile_str: Optional[str]) -> ReleaseProfile:
    if not profile_str:
        return ReleaseProfile.PUBLIC_FOIA
    normalized = profile_str.lower().strip().replace("-", "_")
    try:
        return ReleaseProfile(normalized)
    except ValueError:
        return ReleaseProfile.PUBLIC_FOIA


def _ensure_writable_output_path(requested_path: Path, input_pdf: Path) -> Path:
    """Ensure the output file's parent directory is writable, falling back if needed.

    When a macOS app bundle is launched via LaunchServices (`open RedactGov.app`),
    its initial working directory is `/`, which can produce `/data/output/...` on
    macOS's read-only root volume. This helper transparently redirects any
    unwritable `/data/...` path to the workspace's `data/output` or `input_pdf.parent`.
    """
    resolved = requested_path.expanduser().resolve()
    try:
        if not str(resolved).startswith("/data/"):
            resolved.parent.mkdir(parents=True, exist_ok=True)
            return resolved
    except OSError:
        pass

    # Fallback 1: repository root data/output
    repo_root = Path(__file__).resolve().parent.parent.parent
    repo_out = repo_root / "data" / "output"
    try:
        repo_out.mkdir(parents=True, exist_ok=True)
        return repo_out / resolved.name
    except OSError:
        pass

    # Fallback 2: same directory as input_pdf
    return input_pdf.parent / resolved.name


class EphemeralRedactWorker:
    """Handles line-delimited JSON-RPC requests over stdin/stdout with idle auto-shutdown."""

    def __init__(self, idle_timeout: float = 180.0) -> None:
        silence_parser_warnings()
        self.idle_timeout = idle_timeout
        self.last_activity = time.monotonic()
        self._pipeline: Optional[RedactionPipeline] = None
        self._normalizer = DocumentNormalizer()
        self._shutdown_requested = False
        self._lock = threading.Lock()

    def _get_pipeline(self) -> RedactionPipeline:
        if self._pipeline is None:
            self._pipeline = RedactionPipeline()
        return self._pipeline

    def touch(self) -> None:
        self.last_activity = time.monotonic()

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single JSON-RPC style request dictionary and return a response dictionary."""
        self.touch()
        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params") or {}

        try:
            if method == "ping":
                result = {
                    "status": "online",
                    "worker_loaded": self._pipeline is not None,
                    "gemma_loaded": bool(
                        self._pipeline
                        and self._pipeline.contextual_engine.llama_instance is not None
                    ),
                    "idle_seconds": round(time.monotonic() - self.last_activity, 2),
                    "idle_timeout": self.idle_timeout,
                }
            elif method == "statutes":
                result = {
                    "statutes": [s.model_dump() for s in list_statutes()],
                }
            elif method == "inspect":
                pdf_path = Path(params["input_pdf"]).expanduser().resolve()
                if not pdf_path.is_file():
                    raise FileNotFoundError(f"PDF not found: {pdf_path}")
                report = self._normalizer.inspect_document(pdf_path)
                result = {
                    "file_path": str(pdf_path),
                    "total_pages": report.total_pages,
                    "is_imperfect": report.is_imperfect,
                    "issues": report.issues,
                    "repaired_fonts": report.repaired_fonts_count,
                    "repaired_streams": 0,
                }
            elif method == "plan":
                pdf_path = Path(params["input_pdf"]).expanduser().resolve()
                if not pdf_path.is_file():
                    raise FileNotFoundError(f"PDF not found: {pdf_path}")
                profile = _resolve_profile(params.get("profile"))
                coord_policy = params.get("coordinate_policy") or (
                    "sensitive-only"
                    if profile == ReleaseProfile.ENVIRONMENTAL_REVIEW
                    else "all"
                )
                repair = bool(params.get("repair", True))
                vision_spans = params.get("vision_ocr_spans") or []

                pipeline = self._get_pipeline()
                plan = pipeline.create_plan(
                    input_pdf=pdf_path,
                    normalize_imperfect=repair,
                    coordinate_policy=coord_policy,
                    profile=profile,
                    external_ocr_spans=vision_spans,
                )
                result = plan.model_dump()
            elif method == "execute":
                pdf_path = Path(params["input_pdf"]).expanduser().resolve()
                if not pdf_path.is_file():
                    raise FileNotFoundError(f"PDF not found: {pdf_path}")
                output_pdf = _ensure_writable_output_path(
                    Path(params["output_pdf"]), pdf_path
                )
                cert_pdf_raw = params.get("certificate_pdf")
                cert_pdf = (
                    _ensure_writable_output_path(Path(cert_pdf_raw), pdf_path)
                    if cert_pdf_raw
                    else None
                )
                repair = bool(params.get("repair", True))

                plan_data = params["plan"]
                plan = RedactionPlan.model_validate(plan_data)

                pipeline = self._get_pipeline()
                exec_result = pipeline.execute_plan(
                    input_pdf=pdf_path,
                    plan=plan,
                    output_pdf=output_pdf,
                    certificate_pdf=cert_pdf,
                    repair_imperfect=repair,
                )
                result = exec_result.model_dump()
            elif method == "quick_redact":
                pdf_path = Path(params["input_pdf"]).expanduser().resolve()
                if not pdf_path.is_file():
                    raise FileNotFoundError(f"PDF not found: {pdf_path}")
                output_pdf = _ensure_writable_output_path(
                    Path(
                        params.get(
                            "output_pdf",
                            str(pdf_path.with_name(f"{pdf_path.stem}_sanitized.pdf")),
                        )
                    ),
                    pdf_path,
                )
                cert_pdf = _ensure_writable_output_path(
                    Path(
                        params.get(
                            "certificate_pdf",
                            str(pdf_path.with_name(f"{pdf_path.stem}_certificate.pdf")),
                        )
                    ),
                    pdf_path,
                )
                profile = _resolve_profile(params.get("profile"))
                coord_policy = params.get("coordinate_policy") or (
                    "sensitive-only"
                    if profile == ReleaseProfile.ENVIRONMENTAL_REVIEW
                    else "all"
                )
                repair = bool(params.get("repair", True))
                vision_spans = params.get("vision_ocr_spans") or []

                pipeline = self._get_pipeline()
                plan = pipeline.create_plan(
                    input_pdf=pdf_path,
                    normalize_imperfect=repair,
                    coordinate_policy=coord_policy,
                    profile=profile,
                    external_ocr_spans=vision_spans,
                )
                exec_result = pipeline.execute_plan(
                    input_pdf=pdf_path,
                    plan=plan,
                    output_pdf=output_pdf,
                    certificate_pdf=cert_pdf,
                    repair_imperfect=repair,
                )
                result = {
                    "plan": plan.model_dump(),
                    "result": exec_result.model_dump(),
                }
            elif method == "unload":
                self._pipeline = None
                result = {"status": "unloaded"}
            elif method == "shutdown":
                self._shutdown_requested = True
                self._pipeline = None
                result = {"status": "shutting_down"}
            else:
                raise ValueError(f"Unknown worker method: '{method}'")

            self.touch()
            return {"id": req_id, "ok": True, "result": result}
        except Exception as exc:
            self.touch()
            return {
                "id": req_id,
                "ok": False,
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            }

    def serve_stdio(self) -> None:
        """Run the newline-delimited JSON-RPC loop until EOF or idle timeout."""
        if self.idle_timeout > 0:
            watchdog = threading.Thread(target=self._idle_watchdog, daemon=True)
            watchdog.start()

        for raw_line in sys.stdin:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                resp = {
                    "id": None,
                    "ok": False,
                    "error": {"type": "JSONDecodeError", "message": str(exc)},
                }
            else:
                with self._lock:
                    resp = self.handle_request(payload)

            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

            if self._shutdown_requested:
                break

    def _idle_watchdog(self) -> None:
        while not self._shutdown_requested:
            time.sleep(1.0)
            idle_for = time.monotonic() - self.last_activity
            if idle_for >= self.idle_timeout:
                self._shutdown_requested = True
                try:
                    sys.exit(0)
                except SystemExit:
                    break


if __name__ == "__main__":
    EphemeralRedactWorker().serve_stdio()

