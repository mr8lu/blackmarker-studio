# AI Blackmarker (RedactGov) Project Directives

## Foundational Mandates
- **Product Name & Branding:** **AI Blackmarker** (package/module namespace `redact_gov`, CLI entrypoints `aiblackmarker` and `redactgov`). App icon (`assets/icon/icon_1024.png` & `assets/icon/AppIcon.icns`) strictly adheres to Apple Human Interface Guidelines for macOS (`824x824` continuous superellipse on a `1024x1024` transparent canvas, 90-degree top-down lighting, no text inside the icon).
- **Language & Runtime:** Python 3.12+ managed exclusively via `uv`. Never use raw `pip` or standard `venv` commands.
- **Model Standard:** Primary focus on the **Google Gemma** model series (specifically **Google Gemma 4 E4B** GGUF via `llama-cpp-python` with Apple Metal / CPU acceleration).
- **PDF Sanitization Standard:** Always use `pikepdf` (backed by QPDF) for PDF manipulation, content stream editing, and metadata eradication. Never use `PyMuPDF` or `fitz`.
- **Data Engineering:** Use the `polars` DataFrame library for high-speed tabular processing, token indexing, and redaction certificate record-keeping.
- **Typography & Formatting:** Never use the em dash "—". Use plain dash "-" instead.
- **Git & Commits:** Never auto-add agent name as co-author. All code and GitHub commits must exclusively use `mr8lu` as the author name.

## Core Modules
- `redact_gov.core.models`: Pydantic schemas for entities, bounding boxes, statutory codes, and audit records.
- `redact_gov.core.statutes`: Virginia Code statutory exemption database (Va. Code § 2.2-3700 et seq.).
- `redact_gov.core.geometry`: PDF point coordinate extraction and token-to-bbox alignment via `pdfplumber`.
- `redact_gov.engines.deterministic`: Tier 1 sub-second regex & algorithmic validators for VA Driver's Licenses, SSNs, DOBs, phones, and emails.
- `redact_gov.engines.contextual`: Tier 2 Google Gemma 4 E4B cognitive extractor with constrained JSON grammar for juvenile identifiers, victims, witnesses, and tactical personnel.
- `redact_gov.engines.sanitization`: PikePDF stream surgery engine removing glyph operators (`Tj`, `TJ`), drawing opaque vector rectangles (for both AI-detected and manual Blackmarker boxes), wiping XMP metadata, and certifying zero residual bytes.
- `redact_gov.certificates.generator`: Virginia FOIA Redaction Certificate and Audit Report generator powered by Polars and ReportLab.
- `redact_gov.worker`: Ephemeral stdio JSON-RPC helper worker (`aiblackmarker worker` / `redactgov worker`) with idle watchdog auto-shutdown to free Gemma 4 E4B unified memory when inactive.
- `Sources/RedactGovKit` & `Sources/RedactGovApp`: Native macOS SwiftUI Menu Bar Droplet + AI Blackmarker Studio (`Package.swift` + `./build.sh`) featuring native `PDFKit` annotation overlays, interactive **Manual Blackmarker** marquee drawing (`BlackmarkerPDFView`), Apple `Vision` (`VNRecognizeTextRequest`) neural OCR for scanned pages, and a local SQLite FOIA docket index (`CaseIndexStore`).
