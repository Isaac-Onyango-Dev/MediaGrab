"""
MediaGrab Desktop - UI Manager Tests
Tests for UI component creation and management
"""

import pytest
import tkinter as tk
from unittest.mock import Mock, patch, MagicMock
import customtkinter as ctk

from ui_manager import UIManager


@pytest.fixture
def mock_parent():
    """Create a mock parent widget"""
    parent = Mock(spec=ctk.CTk)
    parent.after = Mock()
    parent.after_idle = Mock()
    return parent


@pytest.fixture
def ui_manager(mock_parent):
    """Create UIManager instance for testing"""
    return UIManager(mock_parent)


class TestUIManagerInitialization:
    """Test UIManager initialization"""
    
    def test_ui_manager_creation(self, ui_manager):
        """Test UIManager creation with default values"""
        assert ui_manager.parent is not None
        assert ui_manager.theme_switch is None
        assert ui_manager.ffmpeg_label is None
        assert ui_manager.url_entry is None
        assert ui_manager.analyze_btn is None
        assert ui_manager.status_badge is None
        assert ui_manager.info_section is None
        assert ui_manager.info_body is None
        assert ui_manager.format_var is None
        assert ui_manager.quality_var is None
        assert ui_manager.quality_label is None
        assert ui_manager.quality_menu is None
        assert ui_manager.dir_label is None
        assert ui_manager.download_btn is None
        assert ui_manager.progress_section is None
        assert ui_manager.progress_bar is None
        assert ui_manager.history_frame is None
        assert ui_manager.history_items == {}


class TestHeaderBuilding:
    """Test header building functionality"""
    
    def test_build_header(self, ui_manager):
        """Test header building with all components"""
        on_update_check = Mock()
        on_show_about = Mock()
        on_theme_toggle = Mock()
        
        with patch('ctk.CTkFrame') as mock_frame, \
             patch('ctk.CTkLabel') as mock_label, \
             patch('ctk.CTkButton') as mock_button, \
             patch('ctk.CTkSwitch') as mock_switch, \
             patch('ctk.get_appearance_mode', return_value="Dark"):
            
            # Mock frame creation
            frame_instance = Mock()
            mock_frame.return_value = frame_instance
            
            # Mock label creation
            label_instance = Mock()
            mock_label.return_value = label_instance
            
            # Mock button creation
            button_instance = Mock()
            mock_button.return_value = button_instance
            
            # Mock switch creation
            switch_instance = Mock()
            mock_switch.return_value = switch_instance
            
            # Build header
            header = ui_manager.build_header(on_update_check, on_show_about, on_theme_toggle)
            
            # Verify frame was created
            mock_frame.assert_called()
            
            # Verify theme switch was set
            assert ui_manager.theme_switch == switch_instance
            switch_instance.select.assert_called_once()
    
    def test_build_header_light_theme(self, ui_manager):
        """Test header building with light theme"""
        with patch('ctk.CTkFrame') as mock_frame, \
             patch('ctk.CTkLabel') as mock_label, \
             patch('ctk.CTkButton') as mock_button, \
             patch('ctk.CTkSwitch') as mock_switch, \
             patch('ctk.get_appearance_mode', return_value="Light"):
            
            frame_instance = Mock()
            mock_frame.return_value = frame_instance
            
            switch_instance = Mock()
            mock_switch.return_value = switch_instance
            
            ui_manager.build_header(Mock(), Mock(), Mock())
            
            # Switch should not be selected for light theme
            switch_instance.select.assert_not_called()


