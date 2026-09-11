"""
MediaGrab - Core Download Engine
"""

import asyncio
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

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
    is_playlist_url,
    validate_url,
    get_platform_patterns
)
from shared.yt_dlp_helper import (
    build_yt_dlp_command,
    normalize_quality,
    parse_progress_line,
)

# Import caching system
from cache import url_analysis_cache, format_cache

PLATFORM_PATTERNS = get_platform_patterns()


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = name.replace("\x00", "").strip().strip(".")
    return name[:180]


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


# Files yt-dlp leaves behind mid-download. ".fNNN." matches the per-stream
# fragments yt-dlp writes before merging; a plain ".f" substring would also
# match ordinary finished files such as "song.flac", so it is anchored.
_TEMP_SUFFIXES = (".part", ".ytdl", ".temp", ".tmp")
_FRAGMENT_RE = re.compile(r"\.f\d+\.[A-Za-z0-9]+$")


def _is_temp_artifact(name: str) -> bool:
    return name.endswith(_TEMP_SUFFIXES) or bool(_FRAGMENT_RE.search(name))


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
        playlist_items: list[int] | None = None,
    ):
        self.url = url
        self.fmt = fmt
        self.quality = quality
        self.base_output_dir = output_dir or MEDIAGRAB_ROOT
        self.output_dir = self.base_output_dir
        self.final_output_dir = self.base_output_dir
        self.task_id = task_id
        self.downloads = downloads
        self.playlist_items = list(playlist_items or [])
        self.total_items = len(self.playlist_items)

        self.process: subprocess.Popen | None = None
        self._status: str = "pending"
        self._last_line: str = ""
        self._filename: str = ""
        self._last_percent: float = 0.0
        self._current_item: int | None = None
        self._started_at: float = 0.0

    def _update(self, **kwargs) -> None:
        current = self.downloads.get(self.task_id, {})
        self.downloads[self.task_id] = {**current, **_make_progress(**kwargs)}

    def _get_yt_dlp_cmd(self) -> list[str]:
        is_playlist = is_playlist_url(self.url)
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
        """Remove only this download's leftover temp files.

        Finished media in the same folder must survive, so entries are matched
        against the yt-dlp temp patterns and against this task's start time.
        """
        if not self.output_dir or not os.path.isdir(self.output_dir):
            return
        for name in os.listdir(self.output_dir):
            if not _is_temp_artifact(name):
                continue
            path = os.path.join(self.output_dir, name)
            try:
                if not os.path.isfile(path):
                    continue
                if self._started_at and os.path.getmtime(path) < self._started_at:
                    continue
                os.remove(path)
            except OSError:
                pass

    def download(self) -> None:
        self._started_at = time.time()
        self._status = "downloading"
        is_playlist = is_playlist_url(self.url)
        if is_playlist:
            try:
                with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True}) as ydl:
                    info = ydl.extract_info(self.url, download=False)
                    playlist_title = info.get("title") or "Playlist"
                    self.total_items = (
                        info.get("playlist_count") or len(info.get("entries") or [])
                    )
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

                parsed = parse_progress_line(line)
                if parsed:
                    if parsed["percent"] is not None:
                        self._last_percent = parsed["percent"]
                    self._update(
                        status="downloading",
                        progress=self._last_percent,
                        speed=parsed["speed"],
                        eta=parsed["eta"],
                        message="Downloading…",
                        filename=self._filename,
                        current_item=self._current_item,
                        total_items=self.total_items or None,
                        output_dir=self.final_output_dir,
                    )
                elif "[download] Destination:" in line:
                    self._filename = os.path.basename(line.split("Destination:", 1)[1].strip())
                    self._update(
                        status="downloading",
                        progress=self._last_percent,
                        filename=self._filename,
                        message="Downloading…",
                        current_item=self._current_item,
                        total_items=self.total_items or None,
                        output_dir=self.final_output_dir,
                    )
                elif "[download] Downloading item" in line or "[download] Downloading video" in line:
                    match = re.search(r"(\d+)\s+of\s+(\d+)", line)
                    if match:
                        self._current_item = int(match.group(1))
                        self.total_items = int(match.group(2))
                elif "[ExtractAudio]" in line or "[Merger]" in line:
                    self._update(
                        status="processing",
                        message="Converting…",
                        progress=99,
                        filename=self._filename,
                        output_dir=self.final_output_dir,
                    )

            self.process.wait()

            if self._status == "cancelled":
                return

            if self.process.returncode == 0:
                self._status = "complete"
                self._update(
                    status="complete",
                    progress=100,
                    message="Download complete!",
                    filename=self._filename,
                    current_item=self.total_items or None,
                    total_items=self.total_items or None,
                    output_dir=self.final_output_dir,
                )
            else:
                self._status = "error"
                self.cleanup_partial()
                self._update(
                    status="error",
                    progress=0,
                    message=f"yt-dlp exited with code {self.process.returncode}: {self._last_line[:160]}",
                    output_dir=self.final_output_dir,
                )

        except FileNotFoundError:
            self._status = "error"
            self._update(
                status="error",
                progress=0,
                message="yt-dlp is not installed or could not be found on PATH.",
                output_dir=self.final_output_dir,
            )
        except Exception as e:
            if self._status != "cancelled":
                self._status = "error"
                self._update(
                    status="error",
                    progress=0,
                    message=str(e)[:200],
                    output_dir=self.final_output_dir,
                )


