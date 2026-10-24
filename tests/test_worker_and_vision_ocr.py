"""Tests for the DigUp-style ephemeral JSON-RPC worker and Apple Vision OCR span bridge."""

import json
import subprocess
import sys
from pathlib import Path

from reportlab.pdfgen import canvas

from redact_gov.pipeline import RedactionPipeline
from redact_gov.worker import EphemeralRedactWorker


def _create_sample_pdf(path: Path, include_digital_text: bool = True) -> Path:
    c = canvas.Canvas(str(path), pagesize=(612, 792))
    if include_digital_text:
        c.setFont("Helvetica", 12)
        c.drawString(72, 700, "VIRGINIA FOIA INCIDENT REPORT")
        c.drawString(72, 680, "Subject SSN: 123-45-6789")
        c.drawString(72, 660, "VA Driver License: T12345678")
    else:
        # Simulate a flattened image-only page with minimal digital text
        c.setFont("Helvetica", 10)
        c.drawString(72, 750, "SCAN")
    c.showPage()
    c.save()
    return path


def test_ephemeral_worker_ping_and_inspect(tmp_path: Path) -> None:
    pdf_path = _create_sample_pdf(tmp_path / "incident.pdf")
    worker = EphemeralRedactWorker(idle_timeout=30.0)

    ping_res = worker.handle_request({"id": 1, "method": "ping", "params": {}})
    assert ping_res["ok"] is True
    assert ping_res["result"]["status"] == "online"

    inspect_res = worker.handle_request(
        {"id": 2, "method": "inspect", "params": {"input_pdf": str(pdf_path)}}
    )
    assert inspect_res["ok"] is True
    assert inspect_res["result"]["total_pages"] == 1
    assert inspect_res["result"]["file_path"] == str(pdf_path)


def test_ephemeral_worker_plan_and_execute(tmp_path: Path) -> None:
    pdf_path = _create_sample_pdf(tmp_path / "foia_doc.pdf")
    out_pdf = tmp_path / "foia_doc_sanitized.pdf"
    cert_pdf = tmp_path / "foia_doc_cert.pdf"

    worker = EphemeralRedactWorker(idle_timeout=30.0)
    plan_res = worker.handle_request(
        {
            "id": 10,
            "method": "plan",
            "params": {
                "input_pdf": str(pdf_path),
                "profile": "public-foia",
                "coordinate_policy": "all",
                "repair": True,
            },
        }
    )
    assert plan_res["ok"] is True
    plan_dict = plan_res["result"]
    assert len(plan_dict["entities"]) >= 2

    exec_res = worker.handle_request(
        {
            "id": 11,
            "method": "execute",
            "params": {
                "input_pdf": str(pdf_path),
                "output_pdf": str(out_pdf),
                "certificate_pdf": str(cert_pdf),
                "plan": plan_dict,
                "repair": True,
            },
        }
    )
    assert exec_res["ok"] is True
    assert exec_res["result"]["verification_passed"] is True
    assert out_pdf.exists()
    assert cert_pdf.exists()


def test_ephemeral_worker_readonly_root_data_fallback(tmp_path: Path) -> None:
    """Verify that passing '/data/output/...' (e.g. when macOS LaunchServices cwd is '/')
    never fails with '[Errno 30] Read-only file system: /data' and redirects safely.
    """
    pdf_path = _create_sample_pdf(tmp_path / "launchservices_doc.pdf")
    worker = EphemeralRedactWorker(idle_timeout=30.0)

    res = worker.handle_request(
        {
            "id": 42,
            "method": "quick_redact",
            "params": {
                "input_pdf": str(pdf_path),
                "output_pdf": "/data/output/launchservices_doc_sanitized.pdf",
                "certificate_pdf": "/data/output/launchservices_doc_certificate.pdf",
                "profile": "public-foia",
            },
        }
    )
    assert res["ok"] is True, f"Expected fallback to succeed, got: {res}"
    actual_out = Path(res["result"]["result"]["output_path"])
    actual_cert = Path(res["result"]["result"]["certificate_path"])
    assert not str(actual_out).startswith("/data/")
    assert actual_out.exists()
    assert actual_cert.exists()


