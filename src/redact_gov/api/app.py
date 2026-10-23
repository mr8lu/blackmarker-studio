"""FastAPI local service for RedactGov Human-in-the-Loop review interface."""

import shutil
import uuid
from pathlib import Path
from typing import Dict, List
from fastapi import FastAPI, File, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from redact_gov.config import settings
from redact_gov.core.models import RedactionPlan, RedactionResult
from redact_gov.core.statutes import list_statutes
from redact_gov.pipeline import RedactionPipeline

app = FastAPI(
    title="AI Blackmarker Sovereign Redaction API",
    description="Local on-device API for air-gapped FOIA redaction, manual Blackmarker drawing, and Virginia compliance.",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static folder
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

pipeline = RedactionPipeline()
DOC_STORE: Dict[str, Path] = {}
PLAN_STORE: Dict[str, RedactionPlan] = {}

@app.get("/")
def get_ui():
    index_path = static_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_text())
    return HTMLResponse("<h1>UI not found. Please create static/index.html</h1>")


@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "mode": "sovereign_air_gapped",
        "engine": "Google Gemma 4 E4B + PikePDF",
    }


@app.get("/api/statutes")
def get_supported_statutes():
    return list_statutes()


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    doc_id = str(uuid.uuid4())[:8]
    doc_path = settings.OUTPUT_DIR / f"upload_{doc_id}_{file.filename}"
    
    with doc_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    DOC_STORE[doc_id] = doc_path
    
    # Generate initial plan
    plan = pipeline.create_plan(doc_path)
    PLAN_STORE[doc_id] = plan

    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "total_pages": plan.total_pages,
        "entities_detected": len(plan.entities),
        "plan": plan,
    }


@app.get("/api/documents/{doc_id}/plan")
def get_plan(doc_id: str):
    if doc_id not in PLAN_STORE:
        raise HTTPException(status_code=404, detail="Document not found.")
    return PLAN_STORE[doc_id]


@app.post("/api/documents/{doc_id}/plan")
def update_plan(doc_id: str, plan: RedactionPlan):
    if doc_id not in PLAN_STORE:
        raise HTTPException(status_code=404, detail="Document not found.")
    PLAN_STORE[doc_id] = plan
    return {"status": "success", "plan": PLAN_STORE[doc_id]}


@app.post("/api/documents/{doc_id}/execute")
def execute_redaction(doc_id: str):
    if doc_id not in DOC_STORE or doc_id not in PLAN_STORE:
        raise HTTPException(status_code=404, detail="Document not found.")

    input_path = DOC_STORE[doc_id]
    plan = PLAN_STORE[doc_id]
    output_path = settings.OUTPUT_DIR / f"sanitized_{input_path.name}"
    cert_path = settings.OUTPUT_DIR / f"certificate_{input_path.stem}.pdf"

    result = pipeline.execute_plan(
        input_pdf=input_path,
        plan=plan,
        output_pdf=output_path,
        certificate_pdf=cert_path,
    )
    return result


@app.get("/api/documents/{doc_id}/download")
def download_sanitized_pdf(doc_id: str):
    if doc_id not in DOC_STORE:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    input_path = DOC_STORE[doc_id]
    output_path = settings.OUTPUT_DIR / f"sanitized_{input_path.name}"
    if not output_path.is_file():
        raise HTTPException(status_code=404, detail="Sanitized PDF not yet generated.")

    return FileResponse(output_path, media_type="application/pdf", filename=output_path.name)


@app.get("/api/documents/{doc_id}/certificate")
def download_certificate_pdf(doc_id: str):
    if doc_id not in DOC_STORE:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    input_path = DOC_STORE[doc_id]
    cert_path = settings.OUTPUT_DIR / f"certificate_{input_path.stem}.pdf"
    if not cert_path.is_file():
        raise HTTPException(status_code=404, detail="Certificate PDF not yet generated.")

    return FileResponse(cert_path, media_type="application/pdf", filename=cert_path.name)
