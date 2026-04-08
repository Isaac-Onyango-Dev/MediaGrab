"""
MediaGrab Desktop - History Manager
Handles download history operations and management
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import customtkinter as ctk


class HistoryManager:
    """Manages download history and history UI components"""
    
    def __init__(self, parent, ui_manager):
        self.parent = parent
        self.ui_manager = ui_manager
        
        self.history_file = Path.home() / ".mediagrab" / "history.json"
        self.history_file.parent.mkdir(exist_ok=True)
        
        self.history_list = []
        self.history_items = {}  # task_id -> HistoryItem
        
        # Callbacks for history item actions
        self.on_pause_callback = None
        self.on_resume_callback = None
        self.on_cancel_callback = None
        self.on_retry_callback = None
        self.on_delete_callback = None
        self.on_open_callback = None
    
    def set_callbacks(self, on_pause: Callable = None, on_resume: Callable = None, 
                     on_cancel: Callable = None, on_retry: Callable = None,
                     on_delete: Callable = None, on_open: Callable = None):
        """Set callback functions for history item actions"""
        self.on_pause_callback = on_pause
        self.on_resume_callback = on_resume
        self.on_cancel_callback = on_cancel
        self.on_retry_callback = on_retry
        self.on_delete_callback = on_delete
        self.on_open_callback = on_open
    
    def load_history(self) -> List[Dict[str, Any]]:
        """Load download history from file"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history_list = json.load(f)
            else:
                self.history_list = []
                self.save_history()
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading history: {e}")
            self.history_list = []
        
        return self.history_list
    
    def save_history(self) -> bool:
        """Save download history to file"""
        try:
            # Keep only last 100 items to prevent file from growing too large
            if len(self.history_list) > 100:
                self.history_list = self.history_list[-100:]
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history_list, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"Error saving history: {e}")
            return False
    
    def add_history_item(self, task_id: str, data: Dict[str, Any]) -> None:
        """Add a new item to history"""
        history_entry = {
            "task_id": task_id,
            "title": data.get("title", "Unknown"),
            "url": data.get("url", ""),
            "platform": data.get("platform", "unknown"),
            "format": data.get("format", "unknown"),
            "quality": data.get("quality", "unknown"),
            "status": data.get("status", "pending"),
            "progress": data.get("progress", 0),
            "message": data.get("message", ""),
            "output_dir": data.get("output_dir", ""),
            "file_size": data.get("file_size", 0),
            "duration": data.get("duration", 0),
            "timestamp": datetime.now().isoformat(),
            "error": data.get("error", "")
        }
        
        # Remove any existing entry with same task_id
        self.history_list = [item for item in self.history_list if item.get("task_id") != task_id]
        
        # Add new entry
        self.history_list.append(history_entry)
        
        # Keep history sorted by timestamp (newest first)
        self.history_list.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Save to file
        self.save_history()
        
        # Update UI
        self.refresh_history_display()
    
    def update_history_item(self, task_id: str, updates: Dict[str, Any]) -> None:
        """Update an existing history item"""
        for item in self.history_list:
            if item.get("task_id") == task_id:
                item.update(updates)
                item["timestamp"] = datetime.now().isoformat()  # Update timestamp
        
        # Update UI item if it exists
        if task_id in self.history_items:
            self.history_items[task_id].update_state(updates)
        
        # Save to file
        self.save_history()
    
    def remove_history_item(self, task_id: str) -> bool:
        """Remove an item from history"""
        original_length = len(self.history_list)
        self.history_list = [item for item in self.history_list if item.get("task_id") != task_id]
        
        # Remove UI item if it exists
        if task_id in self.history_items:
            self.history_items[task_id].destroy()
            del self.history_items[task_id]
        
        # Save if item was removed
        if len(self.history_list) < original_length:
            self.save_history()
            return True
        
        return False
    
    def clear_history(self) -> bool:
        """Clear all history items"""
        try:
            # Clear UI items
            for item in self.history_items.values():
                item.destroy()
            self.history_items.clear()
            
            # Clear history list
            self.history_list.clear()
            
            # Save empty history
            self.save_history()
            
            return True
        except Exception as e:
            print(f"Error clearing history: {e}")
            return False
    
    def get_history_item(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific history item"""
        for item in self.history_list:
            if item.get("task_id") == task_id:
                return item
        return None
    
    def get_recent_history(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent history items"""
        return self.history_list[:count]
    
    def search_history(self, query: str) -> List[Dict[str, Any]]:
        """Search history by title or URL"""
        query_lower = query.lower()
        return [
            item for item in self.history_list
            if query_lower in item.get("title", "").lower() or 
               query_lower in item.get("url", "").lower()
        ]
    
    def get_history_stats(self) -> Dict[str, Any]:
        """Get statistics about download history"""
        total = len(self.history_list)
        completed = len([item for item in self.history_list if item.get("status") == "complete"])
        failed = len([item for item in self.history_list if item.get("status") in ["error", "cancelled"]])
        in_progress = len([item for item in self.history_list if item.get("status") == "downloading"])
        
        # Platform breakdown
        platforms = {}
        for item in self.history_list:
            platform = item.get("platform", "unknown")
            platforms[platform] = platforms.get(platform, 0) + 1
        
        # Format breakdown
        formats = {}
        for item in self.history_list:
            format_type = item.get("format", "unknown")
            formats[format_type] = formats.get(format_type, 0) + 1
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "success_rate": (completed / total * 100) if total > 0 else 0,
            "platforms": platforms,
            "formats": formats
        }
    
    def export_history(self, file_path: str) -> bool:
        """Export history to specified file"""
        try:
            export_path = Path(file_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self.history_list, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error exporting history: {e}")
            return False
    
    def import_history(self, file_path: str, merge: bool = True) -> bool:
        """Import history from specified file"""
        try:
            import_path = Path(file_path)
            if not import_path.exists():
                return False
            
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_history = json.load(f)
            
            if merge:
                # Merge with existing history, avoiding duplicates
                existing_task_ids = {item.get("task_id") for item in self.history_list}
                for item in imported_history:
                    if item.get("task_id") not in existing_task_ids:
                        self.history_list.append(item)
            else:
                # Replace existing history
                self.history_list = imported_history
            
            # Sort by timestamp
            self.history_list.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            # Save and refresh UI
            self.save_history()
            self.refresh_history_display()
            
            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error importing history: {e}")
            return False
    
    def refresh_history_display(self) -> None:
        """Refresh the history display in UI"""
        if not self.ui_manager.history_frame:
            return
        
        # Clear existing items
        for item in self.history_items.values():
            item.destroy()
        self.history_items.clear()
        
        # Add recent items (limit to 20 for performance)
        recent_items = self.get_recent_history(20)
        for item_data in recent_items:
            self._add_history_card(item_data.get("task_id"), item_data)
    
    def _add_history_card(self, task_id: str, data: Dict[str, Any]) -> None:
        """Add a history card to the UI"""
        from main import HistoryItem
        
        card = HistoryItem(
            self.ui_manager.history_frame,
            task_id,
            data,
            on_pause=self.on_history_pause,
            on_resume=self.on_history_resume,
            on_cancel=self.on_history_cancel,
            on_retry=self.on_history_retry,
            on_delete=self.on_history_delete,
            on_open=self.on_history_open
        )
        
        self.history_items[task_id] = card
    
    def _history_pause(self, task_id: str) -> None:
        """Handle history item pause"""
        if self.on_pause_callback:
            self.on_pause_callback(task_id)
    
    def _history_resume(self, task_id: str) -> None:
        """Handle history item resume"""
        if self.on_resume_callback:
            self.on_resume_callback(task_id)
    
    def _history_cancel(self, task_id: str) -> None:
        """Handle history item cancel"""
        if self.on_cancel_callback:
            self.on_cancel_callback(task_id)
    
    def _history_retry(self, task_id: str) -> None:
        """Handle history item retry"""
        if self.on_retry_callback:
            self.on_retry_callback(task_id)
    
    def _history_delete(self, task_id: str) -> None:
        """Handle history item delete"""
        self.remove_history_item(task_id)
    
    def _history_open(self, task_id: str) -> None:
        """Handle history item open folder"""
        if self.on_open_callback:
            self.on_open_callback(task_id)
    
    def cleanup_old_history(self, days: int = 30) -> int:
        """Remove history items older than specified days"""
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        original_length = len(self.history_list)
        self.history_list = [
            item for item in self.history_list
            if datetime.fromisoformat(item.get("timestamp", datetime.now().isoformat())).timestamp() > cutoff_date
        ]
        
        # Remove UI items for deleted history
        removed_task_ids = set()
        for item in self.history_list[:original_length]:
            task_id = item.get("task_id")
            if task_id not in [i.get("task_id") for i in self.history_list]:
                removed_task_ids.add(task_id)
        
        for task_id in removed_task_ids:
            if task_id in self.history_items:
                self.history_items[task_id].destroy()
                del self.history_items[task_id]
        
        # Save if items were removed
        removed_count = original_length - len(self.history_list)
        if removed_count > 0:
            self.save_history()
        
        return removed_count
    
    def get_failed_downloads(self) -> List[Dict[str, Any]]:
        """Get list of failed downloads for retry"""
        return [
            item for item in self.history_list
            if item.get("status") in ["error", "cancelled"]
        ]
    
    def retry_failed_download(self, task_id: str) -> bool:
        """Retry a failed download"""
        history_item = self.get_history_item(task_id)
        if not history_item:
            return False
        
        # Update status to indicate retry
        self.update_history_item(task_id, {
            "status": "pending",
            "message": "Retryingâ¦",
            "progress": 0
        })
        
        # Trigger retry callback
        if self.on_retry_callback:
            self.on_retry_callback(task_id)
        
        return True
    
    def get_download_history_by_platform(self, platform: str) -> List[Dict[str, Any]]:
        """Get history items for specific platform"""
        return [
            item for item in self.history_list
            if item.get("platform", "").lower() == platform.lower()
        ]
    
    def get_download_history_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get history items within date range"""
        start_timestamp = start_date.timestamp()
        end_timestamp = end_date.timestamp()
        
        return [
            item for item in self.history_list
            if start_timestamp <= datetime.fromisoformat(item.get("timestamp", "")).timestamp() <= end_timestamp
        ]