class TestURLSection:
    """Test URL input section building"""
    
    def test_build_url_section(self, ui_manager):
        """Test URL section building"""
        on_paste = Mock()
        on_analyze = Mock()
        
        with patch('ui_manager.SectionFrame') as mock_section_frame, \
             patch('ui_manager.StatusBadge') as mock_status_badge, \
             patch('ctk.CTkEntry') as mock_entry, \
             patch('ctk.CTkButton') as mock_button:
            
            # Mock components
            section_instance = Mock()
            section_instance.body.return_value = Mock()
            mock_section_frame.return_value = section_instance
            
            entry_instance = Mock()
            entry_instance.bind = Mock()
            mock_entry.return_value = entry_instance
            
            button_instance = Mock()
            mock_button.return_value = button_instance
            
            badge_instance = Mock()
            mock_status_badge.return_value = badge_instance
            
            # Build URL section
            sec, row = ui_manager.build_url_section(Mock(), on_paste, on_analyze)
            
            # Verify components were created
            assert ui_manager.url_entry == entry_instance
            assert ui_manager.analyze_btn == button_instance
            assert ui_manager.status_badge == badge_instance
            
            # Verify event binding
            entry_instance.bind.assert_called()
    
    def test_get_url(self, ui_manager):
        """Test getting URL from entry field"""
        # Test with no entry field
        assert ui_manager.get_url() == ""
        
        # Test with entry field
        ui_manager.url_entry = Mock()
        ui_manager.url_entry.get.return_value = "  https://example.com  "
        assert ui_manager.get_url() == "https://example.com"
    
    def test_set_url(self, ui_manager):
        """Test setting URL in entry field"""
        # Test with no entry field (should not crash)
        ui_manager.set_url("test")
        
        # Test with entry field
        ui_manager.url_entry = Mock()
        ui_manager.url_entry.delete = Mock()
        ui_manager.url_entry.insert = Mock()
        
        ui_manager.set_url("https://example.com")
        
        ui_manager.url_entry.delete.assert_called_with(0, tk.END)
        ui_manager.url_entry.insert.assert_called_with(0, "https://example.com")


class TestOptionsSection:
    """Test download options section"""
    
    def test_build_options_section(self, ui_manager):
        """Test options section building"""
        on_fmt_change = Mock()
        on_quality_change = Mock()
        
        with patch('ui_manager.SectionFrame') as mock_section_frame, \
             patch('ctk.CTkLabel') as mock_label, \
             patch('ctk.CTkRadioButton') as mock_radio, \
             patch('ctk.CTkOptionMenu') as mock_option_menu:
            
            # Mock components
            section_instance = Mock()
            section_instance.body.return_value = Mock()
            mock_section_frame.return_value = section_instance
            
            label_instance = Mock()
            mock_label.return_value = label_instance
            
            radio_instance = Mock()
            mock_radio.return_value = radio_instance
            
            menu_instance = Mock()
            mock_option_menu.return_value = menu_instance
            
            # Build options section
            opt_sec, body = ui_manager.build_options_section(Mock(), on_fmt_change, on_quality_change)
            
            # Verify components were created
            assert ui_manager.format_var is not None
            assert ui_manager.quality_var is not None
            assert ui_manager.quality_label == label_instance
            assert ui_manager.quality_menu == menu_instance
    
    def test_get_format(self, ui_manager):
        """Test getting selected format"""
        # Test with no format var
        assert ui_manager.get_format() == "mp4"
        
        # Test with format var
        ui_manager.format_var = Mock()
        ui_manager.format_var.get.return_value = "mp3"
        assert ui_manager.get_format() == "mp3"
    
    def test_get_quality(self, ui_manager):
        """Test getting selected quality"""
        # Test with no quality var
        assert ui_manager.get_quality() == "best"
        
        # Test with quality var
        ui_manager.quality_var = Mock()
        ui_manager.quality_var.get.return_value = "1080p"
        assert ui_manager.get_quality() == "1080p"
    
    def test_update_quality_visibility(self, ui_manager):
        """Test quality options visibility"""
        ui_manager.quality_label = Mock()
        ui_manager.quality_menu = Mock()
        
        # Test showing quality options
        ui_manager.update_quality_visibility(True)
        ui_manager.quality_label.pack.assert_called_with(side="left")
        ui_manager.quality_menu.pack.assert_called_with(side="left")
        
        # Test hiding quality options
        ui_manager.update_quality_visibility(False)
        ui_manager.quality_label.pack_forget.assert_called()
        ui_manager.quality_menu.pack_forget.assert_called()


