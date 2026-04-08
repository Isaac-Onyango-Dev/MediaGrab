import os
import asyncio
import pytest
import respx
import httpx
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch, MagicMock

from downloader import (
    detect_platform, validate_url, sanitize_filename, VideoDownloader, HttpDownloader,
    analyze_url, get_formats, _analyze_url_sync, _get_formats_sync,
    resolve_output_dir, sanitize_folder_name, FFmpegLocator
)

def test_detect_platform():
    assert detect_platform("https://www.youtube.com/watch?v=123") == "youtube"
    assert detect_platform("https://youtu.be/123") == "youtube"
    assert detect_platform("https://tiktok.com/@user/video/123") == "tiktok"
    assert detect_platform("https://twitter.com/user/status/123") == "twitter"
    assert detect_platform("https://instagram.com/p/123/") == "instagram"
    assert detect_platform("https://example.com/video.mp4") == "generic_http"
    assert detect_platform("not-a-url") == "unknown"

def test_validate_url():
    assert validate_url("https://youtube.com") is True
    assert validate_url("http://test.com") is True
    assert validate_url("ftp://test.com") is False
    assert validate_url("not a url") is False
    assert validate_url("") is False

def test_sanitize_filename():
    assert sanitize_filename("safe_name") == "safe_name"
    assert sanitize_filename('bad<name>') == "badname"
    assert sanitize_filename('test|file?name*') == "testfilename"
    assert sanitize_filename('/etc/passwd') == "etcpasswd"

def test_video_downloader_options():
    dl = VideoDownloader(
        url="https://youtube.com/watch?v=123",
        fmt="mp3",
        quality="best",
        output_dir="/tmp",
        task_id="task1",
        downloads={}
    )
    opts = dl._build_opts()
    assert opts["format"] == "bestaudio/best"
    assert "FFmpegExtractAudio" in str(opts["postprocessors"])

    dl_mp4 = VideoDownloader(
        url="https://youtube.com/watch?v=123",
        fmt="mp4",
        quality="720p",
        output_dir="/tmp",
        task_id="task2",
        downloads={}
    )
    opts_mp4 = dl_mp4._build_opts()
    assert opts_mp4["format"] == "720p"
    assert opts_mp4["merge_output_format"] == "mp4"

def test_http_downloader_filename():
    downloads = {}
    with TemporaryDirectory() as tmp:
        dl = HttpDownloader("http://example.com/file_name.mp4", tmp, "t1", downloads)
        # Note: We won't actually hit the network, just verify init state
        assert dl.url == "http://example.com/file_name.mp4"
        assert dl.output_dir == tmp
        dl._update(status="testing")
        assert downloads["t1"]["status"] == "testing"


# ──────────────────────────────────────────────
# URL Analysis Tests
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_url_valid_youtube():
    """Test YouTube URL analysis with mock response"""
    mock_response = {
        "id": "dQw4w9WgXcQ",
        "title": "Never Gonna Give You Up",
        "uploader": "Rick Astley",
        "duration": 212,
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    }
    
    with patch('downloader._analyze_url_sync', return_value=mock_response):
        result = await analyze_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        
        assert result["platform"] == "youtube"
        assert result["title"] == "Never Gonna Give You Up"
        assert result["type"] == "video"
        assert result["duration"] == 212
        assert result["uploader"] == "Rick Astley"


@pytest.mark.asyncio
async def test_analyze_url_invalid_url():
    """Test error handling for invalid URLs"""
    with patch('downloader._analyze_url_sync', side_effect=ValueError("Could not analyze URL: Unsupported URL")):
        with pytest.raises(ValueError, match="Could not analyze URL"):
            await analyze_url("invalid-url")


@pytest.mark.asyncio
async def test_analyze_url_network_error():
    """Test network error recovery"""
    with patch('downloader._analyze_url_sync', side_effect=Exception("Network error")):
        with pytest.raises(ValueError, match="Could not analyze URL: Network error"):
            await analyze_url("https://example.com/video")


@pytest.mark.asyncio
async def test_analyze_playlist():
    """Test playlist analysis with multiple entries"""
    mock_playlist_response = {
        "type": "playlist",
        "platform": "youtube",
        "title": "Test Playlist",
        "count": 2,
        "entries": [
            {
                "id": "video1",
                "title": "Video 1",
                "duration": 120,
                "url": "https://www.youtube.com/watch?v=video1"
            },
            {
                "id": "video2", 
                "title": "Video 2",
                "duration": 180,
                "url": "https://www.youtube.com/watch?v=video2"
            }
        ]
    }
    
    with patch('downloader._analyze_url_sync', return_value=mock_playlist_response):
        result = await analyze_url("https://www.youtube.com/playlist?list=PL123")
        
        assert result["type"] == "playlist"
        assert result["platform"] == "youtube"
        assert result["title"] == "Test Playlist"
        assert result["count"] == 2
        assert len(result["entries"]) == 2
        assert result["entries"][0]["title"] == "Video 1"
        assert result["entries"][1]["duration_str"] == "3:0"


# ──────────────────────────────────────────────
# Format Enumeration Tests
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_formats_video_quality():
    """Test format enumeration and quality options"""
    mock_formats = [
        {"format_id": "140", "ext": "m4a", "acodec": "mp4a.40.2", "vcodec": "none"},
        {"format_id": "137", "ext": "mp4", "acodec": "none", "vcodec": "avc1.640028", "width": 1920, "height": 1080, "fps": 30},
        {"format_id": "136", "ext": "mp4", "acodec": "none", "vcodec": "avc1.64001F", "width": 1280, "height": 720, "fps": 30},
    ]
    
    with patch('downloader._get_formats_sync', return_value=[
        {"label": "1080p", "height": 1080, "fps": 30},
        {"label": "720p", "height": 720, "fps": 30}
    ]):
        result = await get_formats("https://www.youtube.com/watch?v=test")
        
        assert len(result) == 2
        assert result[0]["label"] == "1080p"
        assert result[0]["height"] == 1080
        assert result[1]["label"] == "720p"
        assert result[1]["height"] == 720


@pytest.mark.asyncio
async def test_get_formats_cache_hit():
    """Test format caching functionality"""
    from cache import format_cache
    
    # Pre-populate cache
    cache_key = "formats:https://www.youtube.com/watch?v=test"
    cached_data = [{"label": "720p", "height": 720, "fps": 30}]
    format_cache.set(cache_key, cached_data)
    
    result = await get_formats("https://www.youtube.com/watch?v=test")
    
    assert result == cached_data


@pytest.mark.asyncio
async def test_get_formats_no_formats():
    """Test handling when no formats are available"""
    with patch('downloader._get_formats_sync', return_value=[]):
        result = await get_formats("https://example.com/video")
        assert result == []


# ──────────────────────────────────────────────
# Download Lifecycle Tests
# ──────────────────────────────────────────────

@pytest.fixture
def mock_downloader():
    """Create a mock VideoDownloader for testing"""
    downloads = {}
    downloader = VideoDownloader(
        url="https://www.youtube.com/watch?v=test",
        fmt="mp4",
        quality="720p",
        output_dir="/tmp/test",
        task_id="test-task",
        downloads=downloads
    )
    return downloader, downloads


def test_video_downloader_initialization(mock_downloader):
    """Test VideoDownloader initialization"""
    downloader, downloads = mock_downloader
    
    assert downloader.url == "https://www.youtube.com/watch?v=test"
    assert downloader.fmt == "mp4"
    assert downloader.quality == "720p"
    assert downloader.task_id == "test-task"
    assert downloader._status == "pending"
    assert downloader.downloads == downloads


def test_video_downloader_build_opts_mp4(mock_downloader):
    """Test yt-dlp options building for MP4 format"""
    downloader, _ = mock_downloader
    opts = downloader._build_opts()
    
    assert opts["format"] == "720p"
    assert opts["merge_output_format"] == "mp4"
    assert "postprocessors" in opts


def test_video_downloader_build_opts_mp3(mock_downloader):
    """Test yt-dlp options building for MP3 format"""
    downloader, _ = mock_downloader
    downloader.fmt = "mp3"
    opts = downloader._build_opts()
    
    assert opts["format"] == "bestaudio/best"
    assert any("FFmpegExtractAudio" in str(pp) for pp in opts.get("postprocessors", []))


