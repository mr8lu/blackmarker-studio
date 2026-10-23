<p align="center">
  <img src="assets/icon/icon_512.png" width="136" height="136" alt="AI Blackmarker App Icon" />
</p>

<h1 align="center">AI Blackmarker</h1>

<p align="center">
  <strong>Sovereign, air-gapped FOIA/VFOIA document redaction and statutory compliance engine powered by on-device Google Gemma 4 E4B, interactive Manual Blackmarker marquee drawing, and surgical PikePDF stream sanitization.</strong>
</p>

<p align="center">
  <a href="https://www.virginiaipc.org"><img src="https://img.shields.io/badge/Grant_Target-VIPC_CCF_$50k-blue.svg" alt="Target Sponsor" /></a>
  <a href="https://law.lis.virginia.gov/vacode/title2.2/chapter37/"><img src="https://img.shields.io/badge/Statute-Va._Code_§_2.2--3700-green.svg" alt="Statutory Framework" /></a>
  <a href="https://ai.google.dev/gemma"><img src="https://img.shields.io/badge/SLM-Google_Gemma_4_E4B-red.svg" alt="Inference Engine" /></a>
  <a href="https://pikepdf.readthedocs.io/"><img src="https://img.shields.io/badge/Sanitizer-PikePDF_QPDF-orange.svg" alt="Sanitization Engine" /></a>
  <a href="https://docs.astral.sh/uv/"><img src="https://img.shields.io/badge/Env-Python_3.12+_uv-purple.svg" alt="Environment" /></a>
</p>

---

## Overview

Virginia local governments, school divisions, and municipal law enforcement agencies operate under a strict mandate (**Va. Code § 2.2-3700**) requiring public records disclosure within five business days. 

Standard cloud redaction tools risk exfiltrating CJIS and FERPA data to external servers, while manual desktop redaction (such as black shapes placed on top of text layers) frequently results in catastrophic leaks because the underlying text glyphs remain copyable in the PDF byte stream.

**AI Blackmarker** (formerly *RedactGov*) provides a completely sovereign, air-gapped solution:
1. **Zero-Cloud Local Inference:** Powered by quantized **Google Gemma 4 E4B** running locally on Apple Metal / CPU via `llama.cpp`. No data ever leaves the local device.
2. **Deterministic Fast Path:** Real-time regex and checksum validators for Virginia Driver's Licenses (1 letter + 8 digits), SSNs, DOBs, phone numbers, and financial tokens.
3. **Interactive Manual Blackmarker Drawing:** In addition to automatic AI & deterministic detection, reviewers can toggle **Manual Blackmarker** (or hold **Shift + Drag** directly on any PDF page) to draw custom redaction boxes over missed text, signatures, or badges. AI Blackmarker automatically resolves all underlying PDF word tokens inside the drawn box and excises their glyphs from the PDF content stream alongside an opaque vector rectangle.
4. **Statutory Exemption Tagging:** Automatically maps both AI-detected and manually drawn redactions to specific Virginia Code sections (e.g., Va. Code § 16.1-301 for Juveniles, Va. Code § 19.2-11.2 for Victims/Witnesses, Va. Code § 2.2-3706 for Law Enforcement).
5. **PikePDF Content Stream Surgery:** Excises glyph operators (`Tj`, `TJ`) directly from PDF content streams, burns opaque black bounding boxes onto the base canvas, and strips all XMP metadata and piece-info trees.
6. **Virginia FOIA Redaction Certificate:** Generates a verifiable, auditable legal certificate detailing every withheld item with statutory justification.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI Blackmarker System Flow                        │
├─────────────────────┬─────────────────────────────────┬─────────────────────┤
│   Ingest & Parse    │  AI + Manual Blackmarker Plan   │  Surgical Scrubbing │
│                     │                                 │                     │
│  Scanned / Digital  │  Tier 1 Regex + Tier 2 Gemma 4  │  PikePDF Content    │
│  PDF Documents      │                +                │  Stream Deletion    │
│         │           │   Interactive Manual Marquee    │         +           │
│         ▼           │                │                │  XMP Metadata Wipe  │
│  Spatial Geometry   │                ▼                │         │           │
│  Token Coordinates  │   Va. Code Exemption Classifier │         ▼           │
│  (x0, y0, x1, y1)   │   (Juvenile, Informant, PII)    │  Sanitized PDF +    │
│                     │                                 │  Audit Certificate  │
└─────────────────────┴─────────────────────────────────┴─────────────────────┘
```

---

## Quickstart

### Prerequisites
- Python 3.12+
- `uv` package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh` or `brew install uv`)

### 1. Installation & Environment Setup

```bash
cd redact-gov
uv sync
```

### 2. Generate Synthetic Test Documents

