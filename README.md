<p align="center">
  <img src="assets/icon/icon_512.png" width="140" height="140" alt="Blackmarker Studio App Icon" />
</p>

<h1 align="center">Blackmarker Studio</h1>

<p align="center">
  <strong>Erase private secrets from PDFs forever so nobody can copy-paste them back.</strong><br />
  Blackmarker Studio permanently scrubs names, Social Security Numbers, medical records, and bank accounts from PDF files on your Mac - 100% offline with zero internet required.
</p>

<p align="center">
  <a href="#cross-platform--multi-os-roadmap"><img src="https://img.shields.io/badge/Platform-macOS_14+_(Windows_%26_Linux_v0.5.0)-0F172A.svg" alt="Platform: macOS 14+ today, Windows and Linux planned in v0.5.0" /></a>
  <a href="#architecture"><img src="https://img.shields.io/badge/AI-100%25_Offline_%E2%80%A2_Google_Gemma_4_E4B-1E3A8A.svg" alt="AI: 100% Offline Google Gemma 4 E4B" /></a>
  <a href="https://docs.astral.sh/uv/"><img src="https://img.shields.io/badge/Runtime-Python_3.12+_%E2%80%A2_uv-4C1D95.svg" alt="Runtime: Python 3.12+ and uv" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-14532D.svg" alt="License: MIT" /></a>
</p>

<p align="center">
  <a href="#get-started-in-1-step">Get Started</a> •
  <a href="#how-it-works-1---2---3">How It Works</a> •
  <a href="#why-blackmarker-studio-the-sharpie-trap">Why It Matters</a> •
  <a href="#native-macos-studio--manual-blackmarker">macOS Studio</a> •
  <a href="#supported-compliance-frameworks">Compliance &amp; CLI</a> •
  <a href="SECURITY.md">Security</a>
</p>

---

## Get Started in 1 Step

### Option A: Install the macOS App (Recommended)

```bash
brew tap mr8lu/tap
brew install --cask mr8lu/tap/blackmarker-studio
```

### Option B: Run or Build from Source (`uv` + SwiftPM)

```bash
# 1. Clone the repository and install dependencies in an isolated .venv
git clone https://github.com/mr8lu/blackmarker-studio.git
cd blackmarker-studio
uv sync --reinstall

# 2. Generate synthetic demo PDFs into ./data/synthetic_corpus/
uv run python scripts/generate_synthetic_pdfs.py

# 3. Build and launch the native macOS app
./build.sh && open "build/Blackmarker Studio.app"
```

<details>
<summary><strong>Prerequisites &amp; Optional On-Device Google Gemma 4 E4B Setup</strong></summary>

#### Prerequisites

1. **Python 3.12 or newer**
2. **`uv` package manager** (for deterministic dependency and virtual environment management):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # OR
   brew install uv
   ```
3. **macOS 14.0+ (Sonoma or newer) & Xcode Command Line Tools** *(required only when compiling the native SwiftUI `Blackmarker Studio.app`)*:
   ```bash
   xcode-select --install
   ```

#### Optional: Enable Local Google Gemma 4 E4B Neural Inference

Blackmarker Studio works out of the box with its sub-second deterministic and heuristic engines. To enable full Tier 2 contextual AI with **Google Gemma 4 E4B** (`llama-cpp-python` with Apple Metal / CPU acceleration):

```bash
# Install optional llama-cpp-python bindings
uv sync --extra llm

