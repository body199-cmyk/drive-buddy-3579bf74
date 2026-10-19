"""Orchestrates download → upload → verify with semaphore-bounded concurrency."""
from __future__ import annotations

import asyncio
import mimetypes
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from . import checkpoint_manager, database as db
from .config import (
    CONFIG,
    DOWNLOAD_REQUEST_SIZE,
    FAST_DOWNLOAD_MIN_BYTES,
    MAX_CONCURRENT_TG_DOWNLOADS,
    MAX_PENDING_UPLOADS,
)
from .duplicate_detector import check as dup_check
from .drive_quota import preflight_or_raise
from .error_handler import classify
from .errors import TransferControlSignal, TransferPaused, TransferStopped
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
    #: Minimum seconds between SQLite progress writes for the same item.
    DB_PROGRESS_INTERVAL = 0.5

    def __init__(self, telegram, drive, drive_folder_id: str, queue=None,
                 item_ids=None):
        self.telegram = telegram
        self.drive = drive
        self.drive_folder_id = drive_folder_id
        # The queue is INJECTED. There is no module singleton (Phase C).
        self._queue = queue if queue is not None else QueueManager()
        self._scope: Optional[set[str]] = set(item_ids) if item_ids else None
        self._sema: Optional[asyncio.Semaphore] = None
        # M45-T01: the pipeline has three independent bounds. _sema limits the
        # download stage only, _tg_sema limits whole files on the single MTProto
        # connection, and _upload_sema bounds finished files waiting for the one
        # Drive uploader (disk backpressure).
        self._tg_sema: Optional[asyncio.Semaphore] = None
        self._upload_sema: Optional[asyncio.Semaphore] = None
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
        # Sets are written from Gradio workers and read from the runtime loop.
        # Events are thread-safe by themselves; the related item sets are not.
        self._control_lock = threading.RLock()
        self._paused_items: set[str] = set()
        self._stopped_items: set[str] = set()
        # googleapiclient service objects are not thread-safe. All blocking
        # Drive calls are serialized in a worker thread, never on this loop.
        self._drive_lock = threading.Lock()
        # Waiting for the single Drive service must not consume executor
        # threads; the asyncio gate is created per running loop.
        self._drive_loop_lock: Optional[asyncio.Lock] = None
        self._drive_lock_loop: Any = None
        self._stop_cancel_task: Optional[asyncio.Task] = None
        # Download callbacks run on the runtime loop and upload callbacks are
        # scheduled there from a Drive worker; keep the throttle safe either way.
        self._progress_lock = threading.Lock()
        self._last_db_write: dict[str, float] = {}

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

    def _tg_semaphore(self) -> asyncio.Semaphore:
        """Whole-file download permits on the single MTProto connection.

        ``worker_count`` may be 100, but Telegram must never see 100 simultaneous
        file streams: the socket suffers head-of-line blocking and starts
        answering "Request was unsuccessful 6 time(s)".
        """
        sema = self._tg_sema
        if sema is None:
            cap = max(1, min(self.worker_count(), MAX_CONCURRENT_TG_DOWNLOADS))
            sema = asyncio.Semaphore(cap)
            self._tg_sema = sema
        return sema

    def _upload_buffer(self) -> asyncio.Semaphore:
        """Bound finished .part files waiting for the single Drive uploader."""
        sema = self._upload_sema
        if sema is None:
            sema = asyncio.Semaphore(MAX_PENDING_UPLOADS)
            self._upload_sema = sema
        return sema

    def worker_count(self) -> int:
        from .config import HARD_CONCURRENCY_CAP
        value = self._workers if self._workers is not None else CONFIG.concurrency_value()
        return max(1, min(int(value), HARD_CONCURRENCY_CAP))

    def set_workers(self, workers: int) -> int:
        """Apply a new cap only to a future drain when work is in flight.

        Replacing a live semaphore would split capacity across the old and new
        objects: current workers release the old object while new workers take
        the new one.  Keep the existing object until every tracked task has
        settled, then rebuild lazily on the next run.
        """
        from .config import HARD_CONCURRENCY_CAP

        self._workers = max(1, min(int(workers), HARD_CONCURRENCY_CAP))
        if not self._tasks or all(task.done() for task in self._tasks):
            self._sema = None
            self._tg_sema = None
        return self._workers

    # ---- per-item control ----

    def pause_item(self, item_id: str) -> None:
        with self._control_lock:
            self._paused_items.add(item_id)

    def resume_item(self, item_id: str) -> None:
        with self._control_lock:
            self._paused_items.discard(item_id)

    def stop_item(self, item_id: str) -> None:
        with self._control_lock:
            self._stopped_items.add(item_id)
            self._paused_items.discard(item_id)

    def item_paused(self, item_id: str) -> bool:
        with self._control_lock:
            return item_id in self._paused_items

    def item_stopped(self, item_id: str) -> bool:
        with self._control_lock:
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
        with self._control_lock:
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
        self._reset_progress_throttle(item.id)
        db.add_event(item.id, "transfer", "paused mid-file", {"temp_kept": True})

    def _stop_item_row(self, item: MediaItem) -> None:
        """Park an interrupted item as Stopped (final). Drive untouched."""
        self._queue.try_transition(item.id, "Stopped", reason="stopped")
        PROGRESS.release_item(item.id)
        self._reset_progress_throttle(item.id)
        db.add_event(item.id, "transfer", "stopped mid-file", {"temp_kept": True})

    def request_stop_cancel(self, grace_seconds: float = 5.0) -> None:
        """Loop-thread entry point for a bounded Stop fallback.

        Pause/Stop normally interrupt at the next progress callback. A blocked
        socket can fail to call back, so QueueManager schedules this method on
        the one AsyncRuntime loop after Stop. No ad-hoc loop or global timeout
        is created.
        """
        if self._stop_cancel_task is not None and not self._stop_cancel_task.done():
            return
        self._stop_cancel_task = asyncio.create_task(
            self._cancel_stuck_workers(grace_seconds)
        )

    async def _cancel_stuck_workers(self, grace_seconds: float) -> None:
        await asyncio.sleep(max(0.0, grace_seconds))
        if not self._stop.is_set():
            return
        for task in list(self._tasks):
            if not task.done():
                _log.warning("stop grace elapsed; cancelling stalled transfer task")
                task.cancel()

    def _drive_gate(self) -> asyncio.Lock:
        loop = asyncio.get_running_loop()
        if self._drive_loop_lock is None or self._drive_lock_loop is not loop:
            self._drive_loop_lock = asyncio.Lock()
            self._drive_lock_loop = loop
        return self._drive_loop_lock

    async def _drive_call(self, fn: Callable[..., Any], *args, **kwargs) -> Any:
        """Run one blocking Drive/googleapiclient call off the runtime loop.

        M45-T01: callers queue on an asyncio lock before a worker thread is
        taken. The previous code acquired the threading lock *inside*
        ``to_thread``, so every item waiting for a drive upload also pinned a
        thread from the default executor. With the download/upload pipeline
        that could exhaust the executor and stall unrelated metadata calls.
        """
        def runner():
            with self._drive_lock:
                return fn(*args, **kwargs)

        async with self._drive_gate():
            return await asyncio.to_thread(runner)

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
            # Operator Stop may cancel a wedged worker after its grace period;
            # every other worker exception must reach QueueManager's completion
            # callback instead of being indistinguishable from a clean finish.
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, BaseException) and not isinstance(
                    result, asyncio.CancelledError
                ):
                    raise result


    async def _process(self, item: MediaItem) -> None:
        # A paused item must wait before claiming a download permit. Otherwise a
        # paused first item can starve later runnable items when concurrency is
        # one (or consume every available permit at higher concurrency).
        if not await self._wait_resume():
            self._queue.try_transition(item.id, "Stopped")
            return
        if not await self._wait_item(item.id):
            self._queue.try_transition(item.id, "Stopped")
            return

        try:
            await self._do_item(item)
        except asyncio.CancelledError:
            # The bounded Stop fallback may cancel a socket await after its
            # grace period. It is still an operator Stop, never a failure.
            self._stop_item_row(item)
            raise
        except TransferPaused:
            # Belt and braces: the stages already park the row. Catching here
            # guarantees a control signal is never mistaken for a failure.
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
        """Download then upload as two stages, not one monopolized worker.

        M45-T01: the worker permit covers ONLY the download stage. As soon as
        the file is complete on local disk the permit is released and the upload
        runs under the serialized Drive gate, so Telegram downloads never stop
        waiting for a Drive upload. The upload buffer is acquired *before* the
        download permit is released, which keeps at most MAX_PENDING_UPLOADS
        finished files on disk while still allowing downloads to continue.
        """
        buffer_slot = self._upload_buffer()
        async with self._semaphore():
            if self._stop.is_set() or self.item_stopped(item.id):
                self._queue.try_transition(item.id, "Stopped")
                return
            if not await self._download_stage(item):
                return
            await buffer_slot.acquire()
        try:
            await self._upload_stage(item)
        finally:
            buffer_slot.release()

    async def _download_stage(self, item: MediaItem) -> bool:
        """Duplicate pre-check, disk preflight and the download retry loop.

        No blocking Drive call happens here: an idle-service duplicate check is
        best effort, and quota/duplicate decisions that need Drive are made by
        the upload stage. Returns True only when a complete, size-verified local
        file is ready for upload. Any parked row returns False.
        """
        safe = sanitize_filename(
            item.safe_name or item.original_name or f"{item.id}.{item.extension}"
        )
        temp = temp_path_for(item.id, safe)

        current = db.get_item(item.id)
        if current is not None and current.state == "Downloaded":
            # A previous run (or a failed upload) already downloaded this file.
            # Re-downloading it would throw away gigabytes of valid work.
            expected = int(item.size_bytes or 0)
            if temp.exists() and (expected <= 0 or temp.stat().st_size == expected):
                item.temp_path = str(temp)
                db.upsert_item(item)
                PROGRESS.start_item(item.id, safe, item.size_bytes, phase="download")
                if item.size_bytes:
                    PROGRESS.update(item.id, int(item.size_bytes), phase="download")
                db.add_event(
                    item.id,
                    "transfer",
                    "reusing completed download",
                    {"bytes": temp.stat().st_size},
                )
                _log.info("reusing completed download for %s", item.id)
                return True
            # The row says Downloaded but the temp file is gone (restart on a
            # fresh Colab VM). NeedsRetry is the legal path back to Downloading.
            self._queue.try_transition(item.id, "NeedsRetry", reason="download_missing_temp")

        # Duplicate pre-check. M45-T01 removed every BLOCKING Drive call from
        # the download lane: waiting here behind a multi-minute Drive upload is
        # exactly what stopped Telegram downloads on the owner's queue. The
        # pre-check only runs while the shared Drive service is idle; otherwise
        # the upload stage reuses the existing Drive file instead.
        rep = await self._duplicate_precheck(item)
        if rep is not None and rep.is_duplicate:
            self._queue.try_transition(item.id, "Skipped", reason="duplicate", drive_file_id=rep.drive_file_id or "")
            PROGRESS.finish_item(item.id, ok=True, skipped=True)
            return False

        # Local disk preflight only — it never touches the network.
        ok_disk, free = storage_preflight(item.size_bytes)
        if not ok_disk:
            self._queue.try_transition(item.id, "Failed", reason="disk_full",
                                 last_error_code="DISK_FULL",
                                 last_error_msg=f"free={free} need={item.size_bytes}")
            PROGRESS.finish_item(item.id, ok=False)
            return False

        attempt = 0
        while True:
            attempt += 1
            if not await self._wait_resume():
                self._stop_item_row(item)
                return False
            if self._stop.is_set() or not await self._wait_item(item.id):
                self._stop_item_row(item)
                return False
            try:
                await self._run_download(item)
                return True
            except TransferPaused:
                # NOT a failure: no attempt counter, no retry, no classify().
                self._pause_item_row(item)
                return False
            except TransferStopped:
                self._stop_item_row(item)
                return False
            except Exception as exc:
                err = classify(exc)
                item.last_error_code = err.code
                item.last_error_msg = str(exc)[:400]
                db.upsert_item(item)
                db.add_event(item.id, "error", err.code,
                             {"attempt": attempt, "cat": err.category, "stage": "download"})
                if not should_retry(err, attempt):
                    self._queue.try_transition(item.id, "Failed", reason=err.code)
                    PROGRESS.finish_item(item.id, ok=False)
                    return False
                self._queue.try_transition(item.id, "NeedsRetry", reason=err.code)
                await sleep_for_error(err, attempt)
                self._queue.try_transition(item.id, "Pending", reason="retry")

    async def _duplicate_precheck(self, item: MediaItem):
        """Pre-download duplicate check interleaved between 8 MiB upload chunks.

        M45-T02: ``upload_resumable`` acquires ``_drive_lock`` per 8 MiB chunk
        rather than holding ``_drive_gate`` across an entire multi-minute file
        upload. Running ``dup_check`` under ``_drive_lock`` therefore waits at
        most one chunk before catching a duplicate in ``Pending -> Skipped``
        without downloading gigabytes from Telegram first.
        """
        if self.drive is None:
            return None
        try:
            def runner():
                with self._drive_lock:
                    return dup_check(self.drive, item.source_key, item.size_bytes)

            return await asyncio.to_thread(runner)
        except Exception as exc:  # best effort; the upload stage decides
            _log.warning(
                "duplicate pre-check failed for %s: %s", item.id, type(exc).__name__
            )
            return None

    async def _upload_stage(self, item: MediaItem) -> None:
        """Upload + verify + durable checkpoint with their own retry budget.

        A failed upload retries the upload, never the download. Before M45-T01
        every upload retry re-entered the whole item, so the already-downloaded
        .part file was downloaded again from byte zero.
        """
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
                await self._run_upload(item)
                return
            except TransferPaused:
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
                db.add_event(item.id, "error", err.code,
                             {"attempt": attempt, "cat": err.category, "stage": "upload"})
                if not should_retry(err, attempt):
                    self._queue.try_transition(item.id, "Failed", reason=err.code)
                    PROGRESS.finish_item(item.id, ok=False)
                    return
                self._queue.try_transition(item.id, "NeedsRetry", reason=err.code)
                await sleep_for_error(err, attempt)

    def _should_persist(self, item_id: str, force: bool) -> bool:
        """Rate-limit SQLite progress writes while preserving boundary updates."""

        now = time.monotonic()
        with self._progress_lock:
            last = self._last_db_write.get(item_id, 0.0)
            if not force and now - last < self.DB_PROGRESS_INTERVAL:
                return False
            self._last_db_write[item_id] = now
            return True

    def _reset_progress_throttle(self, item_id: str) -> None:
        """Allow an immediate persistence write when a run changes state."""

        with self._progress_lock:
            self._last_db_write.pop(item_id, None)

    async def _chat_ref(self, item: MediaItem):
        """Resolve a stored chat id when the injected client supports it."""

        resolver = getattr(self.telegram, "resolve_entity", None)
        if not callable(resolver):
            return item.chat_id
        return await resolver(item.chat_id)

    async def _download(self, msg, item: MediaItem, temp: Path, progress_cb) -> str:
        """Resume a usable local partial without deleting it or restarting blindly."""

        partial = getattr(self.telegram, "download_partial", None)
        offset = temp.stat().st_size if temp.exists() else 0
        declared = int(item.size_bytes or 0)

        # M45-T01: a retry (upload failure, transient download error, Colab
        # restart) must never re-download bytes that are already on disk.
        if (
            offset > 0
            and declared > 0
            and offset == declared
            and item.media_type != "photo"
        ):
            db.add_event(
                item.id,
                "transfer",
                "reusing complete local file",
                {"bytes": offset},
            )
            return str(temp)

        if (
            callable(partial)
            and offset > 0
            and declared > offset
            and item.media_type != "photo"
        ):
            db.add_event(
                item.id,
                "transfer",
                "resuming download from offset",
                {"offset": offset, "total": declared},
            )
            return await partial(msg, str(temp), declared, progress_cb=progress_cb)

        # Fresh, sizeable non-photo media: request the MTProto maximum in
        # bounded interleaved streams. Telethon's public download_media() uses
        # 128 KiB requests for files <= 100 MB, which is the main throughput
        # ceiling on Colab. The .part file stays a valid prefix at every
        # contiguous chunk boundary.
        fast = getattr(self.telegram, "download_media_fast", None)
        if (
            callable(fast)
            and offset == 0
            and declared >= FAST_DOWNLOAD_MIN_BYTES
            and item.media_type != "photo"
        ):
            try:
                return await fast(msg, str(temp), declared, progress_cb=progress_cb)
            except TransferControlSignal:
                # Pause/Stop is an operator decision, never a transport failure.
                raise
            except Exception as exc:  # noqa: BLE001 - fallback decision is the point
                # M45-T01: losing a resumed prefix is worse than falling back.
                # If at least one full 512 KiB request reached disk, the retry
                # loop can resume it; the legacy path would open(file, "wb")
                # and throw the bytes away.
                kept = temp.stat().st_size if temp.exists() else 0
                if kept >= DOWNLOAD_REQUEST_SIZE:
                    db.add_event(
                        item.id,
                        "RECOVERY",
                        "fast download interrupted; partial kept for resume",
                        {"bytes": kept, "error": f"{type(exc).__name__}: {exc}"[:400]},
                    )
                    _log.warning(
                        "fast download failed for %s after %s bytes (%s); "
                        "keeping the partial for resume",
                        item.id,
                        kept,
                        type(exc).__name__,
                    )
                    raise
                # Too little to be worth resuming: one clean legacy fallback.
                db.add_event(
                    item.id,
                    "RECOVERY",
                    "fast download failed; legacy path used",
                    {"error": f"{type(exc).__name__}: {exc}"[:400]},
                )
                _log.warning(
                    "fast download failed for %s (%s); using legacy path",
                    item.id,
                    type(exc).__name__,
                )
        return await self.telegram.download_media(msg, str(temp), progress_cb=progress_cb)

    def _record_progress(
        self,
        item_id: str,
        current: int,
        total: int,
        phase: str,
        force: bool = False,
    ) -> None:
        """Persist bounded progress on the AsyncRuntime thread."""

        if not self._should_persist(item_id, force):
            return
        row = db.get_item(item_id)
        if row is None:
            return
        pct = (current / total * 100) if total else 0.0
        if phase == "upload":
            row.upload_pct = pct
        else:
            row.download_pct = pct
        db.upsert_item(row)

    async def _run_download(self, item: MediaItem) -> None:
        """One download attempt, bounded by the Telegram connection budgets."""
        safe = sanitize_filename(item.safe_name or item.original_name or f"{item.id}.{item.extension}")
        temp = temp_path_for(item.id, safe)
        item.temp_path = str(temp)
        db.upsert_item(item)

        self._queue.transition(item.id, "Downloading")
        PROGRESS.start_item(item.id, safe, item.size_bytes, phase="download")

        def dl_cb(current: int, total: int) -> None:
            # M26-T01: the ONLY point where a running download can be
            # interrupted. Telethon calls this per chunk and does not swallow
            # exceptions, so the raise aborts download_media() cleanly and the
            # partial .part file is left exactly where it is.
            self._raise_if_interrupted(item.id)
            PROGRESS.update(item.id, current, phase="download")
            self._record_progress(item.id, current, total, "download")

        # M45-T01: at most MAX_CONCURRENT_TG_DOWNLOADS whole files touch the
        # single MTProto connection, no matter how high the queue concurrency is.
        async with self._tg_semaphore():
            chat_ref = await self._chat_ref(item)
            msg = await self.telegram.get_message(chat_ref, item.message_id)
            actual_path = await self._download(msg, item, temp, dl_cb)

        actual = Path(actual_path)
        if not actual.exists():
            raise RuntimeError("downloaded file missing")
        got = actual.stat().st_size
        if item.size_bytes and got != item.size_bytes:
            # Not fatal for photos (unknown size); tolerate.
            if item.media_type not in ("photo",):
                raise RuntimeError(f"size mismatch download: expected {item.size_bytes}, got {got}")
            item.size_bytes = got
            # The authoritative size for photos becomes known only after the
            # download. Persist it before upload/verification so SQLite,
            # checkpoints, and future retries agree with the in-memory row.
            db.upsert_item(item)

        self._queue.transition(item.id, "Downloaded", download_pct=100.0)
        self._reset_progress_throttle(item.id)

    async def _run_upload(self, item: MediaItem) -> None:
        """One upload attempt: resumable upload, verify, durable checkpoint."""
        loop = asyncio.get_running_loop()
        safe = sanitize_filename(item.safe_name or item.original_name or f"{item.id}.{item.extension}")
        actual = Path(item.temp_path) if item.temp_path else temp_path_for(item.id, safe)
        if not actual.exists():
            raise RuntimeError("downloaded file missing")

        # UPLOAD
        self._queue.transition(item.id, "Uploading")

        # Authoritative duplicate check. The download lane only performs it when
        # the Drive service is idle; this is the fallback that prevents a second
        # copy when it was busy. Reusing the existing Drive file ends the row as
        # Uploaded (the bytes are on Drive), with an explicit event.
        rep = await self._drive_call(dup_check, self.drive, item.source_key, item.size_bytes)
        if rep.is_duplicate and rep.drive_file_id:
            self._queue.transition(item.id, "Verifying", drive_file_id=rep.drive_file_id)
            self._queue.transition(item.id, "UploadedPendingCheckpoint",
                                   drive_file_id=rep.drive_file_id,
                                   drive_folder_id=self.drive_folder_id)
            try:
                await self._drive_call(checkpoint_manager.persist_durable, self.drive)
            except Exception as exc:
                db.add_event(item.id, "RECOVERY",
                             "duplicate reuse could not persist a checkpoint; temp kept",
                             {"error": str(exc)[:400]})
                PROGRESS.finish_item(item.id, ok=False)
                return
            self._queue.transition(item.id, "Uploaded", upload_pct=100.0)
            self._reset_progress_throttle(item.id)
            db.add_event(item.id, "duplicate", "reused existing drive file",
                         {"drive_file_id": rep.drive_file_id})
            cleanup_item(item.id)
            PROGRESS.finish_item(item.id, ok=True, skipped=True)
            return

        # Fresh quota preflight, now that the bytes are already local. It runs
        # in the upload lane so the (blocking) Drive call can never gate a
        # Telegram download.
        try:
            await self._drive_call(preflight_or_raise, self.drive, item.size_bytes)
        except Exception as e:
            self._queue.transition(item.id, "Failed", reason="drive_quota",
                                   last_error_code="DRIVE_QUOTA",
                                   last_error_msg=str(e)[:400])
            PROGRESS.finish_item(item.id, ok=False)
            return

        def up_cb(current: int, total: int) -> None:
            # M26-T01: same gate for the resumable upload. drive_client
            # re-raises TransferControlSignal instead of swallowing it (§4.3).
            self._raise_if_interrupted(item.id)
            PROGRESS.update(item.id, current, phase="upload")
            loop.call_soon_threadsafe(
                self._record_progress, item.id, current, total, "upload"
            )

        mime, _ = mimetypes.guess_type(safe)

        def _upload_with_chunk_lock():
            try:
                return self.drive.upload_resumable(
                    file_path=str(actual),
                    drive_name=safe,
                    parent_id=self.drive_folder_id,
                    source_key=item.source_key,
                    progress_cb=up_cb,
                    mime_type=mime,
                    chunk_lock=self._drive_lock,
                )
            except TypeError:
                with self._drive_lock:
                    return self.drive.upload_resumable(
                        file_path=str(actual),
                        drive_name=safe,
                        parent_id=self.drive_folder_id,
                        source_key=item.source_key,
                        progress_cb=up_cb,
                        mime_type=mime,
                    )

        async with self._drive_gate():
            result = await asyncio.to_thread(_upload_with_chunk_lock)
        file_id = result["id"]

        # VERIFY — Drive must prove id + size + parent + source key + not trashed.
        self._queue.transition(item.id, "Verifying", drive_file_id=file_id)
        try:
            await self._drive_call(self._verify, file_id, item)
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
            checkpoint_id = await self._drive_call(checkpoint_manager.persist_durable, self.drive)
        except Exception as exc:
            db.add_event(item.id, "RECOVERY",
                         "durable checkpoint failed, temp kept and state left "
                         "UploadedPendingCheckpoint",
                         {"error": str(exc)[:400], "drive_file_id": file_id})
            _log.warning("durable checkpoint failed for %s: %s", item.id, exc)
            PROGRESS.finish_item(item.id, ok=False)
            return

        self._queue.transition(item.id, "Uploaded", upload_pct=100.0)
        self._reset_progress_throttle(item.id)
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

