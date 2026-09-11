"""
Shared utility for yt-dlp command construction and progress parsing.
Ensures consistency between Desktop and Backend downloads.
"""

import os
import re
from typing import Any, Dict, List, Optional

# yt-dlp strips the "<type>:" prefix from --progress-template before printing,
# so the template body itself must carry a marker we can recognise on stdout.
PROGRESS_MARKER = "MGPROGRESS"

_PROGRESS_FIELDS = (
    "%(progress.downloaded_bytes)s",
    "%(progress.total_bytes)s",
    "%(progress.total_bytes_estimate)s",
    "%(progress._speed_str)s",
    "%(progress._eta_str)s",
    "%(progress.status)s",
)

PROGRESS_TEMPLATE = "download:" + PROGRESS_MARKER + "|" + "|".join(_PROGRESS_FIELDS)

# Quality labels the UIs offer ("1080p", "720p", …) are not valid yt-dlp format
# selectors; they have to be translated before reaching yt-dlp.
_HEIGHT_LABEL = re.compile(r"^(\d{3,4})p?$", re.IGNORECASE)


def normalize_quality(quality: Optional[str]) -> str:
    """
    Translate a UI quality choice into a yt-dlp format selector.

    "best"/""/None      -> bestvideo+bestaudio/best
    "1080p" / "1080"    -> bestvideo[height<=1080]+bestaudio/best[height<=1080]
    anything else       -> passed through unchanged (already a selector)
    """
    if not quality or quality.strip().lower() in ("best", "auto"):
        return "bestvideo+bestaudio/best"

    quality = quality.strip()
    match = _HEIGHT_LABEL.match(quality)
    if match:
        height = match.group(1)
        return (
            f"bestvideo[height<={height}]+bestaudio/"
            f"best[height<={height}]/best"
        )
    return quality


def parse_progress_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse one stdout line emitted by PROGRESS_TEMPLATE.

    Returns a dict with percent/speed/eta/status, or None when the line is not
    a progress line. percent is None when the total size is still unknown.
    """
    idx = line.find(PROGRESS_MARKER)
    if idx == -1:
        return None

    parts = line[idx + len(PROGRESS_MARKER):].lstrip("|").split("|")
    if len(parts) < 6:
        return None

    downloaded = _to_int(parts[0])
    total = _to_int(parts[1]) or _to_int(parts[2])

    percent: Optional[float] = None
    if downloaded is not None and total:
        percent = max(0.0, min(100.0, (downloaded / total) * 100))

    return {
        "percent": percent,
        "downloaded_bytes": downloaded,
        "total_bytes": total,
        "speed": _clean(parts[3]),
        "eta": _clean(parts[4]),
        "status": _clean(parts[5]) or "downloading",
    }


def _to_int(value: str) -> Optional[int]:
    value = value.strip()
    if not value or value in ("NA", "None"):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _clean(value: str) -> str:
    """Blank out yt-dlp's placeholder strings so the UI shows nothing instead."""
    value = value.strip()
    if value in ("NA", "None") or value.startswith("Unknown"):
        return ""
    return value


def build_yt_dlp_command(
    url: str,
    output_dir: str,
    fmt: str = "mp4",
    quality: str = "best",
    ffmpeg_path: Optional[str] = None,
    is_playlist: bool = False,
    playlist_items: Optional[List[Any]] = None,
    is_live: bool = False,
) -> List[str]:
    """
    Constructs a yt-dlp command-line argument list.

    When is_playlist is False the playlist is explicitly disabled, so a single
    video carrying a "list=" parameter does not pull in the whole playlist.
    """
    # 1. Determine Output Template
    if is_playlist:
        # For playlists, we usually want index prefixing
        outtmpl = os.path.join(output_dir, "%(playlist_index)03d - %(title)s.%(ext)s")
    else:
        outtmpl = os.path.join(output_dir, "%(title)s.%(ext)s")

    # 2. Base Command
    # --newline plus a marked --progress-template makes stdout easy to parse.
    cmd = [
        "yt-dlp",
        "--newline",
        "--progress",
        "--no-warnings",
        "--progress-template", PROGRESS_TEMPLATE,
        "-o", outtmpl,
    ]

    # 3. Playlist scope
    cmd.append("--yes-playlist" if is_playlist else "--no-playlist")

    # 4. Live Specifics
    if is_live:
        cmd.append("--live-from-start")

    # 5. FFmpeg Location
    if ffmpeg_path:
        cmd.extend(["--ffmpeg-location", ffmpeg_path])

    # 6. Playlist Items
    if is_playlist and playlist_items:
        items_str = ",".join(str(i) for i in playlist_items)
        cmd.extend(["--playlist-items", items_str])

    # 7. Format Selection
    if fmt == "mp3":
        # Extract audio as MP3 (high quality)
        cmd.extend([
            "-f", "bestaudio/best",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",  # "0" is best quality for mp3 in yt-dlp
        ])
    elif fmt == "original":
        # Download best individual file without merging
        cmd.extend(["-f", "best"])
    else:
        # Default: Video (mp4 preferred)
        cmd.extend([
            "-f", normalize_quality(quality),
            "--merge-output-format", "mp4",
        ])

    # 8. Final URL
    cmd.append(url)

    return cmd
