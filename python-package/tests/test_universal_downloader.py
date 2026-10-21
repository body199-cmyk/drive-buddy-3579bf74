from __future__ import annotations

import importlib
import subprocess

import pytest

from teledrive.universal_downloader import UniversalDownloadManager


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


def test_youtube_bot_challenge_retries_with_fallback_player(monkeypatch, tmp_path):
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
                    "Sign in to confirm you're not a bot"
                )
            (download_dir / "sample.mp4").write_bytes(b"video")

    download_dir = tmp_path / "download"
    download_dir.mkdir()
    manager = UniversalDownloadManager(ctx=None)
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
    assert "extractor_args" not in attempts[0]
    assert attempts[0]["sleep_interval_requests"] == 1
    assert attempts[1]["extractor_args"]["youtube"]["player_client"] == [
        "tv",
        "web_safari",
    ]
    assert [path.name for path in files] == ["sample.mp4"]
