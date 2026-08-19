"""M26-T01 — transfer control: pause, stop and resume really control a run."""
from __future__ import annotations

import asyncio
import threading
from pathlib import Path

import pytest

from teledrive import database as db
from teledrive import storage_manager
from teledrive.drive_client import DriveService
from teledrive.errors import TransferControlSignal, TransferPaused, TransferStopped
from teledrive.models import MediaItem
from teledrive.progress_tracker import ProgressTracker
from teledrive.queue_manager import QueueManager
from teledrive.transfer_manager import TransferManager

from .mocks.fake_drive import FakeDrive
from .mocks.fake_telegram import FakeDoc, FakeMsg, FakeTelegram

SIZE = 2048


def _manager() -> TransferManager:
    """A manager with inert collaborators: no network, no Drive, no loop."""
    return TransferManager(telegram=object(), drive=object(), drive_folder_id="folder")


def _item(queue: QueueManager, mid: int = 7) -> MediaItem:
    item = MediaItem(
        source_key=f"tg:42:{mid}",
        chat_id=42,
        message_id=mid,
        original_name=f"clip{mid}.bin",
        safe_name=f"clip{mid}.bin",
        media_type="document",
        extension="bin",
        size_bytes=SIZE,
    )
    queue.enqueue(item)
    return item


def _telegram(mid: int) -> FakeTelegram:
    return FakeTelegram({mid: FakeMsg(id=mid, document=FakeDoc(id="d", size=SIZE))})


def _temp_exists(item_id: str) -> bool:
    return (storage_manager.temp_root() / item_id).exists()


def test_control_flags_are_thread_safe_events():
    manager = _manager()
    assert isinstance(manager._paused, threading.Event)
    assert isinstance(manager._stop, threading.Event)
    # Polarity is unchanged: set == not paused.
    assert manager._paused.is_set()
    assert not manager.paused()
    assert not manager.stopping()


def test_pause_makes_the_progress_gate_raise():
    manager = _manager()
    manager._raise_if_interrupted("item-1")  # no signal while running
    manager.pause()
    assert manager.paused()
    with pytest.raises(TransferPaused):
        manager._raise_if_interrupted("item-1")


def test_resume_reopens_the_progress_gate():
    manager = _manager()
    manager.pause()
    manager.resume()
    manager._raise_if_interrupted("item-1")


def test_stop_wins_over_pause():
    manager = _manager()
    manager.pause()
    manager.stop()
    with pytest.raises(TransferStopped):
        manager._raise_if_interrupted("item-1")


def test_per_item_pause_and_stop_gate_only_that_item():
    manager = _manager()
    manager.pause_item("a")
    with pytest.raises(TransferPaused):
        manager._raise_if_interrupted("a")
    manager._raise_if_interrupted("b")
    manager.stop_item("a")
    with pytest.raises(TransferStopped):
        manager._raise_if_interrupted("a")


def test_reset_run_flags_clears_a_previous_stop():
    manager = _manager()
    manager.stop()
    manager.pause_item("a")
    manager.stop_item("b")
    manager.reset_run_flags()
    assert not manager.stopping()
    assert not manager.paused()
    assert not manager.item_paused("a")
    assert not manager.item_stopped("b")
    manager._raise_if_interrupted("a")


def test_control_signals_are_not_teledrive_errors():
    """They must never be classified, retried, or localized."""
    from teledrive.errors import TeleDriveError

    assert issubclass(TransferPaused, TransferControlSignal)
    assert issubclass(TransferStopped, TransferControlSignal)
    assert not issubclass(TransferControlSignal, TeleDriveError)


def test_release_item_moves_no_counter():
    tracker = ProgressTracker()
    tracker.register_totals(1, 100)
    tracker.start_item("x", "x.bin", 100, phase="download")
    tracker.update("x", 50, phase="download")
    tracker.release_item("x")
    snap = tracker.snapshot()
    assert snap["active"] == []
    assert snap["done_files"] == 0
    assert snap["failed_files"] == 0
    assert snap["skipped_files"] == 0


