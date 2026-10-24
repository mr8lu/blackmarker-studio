# Security Policy & Sanitization Assurance

**Blackmarker Studio** is engineered for high-assurance document sanitization across government agencies (FOIA / CJIS), hospital networks (HIPAA Safe Harbor), financial institutions (PCI DSS v4.0 / GLBA), judiciary filings (FRCP 5.2), and enterprise compliance teams (AICPA SOC 2).

Because an incomplete redaction can expose regulated `PII`, `PHI`, or `PPI` in public records or litigation discovery, we treat any **PDF stream sanitization bypass**, **residual metadata leak**, or **unexpected network egress** as a critical security vulnerability.

---

## Supported Versions

| Version | Supported | Notes |
| :--- | :---: | :--- |
| `0.4.x` (Current) | Yes | Active support for multi-sector `PII` / `PHI` / `PPI` sanitization & `Blackmarker Studio.app` (`v0.4.2`) |
| `< 0.4.0` | No | Please upgrade to `0.4.2` or newer |

---

## Core Security Architecture

### 1. 100% Air-Gapped Execution (Zero Network Egress)
- **No Cloud Telemetry or Remote APIs:** Blackmarker Studio never transmits document text, page images, filenames, or usage telemetry over the network.
- **On-Device Neural Inference:** Tier 2 contextual extraction runs locally via quantized **Google Gemma 4 E4B** (`llama-cpp-python` on Apple Metal or local CPU) and Apple `Vision` (`VNRecognizeTextRequest`) on-device OCR.
- **Localhost-Only IPC:** The native macOS application (`Blackmarker Studio.app`) communicates with its ephemeral Python helper (`redactgov-worker`) strictly over anonymous OS `stdin`/`stdout` pipes. When using the Web HITL Reviewer (`blackmarker serve`), the FastAPI server binds exclusively to `127.0.0.1` by default.

### 2. Surgical PDF Stream Excision (`pikepdf` / `QPDF`)
Unlike rudimentary PDF viewers that merely draw a black annotation rectangle over text (leaving underlying text glyphs selectable in the file byte stream), Blackmarker Studio performs true content stream surgery in `src/redact_gov/engines/sanitization.py`:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                Four-Stage PikePDF Sanitization Pipeline                 │
├─────────────────────────────────────────────────────────────────────────┤
│  Stage 1: Content Stream Token Parsing                                  │
│    • Uncompresses PDF page streams via QPDF                             │
│    • Locates Tj / TJ text-showing operators intersecting target boxes   │
│    • Excises matching character glyph bytes from the stream             │
├─────────────────────────────────────────────────────────────────────────┤
│  Stage 2: Opaque Vector Burn-In                                         │
│    • Draws solid black vector rectangles (re + f) directly into the     │
│      page content stream at each AI-detected or Manual Blackmarker box  │
├─────────────────────────────────────────────────────────────────────────┤
│  Stage 3: Metadata & Structure Eradication                              │
│    • Deletes /Metadata (XMP XML streams) and scrubs /Info dictionaries  │
│    • Removes interactive /Annots and form /AcroForm residual values     │
├─────────────────────────────────────────────────────────────────────────┤
│  Stage 4: Post-Redaction Zero-Residual Verification                     │
│    • Re-opens the written output PDF from disk                          │
│    • Scans both extracted text layers and uncompressed raw stream bytes │
│    • Fails closed if any redacted substring remains detectable          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3. Ephemeral Memory Hygiene
The native macOS helper worker (`EphemeralRedactWorker`) enforces an automatic inactivity watchdog (`--idle-timeout`, default 180 seconds) that unloads Google Gemma 4 E4B weights and terminates the helper process when idle, minimizing resident memory exposure on shared workstations.

---

## Threat Model & Known Scope Boundaries

What Blackmarker Studio **protects against**:
- Copy-paste or PDF content-stream extraction (`pdftotext`, `pdfplumber`, `qpdf --qdf`, hex inspection) of excised digital text tokens.
- Leakage of author names, document titles, creation software, or edit history via PDF `/Info` or XMP `/Metadata` dictionaries.
- Accidental omission of words inside user-drawn **Manual Blackmarker** (`Shift + Drag`) regions on digital PDFs (underlying word tokens intersecting the marquee rectangle are automatically resolved and excised).
- Network exfiltration of confidential records to third-party cloud LLM providers.

Operational considerations for **flattened raster images**:
- If a PDF page contains an embedded raster image (such as a scanned TIFF/JPEG page or a photograph of a driver's license), PDF text-operator excision (`Tj`/`TJ`) removes any OCR text layer while the opaque vector burn-in covers the visual region in standard PDF renderers. For adversarial forensic environments where embedded raster image streams themselves must be flattened so image objects cannot be extracted separately, organizations should enable full-page rasterization or pre-flatten image-only pages prior to distribution.

---

## Reporting a Vulnerability

If you discover a security vulnerability - especially any scenario where a redacted string remains recoverable from the output PDF byte stream, metadata dictionary, or temporary files - please report it privately rather than opening a public GitHub issue.

### How to Report
- **Email:** Use GitHub Private Vulnerability Reporting via the repository Security Advisories tab (`Security -> Report a vulnerability`).
- **What to Include:**
  1. A description of the vulnerability and its potential impact.
  2. A minimal synthetic PDF or reproduction script (please **never** attach real PII, PHI, or PPI).
  3. The exact CLI command (`blackmarker redact ...`) or macOS Studio workflow used.
  4. The output of `uv run pytest tests/test_sanitization_spike.py`.

### Response Timeline
- **Acknowledgment:** Within 48 hours of receipt.
- **Triage & Reproduction:** Within 5 business days.
- **Remediation & Coordinated Disclosure:** Critical stream-sanitization issues are prioritized for immediate patching and regression test inclusion prior to public disclosure.
