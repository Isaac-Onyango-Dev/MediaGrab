# MediaGrab

MediaGrab is a universal video and audio downloader packaged as a native app for Windows, macOS, Linux, and Android.

It supports YouTube, TikTok, Instagram, Twitter/X, Vimeo, Reddit, and dozens of other platforms, leveraging 
`yt-dlp` and `FFmpeg`.

## Structure

- **`desktop/`**: Standalone GUI desktop app built with CustomTkinter. Contains bundled yt-dlp dependencies.
- **`backend/`**: FastAPI REST + WebSocket server. Handles downloading on a host machine under remote control.
- **`mobile/`**: React Native (Expo) Android app. Connects to the backend over Wi-Fi to manage downloads.

## 1. Desktop App Quick Start

The desktop app is standalone and runs on Windows, macOS, and Linux. Ensure you have `ffmpeg` installed on your system.

**Run locally:**
```bash
cd desktop
pip install -r requirements.txt
python main.py
```

**Build executable:**
```bash
# Windows
pyinstaller --noconfirm --onefile --windowed --name "MediaGrab" --add-data "assets;assets" --hidden-import "customtkinter" --hidden-import "yt_dlp" --hidden-import "PIL" --hidden-import "requests" main.py

# macOS / Linux
pyinstaller --noconfirm --onedir --windowed --name "MediaGrab" --add-data "assets:assets" --hidden-import "customtkinter" --hidden-import "yt_dlp" --hidden-import "PIL" --hidden-import "requests" main.py
```

## 2. Server Quick Start

The backend server is required if you want to use the Mobile app. It acts as the download engine remote controller.

**Run Locally:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```
*(You may want to copy `.env.example` to `.env` to customize settings)*

**Run via Docker:**
```bash
cd backend
docker compose up -d
```

## 3. Mobile App Quick Start

The Android app acts as a remote control for the backend.

1. Ensure the `backend` is running on your network (e.g., `192.168.1.10:8000`).
2. Run the Expo development server:
```bash
cd mobile
npm install
npx expo start
```
3. Open on your Android device using the Expo Go app.
4. Go to **Settings** in the app and set your Backend Server URL (e.g., `http://192.168.1.10:8000`).

*(To build a standalone APK, refer to `.github/workflows/build-mobile.yml` or run `npm run build:debug`)*