class TestProgressSection:
    """Test progress section functionality"""
    
    def test_build_progress_section(self, ui_manager):
        """Test progress section building"""
        on_pause = Mock()
        on_cancel = Mock()
        
        with patch('ui_manager.SectionFrame') as mock_section_frame, \
             patch('ctk.CTkLabel') as mock_label, \
             patch('ctk.CTkProgressBar') as mock_progress_bar, \
             patch('ctk.CTkFrame') as mock_frame, \
             patch('ctk.CTkButton') as mock_button:
            
            # Mock components
            section_instance = Mock()
            section_instance.body.return_value = Mock()
            mock_section_frame.return_value = section_instance
            
            label_instance = Mock()
            mock_label.return_value = label_instance
            
            progress_instance = Mock()
            progress_instance.set = Mock()
            mock_progress_bar.return_value = progress_instance
            
            button_instance = Mock()
            mock_button.return_value = button_instance
            
            # Build progress section
            prog_sec, body = ui_manager.build_progress_section(Mock(), on_pause, on_cancel)
            
            # Verify components were created
            assert ui_manager.progress_section == section_instance
            assert ui_manager.progress_bar == progress_instance
            assert ui_manager.pause_btn == button_instance
            assert ui_manager.cancel_btn == button_instance
            
            # Verify progress bar was initialized
            progress_instance.set.assert_called_with(0)
    
    def test_update_progress(self, ui_manager):
        """Test progress update"""
        ui_manager.progress_bar = Mock()
        ui_manager.progress_pct = Mock()
        ui_manager.progress_speed = Mock()
        ui_manager.progress_eta = Mock()
        ui_manager.progress_filename = Mock()
        
        progress_data = {
            "progress": 50.5,
            "speed": "1.0MiB/s",
            "eta": "01:23",
            "filename": "test_video.mp4"
        }
        
        ui_manager.update_progress(progress_data)
        
        # Verify progress bar was updated
        ui_manager.progress_bar.set.assert_called_with(0.505)
        ui_manager.progress_pct.configure.assert_called_with(text="50.5%")
        ui_manager.progress_speed.configure.assert_called_with(text="Speed: 1.0MiB/s")
        ui_manager.progress_eta.configure.assert_called_with(text="ETA: 01:23")
        ui_manager.progress_filename.configure.assert_called_with(text="test_video.mp4")
    
    def test_update_progress_no_progress_bar(self, ui_manager):
        """Test progress update with no progress bar (should not crash)"""
        ui_manager.progress_bar = None
        
        progress_data = {"progress": 50}
        # Should not raise exception
        ui_manager.update_progress(progress_data)
    
    def test_show_hide_progress(self, ui_manager):
        """Test showing and hiding progress section"""
        ui_manager.progress_section = Mock()
        
        # Test show
        ui_manager.show_progress()
        ui_manager.progress_section.pack.assert_called_with(fill="x", pady=(0, 10))
        
        # Test hide
        ui_manager.hide_progress()
        ui_manager.progress_section.pack_forget.assert_called()


class TestStatusAndButtons:
    """Test status updates and button management"""
    
    def test_update_status(self, ui_manager):
        """Test status badge update"""
        ui_manager.status_badge = Mock()
        
        ui_manager.update_status("success", "Download complete!")
        ui_manager.status_badge.set.assert_called_with("success", "Download complete!")
    
    def test_update_ffmpeg_status(self, ui_manager):
        """Test FFmpeg status update"""
        ui_manager.ffmpeg_label = Mock()
        
        ui_manager.update_ffmpeg_status("Installed")
        ui_manager.ffmpeg_label.configure.assert_called_with(text="FFmpeg: Installed")
    
    def test_set_analyze_button_state(self, ui_manager):
        """Test analyze button state setting"""
        ui_manager.analyze_btn = Mock()
        
        ui_manager.set_analyze_button_state("disabled", "Analyzingâ¦")
        ui_manager.analyze_btn.configure.assert_called_with(state="disabled", text="Analyzingâ¦")
        
        ui_manager.set_analyze_button_state("normal")
        ui_manager.analyze_btn.configure.assert_called_with(state="normal")
    
    def test_set_download_button_state(self, ui_manager):
        """Test download button state setting"""
        ui_manager.download_btn = Mock()
        
        ui_manager.set_download_button_state("disabled", "Downloadingâ¦")
        ui_manager.download_btn.configure.assert_called_with(state="disabled", text="Downloadingâ¦")
        
        ui_manager.set_download_button_state("normal")
        ui_manager.download_btn.configure.assert_called_with(state="normal")
    
    def test_set_pause_button_text(self, ui_manager):
        """Test pause button text setting"""
        ui_manager.pause_btn = Mock()
        
        ui_manager.set_pause_button_text("  Resume")
        ui_manager.pause_btn.configure.assert_called_with(text="  Resume")


