# Backend

Python FastAPI server for MediaGrab video downloader.

## Setup

```bash
pip install -r requirements.txt
python main.py
```

## Features

- FastAPI REST API for video analysis
- WebSocket support for real-time download progress
- yt-dlp engine for platform detection and format retrieval
- Async/await support

## Environment Variables

Create a `.env` file:
```
BACKEND_URL=http://localhost:8000
CORS_ORIGINS=*
```

## Docker

```bash
docker build -t mediagrab-backend .
docker run -p 8000:8000 mediagrab-backend
```

## API Endpoints

- `GET /api/analyze` - Analyze video metadata
- `WebSocket /ws/download` - Real-time download progress
- `POST /api/formats` - Get available formats
