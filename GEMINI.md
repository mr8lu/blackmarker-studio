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
- `redact_gov.core.models`: Pydantic schemas for entities (`data_domain`: `PII` | `PHI` | `PPI`), bounding boxes, compliance citations, customizable `CertificateConfig` presets, and audit records.
- `redact_gov.core.statutes`: Multi-sector statutory and regulatory registry covering Federal FOIA (5 U.S.C. § 552), State/Local Public Records (Va. Code § 2.2-3700 et seq.), Healthcare HIPAA Safe Harbor (45 CFR § 164.514(b)), Banking & Payment PCI DSS v4.0 & GLBA (16 CFR Part 314), Judicial Filings (Fed. R. Civ. P. 5.2), and Private Sector AICPA SOC 2 (CC6.1 / P4.2).
- `redact_gov.core.criteria`: Multi-sector release profiles (`public_foia`, `hipaa`, `pci_dss`, `glba`, `frcp_5_2`, `aicpa_soc2`, `strict_privacy`, `law_enforcement`, `environmental_review`) and a-la-carte `PII` / `PHI` / `PPI` domain filtering.
- `redact_gov.core.geometry`: PDF point coordinate extraction and token-to-bbox alignment via `pdfplumber`.
- `redact_gov.engines.deterministic`: Tier 1 sub-second regex & algorithmic validators for PII (SSNs, Driver's Licenses, Passports, DOBs, phones, emails), PHI (MRNs, NPIs, Health Plan / Medicare IDs, ICD-10 codes), and PPI (Luhn-validated Credit/Debit PANs, Mod-10 ABA routing numbers, bank accounts, IBAN/SWIFT).
- `redact_gov.engines.contextual`: Tier 2 Google Gemma 4 E4B cognitive extractor with constrained JSON grammar for juvenile identifiers, victims, witnesses, tactical personnel, clinical notes, and financial account context.
- `redact_gov.engines.sanitization`: PikePDF stream surgery engine removing glyph operators (`Tj`, `TJ`), drawing opaque vector rectangles (for both AI-detected and manual Blackmarker boxes), wiping XMP metadata, and certifying zero residual bytes.
- `redact_gov.certificates.generator`: Customizable Multi-Sector Compliance & Redaction Certificate generator powered by Polars and ReportLab (`generic_compliance`, `public_foia`, `hipaa_healthcare`, `banking_glba_pci`, `judicial_frcp`, `enterprise_aicpa`, or custom organization/attestation).
- `redact_gov.worker`: Ephemeral stdio JSON-RPC helper worker (`aiblackmarker worker` / `redactgov worker`) with idle watchdog auto-shutdown to free Gemma 4 E4B unified memory when inactive.
- `Sources/RedactGovKit` & `Sources/RedactGovApp`: Native macOS SwiftUI Menu Bar Droplet + AI Blackmarker Studio (`Package.swift` + `./build.sh`) featuring multi-sector compliance profiles, a-la-carte `PII` / `PHI` / `PPI` domain toggles, customizable Certificate Template editor sheet, native `PDFKit` annotation overlays, interactive **Manual Blackmarker** marquee drawing (`BlackmarkerPDFView`), Apple `Vision` (`VNRecognizeTextRequest`) neural OCR for scanned pages, and a local SQLite docket index (`CaseIndexStore`).
