"""
MediaGrab Desktop - Download Orchestrator Tests
Tests for download workflow coordination and task management
"""

import pytest
import threading
import time
import uuid
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from download_orchestrator import DownloadOrchestrator


@pytest.fixture
def mock_parent():
    """Create a mock parent widget"""
    parent = Mock()
    parent.after = Mock()
    parent.after_idle = Mock()
    return parent


@pytest.fixture
def mock_ui_manager():
    """Create a mock UI manager"""
    ui_manager = Mock()
    ui_manager.get_url = Mock(return_value="https://example.com/video")
    ui_manager.get_format = Mock(return_value="mp4")
    ui_manager.get_quality = Mock(return_value="720p")
    ui_manager.update_status = Mock()
    ui_manager.set_analyze_button_state = Mock()
    ui_manager.set_download_button_state = Mock()
    ui_manager.hide_info_section = Mock()
    ui_manager.show_info_section = Mock()
    ui_manager.show_progress = Mock()
    ui_manager.clear_info_section = Mock()
    ui_manager.update_progress = Mock()
    ui_manager.pause_btn = Mock()
    ui_manager.pause_btn.cget = Mock(return_value={"text": "  Pause"})
    ui_manager.set_pause_button_text = Mock()
    return ui_manager


@pytest.fixture
def mock_config_manager():
    """Create a mock config manager"""
    config_manager = Mock()
    config_manager.get_output_dir = Mock(return_value="/test/output")
    return config_manager


@pytest.fixture
def download_orchestrator(mock_parent, mock_ui_manager, mock_config_manager):
    """Create DownloadOrchestrator instance for testing"""
    return DownloadOrchestrator(mock_parent, mock_ui_manager, mock_config_manager)


class TestDownloadOrchestratorInitialization:
    """Test DownloadOrchestrator initialization"""
    
    def test_orchestrator_creation(self, download_orchestrator):
        """Test orchestrator creation with default values"""
        assert download_orchestrator.parent is not None
        assert download_orchestrator.ui_manager is not None
        assert download_orchestrator.config_manager is not None
        assert download_orchestrator.current_task_id is None
        assert download_orchestrator.current_result is None
        assert download_orchestrator.selected_videos == {}
        assert download_orchestrator.playlist_check_vars == []
        assert download_orchestrator.download_manager is None


