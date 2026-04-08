"""
MediaGrab Desktop – Universal Video Downloader
Windows, macOS & Linux | Python 3.10+ | CustomTkinter + yt-dlp

Run:           python main.py
Build Windows: build_windows.bat
Build macOS:   ./build_mac.sh
Build Linux:   ./build_linux.sh
"""

from __future__ import annotations

# --- BOOTSTRAP PATH ---
# Ensures 'shared' module is found when running from 'desktop/' or bundled
import sys
import os
_base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _base_path not in sys.path:
    sys.path.insert(0, _base_path)
# ----------------------

import json
import os
import re
import subprocess
import sys
import threading
import uuid
import shutil
import zipfile
import tarfile
import tempfile
import platform
import time
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Callable
from urllib.parse import urlparse

import psutil
import customtkinter as ctk
import yt_dlp
import requests

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

APP_NAME = "MediaGrab"

# Version: Try VERSION file first, then fallback to hardcoded version
# This ensures it works both in development AND in PyInstaller builds
VERSION_FILE = Path(__file__).parent.parent / "VERSION"
_hc_version = "1.0.0"  # Hardcoded fallback for PyInstaller builds
try:
    APP_VERSION = VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else _hc_version
except Exception as e:
    import logging
    logging.warning(f"Failed to read VERSION file: {e}")
    APP_VERSION = _hc_version
# If running from PyInstaller, also check the bundled VERSION
if getattr(sys, "frozen", False):
    bundled_version = Path(sys._MEIPASS) / "VERSION"  # type: ignore[attr-defined]
    try:
        if bundled_version.exists():
            APP_VERSION = bundled_version.read_text().strip()
    except Exception as e:
        import logging
        logging.warning(f"Failed to read bundled VERSION file: {e}")
        # Keep hardcoded version

CONFIG_FILE = Path.home() / ".mediagrab_config.json"
HISTORY_FILE = Path.home() / ".mediagrab_history.json"
DEFAULT_DIR = str(Path.home() / "Downloads" / "MediaGrab")

# Import shared platform detection
import sys
sys.path.append(str(Path(__file__).parent.parent))
from shared.platform_detection import (
    detect_platform, 
    validate_url, 
    get_supported_platforms,
    get_platform_patterns
)
from shared.yt_dlp_helper import build_yt_dlp_command
from shared.logger import setup_logger

# Initialize standardized logger
logger = setup_logger("desktop")

SUPPORTED_PLATFORMS = get_supported_platforms()
PLATFORM_PATTERNS = get_platform_patterns()

# ─────────────────────────────────────────────
# FFmpeg Manager (Silent Auto-Installer)
# ─────────────────────────────────────────────

