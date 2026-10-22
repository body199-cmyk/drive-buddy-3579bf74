"""Safety fixes from the 2026-10-22 audit (universal downloader only).

1. SSRF guard: user URLs must not target loopback / private / link-local
   (Colab metadata) addresses.
2. Drive transport sharing: universal uploads must serialize every chunk on
   the same lock the Telegram TransferManager uses for the shared service.
"""
from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest

from teledrive import universal_downloader as ud
from teledrive.universal_downloader import (
    UniversalDownloadManager,
    _SharedDriveChunkLock,
    _url_targets_private_network,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8765/api/state",
        "http://localhost/file.zip",
        "http://169.254.169.254/computeMetadata/v1/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://10.0.0.5/a.pdf",
        "http://192.168.1.1/a.zip",
        "http://[::1]/a.zip",
        "http://[::ffff:127.0.0.1]/a.zip",
        "http://0.0.0.0:8765/",
        "http:///nohost",
    ],
)
def test_private_targets_are_detected(url):
    assert _url_targets_private_network(url) is True


def test_public_literal_ip_is_allowed():
    assert _url_targets_private_network("https://8.8.8.8/file.zip") is False


def test_hostname_resolving_to_private_address_is_blocked(monkeypatch):
    monkeypatch.setattr(
        "socket.getaddrinfo",
        lambda host, port: [(None, None, None, "", ("10.1.2.3", 0))],
    )
    assert _url_targets_private_network("https://intranet.example.com/x.zip") is True


def test_unresolvable_hostname_is_left_to_the_downloader(monkeypatch):
    def boom(host, port):
        raise OSError("dns failure")

    monkeypatch.setattr("socket.getaddrinfo", boom)
    assert _url_targets_private_network("https://does-not-resolve.example/x.zip") is False


def test_start_download_refuses_private_url_before_any_task_or_drive_access():
    class _ExplodingCtx:
        def __getattr__(self, name):  # any Drive/context access is a bug here
            raise AssertionError(f"ctx.{name} must not be touched")

    manager = UniversalDownloadManager(_ExplodingCtx())
    result = manager.start_download(url="http://169.254.169.254/latest/meta-data/")
    assert result["ok"] is False
    assert manager.list_tasks() == []


def test_chunk_lock_uses_transfer_manager_drive_lock():
    tm_lock = threading.Lock()
    ctx = SimpleNamespace(transfer_manager=SimpleNamespace(_drive_lock=tm_lock))
    with _SharedDriveChunkLock(ctx):
        assert tm_lock.locked()
    assert not tm_lock.locked()


def test_chunk_lock_falls_back_to_module_lock_without_transfer_manager():
    ctx = SimpleNamespace(transfer_manager=None)
    with _SharedDriveChunkLock(ctx):
        assert ud._FALLBACK_DRIVE_LOCK.locked()
    assert not ud._FALLBACK_DRIVE_LOCK.locked()


def _run_upload_with(drive, tmp_path, monkeypatch, tm_lock):
    payload = tmp_path / "out.bin"
    payload.write_bytes(b"x" * 10)
    ctx = SimpleNamespace(
        drive_client=drive,
        transfer_manager=SimpleNamespace(_drive_lock=tm_lock),
    )
    manager = UniversalDownloadManager(ctx)
    monkeypatch.setattr(manager, "_ensure_packages", lambda: None)
    monkeypatch.setattr(manager, "_download_to_dir", lambda *a, **k: [payload])
    monkeypatch.setattr(ud, "TEMP_DIR", str(tmp_path / "tmp"))
    task_id = "udl-safe0001"
    manager._tasks.append({"id": task_id, "status": "queued"})
    manager._cancel_events[task_id] = threading.Event()
    gate = threading.Event()
    gate.set()
    manager._resume_events[task_id] = gate
    manager._run_task(task_id, "https://example.com/out.bin", "best", "folder-1")
    return manager._tasks[0]


def test_universal_upload_passes_shared_chunk_lock(tmp_path, monkeypatch):
    tm_lock = threading.Lock()
    seen = {}

    class _Drive:
        def upload_resumable(self, **kwargs):
            lock = kwargs.get("chunk_lock")
            seen["has_lock"] = lock is not None
            with lock:
                seen["held_tm_lock"] = tm_lock.locked()
            return {"id": "drive-file-1"}

    task = _run_upload_with(_Drive(), tmp_path, monkeypatch, tm_lock)
    assert task["status"] == "completed"
    assert task["drive_file_id"] == "drive-file-1"
    assert seen == {"has_lock": True, "held_tm_lock": True}


def test_legacy_drive_without_chunk_lock_runs_under_shared_lock(tmp_path, monkeypatch):
    tm_lock = threading.Lock()
    seen = {}

    class _LegacyDrive:
        def upload_resumable(self, file_path, drive_name, parent_id, source_key,
                             progress_cb=None, mime_type=None):
            seen["held_tm_lock"] = tm_lock.locked()
            return {"id": "drive-file-2"}

    task = _run_upload_with(_LegacyDrive(), tmp_path, monkeypatch, tm_lock)
    assert task["status"] == "completed"
    assert seen == {"held_tm_lock": True}
