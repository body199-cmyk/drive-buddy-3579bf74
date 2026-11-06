from __future__ import annotations

import importlib
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from teledrive.universal_downloader import (
    UniversalDownloadManager,
    _classify_youtube_failure,
    _youtube_multiaudio_format,
)


def test_ensure_packages_installs_gdown_when_yt_dlp_already_exists(monkeypatch):
    available = {"yt_dlp": True, "gdown": False}
    install_calls = []

    def fake_import(module_name):
        if not available.get(module_name, False):
            raise ImportError(module_name)
        return object()

    def fake_run(args, **kwargs):
        install_calls.append(args)
        available["gdown"] = True
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(importlib, "import_module", fake_import)
    monkeypatch.setattr(subprocess, "run", fake_run)

    UniversalDownloadManager(ctx=None)._ensure_packages()

    assert len(install_calls) == 1
    assert "gdown" in install_calls[0]
    assert "yt-dlp[default]" in install_calls[0]
    assert "--upgrade" in install_calls[0]


def test_ensure_packages_reports_failed_install(monkeypatch):
    available = {"yt_dlp": True, "gdown": False}

    def fake_import(module_name):
        if not available.get(module_name, False):
            raise ImportError(module_name)
        return object()

    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(
            args, 1, stdout="", stderr="network unavailable"
        )

    monkeypatch.setattr(importlib, "import_module", fake_import)
    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="network unavailable"):
        UniversalDownloadManager(ctx=None)._ensure_packages()


def test_ensure_packages_serializes_concurrent_updates(monkeypatch):
    install_calls = []

    def fake_import(module_name):
        return object()

    def fake_run(args, **kwargs):
        install_calls.append(args)
        time.sleep(0.03)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(importlib, "import_module", fake_import)
    monkeypatch.setattr(subprocess, "run", fake_run)
    manager = UniversalDownloadManager(ctx=None)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: manager._ensure_packages(), range(8)))

    assert len(install_calls) == 1
    assert "yt-dlp[default]" in install_calls[0]


def test_work_directory_creation_failure_marks_task_failed(monkeypatch, tmp_path):
    import teledrive.universal_downloader as downloader_module

    blocked_parent = tmp_path / "universal_dl"
    blocked_parent.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(downloader_module, "TEMP_DIR", tmp_path)

    manager = UniversalDownloadManager(ctx=None)
    task_id = "directory-error"
    manager._tasks.append({"id": task_id, "status": "queued", "error": ""})
    manager._cancel_events[task_id] = threading.Event()
    manager._resume_events[task_id] = threading.Event()
    manager._resume_events[task_id].set()

    manager._run_task(task_id, "https://example.com/file.mp4", "best", "folder")

    task = manager.list_tasks()[0]
    assert task["status"] == "failed"
    assert task["error"]  # Error is surfaced; OS-specific errno wording may differ.
    assert task_id not in manager._cancel_events
    assert task_id not in manager._resume_events


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Sign in to confirm you're not a bot", "environment_or_ip_block"),
        ("Sign in to confirm you’re not a bot", "environment_or_ip_block"),
        ("ERROR: HTTP Error 429: Too Many Requests", "rate_limited"),
        ("LOGIN_REQUIRED", "session_required"),
        ("HTTP Error 403: Forbidden", "po_token_or_ip_block"),
    ],
)
def test_youtube_failures_are_classified_by_actionable_cause(message, expected):
    assert _classify_youtube_failure(message) == expected


def test_youtube_cookie_prompt_is_classified_as_session_requirement():
    assert _classify_youtube_failure(
        "Use --cookies-from-browser or --cookies for the authentication"
    ) == "session_required"


