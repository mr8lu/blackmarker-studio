<p align="center">
  <img src="assets/icon/icon_512.png" width="140" height="140" alt="Blackmarker Studio App Icon" />
</p>

<h1 align="center">Blackmarker Studio - On-device FOIA, HIPAA, and financial PDF redactor</h1>

<p align="center">
  <strong>Sovereign, air-gapped multi-sector document redaction &amp; compliance studio (FOIA, HIPAA, PCI DSS, GLBA, FRCP 5.2, AICPA SOC 2) with a-la-carte PII / PHI / PPI selection, powered by on-device Google Gemma 4 E4B, interactive Manual Blackmarker marquee drawing, and surgical PikePDF stream excision.</strong>
</p>

<p align="center">
  <a href="#supported-compliance-frameworks"><img src="https://img.shields.io/badge/Compliance-FOIA_%E2%80%A2_HIPAA_%E2%80%A2_PCI_DSS_%E2%80%A2_GLBA_%E2%80%A2_FRCP_5.2-0A66C2.svg" alt="Compliance Frameworks" /></a>
  <a href="#a-la-carte-data-domain-selection-pii--phi--ppi"><img src="https://img.shields.io/badge/Domains-PII_%E2%80%A2_PHI_%E2%80%A2_PPI-008080.svg" alt="Data Domains" /></a>
  <a href="#cross-platform--multi-os-roadmap"><img src="https://img.shields.io/badge/Platform-macOS_14+_(Windows_%26_Linux_Roadmap)-1F2937.svg" alt="Supported Operating Systems" /></a>
  <a href="https://ai.google.dev/gemma"><img src="https://img.shields.io/badge/SLM-Google_Gemma_4_E4B-D93025.svg" alt="Inference Engine" /></a>
  <a href="https://pikepdf.readthedocs.io/"><img src="https://img.shields.io/badge/Sanitizer-PikePDF_QPDF-E37400.svg" alt="Sanitization Engine" /></a>
  <a href="https://docs.astral.sh/uv/"><img src="https://img.shields.io/badge/Env-Python_3.12+_uv-6B4FBB.svg" alt="Environment" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-2EA44F.svg" alt="MIT License" /></a>
</p>

<p align="center">
  <a href="#why-blackmarker-studio">Why Blackmarker Studio?</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#supported-compliance-frameworks">Compliance Frameworks</a> •
  <a href="#quickstart--installation">Quickstart</a> •
  <a href="#native-macos-studio--menu-bar-droplet">macOS Studio</a> •
  <a href="#cli--web-hitl-reference">CLI &amp; Web HITL</a> •
  <a href="#cross-platform--multi-os-roadmap">Multi-OS Roadmap</a> •
  <a href="CONTRIBUTING.md">Contributing</a> •
  <a href="SECURITY.md">Security</a>
</p>

---

## Why Blackmarker Studio?

### The "Sharpie Trap" vs. True PDF Stream Excision

Every year, government agencies, hospital networks, financial institutions, and law firms suffer catastrophic data breaches from a deceptively simple mistake: **drawing a black rectangle over sensitive text in a PDF viewer and clicking "Save."**

Think of a PDF file like a multi-layered glass transparency on an overhead projector. Placing a strip of black tape on the top glass layer hides the words from human eyes on the wall, yet the ink on the bottom sheet remains completely intact. Anyone who opens that PDF can drag their cursor across the black box, press `Cmd+C`, and paste the "redacted" Social Security Number, juvenile victim name, or wire routing number into a plain text editor. Worse still, uploading confidential records to commercial cloud redaction APIs violates strict data sovereignty, CJIS, and HIPAA boundaries before redaction even begins.

**Blackmarker Studio** eliminates both failure modes through **air-gapped on-device intelligence** and **surgical byte-level stream excision**:

| Capability | Cloud Redaction APIs | Basic PDF Viewers ("Black Box") | **Blackmarker Studio** |
| :--- | :---: | :---: | :---: |
| **Network Sovereignty** | Uploads docs to third-party cloud | Local | **100% Air-Gapped / Zero Egress** |
| **PDF Content Stream (`Tj`/`TJ`)** | Varies by vendor | Leaves underlying glyphs intact | **Surgically excises glyph bytes via PikePDF/QPDF** |
| **XMP & `/Info` Metadata** | Often preserved | Preserved | **Completely eradicated** |
| **Contextual AI (Juveniles, Witnesses, Clinical Notes)** | Cloud LLM (Exfiltration risk) | None (Manual eye scan) | **On-Device Google Gemma 4 E4B (Metal / CPU)** |
| **Manual Marquee Drawing (`Shift + Drag`)** | Visual overlay only | Visual overlay only | **Auto-resolves & excises underlying word tokens** |
| **Post-Redaction Byte Verification** | None | None | **Automated zero-residual byte stream audit** |
| **Audit & Legal Certificates** | Generic logs | None | **Customizable Statutory & Compliance PDF Certificates** |