def test_apple_vision_external_ocr_spans_reconciliation(tmp_path: Path) -> None:
    scanned_pdf = _create_sample_pdf(tmp_path / "scanned_page.pdf", include_digital_text=False)
    vision_spans = [
        {
            "page": 1,
            "text": "Witness SSN: 987-65-4321",
            "x0": 80.0,
            "y0": 510.0,
            "x1": 245.0,
            "y1": 526.0,
        },
        {
            "page": 1,
            "text": "Driver License: A87654321",
            "x0": 80.0,
            "y0": 480.0,
            "x1": 250.0,
            "y1": 496.0,
        },
    ]

    pipeline = RedactionPipeline(gemma_model_path=Path("/nonexistent/mock.gguf"))
    plan = pipeline.create_plan(
        scanned_pdf,
        normalize_imperfect=False,
        external_ocr_spans=vision_spans,
    )

    ssn_entities = [e for e in plan.entities if "987-65-4321" in e.text]
    assert len(ssn_entities) == 1
    ssn_entity = ssn_entities[0]
    assert len(ssn_entity.bounding_boxes) == 1
    bbox = ssn_entity.bounding_boxes[0]
    assert bbox.x0 == 80.0
    assert bbox.y0 == 510.0
    assert bbox.x1 == 245.0
    assert bbox.y1 == 526.0