# Download quantized Gemma 4 E4B GGUF weights into ./models/ for offline operation
uv run python scripts/download_gemma.py
```

</details>

---

## How It Works (1 - 2 - 3)

| Step | What You Do | What Happens Under the Hood |
| :--- | :--- | :--- |
| **1. Drop Your PDF** | Drag any PDF into the macOS menu bar icon or the studio window. | Repairs broken fonts, reads digital text or scanned pages via Apple `Vision` OCR, and maps every word's exact position. |
| **2. Review or Draw Boxes** | Let on-device AI highlight secrets (`PII`, `PHI`, `PPI`) automatically, or hold **`Shift + Drag`** to draw a black marker box over anything else. | Matches SSNs, medical IDs, bank accounts, and juvenile/witness names locally with zero internet connection. |
| **3. Save Clean PDF** | Click **Redact PDF** to save `<name>_sanitized.pdf` (and click **Add Certificate** only when you need a legal audit log). | Surgically cuts the hidden letters (`Tj`/`TJ` glyphs) and metadata out of the file via PikePDF/QPDF and verifies zero secret bytes remain. |

---

## Why Blackmarker Studio? (The Sharpie Trap)

Every year, government agencies, hospitals, banks, and law firms suffer preventable data leaks from a simple mistake: **drawing a black rectangle over sensitive text in a basic PDF viewer and clicking "Save."**

Think of a PDF file like a glass transparency sheet on an overhead projector. Putting a strip of black tape on the top glass hides the words on the wall, but the letters underneath are still sitting right there in the file. Anyone who opens that PDF can drag their mouse over the black box, press `Cmd+C`, and paste the "hidden" Social Security Number, patient diagnosis, or bank account number into a text file. Worse, uploading private PDFs to cloud redaction websites sends your secrets to someone else's server before redaction even starts.

**Blackmarker Studio** fixes both problems by running **100% offline on your Mac** and **cutting the underlying letters out of the PDF file forever**:

| Capability | Cloud Redaction APIs | Basic PDF Viewers ("Black Box") | **Blackmarker Studio** |
| :--- | :---: | :---: | :---: |
| **Where Your Files Stay** | Uploaded to third-party cloud | On your computer | **100% Offline / Air-Gapped on Your Mac** |
| **Hidden PDF Letters (`Tj`/`TJ`)** | Varies by vendor | Left intact underneath black boxes | **Cut out of the file forever via PikePDF/QPDF** |
| **Hidden File Metadata (`XMP`/`/Info`)** | Often preserved | Preserved | **Completely wiped clean** |
| **Smart Context AI (Names, Notes)** | Cloud LLM (privacy risk) | None (manual eye scan) | **On-Device Google Gemma 4 E4B (Metal / CPU)** |
| **Manual Blackmarker (`Shift + Drag`)** | Draws a picture on top | Draws a picture on top | **Snaps to words & deletes the hidden letters** |
| **Post-Save Safety Check** | None | None | **Automatic byte-level check proves secrets are gone** |
| **Legal Audit Certificates** | Generic logs | None | **Optional Statutory & Compliance PDF Certificates** |

---

## Native macOS Studio & Manual Blackmarker

Blackmarker Studio includes a native SwiftUI macOS application (`build/Blackmarker Studio.app`) with an Apple Human Interface Guidelines superellipse icon (`assets/icon/AppIcon.icns`) and an on-demand background helper (`Contents/Helpers/redactgov-worker`).

- **Menu Bar Quick-Scrub Droplet (`MenuBarExtra`):** Click the highlighter icon in the macOS menu bar, pick a compliance preset (`FOIA`, `HIPAA`, `PCI DSS`, `GLBA`, `FRCP 5.2`, `SOC 2`), toggle `PII` / `PHI` / `PPI` pills, and drop PDFs for instant one-step scrubbing.
- **Interactive Manual Blackmarker (`Shift + Drag`):** Click **Draw Redaction** in the toolbar - or hold **`Shift + Drag`** anywhere on the PDF page - to draw a live cyan-rimmed Blackmarker box over signatures, badges, or extra text.
  - Automatically snaps to and selects all underlying PDF word tokens inside your box.
  - Lets you pick any FOIA, HIPAA, PCI DSS, GLBA, FRCP 5.2, or SOC 2 citation code.
  - Permanently removes both the visual area and the underlying PDF text bytes when saved.
- **Redact First, Certify on Demand:** Clicking **Redact PDF** outputs a clean `<name>_sanitized.pdf` with zero extra file clutter. Need a formal legal log? Toggle **Include Certificate (Optional)** or click **Add Certificate** after redacting.
- **Privacy-Safe File History:** The sidebar's **File History** remembers only file names and page numbers on disk, never saves redacted secret words in SQLite, and automatically cleans up deleted files.

---

## Supported Compliance Frameworks

Pick a ready-made compliance preset to automatically set legal citations, coordinate rules, public-official allowlists, and certificate headers:

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

### A-La-Carte Data Domains (`PII` • `PHI` • `PPI`)

Mix and match individual data domains in the macOS Studio, Web Reviewer, or CLI (`--domains PII,PHI,PPI`):

- **`PII` (Personal Identifiable Information):** Social Security Numbers (SSNs), Driver's Licenses, Passports, Dates of Birth, Phone Numbers, Emails, Street Addresses, Juveniles, Victims & Witnesses, Tactical Personnel, and Sensitive GPS Coordinates.
- **`PHI` (Protected Health Information - HIPAA):** Medical Record Numbers (MRNs), National Provider Identifiers (NPIs), Health Plan / Medicare IDs, ICD-10 Diagnosis Codes, and Clinical / Psychiatric Notes.
- **`PPI` (Payment & Financial Information - PCI DSS / GLBA):** Luhn-checked Credit & Debit Card Numbers (PANs), CVV/CVC/PIN codes, Mod-10 ABA Routing Numbers, Bank Account Numbers, and IBAN / SWIFT Identifiers.

---

## CLI & Web Studio Reference

Blackmarker Studio installs the `blackmarker` and `blackmarker-studio` CLI commands (plus legacy aliases `aiblackmarker` and `redactgov`).

```bash
# 1. Redact a PDF under HIPAA Safe Harbor (PII + PHI) with a formal compliance certificate
uv run blackmarker redact clinical_note.pdf \
  --output clinical_note_redacted.pdf \
  --cert clinical_note_certificate.pdf \
  --profile hipaa \
  --domains PII,PHI