---

## Architecture

Blackmarker Studio combines a two-tier hybrid detection engine with spatial token geometry, interactive human-in-the-loop (HITL) marquee tools, and low-level QPDF content stream surgery.

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

### Key Architectural Highlights
1. **Document Healing & Spatial Geometry (`redact_gov.core.normalizer` & `geometry`):** Automatically repairs malformed PDF font descriptors (`FontBBox=None`), extracts exact point-coordinate bounding boxes `(x0, y0, x1, y1)`, and pairs with Apple `Vision` (`VNRecognizeTextRequest`) neural OCR on macOS for flattened scans.
2. **Tier 1 Deterministic Fast Path (`redact_gov.engines.deterministic`):** Sub-second regex and algorithmic checksum validators (Luhn PAN validation, Mod-10 ABA routing verification, NPI/MRN/ICD-10 patterns, SSN/DL/Passport rules) with context-aware form prompt evaluation.
3. **Tier 2 Cognitive & Multimodal Vision Engine (`redact_gov.engines.contextual`):** Runs quantized **Google Gemma 4 E4B** locally via `llama.cpp` (Apple Metal GPU and CPU acceleration) with GBNF grammar enforcement to identify nuanced entities: juvenile names, crime victims, confidential informants, psychiatric notes, and public-official allowlists.
4. **Ephemeral Worker Lifecycle (`redact_gov.worker`):** The native macOS Studio communicates with an on-demand JSON-RPC stdio worker (`blackmarker worker`) that automatically unloads Gemma 4 E4B after idle timeout, maintaining **0 MB idle VRAM** when not actively scanning.
5. **Surgical PikePDF Stream Sanitization (`redact_gov.engines.sanitization`):** Parses uncompressed PDF page content streams, removes matching `Tj` and `TJ` text-showing operators inside target bounding boxes, burns opaque vector rectangles, wipes `/Metadata` and `/Info` dictionaries, and runs a mandatory post-redaction verification check confirming zero residual substrings.

---

## Supported Compliance Frameworks

Select a turnkey compliance profile to automatically configure statutory citations, coordinate policies, public-official allowlists, and certificate presets:

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

Need surgical control beyond a preset profile? Mix and match individual data domains in the macOS Studio, Web HITL Reviewer, or CLI (`--domains PII,PHI,PPI`):

- **`PII` (Personal Identifiable Information):**
  Social Security Numbers (SSNs), Driver's Licenses and State IDs, U.S. & International Passport Numbers, Dates of Birth, Telephone Numbers, Email Addresses, Residential Street Addresses, Juvenile Identifiers, Crime Victims & Witnesses, Undercover Tactical Personnel, and Sensitive GPS Coordinates.
- **`PHI` (Protected Health Information - HIPAA 45 CFR § 164.514):**
  Medical Record Numbers (MRNs), National Provider Identifiers (NPIs), Health Plan Beneficiary / Policy / Medicare IDs, ICD-10 Clinical Diagnosis Codes, and Clinical / Psychiatric Treatment Narratives.
- **`PPI` (Payment & Personal Financial Information - PCI DSS / GLBA):**
  Luhn-validated Credit & Debit Card Primary Account Numbers (PANs), Card Security Codes (CVV/CVC/PIN), Mod-10 validated ABA Routing Numbers, Checking / Savings / Wire Bank Account Numbers, and IBAN / SWIFT BIC Identifiers.

---

## Optional Compliance & Redaction Certificates (Redact First, Documentation Second)

By default, Blackmarker Studio prioritizes fast, clutter-free redaction (`<name>_sanitized.pdf` only). Whenever formal audit documentation is needed, you can toggle **Include Certificate (Optional)** before redacting or click **Add Certificate / Generate Certificate** on demand after redacting to emit a cryptographically hashed **Compliance & Redaction Certificate PDF** powered by Polars and ReportLab:

- **Built-in Certificate Presets (`--cert-preset`):**
  - `generic_compliance` - Multi-Sector PII / PHI / PPI Sanitization Certificate
  - `public_foia` - Federal & State Freedom of Information Act Exemption Log
  - `hipaa_healthcare` - HIPAA Safe Harbor De-Identification Certificate (45 CFR § 164.514(b))
  - `banking_glba_pci` - Financial Privacy & PCI DSS v4.0 Sanitization Attestation
  - `judicial_frcp` - Federal Rule of Civil Procedure 5.2 Privacy Compliance Certificate
  - `enterprise_aicpa` - AICPA SOC 2 (CC6.1 / P4.2) Data Sanitization Audit Record
- **Custom Organization Branding:** Override the Jurisdiction / Sector Header Banner, Framework Subtitle, Certificate Title, Organization / Hospital / Bank Name (`--agency`), Certifying Officer (`--reviewer`), and Legal Attestation Clause.

---

## Quickstart & Installation

### Option A: Install via Homebrew (macOS 14+ App Bundle)

```bash
brew tap mr8lu/tap
brew install --cask mr8lu/tap/blackmarker-studio
```

### Option B: Build from Source (`uv` + SwiftPM)

#### Prerequisites

Ensure the following tools are installed on your workstation:

1. **Python 3.12 or newer**
2. **`uv` package manager** (required for deterministic dependency and virtual environment management):
   ```bash
   # Install via standalone installer or Homebrew
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # OR
   brew install uv
   ```
3. **macOS 14.0+ (Sonoma or newer) & Xcode Command Line Tools** *(required only if building the native SwiftUI `Blackmarker Studio.app`)*:
   ```bash
   xcode-select --install
   ```

### Step 1: Clone & Synchronize Environment

```bash
git clone https://github.com/mr8lu/blackmarker-studio.git
cd blackmarker-studio
# (Or if cloned as ai-blackmarker: cd ai-blackmarker)

# Create isolated .venv and install all core dependencies via uv
uv sync --reinstall

# Generate synthetic test & demo PDFs into ./data/synthetic_corpus/ (untracked in git; also auto-generated on first run)
uv run python scripts/generate_synthetic_pdfs.py
```

### Step 2: Optional On-Device Google Gemma 4 E4B Setup

Blackmarker Studio works out of the box using its high-precision deterministic and heuristic engines. To enable full Tier 2 neural inference with **Google Gemma 4 E4B** (`llama-cpp-python` with Apple Metal / CPU acceleration):

```bash
# Install optional llama-cpp-python bindings
uv sync --extra llm

# Download quantized Gemma 4 E4B GGUF weights into ./models/ for air-gapped operation
uv run python scripts/download_gemma.py
```

---

## Native macOS Studio & Menu Bar Droplet

Blackmarker Studio ships a zero-Xcode-project Swift Package Manager macOS application (`build/Blackmarker Studio.app`) featuring an Apple Human Interface Guidelines superellipse icon (`assets/icon/AppIcon.icns`) and an embedded stdio JSON-RPC helper (`Contents/Helpers/redactgov-worker`).

### Building & Launching `Blackmarker Studio.app`

```bash
# 1. Generate Apple HIG AppIcon.icns, compile Release SwiftUI binary, and assemble app bundle
./build.sh

# 2. Run the automated headless bundle + JSON-RPC worker self-test
"./build/Blackmarker Studio.app/Contents/MacOS/RedactGovApp" --self-test

# 3. Launch Blackmarker Studio
open "build/Blackmarker Studio.app"
```

### Studio Workflow & Manual Blackmarker (`Shift + Drag`)

- **Menu Bar Quick-Scrub Droplet (`MenuBarExtra`):** Click the highlighter icon in the macOS status bar, pick any compliance profile (`FOIA`, `HIPAA`, `PCI DSS`, `GLBA`, `FRCP 5.2`, `SOC 2`), toggle `PII` / `PHI` / `PPI` domain pills, and drag-and-drop PDFs for instant one-step sanitization.
- **Interactive Manual Blackmarker (`Shift + Drag`):** Click **Draw Redaction** in the studio toolbar - or hold **Shift + Drag** directly across any region of the PDF canvas - to draw a live cyan-rimmed Blackmarker marquee box over missed text, signatures, or badges.
  - Blackmarker Studio automatically snaps to and resolves all underlying PDF word tokens inside your drawn rectangle.
  - Assign any FOIA, HIPAA, PCI DSS, GLBA, FRCP 5.2, or SOC 2 citation code to the manual box.
  - Upon export, both the visual area and the underlying PDF content stream glyphs are permanently excised.
