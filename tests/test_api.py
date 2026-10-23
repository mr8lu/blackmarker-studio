import pytest
from fastapi.testclient import TestClient

from redact_gov.api.app import DOC_STORE, PLAN_STORE, app
from redact_gov.core.models import RedactionEntity, RedactionPlan

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_stores():
    DOC_STORE.clear()
    PLAN_STORE.clear()
    yield


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "online"
    assert "PII" in response.json()["supported_domains"]
    assert "PHI" in response.json()["supported_domains"]
    assert "PPI" in response.json()["supported_domains"]


def test_ui_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "AI Blackmarker" in response.text
    assert "HIPAA" in response.text
    assert "PCI DSS" in response.text


def test_certificate_presets_and_custom_config():
    presets_resp = client.get("/api/certificate/presets")
    assert presets_resp.status_code == 200
    presets = presets_resp.json()["presets"]
    assert "hipaa_healthcare" in presets
    assert "banking_glba_pci" in presets
    assert "judicial_frcp" in presets
    assert "enterprise_aicpa" in presets

    custom_payload = {
        "template_id": "custom_bank",
        "jurisdiction_banner": "FIRST NATIONAL BANK COMPLIANCE",
        "framework_subtitle": "GLBA 16 CFR Part 314 & PCI DSS v4.0",
        "certificate_title": "BANKING PPI SANITIZATION CERTIFICATE",
        "agency_name": "First National Bank InfoSec",
        "reviewer_name": "Compliance Officer",
        "attestation_statement": "All PAN and routing numbers excised.",
        "include_sha256_signature": True,
    }
    save_resp = client.post("/api/certificate/config", json=custom_payload)
    assert save_resp.status_code == 200
    assert save_resp.json()["config"]["agency_name"] == "First National Bank InfoSec"


def test_upload_pdf(tmp_path, monkeypatch):
    import redact_gov.api.app as app_module

    class MockPipeline:
        def create_plan(self, input_pdf, **kwargs):
            return RedactionPlan(
                document_name=input_pdf.name,
                total_pages=2,
                entities=[],
            )

    monkeypatch.setattr(app_module, "pipeline", MockPipeline())
    monkeypatch.setattr(app_module.settings, "OUTPUT_DIR", tmp_path)

    dummy_pdf = tmp_path / "dummy.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4\n%EOF")

    with open(dummy_pdf, "rb") as f:
        response = client.post(
            "/api/documents/upload",
            files={"file": ("dummy.pdf", f, "application/pdf")},
            data={"profile": "hipaa", "domains": "PII,PHI"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "doc_id" in data
    doc_id = data["doc_id"]

    plan_resp = client.get(f"/api/documents/{doc_id}/plan")
    assert plan_resp.status_code == 200

    plan_data = plan_resp.json()
    plan_data["entities"].append(
        {
            "text": "MRN-123456",
            "category": "mrn",
            "data_domain": "PHI",
            "statute_code": "45 CFR § 164.514(b)",
            "bounding_boxes": [],
            "confidence": 1.0,
            "approved": True,
        }
    )

    update_resp = client.post(f"/api/documents/{doc_id}/plan", json=plan_data)
    assert update_resp.status_code == 200
    assert len(update_resp.json()["plan"]["entities"]) > 0


def test_execute_and_download(tmp_path, monkeypatch):
    import redact_gov.api.app as app_module

    monkeypatch.setattr(app_module.settings, "OUTPUT_DIR", tmp_path)

    class MockPipeline:
        def execute_plan(self, input_pdf, plan, output_pdf, certificate_pdf, **kwargs):
            output_pdf.write_bytes(b"%PDF-1.4 output")
            certificate_pdf.write_bytes(b"%PDF-1.4 cert")
            return {"status": "success"}

    monkeypatch.setattr(app_module, "pipeline", MockPipeline())

    doc_id = "test-doc"
    app_module.DOC_STORE[doc_id] = tmp_path / "input.pdf"
    app_module.DOC_STORE[doc_id].write_bytes(b"%PDF-1.4")
    app_module.PLAN_STORE[doc_id] = RedactionPlan(
        document_name="test", total_pages=1, entities=[]
    )

    exec_resp = client.post(f"/api/documents/{doc_id}/execute", json={})
    assert exec_resp.status_code == 200

    dl_resp = client.get(f"/api/documents/{doc_id}/download")
    assert dl_resp.status_code == 200
    assert dl_resp.content == b"%PDF-1.4 output"

    cert_resp = client.get(f"/api/documents/{doc_id}/certificate")
    assert cert_resp.status_code == 200
    assert cert_resp.content == b"%PDF-1.4 cert"
