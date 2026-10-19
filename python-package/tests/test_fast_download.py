"""M44-T01 speed path: 512 KiB MTProto requests + honest legacy fallback.

These tests use the real TelegramService method with a fake ``iter_download``
generator. They prove the byte stream, the progress contract, that pause/stop
signals are never swallowed, and that a transport failure falls back to the
legacy ``download_media`` path instead of corrupting a partial file.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from teledrive import database as db
from teledrive.config import DOWNLOAD_REQUEST_SIZE, FAST_DOWNLOAD_MIN_BYTES
from teledrive.errors import TransferPaused
from teledrive.models import MediaItem
from teledrive.queue_manager import QueueManager
from teledrive.telegram_client import TelegramService
from teledrive.transfer_manager import TransferManager


class _FastClient:
    def __init__(self, chunks: list[bytes], fail_after: int | None = None):
        self.chunks = chunks
        self.fail_after = fail_after
        self.kwargs = None

    async def iter_download(self, media, **kwargs):
        self.kwargs = kwargs
        for index, chunk in enumerate(self.chunks):
            if self.fail_after is not None and index >= self.fail_after:
                raise RuntimeError("socket reset")
            yield chunk


def _service(client, slots: int | None = None) -> TelegramService:
    from teledrive.config import TG_INFLIGHT_REQUESTS

    service = object.__new__(TelegramService)
    service.client = client
    service._download_request_slots = asyncio.Semaphore(slots or TG_INFLIGHT_REQUESTS)
    return service


def test_fast_download_requests_the_mtproto_maximum_and_reports_progress(tmp_path):
    client = _FastClient([b"a" * 512, b"b" * 512])
    service = _service(client)
    target = tmp_path / "clip.bin"
    ticks: list[tuple[int, int]] = []

    output = asyncio.run(
        service.download_media_fast(
            SimpleNamespace(media=object()),
            str(target),
            1024,
            lambda current, total: ticks.append((current, total)),
        )
    )

    assert output == str(target)
    assert target.read_bytes() == b"a" * 512 + b"b" * 512
    assert client.kwargs["request_size"] == DOWNLOAD_REQUEST_SIZE
    assert client.kwargs["file_size"] == 1024
    assert ticks == [(512, 1024), (1024, 1024)]


class _RangeStream:
    def __init__(self, data: bytes, *, offset: int, stride: int, request_size: int, limit: int, owner=None, fail_at=None):
        self.data = data
        self.offset = offset
        self.stride = stride
        self.request_size = request_size
        self.limit = limit
        self.owner = owner
        self.fail_at = fail_at
        self.index = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.fail_at is not None and self.index == self.fail_at:
            raise RuntimeError("range stream reset")
        if self.index >= self.limit:
            raise StopAsyncIteration
        start = self.offset + self.index * self.stride
        if start >= len(self.data):
            raise StopAsyncIteration
        if self.owner:
            self.owner.active += 1
            self.owner.max_active = max(self.owner.max_active, self.owner.active)
        try:
            await asyncio.sleep(0.005)
            self.index += 1
            return self.data[start:start + self.request_size]
        finally:
            if self.owner:
                self.owner.active -= 1


class _StripedClient:
    def __init__(self, data: bytes, fail_lane=None):
        self.data = data
        self.fail_lane = fail_lane
        self.calls = []
        self.active = 0
        self.max_active = 0

    def iter_download(self, _media, **kwargs):
        lane = len(self.calls)
        self.calls.append(kwargs)
        return _RangeStream(
            self.data,
            offset=kwargs["offset"],
            stride=kwargs["stride"],
            request_size=kwargs["request_size"],
            limit=kwargs["limit"],
            owner=self,
            fail_at=0 if lane == self.fail_lane else None,
        )


def test_large_fast_download_uses_two_ranges_and_reassembles_ordered_prefix(tmp_path, monkeypatch):
    import teledrive.telegram_client as telegram_module

    request = DOWNLOAD_REQUEST_SIZE
    payload = bytes((i % 251 for i in range(request * 2 + 17)))
    monkeypatch.setattr(telegram_module, "PARALLEL_DOWNLOAD_MIN_BYTES", 1)
    client = _StripedClient(payload)
    target = tmp_path / "large.bin"
    ticks = []

    result = asyncio.run(
        _service(client).download_media_fast(
            SimpleNamespace(media=object()), str(target), len(payload),
            lambda current, total: ticks.append((current, total)),
        )
    )

    expected_streams = min(
        telegram_module.PARALLEL_DOWNLOAD_STREAMS,
        (len(payload) + request - 1) // request,
    )
    assert result == str(target)
    assert target.read_bytes() == payload
    assert len(client.calls) == expected_streams
    assert client.max_active == expected_streams, "the ranges should make requests concurrently"
    assert [call["offset"] for call in client.calls] == [
        lane * request for lane in range(expected_streams)
    ]
    assert all(call["stride"] == request * expected_streams for call in client.calls)
    assert all(call["request_size"] == request for call in client.calls)
    assert ticks[-1] == (len(payload), len(payload))
    assert [current for current, _ in ticks] == sorted(current for current, _ in ticks)


def test_parallel_download_pause_keeps_only_a_valid_contiguous_prefix(tmp_path, monkeypatch):
    import teledrive.telegram_client as telegram_module

    request = DOWNLOAD_REQUEST_SIZE
    payload = bytes((i % 251 for i in range(request * 4)))
    monkeypatch.setattr(telegram_module, "PARALLEL_DOWNLOAD_MIN_BYTES", 1)
    client = _StripedClient(payload)
    target = tmp_path / "paused.bin"

    def pause_after_first_chunk(current, _total):
        if current >= request:
            raise TransferPaused("operator pause")

    with pytest.raises(TransferPaused):
        asyncio.run(
            _service(client).download_media_fast(
                SimpleNamespace(media=object()), str(target), len(payload), pause_after_first_chunk
            )
        )

    partial = target.read_bytes()
    assert partial == payload[:len(partial)]
    assert len(partial) == request


def test_parallel_download_transport_failure_raises_for_clean_legacy_fallback(tmp_path, monkeypatch):
    import teledrive.telegram_client as telegram_module

    request = DOWNLOAD_REQUEST_SIZE
    payload = b"x" * (request * 4)
    monkeypatch.setattr(telegram_module, "PARALLEL_DOWNLOAD_MIN_BYTES", 1)
    client = _StripedClient(payload, fail_lane=1)
    target = tmp_path / "failed.bin"

    with pytest.raises(RuntimeError, match="range stream reset"):
        asyncio.run(
            _service(client).download_media_fast(
                SimpleNamespace(media=object()), str(target), len(payload)
            )
        )

    partial = target.read_bytes()
    assert partial == payload[:len(partial)]


def _item(queue: QueueManager, kind: str = "document", size: int = 2 * 1024 * 1024) -> MediaItem:
    item = MediaItem(
        source_key=f"tg:42:{kind}:{size}",
        chat_id=42,
        message_id=7,
        original_name="clip.bin",
        safe_name="clip.bin",
        media_type=kind,
        extension="bin",
        size_bytes=size,
    )
    queue.enqueue(item)
    return item


class _DownloadingTelegram:
    def __init__(self, *, fast=None, fail_fast: bool = False):
        self.fast_calls: list[str] = []
        self.legacy_calls: list[str] = []
        self.fail_fast = fail_fast
        self._fast = fast

    async def download_media_fast(self, msg, file_path, total_size, progress_cb=None):
        self.fast_calls.append(file_path)
        assert self._fast is not None
        return await self._fast(file_path)

    async def download_media(self, msg, file_path, progress_cb=None):
        self.legacy_calls.append(file_path)
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"legacy")
        if progress_cb:
            progress_cb(len(b"legacy"), len(b"legacy"))
        return str(path)


def _manager(telegram) -> tuple[TransferManager, QueueManager]:
    queue = QueueManager()
    return TransferManager(telegram, None, "folder", queue=queue), queue


def test_transfer_manager_uses_the_fast_path_for_a_sizeable_document(tmp_path):
    async def fast(file_path):
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fast")
        return str(path)

    telegram = _DownloadingTelegram(fast=fast)
    manager, queue = _manager(telegram)
    item = _item(queue)
    temp = tmp_path / "clip.bin.part"

    output = asyncio.run(manager._download(object(), item, temp, None))

    assert output == str(temp)
    assert telegram.fast_calls == [str(temp)]
    assert telegram.legacy_calls == []
    assert temp.read_bytes() == b"fast"


def test_fast_path_failure_falls_back_to_legacy_without_appending(tmp_path):
    async def fast(file_path):
        # Leave a partial file behind, then fail: the legacy path must rewrite
        # from zero instead of appending to these bytes.
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"partial")
        raise RuntimeError("socket reset")

    telegram = _DownloadingTelegram(fast=fast)
    manager, queue = _manager(telegram)
    item = _item(queue)
    temp = tmp_path / "clip.bin.part"

    output = asyncio.run(manager._download(object(), item, temp, None))

    assert output == str(temp)
    assert telegram.fast_calls == [str(temp)]
    assert telegram.legacy_calls == [str(temp)]
    assert temp.read_bytes() == b"legacy"
    recovery = [e for e in db.recent_events(50) if e["kind"] == "RECOVERY"]
    assert recovery, "the fallback must leave a RECOVERY event"


def test_pause_signal_is_never_swallowed_by_the_fallback(tmp_path):
    async def fast(file_path):
        raise TransferPaused("paused")

    telegram = _DownloadingTelegram(fast=fast)
    manager, queue = _manager(telegram)
    item = _item(queue)
    temp = tmp_path / "clip.bin.part"

    with pytest.raises(TransferPaused):
        asyncio.run(manager._download(object(), item, temp, None))

    assert telegram.legacy_calls == []


def test_photos_and_small_documents_keep_the_legacy_path(tmp_path):
    async def fast(file_path):  # pragma: no cover - must not be called
        raise AssertionError("fast path called")

    telegram = _DownloadingTelegram(fast=fast)
    manager, queue = _manager(telegram)

    photo = _item(queue, kind="photo")
    small = _item(queue, kind="document", size=FAST_DOWNLOAD_MIN_BYTES - 1)

    for item in (photo, small):
        temp = tmp_path / f"{item.id}.part"
        asyncio.run(manager._download(object(), item, temp, None))

    assert telegram.fast_calls == []
    assert len(telegram.legacy_calls) == 2


# ---------------------------------------------------------------------------
# M45-T01 — protocol-valid resume, preserved partials, bounded pipeline
# ---------------------------------------------------------------------------

import threading
from types import SimpleNamespace


class _RecordingResumeClient:
    def __init__(self, chunk: bytes = b"tail"):
        self.chunk = chunk
        self.offset = None
        self.request_size = None
        self.file_size = None

    async def iter_download(self, media, offset=0, **kwargs):
        self.offset = offset
        self.request_size = kwargs.get("request_size")
        self.file_size = kwargs.get("file_size")
        yield self.chunk


def test_partial_download_aligns_large_offsets_to_512k(tmp_path):
    """A 4 KiB-aligned offset makes a 512 KiB GetFile cross the 1 MiB window."""
    request = DOWNLOAD_REQUEST_SIZE
    total = request * 3 + 1_000
    client = _RecordingResumeClient()
    service = _service(client)
    path = tmp_path / "partial.bin"
    path.write_bytes(b"x" * (request + 75_000))

    asyncio.run(
        service.download_partial(
            SimpleNamespace(media=object()), str(path), total
        )
    )

    assert client.offset == request, "offset must be 512 KiB aligned for large files"
    assert client.request_size == request
    assert client.file_size == total
    assert path.read_bytes() == b"x" * request + b"tail"


class _ConcurrentSequentialClient:
    def __init__(self):
        self.active = 0
        self.peak = 0

    def iter_download(self, media, **_kwargs):
        async def _gen():
            self.active += 1
            self.peak = max(self.peak, self.active)
            try:
                await asyncio.sleep(0.02)
                yield b"x" * 512
            finally:
                self.active -= 1

        return _gen()


def test_small_file_downloads_share_one_global_inflight_budget(tmp_path):
    client = _ConcurrentSequentialClient()
    service = _service(client, slots=1)

    async def scenario():
        await asyncio.gather(
            service.download_media_fast(
                SimpleNamespace(media=object()), str(tmp_path / "a.bin"), 512
            ),
            service.download_media_fast(
                SimpleNamespace(media=object()), str(tmp_path / "b.bin"), 512
            ),
        )

    asyncio.run(scenario())
    assert client.peak == 1, "the global GetFile budget must cap sequential files too"


def test_fast_failure_keeps_a_resumable_partial_and_skips_legacy(tmp_path):
    request = DOWNLOAD_REQUEST_SIZE

    async def fast(file_path):
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * (request + 7))
        raise RuntimeError("socket reset")

    telegram = _DownloadingTelegram(fast=fast)
    manager, queue = _manager(telegram)
    item = _item(queue, size=8 * 1024 * 1024)
    temp = tmp_path / "clip.bin.part"

    with pytest.raises(RuntimeError, match="socket reset"):
        asyncio.run(manager._download(object(), item, temp, None))

    assert telegram.legacy_calls == [], "the legacy path would truncate the prefix"
    assert temp.stat().st_size == request + 7
    recovery = [e for e in db.recent_events(50) if e["kind"] == "RECOVERY"]
    assert any("partial kept" in str(e.get("message")) for e in recovery)


class _CountingTelegram:
    def __init__(self, delay: float = 0.03):
        self.delay = delay
        self.active = 0
        self.peak = 0

    async def get_message(self, chat, mid):
        return SimpleNamespace(id=mid, media=1_024)

    async def download_media(self, message, file_path, progress_cb=None):
        self.active += 1
        self.peak = max(self.peak, self.active)
        try:
            await asyncio.sleep(self.delay)
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"x" * int(message.media))
            if progress_cb:
                progress_cb(int(message.media), int(message.media))
            return str(path)
        finally:
            self.active -= 1


def _pipeline_item(queue: QueueManager, mid: int, size: int = 1_024) -> MediaItem:
    item = MediaItem(
        source_key=f"tg:99:{mid}",
        chat_id=99,
        message_id=mid,
        original_name=f"clip{mid}.bin",
        safe_name=f"clip{mid}.bin",
        media_type="document",
        extension="bin",
        size_bytes=size,
    )
    queue.enqueue(item)
    return item


def test_worker_count_never_multiplies_telegram_file_downloads():
    from teledrive.config import MAX_CONCURRENT_TG_DOWNLOADS
    from .mocks.fake_drive import FakeDrive

    async def scenario():
        queue = QueueManager()
        for mid in range(500, 520):
            _pipeline_item(queue, mid)
        telegram = _CountingTelegram()
        manager = TransferManager(telegram, FakeDrive(), "folder", queue=queue)
        manager.set_workers(20)
        await manager.run()
        return telegram

    telegram = asyncio.run(scenario())
    assert telegram.peak <= MAX_CONCURRENT_TG_DOWNLOADS
    assert telegram.peak > 1, "the cap must still allow real parallelism"


class _GateDrive:
    """FakeDrive whose first upload waits for the second download to start."""

    def __init__(self):
        from .mocks.fake_drive import FakeDrive

        self._inner = FakeDrive()
        self.download_started = threading.Event()
        self.upload_started = threading.Event()
        self.download_during_upload = None
        self.uploads: list[str] = []

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def upload_resumable(self, file_path, drive_name, parent_id, source_key,
                         progress_cb=None, mime_type=None):
        self.uploads.append(drive_name)
        if len(self.uploads) == 1:
            self.upload_started.set()
            self.download_during_upload = self.download_started.wait(timeout=5)
        return self._inner.upload_resumable(
            file_path, drive_name, parent_id, source_key, progress_cb, mime_type
        )


class _TwoStepTelegram:
    def __init__(self):
        self.downloads = 0
        self.drive = None

    async def get_message(self, chat, mid):
        return SimpleNamespace(id=mid, media=1_024)

    async def download_media(self, message, file_path, progress_cb=None):
        self.downloads += 1
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * 1_024)
        if self.downloads == 2 and self.drive is not None:
            self.drive.download_started.set()
        if progress_cb:
            progress_cb(1_024, 1_024)
        return str(path)


def test_downloads_continue_while_a_drive_upload_is_in_flight():
    """workers=1 + one blocked upload must not freeze the download lane."""
    from teledrive import database as db2

    async def scenario():
        queue = QueueManager()
        first = _pipeline_item(queue, 601)
        second = _pipeline_item(queue, 602)
        drive = _GateDrive()
        telegram = _TwoStepTelegram()
        telegram.drive = drive
        manager = TransferManager(telegram, drive, "folder", queue=queue)
        manager.set_workers(1)
        await manager.run()
        return drive, first, second

    drive, first, second = asyncio.run(scenario())
    assert drive.download_during_upload is True, (
        "the second download must start while the first upload is still running"
    )
    assert len(drive.uploads) == 2
    assert db2.get_item(first.id).state == "Uploaded"
    assert db2.get_item(second.id).state == "Uploaded"


class _NeverTelegram:
    async def download_media(self, *args, **kwargs):  # pragma: no cover
        raise AssertionError("a complete .part must never be re-downloaded")

    async def download_media_fast(self, *args, **kwargs):  # pragma: no cover
        raise AssertionError("a complete .part must never be re-downloaded")

    async def download_partial(self, *args, **kwargs):  # pragma: no cover
        raise AssertionError("a complete .part must never be resumed")


def test_complete_partial_is_reused_without_any_network_download(tmp_path):
    manager, queue = _manager(_NeverTelegram())
    item = _item(queue, size=2 * 1024 * 1024)
    temp = tmp_path / "clip.bin.part"
    temp.write_bytes(b"x" * item.size_bytes)

    output = asyncio.run(manager._download(object(), item, temp, None))

    assert output == str(temp)
    assert temp.stat().st_size == item.size_bytes


# ---------------------------------------------------------------------------
# M45-T01 — virtual media must never become a 0-byte queue row
# ---------------------------------------------------------------------------


class _ScanTelegram:
    def __init__(self, messages):
        self.messages = messages

    async def get_entity(self, chat):
        return SimpleNamespace(id=42, title="chan", username=None)

    async def resolve_entity(self, chat):
        return chat

    async def iter_messages(self, chat, **kwargs):
        for message in self.messages:
            yield message


def test_scan_link_ignores_webpages_and_polls_without_files():
    from teledrive.media_scanner import ScanRequest, scan_link
    from teledrive.telegram_links import ParsedLink

    messages = [
        SimpleNamespace(
            id=1,
            media=SimpleNamespace(webpage=SimpleNamespace(url="https://example.com")),
            document=None,
            photo=None,
            date="",
        ),
        SimpleNamespace(
            id=2,
            media=SimpleNamespace(poll=SimpleNamespace(question="q")),
            document=None,
            photo=None,
            date="",
        ),
        SimpleNamespace(
            id=3,
            media=object(),
            document=SimpleNamespace(id=99, size=4_096, mime_type="video/mp4", attributes=[]),
            photo=None,
            date="",
        ),
    ]
    items = asyncio.run(
        scan_link(
            _ScanTelegram(messages),
            ParsedLink(kind="public", chat="chan"),
            ScanRequest(mode="chat", limit=50),
        )
    )

    assert [item.message_id for item in items] == [3]
    assert items[0].size_bytes == 4_096
    assert items[0].extension == "mp4"


def test_telethon_error_strings_are_classified_instead_of_unknown():
    from teledrive.error_handler import classify

    transient = classify(RuntimeError("Request was unsuccessful 6 time(s)"))
    assert transient.code == "TRANSIENT"
    assert transient.retryable is True

    invalid_limit = classify(
        RuntimeError("An invalid limit was provided (caused by GetFileRequest)")
    )
    assert invalid_limit.code == "PERMANENT"
    assert invalid_limit.retryable is False

    missing = classify(RuntimeError("downloaded file missing"))
    assert missing.code == "PERMANENT"
    assert missing.retryable is False


# ---------------------------------------------------------------------------
# M45-T02 — per-chunk Drive lock for duplicate precheck + SQLite recovery
# ---------------------------------------------------------------------------


def test_duplicate_precheck_succeeds_during_active_upload_and_skips_download():
    """A duplicate item must transition Pending -> Skipped without downloading,
    even while another item is mid-upload on Drive."""
    from .mocks.fake_drive import FakeDrive

    class _ChunkedSlowDrive:
        def __init__(self):
            self._inner = FakeDrive()
            self.first_upload_chunk_released = threading.Event()
            self.second_dup_checked = threading.Event()
            # Pre-seed the second item (mid=702) as already on Drive
            self._inner.files["existing-702"] = {
                "id": "existing-702",
                "name": "clip702.bin",
                "size": "1024",
                "parents": ["folder"],
                "appProperties": {
                    "source_key": "tg:99:702",
                    "teledrive_source_key": "tg:99:702",
                },
                "trashed": False,
            }

        def __getattr__(self, name):
            return getattr(self._inner, name)

        def find_by_source_key(self, source_key):
            res = self._inner.find_by_source_key(source_key)
            if source_key == "tg:99:702":
                self.second_dup_checked.set()
            return res

        def upload_resumable(
            self,
            file_path,
            drive_name,
            parent_id,
            source_key,
            progress_cb=None,
            mime_type=None,
            chunk_lock=None,
        ):
            from contextlib import nullcontext

            lock_ctx = chunk_lock if chunk_lock is not None else nullcontext()
            with lock_ctx:
                if progress_cb:
                    progress_cb(512, 1024)
            # Between chunks: chunk_lock is released so duplicate pre-check can run!
            self.first_upload_chunk_released.set()
            self.second_dup_checked.wait(timeout=3.0)
            with lock_ctx:
                return self._inner.upload_resumable(
                    file_path, drive_name, parent_id, source_key, progress_cb, mime_type
                )

    class _StrictTelegram:
        def __init__(self, drive):
            self.drive = drive
            self.downloaded_mids = []

        async def get_message(self, chat, mid):
            return SimpleNamespace(id=mid, media=1024)

        async def download_media(self, message, file_path, progress_cb=None):
            if message.id == 702:
                raise AssertionError("duplicate item 702 should never be downloaded")
            self.downloaded_mids.append(message.id)
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"x" * 1024)
            if progress_cb:
                progress_cb(1024, 1024)
            return str(path)

    async def scenario():
        queue = QueueManager()
        first = _pipeline_item(queue, 701)
        second = _pipeline_item(queue, 702)
        drive = _ChunkedSlowDrive()
        telegram = _StrictTelegram(drive)
        manager = TransferManager(telegram, drive, "folder", queue=queue)
        manager.set_workers(1)
        await manager.run()
        return telegram, first, second

    telegram, first, second = asyncio.run(scenario())
    assert telegram.downloaded_mids == [701]
    assert db.get_item(first.id).state == "Uploaded"
    assert db.get_item(second.id).state == "Skipped"


def test_database_recovers_from_readonly_sqlite_connection(monkeypatch):
    """If SQLite raises OperationalError('attempt to write a readonly database'),
    cursor() reconnects once and succeeds, and error_handler marks it transient."""
    import sqlite3
    from teledrive.error_handler import classify

    classified = classify(sqlite3.OperationalError("attempt to write a readonly database"))
    assert classified.code == "TRANSIENT"
    assert classified.retryable is True

    calls = {"count": 0}
    real_connect = db._connect

    class _StaleReadonlyConn:
        def cursor(self):
            return self

        def execute(self, sql, params=()):
            calls["count"] += 1
            raise sqlite3.OperationalError("attempt to write a readonly database")

        def close(self):
            pass

    db._conn = _StaleReadonlyConn()  # type: ignore[assignment]
    db.set_setting("recovered_key", "recovered_val")
    assert calls["count"] == 1
    assert db.get_setting("recovered_key") == "recovered_val"


# ---------------------------------------------------------------------------
# M45-T03 — Multi-connection MTProto pool + non-stalling sliding window
# ---------------------------------------------------------------------------


def test_parallel_download_uses_independent_media_clients_and_falls_back_cleanly(tmp_path, monkeypatch):
    """Lanes >= 1 use dedicated media clients from _media_clients, and if a
    secondary client fails mid-stream, that lane seamlessly falls back to
    self.client without failing the download."""
    import teledrive.telegram_client as telegram_module

    request = DOWNLOAD_REQUEST_SIZE
    payload = bytes((i % 251 for i in range(request * 4)))
    monkeypatch.setattr(telegram_module, "PARALLEL_DOWNLOAD_MIN_BYTES", 1)
    monkeypatch.setattr(telegram_module, "PARALLEL_DOWNLOAD_STREAMS", 2)

    primary = _StripedClient(payload)
    # Secondary client fails on its first chunk so fallback to primary is tested!
    secondary_failing = _StripedClient(payload, fail_lane=0)

    service = _service(primary)
    service._media_clients = [secondary_failing]
    target = tmp_path / "pooled.bin"

    result = asyncio.run(
        service.download_media_fast(
            SimpleNamespace(media=object()), str(target), len(payload)
        )
    )

    assert result == str(target)
    assert target.read_bytes() == payload
    assert len(secondary_failing.calls) == 1, "lane 1 tried secondary client first"
    assert len(primary.calls) == 2, "lane 0 used primary and lane 1 fell back to primary"
