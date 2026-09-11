"""
MediaGrab backend regression tests.

Every test here pins a bug that shipped in 1.0.0, so they run offline: no
yt-dlp invocation, no network, no mDNS. The FastAPI app is exercised through
TestClient without entering the lifespan context, which keeps Zeroconf out of
the test run.
"""

import os
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR.parent))

import main  # noqa: E402
from downloader import _is_temp_artifact, is_playlist_url  # noqa: E402
from shared.yt_dlp_helper import (  # noqa: E402
    PROGRESS_MARKER,
    build_yt_dlp_command,
    normalize_quality,
    parse_progress_line,
)


@pytest.fixture(autouse=True)
def clean_state():
    main.limiter.enabled = False
    main.downloads.clear()
    main.instances.clear()
    main.task_times.clear()
    main.task_owners.clear()
    yield
    main.downloads.clear()
    main.instances.clear()
    main.task_times.clear()
    main.task_owners.clear()


@pytest.fixture
def client():
    return TestClient(main.app)


class _FakeDownloader:
    """Stands in for VideoDownloader/HttpDownloader; never touches the network."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self._status = "pending"
        self.cancelled = False

    def download(self):
        self._status = "complete"

    def cancel(self):
        self.cancelled = True
        self._status = "cancelled"


@pytest.fixture
def fake_downloaders(monkeypatch):
    created = []

    def factory(**kwargs):
        inst = _FakeDownloader(**kwargs)
        created.append(inst)
        return inst

    monkeypatch.setattr(main, "VideoDownloader", factory)
    monkeypatch.setattr(main, "HttpDownloader", factory)
    return created


# ── health ────────────────────────────────────────────────────────

def test_health_reports_uptime_not_wall_clock(client):
    main.app.state.started_at = time.time() - 5
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert 4 <= body["uptime"] < 60


# ── output directory handling ─────────────────────────────────────

def test_default_output_dir_is_accepted(client, fake_downloaders):
    """The 1.0.0 default was an absolute path its own validator rejected."""
    resp = client.post("/download/start", json={"url": "https://example.com/v"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["task_id"]


def test_output_dir_traversal_is_rejected(client, fake_downloaders):
    resp = client.post(
        "/download/start",
        json={"url": "https://example.com/v", "output_dir": "../../etc"},
    )
    assert resp.status_code == 400


def test_absolute_output_dir_is_rejected(client, fake_downloaders):
    resp = client.post(
        "/download/start",
        json={"url": "https://example.com/v", "output_dir": "/etc"},
    )
    assert resp.status_code == 400


def test_subfolder_output_dir_resolves_under_root(client, fake_downloaders):
    resp = client.post(
        "/download/start",
        json={"url": "https://example.com/v", "output_dir": "Music"},
    )
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]
    root = str(Path(main.get_settings().output_dir).expanduser().resolve())
    assert main.downloads[task_id]["output_dir"].startswith(root)


def test_invalid_url_is_rejected(client):
    resp = client.post("/download/start", json={"url": "ftp://example.com/v"})
    assert resp.status_code == 400


# ── task ownership ────────────────────────────────────────────────

def test_progress_is_private_to_its_owner(client, fake_downloaders):
    task_id = client.post(
        "/download/start",
        json={"url": "https://example.com/v"},
        headers={"X-Client-ID": "phone-a"},
    ).json()["task_id"]

    mine = client.get(f"/download/progress/{task_id}", headers={"X-Client-ID": "phone-a"})
    assert mine.status_code == 200

    theirs = client.get(f"/download/progress/{task_id}", headers={"X-Client-ID": "phone-b"})
    assert theirs.status_code == 403


def test_unknown_task_progress_returns_404(client):
    assert client.get("/download/progress/does-not-exist").status_code == 404


def test_client_identifier_is_stable_across_calls(client, fake_downloaders):
    """A per-process hash() seed used to break ownership after a restart."""
    first = client.post("/download/start", json={"url": "https://example.com/a"})
    second = client.post("/download/start", json={"url": "https://example.com/b"})
    owners = {main.task_owners[first.json()["task_id"]],
              main.task_owners[second.json()["task_id"]]}
    assert len(owners) == 1


# ── cancel / retry ────────────────────────────────────────────────

def test_cancel_marks_task_and_stops_instance(client, fake_downloaders):
    task_id = client.post("/download/start", json={"url": "https://example.com/v"}).json()["task_id"]
    resp = client.post(f"/download/cancel/{task_id}")
    assert resp.status_code == 200
    assert main.downloads[task_id]["status"] == "cancelled"
    assert fake_downloaders[0].cancelled


def test_retry_requires_a_terminal_state(client, fake_downloaders):
    task_id = client.post("/download/start", json={"url": "https://example.com/v"}).json()["task_id"]
    main.downloads[task_id]["status"] = "downloading"
    assert client.post(f"/download/retry/{task_id}").status_code == 400

    main.downloads[task_id]["status"] = "error"
    assert client.post(f"/download/retry/{task_id}").status_code == 200


# ── websocket ─────────────────────────────────────────────────────

def test_websocket_refuses_unknown_task(client):
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/nope") as ws:
            ws.receive_json()


def test_websocket_streams_until_terminal_state(client, fake_downloaders):
    task_id = client.post(
        "/download/start",
        json={"url": "https://example.com/v"},
        headers={"X-Client-ID": "phone-a"},
    ).json()["task_id"]
    main.downloads[task_id]["status"] = "complete"

    with client.websocket_connect(f"/ws/{task_id}?client_id=phone-a") as ws:
        assert ws.receive_json()["status"] == "complete"


# ── cleanup loop ──────────────────────────────────────────────────

def test_cleanup_keeps_running_tasks(client, fake_downloaders):
    running = client.post("/download/start", json={"url": "https://example.com/a"}).json()["task_id"]
    done = client.post("/download/start", json={"url": "https://example.com/b"}).json()["task_id"]

    main.downloads[running]["status"] = "downloading"
    main.downloads[done]["status"] = "complete"
    stale = time.time() - main.TASK_RETENTION_SECONDS - 1
    main.task_times[running] = stale
    main.task_times[done] = stale

    now = time.time()
    expired = [
        tid for tid, ts in main.task_times.items()
        if now - ts > main.TASK_RETENTION_SECONDS
        and main.downloads.get(tid, {}).get("status") in main.TERMINAL_STATES
    ]
    assert expired == [done]


# ── shared yt-dlp helper ──────────────────────────────────────────

@pytest.mark.parametrize("label,expected_fragment", [
    ("best", "bestvideo+bestaudio/best"),
    ("1080p", "height<=1080"),
    ("720", "height<=720"),
])
def test_quality_labels_become_real_selectors(label, expected_fragment):
    assert expected_fragment in normalize_quality(label)


def test_existing_selector_passes_through():
    selector = "bestvideo[height<=480]+bestaudio"
    assert normalize_quality(selector) == selector


def test_progress_template_marker_survives_yt_dlp_prefix_stripping():
    """yt-dlp strips the "download:" prefix, so the marker must be in the body."""
    cmd = build_yt_dlp_command("https://example.com/v", "/tmp", "mp4", "720p")
    template = cmd[cmd.index("--progress-template") + 1]
    body = template.split(":", 1)[1]
    assert PROGRESS_MARKER in body


def test_parse_progress_line():
    line = f"{PROGRESS_MARKER}|500|1000|NA|1.20MiB/s|00:12|downloading"
    parsed = parse_progress_line(line)
    assert parsed["percent"] == 50
    assert parsed["speed"] == "1.20MiB/s"
    assert parsed["eta"] == "00:12"


def test_parse_progress_line_falls_back_to_estimated_total():
    line = f"{PROGRESS_MARKER}|250|NA|1000|NA|NA|downloading"
    parsed = parse_progress_line(line)
    assert parsed["percent"] == 25
    assert parsed["speed"] == ""


def test_parse_progress_line_ignores_other_output():
    assert parse_progress_line("[download] Destination: video.mp4") is None


def test_single_video_download_disables_playlist_expansion():
    cmd = build_yt_dlp_command("https://youtu.be/abc", "/tmp", "mp4", "best")
    assert "--no-playlist" in cmd


def test_playlist_download_enables_playlist_expansion():
    cmd = build_yt_dlp_command(
        "https://youtube.com/playlist?list=X", "/tmp", "mp4", "best",
        is_playlist=True, playlist_items=[1, 2],
    )
    assert "--yes-playlist" in cmd
    assert cmd[cmd.index("--playlist-items") + 1] == "1,2"


# ── downloader helpers ────────────────────────────────────────────

@pytest.mark.parametrize("url,expected", [
    ("https://www.youtube.com/watch?v=abc", False),
    ("https://www.youtube.com/watch?v=abc&list=PL1", True),
    ("https://www.youtube.com/playlist?list=PL1", True),
    ("https://soundcloud.com/artist/sets/mix", True),
    ("https://example.com/my-playlist-of-songs", False),
    ("https://example.com/video.mp4", False),
])
def test_playlist_url_detection(url, expected):
    assert is_playlist_url(url) is expected


@pytest.mark.parametrize("name,is_temp", [
    ("video.mp4.part", True),
    ("video.f137.mp4", True),
    ("video.ytdl", True),
    ("song.flac", False),      # 1.0.0 deleted this: it contains ".f"
    ("my.favourite.mp4", False),
    ("video.mp4", False),
])
def test_temp_artifact_matcher_spares_finished_media(name, is_temp):
    assert _is_temp_artifact(name) is is_temp
