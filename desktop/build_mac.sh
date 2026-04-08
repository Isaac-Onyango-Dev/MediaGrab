#!/bin/bash
set -euo pipefail

# ─── Configuration ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION="$(cat "$PROJECT_ROOT/VERSION" | tr -d '[:space:]')"
APP_NAME="MediaGrab"
BUNDLE_ID="com.isaiconyango.mediagrab"
APP_BUNDLE="$SCRIPT_DIR/dist/${APP_NAME}.app"
DMG_OUTPUT="$SCRIPT_DIR/dist/${APP_NAME}-${VERSION}.dmg"
ASSETS_DIR="$SCRIPT_DIR/assets"
FFMPEG_SOURCE="$SCRIPT_DIR/ffmpeg"  # Optional: place macOS ffmpeg binary here

echo "============================================================"
echo "  MediaGrab macOS Build Script v${VERSION}"
echo "============================================================"

# ─── Pre-flight checks ────────────────────────────────────────────────────────
echo ""
echo "[1/6] Checking prerequisites..."

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install from https://www.python.org"
    exit 1
fi

if ! command -v pyinstaller &>/dev/null; then
    echo "ERROR: PyInstaller not found. Run: pip install pyinstaller"
    exit 1
fi

if ! command -v create-dmg &>/dev/null; then
    echo "WARNING: create-dmg not found. Install with: brew install create-dmg"
    echo "         DMG creation will be skipped (only .app bundle will be produced)."
    SKIP_DMG=true
else
    SKIP_DMG=false
fi

# ─── Step 1: Run PyInstaller ─────────────────────────────────────────────────
echo ""
echo "[2/6] Building .app bundle with PyInstaller..."

cd "$SCRIPT_DIR"

pyinstaller --noconfirm \
    --onedir \
    --windowed \
    --name "${APP_NAME}" \
    --osx-bundle-identifier "${BUNDLE_ID}" \
    --add-data "assets:assets" \
    --add-data "../VERSION:." \
    --add-data "../shared:shared" \
    --collect-all "customtkinter" \
    --collect-all "yt_dlp" \
    --collect-all "PIL" \
    --hidden-import "requests" \
    --hidden-import "psutil" \
    main.py

if [ ! -d "$APP_BUNDLE" ]; then
    echo "ERROR: PyInstaller did not produce ${APP_NAME}.app"
    exit 1
fi

echo "  Created: ${APP_BUNDLE}"

# ─── Step 2: Inject Info.plist metadata ───────────────────────────────────────
echo ""
echo "[3/6] Injecting Info.plist metadata..."

PLIST="$APP_BUNDLE/Contents/Info.plist"

if [ ! -f "$PLIST" ]; then
    echo "ERROR: Info.plist not found at ${PLIST}"
    exit 1
fi

# Use PlistBuddy to set/add keys (safe — overwrites PyInstaller defaults)
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier ${BUNDLE_ID}" "$PLIST" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string ${BUNDLE_ID}" "$PLIST"

/usr/libexec/PlistBuddy -c "Set :CFBundleVersion ${VERSION}" "$PLIST" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :CFBundleVersion string ${VERSION}" "$PLIST"

/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString ${VERSION}" "$PLIST" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string ${VERSION}" "$PLIST"

/usr/libexec/PlistBuddy -c "Set :LSMinimumSystemVersion 11.0" "$PLIST" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :LSMinimumSystemVersion string 11.0" "$PLIST"

/usr/libexec/PlistBuddy -c "Set :NSHighResolutionCapable true" "$PLIST" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :NSHighResolutionCapable bool true" "$PLIST"

/usr/libexec/PlistBuddy -c "Set :NSRequiresAquaSystemAppearance false" "$PLIST" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :NSRequiresAquaSystemAppearance bool false" "$PLIST"

# Set the executable name to match the bundle
EXEC_NAME=$(/usr/libexec/PlistBuddy -c "Print :CFBundleExecutable" "$PLIST" 2>/dev/null || echo "")
if [ -z "$EXEC_NAME" ]; then
    /usr/libexec/PlistBuddy -c "Add :CFBundleExecutable string ${APP_NAME}" "$PLIST"
fi

echo "  CFBundleIdentifier: ${BUNDLE_ID}"
echo "  CFBundleVersion:    ${VERSION}"
echo "  LSMinSystemVersion: 11.0"

# ─── Step 3: Copy app icon to Resources ───────────────────────────────────────
echo ""
echo "[4/6] Installing app icon..."

RESOURCES_DIR="$APP_BUNDLE/Contents/Resources"
mkdir -p "$RESOURCES_DIR"

if [ -f "$ASSETS_DIR/icon.icns" ]; then
    cp "$ASSETS_DIR/icon.icns" "$RESOURCES_DIR/icon.icns"
    echo "  Copied icon.icns -> Resources/"
