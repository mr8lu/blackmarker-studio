# RedactGov 🛡️

> **Sovereign, air-gapped FOIA/VFOIA document redaction and statutory compliance engine powered by on-device Google Gemma 4 E4B and surgical PDF stream sanitization.**

[![Target Sponsor](https://img.shields.io/badge/Grant_Target-VIPC_CCF_$50k-blue.svg)](https://www.virginiaipc.org)
[![Statutory Framework](https://img.shields.io/badge/Statute-Va._Code_§_2.2--3700-green.svg)](https://law.lis.virginia.gov/vacode/title2.2/chapter37/)
[![Inference Engine](https://img.shields.io/badge/SLM-Google_Gemma_4_E4B-red.svg)](https://ai.google.dev/gemma)
[![Sanitization Engine](https://img.shields.io/badge/Sanitizer-PikePDF_QPDF-orange.svg)](https://pikepdf.readthedocs.io/)
[![Environment](https://img.shields.io/badge/Env-Python_3.12+_uv-purple.svg)](https://docs.astral.sh/uv/)

---

## Overview

Virginia local governments, school divisions, and municipal law enforcement agencies operate under a strict mandate (**Va. Code § 2.2-3700**) requiring public records disclosure within five business days. 

Standard cloud redaction tools risk exfiltrating CJIS and FERPA data to external servers, while manual desktop redaction (such as black shapes placed on top of text layers) frequently results in catastrophic leaks because the underlying text glyphs remain copyable in the PDF byte stream.

**RedactGov** provides a completely sovereign, air-gapped solution:
1. **Zero-Cloud Local Inference:** Powered by quantized **Google Gemma 4 E4B** running locally on Apple Metal / CPU via `llama.cpp`. No data ever leaves the local device.
2. **Deterministic Fast Path:** Real-time regex and checksum validators for Virginia Driver's Licenses (1 letter + 8 digits), SSNs, DOBs, phone numbers, and financial tokens.
3. **Statutory Exemption Tagging:** Automatically maps redacted tokens to specific Virginia Code sections (e.g., Va. Code § 16.1-301 for Juveniles, Va. Code § 19.2-11.2 for Victims/Witnesses).
4. **PikePDF Content Stream Surgery:** Excises glyph operators (`Tj`, `TJ`) directly from PDF content streams, burns opaque black bounding boxes onto the base canvas, and strips all XMP metadata and piece-info trees.
5. **Virginia FOIA Redaction Certificate:** Generates a verifiable, auditable legal certificate detailing every withheld item with statutory justification.

---

## System Architecture

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

### 4. Run Automated Test Suite

```bash
uv run pytest
```

---

## CLI Usage

```bash
# Redact a document deterministically + with Google Gemma 4 E4B
uv run redactgov redact input.pdf --output redacted.pdf --cert certificate.pdf

# Inspect and audit bounding boxes without writing modifications
uv run redactgov audit input.pdf

# Run local benchmark comparing token parsing latency
uv run redactgov benchmark

# Launch local FastAPI service for Human-in-the-Loop web review
uv run redactgov serve --port 8000
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