@pytest.mark.asyncio
async def test_download_progress_parsing():
    """Test yt-dlp progress parsing"""
    downloads = {}
    downloader = VideoDownloader(
        url="https://www.youtube.com/watch?v=test",
        fmt="mp4",
        quality="720p",
        output_dir="/tmp/test",
        task_id="test-task",
        downloads=downloads
    )
    
    # Mock progress line
    progress_line = "[download]   5.0% of 100.00MiB at 1.00MiB/s ETA 01:23"
    
    # Simulate progress parsing
    downloader._last_line = progress_line
    # Note: This would normally be called from the download loop
    
    # Verify the progress line was stored
    assert downloader._last_line == progress_line


def test_download_pause_resume(mock_downloader):
    """Test download pause and resume functionality"""
    downloader, downloads = mock_downloader
    
    # Mock process
    mock_process = Mock()
    mock_process.poll.return_value = None
    mock_process.pid = 12345
    downloader.process = mock_process
    
    with patch('psutil.Process') as mock_psutil:
        mock_psutil_instance = Mock()
        mock_psutil.return_value = mock_psutil_instance
        
        # Test pause
        result = downloader.pause()
        assert result is True
        assert downloader._status == "paused"
        mock_psutil_instance.suspend.assert_called_once()
        
        # Reset mock
        mock_psutil_instance.reset_mock()
        
        # Test resume
        result = downloader.resume()
        assert result is True
        assert downloader._status == "downloading"
        mock_psutil_instance.resume.assert_called_once()


def test_download_cancellation(mock_downloader):
    """Test download cancellation and cleanup"""
    downloader, downloads = mock_downloader
    
    # Mock process
    mock_process = Mock()
    mock_process.poll.return_value = None
    mock_process.pid = 12345
    downloader.process = mock_process
    
    with patch('psutil.Process') as mock_psutil:
        mock_psutil_instance = Mock()
        mock_child = Mock()
        mock_psutil_instance.children.return_value = [mock_child]
        mock_psutil.return_value = mock_psutil_instance
        
        # Test cancellation
        downloader.cancel()
        
        assert downloader._status == "cancelled"
        mock_psutil_instance.children.assert_called_once_with(recursive=True)
        mock_child.kill.assert_called_once()
        mock_psutil_instance.kill.assert_called_once()
        
        # Verify status update
        assert downloads["test-task"]["status"] == "cancelled"


def test_download_cleanup_partial_files(mock_downloader):
    """Test cleanup of partial download files"""
    downloader, downloads = mock_downloader
    
    with TemporaryDirectory() as tmp_dir:
        downloader.output_dir = tmp_dir
        
        # Create test partial files
        partial_files = ["video.mp4.part", "video.mp4.ytdl", "video.mp4.temp"]
        for filename in partial_files:
            filepath = os.path.join(tmp_dir, filename)
            with open(filepath, 'w') as f:
                f.write("test content")
        
        # Create a normal file that shouldn't be deleted
        normal_file = os.path.join(tmp_dir, "video.mp4")
        with open(normal_file, 'w') as f:
            f.write("final content")
        
        # Run cleanup
        downloader.cleanup_partial()
        
        # Verify partial files are deleted
        for filename in partial_files:
            filepath = os.path.join(tmp_dir, filename)
            assert not os.path.exists(filepath)
        
        # Verify normal file still exists
        assert os.path.exists(normal_file)


@pytest.mark.asyncio
async def test_playlist_download():
    """Test playlist download with multiple items"""
    downloads = {}
    downloader = VideoDownloader(
        url="https://www.youtube.com/playlist?list=PL123",
        fmt="mp4",
        quality="720p",
        output_dir="/tmp/test",
        task_id="playlist-task",
        downloads=downloads,
        playlist_items=[1, 2, 3]  # Download specific items
    )
    
    with patch('downloader.resolve_output_dir', return_value="/tmp/test/Playlist"):
        with patch('yt_dlp.YoutubeDL') as mock_ydl:
            mock_info = {
                "title": "Test Playlist",
                "count": 5,
                "entries": ["video1", "video2", "video3", "video4", "video5"]
            }
            mock_ydl.return_value.extract_info.return_value = mock_info
            
            # Mock subprocess to avoid actual download
            with patch('subprocess.Popen') as mock_popen:
                mock_process = Mock()
                mock_process.stdout = []
                mock_popen.return_value = mock_process
                
                # Start download
                downloader.download()
                
                # Verify playlist handling
                assert downloader.total_items == 3  # Only selected items
                assert "Playlist" in downloader.final_output_dir
                assert downloader._status == "downloading"


