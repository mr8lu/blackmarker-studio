# AI Blackmarker (RedactGov): Project Execution & Commercialization Blueprint

**Product Name:** AI Blackmarker (Codename: RedactGov)  
**Core Mission:** Sovereign, air-gapped FOIA/VFOIA document redaction and statutory compliance engine powered by on-device Small Language Models (Google Gemma 4 E4B), interactive Manual Blackmarker marquee drawing, and surgical PDF stream sanitization.  
**Primary Target Sponsor:** Virginia Innovation Partnership Corporation (VIPC) - Commonwealth Commercialization Fund (CCF) Launch Grant ($50,000) & Virginia Venture Partners (VVP).

---

## 1. Executive Summary & Core Hypothesis

Virginia local governments, school divisions, and municipal law enforcement agencies operate under a strict statutory mandate (Va. Code § 2.2-3700 et seq.) requiring public records release within five business days. Existing enterprise redaction suites carry prohibitive five-figure licensing hurdles and cloud data exfiltration risks. Conversely, manual redaction using rudimentary desktop tools invites catastrophic data leaks through incomplete layer sanitization (such as drawing black rectangles over text while leaving underlying text glyphs intact in the PDF byte stream).

AI Blackmarker bridges this gap with an air-gapped, zero-cloud desktop/server application. By uniting deterministic pattern matching, a locally hosted open-weight Google Gemma model (Google Gemma 4 E4B / 9B via llama.cpp with Apple Metal and CPU acceleration), interactive Manual Blackmarker marquee drawing, and low-level PDF stream surgery via PikePDF, AI Blackmarker automates 95% of pre-redaction chores while empowering human reviewers to draw custom redactions that surgically excise underlying PDF glyphs. Crucially, it maps withheld information directly to Virginia statutory exemptions, generating legally binding audit logs in seconds without exposing Criminal Justice Information Services (CJIS) or FERPA-governed data to commercial cloud APIs.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI Blackmarker System Flow                        │
├─────────────────────┬─────────────────────────────────┬─────────────────────┤
│   Ingest & Parse    │  AI + Manual Blackmarker Plan   │  Surgical Scrubbing │
│                     │                                 │                     │
│  Scanned / Digital  │  Deterministic Regex + Presidio │  PikePDF Content    │
│  PDF Documents      │                +                │  Stream Deletion    │
│         │           │  Gemma 4 E4B + Manual Marquee   │         +           │
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
- **PDF Extraction & Geometry Engine:** `pdfplumber` and `pypdf` for digital-native text streams and character-level bounding boxes; native visual rasterizer (rendering high-DPI page pixmaps via `pypdf`/`pikepdf`) for scanned image inputs.
- **Inference Runtime:** `llama-cpp-python` executing quantized GGUF weights of **Google Gemma 4 E4B** (Q4_K_M base model + `mmproj` multimodal vision projector, ~2.6 GB VRAM footprint) directly on local CPU / Apple Metal / NVIDIA hardware with zero external network connectivity.
- **Sanitization & Burn-In Engine:** `pikepdf` (backed by the C++ QPDF engine) for deterministic content stream modification, font glyph excision (`Tj` and `TJ` operator rewriting), opaque vector polygon burning, and complete XMP/piece-info metadata eradication.
- **Tabular Data & Audit Optimization:** Polars DataFrame engine for high-velocity aggregation and parsing of redaction logs, token boundaries, and compliance certificates.

### The Hybrid Inference Pipeline

1. **Tier 1 (Deterministic Fast Path - Sub-second):**
   - High-confidence regex and algorithmic validators targeting formatted PII: Social Security Numbers (SSNs), Virginia Driver's License numbers (1 letter + 8 digits), credit card tokens, standard phone formats, and dates of birth.
   - Algorithmic checks (Luhn validation, state license checksums).
   - Instant bounding box generation for verbatim matches.