class TestURLAnalysis:
    """Test URL analysis functionality"""
    
    def test_start_analysis_valid_url(self, download_orchestrator):
        """Test starting analysis with valid URL"""
        download_orchestrator.ui_manager.get_url.return_value = "https://www.youtube.com/watch?v=test"
        
        with patch('threading.Thread') as mock_thread:
            download_orchestrator.start_analysis("https://www.youtube.com/watch?v=test")
            
            # Verify UI was updated
            download_orchestrator.ui_manager.set_analyze_button_state.assert_called_with("disabled", "Analyzingâ¦")
            download_orchestrator.ui_manager.update_status.assert_called_with("info", "Analyzingâ¦")
            download_orchestrator.ui_manager.hide_info_section.assert_called()
            
            # Verify thread was started
            mock_thread.assert_called_once()
    
    def test_start_analysis_empty_url(self, download_orchestrator):
        """Test starting analysis with empty URL"""
        download_orchestrator.start_analysis("")
        
        # Verify error status
        download_orchestrator.ui_manager.update_status.assert_called_with("error", "Please enter a URL")
    
    def test_analyze_thread_success(self, download_orchestrator):
        """Test successful analysis thread"""
        mock_result = {
            "title": "Test Video",
            "platform": "youtube",
            "type": "video"
        }
        
        with patch('download_orchestrator.analyze_url', return_value=mock_result):
            download_orchestrator._analyze_thread("https://example.com/video")
            
            # Verify parent.after was called for success callback
            download_orchestrator.parent.after.assert_called()
    
    def test_analyze_thread_error(self, download_orchestrator):
        """Test analysis thread with error"""
        with patch('download_orchestrator.analyze_url', side_effect=Exception("Network error")):
            download_orchestrator._analyze_thread("https://example.com/video")
            
            # Verify parent.after was called for error callback
            download_orchestrator.parent.after.assert_called()
    
    def test_on_analysis_success(self, download_orchestrator):
        """Test successful analysis callback"""
        mock_result = {
            "title": "Test Video",
            "platform": "youtube",
            "type": "video",
            "duration": 120,
            "uploader": "Test Channel"
        }
        
        with patch.object(download_orchestrator, '_render_media_info') as mock_render, \
             patch.object(download_orchestrator, '_update_download_button_label') as mock_update:
            
            download_orchestrator._on_analysis_success(mock_result)
            
            # Verify state was updated
            assert download_orchestrator.current_result == mock_result
            download_orchestrator.ui_manager.set_analyze_button_state.assert_called_with("normal", "Analyze")
            download_orchestrator.ui_manager.update_status.assert_called_with("success", "Ready to download")
            mock_render.assert_called_with(mock_result)
            mock_update.assert_called()
    
    def test_on_analysis_error(self, download_orchestrator):
        """Test analysis error callback"""
        download_orchestrator._on_analysis_error("Network connection failed")
        
        # Verify error handling
        download_orchestrator.ui_manager.set_analyze_button_state.assert_called_with("normal", "Analyze")
        download_orchestrator.ui_manager.update_status.assert_called()
    
    def test_classify_error(self, download_orchestrator):
        """Test error message classification"""
        test_cases = [
            ("Unsupported URL format", "Unsupported URL format"),
            ("Video not available or private", "Video not available or private"),
            ("Network connection error", "Network connection error"),
            ("Video blocked in your region", "Video blocked in your region"),
            ("Age-restricted content", "Age-restricted content"),
            ("FFmpeg not installed", "FFmpeg not installed or outdated"),
            ("Unknown error occurred", "Unable to analyze this URL")
        ]
        
        for input_error, expected_output in test_cases:
            result = download_orchestrator._classify_error(input_error)
            assert result == expected_output


class TestMediaInfoRendering:
    """Test media information rendering"""
    
    def test_render_single_video_info(self, download_orchestrator):
        """Test rendering single video information"""
        mock_result = {
            "title": "Test Video",
            "uploader": "Test Channel",
            "duration": "2:30",
            "platform": "youtube"
        }
        
        with patch('customtkinter.CTkLabel') as mock_label, \
             patch('customtkinter.CTkFrame') as mock_frame:
            
            label_instance = Mock()
            label_instance.pack = Mock()
            mock_label.return_value = label_instance
            
            frame_instance = Mock()
            frame_instance.pack = Mock()
            mock_frame.return_value = frame_instance
            
            download_orchestrator._render_single_video_info(mock_result)
            
            # Verify UI components were created
            assert mock_label.call_count >= 4  # Title, Channel, Duration, Platform
            assert mock_frame.call_count >= 4
    
    def test_render_playlist_info(self, download_orchestrator):
        """Test rendering playlist information"""
        mock_result = {
            "type": "playlist",
            "title": "Test Playlist",
            "count": 2,
            "platform": "youtube",
            "entries": [
                {"id": "1", "title": "Video 1", "duration_str": "1:30"},
                {"id": "2", "title": "Video 2", "duration_str": "2:00"}
            ]
        }
        
        with patch('customtkinter.CTkLabel') as mock_label, \
             patch('customtkinter.CTkButton') as mock_button, \
             patch('customtkinter.CTkFrame') as mock_frame, \
             patch('customtkinter.CTkCheckBox') as mock_checkbox, \
             patch('customtkinter.CTkScrollableFrame') as mock_scroll:
            
            # Mock components
            for mock_class in [mock_label, mock_button, mock_frame, mock_checkbox]:
                instance = Mock()
                instance.pack = Mock()
                mock_class.return_value = instance
            
            scroll_instance = Mock()
            scroll_instance.pack = Mock()
            mock_scroll.return_value = scroll_instance
            
            download_orchestrator._render_playlist_info(mock_result)
            
            # Verify playlist-specific components
            assert mock_button.call_count >= 2  # Select All, Deselect All
            assert mock_checkbox.call_count == 2  # Two video checkboxes
            assert mock_scroll.call_count == 1  # Scrollable frame
    
    def test_on_playlist_item_toggled(self, download_orchestrator):
        """Test playlist item selection toggle"""
        download_orchestrator.current_result = {"count": 2}
        download_orchestrator.selected_videos = {"1": True, "2": True}
        download_orchestrator.playlist_count_label = Mock()
        
        mock_var = Mock()
        mock_var.get.return_value = False
        
        download_orchestrator._on_playlist_item_toggled("1", mock_var)
        
        # Verify selection was updated
        assert download_orchestrator.selected_videos["1"] is False
        download_orchestrator.playlist_count_label.configure.assert_called()
    
    def test_toggle_all_playlist_items(self, download_orchestrator):
        """Test toggling all playlist items"""
        download_orchestrator.current_result = {"count": 3}
        download_orchestrator.playlist_check_vars = [
            ("1", Mock()),
            ("2", Mock()),
            ("3", Mock())
        ]
        download_orchestrator.playlist_count_label = Mock()
        
        # Test select all
        download_orchestrator._toggle_all_playlist_items(True, download_orchestrator.current_result)
        
        for vid, var in download_orchestrator.playlist_check_vars:
            var.set.assert_called_with(True)
            assert download_orchestrator.selected_videos[vid] is True
        
        # Test deselect all
        download_orchestrator._toggle_all_playlist_items(False, download_orchestrator.current_result)
        
        for vid, var in download_orchestrator.playlist_check_vars:
            var.set.assert_called_with(False)
            assert download_orchestrator.selected_videos[vid] is False