- **Redact First, Certify on Demand:** Click **Redact PDF** to immediately excise sensitive bytes without extra file clutter, or click **Add Certificate** / **Certificate Options** to generate a customized compliance certificate after redacting.
- **Privacy-Safe File History:** The sidebar's **File History** tracks only existing sanitized PDFs on disk (`document_name` and `page_number`), never stores raw redacted text in SQLite, and automatically prunes deleted files.

---

## CLI & Web HITL Reference

Blackmarker Studio installs the primary `blackmarker` and `blackmarker-studio` CLI commands (alongside legacy aliases `aiblackmarker` and `redactgov`).

### 1. `blackmarker redact` - Sanitize PDF & Emit Certificate

```bash
# Redact a clinical record under HIPAA Safe Harbor (PII + PHI) with a formal certificate
uv run blackmarker redact clinical_note.pdf \
  --output clinical_note_redacted.pdf \
  --cert clinical_note_certificate.pdf \
  --profile hipaa \
  --domains PII,PHI \
  --cert-preset hipaa_healthcare \
  --agency "St. Mary Health System" \
  --reviewer "Chief Privacy Officer"

# Redact a wire transfer statement for Payment & Financial data only (PPI)
uv run blackmarker redact wire_statement.pdf \
  --output wire_sanitized.pdf \
  --cert wire_audit_cert.pdf \
  --profile pci-dss \
  --domains PPI \
  --cert-preset banking_glba_pci \
  --agency "First National Bank Compliance"

# Redact a public records request while preserving non-sensitive coordinates
uv run blackmarker redact environmental_permit.pdf \
  --profile environmental-review \
  --coordinate-policy sensitive-only
```

### 2. `blackmarker audit` - Dry-Run Entity & Citation Inspection

Inspect all detected `PII`, `PHI`, and `PPI` entities, bounding box counts, form context labels, and statutory citations in your terminal without modifying the source PDF:

```bash
uv run blackmarker audit incident_report.pdf --profile public-foia --domains PII,PHI,PPI
```

### 3. `blackmarker statutes`, `criteria`, & `inspect`

```bash
# Display the full multi-sector statutory & regulatory citation registry
uv run blackmarker statutes

# Inspect centralized role allowlists, form field rules, and coordinate policies
uv run blackmarker criteria

# Diagnose a PDF for broken font descriptors (FontBBox=None) or structural anomalies
uv run blackmarker inspect malformed_scan.pdf
```

### 4. `blackmarker serve` - Local Human-in-the-Loop Web Studio

Launch the air-gapped FastAPI + interactive Web HITL Reviewer (bound strictly to `127.0.0.1` by default):

```bash
uv run blackmarker serve --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` in your browser to upload PDFs, toggle `PII` / `PHI` / `PPI` domains, draw manual redaction boxes on the HTML5 canvas, customize certificate templates, and download sanitized packages.

---

## Cross-Platform & Multi-OS Roadmap

> **Current Build Status (`v0.4.0`):** Blackmarker Studio is **currently built, packaged, and verified on macOS 14+ (Apple Silicon & Intel)** only. Windows and Linux builds have **not** been packaged or tested yet and are scheduled on the **`v0.5.0` roadmap**.

Because the underlying Python sanitization engine (`pikepdf`/`QPDF`, `pdfplumber`, `polars`, `reportlab`, `FastAPI`) uses portable open-source libraries, our `v0.5.0` milestone focuses on building, testing, and packaging standalone Windows and Linux distributions alongside our existing macOS app bundle.

### Current OS Support Matrix vs. Planned Multi-OS Roadmap

