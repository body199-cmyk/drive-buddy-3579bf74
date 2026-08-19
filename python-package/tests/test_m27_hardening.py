"""M27-T01 local contract tests for transfer hardening.

These tests use fakes only. They do not claim live Telegram, Drive, or Colab
verification.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace

import pytest

from teledrive import database as db
from teledrive.error_handler import classify
from teledrive.errors import PrivateChannelUnresolvedError
from teledrive.media_scanner import ScanRequest, scan_link
from teledrive.models import MediaItem
from teledrive.queue_manager import QueueManager
from teledrive.telegram_client import TelegramService
from teledrive.telegram_links import ParsedLink, peer_id
from teledrive.transfer_manager import TransferManager


def _item(queue: QueueManager, suffix: str = "one", size: int = 10_000) -> MediaItem:
    item = MediaItem(
        source_key=f"m27:{suffix}",
        chat_id=-1001234567890,
        message_id=7,
        original_name="clip.bin",
        safe_name="clip.bin",
        media_type="document",
        extension="bin",
        size_bytes=size,
    )
    queue.enqueue(item)
    return item


# ---------------------------------------------------------------------------
# Progress persistence
# ---------------------------------------------------------------------------


def test_progress_writes_are_throttled_per_item():
    queue = QueueManager()
    item = _item(queue, "throttle")
    manager = TransferManager(None, None, "folder", queue=queue)

    manager._record_progress(item.id, 100, 1_000, "download")
    first = db.get_item(item.id).download_pct
    manager._record_progress(item.id, 500, 1_000, "download")

    assert db.get_item(item.id).download_pct == first


def test_forced_progress_write_and_reset_are_immediate():
    queue = QueueManager()
    item = _item(queue, "forced")
    manager = TransferManager(None, None, "folder", queue=queue)

    manager._record_progress(item.id, 100, 1_000, "download")
    manager._record_progress(item.id, 1_000, 1_000, "download", force=True)
    assert db.get_item(item.id).download_pct == pytest.approx(100.0)

    manager._reset_progress_throttle(item.id)
    manager._record_progress(item.id, 400, 1_000, "download")
    assert db.get_item(item.id).download_pct == pytest.approx(40.0)


# ---------------------------------------------------------------------------
# Queue engine completion
# ---------------------------------------------------------------------------


def test_engine_crash_is_recorded_and_status_returns_to_idle():
    queue = QueueManager()
    queue._status = "running"
    future: Future = Future()
    future.set_exception(RuntimeError("drain loop exploded"))

    queue._on_run_done(future)

    assert queue.status_label() == "idle"
    messages = [event["message"] for event in db.recent_events(50)]
    assert "transfer run crashed" in messages


def test_clean_engine_finish_records_no_crash_event():
    queue = QueueManager()
    queue._status = "running"
    future: Future = Future()
    future.set_result(None)

    queue._on_run_done(future)

    assert queue.status_label() == "idle"
    messages = [event["message"] for event in db.recent_events(50)]
    assert "transfer run crashed" not in messages


def test_run_reraises_unexpected_worker_exception():
    queue = QueueManager()
    _item(queue, "worker-crash")
    manager = TransferManager(None, None, "folder", queue=queue)

    async def exploding_worker(item):
        raise RuntimeError("worker exploded")

    manager._process = exploding_worker
    with pytest.raises(RuntimeError, match="worker exploded"):
        asyncio.run(manager.run())


# ---------------------------------------------------------------------------
# Private peers
# ---------------------------------------------------------------------------


class _Channel:
    def __init__(self, cid: int = 1_234_567_890):
        self.id = cid
        self.title = "private channel"
        self.broadcast = True
        self.megagroup = False


class _Group:
    def __init__(self, cid: int = 555):
        self.id = cid
        self.title = "legacy group"
        self.participants_count = 3


class _Plain:
    def __init__(self, cid: int = 42):
        self.id = cid
        self.title = "plain double"


def test_peer_id_marks_channels_and_groups_without_changing_plain_doubles():
    assert peer_id(_Channel()) == -1001234567890
    assert peer_id(_Group()) == -555
    assert peer_id(_Plain()) == 42
    assert peer_id(_Plain(-1001234567890)) == -1001234567890


class _Message:
    id = 7
    media = object()
    document = SimpleNamespace(size=10_000, id=55, attributes=[], mime_type="application/octet-stream")
    photo = None
    video = None
    audio = None
    voice = None
    sticker = None
    animation = None
    date = ""


class _ResolvableTelegram:
    def __init__(self):
        self.resolved = []
        self.asked = []

    async def resolve_entity(self, chat):
        self.resolved.append(chat)
        return f"inputpeer:{chat}"

    async def get_entity(self, chat):
        self.asked.append(chat)
        return _Channel()

    async def get_message(self, chat, message_id):
        self.asked.append(chat)
        return _Message()



def test_scan_resolves_peer_uses_it_and_stores_marked_channel_id():
    telegram = _ResolvableTelegram()
    parsed = ParsedLink(kind="private", chat=-1001234567890, message_id=7, raw="x")

    items = asyncio.run(scan_link(telegram, parsed, ScanRequest(mode="message", message_id=7)))

    assert telegram.resolved == [-1001234567890]
    assert telegram.asked == ["inputpeer:-1001234567890", "inputpeer:-1001234567890"]
    assert items[0].chat_id == -1001234567890


def test_unresolved_private_peer_is_permanent_and_not_swallowed():
    error = PrivateChannelUnresolvedError("no access to this Telegram chat")
    classified = classify(error)
    assert error.message_key == "err.private_channel_unresolved"
    assert classified.category == "permanent"
    assert classified.retryable is False

    class _Broken:
        async def resolve_entity(self, chat):
            raise error

    queue = QueueManager()
    item = _item(queue, "broken-peer")
    manager = TransferManager(_Broken(), None, "folder", queue=queue)
    with pytest.raises(PrivateChannelUnresolvedError):
        asyncio.run(manager._chat_ref(item))


def test_chat_ref_keeps_stored_peer_for_legacy_client_without_resolver():
    queue = QueueManager()
    item = _item(queue, "legacy-peer")
    manager = TransferManager(object(), None, "folder", queue=queue)

    assert asyncio.run(manager._chat_ref(item)) == -1001234567890


class _EntityClient:
    def __init__(self, results):
        self.results = list(results)
        self.dialog_reads = 0

    async def get_input_entity(self, chat):
        result = self.results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    async def iter_dialogs(self, limit):
        self.dialog_reads += 1
        yield object()


def _service_with_entity_client(results):
    service = object.__new__(TelegramService)
    service.client = _EntityClient(results)
    service._entity_cache_warmed = False
    return service


def test_resolve_entity_warms_cache_for_a_value_error_then_returns_peer():
    service = _service_with_entity_client([ValueError("cache miss"), "input-peer"])

    assert asyncio.run(service.resolve_entity(-1001234567890)) == "input-peer"
    assert service.client.dialog_reads == 1


def test_resolve_entity_propagates_transport_error_without_labeling_it_permanent():
    service = _service_with_entity_client([ConnectionError("network unavailable")])

    with pytest.raises(ConnectionError, match="network unavailable"):
        asyncio.run(service.resolve_entity(-1001234567890))
    assert service.client.dialog_reads == 0


def test_resolve_entity_warms_once_when_peer_remains_unresolved():
    service = _service_with_entity_client(
        [
            ValueError("miss one"),
            ValueError("miss two"),
            ValueError("miss three"),
            ValueError("miss four"),
        ]
    )

    with pytest.raises(PrivateChannelUnresolvedError):
        asyncio.run(service.resolve_entity(-1001234567890))
    with pytest.raises(PrivateChannelUnresolvedError):
        asyncio.run(service.resolve_entity(-1001234567890))
    assert service.client.dialog_reads == 1


# ---------------------------------------------------------------------------
# Download offset resume
# ---------------------------------------------------------------------------


class _ResumableTelegram:
    def __init__(self):
        self.partial_calls = []
        self.full_calls = []

    async def download_partial(self, msg, file_path, total_size, progress_cb=None):
        self.partial_calls.append((file_path, total_size))
        return file_path

    async def download_media(self, msg, file_path, progress_cb=None):
        self.full_calls.append(file_path)
        return file_path


def test_existing_partial_selects_offset_resume_without_deleting_file(tmp_path):
    queue = QueueManager()
    item = _item(queue, "resume", size=10_000)
    telegram = _ResumableTelegram()
    manager = TransferManager(telegram, None, "folder", queue=queue)
    temp = tmp_path / "clip.bin.part"
    temp.write_bytes(b"x" * 4_096)

    asyncio.run(manager._download(None, item, temp, None))

    assert telegram.partial_calls == [(str(temp), 10_000)]
    assert telegram.full_calls == []
    assert temp.stat().st_size == 4_096


def test_missing_or_photo_partial_uses_existing_full_download_path(tmp_path):
    queue = QueueManager()
    telegram = _ResumableTelegram()
    manager = TransferManager(telegram, None, "folder", queue=queue)

    fresh = _item(queue, "fresh", size=10_000)
    fresh_temp = tmp_path / "fresh.part"
    asyncio.run(manager._download(None, fresh, fresh_temp, None))

    photo = _item(queue, "photo", size=10_000)
    photo.media_type = "photo"
    db.upsert_item(photo)
    photo_temp = tmp_path / "photo.part"
    photo_temp.write_bytes(b"x" * 4_096)
    asyncio.run(manager._download(None, photo, photo_temp, None))

    assert telegram.partial_calls == []
    assert telegram.full_calls == [str(fresh_temp), str(photo_temp)]


def test_oversized_partial_uses_full_download_path_without_deleting_file(tmp_path):
    queue = QueueManager()
    item = _item(queue, "oversized", size=1_000)
    telegram = _ResumableTelegram()
    manager = TransferManager(telegram, None, "folder", queue=queue)
    temp = tmp_path / "oversized.part"
    temp.write_bytes(b"x" * 1_500)

    asyncio.run(manager._download(None, item, temp, None))

    assert telegram.partial_calls == []
    assert telegram.full_calls == [str(temp)]
    assert temp.stat().st_size == 1_500


class _IterDownloadClient:
    def __init__(self):
        self.offset = None

    async def iter_download(self, media, offset):
        self.offset = offset
        yield b"tail"



def test_telegram_service_partial_download_aligns_without_deleting(tmp_path):
    service = object.__new__(TelegramService)
    service.client = _IterDownloadClient()
    path = tmp_path / "partial.bin"
    path.write_bytes(b"x" * 5_000)
    ticks = []

    output = asyncio.run(
        service.download_partial(
            SimpleNamespace(media=object()),
            str(path),
            10_000,
            lambda current, total: ticks.append((current, total)),
        )
    )

    assert output == str(path)
    assert service.client.offset == 4_096
    assert path.read_bytes() == b"x" * 4_096 + b"tail"
    assert ticks == [(4_100, 10_000)]