class TestDownloadManagement:
    """Test download management functionality"""
    
    def test_start_download_no_result(self, download_orchestrator):
        """Test starting download without analysis result"""
        download_orchestrator.current_result = None
        
        download_orchestrator.start_download()
        
        # Should not start download without result
        download_orchestrator.ui_manager.update_status.assert_not_called()
    
    def test_start_download_no_url(self, download_orchestrator):
        """Test starting download without URL"""
        download_orchestrator.current_result = {"title": "Test"}
        download_orchestrator.ui_manager.get_url.return_value = ""
        
        download_orchestrator.start_download()
        
        download_orchestrator.ui_manager.update_status.assert_called_with("error", "Please enter a URL")
    
    @patch('download_orchestrator.VideoDownloader')
    @patch('threading.Thread')
    def test_start_download_success(self, mock_thread, mock_video_downloader, download_orchestrator):
        """Test successful download start"""
        download_orchestrator.current_result = {"title": "Test Video"}
        download_orchestrator.ui_manager.get_url.return_value = "https://example.com/video"
        
        with patch.object(download_orchestrator, '_check_ffmpeg_availability', return_value=True):
            download_orchestrator.start_download()
            
            # Verify UI was updated
            download_orchestrator.ui_manager.set_download_button_state.assert_called_with("disabled", " Downloadingâ¦")
            download_orchestrator.ui_manager.set_analyze_button_state.assert_called_with("disabled")
            download_orchestrator.ui_manager.update_status.assert_called_with("info", "Downloadingâ¦")
            download_orchestrator.ui_manager.show_progress.assert_called()
            
            # Verify task ID was set
            assert download_orchestrator.current_task_id is not None
            
            # Verify download manager was created
            mock_video_downloader.assert_called_once()
            
            # Verify thread was started
            mock_thread.assert_called_once()
    
    def test_check_ffmpeg_available(self, download_orchestrator):
        """Test FFmpeg availability check"""
        with patch('download_orchestrator.ffmpeg_mgr') as mock_ffmpeg_mgr:
            mock_ffmpeg_mgr.is_installed = True
            mock_ffmpeg_mgr.installing = False
            
            result = download_orchestrator._check_ffmpeg_availability()
            assert result is True
        
        with patch('download_orchestrator.ffmpeg_mgr') as mock_ffmpeg_mgr:
            mock_ffmpeg_mgr.is_installed = False
            mock_ffmpeg_mgr.installing = True
            
            result = download_orchestrator._check_ffmpeg_availability()
            assert result is False
            download_orchestrator.ui_manager.update_status.assert_called_with("warning", "Please wait for FFmpeg to finish installing...")
    
    def test_download_thread_success(self, download_orchestrator):
        """Test successful download thread"""
        task_id = str(uuid.uuid4())
        download_orchestrator.download_manager = Mock()
        
        with patch.object(download_orchestrator, '_on_download_complete') as mock_complete:
            download_orchestrator._download_thread(task_id)
            
            # Verify download was started
            download_orchestrator.download_manager.download.assert_called_once()
            # Verify completion callback
            download_orchestrator.parent.after.assert_called()
    
    def test_download_thread_error(self, download_orchestrator):
        """Test download thread with error"""
        task_id = str(uuid.uuid4())
        download_orchestrator.download_manager = Mock()
        download_orchestrator.download_manager.download.side_effect = Exception("Download failed")
        
        with patch.object(download_orchestrator, '_on_download_error') as mock_error:
            download_orchestrator._download_thread(task_id)
            
            # Verify error callback
            download_orchestrator.parent.after.assert_called()
    
    def test_on_download_complete(self, download_orchestrator):
        """Test download completion callback"""
        task_id = str(uuid.uuid4())
        download_orchestrator.current_task_id = task_id
        download_orchestrator.download_manager = Mock()
        download_orchestrator.download_manager.final_output_dir = "/test/output"
        
        download_orchestrator._on_download_complete({"output_dir": "/test/output"}, task_id)
        
        # Verify UI was updated
        download_orchestrator.ui_manager.set_download_button_state.assert_called_with("normal", "  Download")
        download_orchestrator.ui_manager.set_analyze_button_state.assert_called_with("normal")
        download_orchestrator.ui_manager.update_status.assert_called_with("success", "Download complete!")
        
        # Verify state was reset
        assert download_orchestrator.current_task_id is None
        assert download_orchestrator.download_manager is None
    
    def test_on_download_error(self, download_orchestrator):
        """Test download error callback"""
        task_id = str(uuid.uuid4())
        download_orchestrator.current_task_id = task_id
        download_orchestrator.download_manager = Mock()
        
        download_orchestrator._on_download_error("Network error", task_id)
        
        # Verify UI was updated
        download_orchestrator.ui_manager.set_download_button_state.assert_called_with("normal", "  Download")
        download_orchestrator.ui_manager.set_analyze_button_state.assert_called_with("normal")
        download_orchestrator.ui_manager.update_status.assert_called_with("error", "Error: Network error")
        
        # Verify state was reset
        assert download_orchestrator.current_task_id is None
        assert download_orchestrator.download_manager is None