# ──────────────────────────────────────────────
# Generic HTTP downloader
# ──────────────────────────────────────────────

class HttpDownloader:
    # 64 KiB keeps LAN transfers fast without huge per-chunk overhead.
    CHUNK_SIZE = 64 * 1024

    def __init__(self, url: str, output_dir: str, task_id: str, downloads: dict):
        self.url = url
        self.output_dir = output_dir or MEDIAGRAB_ROOT
        self.final_output_dir = self.output_dir
        self.task_id = task_id
        self.downloads = downloads
        self._cancelled = False
        # /download/retry inspects _status on every downloader kind.
        self._status: str = "pending"

    def _update(self, **kwargs) -> None:
        current = self.downloads.get(self.task_id, {})
        self.downloads[self.task_id] = {**current, **_make_progress(**kwargs)}

    def cancel(self) -> None:
        self._cancelled = True
        self._status = "cancelled"

    def _resolve_filename(self, resp) -> str:
        """Pick a safe filename from Content-Disposition, else from the URL."""
        disposition = resp.headers.get("content-disposition", "")
        match = re.search(r'filename\*?=(?:UTF-8\'\'|")?([^";]+)', disposition)
        raw_name = match.group(1) if match else urlparse(self.url).path.rsplit("/", 1)[-1]
        name = sanitize_filename(unquote(raw_name))
        # sanitize_filename strips separators, so the result can never escape
        # output_dir; an empty or dot-only name falls back to a fixed default.
        return name or "download"

    def download(self) -> None:
        os.makedirs(self.output_dir, exist_ok=True)
        self._status = "downloading"
        filepath = None

        self._update(status="downloading", progress=0, message="Starting\u2026",
                     output_dir=self.final_output_dir)
        try:
            with requests.get(self.url, stream=True, timeout=30) as resp:
                resp.raise_for_status()
                filename = self._resolve_filename(resp)
                filepath = os.path.join(self.output_dir, filename)
                total = int(resp.headers.get("content-length") or 0)
                downloaded = 0
                last_emit = 0.0

                with open(filepath, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=self.CHUNK_SIZE):
                        if self._cancelled:
                            break
                        if not chunk:
                            continue
                        f.write(chunk)
                        downloaded += len(chunk)
                        now = time.time()
                        # Throttle so a fast LAN transfer does not flood the
                        # progress dict (and every websocket watching it).
                        if now - last_emit < 0.2:
                            continue
                        last_emit = now
                        self._update(
                            status="downloading",
                            progress=(downloaded / total * 100) if total else 0,
                            message="Downloading\u2026",
                            filename=filename,
                            speed=f"{downloaded / (1024 * 1024):.1f} MB downloaded",
                            output_dir=self.final_output_dir,
                        )

            if self._cancelled:
                self._cleanup(filepath)
                self._update(status="cancelled", progress=0, message="Cancelled by user",
                             output_dir=self.final_output_dir)
                return

            self._status = "complete"
            self._update(status="complete", progress=100, message="Download complete!",
                         filename=os.path.basename(filepath), output_dir=self.final_output_dir)
        except Exception as exc:
            if self._cancelled:
                self._cleanup(filepath)
                self._update(status="cancelled", progress=0, message="Cancelled by user",
                             output_dir=self.final_output_dir)
                return
            self._status = "error"
            self._cleanup(filepath)
            self._update(status="error", progress=0, message=str(exc)[:200],
                         output_dir=self.final_output_dir)

    @staticmethod
    def _cleanup(filepath: str | None) -> None:
        if filepath and os.path.isfile(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass
