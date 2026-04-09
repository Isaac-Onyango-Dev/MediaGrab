"""
MediaGrab – FastAPI Backend
Serves the Android mobile app over LAN/Wi-Fi.

Run:    uvicorn main:app --host 0.0.0.0 --port 8000
Docker: docker compose up
"""

from __future__ import annotations

import asyncio
import os
import sys
import json
import uuid
import time
import shutil
import socket
from contextlib import asynccontextmanager
from pathlib import Path

# --- BOOTSTRAP PATH ---
# Ensures 'shared' module is found when running from 'backend/' or bundled
_base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _base_path not in sys.path:
    sys.path.insert(0, _base_path)
# ----------------------

from zeroconf import IPVersion, ServiceInfo, Zeroconf

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi.security.api_key import APIKeyHeader

from config import get_settings
from downloader import (
    HttpDownloader,
    VideoDownloader,
    analyze_url,
    detect_platform,
    get_formats,
    validate_url,
    MEDIAGRAB_ROOT,
    resolve_output_dir,
)
from shared.logger import setup_logger
from storage_manager import ServerStorageManager

# Initialize standardized logger
logger = setup_logger("backend")

# Import caching system
from cache import url_analysis_cache, format_cache

# NOTE: Donation endpoints below are optional. They require payment provider
# configuration (Flutterwave, Stripe, NOWPayments, etc.) in environment variables.
# The website now uses Ko-fi, GitHub Sponsors, and Open Collective directly.
# from donation import handler as donation_handler

# Read version from central VERSION file
VERSION_FILE = Path(__file__).parent.parent / "VERSION"
APP_VERSION = VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else "0.0.0"

settings = get_settings()

limiter = Limiter(key_func=get_remote_address)

# ─────────────────────────────────────────────
# Optional API Key Authentication
# ─────────────────────────────────────────────

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key_header: str = Security(API_KEY_HEADER)):
    """Validate API key - authentication is mandatory for security."""
    if not settings.api_key:
        logger.warning("API key not configured - running in insecure mode (Home Use)")
        return  # Allow access in development/home mode
    
    if not api_key_header:
        raise HTTPException(status_code=401, detail="API key required")
    
    if api_key_header != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return

downloads:  dict[str, dict] = {}
instances:  dict[str, VideoDownloader | HttpDownloader] = {}
task_times: dict[str, float] = {}
task_owners:  dict[str, str] = {}  # task_id -> client_identifier

DEFAULT_OUT = MEDIAGRAB_ROOT


def _get_client_identifier(request: Request) -> str:
    """Extract a unique client identifier from request headers or IP."""
    # Try to get from header first (more reliable)
    client_id = request.headers.get("X-Client-ID")
    if client_id:
        return client_id

    # Fall back to IP address
    client_host = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "unknown")
    return f"{client_host}:{hash(user_agent) % 10000}"


def _verify_task_ownership(task_id: str, request: Request) -> None:
    """Verify that the client owns this task."""
    client_id = _get_client_identifier(request)
    owner_id = task_owners.get(task_id)

    if owner_id is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if owner_id != client_id:
        raise HTTPException(status_code=403, detail="Access denied: task belongs to another client")


async def _cleanup_loop() -> None:
    while True:
        await asyncio.sleep(300)
        now = time.time()
        
        # Clean up expired tasks
        to_del = [
            tid for tid, ts in list(task_times.items())
            if now - ts > 3600
        ]
        for tid in to_del:
            downloads.pop(tid, None)
            instances.pop(tid, None)
            task_times.pop(tid, None)
            task_owners.pop(tid, None)
        
        # Clean up expired cache entries
        url_analysis_cache.cleanup_expired()
        format_cache.cleanup_expired()


@asynccontextmanager
async def lifespan(application: FastAPI):
    ip_addr = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_addr = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    info = ServiceInfo(
        "_mediagrab._tcp.local.",
        "MediaGrab Server._mediagrab._tcp.local.",
        addresses=[socket.inet_aton(ip_addr)],
        port=8000,
        properties={"version": APP_VERSION, "path": "/"},
        server="mediagrab.local.",
    )
    zc = Zeroconf(ip_version=IPVersion.V4Only)
    zc.register_service(info)

    cleanup_task = asyncio.create_task(_cleanup_loop())

    yield

    cleanup_task.cancel()
    zc.unregister_service(info)
    zc.close()