class TestPauseResumeCancel:
    """Test pause, resume, and cancel functionality"""
    
    def test_pause_download_success(self, download_orchestrator):
        """Test successful download pause"""
        task_id = str(uuid.uuid4())
        download_orchestrator.current_task_id = task_id
        download_orchestrator.download_manager = Mock()
        download_orchestrator.download_manager.pause.return_value = True
        
        result = download_orchestrator.pause_download()
        
        assert result is True
        download_orchestrator.download_manager.pause.assert_called_once()
        download_orchestrator.ui_manager.set_pause_button_text.assert_called_with("  Resume")
    
    def test_pause_download_failure(self, download_orchestrator):
        """Test failed download pause"""
        task_id = str(uuid.uuid4())
        download_orchestrator.current_task_id = task_id
        download_orchestrator.download_manager = Mock()
        download_orchestrator.download_manager.pause.return_value = False
        
        result = download_orchestrator.pause_download()
        
        assert result is False
    
    def test_pause_download_no_manager(self, download_orchestrator):
        """Test pause without download manager"""
        result = download_orchestrator.pause_download()
        assert result is False
    
    def test_resume_download_success(self, download_orchestrator):
        """Test successful download resume"""
        task_id = str(uuid.uuid4())
        download_orchestrator.current_task_id = task_id
        download_orchestrator.download_manager = Mock()
        download_orchestrator.download_manager.resume.return_value = True
        
        result = download_orchestrator.resume_download()
        
        assert result is True
        download_orchestrator.download_manager.resume.assert_called_once()
        download_orchestrator.ui_manager.set_pause_button_text.assert_called_with("  Pause")
    
    def test_cancel_download(self, download_orchestrator):
        """Test download cancellation"""
        task_id = str(uuid.uuid4())
        download_orchestrator.current_task_id = task_id
        download_orchestrator.download_manager = Mock()
        
        with patch.object(download_orchestrator, '_on_download_error') as mock_error:
            download_orchestrator.cancel_download()
            
            download_orchestrator.download_manager.cancel.assert_called_once()
            mock_error.assert_called_with("Cancelled", task_id)
    
    def test_toggle_pause_resume_pause(self, download_orchestrator):
        """Test toggle to pause"""
        task_id = str(uuid.uuid4())
        download_orchestrator.current_task_id = task_id
        download_orchestrator.ui_manager.pause_btn.cget.return_value = "  Pause"
        
        with patch.object(download_orchestrator, 'pause_download', return_value=True) as mock_pause:
            download_orchestrator.toggle_pause_resume()
            mock_pause.assert_called_once()
    
    def test_toggle_pause_resume_resume(self, download_orchestrator):
        """Test toggle to resume"""
        task_id = str(uuid.uuid4())
        download_orchestrator.current_task_id = task_id
        download_orchestrator.ui_manager.pause_btn.cget.return_value = "  Resume"
        
        with patch.object(download_orchestrator, 'resume_download', return_value=True) as mock_resume:
            download_orchestrator.toggle_pause_resume()
            mock_resume.assert_called_once()


