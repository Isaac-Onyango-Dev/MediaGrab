# Desktop

GUI application for MediaGrab video downloader running on Windows, macOS, and Linux.

## Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# System dependencies (required)
# Windows: Download FFmpeg from https://ffmpeg.org/download.html
# macOS: brew install ffmpeg
# Linux: sudo apt-get install ffmpeg  (Ubuntu/Debian) or dnf install ffmpeg (Fedora)

# Run the GUI
python main.py
```

## Architecture

- **Fully Self-Contained**: yt-dlp engine is bundled inside the executable
- **No Backend Required**: Works completely standalone (offline)
- **Platform Detection**: Auto-detects OS and optimizes accordingly
- **Direct Downloads**: Saves videos/audio directly to local folder

## Features

- CustomTkinter-based modern UI
- Format and quality selection
- Real-time progress tracking
- Video and audio extraction
- Batch download support
- Cross-platform (Windows, macOS, Linux)

## Build Instructions

### Windows (.exe)

```bash
build_windows.bat
# Output: dist/MediaGrab-Windows.exe
```

### macOS (.dmg)

```bash
bash build_mac.sh
# Output: dist/MediaGrab-macOS.dmg
```

### Linux (.AppImage)

```bash
bash build_linux.sh
# Output: dist/MediaGrab-Linux.AppImage
```

## Assets

Add to `assets/` folder:
- `icon.ico` - Windows application icon (256×256 minimum)
- `icon.icns` - macOS application icon (512×512 minimum)
- `icon.png` - Linux application icon (512×512 minimum)

## Dependencies

### Python Packages
- `customtkinter` - Modern UI framework
- `yt-dlp` - Core download engine (bundled in executable)
- `Pillow` - Image handling
- `pyinstaller` - Executable building
- `ffmpeg-python` - FFmpeg interface

### System Dependencies
- **Python** 3.10+
- **FFmpeg** (required for audio extraction and video merging)
  - Windows: Download from https://ffmpeg.org/download.html
  - macOS: `brew install ffmpeg`
  - Linux: `apt-get install ffmpeg` or equivalent

## Notes

- Fully self-contained: yt-dlp engine is bundled in the executable
- Works offline after initial download of yt-dlp (local executable contains everything needed)
- FFmpeg must be installed as a system dependency for audio/video processing
- Can optionally connect to backend API for advanced features
- Fully open-source and free to distribute
