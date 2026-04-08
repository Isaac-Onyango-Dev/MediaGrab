#!/bin/bash
set -euo pipefail

# ============================================================
# MediaGrab Linux Build Script
# Produces:
#   - AppImage  (if appimagetool is available)
#   - portable .tar.gz (always)
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_DIR="$SCRIPT_DIR"
ASSETS_DIR="$DESKTOP_DIR/assets"
VERSION="$(cat "$PROJECT_ROOT/VERSION" 2>/dev/null || echo '1.0.6')"
APP_NAME="MediaGrab"
APP_BINARY="$APP_NAME"
ARCH="x86_64"

DIST_DIR="$DESKTOP_DIR/dist"
APPDIR="$DIST_DIR/AppDir"

# ---------- colours ----------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ---------- helpers ----------
command_exists() { command -v "$1" &>/dev/null; }

clean() {
    info "Cleaning previous build artifacts..."
    rm -rf "$DIST_DIR" "$DESKTOP_DIR/build" "$DESKTOP_DIR/${APP_NAME}.spec"
}

# ============================================================
# 1. Build PyInstaller executable
# ============================================================
build_executable() {
    info "Building PyInstaller executable..."

    cd "$DESKTOP_DIR"

    pyinstaller --noconfirm --onefile \
        --name "$APP_BINARY" \
        --add-data "assets:assets" \
        --add-data "../VERSION:." \
        --add-data "../shared:shared" \
        --collect-all "customtkinter" \
        --collect-all "yt_dlp" \
        --collect-all "PIL" \
        main.py

    # Move the binary into dist/ for the next stages
    mkdir -p "$DIST_DIR"
    if [ "$DESKTOP_DIR/dist/$APP_BINARY" != "$DIST_DIR/$APP_BINARY" ]; then
        cp "$DESKTOP_DIR/dist/$APP_BINARY" "$DIST_DIR/$APP_BINARY"
    fi

    info "Executable built: $DIST_DIR/$APP_BINARY"
}

# ============================================================
# 2. Assemble AppDir (for AppImage)
# ============================================================
assemble_appdir() {
    info "Assembling AppDir structure..."
    rm -rf "$APPDIR"
    mkdir -p "$APPDIR/usr/share/applications"
    mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

    # Executable - avoid copying to same location
    if [ "$DIST_DIR/$APP_BINARY" != "$APPDIR/$APP_BINARY" ]; then
        cp "$DIST_DIR/$APP_BINARY" "$APPDIR/$APP_BINARY"
    fi
    chmod +x "$APPDIR/$APP_BINARY"

    # AppRun symlink
    ln -sf "$APP_BINARY" "$APPDIR/AppRun"
    chmod +x "$APPDIR/AppRun"

    # Desktop entry
    cp "$DESKTOP_DIR/MediaGrab.desktop" "$APPDIR/$APP_NAME.desktop"
    cp "$DESKTOP_DIR/MediaGrab.desktop" "$APPDIR/usr/share/applications/$APP_NAME.desktop"

    # Icon (use PNG from assets)
    local icon_src="$ASSETS_DIR/icon.png"
    if [ -f "$icon_src" ]; then
        cp "$icon_src" "$APPDIR/mediagrab.png"
        cp "$icon_src" "$APPDIR/usr/share/icons/hicolor/256x256/apps/mediagrab.png"
        info "Icon installed from $icon_src"
    else
        warn "No icon.png found in assets/ — desktop entry will have no icon"
    fi

    # Bundled FFmpeg (if available on PATH or in a known location)
    local ffmpeg_path=""
    if command_exists ffmpeg; then
        ffmpeg_path="$(command -v ffmpeg)"
    elif [ -f "$DESKTOP_DIR/ffmpeg/bin/ffmpeg" ]; then
        ffmpeg_path="$DESKTOP_DIR/ffmpeg/bin/ffmpeg"
    fi

    if [ -n "$ffmpeg_path" ] && [ -f "$ffmpeg_path" ]; then
        mkdir -p "$APPDIR/ffmpeg"
        cp "$ffmpeg_path" "$APPDIR/ffmpeg/ffmpeg"
        chmod +x "$APPDIR/ffmpeg/ffmpeg"
        info "Bundled FFmpeg from $ffmpeg_path"
    else
        warn "FFmpeg not found — user must install ffmpeg separately"
    fi

    info "AppDir assembled at $APPDIR"
}