# 2. Dry-run audit in terminal (inspect detected secrets & legal citations without modifying the PDF)
uv run blackmarker audit incident_report.pdf --profile public-foia --domains PII,PHI,PPI

# 3. Launch the local browser-based Human-in-the-Loop Web Studio (bound to 127.0.0.1)
uv run blackmarker serve --host 127.0.0.1 --port 8000
```

<details>
<summary><strong>Advanced CLI Commands, Certificate Presets &amp; Custom Organization Branding</strong></summary>

### Certificate Presets (`--cert-preset`)

When generating an optional **Compliance & Redaction Certificate PDF** (powered by Polars and ReportLab), choose any built-in preset or customize the organization headers:

- `generic_compliance` - Multi-Sector PII / PHI / PPI Sanitization Certificate
- `public_foia` - Federal & State Freedom of Information Act Exemption Log
- `hipaa_healthcare` - HIPAA Safe Harbor De-Identification Certificate (45 CFR § 164.514(b))
- `banking_glba_pci` - Financial Privacy & PCI DSS v4.0 Sanitization Attestation
- `judicial_frcp` - Federal Rule of Civil Procedure 5.2 Privacy Compliance Certificate
- `enterprise_aicpa` - AICPA SOC 2 (CC6.1 / P4.2) Data Sanitization Audit Record

```bash
# Redact a bank wire statement (PPI only) with custom bank & officer attestation
uv run blackmarker redact wire_statement.pdf \
  --output wire_sanitized.pdf \
  --cert wire_audit_cert.pdf \
  --profile pci-dss \
  --domains PPI \
  --cert-preset banking_glba_pci \
  --agency "First National Bank Compliance" \
  --reviewer "Chief Risk Officer"

# Inspect the built-in statutory registry, role allowlists, or malformed PDF fonts
uv run blackmarker statutes
uv run blackmarker criteria
uv run blackmarker inspect malformed_scan.pdf
```

</details>

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                             BLACKMARKER STUDIO PIPELINE                             │
├───────────────────────────┬─────────────────────────────┬───────────────────────────┤
│    1. Ingest & Geometry   │  2. Hybrid AI + Manual Plan │  3. Surgical Sanitization │
│                           │                             │                           │
│  Digital / Scanned PDF    │  Tier 1: Sub-Second Regex   │  PikePDF / QPDF Engine    │
│  + Auto Font Repair       │  (SSN, PAN, NPI, ABA, DOB)  │  • Excise Tj/TJ Glyphs    │
│             │             │              +              │  • Burn Vector Rectangles │
│             ▼             │  Tier 2: Google Gemma 4 E4B │  • Strip XMP & /Info      │
│  pdfplumber + Apple       │  (Constrained JSON Grammar) │             │             │
│  Vision Neural OCR        │              +              │             ▼             │
│             │             │  Manual Blackmarker Marquee │  Zero-Residual Byte Audit │
│             ▼             │  (Shift + Drag Token Snap)  │             │             │
│  Token Bounding Boxes     │              │              │             ▼             │
│  (x0, y0, x1, y1)         │              ▼              │  Sanitized PDF + Custom   │
│  + Form Prompt Context    │  PII • PHI • PPI Classifier │  Compliance Certificate   │
└───────────────────────────┴─────────────────────────────┴───────────────────────────┘
```