app = FastAPI(
    title="MediaGrab API",
    description="Universal Video Downloader – REST + WebSocket API",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class AnalyzeRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    fmt: str = "mp3"
    quality: str = "best"
    output_dir: str = DEFAULT_OUT
    playlist_items: list[int] = []


class PlaylistDownloadRequest(BaseModel):
    selected_urls: list[str]
    playlist_name: str
    fmt: str = "mp3"
    quality: str = "best"
    output_dir: str = DEFAULT_OUT


def _assert_valid_url(url: str) -> None:
    if len(url) > 2048:
        raise HTTPException(status_code=400, detail="URL exceeds maximum length.")
    if not validate_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL — must start with http:// or https://")


def _assert_safe_output_dir(path: str) -> None:
    """
    Ensures the given relative path is safe and stays within the permitted root.
    """
    settings = get_settings()
    root = Path(settings.output_dir).expanduser().resolve()
    
    try:
        # Prevent any absolute paths or current/parent directory references in input
        if os.path.isabs(path) or ".." in path or ":" in path:
             raise HTTPException(status_code=400, detail="Invalid path - only relative subfolders are allowed.")

        # Resolve the final path
        # We join root with the provided path. If path is empty, it's just root.
        resolved = (root / path).expanduser().resolve()
        
        # Security: The resolved path must be root itself or a descendant of root
        if not str(resolved).startswith(str(root)):
            raise HTTPException(status_code=400, detail="Security error: Path traversal detected.")
            
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Invalid output path configuration.")


def _sanitize_playlist_name(name: str) -> str:
    """Remove dangerous characters and limit length for playlist names."""
    import re
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    if not sanitized or len(sanitized) == 0:
        raise HTTPException(status_code=400, detail="Invalid playlist name")
    return sanitized[:120]


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": APP_VERSION,
        "uptime": time.time(),
    }


@app.post("/analyze")
@limiter.limit("15/minute")
async def analyze(req: AnalyzeRequest, request: Request, _=Depends(verify_api_key)):
    _assert_valid_url(req.url)
    try:
        result = await analyze_url(req.url)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")


@app.post("/formats")
@limiter.limit("15/minute")
async def formats(req: AnalyzeRequest, request: Request, _=Depends(verify_api_key)):
    _assert_valid_url(req.url)
    fmts = await get_formats(req.url)
    return {"formats": fmts}


@app.post("/download/start")
@limiter.limit("5/minute")
async def start_download(req: DownloadRequest, request: Request, _=Depends(verify_api_key)):
    _assert_valid_url(req.url)
    _assert_safe_output_dir(req.output_dir)

    task_id = str(uuid.uuid4())
    client_id = _get_client_identifier(request)
    
    downloads[task_id] = {
        "status": "pending",
        "progress": 0,
        "message": "Queued",
        "filename": "",
        "speed": "",
        "eta": "",
        "current_item": None,
        "total_items": None,
    }
    task_times[task_id] = time.time()
    task_owners[task_id] = client_id

    platform = detect_platform(req.url)
    root = Path(get_settings().output_dir).expanduser().resolve()
    output = str((root / (req.output_dir or "")).resolve())

    if platform == "generic_http":
        inst = HttpDownloader(
            url=req.url, output_dir=output,
            task_id=task_id, downloads=downloads,
        )
    else:
        inst = VideoDownloader(
            url=req.url, fmt=req.fmt, quality=req.quality,
            output_dir=output, task_id=task_id, downloads=downloads,
            playlist_items=req.playlist_items,
        )

    instances[task_id] = inst

    loop = asyncio.get_running_loop()
    asyncio.create_task(loop.run_in_executor(None, inst.download))

    return {"task_id": task_id}


@app.post("/download/playlist")
@limiter.limit("5/minute")
async def start_playlist_download(req: PlaylistDownloadRequest, request: Request, _=Depends(verify_api_key)):
    if not req.selected_urls or len(req.selected_urls) == 0:
        raise HTTPException(status_code=400, detail="No URLs selected")

    for url in req.selected_urls:
        if not validate_url(url):
            raise HTTPException(status_code=400, detail=f"Invalid URL: {url}")

    _assert_safe_output_dir(req.output_dir)

    task_id = str(uuid.uuid4())
    client_id = _get_client_identifier(request)
    total_items = len(req.selected_urls)

    downloads[task_id] = {
        "status": "pending",
        "progress": 0,
        "message": "Queued",
        "filename": "",
        "speed": "",
        "eta": "",
        "output_dir": req.output_dir,
        "items_done": 0,
        "items_total": total_items,
    }
    task_times[task_id] = time.time()
    task_owners[task_id] = client_id

    root = Path(get_settings().output_dir).expanduser().resolve()
    output = str((root / (req.output_dir or "")).resolve())
    safe_playlist_name = _sanitize_playlist_name(req.playlist_name)
    final_output = resolve_output_dir(output, safe_playlist_name)

    async def batch_download() -> None:
        for idx, url in enumerate(req.selected_urls):
            if downloads.get(task_id, {}).get("status") == "cancelled":
                downloads[task_id]["status"] = "cancelled"
                downloads[task_id]["message"] = "Cancelled by user"
                return

            downloads[task_id]["items_done"] = idx
            downloads[task_id]["message"] = f"Downloading item {idx + 1}/{total_items}…"

            try:
                platform = detect_platform(url)

                if platform == "generic_http":
                    dl = HttpDownloader(
                        url=url, output_dir=final_output,
                        task_id=task_id, downloads=downloads,
                    )
                else:
                    dl = VideoDownloader(
                        url=url, fmt=req.fmt, quality=req.quality,
                        output_dir=final_output,
                        task_id=task_id, downloads=downloads,
                        playlist_items=[],
                    )

                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, dl.download)

            except Exception as e:
                downloads[task_id]["status"] = "error"
                downloads[task_id]["message"] = f"Error downloading item {idx + 1}: {str(e)[:100]}"
                return

        downloads[task_id]["status"] = "complete"
        downloads[task_id]["progress"] = 100
        downloads[task_id]["items_done"] = total_items
        downloads[task_id]["message"] = "All items downloaded!"
        downloads[task_id]["output_dir"] = final_output

    loop = asyncio.get_running_loop()
    asyncio.create_task(batch_download())

    return {"task_id": task_id}


