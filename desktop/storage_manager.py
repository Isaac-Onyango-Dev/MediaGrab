"""
MediaGrab Desktop - Storage Manager
Handles disk space checking, storage warnings, and path management.
Production v1.0.0 - No test/dev code.
"""

import os
import shutil
from pathlib import Path
from typing import Optional


class StorageManager:
    """Manages storage awareness for MediaGrab desktop app."""
    
    MIN_INSTALL_SPACE_MB = 200
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
    def has_enough_space(path: str, required_mb: int) -> tuple[bool, dict]:
        """Check if there's enough space at the given path.
        
        Returns:
            Tuple of (has_space, disk_info)
        """
        info = StorageManager.get_disk_info(path)
        if "error" in info:
            return True, info  # Allow if can't check
        
        return info["free_mb"] >= required_mb, info
    
    @staticmethod
    def check_install_space(install_path: str) -> tuple[bool, dict]:
        """Check if there's enough space for installation."""
        return StorageManager.has_enough_space(
            install_path,
            StorageManager.MIN_INSTALL_SPACE_MB
        )
    
    @staticmethod
    def check_download_space(download_path: str) -> tuple[bool, dict]:
        """Check if there's enough space for downloads."""
        return StorageManager.has_enough_space(
            download_path,
            StorageManager.MIN_DOWNLOAD_SPACE_MB
        )
    
    @staticmethod
    def is_low_space(path: str) -> bool:
        """Check if space is below warning threshold."""
        info = StorageManager.get_disk_info(path)
        return info.get("free_mb", float("inf")) < StorageManager.LOW_SPACE_WARNING_MB
    
    @staticmethod
    def get_app_data_size(app_data_dir: str) -> int:
        """Calculate total size of MediaGrab app data."""
        total_size = 0
        if not os.path.exists(app_data_dir):
            return 0
        
        for dirpath, dirnames, filenames in os.walk(app_data_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except (OSError, FileNotFoundError):
                    pass
        
        return total_size
    
    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Format bytes to human-readable string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024**3:
            return f"{size_bytes / (1024**2):.1f} MB"
        else:
            return f"{size_bytes / (1024**3):.2f} GB"
    
    @staticmethod
    def get_default_download_dir() -> str:
        """Get the default download directory."""
        return str(Path.home() / "Downloads" / "MediaGrab")
    
    @staticmethod
    def get_app_data_dir() -> str:
        """Get the app data directory (platform-specific)."""
        import platform
        system = platform.system()
        
        if system == "Windows":
            return str(Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "MediaGrab")
        elif system == "Darwin":
            return str(Path.home() / "Library" / "Application Support" / "MediaGrab")
        else:
            return str(Path.home() / ".local" / "share" / "MediaGrab")
    
    @staticmethod
    def ensure_directories_exist() -> tuple[str, str]:
        """Create necessary directories if they don't exist.
        
        Returns:
            Tuple of (app_data_dir, download_dir)
        """
        app_data_dir = StorageManager.get_app_data_dir()
        download_dir = StorageManager.get_default_download_dir()
        
        os.makedirs(app_data_dir, exist_ok=True)
        os.makedirs(download_dir, exist_ok=True)
        
        return app_data_dir, download_dir