<details>
<summary><strong>Under the Hood: 5-Stage Engine Architecture</strong></summary>

1. **Document Healing & Spatial Geometry (`redact_gov.core.normalizer` & `geometry`):** Automatically repairs malformed PDF font descriptors (`FontBBox=None`), extracts exact point-coordinate bounding boxes `(x0, y0, x1, y1)`, and pairs with Apple `Vision` (`VNRecognizeTextRequest`) neural OCR on macOS for flattened scans.
2. **Tier 1 Deterministic Fast Path (`redact_gov.engines.deterministic`):** Sub-second regex and algorithmic checksum validators (Luhn PAN validation, Mod-10 ABA routing verification, NPI/MRN/ICD-10 patterns, SSN/DL/Passport rules) with context-aware form prompt evaluation.
3. **Tier 2 Cognitive & Multimodal Vision Engine (`redact_gov.engines.contextual`):** Runs quantized **Google Gemma 4 E4B** locally via `llama.cpp` (Apple Metal GPU and CPU acceleration) with GBNF grammar enforcement to identify nuanced entities: juvenile names, crime victims, confidential informants, psychiatric notes, and public-official allowlists.
4. **Ephemeral Worker Lifecycle (`redact_gov.worker`):** The native macOS Studio communicates with an on-demand JSON-RPC stdio worker (`blackmarker worker`) that automatically unloads Gemma 4 E4B after idle timeout, maintaining **0 MB idle VRAM** when not actively scanning.
5. **Surgical PikePDF Stream Sanitization (`redact_gov.engines.sanitization`):** Parses uncompressed PDF page content streams, removes matching `Tj` and `TJ` text-showing operators inside target bounding boxes, burns opaque vector rectangles, wipes `/Metadata` and `/Info` dictionaries, and runs a mandatory post-redaction verification check confirming zero residual substrings.

</details>

<details>
<summary><strong>Project Directory Structure</strong></summary>

```text
blackmarker-studio/
├── .github/                      # PR template, YAML Issue Forms & Discussion templates
├── Package.swift                 # SwiftPM manifest for native macOS app & RedactGovKit
├── build.sh                      # Builds AppIcon.icns, Swift release binary & Blackmarker Studio.app
├── pyproject.toml                # Python 3.12+ project metadata & CLI entrypoints (uv)
├── assets/icon/                  # Apple HIG superellipse icons (SVG, 512px, 1024px, AppIcon.icns)
├── scripts/                      # Gemma 4 E4B downloader, icon generator & synthetic PDF generator
├── Sources/
│   ├── RedactGovKit/             # Swift library: JSON-RPC WorkerClient, Vision OCR, SQLite store
│   └── RedactGovApp/             # SwiftUI macOS Studio, MenuBarExtra droplet & PDFKit canvas
├── src/redact_gov/
│   ├── cli.py                    # Typer CLI (blackmarker / blackmarker-studio)
│   ├── pipeline.py               # End-to-end hybrid planning & execution pipeline
│   ├── worker.py                 # Ephemeral stdio JSON-RPC worker with idle VRAM watchdog
│   ├── api/                      # Local FastAPI server & interactive Web HITL Studio UI
│   ├── certificates/             # Polars + ReportLab Compliance Certificate PDF generator
│   ├── core/                     # Pydantic models, statutes, criteria, geometry & normalizer
│   └── engines/                  # Tier 1 deterministic, Tier 2 Gemma 4 E4B & PikePDF sanitizer
└── tests/                        # Automated pytest suite (stream excision, OCR, API, statutes)
```

</details>

---

## Cross-Platform & Multi-OS Roadmap

| Operating System | Status | Desktop App & Tray Droplet | Core CLI, PikePDF Sanitizer & Local Gemma 4 AI |
| :--- | :--- | :--- | :--- |
| **macOS 14+ (Apple Silicon & Intel)** | **Built & Verified Today (`v0.4.1`)** | Native SwiftUI `Blackmarker Studio.app` + `MenuBarExtra` | Verified (`Apple Metal` / CPU + Apple `Vision` OCR) |
| **Windows 10 / 11 (x64 & ARM64)** | **Planned (`v0.5.0` Roadmap)** | Planned `.exe` / `.msi` (`WebView2` / `Tauri v2` + Tray) | Planned `v0.5.0` Verification (CPU / CUDA / Vulkan + `RapidOCR`) |
| **Linux & Docker (Ubuntu / RHEL / WSL2)** | **Planned (`v0.5.0` Roadmap)** | Planned `.AppImage` / `.deb` / `.rpm` (`WebKitGTK` + Tray) | Planned `v0.5.0` Verification (CPU / CUDA / ROCm + `--network=none` OCI) |