2. **Tier 2 (Cognitive Context & Multimodal Vision Path - Google Gemma 4 E4B):**
   - **Dual-Modal Selective Architecture:**
     - *Text Ingestion Mode (Digital-Native):* High-speed batch text ingestion (~0.1-0.3s/page) using constrained JSON grammar outputs (BNF / JSON Schema enforcement).
     - *Native Vision Mode (Scans & Images):* For flattened scans (<20 digital text characters), handwritten margin notes, signatures, official seals, or crime scene / aerial photos, the engine invokes Gemma 4 E4B's native vision projector (`mmproj-gemma-4-e4b.gguf`) to visually parse and localize sensitive entities without requiring external OCR C-dependencies.
   - Deep classification of protected Virginia statutory legal categories:
     - **Juvenile Identifiers (Va. Code § 16.1-301):** Names, ages, grade levels, juvenile court docket markers, and youth shelter identifiers.
     - **Victim / Witness Safeguards (Va. Code § 19.2-11.2):** Domestic abuse victim descriptors, non-public addresses, protective order details, and 911 caller identities.
     - **Undercover Personnel & Informants (Va. Code § 2.2-3705.2):** Operational unit tags, confidential informant monikers, undercover officer identities, and tactical codes.
     - **Personnel & Privacy Exemptions (Va. Code § 2.2-3705.1):** Personal contact info of non-official individuals, medical data, banking/financial accounts.
     - **Handwritten Signatures & Visual PII:** Direct visual localization of handwritten signatures, private citizen fingerprints, or sensitive photographs.
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

---

## 7. Beta Release Gap Analysis & Commercialization Strategy

### 7.1 Beta Technical Gap Matrix

| Module / Capability | Current State | Beta Target | Priority | Status / Path |
| :--- | :--- | :--- | :--- | :--- |
| **Multimodal Vision & Scanned Records** | Digital-native only (`pdfplumber`) | Gemma 4 E4B Native Vision (`mmproj`) | **P0 (Blocker)** | Activate Gemma 4 E4B vision projector on image-only pages (<20 chars), signatures, and handwritten notes. |
| **Human-in-the-Loop UI** | Headless FastAPI + Typer CLI | Visual PDF.js review interface | **P0 (Blocker)** | Lightweight canvas overlay to approve, modify, or add redaction boxes. |
| **Air-Gapped Packaging** | CLI via `uv run` | Single-click desktop / Docker bundle | **P1 (Critical)** | Package via Tauri desktop shell (.dmg/.msi) and offline `docker-compose`. |
| **Async Processing Queue** | Synchronous in-memory | Chunked background processing | **P1 (Critical)** | Stream large docs (100-500+ pages) without HTTP timeout or OOM. |
| **Model Distribution** | Standalone HF download script | Pre-bundled quantized weights | **P2 (Operational)** | Pre-package `gemma-4-e4b-it-Q4_K_M.gguf` + `mmproj` in installer. |

### 7.2 Air-Gapped Model Architecture (No Download Scripts in Production)
- **Firewall & Air-Gap Compliance:** Municipal and law enforcement networks block outbound connections to Hugging Face. The application installer must co-locate quantized GGUF weights directly in `./models/`:
  - `gemma-4-e4b-it-Q4_K_M.gguf`: Base language model (~2.2 GB).
  - `mmproj-gemma-4-e4b-f16.gguf`: Vision projector module (~400 MB) for native image/scan parsing.
- **Dual-Modal Performance Optimization:**
  - Standard digital text streams bypass the vision projector completely to maintain sub-second speed (~0.1-0.3s/page).
  - Scanned pages, flattened faxes, and visual form boxes activate the vision projector (~2-4s/page), extracting entities and handwritten signatures directly into the unified Virginia FOIA coordinate pipeline.
- **Gated Model Mitigation:** Avoids requiring county staff to manage Hugging Face user tokens (`HF_TOKEN`) or accept individual cloud licenses.
- **Deterministic Fallback:** When model weights are absent or loading fails, `ContextualGemmaEngine` automatically degrades to high-precision heuristic rule extraction without interrupting the user.

### 7.3 Commercialization & Virginia Market Rollout

1. **VPPA Micro-Purchase Fast-Track:**
   - Standard RFP Threshold in Virginia: Procurements over $50,000 require multi-month competitive bidding.
   - Micro-Purchase Exemption (**Va. Code § 2.2-4303(G)**): Purchases under $10,000 can be authorized immediately via Departmental Purchasing Cards (P-Cards).
   - Commercial Pricing Tiers:
     - **Workstation Edition:** $4,900 / year (single clerk seat, unlimited processing).
     - **Department Edition:** $9,500 / year (5 seats, local intranet deployment).
     - **County Enterprise:** $24,500 / year (unlimited intranet seats, multi-department audit logs).

2. **VIPC CCF Grant Submission Roadmap:**
   - Target 3 Virginia counties (e.g., Campbell, Bedford, Pittsylvania) for zero-cost 60-day air-gapped pilot deployments.
   - Secure 2 Letters of Intent (LOIs) from participating clerks to accompany the $50,000 grant application.
   - Secure formal Legal Opinion Letter validating PikePDF low-level stream excision against statutory public disclosure standards.

