"""
Shared utility for yt-dlp command construction.
Ensures consistency between Desktop and Backend downloads.
"""

import os
from typing import List, Optional


def build_yt_dlp_command(
    url: str,
    output_dir: str,
    fmt: str = "mp4",
    quality: str = "best",
    ffmpeg_path: Optional[str] = None,
    is_playlist: bool = False,
    playlist_items: Optional[List[int | str]] = None,
    is_live: bool = False,
) -> List[str]:
    """
    Constructs a yt-dlp command-line argument list.
    """
    # 1. Determine Output Template
    if is_playlist:
        # For playlists, we usually want index prefixing
        outtmpl = os.path.join(output_dir, "%(playlist_index)03d - %(title)s.%(ext)s")
    else:
        outtmpl = os.path.join(output_dir, "%(title)s.%(ext)s")

    # 2. Base Command
    # We use --newline and a custom --progress-template for easier regex parsing
    cmd = [
        "yt-dlp",
        "--newline",
        "--progress",
        "--progress-template", "download:[%(progress.downloaded_bytes)s/%(progress.total_bytes)s] [%(progress.speed)s] [%(progress.eta)s] [%(progress.status)s]",
        "-o", outtmpl,
    ]

    # 3. Platform/Live Specifics
    if is_live:
        cmd.append("--live-from-start")

    # 4. FFmpeg Location
    if ffmpeg_path:
        cmd.extend(["--ffmpeg-location", ffmpeg_path])

    # 5. Playlist Items
    if is_playlist and playlist_items:
        items_str = ",".join(str(i) for i in playlist_items)
        cmd.extend(["--playlist-items", items_str])

    # 6. Format Selection
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
        q = quality if quality != "best" else "bestvideo+bestaudio/best"
        cmd.extend([
            "-f", q,
            "--merge-output-format", "mp4"
        ])

    # 7. Final URL
    cmd.append(url)

    return cmd