class TestProgressTracking:
    """Test progress tracking functionality"""
    
    def test_update_progress_valid(self, download_orchestrator):
        """Test progress update with valid data"""
        task_id = str(uuid.uuid4())
        download_orchestrator.current_task_id = task_id
        
        progress_data = {
            "task_id": task_id,
            "progress": 50.5,
            "speed": "1.0MiB/s",
            "eta": "01:23",
            "filename": "test_video.mp4"
        }
        
        with patch('time.monotonic', return_value=1234567890):
            download_orchestrator.update_progress(progress_data)
            
            # Verify progress history was updated
            assert len(download_orchestrator.progress_history) > 0
            # Verify UI update was scheduled
            download_orchestrator.parent.after_idle.assert_called()
    
    def test_update_progress_wrong_task_id(self, download_orchestrator):
        """Test progress update with wrong task ID"""
        task_id = str(uuid.uuid4())
        download_orchestrator.current_task_id = "different_task_id"
        
        progress_data = {
            "task_id": task_id,
            "progress": 50.5
        }
        
        download_orchestrator.update_progress(progress_data)
        
        # Should not update progress for wrong task
        assert len(download_orchestrator.progress_history) == 0
    
    def test_progress_smoothing(self, download_orchestrator):
        """Test progress smoothing algorithm"""
        task_id = str(uuid.uuid4())
        download_orchestrator.current_task_id = task_id
        
        # Add multiple progress updates
        progress_values = [10, 15, 20, 25, 30]
        
        for i, progress in enumerate(progress_values):
            progress_data = {
                "task_id": task_id,
                "progress": progress
            }
            download_orchestrator.update_progress(progress_data)
        
        # Verify history maintains correct size
        assert len(download_orchestrator.progress_history) <= download_orchestrator.progress_history_max_size
    
    def test_progress_pending_flag(self, download_orchestrator):
        """Test progress pending flag prevents duplicate updates"""
        task_id = str(uuid.uuid4())
        download_orchestrator.current_task_id = task_id
        download_orchestrator.progress_pending = True
        
        progress_data = {"task_id": task_id, "progress": 50}
        
        download_orchestrator.update_progress(progress_data)
        
        # Should not schedule update when already pending
        download_orchestrator.parent.after_idle.assert_not_called()


