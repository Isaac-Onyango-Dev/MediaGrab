# Mobile

Android app for MediaGrab video downloader built with React Native/Expo.

## Directory Structure

```
mobile/
├── screens/          # Navigation screens
│   ├── HomeScreen.tsx      - URL input & video preview
│   ├── DownloadScreen.tsx  - Format selection & progress
│   └── SettingsScreen.tsx  - Backend URL configuration
├── components/       # Reusable UI components
├── hooks/           # Custom React hooks
├── services/        # API client & services
├── App.tsx          # Root navigator
└── app.json         # Expo configuration
```

## Setup

```bash
# Install dependencies
npm install

# Start development  
npm start

# Build for Android
npm run android

# Create production APK
npm run build:release
```

## Features

- Connect to FastAPI backend
- Real-time download progress via WebSocket
- Multiple format/quality selection
- Async storage for saved preferences
- Works completely offline with local caching

## Configuration

Edit `app.json` for:
- App name and version
- Android package name
- API endpoint

## Notes

- No Expo Application Services (EAS) required
- Completely free build process
- Android-only (iOS intentionally excluded)
