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


def _service(client) -> TelegramService:
    service = object.__new__(TelegramService)
    service.client = client
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