class _ChunkStatus:
    def __init__(self, current: int):
        self.resumable_progress = current


class _ChunkRequest:
    def __init__(self):
        self.calls = 0

    def next_chunk(self):
        self.calls += 1
        return _ChunkStatus(1), {"id": "remote-file"}


class _ChunkFiles:
    def __init__(self, request: _ChunkRequest):
        self.request = request

    def create(self, **kwargs):
        return self.request


class _ChunkService:
    def __init__(self):
        self.request = _ChunkRequest()

    def files(self):
        return _ChunkFiles(self.request)


def test_upload_resumable_reraises_a_control_signal(tmp_path):
    """A cosmetic progress error stays swallowed; a control signal escapes."""
    path = tmp_path / "chunk.bin"
    path.write_bytes(b"x")
    drive = DriveService(_ChunkService())

    with pytest.raises(TransferStopped):
        drive.upload_resumable(
            str(path), "chunk.bin", "folder", "source",
            progress_cb=lambda current, total: (_ for _ in ()).throw(TransferStopped()),
        )

    result = drive.upload_resumable(
        str(path), "chunk.bin", "folder", "source",
        progress_cb=lambda current, total: (_ for _ in ()).throw(ValueError("cosmetic")),
    )
    assert result == {"id": "remote-file"}


def test_pausing_a_running_download_parks_the_row_as_paused(monkeypatch):
    from teledrive import transfer_manager as tm

    queue = QueueManager()
    item = _item(queue, mid=11)
    drive = FakeDrive()
    telegram = _telegram(11)
    manager = TransferManager(telegram, drive, "fld_target", queue=queue)
    tracker = ProgressTracker()
    monkeypatch.setattr(tm, "PROGRESS", tracker)
    deleted: list[str] = []
    original_delete = drive.delete_file
    drive.delete_file = lambda file_id: (deleted.append(file_id), original_delete(file_id))[1]

    async def download_then_pause(message, file_path, progress_cb=None):
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * (SIZE // 2))
        assert progress_cb is not None
        progress_cb(SIZE // 2, SIZE)
        manager.pause()
        progress_cb(SIZE, SIZE)
        return str(path)  # pragma: no cover - second callback interrupts

    telegram.download_media = download_then_pause
    asyncio.run(manager.run())

    assert db.get_item(item.id).state == "Paused"
    assert _temp_exists(item.id)
    snap = tracker.snapshot()
    assert snap["failed_files"] == 0
    assert snap["done_files"] == 0
    assert deleted == []
    assert drive.files == {}


def test_stopping_a_running_upload_parks_the_row_as_stopped(monkeypatch):
    from teledrive import transfer_manager as tm

    queue = QueueManager()
    item = _item(queue, mid=12)
    drive = FakeDrive()
    telegram = _telegram(12)
    manager = TransferManager(telegram, drive, "fld_target", queue=queue)
    tracker = ProgressTracker()
    monkeypatch.setattr(tm, "PROGRESS", tracker)
    deleted: list[str] = []
    original_delete = drive.delete_file
    drive.delete_file = lambda file_id: (deleted.append(file_id), original_delete(file_id))[1]

    def upload_then_stop(file_path, drive_name, parent_id, source_key, progress_cb=None, mime_type=None):
        assert progress_cb is not None
        progress_cb(SIZE // 2, SIZE)
        manager.stop()
        progress_cb(SIZE, SIZE)
        raise AssertionError("control signal must interrupt before an upload is recorded")

    drive.upload_resumable = upload_then_stop
    asyncio.run(manager.run())

    assert db.get_item(item.id).state == "Stopped"
    assert _temp_exists(item.id)
    assert tracker.snapshot()["failed_files"] == 0
    assert deleted == []
    assert drive.files == {}
