#!/bin/bash
# Build script for Space Debris macOS app
set -e

cd "$(dirname "$0")"

echo "=== Building Space Debris for macOS ==="

# Step 1: Compile Qt resources
echo ""
echo "Step 1: Compiling Qt resources..."
pyrcc5 resources.qrc -o resources_rc.py
echo "Created resources_rc.py"

# Step 2: Run PyInstaller
echo ""
echo "Step 2: Running PyInstaller..."
pyinstaller space-debris-macos.spec --noconfirm

# Step 3: Ad-hoc sign (for local testing)
echo ""
echo "Step 3: Signing app (ad-hoc)..."
codesign --force --deep --sign - "dist/Space Debris.app"

echo ""
echo "=== Build complete ==="
echo "App bundle: dist/Space Debris.app"
echo ""
echo 'To run: open "dist/Space Debris.app"'
echo ""
echo "For distribution, sign with Developer ID:"
echo "  codesign --force --deep --options runtime \\"
echo "    --sign \"Developer ID Application: Your Name (TEAMID)\" \\"
echo '    "dist/Space Debris.app"'