Generate three realistic Virginia public records documents (police incident narrative, school board disciplinary hearing, and municipal rezoning dispute):

```bash
uv run python scripts/generate_synthetic_pdfs.py
```

### 3. Run the Phase 0 Sanitization Spike

Verify that sensitive tokens are purged from both visual rendering and raw underlying PDF byte streams:

```bash
uv run python scripts/run_spike.py
```

### 4. Build & Launch the Native macOS Utility (`AI Blackmarker.app`)

AI Blackmarker ships a zero-Xcode-project Swift Package Manager macOS application (`build/AI Blackmarker.app`) with an Apple HIG superellipse icon (`assets/icon/AppIcon.icns`) paired with an ephemeral stdio JSON-RPC helper (`Contents/Helpers/redactgov-worker`):

- **Menu Bar Quick-Scrub Droplet (`MenuBarExtra`):** Drag and drop any PDF onto the macOS status bar highlighter icon to scrub glyphs, wipe XMP metadata, and generate a Virginia FOIA Redaction Certificate on the spot.
- **Interactive Manual Blackmarker Canvas:** Click **Draw Redaction** in the toolbar (or hold **Shift + Drag** anywhere on the PDF page) to draw a live cyan-rimmed Blackmarker marquee box. Pick the applicable Virginia Code statute directly from the canvas bar; AI Blackmarker extracts the underlying PDF text inside the drawn rectangle and performs full `pikepdf` stream glyph excision upon sanitization.
- **Ephemeral Worker Lifecycle (0 MB Idle VRAM):** The native SwiftUI shell spawns `redactgov-worker` on demand over stdio pipes and automatically unloads **Google Gemma 4 E4B** after inactivity (or via the one-click **Free RAM** button) so the menu bar utility uses near-zero unified memory while idle.
- **Native `PDFKit` + Apple `Vision` Neural OCR (`VNRecognizeTextRequest`):** Digital pages use fast stream extraction, while flattened or scanned pages (< 40 characters) run through the Apple Neural Engine in `RedactGovKit` to recover exact bottom-left PDF point bounding boxes (`x0, y0, x1, y1`).
- **SQLite FOIA Docket Memory Index:** Automatically indexes every sanitized document, withheld entity, and statutory citation in a local WAL-mode SQLite database (`foia_docket_index.sqlite3`) for instant cross-docket search.

```bash
# Generate Apple HIG AppIcon.icns, compile SwiftUI app, and assemble build/AI Blackmarker.app
./build.sh

# Run the headless native bundle + worker self-test
"./build/AI Blackmarker.app/Contents/MacOS/RedactGovApp" --self-test

# Launch the native macOS AI Blackmarker Studio + Menu Bar app
open "build/AI Blackmarker.app"
```

### 5. Run Automated Test Suite

```bash
uv run pytest
```

---

## CLI Usage

```bash
# Redact a document deterministically + with Google Gemma 4 E4B
uv run aiblackmarker redact input.pdf --output redacted.pdf --cert certificate.pdf

# Inspect and audit bounding boxes without writing modifications
uv run aiblackmarker audit input.pdf

# Run the ephemeral stdio JSON-RPC worker used by AI Blackmarker.app
uv run aiblackmarker worker --idle-timeout 180

# Launch local FastAPI service for Human-in-the-Loop web review (also supports Shift+Drag manual redaction)
uv run aiblackmarker serve --port 8000
```

---

## Virginia Statutory Mapping

| Statute | Category | Exemption Description |
| :--- | :--- | :--- |
| **Va. Code § 2.2-3705.1(1)** | Personnel Records | Personal records of public employees |
| **Va. Code § 2.2-3705.1(10)** | Personal Privacy / PII | SSNs, personal contact info, bank accounts |
| **Va. Code § 2.2-3705.2(1)** | Law Enforcement Tactical | Undercover officer IDs, tactical plans, tactical logs |
| **Va. Code § 2.2-3705.4(1)** | Scholastic Records | Student disciplinary records, transcripts, FERPA data |
| **Va. Code § 16.1-301** | Juvenile Records | Child/juvenile identifiers in law-enforcement records |
| **Va. Code § 19.2-11.2** | Victim & Witness Protection | Names, addresses, and phone numbers of victims/witnesses |

---

## Commercialization & Grant Target

Targeting the **Virginia Innovation Partnership Corporation (VIPC) Commonwealth Commercialization Fund (CCF) Launch Grant ($50,000)** and follow-on capital from **Virginia Venture Partners (VVP)**.

Tailored for direct municipal procurement under the **Virginia Public Procurement Act (VPPA)** small-purchase exemption threshold (<$10,000 P-Card signoff without RFP).

See [BLUEPRINT.md](BLUEPRINT.md) for the full commercialization and engineering roadmap.