| Layer / Capability | macOS 14+ (Apple Silicon & Intel) | Windows 10 / 11 (x64 & ARM64) | Linux Desktop & Server (Ubuntu / Debian / RHEL / WSL2) |
| :--- | :---: | :---: | :---: |
| **Build & Verification Status** | **Built & Verified (`v0.4.0` Today)** | **Planned (`v0.5.0` Roadmap)** | **Planned (`v0.5.0` Roadmap)** |
| **Core PikePDF / QPDF Stream Sanitizer** | Built & Verified (`v0.4.0`) | Planned Verification (`v0.5.0`) | Planned Verification (`v0.5.0`) |
| **Spatial Geometry (`pdfplumber`) & Polars Audit Engine** | Built & Verified (`v0.4.0`) | Planned Verification (`v0.5.0`) | Planned Verification (`v0.5.0`) |
| **Tier 1 Deterministic Engine (`PII` • `PHI` • `PPI`)** | Built & Verified (`v0.4.0`) | Planned Verification (`v0.5.0`) | Planned Verification (`v0.5.0`) |
| **Tier 2 Google Gemma 4 E4B (`llama-cpp-python`)** | Apple Metal / CPU (`v0.4.0` Today) | Planned CPU / CUDA / Vulkan (`v0.5.0`) | Planned CPU / CUDA / ROCm / Vulkan (`v0.5.0`) |
| **`blackmarker` CLI & Local Web HITL (`blackmarker serve`)** | Built & Verified (`v0.4.0`) | Planned Windows Build (`v0.5.0`) | Planned Linux Build (`v0.5.0`) |
| **Native Desktop Studio Shell & System Tray Droplet** | `Blackmarker Studio.app` (SwiftUI + `PDFKit` + `MenuBarExtra` - **Today**) | Planned `.exe` / `.msi` (`WebView2` / `Tauri v2` + `pystray` - **`v0.5.0`**) | Planned `.AppImage` / `.deb` / `.rpm` (`WebKitGTK` + Tray - **`v0.5.0`**) |
| **On-Device Scanned PDF OCR** | Apple `Vision` (`VNRecognizeTextRequest`) + Gemma 4 Vision (**Today**) | Planned Local ONNX Runtime (`RapidOCR`) + Gemma 4 Vision (**`v0.5.0`**) | Planned Local ONNX Runtime (`RapidOCR`) + Gemma 4 Vision (**`v0.5.0`**) |

### Release Milestones

- **`v0.4.0` (Current Release - macOS 14+ Only):**
  - **macOS 14+ (`Blackmarker Studio.app`):** Native SwiftUI desktop studio, `PDFKit` annotation canvas, Apple `Vision` (`VNRecognizeTextRequest`) neural OCR, `MenuBarExtra` status bar quick-scrub droplet, and Apple Metal GPU acceleration.
  - **`blackmarker` CLI & Local Web HITL Studio (`blackmarker serve`):** Built and verified on macOS with `PDF.js` interactive review canvas, `Shift + Drag` Manual Blackmarker marquee drawing, a-la-carte `PII` / `PHI` / `PPI` toggles, and ReportLab compliance certificates.
- **`v0.5.0` (Planned Roadmap) - Cross-Platform Verification, macOS Finder Quick Action & Native Windows / Linux Packaging:**
  - **macOS Finder Right-Click Quick Action:** On macOS right-click Quick Action for instant PDF redaction directly from Finder, allowing quick selection of the target redaction profile (`PII`, `PHI`, `PPI`).
  - **Public vs. Private Sector Policy Separation:** Concise, user-friendly separation of **Public Sector** (PII, FOIA, victim names, sensitive information, purchases, regulatory requirements) and **Private Sector** (Banking, Lifescience & Healthcare) policies.
  - **Windows 10/11 (`.exe` / `.msi`):** Standalone desktop shell via `PyWebView` (Microsoft Edge `WebView2`) / `Tauri v2` + system tray quick-scrub droplet (`pystray`) + single-binary `PyInstaller` bundle, with `llama-cpp-python` AVX2, NVIDIA CUDA, and Vulkan GPU acceleration, plus local ONNX Runtime (`RapidOCR`) fallback for scanned PDFs.
  - **Linux Desktop & Server (`.AppImage` / `.deb` / `.rpm` / Docker):** Standalone `WebKitGTK` desktop shell + `.AppImage`, `.deb`, and `.rpm` packages + air-gapped `--network=none` OCI/Docker container image for enterprise Linux servers and Windows WSL2.
  - **GitHub Actions Multi-OS CI/CD Matrix:** Automated builds, test runs, and zero-residual PDF verification across `macos-latest`, `windows-latest`, and `ubuntu-latest`.
- **`v0.6.0` (Planned Roadmap) - Expanded Global & State Regulatory Packs:**
  - Pluggable policy packs for **GDPR** (European Union), **CCPA / CPRA** (California), **FERPA** (Education), **CJIS Security Policy v6.0**, and 50-state FOIA statutory registries.

