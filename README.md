<p align="center">
  <img src="assets/icon/icon_512.png" width="136" height="136" alt="AI Blackmarker App Icon" />
</p>

<h1 align="center">AI Blackmarker</h1>

<p align="center">
  <strong>Sovereign, air-gapped multi-sector document redaction & compliance engine (FOIA, HIPAA, PCI DSS, GLBA, FRCP 5.2, AICPA SOC 2) with a-la-carte PII / PHI / PPI selection, powered by on-device Google Gemma 4 E4B, interactive Manual Blackmarker marquee drawing, and surgical PikePDF stream sanitization.</strong>
</p>

<p align="center">
  <a href="#supported-compliance-frameworks--profiles"><img src="https://img.shields.io/badge/Compliance-FOIA_•_HIPAA_•_PCI_DSS_•_GLBA_•_FRCP_5.2-blue.svg" alt="Compliance Frameworks" /></a>
  <a href="#a-la-carte-data-domain-selection-pii--phi--ppi"><img src="https://img.shields.io/badge/Domains-PII_•_PHI_•_PPI-teal.svg" alt="Data Domains" /></a>
  <a href="https://ai.google.dev/gemma"><img src="https://img.shields.io/badge/SLM-Google_Gemma_4_E4B-red.svg" alt="Inference Engine" /></a>
  <a href="https://pikepdf.readthedocs.io/"><img src="https://img.shields.io/badge/Sanitizer-PikePDF_QPDF-orange.svg" alt="Sanitization Engine" /></a>
  <a href="https://docs.astral.sh/uv/"><img src="https://img.shields.io/badge/Env-Python_3.12+_uv-purple.svg" alt="Environment" /></a>
</p>

---

## Overview

Government agencies (Federal, State, and Local), hospital systems, financial institutions, law firms, and enterprise compliance teams must sanitize sensitive PDFs before public disclosure, litigation production, clinical de-identification, or audit archival.

Standard cloud redaction services risk exfiltrating regulated **PII**, **PHI**, and **PPI** to third-party servers, while manual desktop redaction (such as black shapes placed on top of text layers) frequently results in catastrophic leaks because the underlying text glyphs remain copyable in the PDF byte stream.

**AI Blackmarker** provides a 100% sovereign, air-gapped solution across public and private sectors:
1. **Multi-Sector Compliance Profiles:** Built-in regulatory profiles for **Public FOIA** (5 U.S.C. § 552 & State Public Records), **HIPAA Safe Harbor** (45 CFR § 164.514(b)), **PCI DSS v4.0** (Req. 3.3 / 3.4), **GLBA Safeguards** (16 CFR Part 314), **Judicial Filings** (Fed. R. Civ. P. 5.2), **AICPA SOC 2** (TSC CC6.1 / P4.2), **Law Enforcement / CJIS**, and **Environmental Review**.
2. **A-La-Carte Data Domain Selection (`PII` • `PHI` • `PPI`):** Toggle **Personal Identifiable Information (PII)**, **Protected Health Information (PHI)**, and **Payment & Personal Financial Information (PPI)** independently or in any combination.
3. **Zero-Cloud Local Inference:** Powered by quantized **Google Gemma 4 E4B** running locally on Apple Metal / CPU via `llama.cpp`. No data ever leaves the local device.
4. **Deterministic Fast Path (Tier 1):** Sub-second regex and algorithmic checksum validators for SSNs, Driver's Licenses, Passports, Phones, Emails, Medical Record Numbers (MRNs), NPIs, ICD-10 diagnosis codes, Health Plan / Medicare IDs, Luhn-validated Credit/Debit PANs, Mod-10 ABA Routing Numbers, Bank Account numbers, and IBAN/SWIFT codes.
5. **Interactive Manual Blackmarker Drawing:** Toggle **Manual Blackmarker** (or hold **Shift + Drag** directly on any PDF page) to draw custom redaction boxes over missed text, signatures, or badges. AI Blackmarker automatically resolves all underlying PDF word tokens inside the drawn box and excises their glyphs from the PDF content stream alongside an opaque vector rectangle.
6. **Customizable Redaction & Compliance Certificates:** Generate verifiable PDF audit certificates tailored to your organization - choose from built-in presets (*General Compliance*, *Public Records / FOIA*, *Healthcare HIPAA Safe Harbor*, *Banking & Payment PCI DSS / GLBA*, *Judicial Filing FRCP 5.2*, *Enterprise AICPA SOC 2*) or customize the Header Banner, Organization/Hospital/Bank Name, Certifying Officer, and Legal Attestation text.

---

## Supported Compliance Frameworks & Profiles

