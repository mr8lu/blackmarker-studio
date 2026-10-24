"""FastAPI local service for Blackmarker Studio Human-in-the-Loop review interface."""

import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from redact_gov.config import settings
from redact_gov.core.models import (
    CERTIFICATE_PRESETS,
    CertificateConfig,
    RedactionPlan,
    get_certificate_preset,
)
from redact_gov.core.statutes import list_statutes
from redact_gov.pipeline import RedactionPipeline

app = FastAPI(
    title="Blackmarker Studio Sovereign Redaction API",
    description="Local on-device API for air-gapped FOIA, HIPAA, PCI DSS, GLBA, FRCP 5.2 & AICPA redaction and customizable compliance certificates.",
    version="0.4.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

pipeline = RedactionPipeline()
DOC_STORE: Dict[str, Path] = {}
PLAN_STORE: Dict[str, RedactionPlan] = {}
CERT_CONFIG_STORE: Dict[str, CertificateConfig] = {
    "default": get_certificate_preset("generic_compliance")
}


class ReplanRequest(BaseModel):
    profile: str = "public_foia"
    enabled_domains: List[str] = ["PII", "PHI", "PPI"]
    coordinate_policy: Optional[str] = None


class ExecuteRequest(BaseModel):
    include_certificate: bool = False
    certificate_config: Optional[CertificateConfig] = None
    agency_name: Optional[str] = None
    reviewer_name: Optional[str] = None


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
        "supported_domains": ["PII", "PHI", "PPI"],
        "supported_profiles": [
            "public_foia",
            "strict_privacy",
            "hipaa",
            "pci_dss",
            "glba",
            "frcp_5_2",
            "aicpa_soc2",
            "environmental_review",
            "law_enforcement",
        ],
    }


@app.get("/api/statutes")
def get_supported_statutes():
    return list_statutes()


@app.get("/api/certificate/presets")
def get_certificate_presets():
    return {
        "presets": {k: v.model_dump() for k, v in CERTIFICATE_PRESETS.items()},
        "active": CERT_CONFIG_STORE["default"].model_dump(),
    }


@app.post("/api/certificate/config")
def update_certificate_config(config: CertificateConfig):
    CERT_CONFIG_STORE["default"] = config
    return {"status": "success", "config": config.model_dump()}


@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    profile: str = Form("public_foia"),
    domains: str = Form("PII,PHI,PPI"),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    doc_id = str(uuid.uuid4())[:8]
    doc_path = settings.OUTPUT_DIR / f"upload_{doc_id}_{file.filename}"

    with doc_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    DOC_STORE[doc_id] = doc_path

    enabled_domains = [
        d.strip().upper()
        for d in domains.split(",")
        if d.strip().upper() in ("PII", "PHI", "PPI")
    ] or ["PII", "PHI", "PPI"]

    plan = pipeline.create_plan(
        doc_path,
        profile=profile,
        enabled_domains=enabled_domains,
    )
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


@app.post("/api/documents/{doc_id}/replan")
def replan_document(doc_id: str, req: ReplanRequest):
    if doc_id not in DOC_STORE:
        raise HTTPException(status_code=404, detail="Document not found.")
    doc_path = DOC_STORE[doc_id]
    existing_plan = PLAN_STORE.get(doc_id)
    manual_entities = [
        e for e in (existing_plan.entities if existing_plan else [])
        if e.tier == "manual_blackmarker"
    ]
    new_plan = pipeline.create_plan(
        doc_path,
        profile=req.profile,
        enabled_domains=req.enabled_domains,
        coordinate_policy=req.coordinate_policy,
    )
    new_plan.entities.extend(manual_entities)
    PLAN_STORE[doc_id] = new_plan
    return {
        "status": "success",
        "entities_detected": len(new_plan.entities),
        "plan": new_plan,
    }


@app.post("/api/documents/{doc_id}/execute")
def execute_redaction(
    doc_id: str,
    req: Optional[ExecuteRequest] = Body(default=None),
):
    if doc_id not in DOC_STORE or doc_id not in PLAN_STORE:
        raise HTTPException(status_code=404, detail="Document not found.")

    input_path = DOC_STORE[doc_id]
    plan = PLAN_STORE[doc_id]
    output_path = settings.OUTPUT_DIR / f"sanitized_{input_path.name}"
    include_cert = bool(req.include_certificate) if req else False
    cert_path = (
        settings.OUTPUT_DIR / f"certificate_{input_path.stem}.pdf"
        if include_cert
        else None
    )

    cert_cfg = (
        req.certificate_config
        if (req and req.certificate_config)
        else CERT_CONFIG_STORE.get("default")
    )

    result = pipeline.execute_plan(
        input_pdf=input_path,
        plan=plan,
        output_pdf=output_path,
        certificate_pdf=cert_path,
        agency_name=req.agency_name if req else None,
        reviewer_name=req.reviewer_name if req else None,
        certificate_config=cert_cfg,
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
    if not cert_path.is_file() and doc_id in PLAN_STORE:
        cert_cfg = CERT_CONFIG_STORE.get("default")
        if hasattr(pipeline, "certificate_generator"):
            pipeline.certificate_generator.generate_certificate(
                document_name=input_path.name,
                entities=PLAN_STORE[doc_id].entities,
                output_path=cert_path,
                certificate_config=cert_cfg,
            )
        else:
            output_path = settings.OUTPUT_DIR / f"sanitized_{input_path.name}"
            pipeline.execute_plan(
                input_pdf=input_path,
                plan=PLAN_STORE[doc_id],
                output_pdf=output_path,
                certificate_pdf=cert_path,
                certificate_config=cert_cfg,
            )
    if not cert_path.is_file():
        raise HTTPException(status_code=404, detail="Certificate PDF not yet generated.")

    return FileResponse(cert_path, media_type="application/pdf", filename=cert_path.name)