class TestCleanupAndReset:
    """Test cleanup and reset functionality"""
    
    def test_cleanup(self, download_orchestrator):
        """Test orchestrator cleanup"""
        task_id = str(uuid.uuid4())
        download_orchestrator.current_task_id = task_id
        download_orchestrator.current_result = {"title": "Test"}
        download_orchestrator.download_manager = Mock()
        
        download_orchestrator.cleanup()
        
        # Verify state was reset
        assert download_orchestrator.current_task_id is None
        assert download_orchestrator.current_result is None
        assert download_orchestrator.selected_videos == {}
        assert download_orchestrator.playlist_check_vars == []
        assert download_orchestrator.download_manager is None
    
    def test_update_download_button_label_single_video(self, download_orchestrator):
        """Test download button label update for single video"""
        download_orchestrator.current_result = {"type": "video"}
        
        with patch.object(download_orchestrator, '_update_download_button_label') as mock_update:
            download_orchestrator._update_download_button_label()
            
            download_orchestrator.ui_manager.set_download_button_state.assert_called_with("normal", "  Download")
    
    def test_update_download_button_label_playlist(self, download_orchestrator):
        """Test download button label update for playlist"""
        download_orchestrator.current_result = {"type": "playlist", "count": 3}
        download_orchestrator.selected_videos = {"1": True, "2": False, "3": True}
        
        download_orchestrator._update_download_button_label()
        
        # Should show selected count
        download_orchestrator.ui_manager.set_download_button_state.assert_called_with("normal", "  Download Selected (2/3)")


class TestIntegrationScenarios:
    """Test integration scenarios"""
    
    def test_complete_workflow_success(self, download_orchestrator):
        """Test complete successful download workflow"""
        # Mock successful analysis
        mock_result = {
            "title": "Test Video",
            "platform": "youtube",
            "type": "video"
        }
        
        with patch('download_orchestrator.analyze_url', return_value=mock_result), \
             patch('download_orchestrator.VideoDownloader') as mock_downloader, \
             patch('threading.Thread') as mock_thread, \
             patch.object(download_orchestrator, '_check_ffmpeg_availability', return_value=True):
            
            # Start analysis
            download_orchestrator.start_analysis("https://example.com/video")
            
            # Simulate analysis success
            download_orchestrator._on_analysis_success(mock_result)
            
            # Start download
            download_orchestrator.start_download()
            
            # Verify workflow progression
            assert download_orchestrator.current_result == mock_result
            assert download_orchestrator.current_task_id is not None
            mock_downloader.assert_called_once()
    
    def test_complete_workflow_with_error(self, download_orchestrator):
        """Test workflow with analysis error"""
        with patch('download_orchestrator.analyze_url', side_effect=Exception("Network error")):
            download_orchestrator.start_analysis("https://example.com/video")
            
            # Simulate analysis error
            download_orchestrator._on_analysis_error("Network error")
            
            # Verify error handling
            assert download_orchestrator.current_result is None
            download_orchestrator.ui_manager.update_status.assert_called()
    
    def test_playlist_download_workflow(self, download_orchestrator):
        """Test playlist download workflow"""
        mock_playlist = {
            "type": "playlist",
            "title": "Test Playlist",
            "count": 2,
            "entries": [
                {"id": "1", "title": "Video 1", "url": "https://example.com/1"},
                {"id": "2", "title": "Video 2", "url": "https://example.com/2"}
            ]
        }
        
        with patch('download_orchestrator.analyze_url', return_value=mock_playlist), \
             patch.object(download_orchestrator, '_check_ffmpeg_availability', return_value=True), \
             patch('download_orchestrator.VideoDownloader') as mock_downloader:
            
            # Analyze playlist
            download_orchestrator.start_analysis("https://example.com/playlist")
            download_orchestrator._on_analysis_success(mock_playlist)
            
            # Select specific videos
            download_orchestrator.selected_videos = {"1": True, "2": False}
            
            # Start download
            download_orchestrator.start_download()
            
            # Verify playlist handling
            call_args = mock_downloader.call_args
            assert call_args is not None
            # VideoDownloader should be called with playlist_items parameter
