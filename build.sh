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

echo "[4/5] Installing ephemeral helper Contents/Helpers/redactgov-worker..."
cat > "${HELPERS_DIR}/redactgov-worker" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export REDACTGOV_WORKSPACE_ROOT="${ROOT_DIR}"
cd "${ROOT_DIR}"
if [[ -x "${ROOT_DIR}/.venv/bin/blackmarker" ]]; then
    exec "${ROOT_DIR}/.venv/bin/blackmarker" worker "\$@"
elif [[ -x "${ROOT_DIR}/.venv/bin/redactgov" ]]; then
    exec "${ROOT_DIR}/.venv/bin/redactgov" worker "\$@"
else
    exec uv run blackmarker worker "\$@"
fi
EOF
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