@app.get("/download/progress/{task_id}")
async def get_progress(task_id: str, request: Request, _=Depends(verify_api_key)):
    _verify_task_ownership(task_id, request)
    return downloads[task_id]


@app.get("/download/list")
async def list_downloads(request: Request, _=Depends(verify_api_key)):
    client_id = _get_client_identifier(request)
    return {
        "tasks": [
            {"task_id": tid, **data}
            for tid, data in downloads.items()
            if task_owners.get(tid) == client_id
        ]
    }


@app.post("/download/cancel/{task_id}")
async def cancel_download(task_id: str, request: Request, _=Depends(verify_api_key)):
    _verify_task_ownership(task_id, request)
    if task_id not in instances:
        raise HTTPException(status_code=404, detail="Task not found")
    downloads[task_id]["status"] = "cancelled"
    downloads[task_id]["message"] = "Cancelled by user"
    instances[task_id].cancel()
    return {"status": "cancelled"}


@app.post("/download/pause/{task_id}")
async def pause_download(task_id: str, request: Request, _=Depends(verify_api_key)):
    _verify_task_ownership(task_id, request)
    if task_id not in instances:
        raise HTTPException(status_code=404, detail="Task not found")
    inst = instances[task_id]
    if isinstance(inst, VideoDownloader):
        success = inst.pause()
        if success:
            return {"status": "paused"}
    raise HTTPException(status_code=400, detail="Cannot pause this type of download")


@app.post("/download/resume/{task_id}")
async def resume_download(task_id: str, request: Request, _=Depends(verify_api_key)):
    _verify_task_ownership(task_id, request)
    if task_id not in instances:
        raise HTTPException(status_code=404, detail="Task not found")
    inst = instances[task_id]
    if isinstance(inst, VideoDownloader):
        success = inst.resume()
        if success:
            return {"status": "resuming"}
    raise HTTPException(status_code=400, detail="Cannot resume this type of download")


@app.post("/download/retry/{task_id}")
async def retry_download(task_id: str, background_tasks: BackgroundTasks, request: Request, _=Depends(verify_api_key)):
    _verify_task_ownership(task_id, request)
    if task_id not in instances:
        raise HTTPException(status_code=404, detail="Task not found")

    inst = instances[task_id]
    if inst._status in ("cancelled", "error", "complete"):
        downloads[task_id]["status"] = "pending"
        downloads[task_id]["progress"] = 0
        loop = asyncio.get_running_loop()
        asyncio.create_task(loop.run_in_executor(None, inst.download))
        return {"status": "retrying"}

    raise HTTPException(status_code=400, detail="Terminal state required for retry")


@app.delete("/download/{task_id}")
async def delete_download(task_id: str, request: Request, delete_file: bool = False, _=Depends(verify_api_key)):
    _verify_task_ownership(task_id, request)
    if task_id not in downloads:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_id in instances:
        inst = instances[task_id]
        if hasattr(inst, "cancel"):
            inst.cancel()

    if delete_file and task_id in downloads:
        progress = downloads[task_id]
        if progress.get("output_dir") and progress.get("filename"):
            path = Path(progress["output_dir"]) / progress["filename"]
            if path.exists():
                try:
                    path.unlink()
                except Exception:
                    pass

    downloads.pop(task_id, None)
    instances.pop(task_id, None)
    task_times.pop(task_id, None)
    task_owners.pop(task_id, None)
    return {"status": "deleted"}


@app.post("/download/clear")
async def clear_history(request: Request, _=Depends(verify_api_key)):
    client_id = _get_client_identifier(request)
    to_del = [
        tid for tid, data in downloads.items()
        if data["status"] in ("complete", "error", "cancelled") and task_owners.get(tid) == client_id
    ]
    for tid in to_del:
        downloads.pop(tid, None)
        instances.pop(tid, None)
        task_times.pop(tid, None)
        task_owners.pop(tid, None)
    return {"count": len(to_del)}


@app.delete("/download/clean/{task_id}")
async def clean_task(task_id: str, request: Request, _=Depends(verify_api_key)):
    return await delete_download(task_id, request)


@app.websocket("/ws/{task_id}")
async def ws_progress(ws: WebSocket, task_id: str):
    await ws.accept()
    try:
        while True:
            if task_id in downloads:
                data = downloads[task_id]
                await ws.send_json(data)
                if data["status"] in ("complete", "error", "cancelled"):
                    break
            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass
