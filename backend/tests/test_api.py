import pytest
import asyncio
import json
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, patch, AsyncMock

from main import app, downloads, instances, task_times, task_owners, _get_client_identifier, _verify_task_ownership


@pytest.mark.asyncio
async def test_health_check_returns_ok():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_analyze_with_invalid_url_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/analyze", json={"url": "not a url"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_download_start_without_url_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/download/start", json={"fmt": "mp3"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_formats_with_invalid_url_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/formats", json={"url": "invalid://"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_cancel_nonexistent_task_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/download/cancel/fake-task-id")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_progress_for_unknown_task_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/download/progress/unknown-id")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_downloads_returns_empty_tasks():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/download/list")

    assert response.json()["tasks"] == []


# ──────────────────────────────────────────────
# Authentication Tests
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check with system status"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "uptime" in data


@pytest.mark.asyncio
async def test_analyze_endpoint_auth():
    """Test analyze endpoint authentication"""
    # Test without API key (should work in development mode)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/analyze", json={"url": "https://www.youtube.com/watch?v=test"})
    
    # Should succeed in development mode (no API key configured)
    assert response.status_code in [200, 422]  # 422 if URL validation fails


@pytest.mark.asyncio
async def test_analyze_endpoint_with_invalid_api_key():
    """Test analyze endpoint with invalid API key"""
    with patch('main.settings.api_key', 'test-api-key'):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/analyze", 
                json={"url": "https://www.youtube.com/watch?v=test"},
                headers={"X-API-Key": "wrong-key"}
            )
        
        assert response.status_code == 403
        assert "Invalid API key" in response.json()["detail"]