@pytest.mark.parametrize(
    "challenge_text",
    [
        "Sign in to confirm you're not a bot",
        "Sign in to confirm you’re not a bot",
    ],
)
def test_youtube_bot_challenge_retries_with_fallback_player(monkeypatch, tmp_path, challenge_text):
    import yt_dlp

    attempts = []

    class FakeYoutubeDL:
        def __init__(self, options):
            attempts.append(dict(options))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def download(self, urls):
            if len(attempts) == 1:
                raise yt_dlp.utils.DownloadError(
                    challenge_text
                )
            (download_dir / "sample.mkv").write_bytes(b"video")

    download_dir = tmp_path / "download"
    download_dir.mkdir()
    manager = UniversalDownloadManager(ctx=None)
    monkeypatch.setattr(manager, "_ensure_youtube_pot_provider", lambda task_id: "http://127.0.0.1:4416")
    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)
    monkeypatch.setattr(manager, "_is_cancelled", lambda task_id: False)
    monkeypatch.setattr(manager, "_update", lambda *args, **kwargs: None)

    files = manager._download_to_dir(
        "test-task",
        "https://www.youtube.com/watch?v=NynTjmmYIlg",
        "best",
        download_dir,
    )

    assert len(attempts) == 2
    assert attempts[0]["extractor_args"]["youtube"]["player_client"] == ["mweb", "web_safari"]
    assert attempts[0]["extractor_args"]["youtubepot-bgutilhttp"]["base_url"] == "http://127.0.0.1:4416"
    assert attempts[0]["audio_multistreams"] is True
    assert attempts[0]["merge_output_format"] == "mkv"
    assert "ba[language^=ar]+ba[language^=en]" in attempts[0]["format"]
    assert attempts[0]["sleep_interval_requests"] == 1
    assert attempts[0]["concurrent_fragment_downloads"] == 8
    assert attempts[1]["concurrent_fragment_downloads"] == 8
    assert attempts[1]["extractor_args"]["youtubepot-bgutilhttp"]["base_url"] == "http://127.0.0.1:4416"
    assert "youtube" not in attempts[1]["extractor_args"]
    assert [path.name for path in files] == ["sample.mkv"]




@pytest.mark.parametrize(
    "challenge_text",
    [
        "Sign in to confirm you're not a bot",
        "Sign in to confirm you’re not a bot",
    ],
)
def test_youtube_challenge_uses_legacy_player_only_after_token_and_default_fail(
    monkeypatch, tmp_path, challenge_text
):
    import yt_dlp

    attempts = []

    download_dir = tmp_path / "download"
    download_dir.mkdir()

    class FakeYoutubeDL:
        def __init__(self, options):
            attempts.append(dict(options))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def download(self, urls):
            if len(attempts) < 3:
                raise yt_dlp.utils.DownloadError(challenge_text)
            (download_dir / "sample.mkv").write_bytes(b"video")

    manager = UniversalDownloadManager(ctx=None)
    monkeypatch.setattr(manager, "_ensure_youtube_pot_provider", lambda task_id: "http://127.0.0.1:4416")
    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)
    monkeypatch.setattr(manager, "_is_cancelled", lambda task_id: False)
    monkeypatch.setattr(manager, "_update", lambda *args, **kwargs: None)

    files = manager._download_to_dir(
        "test-task",
        "https://www.youtube.com/watch?v=video-id",
        "best",
        download_dir,
    )

    assert len(attempts) == 3
    assert attempts[2]["extractor_args"]["youtube"]["player_client"] == ["tv", "web_safari"]
    assert attempts[2]["extractor_args"]["youtubepot-bgutilhttp"]["base_url"] == "http://127.0.0.1:4416"
    assert [path.name for path in files] == ["sample.mkv"]


def test_youtube_rate_limit_stops_without_repeating_player_requests(monkeypatch, tmp_path):
    import yt_dlp

    attempts = []

    class FakeYoutubeDL:
        def __init__(self, options):
            attempts.append(dict(options))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def download(self, urls):
            raise yt_dlp.utils.DownloadError("HTTP Error 429: Too Many Requests")

    manager = UniversalDownloadManager(ctx=None)
    monkeypatch.setattr(manager, "_ensure_youtube_pot_provider", lambda task_id: "http://127.0.0.1:4416")
    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)
    monkeypatch.setattr(manager, "_is_cancelled", lambda task_id: False)
    monkeypatch.setattr(manager, "_update", lambda *args, **kwargs: None)

    with pytest.raises(RuntimeError, match="HTTP 429"):
        manager._download_to_dir(
            "test-task",
            "https://www.youtube.com/watch?v=video-id",
            "best",
            tmp_path,
        )

    assert len(attempts) == 1


def test_youtube_multiaudio_selector_prefers_both_languages_and_falls_back():
    selector = _youtube_multiaudio_format("720p")

    assert "bestvideo[height<=720][ext=mp4]+ba[language^=ar]+ba[language^=en]" in selector
    assert "bestvideo[height<=720][ext=mp4]+ba[language^=ar]/" in selector
    assert "bestvideo[height<=720][ext=mp4]+ba[language^=en]/" in selector
    assert selector.endswith("best[height<=720]")


def test_youtube_multiaudio_selector_uses_original_audio_fallback():
    selector = _youtube_multiaudio_format("best")

    assert "bestvideo+ba[language^=ar]+ba[language^=en]" in selector
    assert "bestvideo+bestaudio" in selector
    assert selector.endswith("best")


