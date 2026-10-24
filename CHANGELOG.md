## [0.4.2] - 2026-10-24

### 🐛 Bug Fixes

- *(security)* Harden upload validation, HTML/XML escaping, prompt sanitization, and temp image cleanup

### 📚 Documentation

- *(readme)* Streamline README hierarchy, plain-English pitch, and WCAG AAA badges
## [0.4.1] - 2026-10-24

### 🚀 Features

- *(ui)* Streamline Studio UX with always-on marquee, plain-language domains, and safe droplet review

### 📚 Documentation

- Update title and description to On-device FOIA, HIPAA, and financial PDF redactor
- *(readme)* Document redact-first optional certificates and privacy-safe File History

### ⚙️ Miscellaneous Tasks

- *(release)* Bump version to v0.4.1
## [0.4.0] - 2026-10-24

### 🚀 Features

- Implement Visual HITL Review UI and API endpoints
- *(vision)* Integrate Gemma 4 E4B multimodal vision support and scanned page handling
- Rebrand to AI Blackmarker with HIG macOS icon and manual marquee redaction
- Add multi-sector compliance (HIPAA/PCI/GLBA/FRCP/SOC2), a-la-carte PII/PHI/PPI domains, and customizable certificates
- Rebrand to Blackmarker Studio and add open-source repository documentation (LICENSE, CONTRIBUTING, SECURITY)
- Auto-generate untracked data/synthetic_corpus on first run and harden .gitignore
- Add comb-box form reconstruction, ToUnicode/spatial stream excision, and PII/PPI hardening
- *(ux)* Make compliance certificate optional (redact first, documentation second)

### 🐛 Bug Fixes

- *(privacy)* Scrub sensitive entity text from File History and only list existing files

### 📚 Documentation

- Integrate Gemma 4 E4B native multimodal vision into architecture blueprint
- Add Multi-OS roadmap (macOS, Windows, Linux) and GitHub PR, Issue, and Discussion templates

### 💼 Other

- Incorporate feat/p0-multimodal-vision into feat/p0-beta-release
- *(homebrew)* Bundle portable backend resources and add Homebrew Cask install docs
## [0.1.0] - 2026-09-11

### 🚀 Features

- MVP pre-release sovereign FOIA redaction engine
- Centralized criteria registry, document normalizer, and low-level stream surgery
