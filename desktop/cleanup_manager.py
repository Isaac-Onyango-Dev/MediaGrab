"""
MediaGrab Desktop - Cleanup Manager
Handles complete uninstall cleanup, removing all user data.
Production v1.0.0 - No test/dev code.
"""

import os
import shutil
from pathlib import Path
from typing import Optional


class CleanupManager:
    """Manages complete cleanup of all MediaGrab data."""
    
    @staticmethod
    def get_all_data_paths() -> dict:
        """Get all paths where MediaGrab stores data."""
        import platform
        system = platform.system()
        
        paths = {
            "downloads": str(Path.home() / "Downloads" / "MediaGrab"),
            "config": None,
            "history": None,
            "cache": None,
            "logs": None,
        }
        
        if system == "Windows":
            app_data = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
            paths["config"] = str(Path(app_data) / "MediaGrab" / "config.json")
            paths["history"] = str(Path(app_data) / "MediaGrab" / "history.json")
            paths["cache"] = str(Path(app_data) / "MediaGrab" / "cache")
            paths["logs"] = str(Path(app_data) / "MediaGrab" / "logs")
        elif system == "Darwin":
            app_support = str(Path.home() / "Library" / "Application Support" / "MediaGrab")
            paths["config"] = str(Path(app_support) / "config.json")
            paths["history"] = str(Path(app_support) / "history.json")
            paths["cache"] = str(Path(app_support) / "cache")
            paths["logs"] = str(Path(app_support) / "logs")
        else:
            paths["config"] = str(Path.home() / ".config" / "MediaGrab" / "config.json")
            paths["history"] = str(Path.home() / ".local" / "share" / "MediaGrab" / "history.json")
            paths["cache"] = str(Path.home() / ".cache" / "MediaGrab")
            paths["logs"] = str(Path.home() / ".local" / "share" / "MediaGrab" / "logs")
        
        return paths
    
    @staticmethod
    def get_total_data_size() -> dict:
        """Calculate size of all MediaGrab data."""
        paths = CleanupManager.get_all_data_paths()
        sizes = {}
        total = 0
        
        for name, path in paths.items():
            if path and os.path.exists(path):
                if os.path.isdir(path):
                    size = sum(
                        os.path.getsize(os.path.join(dirpath, filename))
                        for dirpath, dirnames, filenames in os.walk(path)
                        for filename in filenames
                    )
                else:
                    size = os.path.getsize(path)
                sizes[name] = size
                total += size
            else:
                sizes[name] = 0
        
        return {"sizes": sizes, "total": total}
    
    @staticmethod
    def cleanup_all(include_downloads: bool = False) -> dict:
        """Remove all MediaGrab data.
        
        Args:
            include_downloads: If True, also remove downloaded files
            
        Returns:
            Dict with cleanup results
        """
        paths = CleanupManager.get_all_data_paths()
        results = {
            "success": [],
            "failed": [],
            "skipped": []
        }
        
        # Remove config, history, cache, logs
        for name in ["config", "history", "cache", "logs"]:
            path = paths.get(name)
            if not path:
                continue
            
            try:
                if os.path.exists(path):
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                results["success"].append(name)
            except Exception as e:
                results["failed"].append({"name": name, "error": str(e)})
        
        # Remove downloads only if requested
        if include_downloads:
            download_path = paths.get("downloads")
            if download_path and os.path.exists(download_path):
                try:
                    shutil.rmtree(download_path)
                    results["success"].append("downloads")
                except Exception as e:
                    results["failed"].append({"name": "downloads", "error": str(e)})
        else:
            results["skipped"].append("downloads")
        
        # Remove app data directory if empty
        import platform
        system = platform.system()
        app_data_dir = None
        
        if system == "Windows":
            app_data_dir = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
            app_data_dir = str(Path(app_data_dir) / "MediaGrab")
        elif system == "Darwin":
            app_data_dir = str(Path.home() / "Library" / "Application Support" / "MediaGrab")
        else:
            app_data_dir = str(Path.home() / ".local" / "share" / "MediaGrab")
        
        if app_data_dir and os.path.exists(app_data_dir):
            try:
                if not os.listdir(app_data_dir):
                    os.rmdir(app_data_dir)
            except Exception:
                pass
        
        return results
    
    @staticmethod
    def cleanup_registry_windows() -> None:
        """Remove Windows registry entries (Windows only)."""
        import platform
        if platform.system() != "Windows":
            return
        
        try:
            import winreg
            # Remove MediaGrab registry keys
            key_path = r"Software\MediaGrab"
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
            except FileNotFoundError:
                pass
        except Exception:
            pass
