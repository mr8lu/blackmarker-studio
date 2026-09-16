import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from redact_gov.api.app import app, DOC_STORE, PLAN_STORE
from redact_gov.core.models import RedactionPlan, RedactionEntity, BoundingBox

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

def test_ui_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "RedactGov HITL Reviewer" in response.text

def test_upload_pdf(tmp_path, monkeypatch):
    import redact_gov.api.app as app_module
    
    # Mock pipeline
    class MockPipeline:
        def create_plan(self, input_pdf):
            return RedactionPlan(
                document_name=input_pdf.name,
                total_pages=2,
                entities=[]
            )
            
    monkeypatch.setattr(app_module, "pipeline", MockPipeline())
    monkeypatch.setattr(app_module.settings, "OUTPUT_DIR", tmp_path)
    
    # Create a dummy PDF
    dummy_pdf = tmp_path / "dummy.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4\n%EOF")
    
    with open(dummy_pdf, "rb") as f:
        response = client.post("/api/documents/upload", files={"file": ("dummy.pdf", f, "application/pdf")})
        
    assert response.status_code == 200
    data = response.json()
    assert "doc_id" in data
    doc_id = data["doc_id"]
    
    # Check plan
    plan_resp = client.get(f"/api/documents/{doc_id}/plan")
    assert plan_resp.status_code == 200
    
    # Update plan
    plan_data = plan_resp.json()
    # Add a mock entity
    plan_data["entities"].append({
        "text": "Secret",
        "category": "SSN",
        "statute_code": "2.2-3705.1(1)",
        "bounding_boxes": [],
        "confidence": 1.0,
        "approved": True
    })
    
    update_resp = client.post(f"/api/documents/{doc_id}/plan", json=plan_data)
    assert update_resp.status_code == 200
    assert len(update_resp.json()["plan"]["entities"]) > 0

def test_execute_and_download(tmp_path, monkeypatch):
    import redact_gov.api.app as app_module
    
    # Patch output dir to temp
    monkeypatch.setattr(app_module.settings, "OUTPUT_DIR", tmp_path)
    
    # Set up mock pipeline
    class MockPipeline:
        def execute_plan(self, input_pdf, plan, output_pdf, certificate_pdf):
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
    
    # Execute
    exec_resp = client.post(f"/api/documents/{doc_id}/execute")
    assert exec_resp.status_code == 200
    
    # Download sanitized
    dl_resp = client.get(f"/api/documents/{doc_id}/download")
    assert dl_resp.status_code == 200
    assert dl_resp.content == b"%PDF-1.4 output"
    
    # Download cert
    cert_resp = client.get(f"/api/documents/{doc_id}/certificate")
    assert cert_resp.status_code == 200
    assert cert_resp.content == b"%PDF-1.4 cert"