<details>
<summary><strong>Detailed Multi-OS Engine Matrix &amp; v0.5.0 / v0.6.0 Milestones</strong></summary>

### Layer-by-Layer Multi-OS Matrix

| Layer / Capability | macOS 14+ (`v0.4.1` Today) | Windows 10 / 11 (`v0.5.0` Planned) | Linux & Docker (`v0.5.0` Planned) |
| :--- | :--- | :--- | :--- |
| **PikePDF / QPDF Stream Sanitizer** | Built & Verified | Portable Python / QPDF | Portable Python / QPDF |
| **Spatial Geometry & Polars Audit** | Built & Verified | Portable Python / Rust | Portable Python / Rust |
| **Tier 1 Regex & Checksum Engine** | Built & Verified | Portable Python | Portable Python |
| **Tier 2 Google Gemma 4 E4B** | Apple Metal / CPU | CPU / CUDA / Vulkan | CPU / CUDA / ROCm / Vulkan |
| **Scanned PDF Neural OCR** | Apple `Vision` + Gemma 4 Vision | Local ONNX (`RapidOCR`) + Gemma 4 | Local ONNX (`RapidOCR`) + Gemma 4 |
| **Desktop Shell & System Tray** | SwiftUI + `PDFKit` + `MenuBarExtra` | `WebView2` / `Tauri v2` + `pystray` | `WebKitGTK` + System Tray |

### Release Milestones

- **`v0.4.1` (Current Release - macOS 14+ Verified):**
  - Native SwiftUI desktop studio (`Blackmarker Studio.app`), `PDFKit` annotation canvas, Apple `Vision` (`VNRecognizeTextRequest`) neural OCR, `MenuBarExtra` status bar droplet, `blackmarker` CLI, and local Web HITL Studio (`blackmarker serve`).
- **`v0.5.0` (Planned Roadmap - Windows, Linux & Finder Quick Actions):**
  - **macOS Finder Right-Click Quick Action:** Instant right-click PDF redaction directly in Finder with profile selection (`PII`, `PHI`, `PPI`).
  - **Public vs. Private Sector Policy Presets:** Streamlined separation between **Public Sector** (FOIA, victim names, law enforcement) and **Private Sector** (Banking, Healthcare & Lifesciences) workflows.
  - **Windows 10/11 & Linux Packaging:** Standalone desktop installers (`.exe`/`.msi` and `.AppImage`/`.deb`/`.rpm`), air-gapped Docker container (`--network=none`), local ONNX Runtime (`RapidOCR`) for scanned PDFs, and automated GitHub Actions CI matrix across `macos-latest`, `windows-latest`, and `ubuntu-latest`.
- **`v0.6.0` (Planned Roadmap - Global & State Regulatory Packs):**
  - Pluggable policy packs for **GDPR** (EU), **CCPA / CPRA** (California), **FERPA** (Education), **CJIS Security Policy v6.0**, and 50-state FOIA statutory registries.

</details>

---

## Running the Test Suite

```bash
# 1. Run the Python pytest suite (70+ unit, integration, and zero-residual byte tests)
uv run pytest

# 2. Run the native macOS Swift package tests
swift test

# 3. Run the headless macOS app bundle + JSON-RPC worker self-test
"./build/Blackmarker Studio.app/Contents/MacOS/RedactGovApp" --self-test
```

---

## Contributing & Security

- **Contributing:** Pull requests for new compliance profiles, statutory mappings, deterministic validators, and Multi-OS packaging are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) and our [Code of Conduct](CODE_OF_CONDUCT.md).
- **Security & Sanitization Integrity:** Any issue where underlying PDF text bytes survive redaction is treated as a critical security vulnerability. See [SECURITY.md](SECURITY.md) for our air-gapped verification architecture and responsible disclosure policy.

---

## License

Released under the [MIT License](LICENSE). Copyright (c) 2026 Blackmarker Studio Contributors.
