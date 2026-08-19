"""Queue manager: ONLY module allowed to mutate item state."""
from __future__ import annotations

from concurrent.futures import CancelledError
from typing import Iterable, Optional

from . import database as db
from .logging_config import get_logger
from .models import MediaItem
from .state_machine import assert_transition, can_transition

_log = get_logger("teledrive.queue")


class QueueManager:
    """Instance-scoped. There is NO module-level singleton (Phase C).

    Every runtime attribute lives on the instance, so two contexts can never
    share transfer state through class attributes.
    """

    def __init__(self, ctx=None) -> None:
        self.ctx = ctx
        self._future = None
        self._status = "idle"

    def enqueue(self, item: MediaItem) -> MediaItem:

        existing = db.find_by_source_key(item.source_key) if item.source_key else None
        if existing:
            return existing
        db.upsert_item(item)
        db.add_event(item.id, "enqueued", f"{item.safe_name}")
        return item

    def bulk_enqueue(self, items: Iterable[MediaItem]) -> list[MediaItem]:
        return [self.enqueue(i) for i in items]

    def transition(self, item_id: str, to_state: str, reason: str = "", **fields) -> MediaItem:
        item = db.get_item(item_id)
        if not item:
            raise KeyError(item_id)
        assert_transition(item.state, to_state)
        prev = item.state
        item.state = to_state
        if to_state in ("Downloading", "Uploading"):
            item.attempts += 1
        for k, v in fields.items():
            if hasattr(item, k):
                setattr(item, k, v)
        db.upsert_item(item)
        db.add_event(item.id, "state", f"{prev}->{to_state} {reason}".strip(),
                     {"from": prev, "to": to_state, "reason": reason, "attempts": item.attempts})
        return item

    def try_transition(self, item_id: str, to_state: str, **fields) -> Optional[MediaItem]:
        item = db.get_item(item_id)
        if not item or not can_transition(item.state, to_state):
            return None
        return self.transition(item_id, to_state, **fields)

    def set_priority(self, item_id: str, priority: int) -> None:
        item = db.get_item(item_id)
        if not item:
            return
        item.priority = priority
        db.upsert_item(item)

    def next_pending(self) -> Optional[MediaItem]:
        items = db.list_items(state="Pending", limit=1)
        return items[0] if items else None

    def pending(self) -> list[MediaItem]:
        return db.items_in_states(["Pending", "NeedsRetry", "Downloaded"])

    def active(self) -> list[MediaItem]:
        return db.items_in_states(["Downloading", "Uploading"])

    def snapshot_counts(self) -> dict[str, int]:
        return db.counts_by_state()

    # ------------------------------------------------------------------
    # Transfer control surface (Constitution Section 9).
    # Bound to the ApplicationContext; the ONLY place transfers are started.
    # ------------------------------------------------------------------

    def bind_context(self, ctx) -> "QueueManager":
        self.ctx = ctx
        return self

    def _require_ctx(self):
        if self.ctx is None:
            raise RuntimeError("QueueManager is not bound to an ApplicationContext")
        return self.ctx

    def status_label(self) -> str:
        return self._status

    def apply_concurrency(self, workers: int) -> int:
        """Clamp to 1..HARD_CONCURRENCY_CAP and forward the clamped value."""
        from .config import HARD_CONCURRENCY_CAP

        clamped = max(1, min(int(workers), HARD_CONCURRENCY_CAP))
        manager = getattr(self._require_ctx(), "transfer_manager", None)
        if manager is not None and hasattr(manager, "set_workers"):
            manager.set_workers(clamped)
        return clamped


    def running(self) -> bool:
        return self._future is not None and not self._future.done()

    # -- batch preflight (Phase C): one gate, before any worker starts --

    def batch_preflight(self, items: list[MediaItem]) -> dict:
        """Telegram, Drive, quota, local disk + reserve. Raises on failure."""
        from .drive_quota import preflight_or_raise
        from .errors import DriveNotReadyError, LocalDiskError, TelegramNotReadyError
        from .storage_manager import preflight as storage_preflight

        ctx = self._require_ctx()
        if ctx.telegram_auth is None or not ctx.telegram_auth.authorized:
            raise TelegramNotReadyError("telegram is not authorized")
        if ctx.drive_auth is None or not ctx.drive_auth.connected:
            raise DriveNotReadyError("drive is not connected")
        folder = ctx.drive_folders.require_selected()

        total = sum(int(i.size_bytes or 0) for i in items)
        largest = max([int(i.size_bytes or 0) for i in items] or [0])
        quota = preflight_or_raise(ctx.drive_client, total)
        ok_disk, free = storage_preflight(largest)
        if not ok_disk:
            raise LocalDiskError(f"local disk reserve: free={free} need={largest}")
        return {
            "folder_id": folder.id,
            "items": len(items),
            "total_bytes": total,
            "largest_bytes": largest,
            "free_bytes": free,
            "quota": getattr(quota, "__dict__", {}) or {},
        }

    def selected_pending(self, item_ids=None) -> list[MediaItem]:
        """Resolve which pending rows Start should process.

        * An explicit id list is a hard filter — never every Pending row.
        * An explicit empty list means start nothing (the Phase C contract).
        * ``None`` (the Start button, no argument) uses the in-memory analyze
          selection when it still matches queue rows. After a Colab Restart
          that selection is gone while SQLite still holds leftover work, so
          we fall back to every startable Pending/NeedsRetry/Downloaded row.
          That is an explicit Start click, not auto-resume.
        """
        if item_ids is not None:
            wanted = {str(i) for i in item_ids if str(i)}
            if not wanted:
                return []
            return [i for i in self.pending() if i.id in wanted]
        selection = getattr(self._require_ctx(), "selection", None)
        wanted = {str(i) for i in getattr(selection, "selected_ids", set()) or set()}
        if wanted:
            matched = [i for i in self.pending() if i.id in wanted]
            if matched:
                return matched
        return list(self.pending())

    def start_selected(self, item_ids=None) -> dict:
        from .drive_client import DriveService
        from .errors import NothingSelectedError

        ctx = self._require_ctx()
        if self.running():
            return {"status": "running", "started": 0}

        items = self.selected_pending(item_ids)
        if not items:
            self._status = "idle"
            # Preserve the established explicit-empty selection contract: it
            # means "start nothing". A normal Start click (None) after Stop
            # has no Pending work and must surface the translated error.
            if item_ids is not None:
                return {"status": "idle", "started": 0, "message_key": "msg.no_selection"}
            # The decorated handler maps this typed error to the current UI
            # output shape and localized message instead of failing silently.
            raise NothingSelectedError("no pending items to transfer")

        if ctx.drive_client is None:
            ctx.drive_client = DriveService.from_auth(ctx.drive_auth)
        report = self.batch_preflight(items)

        manager = ctx.ensure_transfer_manager(report["folder_id"])
        # M26-T01 / RC-5: ONE manager is reused per context, so a Stop from an
        # earlier batch would otherwise refuse this Start outright.
        manager.reset_run_flags()
        manager.set_scope([i.id for i in items])
        manager.set_workers(ctx.config.concurrency_value())
        self._future = ctx.aio.submit(manager.run())
        self._future.add_done_callback(self._on_run_done)
        self._status = "running"
        db.add_event("", "transfer", "started", {"count": len(items)})
        return {"status": "running", "started": len(items), "preflight": report}

    def _on_run_done(self, future) -> None:
        """Release the running label and surface a drain-loop crash.

        Per-item outcomes remain TransferManager's responsibility. This callback
        only records an unexpected engine-level failure that would otherwise be
        indistinguishable from a clean queue finish.
        """
        # Resume can replace the tracked future while a previous drain is
        # finishing. A stale callback may still record its own exception, but
        # it must never overwrite the status of the newer run.
        # Direct diagnostic/test invocation may not have installed a tracked
        # future yet; in that case this callback is necessarily current.
        is_current = self._future is None or future is self._future
        error = None
        try:
            error = future.exception()
        except CancelledError:
            # A bounded operator Stop may cancel a wedged worker after its
            # grace period. That is an expected control outcome, not an engine
            # crash and must never produce a false error event.
            error = None
        except Exception as exc:  # already-consumed/defensive future failure
            error = exc
        if error is not None:
            _log.error("transfer run crashed: %s", error, exc_info=error)
            db.add_event(
                "",
                "error",
                "transfer run crashed",
                {"error": f"{type(error).__name__}: {error}"[:400]},
            )
        if is_current and self._status == "running":
            self._status = "idle"


    def _manager(self):
        return getattr(self._require_ctx(), "transfer_manager", None)

    def _safe_checkpoint(self) -> dict:
        """Best-effort checkpoint used by Pause. Never raises."""
        from . import checkpoint_manager

        try:
            path = checkpoint_manager.persist_local()
        except Exception as exc:  # pragma: no cover - defensive
            _log.warning("pause checkpoint (local) failed: %s", exc)
            return {"local": None, "drive_file_id": None}
        file_id = None
        drive = getattr(self.ctx, "drive_client", None) if self.ctx else None
        if drive is not None:
            try:
                file_id = checkpoint_manager.persist(drive)
            except Exception as exc:  # pragma: no cover - defensive
                _log.warning("pause checkpoint (drive) failed: %s", exc)
        return {"local": str(path), "drive_file_id": file_id}

    def pause(self) -> dict:
        # Pausing an idle queue must be a no-op.  In particular, it must not
        # advertise a fake paused engine or write a needless checkpoint when
        # no drain worker exists.
        if not self.running():
            return self.snapshot()

        manager = self._manager()
        if manager is not None:
            manager.pause()
        # A safe checkpoint is exported BEFORE the queue is declared paused.
        checkpoint = self._safe_checkpoint()
        db.add_event("", "checkpoint", "pause", checkpoint)
        self._status = "paused"
        snapshot = self.snapshot()
        snapshot["checkpoint"] = checkpoint
        return snapshot


    def resume(self) -> dict:
        """Un-pause the engine and really put the paused work back in flight.

        Three things were missing (M26-T01 / RC-4):
        1. pending() never returns a Paused row, so nothing was re-claimed.
        2. When the previous drain loop had already finished, no run existed
           to claim anything at all.
        3. The status said "running" while nothing ran.
        Drive is not touched and no file is deleted: a resumed item simply
        restarts its current file from the beginning, keeping its .part.
        """
        manager = self._manager()
        if manager is not None:
            manager.resume()
        revived = 0
        for item in db.items_in_states(["Paused"]):
            if self.try_transition(item.id, "Pending", reason="resumed"):
                revived += 1
        if manager is not None and revived:
            # A Paused worker may have returned while the previous drain future
            # still reports running. That old drain has already recorded this
            # item in its `seen` set, so it can never claim the revived Pending
            # row. It can also still be unwinding a Telethon generator: starting
            # another drain immediately would overlap two downloads on the one
            # client. Queue the fresh drain after the old future settles.
            previous = self._future
            if previous is not None and not previous.done():
                def restart_after_previous(completed):
                    self._restart_resumed_drain(manager, completed)

                previous.add_done_callback(restart_after_previous)
            else:
                self._start_resumed_drain(manager)
        # A queue with no active drain and no revived Paused row is idle.  Do
        # not display a false running badge merely because Resume was clicked.
        self._status = "running" if self.running() else "idle"
        snapshot = self.snapshot()
        snapshot["resumed"] = revived
        return snapshot

    def _restart_resumed_drain(self, manager, completed_future) -> None:
        """Callback path: only the still-current prior drain may restart work."""
        if self._future is not completed_future:
            return
        self._start_resumed_drain(manager)

    def _start_resumed_drain(self, manager) -> None:
        """Start revived work after the previous drain is no longer in flight."""
        if manager.stopping() or not self.pending():
            return
        manager.reset_run_flags()
        self._status = "running"
        self._future = self._require_ctx().aio.submit(manager.run())
        self._future.add_done_callback(self._on_run_done)

    def stop(self) -> dict:
        """Stop the engine. In-flight files abort at the next chunk boundary
        and become Stopped (final). No Drive file is ever deleted and no
        temp file is blindly cleaned.
        """
        manager = self._manager()
        if manager is not None:
            manager.stop()
            # Cooperative callbacks normally settle immediately. This only
            # handles a wedged await after five seconds on the existing runtime
            # loop; it never creates another event loop or cancels globally.
            ctx = self._require_ctx()
            if ctx.aio.is_running:
                ctx.aio.call_soon(manager.request_stop_cancel, 5.0)
        self._status = "stopped"
        db.add_event("", "transfer", "stop requested", {"drive_touched": False})
        snapshot = self.snapshot()
        snapshot["stopping"] = True
        return snapshot

    def pause_item(self, item_id: str) -> dict:
        manager = self._manager()
        if manager is not None:
            manager.pause_item(item_id)
        self.try_transition(item_id, "Paused")
        return self.snapshot()

    def resume_item(self, item_id: str) -> dict:
        manager = self._manager()
        if manager is not None:
            manager.resume_item(item_id)
        self.try_transition(item_id, "Pending")
        return self.snapshot()

    def stop_item(self, item_id: str) -> dict:
        manager = self._manager()
        if manager is not None:
            manager.stop_item(item_id)
        self.try_transition(item_id, "Stopped")
        return self.snapshot()

    def retry_item(self, item_id: str) -> dict:
        self.try_transition(item_id, "NeedsRetry")
        self.try_transition(item_id, "Pending")
        return self.snapshot()

    def retry_failed(self) -> dict:
        """Retries Failed/NeedsRetry only. Stopped is FINAL and never revived."""
        retried = 0
        for item in db.items_in_states(["Failed", "NeedsRetry"]):
            if self.try_transition(item.id, "Pending", last_error_code="", last_error_msg=""):
                retried += 1
            elif self.try_transition(item.id, "NeedsRetry"):
                if self.try_transition(item.id, "Pending"):
                    retried += 1
        snapshot = self.snapshot()
        snapshot["retried"] = retried
        return snapshot


    def clear_completed_metadata(self) -> dict:
        """Clears finished ROWS only. Never touches files already on Drive."""
        removed = 0
        for item in db.items_in_states(["Uploaded", "Skipped"]):
            db.delete_item(item.id)
            removed += 1
        snapshot = self.snapshot()
        snapshot["removed"] = removed
        return snapshot

    # Unfinished queue rows. Uploaded/Skipped stay (clear_completed owns them).
    # Deleted is already gone. Drive files are never touched — delete_item
    # removes the SQLite row and its events only.
    INCOMPLETE_STATES: tuple[str, ...] = (
        "Pending",
        "Analyzing",
        "Downloading",
        "Downloaded",
        "Uploading",
        "Verifying",
        "UploadedPendingCheckpoint",
        "Paused",
        "Failed",
        "NeedsRetry",
        "Stopped",
    )

    def clear_incomplete_metadata(self) -> dict:
        """Clears unfinished ROWS only. Never deletes a file already on Drive."""
        removed = 0
        for item in db.items_in_states(self.INCOMPLETE_STATES):
            db.delete_item(item.id)
            removed += 1
        snapshot = self.snapshot()
        snapshot["removed"] = removed
        return snapshot

    def snapshot(self) -> dict:
        return {
            "status": self._status,
            "counts": db.counts_by_state(),
            "active": [i.id for i in self.active()],
            "pending": len(self.pending()),
        }