@pytest.mark.parametrize(
    ("url", "expected_noplaylist", "expected_playlist"),
    [
        ("https://www.youtube.com/watch?v=video-id&list=PL123", True, False),
        ("https://www.youtube.com/playlist?list=PL123", False, True),
        ("https://www.youtube.com/playlist?list=UU123", False, True),
        ("https://vimeo.com/123456", False, False),
    ],
)
def test_ytdlp_keeps_video_links_single_and_playlist_links_expanded(
    monkeypatch, tmp_path, url, expected_noplaylist, expected_playlist
):
    import yt_dlp

    options_seen = []

    class FakeYoutubeDL:
        def __init__(self, options):
            options_seen.append(dict(options))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def download(self, urls):
            (download_dir / "sample.mp4").write_bytes(b"video")

    download_dir = tmp_path / "download"
    download_dir.mkdir()
    manager = UniversalDownloadManager(ctx=None)
    monkeypatch.setattr(manager, "_ensure_youtube_pot_provider", lambda task_id: None)
    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)
    monkeypatch.setattr(manager, "_is_cancelled", lambda task_id: False)
    monkeypatch.setattr(manager, "_update", lambda *args, **kwargs: None)

    manager._download_to_dir("test-task", url, "best", download_dir)

    assert len(options_seen) == 1
    assert options_seen[0]["noplaylist"] is expected_noplaylist
    assert options_seen[0].get("ignoreerrors", False) is expected_playlist
    assert "%(playlist_index&{} - |)s" in options_seen[0]["outtmpl"]
    assert "%(id)s" in options_seen[0]["outtmpl"]


def test_youtube_playlist_downloads_all_items_in_order_and_reports_position(
    monkeypatch, tmp_path
):
    import yt_dlp

    updates = []

    class FakeYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def download(self, urls):
            assert urls == ["https://www.youtube.com/playlist?list=PL123"]
            hook = self.options["progress_hooks"][0]
            hook({
                "status": "downloading",
                "downloaded_bytes": 100,
                "total_bytes": 1000,
                "speed": 100,
                "info_dict": {
                    "title": "Second video",
                    "playlist_index": 2,
                    "playlist_count": 2,
                },
            })
            # Simulate yt-dlp completing entries in a way that filesystem
            # enumeration does not guarantee to preserve playlist order.
            (tmp_path / "download" / "02 - second-video.mp4").write_bytes(b"second")
            (tmp_path / "download" / "01 - first-video.mp4").write_bytes(b"first")

    download_dir = tmp_path / "download"
    download_dir.mkdir()
    manager = UniversalDownloadManager(ctx=None)
    monkeypatch.setattr(manager, "_ensure_youtube_pot_provider", lambda task_id: None)
    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)
    monkeypatch.setattr(manager, "_is_cancelled", lambda task_id: False)
    monkeypatch.setattr(manager, "_wait_if_paused", lambda task_id: None)
    monkeypatch.setattr(manager, "_update", lambda *args, **kwargs: updates.append(kwargs))

    files = manager._download_to_dir(
        "playlist-task",
        "https://www.youtube.com/playlist?list=PL123",
        "best",
        download_dir,
    )

    assert [path.name for path in files] == [
        "01 - first-video.mp4",
        "02 - second-video.mp4",
    ]
    assert len(files) == 2
    assert updates[0]["status_ar"] == "📃 القائمة: الفيديو 2/2..."
    assert updates[0]["title"].startswith("(2/2) Second video")


def test_youtube_progress_updates_are_throttled_but_finish_is_immediate(monkeypatch, tmp_path):
    import yt_dlp
    import teledrive.universal_downloader as downloader

    clock = [100.0]
    updates = []

    class FakeYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def download(self, urls):
            hook = self.options["progress_hooks"][0]
            payload = {"status": "downloading", "downloaded_bytes": 100, "total_bytes": 1000, "speed": 100}
            hook(payload)
            clock[0] += 0.1
            hook(payload)
            clock[0] += 0.5
            hook(payload)
            hook({"status": "finished"})
            (tmp_path / "sample.mp4").write_bytes(b"video")

    manager = UniversalDownloadManager(ctx=None)
    monkeypatch.setattr(manager, "_ensure_youtube_pot_provider", lambda task_id: None)
    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)
    monkeypatch.setattr(downloader.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(manager, "_is_cancelled", lambda task_id: False)
    monkeypatch.setattr(manager, "_wait_if_paused", lambda task_id: None)
    monkeypatch.setattr(manager, "_update", lambda *args, **kwargs: updates.append(kwargs))

    manager._download_to_dir("test-task", "https://www.youtube.com/watch?v=test", "best", tmp_path)

    download_updates = [u for u in updates if "speed_bps" in u]
    assert len(download_updates) == 2
    assert any(u.get("progress") == 83.0 for u in updates)