class TestInfoSection:
    """Test info section functionality"""
    
    def test_build_info_section(self, ui_manager):
        """Test info section building"""
        with patch('ui_manager.SectionFrame') as mock_section_frame:
            section_instance = Mock()
            section_instance.body.return_value = Mock()
            mock_section_frame.return_value = section_instance
            
            sec, body = ui_manager.build_info_section(Mock())
            
            assert ui_manager.info_section == section_instance
            assert ui_manager.info_body == body
    
    def test_clear_info_section(self, ui_manager):
        """Test clearing info section"""
        ui_manager.info_body = Mock()
        ui_manager.info_body.winfo_children.return_value = [Mock(), Mock(), Mock()]
        
        ui_manager.clear_info_section()
        
        # Verify all children were destroyed
        for child in ui_manager.info_body.winfo_children.return_value:
            child.destroy.assert_called()
    
    def test_show_hide_info_section(self, ui_manager):
        """Test showing and hiding info section"""
        ui_manager.info_section = Mock()
        
        # Test show
        ui_manager.show_info_section()
        ui_manager.info_section.pack.assert_called_with(fill="x", pady=(0, 10))
        
        # Test hide
        ui_manager.hide_info_section()
        ui_manager.info_section.pack_forget.assert_called()


class TestThemeManagement:
    """Test theme management functionality"""
    
    def test_toggle_theme(self, ui_manager):
        """Test theme toggling"""
        ui_manager.theme_switch = Mock()
        
        with patch('ctk.get_appearance_mode', return_value="Dark"), \
             patch('ctk.set_appearance_mode') as mock_set_theme:
            
            ui_manager.toggle_theme()
            mock_set_theme.assert_called_with("Light")
            ui_manager.theme_switch.deselect.assert_called()
        
        with patch('ctk.get_appearance_mode', return_value="Light"), \
             patch('ctk.set_appearance_mode') as mock_set_theme:
            
            ui_manager.toggle_theme()
            mock_set_theme.assert_called_with("Dark")
            ui_manager.theme_switch.select.assert_called()


class TestOutputDirectory:
    """Test output directory functionality"""
    
    def test_update_output_dir_display(self, ui_manager):
        """Test output directory display update"""
        ui_manager.dir_label = Mock()
        
        ui_manager.update_output_dir_display("/custom/path")
        ui_manager.dir_label.configure.assert_called_with(text="/custom/path")


class TestHistorySection:
    """Test history section functionality"""
    
    def test_build_history_section(self, ui_manager):
        """Test history section building"""
        on_open_folder = Mock()
        on_clear_history = Mock()
        output_dir = "/test/output"
        
        with patch('ui_manager.SectionFrame') as mock_section_frame, \
             patch('ctk.CTkScrollableFrame') as mock_scroll_frame, \
             patch('ctk.CTkFrame') as mock_frame, \
             patch('ctk.CTkButton') as mock_button:
            
            # Mock components
            section_instance = Mock()
            section_instance.body.return_value = Mock()
            mock_section_frame.return_value = section_instance
            
            scroll_instance = Mock()
            mock_scroll_frame.return_value = scroll_instance
            
            button_instance = Mock()
            mock_button.return_value = button_instance
            
            # Build history section
            sec, body = ui_manager.build_history_section(Mock(), on_open_folder, on_clear_history, output_dir)
            
            # Verify components were created
            assert ui_manager.history_frame == scroll_instance