# ============================================================
# 3. Create AppImage (optional — requires appimagetool)
# ============================================================
create_appimage() {
    if ! command_exists appimagetool; then
        warn "appimagetool not found — skipping AppImage creation."
        warn "Install it from https://github.com/AppImage/AppImageKit/releases"
        return 0
    fi

    info "Creating AppImage..."

    local appimage_name="${APP_NAME}-${VERSION}-${ARCH}.AppImage"
    local appimage_path="$DIST_DIR/$appimage_name"

    # appimagetool expects the environment variable for the desktop file name
    (
        cd "$DIST_DIR"
        ARCH=x86_64 appimagetool AppDir "$appimage_name"
    )

    chmod +x "$appimage_path"
    info "AppImage created: $appimage_path"
}

# ============================================================
# 4. Create portable .tar.gz archive
# ============================================================
create_tarball() {
    info "Creating portable .tar.gz archive..."

    local tarball_name="${APP_NAME}-${VERSION}-linux-${ARCH}.tar.gz"
    local staging="$DIST_DIR/staging-${APP_NAME}-${VERSION}"

    rm -rf "$staging"
    mkdir -p "$staging"

    # Executable
    cp "$DIST_DIR/$APP_BINARY" "$staging/$APP_BINARY"

    # FFmpeg if we bundled one
    if [ -f "$APPDIR/ffmpeg/ffmpeg" ]; then
        mkdir -p "$staging/ffmpeg"
        cp "$APPDIR/ffmpeg/ffmpeg" "$staging/ffmpeg/ffmpeg"
        chmod +x "$staging/ffmpeg/ffmpeg"
    fi

    # Assets folder
    if [ -d "$ASSETS_DIR" ]; then
        cp -r "$ASSETS_DIR" "$staging/assets"
    fi

    # README with install instructions
    cat > "$staging/README.txt" <<EOF
MediaGrab ${VERSION} — Linux Portable

INSTALLATION
------------
1. Extract this archive:
     tar -xzf ${tarball_name}

2. Make the executable runnable:
     chmod +x ${APP_NAME}

3. Run:
     ./${APP_NAME}

OPTIONAL — Desktop Integration
-------------------------------
To add MediaGrab to your application menu:

  a) Copy the binary to a location in your PATH, e.g.:
       sudo cp ${APP_NAME} /usr/local/bin/

  b) Copy the desktop entry and icon:
       sudo cp ${APP_NAME}.desktop /usr/share/applications/
       sudo cp mediagrab.png /usr/share/icons/hicolor/256x256/apps/mediagrab.png

  c) Refresh the desktop database:
       update-desktop-database ~/.local/share/applications/ 2>/dev/null || true

REQUIREMENTS
------------
- Python runtime is NOT required (binary is self-contained via PyInstaller).
- FFmpeg: bundled if present; otherwise install via your package manager:
    Ubuntu/Debian:  sudo apt install ffmpeg
    Fedora:         sudo dnf install ffmpeg
    Arch:           sudo pacman -S ffmpeg

For more info visit the project repository.
EOF

    # Copy desktop file and icon into the tarball for manual install
    if [ -f "$DESKTOP_DIR/MediaGrab.desktop" ]; then
        cp "$DESKTOP_DIR/MediaGrab.desktop" "$staging/$APP_NAME.desktop"
    fi
    if [ -f "$APPDIR/mediagrab.png" ]; then
        cp "$APPDIR/mediagrab.png" "$staging/mediagrab.png"
    fi

    # Create tarball
    (
        cd "$DIST_DIR"
        tar -czf "$tarball_name" -C "$DIST_DIR" "$(basename "$staging")"
    )

    rm -rf "$staging"
    info "Portable archive created: $DIST_DIR/$tarball_name"
}

# ============================================================
# 5. Clean up staging artifacts
# ============================================================
cleanup_staging() {
    rm -rf "$DIST_DIR/staging-"*
}

# ============================================================
# MAIN
# ============================================================
main() {
    echo "========================================"
    echo "  MediaGrab ${VERSION} — Linux Build"
    echo "========================================"
    echo

    clean
    build_executable
    assemble_appdir
    create_appimage
    create_tarball
    cleanup_staging

    echo
    echo "========================================"
    echo "  Build complete!"
    echo "========================================"
    echo
    ls -lh "$DIST_DIR/"*.AppImage 2>/dev/null || true
    ls -lh "$DIST_DIR/"*.tar.gz 2>/dev/null || true
    echo
    info "Outputs are in: $DIST_DIR/"
}

main "$@"