FFMPEG_URLS = {
    "win32": [
        "https://github.com/GyanD/codexffmpeg/releases/download/7.1/ffmpeg-7.1-essentials_build.zip",
        "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    ],
    "darwin": [
        "https://github.com/nicmcd/ffmpeg-static/releases/download/v6.0/ffmpeg-macos.zip",
        "https://evermeet.cx/ffmpeg/getrelease/zip",
    ],
    "linux": [],
}


def _get_linux_ffmpeg_urls() -> list[str]:
    machine = platform.machine()
    if machine in ("x86_64", "amd64"):
        arch = "amd64"
    elif machine in ("aarch64", "arm64"):
        arch = "arm64"
    else:
        arch = "amd64"
    return [
        f"https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-{arch}-static.tar.xz",
    ]


class FFmpegManager:
    def __init__(self):
        self.base_dir = Path(__file__).parent / "ffmpeg"
        self.bin_dir = self.base_dir / "bin"
        self.ffmpeg_path = self._resolve_ffmpeg_path()
        self.is_installed = self.ffmpeg_path is not None
        self.installing = False
        self.progress = 0

    def _resolve_ffmpeg_path(self) -> str | None:
        ext = ".exe" if sys.platform == "win32" else ""
        if getattr(sys, "frozen", False):
            base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
            candidate = base / "ffmpeg" / f"ffmpeg{ext}"
            if candidate.exists():
                return str(candidate.absolute())
        local_bin = self.bin_dir / f"ffmpeg{ext}"
        if local_bin.exists():
            return str(local_bin.absolute())
        sys_bin = shutil.which("ffmpeg")
        if sys_bin:
            return sys_bin
        return None

    def get_path(self) -> str | None:
        return self.ffmpeg_path

    def verify(self) -> bool:
        path = self.get_path()
        if not path:
            return False
        try:
            subprocess.run(
                [path, "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    def start_install(self, on_progress: Callable[[float], None], on_done: Callable[[], None], on_error: Callable[[str], None]):
        if self.installing:
            return
        self.installing = True
        threading.Thread(target=self._install_thread, args=(on_progress, on_done, on_error), daemon=True).start()

    def _install_thread(self, on_progress, on_done, on_error):
        archive_path: Path | None = None
        try:
            urls = FFMPEG_URLS.get(sys.platform, [])
            if sys.platform == "linux":
                urls = _get_linux_ffmpeg_urls()
            if not urls:
                raise Exception(f"No FFmpeg download URLs configured for platform: {sys.platform}")

            os.makedirs(self.base_dir, exist_ok=True)

            last_error = None
            for attempt, url in enumerate(urls):
                if attempt > 0:
                    time.sleep(2 ** attempt)
                try:
                    archive_path = self.base_dir / os.path.basename(urlparse(url).path)
                    with requests.get(url, stream=True, timeout=120) as r:
                        r.raise_for_status()
                        total = int(r.headers.get("content-length", 0))
                        downloaded = 0
                        with open(archive_path, "wb") as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total > 0:
                                    self.progress = (downloaded / total) * 100
                                    on_progress(self.progress)

                    on_progress(100)
                    self._extract(archive_path)
                    self.ffmpeg_path = self._resolve_ffmpeg_path()
                    if self.verify():
                        self.is_installed = True
                        self.installing = False
                        on_done()
                        return
                    else:
                        last_error = "Verification failed after install."
                        continue
                except Exception as e:
                    last_error = str(e)
                    if archive_path and archive_path.exists():
                        try:
                            os.remove(archive_path)
                        except OSError:
                            pass
                    archive_path = None
                    continue
            raise Exception(f"FFmpeg install failed after trying all sources. Last error: {last_error}")
        except Exception as e:
            self.installing = False
            on_error(str(e))
        finally:
            if archive_path and archive_path.exists():
                try:
                    os.remove(archive_path)
                except OSError:
                    pass

    def _extract(self, archive_path: Path):
        temp_extract = self.base_dir / "_temp"
        if temp_extract.exists():
            shutil.rmtree(temp_extract)
        os.makedirs(temp_extract, exist_ok=True)
        try:
            if archive_path.suffix == ".zip":
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    zip_ref.extractall(temp_extract)
            else:
                with tarfile.open(archive_path, "r:xz") as tar_ref:
                    tar_ref.extractall(temp_extract)
            ext = ".exe" if sys.platform == "win32" else ""
            bin_name = f"ffmpeg{ext}"
            found = False
            for root, _, files in os.walk(temp_extract):
                if bin_name in files:
                    os.makedirs(self.bin_dir, exist_ok=True)
                    shutil.move(os.path.join(root, bin_name), self.bin_dir / bin_name)
                    if f"ffprobe{ext}" in files:
                        shutil.move(os.path.join(root, f"ffprobe{ext}"), self.bin_dir / f"ffprobe{ext}")
                    found = True
                    break
            if not found:
                raise Exception("FFmpeg binary not found in archive.")
        finally:
            if temp_extract.exists():
                shutil.rmtree(temp_extract)


ffmpeg_mgr = FFmpegManager()


# ─────────────────────────────────────────────
# Update Manager (Auto-Update from GitHub Releases)
# ─────────────────────────────────────────────

class UpdateManager:
    REPO_OWNER = "Isaac-Onyango-Dev"
    REPO_NAME = "MediaGrab"
    CURRENT_VERSION = APP_VERSION

    def __init__(self):
        self.platform = self._detect_platform()

    def _detect_platform(self) -> str:
        if sys.platform == "win32":
            return "windows"
        if sys.platform == "darwin":
            return "macos"
        return "linux"

    def check_for_updates(self) -> dict | None:
        try:
            url = f"https://api.github.com/repos/{self.REPO_OWNER}/{self.REPO_NAME}/releases/latest"
            resp = requests.get(url, timeout=10, headers={"Accept": "application/vnd.github.v3+json"})
            resp.raise_for_status()
            release = resp.json()
            latest_tag = release.get("tag_name", "").lstrip("v")
            if not latest_tag:
                return None
            if self._compare_versions(self.CURRENT_VERSION, latest_tag) < 0:
                return {
                    "version": latest_tag,
                    "release": release,
                    "notes": release.get("body", "No release notes available."),
                }
        except Exception:
            pass
        return None

    def _compare_versions(self, current: str, latest: str) -> int:
        def parse(v: str) -> tuple:
            try:
                return tuple(int(x) for x in v.split("."))
            except (ValueError, AttributeError):
                return (0, 0, 0)
        a, b = parse(current), parse(latest)
        if a < b:
            return -1
        if a > b:
            return 1
        return 0

    def _select_asset(self, release: dict) -> tuple[str, str] | None:
        for asset in release.get("assets", []):
            name = asset.get("name", "").lower()
            if self.platform == "windows" and ("windows" in name or name.endswith(".exe")):
                return asset["browser_download_url"], asset["name"]
            if self.platform == "macos" and ("macos" in name or name.endswith(".dmg")):
                return asset["browser_download_url"], asset["name"]
            if self.platform == "linux" and "linux" in name and ".exe" not in name and ".dmg" not in name:
                return asset["browser_download_url"], asset["name"]
        return None

    def download_update(self, url: str, on_progress: Callable[[float], None]) -> str:
        filename = url.split("/")[-1]
        dest = Path(tempfile.gettempdir()) / filename
        resp = requests.get(url, stream=True, timeout=300)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    on_progress((downloaded / total) * 100)
        return str(dest)

    def install_update(self, file_path: str) -> None:
        if self.platform == "windows":
            # Launch the installer with user consent
            subprocess.Popen([file_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
            # Give the installer time to start before we exit
            import time
            time.sleep(2)
            sys.exit(0)
        elif self.platform == "macos":
            subprocess.run(["hdiutil", "attach", file_path], check=True)
            vol = "/Volumes/MediaGrab"
            if Path(vol).exists():
                app_src = f"{vol}/MediaGrab.app"
                app_dst = "/Applications/MediaGrab.app"
                if Path(app_dst).exists():
                    shutil.rmtree(app_dst)
                shutil.copytree(app_src, app_dst)
                subprocess.run(["hdiutil", "detach", vol], check=True)
            self.restart_app()
        else:
            os.chmod(file_path, 0o755)
            current_exe = sys.argv[0]
            shutil.copy2(file_path, current_exe)
            self.restart_app()

    def restart_app(self) -> None:
        subprocess.Popen([sys.executable] + sys.argv)
        sys.exit(0)


update_mgr = UpdateManager()


# ─────────────────────────────────────────────
# Utility Functions
# -----------------------------------------
# Platform detection and URL validation now imported from shared.platform_detection


def load_config() -> dict:
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        import logging
        logging.warning(f"Failed to load config file: {e}")
    return {"output_dir": DEFAULT_DIR, "theme": "dark", "format": "mp3"}


def save_config(cfg: dict) -> None:
    try:
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except Exception as e:
        import logging
        logging.error(f"Failed to save config file: {e}")


def load_history() -> list[dict]:
    try:
        if HISTORY_FILE.exists():
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        import logging
        logging.warning(f"Failed to load history file: {e}")
    return []


def save_history(entries: list[dict]) -> None:
    try:
        HISTORY_FILE.write_text(json.dumps(entries[-100:], indent=2), encoding="utf-8")
    except Exception as e:
        import logging
        logging.error(f"Failed to save history file: {e}")


# ─────────────────────────────────────────────
# Download Manager
# ─────────────────────────────────────────────

class DownloadManager:
    def __init__(self):
        self._processes: dict[str, subprocess.Popen] = {}
        self._cancel_flags: dict[str, bool] = {}

    def analyze(self, url: str) -> dict:
        opts: dict[str, Any] = {
            "quiet": True, "no_warnings": True,
            "extract_flat": True, "ignoreerrors": True,
        }
        path = ffmpeg_mgr.get_path()
        if path:
            opts["ffmpeg_location"] = path
        with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[attr-defined]
            info = ydl.extract_info(url, download=False)
        if not info:
            raise ValueError("Could not retrieve information for this URL.")

        is_playlist = info.get("_type") == "playlist" or "entries" in info
        if is_playlist:
            entries = []
            plat = detect_platform(url)
            for e in info.get("entries") or []:
                if not e:
                    continue
                dur = e.get("duration")
                video_url = e.get("url")
                if not video_url:
                    eid = e.get("id", "")
                    if plat == "youtube" and eid:
                        video_url = f"https://www.youtube.com/watch?v={eid}"
                    elif plat == "vimeo" and eid:
                        video_url = f"https://vimeo.com/{eid}"
                    elif plat == "dailymotion" and eid:
                        video_url = f"https://www.dailymotion.com/video/{eid}"
                    elif e.get("webpage_url"):
                        video_url = e["webpage_url"]
                    else:
                        continue
                entries.append({
                    "title": e.get("title", "Unknown"), "id": e.get("id", ""),
                    "url": video_url, "duration": dur,
                    "duration_str": f"{int(dur // 60)}:{int(dur % 60):02d}" if dur else "N/A",
                })
            return {
                "type": "playlist", "platform": plat,
                "title": info.get("title", "Unknown Playlist"),
                "count": len(entries), "entries": entries,
            }
        else:
            dur = info.get("duration")
            return {
                "type": "video", "platform": detect_platform(url),
                "title": info.get("title", "Unknown"),
                "uploader": info.get("uploader", "Unknown"),
                "duration_str": f"{int(dur // 60)}:{int(dur % 60):02d}" if dur else "N/A",
                "thumbnail": info.get("thumbnail"),
            }

    def get_qualities(self, url: str) -> list[dict]:
        opts: dict[str, Any] = {"quiet": True, "no_warnings": True}
        path = ffmpeg_mgr.get_path()
        if path:
            opts["ffmpeg_location"] = path
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[attr-defined]
                info = ydl.extract_info(url, download=False)
            seen: dict[str, dict] = {}
            for fmt in info.get("formats", []):
                if fmt.get("vcodec") != "none":
                    h = fmt.get("height")
                    if h:
                        k = f"{h}p"
                        if k not in seen:
                            seen[k] = {"height": h, "fps": fmt.get("fps", 30)}
            return [{"label": k, **v} for k, v in sorted(seen.items(), key=lambda x: x[1]["height"], reverse=True)]
        except Exception:
            return []

    def download(self, *, url: str, output_dir: str, fmt: str, quality: str, task_id: str, selected_urls: list[str] | None = None, on_progress: Callable | None = None, on_complete: Callable | None = None, on_error: Callable | None = None) -> None:
        self._cancel_flags[task_id] = False
        os.makedirs(output_dir, exist_ok=True)
        selected_urls = selected_urls or []
        try:
            if selected_urls:
                total = len(selected_urls)
                try:
                    info = self.analyze(url)
                    playlist_title = info.get("title", "Playlist")
                except Exception:
                    playlist_title = "Playlist"
                safe_name = re.sub(r'[<>:"/\|?*]', "", playlist_title)[:120].strip(". ")
                playlist_dir = os.path.join(output_dir, safe_name)
                os.makedirs(playlist_dir, exist_ok=True)
                for i, v_url in enumerate(selected_urls):
                    if self._cancel_flags.get(task_id):
                        break
                    if on_progress:
                        on_progress(0, "", "", f"Preparing item {i+1} of {total}…", i+1, total)
                    self._run_task_process(v_url, playlist_dir, fmt, quality, task_id, lambda p, s, e, f, cur=i+1, tot=total: on_progress(p, s, e, f, cur, tot) if on_progress else None)
                if not self._cancel_flags.get(task_id) and on_complete:
                    on_complete({"output_dir": playlist_dir})
            else:
                self._run_task_process(url, output_dir, fmt, quality, task_id, on_progress)
                if not self._cancel_flags.get(task_id) and on_complete:
                    on_complete({"output_dir": output_dir})
        except Exception as exc:
            if self._cancel_flags.get(task_id):
                if on_error: on_error("Cancelled")
            else:
                if on_error: on_error(str(exc))
        finally:
            self._processes.pop(task_id, None)
            self._cancel_flags.pop(task_id, None)

    def _run_task_process(self, url, out_dir, fmt, quality, task_id, on_progress):
        path = ffmpeg_mgr.get_path()
        is_playlist = "playlist" in url.lower() or "list=" in url
        
        # Build command using shared helper
        cmd = build_yt_dlp_command(
            url=url,
            output_dir=out_dir,
            fmt=fmt,
            quality=quality,
            ffmpeg_path=path,
            is_playlist=is_playlist
        )
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding="utf-8", bufsize=1, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        self._processes[task_id] = proc
        for line in proc.stdout:
            if self._cancel_flags.get(task_id):
                break
            line = line.strip()
            if not line:
                continue
            if "download:[" in line:
                try:
                    parts = re.findall(r"\[(.*?)\]", line)
                    if len(parts) >= 4 and on_progress:
                        bytes_part = parts[0]
                        if "/" in bytes_part:
                            cur, tot = bytes_part.split("/")
                            # Enhanced validation to prevent division by zero
                            if (tot.isdigit() and int(tot) > 0 and 
                                cur.isdigit() and int(cur) >= 0):
                                try:
                                    pct = (int(cur) / int(tot)) * 100
                                    # Clamp percentage to reasonable bounds
                                    pct = max(0, min(100, pct))
                                    on_progress(pct, parts[1], parts[2], "")
                                except (ZeroDivisionError, ValueError, OverflowError):
                                    # Silently handle calculation errors
                                    pass
                except Exception:
                    pass
            elif "[download] Destination:" in line and on_progress:
                fname = os.path.basename(line.split("Destination:", 1)[1].strip())
                on_progress(0, "", "", fname)
            elif "[ExtractAudio]" in line and on_progress:
                on_progress(99, "", "", "Extracting audio…")
        proc.wait()
        if proc.returncode != 0 and not self._cancel_flags.get(task_id):
            raise Exception(f"yt-dlp failed with code {proc.returncode}")

    def pause(self, task_id: str) -> bool:
        proc = self._processes.get(task_id)
        if proc and proc.poll() is None:
            try:
                psutil.Process(proc.pid).suspend()
                return True
            except Exception:
                return False
        return False

    def resume(self, task_id: str) -> bool:
        proc = self._processes.get(task_id)
        if proc and proc.poll() is None:
            try:
                psutil.Process(proc.pid).resume()
                return True
            except Exception:
                return False
        return False

    def cancel(self, task_id: str) -> None:
        self._cancel_flags[task_id] = True
        proc = self._processes.get(task_id)
        if proc and proc.poll() is None:
            try:
                p = psutil.Process(proc.pid)
                for child in p.children(recursive=True):
                    child.kill()
                p.kill()
            except Exception:
                pass


def _classify_error(msg: str) -> str:
    m = msg.lower()
    if "sign in" in m or "login" in m or "age" in m:
        return "This content requires authentication or is age-restricted."
    if "private" in m:
        return "This video is private or unavailable."
    if "not available" in m or "removed" in m:
        return "This video is not available."
    if "unsupported url" in m:
        return "Unsupported URL — this platform may not be supported."
    if "connection" in m or "network" in m or "timeout" in m:
        return "Network error — check your internet connection."
    if "no space" in m or "disk" in m:
        return "Insufficient disk space."
    return msg[:120]


# ─────────────────────────────────────────────
# Labeled Card Section
# ─────────────────────────────────────────────

class SectionFrame(ctk.CTkFrame):
    def __init__(self, master: Any, title: str, **kw: Any):
        super().__init__(master, **kw)
        self._lbl = ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=13, weight="bold"))
        self._lbl.pack(anchor="w", padx=14, pady=(12, 4))

    def body(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", padx=14, pady=(0, 12))
        return f


# ─────────────────────────────────────────────
# Status Badge
# ─────────────────────────────────────────────

class StatusBadge(ctk.CTkLabel):
    COLOURS = {
        "info": ("#1d6fa5", "#3d9bd4"), "success": ("#1d7a42", "#2ea05a"),
        "warning": ("#8a6d00", "#c9a000"), "error": ("#8a1c1c", "#c93d3d"),
        "idle": ("gray40", "gray60"),
    }

    def set(self, text: str, kind: str = "info") -> None:
        dark, light = self.COLOURS.get(kind, self.COLOURS["idle"])
        self.configure(text=f"  {text}  ", fg_color=(light, dark))


# ─────────────────────────────────────────────
# Main Application Window
# ─────────────────────────────────────────────

class MediaGrabApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self._cfg = load_config()
        self._history_list: list[dict] = load_history()
        self._manager = DownloadManager()
        self._result: dict | None = None
        self._task_id: str | None = None
        self._fmt_var = ctk.StringVar(value=self._cfg.get("format", "mp3"))
        self._quality_var = ctk.StringVar(value="best")
        self._output_dir = self._cfg.get("output_dir", DEFAULT_DIR)
        self._selected_videos: dict[str, bool] = {}
        self._last_progress_update = 0.0
        self._progress_pending = False
        self._progress_history: list[float] = []

        ctk.set_appearance_mode(self._cfg.get("theme", "dark"))
        ctk.set_default_color_theme("blue")
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("960x780")
        self.minsize(820, 640)
        self._center()
        self.protocol("WM_DELETE_WINDOW", self._on_quit)
        self._build()
        self._reload_history_display()
        self.after(500, self._check_ffmpeg_status)
        threading.Thread(target=self._check_updates_bg, daemon=True).start()

    def _build(self) -> None:
        self._build_header()
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=18, pady=(8, 18))
        self._scroll = scroll
        self._build_url_section(scroll)
        self._build_info_section(scroll)
        self._build_options_section(scroll)
        self._build_output_section(scroll)
        self._build_download_btn(scroll)
        self._build_progress_section(scroll)
        self._build_history_section(scroll)

    def _build_header(self) -> None:
        bar = ctk.CTkFrame(self, height=62, corner_radius=0, fg_color=("gray90", "gray15"))
        bar.pack(fill="x")
        bar.pack_propagate(False)
        ctk.CTkLabel(bar, text=f"  {APP_NAME}", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left", padx=20)
        ctk.CTkLabel(bar, text="Universal Video Downloader", font=ctk.CTkFont(size=12), text_color="gray").pack(side="left", padx=4)
        ctk.CTkButton(bar, text="🔄", width=32, height=32, corner_radius=16, fg_color="transparent", hover_color=("gray80", "gray25"), command=self._manual_check_updates).pack(side="right", padx=6)
        ctk.CTkButton(bar, text="ℹ", width=32, height=32, corner_radius=16, fg_color="transparent", hover_color=("gray80", "gray25"), command=self._show_about).pack(side="right", padx=10)
        self._theme_sw = ctk.CTkSwitch(bar, text="Dark", width=80, command=self._toggle_theme, onvalue="dark", offvalue="light")
        self._theme_sw.pack(side="right", padx=18)
        if ctk.get_appearance_mode() == "Dark":
            self._theme_sw.select()
        self._ffmpeg_status_row = ctk.CTkFrame(bar, fg_color="transparent")
        self._ffmpeg_status_row.pack(side="right", padx=10)
        self._ffmpeg_lbl = ctk.CTkLabel(self._ffmpeg_status_row, text="FFmpeg: Checking...", font=ctk.CTkFont(size=11), text_color="gray")
        self._ffmpeg_lbl.pack(side="left")

    def _build_url_section(self, parent: Any) -> None:
        sec = SectionFrame(parent, "  Video URL")
        sec.pack(fill="x", pady=(0, 10))
        row = sec.body()
        self._url_entry = ctk.CTkEntry(row, placeholder_text="Paste any video or playlist URL…", height=44, font=ctk.CTkFont(size=13))
        self._url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._url_entry.bind("<Return>", lambda _: self._start_analysis())
        ctk.CTkButton(row, text="📋", width=44, height=44, corner_radius=8, command=self._paste).pack(side="left", padx=(0, 8))
        self._analyze_btn = ctk.CTkButton(row, text="Analyze", width=100, height=44, font=ctk.CTkFont(size=13, weight="bold"), command=self._start_analysis)
        self._analyze_btn.pack(side="left")
        self._badge = StatusBadge(sec, text="  Idle  ", corner_radius=6, height=24)
        self._badge.pack(anchor="w", padx=14, pady=(0, 10))
        self._badge.set("Idle", "idle")

    def _build_info_section(self, parent: Any) -> None:
        self._info_sec = SectionFrame(parent, "  Media Information")
        body = self._info_sec.body()
        self._info_body = body

    def _build_options_section(self, parent: Any) -> None:
        self._opt_sec = SectionFrame(parent, "  Download Options")
        self._opt_sec.pack(fill="x", pady=(0, 10))
        body = self._opt_sec.body()
        ctk.CTkLabel(body, text="Format:", font=ctk.CTkFont(weight="bold"), width=70).pack(side="left")
        ctk.CTkRadioButton(body, text="MP3 (Audio)", variable=self._fmt_var, value="mp3", command=self._on_fmt_change).pack(side="left", padx=(4, 8))
        ctk.CTkRadioButton(body, text="MP4 (Video)", variable=self._fmt_var, value="mp4", command=self._on_fmt_change).pack(side="left", padx=(0, 8))
        ctk.CTkRadioButton(body, text="Original", variable=self._fmt_var, value="original", command=self._on_fmt_change).pack(side="left", padx=(0, 24))
        self._q_lbl = ctk.CTkLabel(body, text="Quality:", font=ctk.CTkFont(weight="bold"), width=70)
        self._q_menu = ctk.CTkOptionMenu(body, values=["best", "1080p", "720p", "480p", "360p"], variable=self._quality_var, width=130, command=self._on_quality_change)
        if self._fmt_var.get() == "mp4":
            self._q_lbl.pack(side="left")
            self._q_menu.pack(side="left")

    def _build_output_section(self, parent: Any) -> None:
        sec = SectionFrame(parent, "  Save Location")
        sec.pack(fill="x", pady=(0, 10))
        body = sec.body()
        self._dir_lbl = ctk.CTkLabel(body, text=self._output_dir, font=ctk.CTkFont(size=12), text_color="gray", anchor="w")
        self._dir_lbl.pack(side="left", fill="x", expand=True, padx=(0, 12))
        ctk.CTkButton(body, text="Browse…", width=90, height=34, command=self._browse_dir).pack(side="left")
        ctk.CTkButton(body, text="Open", width=70, height=34, fg_color="transparent", border_width=1, command=lambda: self._open_folder(self._output_dir)).pack(side="left", padx=(8, 0))

    def _build_download_btn(self, parent: Any) -> None:
        self._dl_btn = ctk.CTkButton(parent, text="  Download", height=52, font=ctk.CTkFont(size=16, weight="bold"), state="disabled", command=self._start_download)
        self._dl_btn.pack(fill="x", pady=(0, 10))

    def _build_progress_section(self, parent: Any) -> None:
        self._prog_sec = SectionFrame(parent, "  Download Progress")
        body = self._prog_sec.body()
        self._prog_filename = ctk.CTkLabel(body, text="", font=ctk.CTkFont(size=12), anchor="w")
        self._prog_filename.pack(fill="x", pady=(0, 4))
        self._prog_bar = ctk.CTkProgressBar(body, height=16, corner_radius=8)
        self._prog_bar.pack(fill="x", pady=(0, 4))
        self._prog_bar.set(0)
        stat_row = ctk.CTkFrame(body, fg_color="transparent")
        stat_row.pack(fill="x")
        self._prog_pct = ctk.CTkLabel(stat_row, text="0%", font=ctk.CTkFont(size=12, weight="bold"))
        self._prog_pct.pack(side="left")
        self._prog_speed = ctk.CTkLabel(stat_row, text="", font=ctk.CTkFont(size=12), text_color="gray")
        self._prog_speed.pack(side="left", padx=12)
        self._prog_eta = ctk.CTkLabel(stat_row, text="", font=ctk.CTkFont(size=12), text_color="gray")
        self._prog_eta.pack(side="left")
        self._pause_btn = ctk.CTkButton(stat_row, text="  Pause", width=90, height=26, command=self._toggle_pause)
        self._pause_btn.pack(side="right")
        self._cancel_btn = ctk.CTkButton(body, text="  Cancel", width=100, height=30, fg_color=("red3", "red4"), hover_color=("red4", "red3"), command=self._cancel_download)
        self._cancel_btn.pack(anchor="e", pady=(8, 0))

    def _build_history_section(self, parent: Any) -> None:
        sec = SectionFrame(parent, "  Recent Downloads")
        sec.pack(fill="x", pady=(0, 10))
        body = sec.body()
        self._history_frame = ctk.CTkScrollableFrame(body, height=300, fg_color="transparent")
        self._history_frame.pack(fill="x")
        self._history_items: dict[str, HistoryItem] = {}
        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.pack(fill="x", pady=(6, 0))
        ctk.CTkButton(btn_row, text="Open Folder", width=110, height=28, command=lambda: self._open_folder(self._output_dir)).pack(side="left")
        ctk.CTkButton(btn_row, text="Clear History", width=110, height=28, fg_color="transparent", border_width=1, command=self._clear_history).pack(side="right")

    # ── Actions ───────────────────────────────

    def _paste(self) -> None:
        try:
            text = self.clipboard_get()
            self._url_entry.delete(0, "end")
            self._url_entry.insert(0, text.strip())
        except Exception:
            pass

    def _browse_dir(self) -> None:
        folder = filedialog.askdirectory(initialdir=self._output_dir)
        if folder:
            self._output_dir = folder
            self._dir_lbl.configure(text=folder)
            self._cfg["output_dir"] = folder
            save_config(self._cfg)

    def _toggle_theme(self) -> None:
        mode = self._theme_sw.get()
        ctk.set_appearance_mode(mode)
        self._cfg["theme"] = mode
        save_config(self._cfg)

    def _on_fmt_change(self) -> None:
        fmt = self._fmt_var.get()
        self._cfg["format"] = fmt
        save_config(self._cfg)
        if fmt == "mp4":
            self._q_lbl.pack(side="left")
            self._q_menu.pack(side="left")
        else:
            self._q_lbl.pack_forget()
            self._q_menu.pack_forget()

    def _on_quality_change(self, value: str) -> None:
        if value == "best":
            self._quality_var.set("best")
        else:
            h = value[:-1]
            self._quality_var.set(f"bestvideo[height<={h}]+bestaudio/best")

    # ── Analysis ──────────────────────────────

    def _start_analysis(self) -> None:
        url = self._url_entry.get().strip()
        if not url:
            self._badge.set("Please enter a URL", "warning")
            return
        if not validate_url(url):
            self._badge.set("Invalid URL format", "error")
            return
        self._analyze_btn.configure(state="disabled", text=" Analyzing…")
        self._dl_btn.configure(state="disabled")
        self._badge.set("Analyzing…", "info")
        self._info_sec.pack_forget()
        threading.Thread(target=self._analyze_thread, args=(url,), daemon=True).start()

    def _analyze_thread(self, url: str) -> None:
        try:
            result = self._manager.analyze(url)
            self.after(0, self._on_analysis_ok, result)
        except Exception as exc:
            self.after(0, self._on_analysis_err, str(exc))

    def _on_analysis_ok(self, result: dict) -> None:
        self._result = result
        self._analyze_btn.configure(state="normal", text="Analyze")
        self._badge.set("Ready to download", "success")
        self._render_info(result)
        self._update_download_btn_label()

    def _on_analysis_err(self, msg: str) -> None:
        self._analyze_btn.configure(state="normal", text="Analyze")
        user_msg = _classify_error(msg)
        self._badge.set(f"Error: {user_msg[:70]}", "error")

    def _render_info(self, result: dict) -> None:
        for w in self._info_body.winfo_children():
            w.destroy()
        self._selected_videos = {}
        if result["type"] == "playlist":
            ctk.CTkLabel(self._info_body, text=f"  {result['title']}", font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(fill="x", pady=(0, 4))
            ctk.CTkLabel(self._info_body, text=f"{result['count']} videos  ·  {result['platform'].title()}", text_color="gray", anchor="w").pack(fill="x", pady=(0, 8))
            btn_frame = ctk.CTkFrame(self._info_body, fg_color="transparent")
            btn_frame.pack(fill="x", pady=(0, 6))
            ctk.CTkButton(btn_frame, text="Select All", width=90, height=26, command=lambda: self._toggle_all_playlist_items(True, result)).pack(side="left", padx=(0, 6))
            ctk.CTkButton(btn_frame, text="Deselect All", width=90, height=26, fg_color="transparent", border_width=1, command=lambda: self._toggle_all_playlist_items(False, result)).pack(side="left")
            scroll_frame = ctk.CTkScrollableFrame(self._info_body, height=250, fg_color="transparent")
            scroll_frame.pack(fill="both", expand=True, pady=(0, 8))
            self._playlist_check_vars = []
            for i, entry in enumerate(result["entries"]):
                vid = entry.get("id", str(i))
                var = ctk.BooleanVar(value=True)
                self._playlist_check_vars.append((vid, var))
                self._selected_videos[vid] = True
                item = ctk.CTkFrame(scroll_frame, fg_color="transparent")
                item.pack(fill="x", pady=2)
                ctk.CTkCheckBox(item, text="", variable=var, width=24, command=lambda v=vid, var=var: self._on_playlist_item_toggled(v, var)).pack(side="left")
                ctk.CTkLabel(item, text=f"{i+1:>3}. [{entry.get('duration_str', 'N/A')}] {entry.get('title', 'Unknown')}", font=ctk.CTkFont(size=11), anchor="w").pack(side="left", fill="x", expand=True)
            self._playlist_count_label = ctk.CTkLabel(self._info_body, text=f"Selected: {result['count']} / {result['count']}", text_color="gray", font=ctk.CTkFont(size=11))
            self._playlist_count_label.pack(anchor="w", pady=(0, 4))
        else:
            rows = [("Title", result["title"]), ("Channel", result["uploader"]), ("Duration", result["duration_str"]), ("Platform", result["platform"].title())]
            for label, val in rows:
                r = ctk.CTkFrame(self._info_body, fg_color="transparent")
                r.pack(fill="x", pady=2)
                ctk.CTkLabel(r, text=f"{label}:", width=80, font=ctk.CTkFont(weight="bold"), anchor="w").pack(side="left")
                ctk.CTkLabel(r, text=val, anchor="w").pack(side="left", fill="x", expand=True)
        self._info_sec.pack(fill="x", pady=(0, 10), before=self._opt_sec)

    def _on_playlist_item_toggled(self, video_id, var):
        self._selected_videos[video_id] = var.get()
        count = len([v for v in self._selected_videos.values() if v])
        self._playlist_count_label.configure(text=f"Selected: {count} / {self._result['count']}")
        self._update_download_btn_label()

    def _toggle_all_playlist_items(self, select_all, result):
        for vid, var in self._playlist_check_vars:
            var.set(select_all)
            self._selected_videos[vid] = select_all
        self._update_download_btn_label()
        count = len([v for v in self._selected_videos.values() if v])
        self._playlist_count_label.configure(text=f"Selected: {count} / {result['count']}")

    def _update_download_btn_label(self):
        if self._result and self._result.get("type") == "playlist":
            count = len([v for v in self._selected_videos.values() if v])
            self._dl_btn.configure(text=f"  Download Selected ({count}/{self._result['count']})", state="normal" if count > 0 else "disabled")
        else:
            self._dl_btn.configure(text="  Download", state="normal")

    # ── Download ──────────────────────────────

    def _start_download(self):
        if not self._result:
            return
        if not ffmpeg_mgr.is_installed:
            if ffmpeg_mgr.installing:
                self._badge.set("Please wait for FFmpeg to finish installing...", "warning")
                return
            else:
                messagebox.showwarning("FFmpeg Missing", "FFmpeg is required for downloads. It will be installed automatically now.")
                self._check_ffmpeg_status()
                return
        url = self._url_entry.get().strip()
        selected_urls = []
        if self._result.get("type") == "playlist":
            selected_urls = [e["url"] for e in self._result.get("entries", []) if self._selected_videos.get(e.get("id"))]
        self._dl_btn.configure(state="disabled", text=" Downloading…")
        self._analyze_btn.configure(state="disabled")
        self._badge.set("Downloading…", "info")
        self._show_progress()
        tid = str(uuid.uuid4())
        self._task_id = tid
        data = {"title": self._result["title"], "status": "downloading", "progress": 0, "message": "Starting…"}
        self._add_history_card(tid, data)
        threading.Thread(
            target=self._manager.download,
            kwargs=dict(
                url=url, output_dir=self._output_dir, fmt=self._fmt_var.get(),
                quality=self._quality_var.get(), task_id=tid, selected_urls=selected_urls,
                on_progress=lambda p, s, e, f, ci=None, ti=None: self.after(0, self._update_progress, p, s, e, f, ci, ti, tid),
                on_complete=lambda d: self.after(0, self._on_dl_complete, d, tid),
                on_error=lambda err: self.after(0, self._on_dl_error, err, tid),
            ),
            daemon=True
        ).start()

    def _show_progress(self):
        self._last_progress_update = 0.0
        self._progress_pending = False
        self._progress_history = []
        self._prog_bar.set(0)
        self._prog_pct.configure(text="0%")
        self._prog_speed.configure(text="")
        self._prog_eta.configure(text="")
        self._prog_filename.configure(text="")
        if not hasattr(self, '_prog_item_label'):
            self._prog_item_label = ctk.CTkLabel(self._prog_sec.body(), text="", font=ctk.CTkFont(size=10), text_color="gray", anchor="w")
            self._prog_item_label.pack(fill="x", pady=(0, 4))
        self._prog_sec.pack(fill="x", pady=(0, 10), before=self._dl_btn)

    def _update_progress(self, pct, speed, eta, filename, ci=None, ti=None, tid=None):
        # Debounce main UI progress and history cards to every 250ms
        now = time.monotonic()
        if now - self._last_progress_update < 0.25:
            return
        self._last_progress_update = now

        # Throttled update of history items to prevent event loop saturation
        if tid in self._history_items:
            # We only update the history card if enough time has passed
            self._history_items[tid].update_state({
                "status": "downloading", 
                "progress": pct, 
                "message": f"{speed} | {eta}" if speed else "Downloading…",
                "filename": filename
            })

        # Smooth progress with last 3 values to prevent jitter (circular buffer)
        if not hasattr(self, '_progress_history'):
            self._progress_history = []
        if not hasattr(self, '_progress_history_index'):
            self._progress_history_index = 0
            self._progress_history_max_size = 3
        
        # Maintain circular buffer of fixed size
        if len(self._progress_history) < self._progress_history_max_size:
            self._progress_history.append(pct)
        else:
            # Replace oldest value in circular buffer
            self._progress_history[self._progress_history_index] = pct
            self._progress_history_index = (self._progress_history_index + 1) % self._progress_history_max_size
        
        # Calculate average of available values
        if self._progress_history:
            smoothed_pct = sum(self._progress_history) / len(self._progress_history)
        else:
            smoothed_pct = pct

        def _apply():
            self._progress_pending = False
            if tid != self._task_id:
                return
            self._last_progress_update = time.monotonic()
            clamped = min(smoothed_pct / 100, 1.0)
            self._prog_bar.set(clamped)
            self._prog_pct.configure(text=f"{smoothed_pct:.1f}%")
            if speed:
                self._prog_speed.configure(text=f"Speed: {speed}")
            if eta:
                self._prog_eta.configure(text=f"ETA: {eta}")
            if filename:
                self._prog_filename.configure(text=filename[:80])
            if ci and ti:
                self._prog_item_label.configure(text=f"Item {ci} of {ti}")

        self.after_idle(_apply)

    def _toggle_pause(self):
        if not self._task_id:
            return
        txt = self._pause_btn.cget("text")
        if "Pause" in txt:
            if self._manager.pause(self._task_id):
                self._pause_btn.configure(text="  Resume")
                if self._task_id in self._history_items:
                    self._history_items[self._task_id].update_state({"status": "paused", "message": "Paused"})
        else:
            if self._manager.resume(self._task_id):
                self._pause_btn.configure(text="  Pause")
                if self._task_id in self._history_items:
                    self._history_items[self._task_id].update_state({"status": "downloading", "message": "Resuming…"})

    def _cancel_download(self):
        if self._task_id:
            self._manager.cancel(self._task_id)
            self._on_dl_error("Cancelled", self._task_id)

    def _on_dl_complete(self, data, tid):
        if tid == self._task_id:
            self._dl_btn.configure(state="normal", text="  Download")
            self._analyze_btn.configure(state="normal")
            self._badge.set("Download complete!", "success")
        if tid in self._history_items:
            self._history_items[tid].update_state({"status": "complete", "progress": 100, "message": "Finished", "output_dir": data.get("output_dir")})
        self._history_list.append({"tid": tid, "title": self._history_items[tid].data["title"], "status": "complete", "ts": datetime.now().isoformat()})
        save_history(self._history_list)

    def _on_dl_error(self, msg, tid):
        if tid == self._task_id:
            self._dl_btn.configure(state="normal", text="  Download")
            self._analyze_btn.configure(state="normal")
            self._badge.set(f"Error: {msg[:80]}", "error")
        if tid in self._history_items:
            st = "cancelled" if "cancel" in msg.lower() else "error"
            self._history_items[tid].update_state({"status": st, "progress": 0, "message": msg})

    # ── History Card Helpers ───────────────────

    def _add_history_card(self, tid, data):
        card = HistoryItem(
            self._history_frame, tid, data,
            on_pause=self._history_pause, on_resume=self._history_resume,
            on_cancel=self._history_cancel, on_retry=self._history_retry,
            on_delete=self._history_delete, on_open=self._open_folder
        )
        self._history_items[tid] = card

    def _history_pause(self, tid):
        self._manager.pause(tid)

    def _history_resume(self, tid):
        self._manager.resume(tid)

    def _history_cancel(self, tid):
        self._manager.cancel(tid)

    def _history_retry(self, tid):
        if tid in self._history_items:
            card = self._history_items[tid]
            url = self._url_entry.get().strip()
            if url:
                card.update_state({"status": "starting", "message": "Retrying…", "progress": 0})
                self._start_download()

    def _history_delete(self, tid):
        if tid in self._history_items:
            file_path = self._history_items[tid].data.get("output_dir")
            if file_path and os.path.exists(file_path):
                if messagebox.askyesno("Delete File", f"Do you want to permanently delete the downloaded files at:\n{file_path}?"):
                    try:
                        if os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                        else:
                            os.remove(file_path)
                    except Exception as e:
                        messagebox.showerror("Error", f"Could not delete file: {e}")
            self._history_items[tid].destroy()
            del self._history_items[tid]

    def _clear_history(self):
        for tid in list(self._history_items.keys()):
            self._history_delete(tid)
        self._history_list = []
        save_history([])

    def _reload_history_display(self):
        for entry in self._history_list:
            if entry.get("status") in ("complete", "error", "cancelled"):
                self._add_history_card(entry["tid"], entry)

    # ── FFmpeg Status ─────────────────────────

    def _check_ffmpeg_status(self):
        if ffmpeg_mgr.is_installed:
            self._ffmpeg_lbl.configure(text="FFmpeg: Ready", text_color="green")
        else:
            self._ffmpeg_lbl.configure(text="FFmpeg: Missing! Auto-installing...", text_color="orange")
            if messagebox.askyesno("FFmpeg Missing", "FFmpeg is required for audio/video processing. Download and install it now? ( ~60-100 MB )"):
                ffmpeg_mgr.start_install(
                    on_progress=lambda p: self.after(0, self._on_ffmpeg_progress, p),
                    on_done=lambda: self.after(0, self._on_ffmpeg_ready),
                    on_error=lambda e: self.after(0, self._on_ffmpeg_error, e)
                )
            else:
                self._ffmpeg_lbl.configure(text="FFmpeg: Not Installed", text_color="red")

    def _on_ffmpeg_progress(self, p):
        self._ffmpeg_lbl.configure(text=f"FFmpeg: Installing ({int(p)}%)")

    def _on_ffmpeg_ready(self):
        self._ffmpeg_lbl.configure(text="FFmpeg: Ready", text_color="green")
        self._badge.set("FFmpeg Ready", "success")

    def _on_ffmpeg_error(self, err):
        self._ffmpeg_lbl.configure(text="FFmpeg: Error! Click to Retry", text_color="red", cursor="hand2")
        self._ffmpeg_lbl.bind("<Button-1>", lambda _: self._check_ffmpeg_status())
        messagebox.showerror("FFmpeg Error", f"Silent installation failed:\n{err}")

    # ── Update System ─────────────────────────

    def _check_updates_bg(self):
        try:
            result = update_mgr.check_for_updates()
            if result:
                self.after(0, self._show_update_available, result)
        except Exception:
            pass

    def _manual_check_updates(self):
        self._badge.set("Checking for updates...", "info")
        threading.Thread(target=self._manual_check_updates_bg, daemon=True).start()

    def _manual_check_updates_bg(self):
        try:
            result = update_mgr.check_for_updates()
            if result:
                self.after(0, self._show_update_available, result)
            else:
                self.after(0, lambda: self._badge.set("You are on the latest version", "success"))
        except Exception as e:
            self.after(0, lambda: self._badge.set(f"Update check failed: {e}", "error"))

    def _show_update_available(self, info: dict):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Update Available — v{info['version']}")
        dialog.geometry("500x450")
        dialog.grab_set()
        dialog.resizable(False, False)
        ctk.CTkLabel(dialog, text=f"New version v{info['version']} is available!", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 10))
        ctk.CTkLabel(dialog, text=f"Current version: v{update_mgr.CURRENT_VERSION}", font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(0, 10))
        notes_frame = ctk.CTkScrollableFrame(dialog, height=150, width=460)
        notes_frame.pack(padx=20, pady=10, fill="both", expand=True)
        ctk.CTkLabel(notes_frame, text=info.get("notes", "No release notes available."), font=ctk.CTkFont(size=11), anchor="w", justify="left").pack(fill="x", padx=10, pady=10)

        # Add important note about installer
        note_frame = ctk.CTkFrame(dialog, fg_color=("#fff3cd", "#3d3522"), corner_radius=8)
        note_frame.pack(padx=20, pady=(0, 10), fill="x")
        ctk.CTkLabel(note_frame, text="ℹ️ Note: The installer will launch automatically.\nThe app will close during installation.", font=ctk.CTkFont(size=10), text_color=("#856404", "#ffc107"), wraplength=440).pack(padx=10, pady=8)

        self._update_progress_var = ctk.DoubleVar(value=0)
        self._update_progress_bar = ctk.CTkProgressBar(dialog, variable=self._update_progress_var)
        self._update_progress_bar.pack(fill="x", padx=20, pady=(0, 10))
        self._update_progress_bar.set(0)
        self._update_status_lbl = ctk.CTkLabel(dialog, text="", font=ctk.CTkFont(size=11), text_color="gray")
        self._update_status_lbl.pack(pady=(0, 10))

        def do_update():
            # Release modal grab so the dialog doesn't appear frozen
            dialog.grab_release()
            update_btn.configure(state="disabled")
            later_btn.configure(state="disabled")

            def _do_update_bg():
                try:
                    self.after(0, lambda: self._update_status_lbl.configure(text="Selecting best installer for your OS..."))
                    asset = update_mgr._select_asset(info["release"])
                    if not asset:
                        self.after(0, lambda: self._update_status_lbl.configure(text="No compatible update file found.", text_color="red"))
                        self.after(0, lambda: update_btn.configure(state="normal"))
                        self.after(0, lambda: later_btn.configure(state="normal"))
                        return
                    self.after(0, lambda: self._update_status_lbl.configure(text="Downloading update..."))
                    def on_progress(pct):
                        self.after(0, lambda: self._update_progress_var.set(pct / 100))
                        self.after(0, lambda: self._update_status_lbl.configure(text=f"Downloading... {pct:.0f}%"))
                    file_path = update_mgr.download_update(asset[0], on_progress)
                    self.after(0, lambda: self._update_status_lbl.configure(text="Launching installer... App will close."))
                    # Give user time to read the message
                    import time
                    time.sleep(1.5)
                    self.after(0, lambda: update_mgr.install_update(file_path))
                except Exception as e:
                    self.after(0, lambda: self._update_status_lbl.configure(text=f"Download failed: {e}", text_color="red"))
                    self.after(0, lambda: update_btn.configure(state="normal"))
                    self.after(0, lambda: later_btn.configure(state="normal"))

            threading.Thread(target=_do_update_bg, daemon=True).start()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)
        update_btn = ctk.CTkButton(btn_frame, text="Update Now", width=120, height=36, font=ctk.CTkFont(size=13, weight="bold"), command=do_update)
        update_btn.pack(side="left", padx=10)
        later_btn = ctk.CTkButton(btn_frame, text="Later", width=100, height=36, fg_color="transparent", border_width=1, command=dialog.destroy)
        later_btn.pack(side="left", padx=10)
        dialog.update_idletasks()
        w = dialog.winfo_width()
        h = dialog.winfo_height()
        x = self.winfo_x() + (self.winfo_width() - w) // 2
        y = self.winfo_y() + (self.winfo_height() - h) // 2
        dialog.geometry(f"+{x}+{y}")

    # ── Misc ──────────────────────────────────

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _open_folder(self, path):
        if not path or not os.path.exists(path):
            return
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])

    def _show_about(self):
        messagebox.showinfo(f"About {APP_NAME}", f"{APP_NAME} {APP_VERSION}\nUniversal Video Downloader\nPublisher: Isaac Onyango")

    def _on_quit(self):
        save_config(self._cfg)
        self.destroy()


class HistoryItem(ctk.CTkFrame):
    def __init__(self, master, task_id, data, on_pause, on_resume, on_cancel, on_retry, on_delete, on_open):
        super().__init__(master, fg_color=("gray95", "gray20"))
        self.task_id = task_id
        self.data = data
        self.on_pause = on_pause
        self.on_resume = on_resume
        self.on_cancel = on_cancel
        self.on_retry = on_retry
        self.on_delete = on_delete
        self.on_open = on_open
        self.pack(fill="x", pady=4, padx=2)
        self._setup_ui()
        self.update_state(data)

    def _setup_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=6)
        self.title_lbl = ctk.CTkLabel(header, text=self.data.get("title", "Unknown"), font=ctk.CTkFont(size=12, weight="bold"), anchor="w")
        self.title_lbl.pack(side="left", fill="x", expand=True)
        self.status_badge = ctk.CTkLabel(header, text="  Pending  ", corner_radius=6, font=ctk.CTkFont(size=10), height=20)
        self.status_badge.pack(side="right")
        self.pbar = ctk.CTkProgressBar(self, height=8)
        self.pbar.pack(fill="x", padx=10, pady=(0, 6))
        self.pbar.set(0)
        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.pack(fill="x", padx=10, pady=(0, 6))
        self.pct_lbl = ctk.CTkLabel(stats, text="0%", font=ctk.CTkFont(size=11))
        self.pct_lbl.pack(side="left")
        self.msg_lbl = ctk.CTkLabel(stats, text="", font=ctk.CTkFont(size=11), text_color="gray")
        self.msg_lbl.pack(side="left", padx=10)
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(0, 8))
        self.pause_btn = ctk.CTkButton(actions, text="Pause", width=60, height=24, font=ctk.CTkFont(size=11), command=lambda: self.on_pause(self.task_id))
        self.pause_btn.pack(side="left", padx=(0, 4))
        self.resume_btn = ctk.CTkButton(actions, text="Resume", width=60, height=24, font=ctk.CTkFont(size=11), command=lambda: self.on_resume(self.task_id))
        self.resume_btn.pack(side="left", padx=(0, 4))
        self.cancel_btn = ctk.CTkButton(actions, text="Cancel", width=60, height=24, font=ctk.CTkFont(size=11), fg_color="transparent", border_width=1, command=lambda: self.on_cancel(self.task_id))
        self.cancel_btn.pack(side="left", padx=(0, 4))
        self.retry_btn = ctk.CTkButton(actions, text="Retry", width=60, height=24, font=ctk.CTkFont(size=11), command=lambda: self.on_retry(self.task_id))
        self.retry_btn.pack(side="left", padx=(0, 4))
        self.open_btn = ctk.CTkButton(actions, text="Open", width=60, height=24, font=ctk.CTkFont(size=11), command=lambda: self.on_open(self.data.get("output_dir")))
        self.open_btn.pack(side="left", padx=(0, 4))
        self.delete_btn = ctk.CTkButton(actions, text="Delete", width=60, height=24, font=ctk.CTkFont(size=11), fg_color="transparent", text_color="red", border_width=1, border_color="red", command=lambda: self.on_delete(self.task_id))
        self.delete_btn.pack(side="right")

    def update_state(self, data):
        self.data = data
        status = data.get("status", "pending")
        progress = data.get("progress", 0) / 100
        self.pbar.set(progress)
        self.pct_lbl.configure(text=f"{int(progress*100)}%")
        self.msg_lbl.configure(text=data.get("message", ""))
        badge_text = status.upper()
        badge_color = ("#3d9bd4", "#1d6fa5")
        if status == "complete":
            badge_color = ("#2ea05a", "#1d7a42")
        elif status == "error":
            badge_color = ("#c93d3d", "#8a1c1c")
        elif status == "cancelled":
            badge_color = ("gray60", "gray40")
        elif status == "paused":
            badge_color = ("#c9a000", "#8a6d00")
        self.status_badge.configure(text=f"  {badge_text}  ", fg_color=badge_color)
        is_active = status in ("downloading", "starting", "processing", "paused")
        if is_active:
            if status == "paused":
                self.pause_btn.pack_forget()
                self.resume_btn.pack(side="left", padx=(0, 4))
            else:
                self.resume_btn.pack_forget()
                self.pause_btn.pack(side="left", padx=(0, 4))
            self.cancel_btn.pack(side="left", padx=(0, 4))
            self.retry_btn.pack_forget()
        else:
            self.pause_btn.pack_forget()
            self.resume_btn.pack_forget()
            self.cancel_btn.pack_forget()
            self.retry_btn.pack(side="left", padx=(0, 4))
        if status == "complete":
            self.open_btn.pack(side="left", padx=(0, 4))
        else:
            self.open_btn.pack_forget()


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app = MediaGrabApp()
    app.mainloop()
