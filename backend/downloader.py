"""
MediaGrab - Core Download Engine
"""

import asyncio
import os
import re
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import psutil
import requests
import yt_dlp

# ──────────────────────────────────────────────
# Download folder configuration
# ──────────────────────────────────────────────

MEDIAGRAB_ROOT = str(Path.home() / "Downloads" / "MediaGrab")


def sanitize_folder_name(name: str) -> str:
    name = re.sub(r'[<>:"/\|?*]', "", name)
    name = re.sub(r"\s+", " ", name).strip(". ")
    return name[:120] or "Playlist"


def resolve_output_dir(base_dir: str | None = None, playlist_name: str | None = None) -> str:
    if base_dir is None:
        base_dir = MEDIAGRAB_ROOT
    os.makedirs(base_dir, exist_ok=True)

    if playlist_name is None:
        return base_dir

    safe_name = sanitize_folder_name(playlist_name)
    candidate = os.path.join(base_dir, safe_name)

    if not os.path.exists(candidate):
        os.makedirs(candidate, exist_ok=True)
        return candidate

    counter = 2
    while True:
        numbered = os.path.join(base_dir, f"{safe_name} ({counter})")
        if not os.path.exists(numbered):
            os.makedirs(numbered, exist_ok=True)
            return numbered
        counter += 1


# ──────────────────────────────────────────────
# FFmpeg Locator
# ──────────────────────────────────────────────

class FFmpegLocator:
    _path: str | None = None

    @classmethod
    def find_ffmpeg(cls) -> str | None:
        if cls._path is not None:
            return cls._path

        ext = ".exe" if os.name == "nt" else ""

        candidates = [
            Path(__file__).parent.parent / "ffmpeg" / "bin" / f"ffmpeg{ext}",
            Path(__file__).parent / "ffmpeg" / "bin" / f"ffmpeg{ext}",
        ]

        for candidate in candidates:
            if candidate.exists():
                cls._path = str(candidate)
                return cls._path

        sys_path = shutil.which("ffmpeg")
        if sys_path:
            cls._path = sys_path

        return cls._path


# ──────────────────────────────────────────────
# Platform detection
# ──────────────────────────────────────────────

# Import shared platform detection
sys.path.append(str(Path(__file__).parent.parent))
from shared.platform_detection import (
    detect_platform, 
    validate_url, 
    get_platform_patterns
)
from shared.yt_dlp_helper import build_yt_dlp_command

# Import caching system
from cache import url_analysis_cache, format_cache

PLATFORM_PATTERNS = get_platform_patterns()


def sanitize_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "", name).strip()


# ──────────────────────────────────────────────
# URL Analysis
# ──────────────────────────────────────────────

def _analyze_url_sync(url: str) -> dict:
    ydl_opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "ignoreerrors": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        raise ValueError(f"Could not analyze URL: {e}")

    if not info:
        raise ValueError("No information found for this URL.")

    platform = detect_platform(url)
    is_playlist = info.get("_type") == "playlist" or "entries" in info

    if is_playlist:
        raw_entries = info.get("entries") or []
        entries = []
        for e in raw_entries:
            if e is None:
                continue
            dur = e.get("duration")
            entries.append({
                "title": e.get("title", "Unknown"),
                "id": e.get("id", ""),
                "url": e.get("url") or (f"https://www.youtube.com/watch?v={e.get('id')}" if platform == "youtube" else ""),
                "duration": dur,
                "duration_str": f"{int(dur // 60)}:{int(dur % 60):02d}" if dur else "N/A",
            })
        return {
            "type": "playlist",
            "platform": platform,
            "title": info.get("title", "Unknown Playlist"),
            "count": len(entries),
            "entries": entries,
        }
    else:
        dur = info.get("duration")
        return {
            "type": "video",
            "platform": platform,
            "title": info.get("title", "Unknown"),
            "uploader": info.get("uploader", "Unknown"),
            "duration": dur,
            "duration_str": f"{int(dur // 60)}:{int(dur % 60):02d}" if dur else "N/A",
            "thumbnail": info.get("thumbnail"),
            "view_count": info.get("view_count"),
            "description": (info.get("description") or "")[:300],
        }


async def analyze_url(url: str) -> dict:
    # Check cache first
    cache_key = f"analyze:{url}"
    cached_result = url_analysis_cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    # Perform analysis
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _analyze_url_sync, url)
    
    # Cache the result
    url_analysis_cache.set(cache_key, result)
    
    return result


# ──────────────────────────────────────────────
# Format / Quality Enumeration
# ──────────────────────────────────────────────

