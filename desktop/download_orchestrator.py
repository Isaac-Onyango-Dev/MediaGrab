"""
MediaGrab Desktop - Download Orchestrator
Handles download workflow coordination and task management
"""

import threading
import time
import uuid
from typing import Any, Callable, Dict, Optional
from pathlib import Path

import yt_dlp
from downloader import analyze_url, VideoDownloader, MEDIAGRAB_ROOT


class DownloadOrchestrator:
    """Manages download workflows and task coordination"""
    
    def __init__(self, parent, ui_manager, config_manager):
        self.parent = parent
        self.ui_manager = ui_manager
        self.config_manager = config_manager
        
        self.current_task_id = None
        self.current_result = None
        self.selected_videos = {}
        self.playlist_check_vars = []
        self.playlist_count_label = None
        
        # Progress tracking
        self.progress_history = []
        self.progress_history_max_size = 3
        self.progress_history_index = 0
        self.progress_pending = False
        self.last_progress_update = 0
        
        # Download manager
        self.download_manager = None
    
    def start_analysis(self, url: str) -> None:
        """Start URL analysis in background thread"""
        if not url:
            self.ui_manager.update_status("error", "Please enter a URL")
            return
        
        self.ui_manager.set_analyze_button_state("disabled", "Analyzingâ¦")
        self.ui_manager.update_status("info", "Analyzingâ¦")
        self.ui_manager.hide_info_section()
        
        threading.Thread(target=self._analyze_thread, args=(url,), daemon=True).start()
    
    def _analyze_thread(self, url: str) -> None:
        """Background thread for URL analysis"""
        try:
            result = analyze_url(url)
            self.parent.after(0, self._on_analysis_success, result)
        except Exception as exc:
            self.parent.after(0, self._on_analysis_error, str(exc))
    
    def _on_analysis_success(self, result: dict) -> None:
        """Handle successful URL analysis"""
        self.current_result = result
        self.ui_manager.set_analyze_button_state("normal", "Analyze")
        self.ui_manager.update_status("success", "Ready to download")
        self._render_media_info(result)
        self._update_download_button_label()
    
    def _on_analysis_error(self, error_msg: str) -> None:
        """Handle URL analysis error"""
        self.ui_manager.set_analyze_button_state("normal", "Analyze")
        user_msg = self._classify_error(error_msg)
        self.ui_manager.update_status("error", f"Error: {user_msg[:70]}")
    
    def _classify_error(self, error_msg: str) -> str:
        """Classify and simplify error messages for users"""
        error_lower = error_msg.lower()
        
        if "unsupported url" in error_lower or "invalid url" in error_lower:
            return "Unsupported URL format"
        elif "network" in error_lower or "connection" in error_lower:
            return "Network connection error"
        elif "video not available" in error_lower or "private" in error_lower:
            return "Video not available or private"
        elif "region" in error_lower or "blocked" in error_lower:
            return "Video blocked in your region"
        elif "age" in error_lower or "restricted" in error_lower:
            return "Age-restricted content"
        elif "ffmpeg" in error_lower:
            return "FFmpeg not installed or outdated"
        else:
            return "Unable to analyze this URL"
    
    def _render_media_info(self, result: dict) -> None:
        """Render media information in UI"""
        self.ui_manager.clear_info_section()
        self.selected_videos = {}
        
        if result.get("type") == "playlist":
            self._render_playlist_info(result)
        else:
            self._render_single_video_info(result)
        
        self.ui_manager.show_info_section()
    
    def _render_playlist_info(self, result: dict) -> None:
        """Render playlist information"""
        import customtkinter as ctk
        
        # Playlist title and info
        ctk.CTkLabel(self.ui_manager.info_body, text=f"  {result['title']}", 
                    font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(self.ui_manager.info_body, text=f"{result['count']} videos  Â·  {result['platform'].title()}", 
                    text_color="gray", anchor="w").pack(fill="x", pady=(0, 8))
        
        # Select/Deselect buttons
        btn_frame = ctk.CTkFrame(self.ui_manager.info_body, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 6))
        
        ctk.CTkButton(btn_frame, text="Select All", width=90, height=26, 
                     command=lambda: self._toggle_all_playlist_items(True, result)).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_frame, text="Deselect All", width=90, height=26, 
                     fg_color="transparent", border_width=1,
                     command=lambda: self._toggle_all_playlist_items(False, result)).pack(side="left")
        
        # Playlist items
        scroll_frame = ctk.CTkScrollableFrame(self.ui_manager.info_body, height=250, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, pady=(0, 8))
        
        self.playlist_check_vars = []
        for i, entry in enumerate(result.get("entries", [])):
            vid = entry.get("id", str(i))
            var = ctk.BooleanVar(value=True)
            self.playlist_check_vars.append((vid, var))
            self.selected_videos[vid] = True
            
            item = ctk.CTkFrame(scroll_frame, fg_color="transparent")
            item.pack(fill="x", pady=2)
            
            ctk.CTkCheckBox(item, text="", variable=var, width=24,
                           command=lambda v=vid, var=var: self._on_playlist_item_toggled(v, var)).pack(side="left")
            
            duration_str = entry.get('duration_str', 'N/A')
            title = entry.get('title', 'Unknown')
            ctk.CTkLabel(item, text=f"{i+1:>3}. [{duration_str}] {title}", 
                        font=ctk.CTkFont(size=11), anchor="w").pack(side="left", fill="x", expand=True)
        
        # Count label
        self.playlist_count_label = ctk.CTkLabel(self.ui_manager.info_body, 
                                                text=f"Selected: {result['count']} / {result['count']}", 
                                                text_color="gray", font=ctk.CTkFont(size=11))
        self.playlist_count_label.pack(anchor="w", pady=(0, 4))
    
    def _render_single_video_info(self, result: dict) -> None:
        """Render single video information"""
        import customtkinter as ctk
        
        rows = [
            ("Title", result["title"]),
            ("Channel", result.get("uploader", "Unknown")),
            ("Duration", result.get("duration_str", "Unknown")),
            ("Platform", result.get("platform", "Unknown").title())
        ]
        
        for label, value in rows:
            row = ctk.CTkFrame(self.ui_manager.info_body, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            ctk.CTkLabel(row, text=f"{label}:", width=80, font=ctk.CTkFont(weight="bold"), 
                        anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=value, anchor="w").pack(side="left", fill="x", expand=True)
    
    def _on_playlist_item_toggled(self, video_id: str, var) -> None:
        """Handle playlist item selection toggle"""
        self.selected_videos[video_id] = var.get()
        count = len([v for v in self.selected_videos.values() if v])
        if self.playlist_count_label:
            self.playlist_count_label.configure(text=f"Selected: {count} / {self.current_result['count']}")
        self._update_download_button_label()
    
    def _toggle_all_playlist_items(self, select_all: bool, result: dict) -> None:
        """Toggle all playlist items selection"""
        for vid, var in self.playlist_check_vars:
            var.set(select_all)
            self.selected_videos[vid] = select_all
        
        self._update_download_button_label()
        count = len([v for v in self.selected_videos.values() if v])
        if self.playlist_count_label:
            self.playlist_count_label.configure(text=f"Selected: {count} / {result['count']}")
    
    def _update_download_button_label(self) -> None:
        """Update download button based on selection"""
        if self.current_result and self.current_result.get("type") == "playlist":
            count = len([v for v in self.selected_videos.values() if v])
            state = "normal" if count > 0 else "disabled"
            text = f"  Download Selected ({count}/{self.current_result['count']})"
            self.ui_manager.set_download_button_state(state, text)
        else:
            self.ui_manager.set_download_button_state("normal", "  Download")
    
    def start_download(self) -> None:
        """Start the download process"""
        if not self.current_result:
            return
        
        # Check FFmpeg availability
        if not self._check_ffmpeg_availability():
            return
        
        url = self.ui_manager.get_url()
        if not url:
            self.ui_manager.update_status("error", "Please enter a URL")
            return
        
        # Prepare download parameters
        fmt = self.ui_manager.get_format()
        quality = self.ui_manager.get_quality()
        output_dir = self.config_manager.get_output_dir()
        
        # Handle playlist selection
        selected_urls = []
        if self.current_result.get("type") == "playlist":
            selected_urls = [
                e["url"] for e in self.current_result.get("entries", []) 
                if self.selected_videos.get(e.get("id"))
            ]
        
        # Update UI
        self.ui_manager.set_download_button_state("disabled", " Downloadingâ¦")
        self.ui_manager.set_analyze_button_state("disabled")
        self.ui_manager.update_status("info", "Downloadingâ¦")
        self.ui_manager.show_progress()
        
        # Start download
        task_id = str(uuid.uuid4())
        self.current_task_id = task_id
        
        # Create download manager
        self.download_manager = VideoDownloader(
            url=url,
            fmt=fmt,
            quality=quality,
            output_dir=output_dir,
            task_id=task_id,
            downloads={},  # Will be populated by download manager
            playlist_items=selected_urls if selected_urls else None
        )
        
        # Start download in background thread
        threading.Thread(target=self._download_thread, args=(task_id,), daemon=True).start()
    
    def _check_ffmpeg_availability(self) -> bool:
        """Check if FFmpeg is available"""
        from main import ffmpeg_mgr
        
        if not ffmpeg_mgr.is_installed:
            if ffmpeg_mgr.installing:
                self.ui_manager.update_status("warning", "Please wait for FFmpeg to finish installing...")
                return False
            else:
                # Start FFmpeg installation
                from tkinter import messagebox
                messagebox.showwarning("FFmpeg Missing", 
                                     "FFmpeg is required for downloads. It will be installed automatically now.")
                self.parent._check_ffmpeg_status()
                return False
        
        return True
    
    def _download_thread(self, task_id: str) -> None:
        """Background thread for download execution"""
        try:
            self.download_manager.download()
            self.parent.after(0, self._on_download_complete, {"output_dir": self.download_manager.final_output_dir}, task_id)
        except Exception as exc:
            self.parent.after(0, self._on_download_error, str(exc), task_id)
    
    def _on_download_complete(self, data: dict, task_id: str) -> None:
        """Handle download completion"""
        if task_id == self.current_task_id:
            self.ui_manager.set_download_button_state("normal", "  Download")
            self.ui_manager.set_analyze_button_state("normal")
            self.ui_manager.update_status("success", "Download complete!")
        
        # Add to history
        self.parent._add_history_card(task_id, self.current_result)
        
        # Reset state
        self.current_task_id = None
        self.download_manager = None
    
    def _on_download_error(self, error_msg: str, task_id: str) -> None:
        """Handle download error"""
        if task_id == self.current_task_id:
            self.ui_manager.set_download_button_state("normal", "  Download")
            self.ui_manager.set_analyze_button_state("normal")
            self.ui_manager.update_status("error", f"Error: {error_msg[:80]}")
        
        # Add to history with error status
        if hasattr(self.parent, '_add_history_card'):
            error_result = self.current_result.copy() if self.current_result else {"title": "Unknown"}
            error_result["error"] = error_msg
            self.parent._add_history_card(task_id, error_result)
        
        # Reset state
        self.current_task_id = None
        self.download_manager = None
    
    def pause_download(self) -> bool:
        """Pause current download"""
        if self.download_manager and self.current_task_id:
            success = self.download_manager.pause()
            if success:
                self.ui_manager.set_pause_button_text("  Resume")
                return True
        return False
    
    def resume_download(self) -> bool:
        """Resume current download"""
        if self.download_manager and self.current_task_id:
            success = self.download_manager.resume()
            if success:
                self.ui_manager.set_pause_button_text("  Pause")
                return True
        return False
    
    def cancel_download(self) -> None:
        """Cancel current download"""
        if self.download_manager and self.current_task_id:
            self.download_manager.cancel()
            self._on_download_error("Cancelled", self.current_task_id)
    
    def toggle_pause_resume(self) -> None:
        """Toggle between pause and resume"""
        if self.current_task_id:
            btn_text = self.ui_manager.pause_btn.cget("text") if self.ui_manager.pause_btn else ""
            if "Pause" in btn_text:
                self.pause_download()
            else:
                self.resume_download()
    
    def update_progress(self, progress_data: dict) -> None:
        """Update download progress with smoothing"""
        if not self.current_task_id or progress_data.get("task_id") != self.current_task_id:
            return
        
        # Apply smoothing to progress percentage
        pct = progress_data.get("progress", 0)
        
        # Initialize progress history if needed
        if not hasattr(self, 'progress_history'):
            self.progress_history = []
            self.progress_history_max_size = 3
            self.progress_history_index = 0
        
        # Maintain circular buffer of fixed size
        if len(self.progress_history) < self.progress_history_max_size:
            self.progress_history.append(pct)
        else:
            # Replace oldest value in circular buffer
            self.progress_history[self.progress_history_index] = pct
            self.progress_history_index = (self.progress_history_index + 1) % self.progress_history_max_size
        
        # Calculate average of available values
        if self.progress_history:
            smoothed_pct = sum(self.progress_history) / len(self.progress_history)
        else:
            smoothed_pct = pct
        
        # Update UI with smoothed progress
        def _apply():
            self.progress_pending = False
            if progress_data.get("task_id") != self.current_task_id:
                return
            
            self.last_progress_update = time.monotonic()
            self.ui_manager.update_progress({
                "progress": smoothed_pct,
                "speed": progress_data.get("speed", ""),
                "eta": progress_data.get("eta", ""),
                "filename": progress_data.get("filename", ""),
                "current_item": progress_data.get("current_item"),
                "total_items": progress_data.get("total_items")
            })
        
        # Schedule UI update
        if not self.progress_pending:
            self.progress_pending = True
            self.parent.after_idle(_apply)
    
    def cleanup(self) -> None:
        """Clean up resources"""
        if self.download_manager and self.current_task_id:
            self.cancel_download()
        
        self.current_task_id = None
        self.current_result = None
        self.selected_videos = {}
        self.playlist_check_vars = []
        self.download_manager = None
