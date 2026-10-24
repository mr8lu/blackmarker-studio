#!/usr/bin/env bash
set -euo pipefail

# Blackmarker Studio Native macOS App Bundle Builder (SwiftPM + Ephemeral Helper + HIG Icon Packaging)
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
APP_BUNDLE="${BUILD_DIR}/Blackmarker Studio.app"
CONTENTS_DIR="${APP_BUNDLE}/Contents"
MACOS_DIR="${CONTENTS_DIR}/MacOS"
HELPERS_DIR="${CONTENTS_DIR}/Helpers"
RESOURCES_DIR="${CONTENTS_DIR}/Resources"

echo "[1/5] Generating Apple HIG AppIcon.icns & synthetic sample PDFs..."
cd "${ROOT_DIR}"
if [[ ! -f "${ROOT_DIR}/assets/icon/AppIcon.icns" ]]; then
    uv run python scripts/generate_app_icon.py
fi
uv run python scripts/generate_synthetic_pdfs.py

echo "[2/5] Building SwiftUI Blackmarker Studio (Release)..."
swift build -c release --product RedactGovApp

BIN_PATH="$(swift build -c release --show-bin-path)/RedactGovApp"

echo "[3/5] Assembling Blackmarker Studio.app bundle structure..."
rm -rf "${APP_BUNDLE}" "${BUILD_DIR}/AI Blackmarker.app" "${BUILD_DIR}/RedactGov.app"
mkdir -p "${MACOS_DIR}" "${HELPERS_DIR}" "${RESOURCES_DIR}"

cp "${BIN_PATH}" "${MACOS_DIR}/RedactGovApp"
chmod +x "${MACOS_DIR}/RedactGovApp"

if [[ -f "${ROOT_DIR}/assets/icon/AppIcon.icns" ]]; then
    cp "${ROOT_DIR}/assets/icon/AppIcon.icns" "${RESOURCES_DIR}/AppIcon.icns"
fi

if [[ -d "${ROOT_DIR}/data/synthetic_corpus" ]]; then
    mkdir -p "${RESOURCES_DIR}/synthetic_corpus"
    cp -R "${ROOT_DIR}/data/synthetic_corpus/"*.pdf "${RESOURCES_DIR}/synthetic_corpus/" 2>/dev/null || true
fi

mkdir -p "${RESOURCES_DIR}/backend"
cp "${ROOT_DIR}/pyproject.toml" "${ROOT_DIR}/README.md" "${RESOURCES_DIR}/backend/"
cp -R "${ROOT_DIR}/src" "${RESOURCES_DIR}/backend/src"

echo "[4/5] Installing ephemeral helper Contents/Helpers/redactgov-worker..."
cat > "${HELPERS_DIR}/redactgov-worker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"

HELPER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTENTS_DIR="$(cd "${HELPER_DIR}/.." && pwd)"
BUNDLED_BACKEND="${CONTENTS_DIR}/Resources/backend"
DEV_ROOT="__DEV_ROOT__"

if [[ -d "${DEV_ROOT}" && -x "${DEV_ROOT}/.venv/bin/blackmarker" ]]; then
    export REDACTGOV_WORKSPACE_ROOT="${DEV_ROOT}"
    cd "${DEV_ROOT}"
    exec "${DEV_ROOT}/.venv/bin/blackmarker" worker "$@"
elif command -v blackmarker >/dev/null 2>&1; then
    exec blackmarker worker "$@"
elif command -v uv >/dev/null 2>&1 && [[ -f "${BUNDLED_BACKEND}/pyproject.toml" ]]; then
    RUNTIME_DIR="${HOME}/Library/Application Support/RedactGov/runtime"
    mkdir -p "${RUNTIME_DIR}"
    rsync -a --delete --exclude '.venv' "${BUNDLED_BACKEND}/" "${RUNTIME_DIR}/"
    cd "${RUNTIME_DIR}"
    exec uv run blackmarker worker "$@"
else
    echo "Error: Neither blackmarker nor uv found on PATH." >&2
    exit 1
fi
EOF
sed -i '' "s|__DEV_ROOT__|${ROOT_DIR}|g" "${HELPERS_DIR}/redactgov-worker"
chmod +x "${HELPERS_DIR}/redactgov-worker"

cat > "${CONTENTS_DIR}/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>RedactGovApp</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>studio.blackmarker.app</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>Blackmarker Studio</string>
    <key>CFBundleDisplayName</key>
    <string>Blackmarker Studio</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>0.4.0</string>
    <key>CFBundleVersion</key>
    <string>4</string>
    <key>LSMinimumSystemVersion</key>
    <string>14.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>RedactGovWorkspaceRoot</key>
    <string>${ROOT_DIR}</string>
</dict>
</plist>
EOF

echo "[5/5] Ad-hoc signing ${APP_BUNDLE}..."
codesign --force --deep --sign - "${APP_BUNDLE}"

echo "Built native macOS bundle: ${APP_BUNDLE}"
echo "Launch with: open \"${APP_BUNDLE}\""