else
    echo "  WARNING: icon.icns not found in assets/. Using PyInstaller default."
fi

# ─── Step 4: Bundle FFmpeg (optional) ────────────────────────────────────────
echo ""
echo "[5/6] Bundling FFmpeg..."

FFMPEG_IN_BUNDLE="$RESOURCES_DIR/ffmpeg"

# Check for macOS-specific ffmpeg binary in desktop/ffmpeg/
if [ -f "$FFMPEG_SOURCE/ffmpeg" ] && file "$FFMPEG_SOURCE/ffmpeg" | grep -q "Mach-O"; then
    mkdir -p "$FFMPEG_IN_BUNDLE"
    cp "$FFMPEG_SOURCE/ffmpeg" "$FFMPEG_IN_BUNDLE/ffmpeg"
    chmod +x "$FFMPEG_IN_BUNDLE/ffmpeg"
    echo "  Bundled FFmpeg from desktop/ffmpeg/"
elif [ -f "$FFMPEG_SOURCE/ffmpeg_mac" ]; then
    mkdir -p "$FFMPEG_IN_BUNDLE"
    cp "$FFMPEG_SOURCE/ffmpeg_mac" "$FFMPEG_IN_BUNDLE/ffmpeg"
    chmod +x "$FFMPEG_IN_BUNDLE/ffmpeg"
    echo "  Bundled FFmpeg from desktop/ffmpeg/ffmpeg_mac"
elif command -v ffmpeg &>/dev/null; then
    SYSTEM_FFMPEG=$(which ffmpeg)
    if file "$SYSTEM_FFMPEG" | grep -q "Mach-O"; then
        mkdir -p "$FFMPEG_IN_BUNDLE"
        cp "$SYSTEM_FFMPEG" "$FFMPEG_IN_BUNDLE/ffmpeg"
        chmod +x "$FFMPEG_IN_BUNDLE/ffmpeg"
        echo "  Bundled system FFmpeg: $SYSTEM_FFMPEG"
    else
        echo "  SKIPPED: No macOS FFmpeg found. The app will download it at runtime."
    fi
else
    echo "  SKIPPED: FFmpeg not found. The app will download it at runtime."
fi

# ─── Step 5: Ensure PkgInfo exists ───────────────────────────────────────────
if [ ! -f "$APP_BUNDLE/Contents/PkgInfo" ]; then
    echo "APPL????" > "$APP_BUNDLE/Contents/PkgInfo"
    echo "  Created PkgInfo"
fi

# ─── Step 6: Create DMG ──────────────────────────────────────────────────────
echo ""

if [ "$SKIP_DMG" = true ]; then
    echo "[6/6] SKIPPED: create-dmg not installed."
    echo ""
    echo "============================================================"
    echo "  .app bundle built successfully!"
    echo "  Location: ${APP_BUNDLE}"
    echo ""
    echo "  To create a DMG, install create-dmg:"
    echo "    brew install create-dmg"
    echo "  Then re-run this script."
    echo "============================================================"
    exit 0
fi

echo "[6/6] Creating DMG installer..."

# Clean up old DMG
rm -f "$DMG_OUTPUT"

# Create a staging directory for the DMG contents
DMG_STAGING="$SCRIPT_DIR/dist/dmg-staging"
rm -rf "$DMG_STAGING"
mkdir -p "$DMG_STAGING"

# Copy the .app into the staging area
cp -R "$APP_BUNDLE" "$DMG_STAGING/"

# Create Applications symlink (will appear as a shortcut in the DMG)
ln -s /Applications "$DMG_STAGING/Applications"

create-dmg \
    --volname "MediaGrab ${VERSION}" \
    --volicon "$ASSETS_DIR/icon.icns" \
    --window-pos 200 120 \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "${APP_NAME}.app" 175 190 \
    --hide-extension "${APP_NAME}.app" \
    --app-drop-link 425 190 \
    --no-internet-enable \
    "$DMG_OUTPUT" \
    "$DMG_STAGING"

# Clean up staging
rm -rf "$DMG_STAGING"

# ─── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  Build complete!"
echo "============================================================"
echo ""
echo "  App bundle: ${APP_BUNDLE}"
echo "  DMG file:   ${DMG_OUTPUT}"
echo ""
echo "  To distribute:"
echo "    1. Code-sign (optional but recommended):"
echo "       codesign --force --deep --sign - '${APP_BUNDLE}'"
echo "    2. Notarize with Apple (for Gatekeeper):"
echo "       xcrun notarytool submit '${DMG_OUTPUT}' --keychain-profile 'mediagrab' --wait"
echo ""
echo "  Without code-signing, users must right-click > Open on first launch."
echo "============================================================"