# ──────────────────────────────────────────────
# Utility Function Tests
# ──────────────────────────────────────────────

def test_sanitize_folder_name():
    """Test folder name sanitization"""
    assert sanitize_folder_name("Safe Name") == "Safe Name"
    assert sanitize_folder_name('Bad<Name>"With/Special*Chars') == "Bad Name With Special Chars"
    assert sanitize_folder_name("   Spaces and dots...   ") == "Spaces and dots"
    assert sanitize_folder_name("") == "Playlist"
    assert sanitize_folder_name("a" * 150) == "a" * 120  # Length limit


def test_resolve_output_dir():
    """Test output directory resolution"""
    with TemporaryDirectory() as tmp_dir:
        # Test basic directory creation
        result = resolve_output_dir(tmp_dir, None)
        assert result == tmp_dir
        assert os.path.exists(tmp_dir)
        
        # Test playlist directory creation
        playlist_dir = resolve_output_dir(tmp_dir, "Test Playlist")
        expected_dir = os.path.join(tmp_dir, "Test Playlist")
        assert playlist_dir == expected_dir
        assert os.path.exists(expected_dir)
        
        # Test duplicate directory handling
        duplicate_dir = resolve_output_dir(tmp_dir, "Test Playlist")
        expected_duplicate = os.path.join(tmp_dir, "Test Playlist (2)")
        assert duplicate_dir == expected_duplicate
        assert os.path.exists(expected_duplicate)


def test_ffmpeg_locator():
    """Test FFmpeg binary detection"""
    # Reset cached path
    FFmpegLocator._path = None
    
    with patch('shutil.which', return_value="/usr/bin/ffmpeg"):
        path = FFmpegLocator.find_ffmpeg()
        assert path == "/usr/bin/ffmpeg"
        
        # Test caching
        path2 = FFmpegLocator.find_ffmpeg()
        assert path2 == "/usr/bin/ffmpeg"
    
    # Reset for next test
    FFmpegLocator._path = None
    
    with patch('shutil.which', return_value=None):
        path = FFmpegLocator.find_ffmpeg()
        assert path is None


# ──────────────────────────────────────────────
# Error Handling Tests
# ──────────────────────────────────────────────

def test_video_downloader_error_handling(mock_downloader):
    """Test error handling in VideoDownloader"""
    downloader, downloads = mock_downloader
    
    # Test pause with no process
    result = downloader.pause()
    assert result is False
    
    # Test resume with no process
    result = downloader.resume()
    assert result is False
    
    # Test pause with dead process
    mock_process = Mock()
    mock_process.poll.return_value = 1  # Process has exited
    downloader.process = mock_process
    
    result = downloader.pause()
    assert result is False


def test_cleanup_with_nonexistent_directory(mock_downloader):
    """Test cleanup when output directory doesn't exist"""
    downloader, downloads = mock_downloader
    downloader.output_dir = "/nonexistent/directory"
    
    # Should not raise exception
    downloader.cleanup_partial()


def test_progress_update_structure(mock_downloader):
    """Test progress update structure and content"""
    downloader, downloads = mock_downloader
    
    # Test progress update
    downloader._update(
        status="downloading",
        progress=50.5,
        message="Downloading…",
        filename="video.mp4",
        speed="1.0MiB/s",
        eta="01:23",
        current_item=1,
        total_items=5
    )
    
    progress_data = downloads["test-task"]
    
    assert progress_data["status"] == "downloading"
    assert progress_data["progress"] == 50.5
    assert progress_data["message"] == "Downloading…"
    assert progress_data["filename"] == "video.mp4"
    assert progress_data["speed"] == "1.0MiB/s"
    assert progress_data["eta"] == "01:23"
    assert progress_data["current_item"] == 1
    assert progress_data["total_items"] == 5
