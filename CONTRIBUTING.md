# Contributing to Blackmarker Studio

Thank you for your interest in contributing to **Blackmarker Studio**! Whether you are adding a new statutory exemption, tightening a deterministic checksum validator for `PII` / `PHI` / `PPI`, or refining the native macOS SwiftUI canvas, your work helps organizations sanitize sensitive documents safely without cloud data exfiltration.

Think of contributing to a redaction engine like maintaining surgical instruments: precision, repeatability, and zero unintended residue matter above all else.

---

## Foundational Engineering Rules

Before writing code or documentation, please keep these repository-wide standards in mind:

1. **Python & Dependency Management (`uv` only):** Always use Python 3.12+ managed via `uv`. Never invoke raw `pip` or `python -m venv`.
2. **PDF Sanitization Engine (`pikepdf` only):** All PDF content stream manipulation, glyph excision (`Tj`/`TJ`), vector burn-in, and metadata removal must use `pikepdf` (backed by QPDF). Never introduce `PyMuPDF` or `fitz`.
3. **Data Processing (`polars`):** Use `polars` DataFrames for tabular audit aggregation, token indexing, and compliance certificate generation.
4. **Typography Rule:** Never use the em dash character in code, comments, UI strings, or documentation. Always use a standard ASCII hyphen/dash (`-`) instead.
5. **100% Air-Gapped Runtime:** Never introduce runtime calls to external cloud APIs, telemetry endpoints, or remote inference servers.

---

## Development Environment Setup

### Prerequisites
- **Python 3.12+**
- **`uv`** (`curl -LsSf https://astral.sh/uv/install.sh | sh` or `brew install uv`)
- **macOS 14.0+ with Xcode Command Line Tools** (`xcode-select --install`) for building the SwiftUI macOS application (`Blackmarker Studio.app`)

### Step-by-Step Setup

```bash
# 1. Clone the repository and enter the directory
git clone https://github.com/mr8lu/blackmarker-studio.git
cd blackmarker-studio
# (Or if cloned as ai-blackmarker: cd ai-blackmarker)

# 2. Synchronize the Python virtual environment and reinstall local entrypoints
uv sync --reinstall

# 3. Verify the CLI entrypoints are active
uv run blackmarker --help
uv run blackmarker-studio statutes

# 4. Build the native macOS application bundle (build/Blackmarker Studio.app)
./build.sh
```

---

## Running the Test Suite

Every pull request must pass both the Python test suite and the native macOS bundle self-test before merge.

```bash
# 1. Run the full Python test suite
uv run pytest

# 2. Run Swift Package Manager unit tests (RedactGovKit)
swift test

# 3. Run the headless macOS app bundle + ephemeral JSON-RPC worker self-test
"./build/Blackmarker Studio.app/Contents/MacOS/RedactGovApp" --self-test
```

---

## How to Extend Blackmarker Studio

### 1. Adding a Statutory or Regulatory Citation

All statutory and compliance citations live in `src/redact_gov/core/statutes.py` inside the `VIRGINIA_STATUTES` registry (which indexes Federal FOIA, State FOIA, HIPAA Safe Harbor, PCI DSS v4.0, GLBA, FRCP 5.2, and AICPA SOC 2).

1. Add a new `StatuteExemption` entry in `src/redact_gov/core/statutes.py` specifying:
   - `code`: Unique identifier (for example, `"HIPAA-164.514(b)(2)(i)(O)"` or `"PCI-DSS-3.4"`).
   - `legal_citation`: Formal legal or regulatory citation printed on audit certificates.
   - `short_title`: Concise human-readable title.
   - `description`: Explanation of what the exemption covers.
   - `category`: Internal entity category key (for example, `"medical_id"`, `"financial_pan"`, `"ssn"`).
   - `data_domain`: Must be one of `"PII"`, `"PHI"`, or `"PPI"`.
2. Map the category or statute code to the appropriate `ReleaseProfile` in `src/redact_gov/core/criteria.py`.
3. Add a unit test in `tests/test_statutes.py` and `tests/test_criteria.py`.

### 2. Adding a Tier 1 Deterministic Validator (`PII` / `PHI` / `PPI`)

Deterministic validators live in `src/redact_gov/engines/deterministic.py` and form-field context rules live in `src/redact_gov/core/criteria.py`.

1. **Regex + Algorithmic Checksum:** Whenever possible, pair regex matching with an algorithmic check (such as Luhn validation for payment cards or Mod-10 weighting for ABA routing numbers) to prevent false positives on ordinary numbers.
2. **Assign the Data Domain:** Ensure every emitted `DetectedEntity` sets `data_domain` to `"PII"`, `"PHI"`, or `"PPI"` so a-la-carte domain filtering (`--domains`) works seamlessly.
3. **Test Coverage:** Add positive and negative test cases in `tests/test_deterministic.py` and verify that `PikePDFSanitizer` completely excises the matched tokens from a synthetic PDF.

### 3. Modifying the Native macOS App or Web HITL Studio

- **macOS SwiftUI App:** Located in `Sources/RedactGovKit/` and `Sources/RedactGovApp/`. After editing Swift files, run `./build.sh` and `"./build/Blackmarker Studio.app/Contents/MacOS/RedactGovApp" --self-test` to verify that `build/Blackmarker Studio.app` compiles cleanly and communicates over JSON-RPC with `redactgov-worker`.
- **Web HITL Studio:** Located in `src/redact_gov/api/app.py` and `src/redact_gov/api/static/index.html`. Test changes using `uv run pytest tests/test_api.py`.

---

## Pull Request Checklist

- [ ] Code is formatted cleanly and adheres to Python 3.12+ type annotations (`pydantic` v2 models where applicable).
- [ ] All tests pass via `uv run pytest` and `"./build/Blackmarker Studio.app/Contents/MacOS/RedactGovApp" --self-test`.
- [ ] New features or compliance profiles include corresponding test cases and documentation updates.
- [ ] Zero em dashes appear in any modified files (use plain hyphen/dash `-` only).
- [ ] Commit messages are concise, descriptive, and do not include automated AI co-author trailers.
