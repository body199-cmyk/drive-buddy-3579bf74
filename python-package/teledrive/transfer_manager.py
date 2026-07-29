"""Orchestrates download → upload → verify with semaphore-bounded concurrency."""
from __future__ import annotations

import asyncio
import mimetypes
import os
from pathlib import Path
from typing import Optional

from . import checkpoint_manager, database as db
from .config import CONFIG
from .duplicate_detector import check as dup_check
from .drive_quota import preflight_or_raise
from .error_handler import classify
from .logging_config import get_logger
from .models import MediaItem
from .progress_tracker import PROGRESS
from .queue_manager import QUEUE
from .retry_policy import should_retry, sleep_for_error
from .storage_manager import cleanup_item, preflight as storage_preflight, temp_path_for
from .utils import sanitize_filename

_log = get_logger("teledrive.transfer")


class TransferManager:
    def __init__(self, telegram, drive, drive_folder_id: str):
        self.telegram = telegram
        self.drive = drive
        self.drive_folder_id = drive_folder_id
        self._sema: Optional[asyncio.Semaphore] = None
        self._paused = asyncio.Event()
        self._paused.set()  # not paused
        self._stop = asyncio.Event()
        self._tasks: list[asyncio.Task] = []
        self._workers: Optional[int] = None
        self._paused_items: set[str] = set()
        self._stopped_items: set[str] = set()

    def _semaphore(self) -> asyncio.Semaphore:
        if self._sema is None:
            self._sema = asyncio.Semaphore(self.worker_count())
        return self._sema

    def worker_count(self) -> int:
        from .config import HARD_CONCURRENCY_CAP
        value = self._workers if self._workers is not None else CONFIG.concurrency_value()
        return max(1, min(int(value), HARD_CONCURRENCY_CAP))

    def set_workers(self, workers: int) -> int:
        """Applies to newly started items; running items are never killed."""
        from .config import HARD_CONCURRENCY_CAP
        self._workers = max(1, min(int(workers), HARD_CONCURRENCY_CAP))
        self._sema = None
        return self._workers

    # ---- per-item control ----

    def pause_item(self, item_id: str) -> None:
        self._paused_items.add(item_id)

    def resume_item(self, item_id: str) -> None:
        self._paused_items.discard(item_id)

    def stop_item(self, item_id: str) -> None:
        self._stopped_items.add(item_id)
        self._paused_items.discard(item_id)

    def item_paused(self, item_id: str) -> bool:
        return item_id in self._paused_items

    def item_stopped(self, item_id: str) -> bool:
        return item_id in self._stopped_items

    async def _wait_item(self, item_id: str) -> bool:
        """Returns False when the item was stopped."""
        while self.item_paused(item_id) and not self._stop.is_set():
            if self.item_stopped(item_id):
                return False
            await asyncio.sleep(0.2)
        return not (self.item_stopped(item_id) or self._stop.is_set())

    def pause(self) -> None:
        self._paused.clear()

    def resume(self) -> None:
        self._paused.set()

    def stop(self) -> None:
        self._stop.set()
        self._paused.set()  # unblock waits

    async def run(self) -> None:
        pending = QUEUE.pending()
        total_bytes = sum(p.size_bytes for p in pending)
        PROGRESS.register_totals(len(pending), total_bytes)
        self._tasks = [asyncio.create_task(self._process(item)) for item in pending]
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _process(self, item: MediaItem) -> None:
        async with self._semaphore():
            if self._stop.is_set() or self.item_stopped(item.id):
                QUEUE.try_transition(item.id, "Stopped")
                return
            await self._paused.wait()
            if not await self._wait_item(item.id):
                QUEUE.try_transition(item.id, "Stopped")
                return
            try:
                await self._do_item(item)
            except Exception as exc:  # last-resort classification
                err = classify(exc)
                item.last_error_code = err.code
                item.last_error_msg = err.raw[:400]
                db.upsert_item(item)
                QUEUE.try_transition(item.id, "Failed", reason=err.code)
                PROGRESS.finish_item(item.id, ok=False)

    async def _do_item(self, item: MediaItem) -> None:
        # Duplicate check
        rep = dup_check(self.drive, item.source_key, item.size_bytes)
        if rep.is_duplicate:
            QUEUE.try_transition(item.id, "Skipped", reason="duplicate", drive_file_id=rep.drive_file_id or "")
            PROGRESS.finish_item(item.id, ok=True, skipped=True)
            return

        # Preflights
        ok_disk, free = storage_preflight(item.size_bytes)
        if not ok_disk:
            QUEUE.try_transition(item.id, "Failed", reason="disk_full",
                                 last_error_code="DISK_FULL",
                                 last_error_msg=f"free={free} need={item.size_bytes}")
            PROGRESS.finish_item(item.id, ok=False)
            return
        try:
            preflight_or_raise(self.drive, item.size_bytes)
        except Exception as e:
            QUEUE.try_transition(item.id, "Failed", reason="drive_quota",
                                 last_error_code="DRIVE_QUOTA", last_error_msg=str(e)[:400])
            PROGRESS.finish_item(item.id, ok=False)
            return

        attempt = 0
        while True:
            attempt += 1
            await self._paused.wait()
            if self._stop.is_set() or not await self._wait_item(item.id):
                QUEUE.try_transition(item.id, "Stopped")
                return
            try:
                await self._run_once(item)
                return
            except Exception as exc:
                err = classify(exc)
                item.last_error_code = err.code
                item.last_error_msg = str(exc)[:400]
                db.upsert_item(item)
                db.add_event(item.id, "error", err.code, {"attempt": attempt, "cat": err.category})
                if not should_retry(err, attempt):
                    to = "Failed" if err.category != "reauth" else "Failed"
                    QUEUE.try_transition(item.id, to, reason=err.code)
                    PROGRESS.finish_item(item.id, ok=False)
                    return
                QUEUE.try_transition(item.id, "NeedsRetry", reason=err.code)
                await sleep_for_error(err, attempt)
                QUEUE.try_transition(item.id, "Pending", reason="retry")

    async def _run_once(self, item: MediaItem) -> None:
        safe = sanitize_filename(item.safe_name or item.original_name or f"{item.id}.{item.extension}")
        temp = temp_path_for(item.id, safe)
        item.temp_path = str(temp)
        db.upsert_item(item)

        # DOWNLOAD
        QUEUE.transition(item.id, "Downloading")
        PROGRESS.start_item(item.id, safe, item.size_bytes, phase="download")

        def dl_cb(current: int, total: int) -> None:
            PROGRESS.update(item.id, current, phase="download")
            it = db.get_item(item.id)
            if it:
                it.download_pct = (current / total * 100) if total else 0.0
                db.upsert_item(it)

        msg = await self.telegram.get_message(item.chat_id, item.message_id)
        actual_path = await self.telegram.download_media(msg, str(temp), progress_cb=dl_cb)
        actual = Path(actual_path)
        if not actual.exists():
            raise RuntimeError("downloaded file missing")
        got = actual.stat().st_size
        if item.size_bytes and got != item.size_bytes:
            # Not fatal for photos (unknown size); tolerate.
            if item.media_type not in ("photo",):
                raise RuntimeError(f"size mismatch download: expected {item.size_bytes}, got {got}")
            item.size_bytes = got

        QUEUE.transition(item.id, "Downloaded")

        # UPLOAD
        QUEUE.transition(item.id, "Uploading")

        def up_cb(current: int, total: int) -> None:
            PROGRESS.update(item.id, current, phase="upload")
            it = db.get_item(item.id)
            if it:
                it.upload_pct = (current / total * 100) if total else 0.0
                db.upsert_item(it)

        mime, _ = mimetypes.guess_type(safe)
        result = self.drive.upload_resumable(
            file_path=str(actual),
            drive_name=safe,
            parent_id=self.drive_folder_id,
            source_key=item.source_key,
            progress_cb=up_cb,
            mime_type=mime,
        )
        file_id = result["id"]

        # VERIFY — Drive must prove id + size + parent + source key + not trashed.
        QUEUE.transition(item.id, "Verifying", drive_file_id=file_id)
        try:
            self._verify(file_id, item)
        except Exception as exc:
            # Do NOT delete temp — mark failed for user review.
            QUEUE.transition(item.id, "Failed",
                             reason="verify_failed",
                             last_error_code="VERIFY_FAILED",
                             last_error_msg=str(exc)[:400])
            db.add_event(item.id, "RECOVERY", "verification failed, temp kept",
                         {"drive_file_id": file_id})
            PROGRESS.finish_item(item.id, ok=False)
            return

        # DURABLE CHECKPOINT before the temp file is allowed to disappear.
        QUEUE.transition(item.id, "UploadedPendingCheckpoint",
                         drive_file_id=file_id,
                         drive_folder_id=self.drive_folder_id)
        try:
            checkpoint_id = checkpoint_manager.persist_durable(self.drive)
        except Exception as exc:
            db.add_event(item.id, "RECOVERY",
                         "durable checkpoint failed, temp kept and state left "
                         "UploadedPendingCheckpoint",
                         {"error": str(exc)[:400], "drive_file_id": file_id})
            _log.warning("durable checkpoint failed for %s: %s", item.id, exc)
            PROGRESS.finish_item(item.id, ok=False)
            return

        QUEUE.transition(item.id, "Uploaded", upload_pct=100.0)
        db.add_event(item.id, "checkpoint", "durable", {"checkpoint_file_id": checkpoint_id})
        cleanup_item(item.id)
        PROGRESS.finish_item(item.id, ok=True)

    def _verify(self, file_id: str, item: MediaItem) -> None:
        from .drive_client import verify_metadata

        verifier = getattr(self.drive, "verify_uploaded", None)
        if callable(verifier):
            verifier(file_id, item.size_bytes, self.drive_folder_id, item.source_key)
            return
        getter = getattr(self.drive, "get_file", None)
        meta = getter(file_id) if callable(getter) else None
        verify_metadata(meta, item.size_bytes, self.drive_folder_id, item.source_key)

