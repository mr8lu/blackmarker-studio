# RedactGov: Project Execution & Commercialization Blueprint

**Project Codename:** RedactGov  
**Core Mission:** Sovereign, air-gapped FOIA/VFOIA document redaction and statutory compliance engine powered by on-device Small Language Models (Google Gemma 4 E4B) and surgical PDF stream sanitization.  
**Primary Target Sponsor:** Virginia Innovation Partnership Corporation (VIPC) - Commonwealth Commercialization Fund (CCF) Launch Grant ($50,000) & Virginia Venture Partners (VVP).

---

## 1. Executive Summary & Core Hypothesis

Virginia local governments, school divisions, and municipal law enforcement agencies operate under a strict statutory mandate (Va. Code § 2.2-3700 et seq.) requiring public records release within five business days. Existing enterprise redaction suites carry prohibitive five-figure licensing hurdles and cloud data exfiltration risks. Conversely, manual redaction using rudimentary desktop tools invites catastrophic data leaks through incomplete layer sanitization (such as drawing black rectangles over text while leaving underlying text glyphs intact in the PDF byte stream).

RedactGov bridges this gap with an air-gapped, zero-cloud desktop/server application. By uniting deterministic pattern matching, a locally hosted open-weight Google Gemma model (Google Gemma 4 E4B / 9B via llama.cpp with Apple Metal and CPU acceleration), and low-level PDF stream surgery via PikePDF, RedactGov automates 95% of pre-redaction chores. Crucially, it maps withheld information directly to Virginia statutory exemptions, generating legally binding audit logs in seconds without exposing Criminal Justice Information Services (CJIS) or FERPA-governed data to commercial cloud APIs.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             RedactGov System Flow                           │
├─────────────────────┬─────────────────────────────────┬─────────────────────┤
│   Ingest & Parse    │       Contextual Inference      │  Surgical Scrubbing │
│                     │                                 │                     │
│  Scanned / Digital  │  Deterministic Regex + Presidio │  PikePDF Content    │
│  PDF Documents      │                +                │  Stream Deletion    │
│         │           │      Quantized Google Gemma 4 E4B   │         +           │
│         ▼           │                │                │  XMP Metadata Wipe  │
│  Spatial Geometry   │                ▼                │         │           │
│  Token Coordinates  │   Va. Code Exemption Classifier │         ▼           │
│  (x0, y0, x1, y1)   │   (Juvenile, Informant, PII)    │  Sanitized PDF +    │
│                     │                                 │  Audit Certificate  │
└─────────────────────┴─────────────────────────────────┴─────────────────────┘
```

---

## 2. Technical Architecture Specification

### Core Processing Stack
- **Runtime Environment:** Python 3.12+ orchestrated via `uv`, packaged with a local Web GUI (FastAPI + React/PDF.js) or desktop shell (Tauri).
- **PDF Extraction & Geometry Engine:** `pdfplumber` and `pypdf` for digital-native text streams and exact character-level bounding box spatial geometry; integrated Tesseract OCR pipeline interface for legacy scanned image layers.
- **Inference Runtime:** `llama-cpp-python` executing quantized GGUF weights of **Google Gemma 4 E4B** (Q4_K_M, ~2.2 GB VRAM footprint; expandable to Gemma 2 9B for high-throughput county workstations) directly on local CPU / Apple Metal / NVIDIA hardware with zero external network connectivity.
- **Sanitization & Burn-In Engine:** `pikepdf` (backed by the C++ QPDF engine) for deterministic content stream modification, font glyph excision (`Tj` and `TJ` operator rewriting), opaque vector polygon burning, and complete XMP/piece-info metadata eradication.
- **Tabular Data & Audit Optimization:** Polars DataFrame engine for high-velocity aggregation and parsing of redaction logs, token boundaries, and compliance certificates.

### The Hybrid Inference Pipeline

1. **Tier 1 (Deterministic Fast Path - Sub-second):**
   - High-confidence regex and algorithmic validators targeting formatted PII: Social Security Numbers (SSNs), Virginia Driver's License numbers (1 letter + 8 digits), credit card tokens, standard phone formats, and dates of birth.
   - Algorithmic checks (Luhn validation, state license checksums).
   - Instant bounding box generation for verbatim matches.

2. **Tier 2 (Cognitive Context Path - Google Gemma 4 E4B):**
   - Batched paragraph ingestion into quantized Google Gemma 4 E4B using constrained JSON grammar outputs (BNF / JSON Schema enforcement).
   - Deep classification of protected Virginia statutory legal categories:
     - **Juvenile Identifiers (Va. Code § 16.1-301):** Names, ages, grade levels, juvenile court docket markers, and youth shelter identifiers.
     - **Victim / Witness Safeguards (Va. Code § 19.2-11.2):** Domestic abuse victim descriptors, non-public addresses, protective order details, and 911 caller identities.
     - **Undercover Personnel & Informants (Va. Code § 2.2-3705.2):** Operational unit tags, confidential informant monikers, undercover officer identities, and tactical codes.
     - **Personnel & Privacy Exemptions (Va. Code § 2.2-3705.1):** Personal contact info of non-official individuals, medical data, banking/financial accounts.
     - **Exclusion Heuristics:** Public figures, elected county supervisors, school board chairs, and official agency spokespersons are explicitly allowlisted from accidental redaction.

3. **Spatial Alignment & PikePDF Burn-In:**
   - **Coordinate Reconciliation:** Matching string token offsets returned by Google Gemma 4 E4B against raw geometric bounding boxes `(x0, y0, x1, y1)` extracted from the source PDF.
   - **Content Stream Parsing:** Decompressing page object streams, replacing matching glyph operators (`Tj`, `TJ`) with null spaces / dummy positions, superimposing opaque black raster/vector polygons directly on the canvas, and stripping `/Metadata` streams to preclude copy-paste and layer exfiltration.
   - **Post-Redaction Verification Spike:** Automated automated testing inspecting every token in the output binary to guarantee 0 string hits in both text extraction and uncompressed byte stream scans.

---

## 3. Virginia Statutory Exemption Mapping

RedactGov natively indexes and cites Virginia Code sections on every redaction:

| Statute Code | Short Title | Description & Redaction Policy |
| :--- | :--- | :--- |
| **Va. Code § 2.2-3705.1(1)** | Personnel Records | Personal identifying information of public employees held in personnel files. |
| **Va. Code § 2.2-3705.1(10)** | Personal Privacy / PII | Social Security Numbers, personal contact numbers, and private financial identifiers. |
| **Va. Code § 2.2-3705.2(1)** | Law Enforcement Tactical Info | Tactical plans, undercover operational identities, and sensitive deployment logs. |
| **Va. Code § 2.2-3705.4(1)** | Scholastic Records | Student disciplinary records, grade sheets, IEP files, and identifiable student data. |
| **Va. Code § 16.1-301** | Juvenile Law-Enforcement Records | Any record identifying a child or juvenile subject to law-enforcement investigation. |
| **Va. Code § 19.2-11.2** | Crime Victim & Witness Protection | Names, addresses, and phone numbers of victims and witnesses in criminal proceedings. |

---

## 4. Phased Implementation Roadmap

```
2026 Milestone Schedule
┌────────────────┬────────────────────────────────────────────────────────────┐
│ Phase 0        │ Architecture Spike & Sanitization Testbed                  │
│ Weeks 1 - 2    │ (PikePDF Burn-In Verification + Gemma 2 Prompt Prototype)  │
├────────────────┼────────────────────────────────────────────────────────────┤
│ Phase 1        │ Alpha Engine & Virginia Statute Mapping                    │
│ Weeks 3 - 5    │ (Gemma 2 Grammars, JSON Schemas, Spatial Geometry Align)   │
├────────────────┼────────────────────────────────────────────────────────────┤
│ Phase 2        │ Reviewer UI & Exemption Log Generator                      │
│ Weeks 6 - 8    │ (Human-in-the-Loop Web Interface + Audit Certificate)      │
├────────────────┼────────────────────────────────────────────────────────────┤
│ Phase 3        │ VIPC CCF Application & Municipal Pilot Setup              │
│ Weeks 9 - 11   │ (Grant Submission, 1-2 VA County Clerk Beta Trials)        │
├────────────────┼────────────────────────────────────────────────────────────┤
│ Phase 4        │ Production Hardening & Packaging                          │
│ Weeks 12 - 16  │ (Docker / Tauri Distributable, VPPA Micro-Purchase Launch) │
└────────────────┴────────────────────────────────────────────────────────────┘
```

### Phase 0: Core Sanitization & Inference Spike (Weeks 1 - 2)
- Validate complete glyph excision using PikePDF. Build automated verification tests ensuring string searches against the scrubbed PDF return zero hits.
- Benchmark local quantized Google Gemma 4 E4B inference latency and token output fidelity on Apple Metal / CPU across synthetic police blotters and county school board records.
- Exit Gate: Zero residual metadata in output binaries; 100% true burn-in without display artifacts.

### Phase 1: Contextual Inference & Geometry Engine (Weeks 3 - 5)
- Construct the spatial mapper translating Gemma 2 string matches back to PDF point coordinates.
- Implement structured output grammars using `llama-cpp-python` enforcing the standard schema (`verbatim_text`, `statutory_code`, `confidence`).
- Calibrate the prompt matrix against common Virginia legal exemptions.
- Exit Gate: Sub-10-second processing time for a typical 5-page public records document on standard commercial laptop hardware.

### Phase 2: Human-in-the-Loop Review Interface (Weeks 6 - 8)
- Build a lightweight local web interface using React and PDF.js connected to FastAPI.
- Feature set: Visual bounding box overlays color-coded by confidence, single-click approve/reject toggles, manual marquee box drawing, and batch redaction overrides.
- Export mechanism: Dual artifact production - (1) The sanitized PDF, and (2) The formal "Virginia FOIA Redaction Certificate" itemizing page numbers, timestamps, and statutory citations.
- Exit Gate: Complete document review workflow operational end-to-end.

### Phase 3: VIPC Commonwealth Commercialization Fund (CCF) Pitch (Weeks 9 - 11)
- Finalize the CCF Launch Grant application ($50,000 tier with 1:1 match).
- Target key regional partners: Engage Commonwealth Cyber Initiative (CCI) regional nodes (e.g., CCI Northern Virginia or Central Virginia Node) for technical endorsement.
- Secure 2 Letters of Intent (LOIs) from Virginia municipal stakeholders (such as a county clerk's office, school board administrative team, or regional law enforcement agency).
- Exit Gate: Formal submission of VIPC CCF application; active beta testing with pilot partners.

### Phase 4: Production Hardening & Commercial Release (Weeks 12 - 16)
- Package application as a turnkey Docker container (for municipal IT deployments) and an isolated desktop executable (via Tauri).
- Integrate non-destructive Tesseract OCR pipeline for degraded facsimile and scan inputs.
- Launch commercial small-tier licensing under Virginia Public Procurement Act micro-purchase thresholds.

---

## 5. Virginia Procurement & Go-to-Market Strategy

### The "Under-the-Radar" Procurement Model
- **Pricing Strategy:** $399/month per department seat or $4,500/year site licenses.
- **VPPA Micro-Purchase Alignment:** The Virginia Public Procurement Act allows individual municipal agencies and departments to procure commercial off-the-shelf software under $10,000 without competitive bidding, complex RFP generation, or multi-month committee approvals. Department heads can authorize transactions directly using procurement cards (P-Cards).
- **Target Customer Segments:**
  1. **Municipal Clerks & FOIA Coordinators:** 133 cities and counties throughout the Commonwealth.
  2. **Virginia School Boards:** Over 130 school divisions processing student disciplinary records, IEP disclosures, and parent FOIA filings.
  3. **Sheriff Offices & Town Police Departments:** Redacting incident narratives, dispatch recordings, and traffic stop reports for media inquiries.

---

## 6. VIPC Funding Alignment & Budget Plan

### Grant Allocation: VIPC CCF Launch Grant ($50,000)

| Category | Budget | Justification & Objectives |
| :--- | :--- | :--- |
| **Model Optimization & Tuning** | $18,000 | Quantization, synthetic Virginia FOIA training corpora creation, and Google Gemma 4 E4B prompt calibration for low-power endpoints. |
| **PDF Engineering & Security Audit** | $16,000 | Hardening the PikePDF stream sanitization pipeline, memory safety checks, and forensic byte extraction validation. |
| **Frontend & Packaging** | $10,000 | Local UI development, PDF.js spatial coordinate engine, and Tauri cross-platform compilation. |
| **Pilot Support & Legal Consultation** | $6,000 | Onboarding municipal beta partners in Virginia; review of statutory exemption tags with Virginia administrative law specialists. |

### Follow-On Trajectory: Virginia Venture Partners (VVP)
- **Milestone for Equity Funding:** 5 active municipal deployments across Virginia and $30k+ ARR within 9 months.
- **Vehicle:** Pitch for a $150,000 VVP Launch Note or $250,000 Pre-Seed Round to scale sales across the Mid-Atlantic state-and-local government (SLED) corridor.
