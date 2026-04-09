"""
MediaGrab Backend - Storage Manager
Handles server-side disk space checking and download validation.
Production v1.0.0 - No test/dev code.
"""

import os
import shutil
from pathlib import Path
from typing import Optional


class ServerStorageManager:
    """Manages storage awareness for MediaGrab backend server."""
    
    MIN_DOWNLOAD_SPACE_MB = 100
    LOW_SPACE_WARNING_MB = 500
    
    @staticmethod
    def get_disk_info(path: str) -> dict:
        """Get disk space information for the given path."""
        try:
            usage = shutil.disk_usage(path)
            return {
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "total_gb": usage.total / (1024**3),
                "used_gb": usage.used / (1024**3),
                "free_gb": usage.free / (1024**3),
                "free_mb": usage.free / (1024**2),
                "usage_percent": (usage.used / usage.total) * 100 if usage.total > 0 else 0
            }
        except Exception as e:
            return {
                "error": str(e),
                "total_bytes": 0,
                "used_bytes": 0,
                "free_bytes": 0,
                "total_gb": 0,
                "used_gb": 0,
                "free_gb": 0,
                "free_mb": 0,
                "usage_percent": 0
            }
    
    @staticmethod
    def check_output_dir_space(output_dir: str) -> dict:
        """Check available space in output directory.
        
        Returns:
            Dict with space info and whether downloads should be allowed
        """
        os.makedirs(output_dir, exist_ok=True)
        info = ServerStorageManager.get_disk_info(output_dir)
        
        if "error" in info:
            return {
                "can_download": True,
                "free_mb": 0,
                "warning": "Could not check disk space",
                "info": info
            }
        
        can_download = info["free_mb"] >= ServerStorageManager.MIN_DOWNLOAD_SPACE_MB
        is_low = info["free_mb"] < ServerStorageManager.LOW_SPACE_WARNING_MB
        
        return {
            "can_download": can_download,
            "free_mb": info["free_mb"],
            "free_gb": info["free_gb"],
            "is_low_space": is_low,
            "usage_percent": info["usage_percent"],
            "warning": f"Low disk space: {info['free_mb']:.0f}MB remaining" if is_low else None,
            "info": info
        }
    
    @staticmethod
    def estimate_download_size(url: str) -> Optional[int]:
        """Estimate file size from URL metadata (in MB).
        
        This is a rough estimate - actual size may vary.
        Returns None if estimation fails.
        """
        try:
            import yt_dlp
            
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if info and "formats" in info:
                    # Get the largest format size as estimate
                    max_size = 0
                    for fmt in info["formats"]:
                        size = fmt.get("filesize") or fmt.get("filesize_approx")
                        if size and size > max_size:
                            max_size = size
                    
                    if max_size > 0:
                        return max_size / (1024 * 1024)  # Convert to MB
                    
                    # Fallback: estimate based on duration
                    duration = info.get("duration", 0)
                    if duration > 0:
                        # Rough estimate: 5MB per minute for video, 1MB for audio
                        return (duration / 60) * 5
                
                return None
        except Exception:
            return None
    
    @staticmethod
    def reject_if_insufficient_space(url: str, output_dir: str) -> dict:
        """Check if there's enough space for a download.
        
        Returns:
            Dict with:
            - allowed: bool
            - reason: str (if rejected)
            - estimated_size_mb: float
            - free_space_mb: float
        """
        space_info = ServerStorageManager.check_output_dir_space(output_dir)
        estimated_size = ServerStorageManager.estimate_download_size(url)
        
        if not space_info["can_download"]:
            return {
                "allowed": False,
                "reason": f"Insufficient disk space. Only {space_info['free_mb']:.0f}MB available.",
                "estimated_size_mb": estimated_size,
                "free_space_mb": space_info["free_mb"]
            }
        
        if estimated_size and estimated_size > space_info["free_mb"]:
            return {
                "allowed": False,
                "reason": f"Estimated download size ({estimated_size:.0f}MB) exceeds available space ({space_info['free_mb']:.0f}MB).",
                "estimated_size_mb": estimated_size,
                "free_space_mb": space_info["free_mb"]
            }
        
        return {
            "allowed": True,
            "estimated_size_mb": estimated_size,
            "free_space_mb": space_info["free_mb"],
            "warning": space_info.get("warning")
        }