| Profile Key | Sector / Mandate | Default Domains | Primary Regulatory Citations |
| :--- | :--- | :--- | :--- |
| `public_foia` | Federal, State & Local Public Records | `PII`, `PHI`, `PPI` | 5 U.S.C. § 552(b)(6)/(7)(C), State FOIA (incl. Va. Code § 2.2-3705.1) |
| `hipaa` | Healthcare & Clinical De-Identification | `PII`, `PHI` | HIPAA Safe Harbor - 45 CFR § 164.514(b)(2) (18 Identifiers) |
| `pci_dss` | Payment Card Industry & Merchant Audit | `PPI`, `PII` | PCI DSS v4.0 Req. 3.3 & 3.4 (PAN, CVV/CVC, Track Data) |
| `glba` | Banking & Financial Institutions | `PPI`, `PII` | Gramm-Leach-Bliley Act (15 U.S.C. § 6801 / 16 CFR Part 314) |
| `frcp_5_2` | Federal & State Court E-Filings | `PII`, `PPI` | Fed. R. Civ. P. 5.2(a) & Fed. R. Crim. P. 49.1 |
| `aicpa_soc2` | Private Sector & Enterprise Audit | `PII`, `PHI`, `PPI` | AICPA Trust Services Criteria CC6.1 / P4.2 & NIST SP 800-122 |
| `strict_privacy` | Maximum Multi-Domain Sanitization | `PII`, `PHI`, `PPI` | NIST SP 800-88 Rev. 1 & Cross-Sector Privacy Mandates |
| `law_enforcement` | Criminal Justice & Tactical Records | `PII`, `PHI` | 5 U.S.C. § 552(b)(7), CJIS Security Policy, Victim/Witness Protection |
| `environmental_review` | Environmental & Critical Habitat | `PII` | 16 U.S.C. § 1533 (ESA) & State Natural Heritage Exemptions |

---

## A-La-Carte Data Domain Selection (`PII` • `PHI` • `PPI`)

Users can select a compliance profile **or** mix-and-match individual data domains a-la-carte in the native macOS Studio, Web HITL Reviewer, or CLI (`--domains PII,PHI,PPI`):

- **`PII` (Personal Identifiable Information):** Social Security Numbers (SSNs), Driver's Licenses & State IDs, Passport Numbers, Dates of Birth, Phone Numbers, Email Addresses, Residential Addresses, Juvenile Identifiers, Crime Victims/Witnesses, Law Enforcement Tactical Personnel, and Sensitive GPS Coordinates.
- **`PHI` (Protected Health Information - HIPAA 45 CFR § 164.514):** Medical Record Numbers (MRNs), National Provider Identifiers (NPIs), Health Plan Beneficiary / Policy / Medicare IDs, ICD-10 Clinical Diagnosis Codes, and Clinical / Psychiatric Treatment Notes.
- **`PPI` (Payment & Personal Financial Information - PCI DSS / GLBA):** Luhn-validated Credit/Debit Card PANs, Card Security Codes (CVV/CVC/PIN), Mod-10 validated ABA Routing Numbers, Checking/Savings/Wire Bank Account Numbers, and IBAN / SWIFT BIC Identifiers.

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

### 2. Build & Launch the Native macOS Utility (`AI Blackmarker.app`)

AI Blackmarker ships a zero-Xcode-project Swift Package Manager macOS application (`build/AI Blackmarker.app`) with an Apple HIG superellipse icon (`assets/icon/AppIcon.icns`) paired with an ephemeral stdio JSON-RPC helper (`Contents/Helpers/redactgov-worker`):

- **Menu Bar Quick-Scrub Droplet (`MenuBarExtra`):** Select any compliance profile (`FOIA`, `HIPAA`, `PCI DSS`, `GLBA`, `FRCP 5.2`, `SOC 2`), toggle `PII` / `PHI` / `PPI` pills, and drag-and-drop any PDF onto the macOS status bar highlighter icon.
- **Interactive Manual Blackmarker Canvas:** Click **Draw Redaction** in the toolbar (or hold **Shift + Drag** anywhere on the PDF page) to draw a live cyan-rimmed Blackmarker marquee box and tag it with Federal FOIA, HIPAA, PCI DSS, GLBA, FRCP 5.2, SOC 2, or State statutory citations.
- **Customizable Certificate Template Sheet:** Click **Certificate Template** in the toolbar or sidebar to pick an industry preset or customize the Jurisdiction/Sector Banner, Framework Subtitle, Certificate Title, Organization/Hospital/Bank Name, and Legal Attestation statement.
- **Ephemeral Worker Lifecycle (0 MB Idle VRAM):** Spawns `redactgov-worker` on demand over stdio pipes and automatically unloads **Google Gemma 4 E4B** after inactivity.

```bash
# Generate Apple HIG AppIcon.icns, compile SwiftUI app, and assemble build/AI Blackmarker.app
./build.sh

# Run the headless native bundle + worker self-test
"./build/AI Blackmarker.app/Contents/MacOS/RedactGovApp" --self-test

# Launch the native macOS AI Blackmarker Studio + Menu Bar app
open "build/AI Blackmarker.app"
```

### 3. CLI Usage

```bash
# Redact a healthcare record under HIPAA Safe Harbor (PII + PHI) with a HIPAA certificate preset
uv run aiblackmarker redact clinical_note.pdf \
  --profile hipaa \
  --domains PII,PHI \
  --cert-preset hipaa_healthcare \
  --agency "St. Mary Health System"

# Redact a financial wire statement for PPI only (PCI DSS & GLBA)
uv run aiblackmarker redact wire_statement.pdf \
  --profile pci_dss \
  --domains PPI \
  --cert-preset banking_glba_pci \
  --agency "First National Bank Compliance"

# List all supported regulatory citations & certificate presets
uv run aiblackmarker statutes

# Launch local FastAPI service for Human-in-the-Loop web review
uv run aiblackmarker serve --port 8000
```

### 4. Run Automated Test Suite

```bash
uv run pytest
```