def _get_formats_sync(url: str) -> list:
    ydl_opts: dict[str, Any] = {"quiet": True, "no_warnings": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        qualities: dict = {}
        for fmt in info.get("formats", []):
            if fmt.get("vcodec") != "none":
                height = fmt.get("height")
                if height:
                    key = f"{height}p"
                    if key not in qualities:
                        qualities[key] = {
                            "height": height,
                            "fps": fmt.get("fps", 30),
                        }
        return [
            {"label": k, "height": v["height"], "fps": v["fps"]}
            for k, v in sorted(qualities.items(), key=lambda x: x[1]["height"], reverse=True)
        ]
    except Exception:
        return []


async def get_formats(url: str) -> list:
    # Check cache first
    cache_key = f"formats:{url}"
    cached_result = format_cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    # Perform format analysis
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _get_formats_sync, url)
    
    # Cache the result
    format_cache.set(cache_key, result)
    
    return result


# ──────────────────────────────────────────────
# Shared progress schema
# ──────────────────────────────────────────────

def _make_progress(
    *,
    status: str,
    progress: float = 0,
    message: str = "",
    filename: str = "",
    speed: str = "",
    eta: str = "",
    current_item: int | None = None,
    total_items: int | None = None,
    output_dir: str | None = None,
) -> dict:
    return {
        "status": status,
        "progress": round(progress, 1),
        "message": message,
        "filename": filename,
        "speed": speed,
        "eta": eta,
        "current_item": current_item,
        "total_items": total_items,
        "output_dir": output_dir,
    }


# ──────────────────────────────────────────────
# Download Engine
# ──────────────────────────────────────────────

class VideoDownloader:
    def __init__(
        self,
        url: str,
        fmt: str,
        quality: str,
        output_dir: str,
        task_id: str,
        downloads: dict,
        playlist_items: list[int] = [],
    ):
        self.url = url
        self.fmt = fmt
        self.quality = quality
        self.base_output_dir = output_dir or MEDIAGRAB_ROOT
        self.output_dir = self.base_output_dir
        self.final_output_dir = self.base_output_dir
        self.task_id = task_id
        self.downloads = downloads
        self.playlist_items = playlist_items
        self.total_items = len(playlist_items) if playlist_items else 0

        self.process: subprocess.Popen | None = None
        self._status: str = "pending"
        self._last_line: str = ""
        self._filename: str = ""

    def _update(self, **kwargs) -> None:
        current = self.downloads.get(self.task_id, {})
        self.downloads[self.task_id] = {**current, **_make_progress(**kwargs)}

    def _build_opts(self) -> dict:
        opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "outtmpl": os.path.join(self.output_dir, "%(title)s.%(ext)s"),
        }

        if self.fmt == "mp3":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        elif self.fmt == "original":
            opts["format"] = "best"
        else:
            opts["format"] = self.quality if self.quality != "best" else "bestvideo+bestaudio/best"
            opts["merge_output_format"] = "mp4"

        return opts

    def _get_yt_dlp_cmd(self) -> list[str]:
        is_playlist = "playlist" in self.url.lower() or "list=" in self.url
        ffmpeg_path = FFmpegLocator.find_ffmpeg()
        
        # Standardize playlist item indexing (1-based for yt-dlp)
        items = [i + 1 for i in self.playlist_items] if self.playlist_items else None

        return build_yt_dlp_command(
            url=self.url,
            output_dir=self.output_dir,
            fmt=self.fmt,
            quality=self.quality,
            ffmpeg_path=ffmpeg_path,
            is_playlist=is_playlist,
            playlist_items=items
        )

    def pause(self) -> bool:
        if self.process and self.process.poll() is None:
            try:
                p = psutil.Process(self.process.pid)
                p.suspend()
                self._status = "paused"
                self._update(status="paused", message="Paused")
                return True
            except Exception:
                return False
        return False

    def resume(self) -> bool:
        if self.process and self.process.poll() is None:
            try:
                p = psutil.Process(self.process.pid)
                p.resume()
                self._status = "downloading"
                self._update(status="downloading", message="Downloading…")
                return True
            except Exception:
                return False
        return False

    def cancel(self) -> None:
        self._status = "cancelled"
        if self.process and self.process.poll() is None:
            try:
                parent = psutil.Process(self.process.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
            except Exception:
                pass
        self.cleanup_partial()
        self._update(status="cancelled", message="Cancelled by user")

    def cleanup_partial(self) -> None:
        if not self.output_dir or not os.path.exists(self.output_dir):
            return
        for f in os.listdir(self.output_dir):
            if f.endswith((".part", ".ytdl", ".temp")) or ".f" in f:
                try:
                    os.remove(os.path.join(self.output_dir, f))
                except Exception:
                    pass

    def download(self) -> None:
        is_playlist = "playlist" in self.url.lower() or "list=" in self.url
        if is_playlist:
            try:
                with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True}) as ydl:
                    info = ydl.extract_info(self.url, download=False)
                    playlist_title = info.get("title", "Playlist")
                    self.total_items = info.get("count", len(info.get("entries", [])))
            except Exception:
                playlist_title = "Playlist"

            if self.playlist_items:
                self.total_items = len(self.playlist_items)

            self.final_output_dir = resolve_output_dir(self.base_output_dir, playlist_title)
            self.output_dir = self.final_output_dir
        else:
            self.final_output_dir = self.base_output_dir
            self.output_dir = self.base_output_dir
            os.makedirs(self.output_dir, exist_ok=True)

        cmd = self._get_yt_dlp_cmd()
        self._status = "downloading"
        self._update(status="downloading", progress=0, message="Starting…", output_dir=self.final_output_dir)

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding="utf-8",
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            for line in self.process.stdout:
                if self._status == "cancelled":
                    break

                line = line.strip()
                if not line:
                    continue
                self._last_line = line

                if "download:[" in line:
                    try:
                        parts = re.findall(r"\[(.*?)\]", line)
                        if len(parts) >= 4:
                            bytes_part = parts[0]
                            speed = parts[1]
                            eta = parts[2]
                            status = parts[3]

                            if "/" in bytes_part:
                                cur, tot = bytes_part.split("/")
                                # Enhanced validation to prevent division by zero
                                if (tot.isdigit() and int(tot) > 0 and 
                                    cur.isdigit() and int(cur) >= 0):
                                    pct = (int(cur) / int(tot)) * 100
                                    # Clamp percentage to reasonable bounds
                                    pct = max(0, min(100, pct))
                                    self._update(
                                        status="downloading",
                                        progress=pct,
                                        speed=speed,
                                        eta=eta,
                                        message=f"Downloading ({status})..."
                                    )
                    except Exception:
                        pass
                elif "[download] Destination:" in line:
                    self._filename = os.path.basename(line.split("Destination:", 1)[1].strip())
                    self._update(filename=self._filename)
                elif "[ExtractAudio]" in line:
                    self._update(status="processing", message="Extracting audio…", progress=99)

            self.process.wait()

            if self._status == "cancelled":
                return

            if self.process.returncode == 0:
                self._update(status="complete", progress=100, message="Download complete!", current_item=self.total_items)
            else:
                self._update(status="error", progress=0, message=f"Process exited with code {self.process.returncode}")

        except Exception as e:
            if self._status != "cancelled":
                self._update(status="error", progress=0, message=str(e))


