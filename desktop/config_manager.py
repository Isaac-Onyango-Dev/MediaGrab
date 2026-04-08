"""
MediaGrab Desktop - Configuration Manager
Handles configuration loading, saving, and management
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
import customtkinter as ctk


class ConfigManager:
    """Manages application configuration and settings"""
    
    def __init__(self):
        self.config_file = Path.home() / ".mediagrab" / "config.json"
        self.config_file.parent.mkdir(exist_ok=True)
        
        # Default configuration
        self.default_config = {
            "output_dir": str(Path.home() / "Downloads" / "MediaGrab"),
            "format": "mp4",
            "quality": "best",
            "theme": "dark",
            "window_geometry": "",
            "auto_check_updates": True,
            "max_concurrent_downloads": 3,
            "remember_last_url": False,
            "last_url": "",
            "ffmpeg_path": "",
            "proxy": "",
            "cookies_file": "",
            "embed_subs": True,
            "embed_thumbnail": True,
            "download_archive": True,
            "restrict_filenames": True
        }
        
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
                # Merge with defaults to handle missing keys
                config = self.default_config.copy()
                config.update(loaded_config)
                return config
            else:
                # Create default config file
                self.save_config(self.default_config)
                return self.default_config.copy()
        
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config: {e}")
            return self.default_config.copy()
    
    def save_config(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """Save configuration to file"""
        try:
            config_to_save = config if config is not None else self.config
            
            # Ensure directory exists
            self.config_file.parent.mkdir(exist_ok=True)
            
            # Save with pretty formatting
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)
            
            # Update internal config if different
            if config is not None and config != self.config:
                self.config = config.copy()
            
            return True
        
        except (IOError, TypeError) as e:
            print(f"Error saving config: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """Set configuration value"""
        try:
            self.config[key] = value
            return self.save_config()
        except Exception as e:
            print(f"Error setting config key '{key}': {e}")
            return False
    
    def get_output_dir(self) -> str:
        """Get output directory, ensure it exists"""
        output_dir = self.get("output_dir", str(Path.home() / "Downloads" / "MediaGrab"))
        
        # Ensure directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        return output_dir
    
    def set_output_dir(self, output_dir: str) -> bool:
        """Set output directory"""
        try:
            # Validate directory
            path = Path(output_dir)
            path.mkdir(parents=True, exist_ok=True)
            
            return self.set("output_dir", str(path.absolute()))
        except Exception as e:
            print(f"Error setting output directory: {e}")
            return False
    
    def get_format(self) -> str:
        """Get default format"""
        return self.get("format", "mp4")
    
    def set_format(self, format_type: str) -> bool:
        """Set default format"""
        if format_type not in ["mp3", "mp4", "original"]:
            return False
        return self.set("format", format_type)
    
    def get_quality(self) -> str:
        """Get default quality"""
        return self.get("quality", "best")
    
    def set_quality(self, quality: str) -> bool:
        """Set default quality"""
        valid_qualities = ["best", "1080p", "720p", "480p", "360p"]
        if quality not in valid_qualities:
            return False
        return self.set("quality", quality)
    
    def get_theme(self) -> str:
        """Get theme preference"""
        return self.get("theme", "dark")
    
    def set_theme(self, theme: str) -> bool:
        """Set theme preference"""
        if theme not in ["dark", "light", "system"]:
            return False
        return self.set("theme", theme)
    
    def get_window_geometry(self) -> str:
        """Get window geometry"""
        return self.get("window_geometry", "")
    
    def set_window_geometry(self, geometry: str) -> bool:
        """Set window geometry"""
        return self.set("window_geometry", geometry)
    
    def is_auto_check_updates(self) -> bool:
        """Check if auto update checking is enabled"""
        return self.get("auto_check_updates", True)
    
    def set_auto_check_updates(self, enabled: bool) -> bool:
        """Set auto update checking preference"""
        return self.set("auto_check_updates", enabled)
    
    def get_max_concurrent_downloads(self) -> int:
        """Get maximum concurrent downloads"""
        return self.get("max_concurrent_downloads", 3)
    
    def set_max_concurrent_downloads(self, count: int) -> bool:
        """Set maximum concurrent downloads"""
        if not isinstance(count, int) or count < 1 or count > 10:
            return False
        return self.set("max_concurrent_downloads", count)
    
    def remember_last_url(self) -> bool:
        """Check if last URL should be remembered"""
        return self.get("remember_last_url", False)
    
    def set_remember_last_url(self, enabled: bool) -> bool:
        """Set whether to remember last URL"""
        return self.set("remember_last_url", enabled)
    
    def get_last_url(self) -> str:
        """Get last URL"""
        return self.get("last_url", "")
    
    def set_last_url(self, url: str) -> bool:
        """Set last URL"""
        return self.set("last_url", url)
    
    def get_ffmpeg_path(self) -> str:
        """Get custom FFmpeg path"""
        return self.get("ffmpeg_path", "")
    
    def set_ffmpeg_path(self, path: str) -> bool:
        """Set custom FFmpeg path"""
        return self.set("ffmpeg_path", path)
    
    def get_proxy(self) -> str:
        """Get proxy configuration"""
        return self.get("proxy", "")
    
    def set_proxy(self, proxy: str) -> bool:
        """Set proxy configuration"""
        return self.set("proxy", proxy)
    
    def get_cookies_file(self) -> str:
        """Get cookies file path"""
        return self.get("cookies_file", "")
    
    def set_cookies_file(self, path: str) -> bool:
        """Set cookies file path"""
        return self.set("cookies_file", path)
    
    def is_embed_subs(self) -> bool:
        """Check if subtitles should be embedded"""
        return self.get("embed_subs", True)
    
    def set_embed_subs(self, enabled: bool) -> bool:
        """Set subtitle embedding preference"""
        return self.set("embed_subs", enabled)
    
    def is_embed_thumbnail(self) -> bool:
        """Check if thumbnail should be embedded"""
        return self.get("embed_thumbnail", True)
    
    def set_embed_thumbnail(self, enabled: bool) -> bool:
        """Set thumbnail embedding preference"""
        return self.set("embed_thumbnail", enabled)
    
    def is_download_archive(self) -> bool:
        """Check if download archive is enabled"""
        return self.get("download_archive", True)
    
    def set_download_archive(self, enabled: bool) -> bool:
        """Set download archive preference"""
        return self.set("download_archive", enabled)
    
    def is_restrict_filenames(self) -> bool:
        """Check if filenames should be restricted"""
        return self.get("restrict_filenames", True)
    
    def set_restrict_filenames(self, enabled: bool) -> bool:
        """Set filename restriction preference"""
        return self.set("restrict_filenames", enabled)
    
    def reset_to_defaults(self) -> bool:
        """Reset configuration to defaults"""
        return self.save_config(self.default_config.copy())
    
    def export_config(self, file_path: str) -> bool:
        """Export configuration to specified file"""
        try:
            export_path = Path(file_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error exporting config: {e}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """Import configuration from specified file"""
        try:
            import_path = Path(file_path)
            if not import_path.exists():
                return False
            
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # Validate imported config
            valid_config = self.default_config.copy()
            for key, value in imported_config.items():
                if key in valid_config:
                    valid_config[key] = value
            
            return self.save_config(valid_config)
        
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error importing config: {e}")
            return False
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration and return issues"""
        issues = []
        
        # Check output directory
        output_dir = self.get("output_dir")
        if not output_dir or not Path(output_dir).exists():
            issues.append("Output directory does not exist")
        
        # Check format
        format_type = self.get("format")
        if format_type not in ["mp3", "mp4", "original"]:
            issues.append("Invalid format specified")
        
        # Check quality
        quality = self.get("quality")
        valid_qualities = ["best", "1080p", "720p", "480p", "360p"]
        if quality not in valid_qualities:
            issues.append("Invalid quality specified")
        
        # Check concurrent downloads
        max_concurrent = self.get("max_concurrent_downloads")
        if not isinstance(max_concurrent, int) or max_concurrent < 1 or max_concurrent > 10:
            issues.append("Invalid max concurrent downloads")
        
        # Check FFmpeg path if specified
        ffmpeg_path = self.get("ffmpeg_path")
        if ffmpeg_path and not Path(ffmpeg_path).exists():
            issues.append("FFmpeg path does not exist")
        
        # Check cookies file if specified
        cookies_file = self.get("cookies_file")
        if cookies_file and not Path(cookies_file).exists():
            issues.append("Cookies file does not exist")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    def get_download_options(self) -> Dict[str, Any]:
        """Get download-related options as a dictionary"""
        return {
            "format": self.get_format(),
            "quality": self.get_quality(),
            "output_dir": self.get_output_dir(),
            "embed_subs": self.is_embed_subs(),
            "embed_thumbnail": self.is_embed_thumbnail(),
            "download_archive": self.is_download_archive(),
            "restrict_filenames": self.is_restrict_filenames(),
            "proxy": self.get_proxy(),
            "cookies_file": self.get_cookies_file(),
            "ffmpeg_path": self.get_ffmpeg_path()
        }
    
    def apply_theme(self) -> None:
        """Apply the configured theme"""
        theme = self.get_theme()
        if theme == "system":
            # Use system appearance
            current = ctk.get_appearance_mode()
            ctk.set_appearance_mode(current)
        else:
            ctk.set_appearance_mode(theme.title())
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration"""
        return {
            "output_dir": self.get_output_dir(),
            "format": self.get_format(),
            "quality": self.get_quality(),
            "theme": self.get_theme(),
            "auto_check_updates": self.is_auto_check_updates(),
            "max_concurrent_downloads": self.get_max_concurrent_downloads(),
            "remember_last_url": self.remember_last_url(),
            "embed_subs": self.is_embed_subs(),
            "embed_thumbnail": self.is_embed_thumbnail()
        }