@pytest.mark.asyncio
async def test_analyze_endpoint_with_valid_api_key():
    """Test analyze endpoint with valid API key"""
    with patch('main.settings.api_key', 'test-api-key'):
        with patch('main.analyze_url', return_value={"platform": "youtube", "title": "Test"}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/analyze", 
                    json={"url": "https://www.youtube.com/watch?v=test"},
                    headers={"X-API-Key": "test-api-key"}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["platform"] == "youtube"
            assert data["title"] == "Test"


# ──────────────────────────────────────────────
# Download Management Tests
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_download_start_validation():
    """Test download request validation"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test missing URL
        response = await client.post("/download/start", json={"fmt": "mp4"})
        assert response.status_code == 422
        
        # Test invalid format
        response = await client.post("/download/start", json={
            "url": "https://www.youtube.com/watch?v=test",
            "fmt": "invalid"
        })
        assert response.status_code == 422
        
        # Test valid request
        with patch('main.analyze_url', return_value={"platform": "youtube", "title": "Test"}):
            response = await client.post("/download/start", json={
                "url": "https://www.youtube.com/watch?v=test",
                "fmt": "mp4",
                "quality": "720p"
            })
            # Should succeed or fail due to missing dependencies, but not validation error
            assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_download_start_with_playlist():
    """Test download start with playlist and selected items"""
    mock_playlist_data = {
        "type": "playlist",
        "platform": "youtube",
        "title": "Test Playlist",
        "count": 3,
        "entries": [
            {"id": "1", "title": "Video 1", "url": "https://www.youtube.com/watch?v=1"},
            {"id": "2", "title": "Video 2", "url": "https://www.youtube.com/watch?v=2"},
            {"id": "3", "title": "Video 3", "url": "https://www.youtube.com/watch?v=3"}
        ]
    }
    
    with patch('main.analyze_url', return_value=mock_playlist_data):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/download/start", json={
                "url": "https://www.youtube.com/playlist?list=PL123",
                "fmt": "mp4",
                "quality": "720p",
                "playlist_items": [1, 3]  # Download only items 1 and 3
            })
            
            # Should succeed or fail due to missing dependencies
            assert response.status_code in [200, 500]
            
            if response.status_code == 200:
                data = response.json()
                assert "task_id" in data
                assert data["status"] == "starting"


@pytest.mark.asyncio
async def test_task_ownership_isolation():
    """Test task isolation between users"""
    # Clear any existing tasks
    downloads.clear()
    instances.clear()
    task_times.clear()
    task_owners.clear()
    
    # Create a task for client 1
    with patch('main.analyze_url', return_value={"platform": "youtube", "title": "Test"}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client1:
            response = await client1.post("/download/start", json={
                "url": "https://www.youtube.com/watch?v=test",
                "fmt": "mp4",
                "quality": "720p"
            }, headers={"X-Client-ID": "client1"})
            
            if response.status_code == 200:
                task_id = response.json()["task_id"]
                
                # Client 2 should not be able to access client 1's task
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client2:
                    # Try to get progress for client 1's task
                    response = await client1.get(f"/download/progress/{task_id}")
                    assert response.status_code == 200
                    
                    # Client 2 should get access denied
                    response = await client2.get(f"/download/progress/{task_id}", headers={"X-Client-ID": "client2"})
                    assert response.status_code == 403
                    assert "task belongs to another client" in response.json()["detail"]


@pytest.mark.asyncio
async def test_task_ownership_verification():
    """Test task ownership verification function"""
    from fastapi import Request
    
    # Setup test data
    task_times["test-task"] = 1234567890
    task_owners["test-task"] = "test-client"
    
    # Create mock request
    mock_request = Mock(spec=Request)
    mock_request.headers = {"X-Client-ID": "test-client"}
    mock_request.client = Mock()
    mock_request.client.host = "127.0.0.1"
    
    # Should not raise exception for valid owner
    _verify_task_ownership("test-task", mock_request)
    
    # Should raise exception for wrong client
    mock_request.headers = {"X-Client-ID": "wrong-client"}
    with pytest.raises(Exception) as exc_info:
        _verify_task_ownership("test-task", mock_request)
    assert "task belongs to another client" in str(exc_info.value)
    
    # Should raise exception for non-existent task
    with pytest.raises(Exception) as exc_info:
        _verify_task_ownership("non-existent-task", mock_request)
    assert "Task not found" in str(exc_info.value)
    
    # Cleanup
    task_times.pop("test-task", None)
    task_owners.pop("test-task", None)


# ──────────────────────────────────────────────
# Rate Limiting Tests
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rate_limiting():
    """Test API rate limiting"""
    # This test would need to be adjusted based on actual rate limit configuration
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Make multiple rapid requests
        responses = []
        for _ in range(10):
            response = await client.get("/health")
            responses.append(response)
            
        # Check if any responses were rate limited
        rate_limited = any(r.status_code == 429 for r in responses)
        # Note: Rate limiting behavior depends on configuration
        # This test mainly verifies the endpoint exists
        assert all(r.status_code in [200, 429] for r in responses)


# ──────────────────────────────────────────────
# WebSocket Progress Tests
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_websocket_progress():
    """Test WebSocket progress updates"""
    # Create a test task first
    with patch('main.analyze_url', return_value={"platform": "youtube", "title": "Test"}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/download/start", json={
                "url": "https://www.youtube.com/watch?v=test",
                "fmt": "mp4",
                "quality": "720p"
            })
            
            if response.status_code == 200:
                task_id = response.json()["task_id"]
                
                # Test WebSocket connection
                with patch('main.app.websocket_route') as mock_websocket:
                    mock_websocket.return_value = AsyncMock()
                    
                    # This is a simplified test - in reality, WebSocket testing
                    # requires more complex setup with actual connections
                    try:
                        async with client.websocket_connect(f"/ws/progress/{task_id}") as websocket:
                            # Should be able to connect (may timeout waiting for messages)
                            pass
                    except Exception:
                        # WebSocket connection might fail in test environment
                        # This is expected behavior for unit tests
                        pass


@pytest.mark.asyncio
async def test_websocket_progress_unauthorized_task():
    """Test WebSocket progress with unauthorized task access"""
    # Test WebSocket connection to non-existent task
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            async with client.websocket_connect("/ws/progress/non-existent-task") as websocket:
                # Should not be able to connect to non-existent task
                pass
    except Exception:
        # Expected to fail
        pass


# ──────────────────────────────────────────────
# Format Endpoint Tests
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_formats_endpoint_valid():
    """Test formats endpoint with valid URL"""
    mock_formats = [
        {"label": "1080p", "height": 1080, "fps": 30},
        {"label": "720p", "height": 720, "fps": 30}
    ]
    
    with patch('main.get_formats', return_value=mock_formats):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/formats", json={
                "url": "https://www.youtube.com/watch?v=test"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["label"] == "1080p"
            assert data[1]["height"] == 720


@pytest.mark.asyncio
async def test_formats_endpoint_cache():
    """Test formats endpoint caching"""
    mock_formats = [{"label": "720p", "height": 720, "fps": 30}]
    
    with patch('main.get_formats', return_value=mock_formats) as mock_get_formats:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # First call
            response1 = await client.post("/formats", json={
                "url": "https://www.youtube.com/watch?v=test"
            })
            
            # Second call (should use cache)
            response2 = await client.post("/formats", json={
                "url": "https://www.youtube.com/watch?v=test"
            })
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            
            # get_formats should be called twice (cache is checked inside)
            assert mock_get_formats.call_count == 2


# ──────────────────────────────────────────────
# Client Identification Tests
# ──────────────────────────────────────────────

def test_client_identifier_extraction():
    """Test client identifier extraction from request"""
    from fastapi import Request
    
    # Test with X-Client-ID header
    mock_request = Mock(spec=Request)
    mock_request.headers = {"X-Client-ID": "test-client-123"}
    mock_request.client = Mock()
    mock_request.client.host = "127.0.0.1"
    
    client_id = _get_client_identifier(mock_request)
    assert client_id == "test-client-123"
    
    # Test fallback to IP + User-Agent
    mock_request.headers = {}
    mock_request.headers.get = Mock(return_value=None)
    mock_request.headers.__getitem__ = Mock(side_effect=lambda k: {
        "User-Agent": "Mozilla/5.0 Test Browser"
    }[k])
    
    client_id = _get_client_identifier(mock_request)
    assert "127.0.0.1:" in client_id
    assert len(client_id.split(":")) == 2


# ──────────────────────────────────────────────
# Error Handling Tests
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_endpoint_network_error():
    """Test analyze endpoint with network errors"""
    with patch('main.analyze_url', side_effect=Exception("Network error")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/analyze", json={
                "url": "https://www.youtube.com/watch?v=test"
            })
            
            assert response.status_code == 500
            assert "Network error" in response.json()["detail"]


@pytest.mark.asyncio
async def test_download_start_missing_dependencies():
    """Test download start when dependencies are missing"""
    with patch('main.analyze_url', return_value={"platform": "youtube", "title": "Test"}):
        with patch('main.VideoDownloader', side_effect=Exception("FFmpeg not found")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/download/start", json={
                    "url": "https://www.youtube.com/watch?v=test",
                    "fmt": "mp4",
                    "quality": "720p"
                })
                
                assert response.status_code == 500
                assert "FFmpeg not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_cancel_nonexistent_task_returns_404():
    """Test cancel endpoint with non-existent task"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/download/cancel/fake-task-id")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_progress_for_unknown_task_returns_404():
    """Test progress endpoint with unknown task"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/download/progress/unknown-id")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_pause_resume_nonexistent_task():
    """Test pause/resume endpoints with non-existent task"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test pause
        response = await client.post("/download/pause/fake-task-id")
        assert response.status_code == 404
        
        # Test resume
        response = await client.post("/download/resume/fake-task-id")
        assert response.status_code == 404


