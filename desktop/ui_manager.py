"""
MediaGrab Desktop - UI Manager
Handles all CustomTkinter UI creation and event management
"""

import tkinter as tk
from typing import Any, Callable, Optional
import customtkinter as ctk

from main import APP_NAME


class UIManager:
    """Manages all UI components and their interactions"""
    
    def __init__(self, parent: ctk.CTk):
        self.parent = parent
        self.theme_switch = None
        self.ffmpeg_label = None
        
        # UI Components
        self.url_entry = None
        self.analyze_btn = None
        self.status_badge = None
        
        self.info_section = None
        self.info_body = None
        
        self.format_var = None
        self.quality_var = None
        self.quality_label = None
        self.quality_menu = None
        
        self.dir_label = None
        self.download_btn = None
        
        self.progress_section = None
        self.progress_bar = None
        self.progress_filename = None
        self.progress_pct = None
        self.progress_speed = None
        self.progress_eta = None
        self.pause_btn = None
        self.cancel_btn = None
        
        self.history_frame = None
        self.history_items = {}
    
    def build_header(self, on_update_check: Callable, on_show_about: Callable, on_theme_toggle: Callable) -> ctk.CTkFrame:
        """Build the application header"""
        bar = ctk.CTkFrame(self.parent, height=62, corner_radius=0, fg_color=("gray90", "gray15"))
        bar.pack(fill="x")
        bar.pack_propagate(False)
        
        ctk.CTkLabel(bar, text=f"  {APP_NAME}", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left", padx=20)
        ctk.CTkLabel(bar, text="Universal Video Downloader", font=ctk.CTkFont(size=12), text_color="gray").pack(side="left", padx=4)
        
        ctk.CTkButton(bar, text="ð", width=32, height=32, corner_radius=16, 
                     fg_color="transparent", hover_color=("gray80", "gray25"), 
                     command=on_update_check).pack(side="right", padx=6)
        
        ctk.CTkButton(bar, text="â", width=32, height=32, corner_radius=16, 
                     fg_color="transparent", hover_color=("gray80", "gray25"), 
                     command=on_show_about).pack(side="right", padx=10)
        
        self.theme_switch = ctk.CTkSwitch(bar, text="Dark", width=80, 
                                        command=on_theme_toggle, 
                                        onvalue="dark", offvalue="light")
        self.theme_switch.pack(side="right", padx=18)
        
        if ctk.get_appearance_mode() == "Dark":
            self.theme_switch.select()
        
        ffmpeg_status_row = ctk.CTkFrame(bar, fg_color="transparent")
        ffmpeg_status_row.pack(side="right", padx=10)
        self.ffmpeg_label = ctk.CTkLabel(ffmpeg_status_row, text="FFmpeg: Checking...", 
                                        font=ctk.CTkFont(size=11), text_color="gray")
        self.ffmpeg_label.pack(side="left")
        
        return bar
    
    def build_url_section(self, parent: Any, on_paste: Callable, on_analyze: Callable) -> tuple:
        """Build the URL input section"""
        from main import SectionFrame, StatusBadge
        
        sec = SectionFrame(parent, "  Video URL")
        sec.pack(fill="x", pady=(0, 10))
        row = sec.body()
        
        self.url_entry = ctk.CTkEntry(row, placeholder_text="Paste any video or playlist URLâ¦", 
                                   height=44, font=ctk.CTkFont(size=13))
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.url_entry.bind("<Return>", lambda _: on_analyze())
        
        ctk.CTkButton(row, text="ð", width=44, height=44, corner_radius=8, 
                     command=on_paste).pack(side="left", padx=(0, 8))
        
        self.analyze_btn = ctk.CTkButton(row, text="Analyze", width=100, height=44, 
                                       font=ctk.CTkFont(size=13, weight="bold"), 
                                       command=on_analyze)
        self.analyze_btn.pack(side="left")
        
        self.status_badge = StatusBadge(sec, text="  Idle  ", corner_radius=6, height=24)
        self.status_badge.pack(anchor="w", padx=14, pady=(0, 10))
        self.status_badge.set("Idle", "idle")
        
        return sec, row
    
    def build_info_section(self, parent: Any) -> tuple:
        """Build the media information section"""
        from main import SectionFrame
        
        self.info_section = SectionFrame(parent, "  Media Information")
        body = self.info_section.body()
        self.info_body = body
        
        return self.info_section, body
    
    def build_options_section(self, parent: Any, on_fmt_change: Callable, on_quality_change: Callable) -> tuple:
        """Build the download options section"""
        from main import SectionFrame
        
        opt_sec = SectionFrame(parent, "  Download Options")
        opt_sec.pack(fill="x", pady=(0, 10))
        body = opt_sec.body()
        
        ctk.CTkLabel(body, text="Format:", font=ctk.CTkFont(weight="bold"), width=70).pack(side="left")
        
        self.format_var = ctk.StringVar(value="mp4")
        ctk.CTkRadioButton(body, text="MP3 (Audio)", variable=self.format_var, 
                         value="mp3", command=on_fmt_change).pack(side="left", padx=(4, 8))
        ctk.CTkRadioButton(body, text="MP4 (Video)", variable=self.format_var, 
                         value="mp4", command=on_fmt_change).pack(side="left", padx=(0, 8))
        ctk.CTkRadioButton(body, text="Original", variable=self.format_var, 
                         value="original", command=on_fmt_change).pack(side="left", padx=(0, 24))
        
        self.quality_label = ctk.CTkLabel(body, text="Quality:", font=ctk.CTkFont(weight="bold"), width=70)
        self.quality_var = ctk.StringVar(value="best")
        self.quality_menu = ctk.CTkOptionMenu(body, values=["best", "1080p", "720p", "480p", "360p"], 
                                           variable=self.quality_var, width=130, 
                                           command=on_quality_change)
        
        if self.format_var.get() == "mp4":
            self.quality_label.pack(side="left")
            self.quality_menu.pack(side="left")
        
        return opt_sec, body
    
    def build_output_section(self, parent: Any, on_browse: Callable, on_open_folder: Callable, output_dir: str) -> tuple:
        """Build the save location section"""
        from main import SectionFrame
        
        sec = SectionFrame(parent, "  Save Location")
        sec.pack(fill="x", pady=(0, 10))
        body = sec.body()
        
        self.dir_label = ctk.CTkLabel(body, text=output_dir, font=ctk.CTkFont(size=12), 
                                    text_color="gray", anchor="w")
        self.dir_label.pack(side="left", fill="x", expand=True, padx=(0, 12))
        
        ctk.CTkButton(body, text="Browseâ¦", width=90, height=34, command=on_browse).pack(side="left")
        ctk.CTkButton(body, text="Open", width=70, height=34, fg_color="transparent", 
                     border_width=1, command=lambda: on_open_folder(output_dir)).pack(side="left", padx=(8, 0))
        
        return sec, body
    
    def build_download_btn(self, parent: Any, on_download: Callable) -> ctk.CTkButton:
        """Build the download button"""
        self.download_btn = ctk.CTkButton(parent, text="  Download", height=52, 
                                         font=ctk.CTkFont(size=16, weight="bold"), 
                                         state="disabled", command=on_download)
        self.download_btn.pack(fill="x", pady=(0, 10))
        return self.download_btn
    
    def build_progress_section(self, parent: Any, on_pause: Callable, on_cancel: Callable) -> tuple:
        """Build the progress section"""
        from main import SectionFrame
        
        self.progress_section = SectionFrame(parent, "  Download Progress")
        body = self.progress_section.body()
        
        self.progress_filename = ctk.CTkLabel(body, text="", font=ctk.CTkFont(size=12), anchor="w")
        self.progress_filename.pack(fill="x", pady=(0, 4))
        
        self.progress_bar = ctk.CTkProgressBar(body, height=16, corner_radius=8)
        self.progress_bar.pack(fill="x", pady=(0, 4))
        self.progress_bar.set(0)
        
        stat_row = ctk.CTkFrame(body, fg_color="transparent")
        stat_row.pack(fill="x")
        
        self.progress_pct = ctk.CTkLabel(stat_row, text="0%", font=ctk.CTkFont(size=12, weight="bold"))
        self.progress_pct.pack(side="left")
        
        self.progress_speed = ctk.CTkLabel(stat_row, text="", font=ctk.CTkFont(size=12), text_color="gray")
        self.progress_speed.pack(side="left", padx=12)
        
        self.progress_eta = ctk.CTkLabel(stat_row, text="", font=ctk.CTkFont(size=12), text_color="gray")
        self.progress_eta.pack(side="left")
        
        self.pause_btn = ctk.CTkButton(stat_row, text="  Pause", width=90, height=26, command=on_pause)
        self.pause_btn.pack(side="right")
        
        self.cancel_btn = ctk.CTkButton(body, text="  Cancel", width=100, height=30, 
                                      fg_color=("red3", "red4"), hover_color=("red4", "red3"), 
                                      command=on_cancel)
        self.cancel_btn.pack(anchor="e", pady=(8, 0))
        
        return self.progress_section, body
    
    def build_history_section(self, parent: Any, on_open_folder: Callable, on_clear_history: Callable, output_dir: str) -> tuple:
        """Build the history section"""
        from main import SectionFrame
        
        sec = SectionFrame(parent, "  Recent Downloads")
        sec.pack(fill="x", pady=(0, 10))
        body = sec.body()
        
        self.history_frame = ctk.CTkScrollableFrame(body, height=300, fg_color="transparent")
        self.history_frame.pack(fill="x")
        
        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.pack(fill="x", pady=(6, 0))
        
        ctk.CTkButton(btn_row, text="Open Folder", width=110, height=28, 
                     command=lambda: on_open_folder(output_dir)).pack(side="left")
        ctk.CTkButton(btn_row, text="Clear History", width=110, height=28, 
                     fg_color="transparent", border_width=1, 
                     command=on_clear_history).pack(side="right")
        
        return sec, body
    
    def show_progress(self) -> None:
        """Show the progress section"""
        if self.progress_section:
            self.progress_section.pack(fill="x", pady=(0, 10))
    
    def hide_progress(self) -> None:
        """Hide the progress section"""
        if self.progress_section:
            self.progress_section.pack_forget()
    
    def show_info_section(self) -> None:
        """Show the info section"""
        if self.info_section:
            self.info_section.pack(fill="x", pady=(0, 10))
    
    def hide_info_section(self) -> None:
        """Hide the info section"""
        if self.info_section:
            self.info_section.pack_forget()
    
    def update_progress(self, progress_data: dict) -> None:
        """Update progress display"""
        if not self.progress_bar:
            return
        
        percentage = progress_data.get("progress", 0) / 100
        self.progress_bar.set(percentage)
        
        if self.progress_pct:
            self.progress_pct.configure(text=f"{progress_data.get('progress', 0):.1f}%")
        
        if self.progress_speed and progress_data.get("speed"):
            self.progress_speed.configure(text=f"Speed: {progress_data['speed']}")
        
        if self.progress_eta and progress_data.get("eta"):
            self.progress_eta.configure(text=f"ETA: {progress_data['eta']}")
        
        if self.progress_filename and progress_data.get("filename"):
            self.progress_filename.configure(text=progress_data["filename"][:80])
    
    def update_status(self, status: str, message: str) -> None:
        """Update status badge"""
        if self.status_badge:
            self.status_badge.set(status, message)
    
    def update_ffmpeg_status(self, status: str) -> None:
        """Update FFmpeg status label"""
        if self.ffmpeg_label:
            self.ffmpeg_label.configure(text=f"FFmpeg: {status}")
    
    def set_analyze_button_state(self, state: str, text: Optional[str] = None) -> None:
        """Set analyze button state and optional text"""
        if self.analyze_btn:
            self.analyze_btn.configure(state=state)
            if text:
                self.analyze_btn.configure(text=text)
    
    def set_download_button_state(self, state: str, text: Optional[str] = None) -> None:
        """Set download button state and optional text"""
        if self.download_btn:
            self.download_btn.configure(state=state)
            if text:
                self.download_btn.configure(text=text)
    
    def set_pause_button_text(self, text: str) -> None:
        """Set pause button text"""
        if self.pause_btn:
            self.pause_btn.configure(text=text)
    
    def update_quality_visibility(self, show: bool) -> None:
        """Show or hide quality options based on format"""
        if self.quality_label and self.quality_menu:
            if show:
                self.quality_label.pack(side="left")
                self.quality_menu.pack(side="left")
            else:
                self.quality_label.pack_forget()
                self.quality_menu.pack_forget()
    
    def update_output_dir_display(self, output_dir: str) -> None:
        """Update output directory display"""
        if self.dir_label:
            self.dir_label.configure(text=output_dir)
    
    def clear_info_section(self) -> None:
        """Clear all widgets from info section"""
        if self.info_body:
            for widget in self.info_body.winfo_children():
                widget.destroy()
    
    def get_url(self) -> str:
        """Get URL from entry field"""
        if self.url_entry:
            return self.url_entry.get().strip()
        return ""
    
    def set_url(self, url: str) -> None:
        """Set URL in entry field"""
        if self.url_entry:
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, url)
    
    def get_format(self) -> str:
        """Get selected format"""
        if self.format_var:
            return self.format_var.get()
        return "mp4"
    
    def get_quality(self) -> str:
        """Get selected quality"""
        if self.quality_var:
            return self.quality_var.get()
        return "best"
    
    def toggle_theme(self) -> None:
        """Toggle theme switch"""
        if self.theme_switch:
            current = ctk.get_appearance_mode()
            new_mode = "Light" if current == "Dark" else "Dark"
            ctk.set_appearance_mode(new_mode)
            # Update switch state
            if new_mode == "Dark":
                self.theme_switch.select()
            else:
                self.theme_switch.deselect()