---

## Project Structure

```text
blackmarker-studio/
├── .github/
│   ├── PULL_REQUEST_TEMPLATE.md  # Contributor PR verification & layer checklist
│   ├── ISSUE_TEMPLATE/           # Structured YAML Issue Forms (Bug, Feature, Compliance/Statute)
│   └── DISCUSSION_TEMPLATE/      # Structured GitHub Discussion templates (Ideas, Q&A, Show & Tell)
├── Package.swift                 # SwiftPM manifest for native macOS app & RedactGovKit
├── build.sh                      # Builds AppIcon.icns, Swift release binary & Blackmarker Studio.app
├── pyproject.toml                # Python 3.12+ project metadata & CLI entrypoints (uv)
├── uv.lock                       # Deterministic dependency lockfile
├── BLUEPRINT.md                  # Technical architecture, Multi-OS roadmap & commercialization blueprint
├── CODE_OF_CONDUCT.md            # Contributor Covenant v2.1 community standards
├── CONTRIBUTING.md               # Contributor guide, testing standards & extension instructions
├── SECURITY.md                   # Air-gapped threat model, stream verification & disclosure policy
├── LICENSE                       # MIT License
├── assets/
│   └── icon/                     # Apple HIG superellipse icons (SVG, 512px, 1024px, AppIcon.icns)
├── scripts/
│   ├── download_gemma.py         # Air-gapped GGUF model downloader (Google Gemma 4 E4B)
│   ├── generate_app_icon.py      # Procedural Apple HIG icon & .icns generator
│   ├── generate_synthetic_pdfs.py# Synthetic FOIA / clinical / financial test PDF generator
│   └── try_interactive.py        # Interactive CLI walkthrough script
├── Sources/
│   ├── RedactGovKit/             # Swift library: JSON-RPC WorkerClient, Vision OCR, SQLite store
│   └── RedactGovApp/             # SwiftUI macOS Studio, MenuBarExtra droplet & PDFKit canvas
├── src/
│   └── redact_gov/
│       ├── cli.py                # Typer CLI (blackmarker / blackmarker-studio)
│       ├── config.py             # Runtime & model path configuration
│       ├── pipeline.py           # End-to-end hybrid planning & execution pipeline
│       ├── worker.py             # Ephemeral stdio JSON-RPC worker with idle VRAM watchdog
│       ├── api/                  # Local FastAPI server & interactive Web HITL Studio UI
│       ├── certificates/         # Polars + ReportLab Compliance Certificate PDF generator
│       ├── core/                 # Pydantic models, statutes, criteria, geometry & normalizer
│       └── engines/              # Tier 1 deterministic, Tier 2 Gemma 4 E4B & PikePDF sanitizer
└── tests/                        # Comprehensive pytest suite (stream excision, OCR, API, statutes)
```

---

## Running the Test Suite

Blackmarker Studio enforces strict automated testing across byte-level PDF stream excision, multi-sector compliance profiles, form context evaluation, and native macOS bundle execution:

```bash
# Run the full Python pytest suite (70+ unit, integration, and byte-verification tests)
uv run pytest

# Run the native macOS Swift package tests
swift test

# Run the end-to-end macOS app bundle + stdio worker self-test
"./build/Blackmarker Studio.app/Contents/MacOS/RedactGovApp" --self-test
```

---

## Contributing & Security

- **Contributing:** We welcome pull requests for new sector compliance profiles, statutory mappings, deterministic validators, Multi-OS packaging targets, and UI refinements! Please read [CONTRIBUTING.md](CONTRIBUTING.md) and our [Code of Conduct](CODE_OF_CONDUCT.md) before submitting changes.
- **Community & Discussions:** Have questions about air-gapped deployment, hardware benchmarks, or new regulatory frameworks? Open a thread in **GitHub Discussions** or use our structured **GitHub Issue Forms**.
- **Security & Sanitization Integrity:** Because Blackmarker Studio is engineered for high-assurance legal, clinical, and financial sanitization, any bypass where underlying glyphs survive redaction is treated as a critical security vulnerability. See [SECURITY.md](SECURITY.md) for our air-gapped verification architecture and responsible disclosure policy.

---

## License

Released under the [MIT License](LICENSE). Copyright (c) 2026 Blackmarker Studio Contributors.