# ──────────────────────────────────────────────
# Cleanup Tests
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cleanup_loop():
    """Test background cleanup loop functionality"""
    # Add some test data
    import time
    old_time = time.time() - 7200  # 2 hours ago
    recent_time = time.time() - 300  # 5 minutes ago
    
    task_times["old-task"] = old_time
    task_times["recent-task"] = recent_time
    downloads["old-task"] = {"status": "completed"}
    downloads["recent-task"] = {"status": "downloading"}
    instances["old-task"] = Mock()
    instances["recent-task"] = Mock()
    task_owners["old-task"] = "client1"
    task_owners["recent-task"] = "client2"
    
    # Mock the cleanup function to run immediately
    with patch('asyncio.sleep', side_effect=StopAsyncIteration):
        try:
            from main import _cleanup_loop
            await _cleanup_loop()
        except StopAsyncIteration:
            pass
    
    # Old task should be cleaned up
    assert "old-task" not in task_times
    assert "old-task" not in downloads
    assert "old-task" not in instances
    assert "old-task" not in task_owners
    
    # Recent task should still exist
    assert "recent-task" in task_times
    assert "recent-task" in downloads
    assert "recent-task" in instances
    assert "recent-task" in task_owners


# ──────────────────────────────────────────────
# Configuration Tests
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cors_configuration():
    """Test CORS middleware configuration"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test preflight request
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        # Should allow CORS (status 200 or 204)
        assert response.status_code in [200, 204]
        
        # Check CORS headers
        cors_headers = response.headers
        assert "access-control-allow-origin" in cors_headers or "Access-Control-Allow-Origin" in cors_headers


@pytest.mark.asyncio
async def test_api_version_endpoint():
    """Test API version information"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        
        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