class TestUIManagerIntegration:
    """Test UIManager integration scenarios"""
    
    def test_complete_ui_building(self, ui_manager):
        """Test building complete UI"""
        callbacks = {
            'on_update_check': Mock(),
            'on_show_about': Mock(),
            'on_theme_toggle': Mock(),
            'on_paste': Mock(),
            'on_analyze': Mock(),
            'on_fmt_change': Mock(),
            'on_quality_change': Mock(),
            'on_browse': Mock(),
            'on_open_folder': Mock(),
            'on_download': Mock(),
            'on_pause': Mock(),
            'on_cancel': Mock(),
            'on_clear_history': Mock()
        }
        
        # Mock all UI components
        with patch('ui_manager.SectionFrame') as mock_section_frame, \
             patch('ui_manager.StatusBadge') as mock_status_badge, \
             patch('ctk.CTkFrame') as mock_frame, \
             patch('ctk.CTkLabel') as mock_label, \
             patch('ctk.CTkEntry') as mock_entry, \
             patch('ctk.CTkButton') as mock_button, \
             patch('ctk.CTkSwitch') as mock_switch, \
             patch('ctk.CTkRadioButton') as mock_radio, \
             patch('ctk.CTkOptionMenu') as mock_option_menu, \
             patch('ctk.CTkProgressBar') as mock_progress_bar, \
             patch('ctk.CTkScrollableFrame') as mock_scroll_frame:
            
            # Mock all component instances
            for mock_class in [mock_frame, mock_label, mock_entry, mock_button, 
                              mock_switch, mock_radio, mock_option_menu, mock_progress_bar, mock_scroll_frame]:
                instance = Mock()
                instance.pack = Mock()
                instance.pack_forget = Mock()
                instance.configure = Mock()
                instance.bind = Mock()
                instance.get = Mock(return_value="test")
                instance.set = Mock()
                instance.select = Mock()
                instance.deselect = Mock()
                mock_class.return_value = instance
            
            section_instance = Mock()
            section_instance.body.return_value = Mock()
            section_instance.pack = Mock()
            mock_section_frame.return_value = section_instance
            
            badge_instance = Mock()
            badge_instance.set = Mock()
            mock_status_badge.return_value = badge_instance
            
            # Build all sections
            ui_manager.build_header(callbacks['on_update_check'], callbacks['on_show_about'], callbacks['on_theme_toggle'])
            ui_manager.build_url_section(Mock(), callbacks['on_paste'], callbacks['on_analyze'])
            ui_manager.build_info_section(Mock())
            ui_manager.build_options_section(Mock(), callbacks['on_fmt_change'], callbacks['on_quality_change'])
            ui_manager.build_output_section(Mock(), callbacks['on_browse'], callbacks['on_open_folder'], "/test/output")
            ui_manager.build_download_btn(Mock(), callbacks['on_download'])
            ui_manager.build_progress_section(Mock(), callbacks['on_pause'], callbacks['on_cancel'])
            ui_manager.build_history_section(Mock(), callbacks['on_open_folder'], callbacks['on_clear_history'], "/test/output")
            
            # Verify all components were created
            assert ui_manager.theme_switch is not None
            assert ui_manager.url_entry is not None
            assert ui_manager.analyze_btn is not None
            assert ui_manager.status_badge is not None
            assert ui_manager.info_section is not None
            assert ui_manager.format_var is not None
            assert ui_manager.quality_var is not None
            assert ui_manager.download_btn is not None
            assert ui_manager.progress_bar is not None
            assert ui_manager.history_frame is not None
    
    def test_ui_state_transitions(self, ui_manager):
        """Test UI state transitions during download workflow"""
        # Mock components
        ui_manager.status_badge = Mock()
        ui_manager.analyze_btn = Mock()
        ui_manager.download_btn = Mock()
        ui_manager.progress_section = Mock()
        ui_manager.info_section = Mock()
        ui_manager.progress_bar = Mock()
        ui_manager.progress_pct = Mock()
        ui_manager.pause_btn = Mock()
        
        # Initial state
        ui_manager.update_status("idle", "Idle")
        ui_manager.set_analyze_button_state("normal")
        ui_manager.set_download_button_state("disabled")
        
        # Start analysis
        ui_manager.set_analyze_button_state("disabled", "Analyzingâ¦")
        ui_manager.update_status("info", "Analyzingâ¦")
        
        # Analysis complete
        ui_manager.show_info_section()
        ui_manager.set_analyze_button_state("normal")
        ui_manager.update_status("success", "Ready to download")
        ui_manager.set_download_button_state("normal")
        
        # Start download
        ui_manager.set_download_button_state("disabled", "Downloadingâ¦")
        ui_manager.set_analyze_button_state("disabled")
        ui_manager.show_progress()
        ui_manager.update_status("info", "Downloadingâ¦")
        
        # Download progress
        ui_manager.update_progress({"progress": 25, "speed": "1.0MiB/s", "eta": "01:23"})
        
        # Download complete
        ui_manager.set_download_button_state("normal")
        ui_manager.set_analyze_button_state("normal")
        ui_manager.update_status("success", "Download complete!")
        
        # Verify all calls were made
        assert ui_manager.status_badge.set.call_count > 0
        assert ui_manager.analyze_btn.configure.call_count > 0
        assert ui_manager.download_btn.configure.call_count > 0
        assert ui_manager.progress_bar.set.call_count > 0