# ──────────────────────────────────────────────
# Generic HTTP downloader
# ──────────────────────────────────────────────

class HttpDownloader:
    def __init__(self, url: str, output_dir: str, task_id: str, downloads: dict):
        self.url = url
        self.output_dir = output_dir or MEDIAGRAB_ROOT
        self.final_output_dir = self.output_dir
        self.task_id = task_id
        self.downloads = downloads
        self._cancelled = False

    def _update(self, **kwargs) -> None:
        self.downloads[self.task_id] = _make_progress(**kwargs)

    def cancel(self) -> None:
        self._cancelled = True

    def download(self) -> None:
        os.makedirs(self.output_dir, exist_ok=True)
        raw_name = self.url.split("/")[-1].split("?")[0] or "download"
        filename = sanitize_filename(raw_name) or "download"
        filepath = os.path.join(self.output_dir, filename)

        self._update(status="downloading", progress=0, message="Starting…",
                     filename=filename, current_item=None, total_items=None,
                     output_dir=self.final_output_dir)
        try:
            resp = requests.get(self.url, stream=True, timeout=30)
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if self._cancelled:
                        self._update(status="cancelled", progress=0,
                                     message="Cancelled", current_item=None, total_items=None,
                                     output_dir=self.final_output_dir)
                        return
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        pct = (downloaded / total * 100) if total else 0
                        self._update(
                            status="downloading",
                            progress=pct,
                            message="Downloading…",
                            filename=filename,
                            speed=f"{downloaded / (1024 * 1024):.1f} MB downloaded",
                            eta="",
                            current_item=None,
                            total_items=None,
                            output_dir=self.final_output_dir,
                        )

            self._update(status="complete", progress=100, message="Download complete!",
                         filename=filename, current_item=None, total_items=None,
                         output_dir=self.final_output_dir)
        except Exception as exc:
            self._update(status="error", progress=0, message=str(exc)[:200],
                         current_item=None, total_items=None,
                         output_dir=self.final_output_dir)