def test_worker_stdio_subprocess_roundtrip(tmp_path: Path) -> None:
    pdf_path = _create_sample_pdf(tmp_path / "stdio_test.pdf")
    proc = subprocess.Popen(
        [sys.executable, "-m", "redact_gov.worker"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None

    req = {"id": 99, "method": "inspect", "params": {"input_pdf": str(pdf_path)}}
    proc.stdin.write(json.dumps(req) + "\n")
    proc.stdin.flush()

    line = proc.stdout.readline()
    resp = json.loads(line)
    assert resp["id"] == 99
    assert resp["ok"] is True
    assert resp["result"]["total_pages"] == 1

    shutdown_req = {"id": 100, "method": "shutdown", "params": {}}
    proc.stdin.write(json.dumps(shutdown_req) + "\n")
    proc.stdin.flush()
    proc.wait(timeout=5)


def test_manual_blackmarker_box_enrichment_and_stream_sanitization(tmp_path: Path) -> None:
    """Verify that a user-drawn Manual Blackmarker marquee box automatically resolves
    underlying PDF word tokens inside its coordinates, excises them from the PDF
    content stream via PikePDF, and passes zero-residual verification.
    """
    pdf_path = tmp_path / "manual_blackmarker_target.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=(612, 792))
    c.setFont("Helvetica", 12)
    c.drawString(72, 700, "PUBLIC HEADER: VIRGINIA FOIA RELEASE")
    c.drawString(72, 640, "Undercover Callsign: NIGHTHAWK-77")
    c.showPage()
    c.save()

    out_pdf = tmp_path / "manual_blackmarker_sanitized.pdf"
    cert_pdf = tmp_path / "manual_blackmarker_cert.pdf"

    worker = EphemeralRedactWorker(idle_timeout=30.0)
    plan_res = worker.handle_request(
        {
            "id": 201,
            "method": "plan",
            "params": {
                "input_pdf": str(pdf_path),
                "profile": "public-foia",
                "coordinate_policy": "all",
                "repair": True,
            },
        }
    )
    assert plan_res["ok"] is True
    plan_dict = plan_res["result"]

    # Simulate user drawing a manual Blackmarker marquee rectangle over y=632..656
    plan_dict["entities"].append(
        {
            "id": "man_001",
            "text": "[Manual Blackmarker (240x24pt)]",
            "category": "manual_redaction",
            "statute_code": "Va. Code § 2.2-3706",
            "confidence": 1.0,
            "page_number": 1,
            "bounding_boxes": [
                {"page": 1, "x0": 68.0, "y0": 632.0, "x1": 310.0, "y1": 656.0}
            ],
            "tier": "manual_blackmarker",
            "approved": True,
            "context_label": "Manual Blackmarker • Law Enforcement & Victims",
        }
    )

    exec_res = worker.handle_request(
        {
            "id": 202,
            "method": "execute",
            "params": {
                "input_pdf": str(pdf_path),
                "output_pdf": str(out_pdf),
                "certificate_pdf": str(cert_pdf),
                "plan": plan_dict,
                "repair": True,
            },
        }
    )
    assert exec_res["ok"] is True
    assert exec_res["result"]["verification_passed"] is True

    # Confirm 'NIGHTHAWK-77' was excised from the output PDF stream while 'PUBLIC HEADER' remains
    import pdfplumber

    with pdfplumber.open(out_pdf) as pdf:
        extracted = pdf.pages[0].extract_text() or ""
    assert "NIGHTHAWK-77" not in extracted
    assert "PUBLIC HEADER" in extracted


def test_native_macos_bundle_self_test() -> None:
    app_exec = (
        Path(__file__).resolve().parent.parent
        / "build"
        / "Blackmarker Studio.app"
        / "Contents"
        / "MacOS"
        / "RedactGovApp"
    )
    if not app_exec.exists():
        return
    # Simulate macOS LaunchServices ('open "build/Blackmarker Studio.app"') where cwd is '/'
    res = subprocess.run(
        [str(app_exec), "--self-test"],
        cwd="/",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert res.returncode == 0, f"Self-test failed with cwd='/': {res.stderr}"
    assert "REDACTGOV_NATIVE_SELFTEST_OK" in res.stdout


def test_file_history_ui_does_not_expose_sensitive_entity_text() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    app_swift = (repo_root / "Sources" / "RedactGovApp" / "RedactGovApp.swift").read_text(
        encoding="utf-8"
    )
    store_swift = (repo_root / "Sources" / "RedactGovKit" / "CaseIndexStore.swift").read_text(
        encoding="utf-8"
    )

    assert 'SidebarCard(title: "FILE HISTORY"' in app_swift
    assert 'SidebarCard(title: "FOIA DOCKET HISTORY"' not in app_swift
    assert "entry.entityText" not in app_swift.split('SidebarCard(title: "FILE HISTORY"')[1]
    assert "fm.fileExists(atPath: outPath)" in store_swift
    assert 'sqlite3_bind_text(stmt, 4, "[REDACTED]"' in store_swift


def test_redact_first_optional_certificate_second(tmp_path: Path) -> None:
    pdf_path = _create_sample_pdf(tmp_path / "redact_first.pdf")
    out_pdf = tmp_path / "redact_first_sanitized.pdf"
    cert_pdf = tmp_path / "redact_first_certificate.pdf"

    worker = EphemeralRedactWorker(idle_timeout=30.0)
    quick_res = worker.handle_request(
        {
            "id": 301,
            "method": "quick_redact",
            "params": {
                "input_pdf": str(pdf_path),
                "output_pdf": str(out_pdf),
                "profile": "public-foia",
            },
        }
    )
    assert quick_res["ok"] is True
    assert out_pdf.exists()
    assert not cert_pdf.exists()
    assert quick_res["result"]["result"]["certificate_path"] is None

    # Step 2: Generate optional certificate on demand
    cert_res = worker.handle_request(
        {
            "id": 302,
            "method": "generate_certificate",
            "params": {
                "input_pdf": str(pdf_path),
                "certificate_pdf": str(cert_pdf),
                "plan": quick_res["result"]["plan"],
            },
        }
    )
    assert cert_res["ok"] is True
    assert cert_pdf.exists()


def test_review_md_kid_simple_ux_remediations() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    app_swift = (repo_root / "Sources" / "RedactGovApp" / "RedactGovApp.swift").read_text(
        encoding="utf-8"
    )
    models_swift = (repo_root / "Sources" / "RedactGovKit" / "Models.swift").read_text(
        encoding="utf-8"
    )
    vm_swift = (repo_root / "Sources" / "RedactGovApp" / "AppViewModel.swift").read_text(
        encoding="utf-8"
    )

    # MUST-01: Manual Statute Picker removed from canvas bar
    assert 'Picker("Manual Statute"' not in app_swift
    # MUST-02: Ephemeral Worker Engine RAM card removed from sidebar
    assert 'SidebarCard(title: "EPHEMERAL WORKER ENGINE"' not in app_swift
    assert 'Label("Free RAM"' not in app_swift
    # MUST-03: Technical toggles ("Auto-Heal Imperfect PDFs", "Apple Vision Neural OCR") removed from UI
    assert 'Text("Auto-Heal Imperfect PDFs")' not in app_swift
    assert 'Text("Apple Vision Neural OCR")' not in app_swift
    # MUST-04: MenuBarDropletView opens Studio for visual review instead of silent auto-redaction
    droplet_section = app_swift.split("struct MenuBarDropletView")[1].split(
        "struct SovereignStudioView"
    )[0]
    assert "viewModel.loadAndAnalyze(pdfURL: url)" in droplet_section
    assert "quickDropSanitize" not in droplet_section
    # SHOULD-01 & SHOULD-02: Standard (All Protections) default + Plain-language domain labels
    assert "releaseProfile: ReleaseProfileChoice = .strictPrivacy" in vm_swift
    assert '"Standard (All Protections)"' in models_swift
    assert '"Personal Info"' in models_swift
    assert '"Medical & Health"' in models_swift
    assert '"Bank & Cards"' in models_swift
    # SHOULD-03: Certificate Template Editor moved to macOS Settings scene
    assert "Settings {" in app_swift




