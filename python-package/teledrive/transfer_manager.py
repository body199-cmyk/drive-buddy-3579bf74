"""Orchestrates download → upload → verify with semaphore-bounded concurrency."""
from __future__ import annotations

import asyncio
import mimetypes
import os
import threading
from pathlib import Path
from typing import Optional

from . import checkpoint_manager, database as db
from .config import CONFIG
from .duplicate_detector import check as dup_check
from .drive_quota import preflight_or_raise
from .error_handler import classify
from .errors import TransferPaused, TransferStopped
from .logging_config import get_logger
from .models import MediaItem
from .progress_tracker import PROGRESS
from .queue_manager import QueueManager
from .retry_policy import should_retry, sleep_for_error
from .storage_manager import cleanup_item, preflight as storage_preflight, temp_path_for
from .utils import sanitize_filename

_log = get_logger("teledrive.transfer")


class TransferManager:
    #: how often the drain loop looks for newly enqueued work
    DRAIN_INTERVAL = 0.05
    #: how often a paused worker re-reads the control flags
    CONTROL_POLL = 0.2

    def __init__(self, telegram, drive, drive_folder_id: str, queue=None,
                 item_ids=None):
        self.telegram = telegram
        self.drive = drive
        self.drive_folder_id = drive_folder_id
        # The queue is INJECTED. There is no module singleton (Phase C).
        self._queue = queue if queue is not None else QueueManager()
        self._scope: Optional[set[str]] = set(item_ids) if item_ids else None
        self._sema: Optional[asyncio.Semaphore] = None
        # M26-T01 / RC-1: pause(), resume() and stop() are called from the
        # Gradio request thread while run() lives on the AsyncRuntime thread.
        # asyncio.Event is NOT thread-safe across loops/threads, so a resume
        # could fail to wake its waiters. threading.Event is, and the polarity
        # is deliberately unchanged (set == NOT paused), so pause()/resume()/
        # stop() bodies and every existing test keep working verbatim.
        self._paused = threading.Event()
        self._paused.set()  # set == not paused
        self._stop = threading.Event()
        self._tasks: list[asyncio.Task] = []
        self._workers: Optional[int] = None
        self._paused_items: set[str] = set()
        self._stopped_items: set[str] = set()

    @property
    def queue(self):
        return self._queue

    def set_scope(self, item_ids) -> set[str]:
        """Restrict this run to the selected items only."""
        self._scope = {str(i) for i in item_ids} if item_ids else None
        return set(self._scope or set())

    def in_scope(self, item_id: str) -> bool:
        return self._scope is None or item_id in self._scope


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

    # ---- control surface (M26-T01) ----

    def paused(self) -> bool:
        """True while the whole engine is paused."""
        return not self._paused.is_set()

    def stopping(self) -> bool:
        return self._stop.is_set()

    def reset_run_flags(self) -> None:
        """Clear the previous run's control state before a new Start.

        ensure_transfer_manager() reuses ONE manager per context (RC-5), so a
        Stop from an earlier batch would otherwise refuse every later Start.
        Per-item marks are cleared too: a Stopped ROW is final and is never
        returned by pending(), so nothing is silently resurrected.
        """
        self._stop.clear()
        self._paused.set()
        self._paused_items.clear()
        self._stopped_items.clear()

    async def _wait_resume(self) -> bool:
        """Block while globally paused. Returns False when the run must stop."""
        while not self._paused.is_set():
            if self._stop.is_set():
                return False
            await asyncio.sleep(self.CONTROL_POLL)
        return not self._stop.is_set()

    def _control_signal(self, item_id: str):
        """The interruption that applies to this item right now, or None.

        Stop wins over Pause: an operator who pressed Stop must never see the
        file resume later.
        """
        if self._stop.is_set() or self.item_stopped(item_id):
            return TransferStopped(item_id)
        if not self._paused.is_set() or self.item_paused(item_id):
            return TransferPaused(item_id)
        return None

    def _raise_if_interrupted(self, item_id: str) -> None:
        """Called from the download/upload progress callbacks (RC-2).

        Aborts the in-flight file at the next chunk boundary. The partial
        .part file stays on local disk and NOTHING on Drive is deleted.
        """
        signal = self._control_signal(item_id)
        if signal is not None:
            raise signal

    def _pause_item_row(self, item: MediaItem) -> None:
        """Park an interrupted item as Paused. Temp kept, Drive untouched."""
        self._queue.try_transition(item.id, "Paused", reason="paused")
        PROGRESS.release_item(item.id)
        db.add_event(item.id, "transfer", "paused mid-file", {"temp_kept": True})

    def _stop_item_row(self, item: MediaItem) -> None:
        """Park an interrupted item as Stopped (final). Drive untouched."""
        self._queue.try_transition(item.id, "Stopped", reason="stopped")
        PROGRESS.release_item(item.id)
        db.add_event(item.id, "transfer", "stopped mid-file", {"temp_kept": True})

    def _claimable(self, seen: set[str]) -> list[MediaItem]:
        return [
            i for i in self._queue.pending()
            if i.id not in seen and self.in_scope(i.id)
        ]

    async def run(self) -> None:
        """Drain the queue: keep picking up newly enqueued work until empty.

        A single snapshot is never taken; items enqueued while the run is in
        flight are picked up on the next drain tick.
        """
        seen: set[str] = set()
        tasks: list[asyncio.Task] = []
        self._tasks = tasks
        total_items = 0
        total_bytes = 0

        while not self._stop.is_set():
            batch = self._claimable(seen)
            if batch:
                for item in batch:
                    seen.add(item.id)
                total_items += len(batch)
                total_bytes += sum(int(i.size_bytes or 0) for i in batch)
                PROGRESS.register_totals(total_items, total_bytes)
                tasks.extend(asyncio.create_task(self._process(i)) for i in batch)

            active = [t for t in tasks if not t.done()]
            if active:
                await asyncio.wait(active, timeout=self.DRAIN_INTERVAL,
                                   return_when=asyncio.FIRST_COMPLETED)
                continue
            if batch:
                continue
            # No work in flight and nothing claimable: one last look for a
            # late enqueue, then the run is finished.
            await asyncio.sleep(self.DRAIN_INTERVAL)
            if not self._claimable(seen):
                break

        if tasks:
            # No task.cancel() here on purpose (RC-3): cancelling mid-chunk
            # would leave rows stuck in Downloading/Uploading with no owner.
            # The cooperative signal ends every worker within one chunk, and
            # gather() then only drains already-finishing work.
            await asyncio.gather(*tasks, return_exceptions=True)


    async def _process(self, item: MediaItem) -> None:
        async with self._semaphore():
            if self._stop.is_set() or self.item_stopped(item.id):
                self._queue.try_transition(item.id, "Stopped")
                return
            # M26-T01: threading.Event has no awaitable wait(); _wait_resume
            # polls it and also honours a Stop pressed while paused.
            if not await self._wait_resume():
                self._queue.try_transition(item.id, "Stopped")
                return
            if not await self._wait_item(item.id):
                self._queue.try_transition(item.id, "Stopped")
                return
            try:
                await self._do_item(item)
            except TransferPaused:
                # Belt and braces: _do_item already parks the row. Catching
                # here too guarantees a control signal can never be mistaken
                # for a transfer failure by the generic branch below.
                self._pause_item_row(item)
            except TransferStopped:
                self._stop_item_row(item)
            except Exception as exc:  # last-resort classification
                err = classify(exc)
                item.last_error_code = err.code
                item.last_error_msg = err.raw[:400]
                db.upsert_item(item)
                self._queue.try_transition(item.id, "Failed", reason=err.code)
                PROGRESS.finish_item(item.id, ok=False)

    async def _do_item(self, item: MediaItem) -> None:
        # Duplicate check
        rep = dup_check(self.drive, item.source_key, item.size_bytes)
        if rep.is_duplicate:
            self._queue.try_transition(item.id, "Skipped", reason="duplicate", drive_file_id=rep.drive_file_id or "")
            PROGRESS.finish_item(item.id, ok=True, skipped=True)
            return

        # Preflights
        ok_disk, free = storage_preflight(item.size_bytes)
        if not ok_disk:
            self._queue.try_transition(item.id, "Failed", reason="disk_full",
                                 last_error_code="DISK_FULL",
                                 last_error_msg=f"free={free} need={item.size_bytes}")
            PROGRESS.finish_item(item.id, ok=False)
            return
        try:
            preflight_or_raise(self.drive, item.size_bytes)
        except Exception as e:
            self._queue.try_transition(item.id, "Failed", reason="drive_quota",
                                 last_error_code="DRIVE_QUOTA", last_error_msg=str(e)[:400])
            PROGRESS.finish_item(item.id, ok=False)
            return

        attempt = 0
        while True:
            attempt += 1
            if not await self._wait_resume():
                self._stop_item_row(item)
                return
            if self._stop.is_set() or not await self._wait_item(item.id):
                self._stop_item_row(item)
                return
            try:
                await self._run_once(item)
                return
            except TransferPaused:
                # NOT a failure: no attempt counter, no retry, no classify().
                self._pause_item_row(item)
                return
            except TransferStopped:
                self._stop_item_row(item)
                return
            except Exception as exc:
                err = classify(exc)
                item.last_error_code = err.code
                item.last_error_msg = str(exc)[:400]
                db.upsert_item(item)
                db.add_event(item.id, "error", err.code, {"attempt": attempt, "cat": err.category})
                if not should_retry(err, attempt):
                    to = "Failed" if err.category != "reauth" else "Failed"
                    self._queue.try_transition(item.id, to, reason=err.code)
                    PROGRESS.finish_item(item.id, ok=False)
                    return
                self._queue.try_transition(item.id, "NeedsRetry", reason=err.code)
                await sleep_for_error(err, attempt)
                self._queue.try_transition(item.id, "Pending", reason="retry")

    async def _run_once(self, item: MediaItem) -> None:
        safe = sanitize_filename(item.safe_name or item.original_name or f"{item.id}.{item.extension}")
        temp = temp_path_for(item.id, safe)
        item.temp_path = str(temp)
        db.upsert_item(item)

        # DOWNLOAD
        self._queue.transition(item.id, "Downloading")
        PROGRESS.start_item(item.id, safe, item.size_bytes, phase="download")

        def dl_cb(current: int, total: int) -> None:
            # M26-T01: the ONLY point where a running download can be
            # interrupted. Telethon calls this per chunk and does not swallow
            # exceptions, so the raise aborts download_media() cleanly and the
            # partial .part file is left exactly where it is.
            self._raise_if_interrupted(item.id)
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

        self._queue.transition(item.id, "Downloaded")

        # UPLOAD
        self._queue.transition(item.id, "Uploading")

        def up_cb(current: int, total: int) -> None:
            # M26-T01: same gate for the resumable upload. drive_client
            # re-raises TransferControlSignal instead of swallowing it (§4.3).
            self._raise_if_interrupted(item.id)
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
        self._queue.transition(item.id, "Verifying", drive_file_id=file_id)
        try:
            self._verify(file_id, item)
        except Exception as exc:
            # Do NOT delete temp — mark failed for user review.
            self._queue.transition(item.id, "Failed",
                             reason="verify_failed",
                             last_error_code="VERIFY_FAILED",
                             last_error_msg=str(exc)[:400])
            db.add_event(item.id, "RECOVERY", "verification failed, temp kept",
                         {"drive_file_id": file_id})
            PROGRESS.finish_item(item.id, ok=False)
            return

        # DURABLE CHECKPOINT before the temp file is allowed to disappear.
        self._queue.transition(item.id, "UploadedPendingCheckpoint",
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

        self._queue.transition(item.id, "Uploaded", upload_pct=100.0)
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

