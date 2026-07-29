"""Queue manager: ONLY module allowed to mutate item state."""
from __future__ import annotations

from typing import Iterable, Optional

from . import database as db
from .logging_config import get_logger
from .models import MediaItem
from .state_machine import assert_transition, can_transition

_log = get_logger("teledrive.queue")


class QueueManager:
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

    ctx = None
    _future = None
    _status = "idle"

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
        manager = getattr(self._require_ctx(), "transfer_manager", None)
        if manager is not None and hasattr(manager, "set_workers"):
            manager.set_workers(workers)
        return workers

    def running(self) -> bool:
        return self._future is not None and not self._future.done()

    def start_selected(self) -> dict:
        from .drive_client import DriveService
        from .errors import DriveNotReadyError, TelegramNotReadyError
        from .transfer_manager import TransferManager

        ctx = self._require_ctx()
        if ctx.telegram_auth is None or not ctx.telegram_auth.authorized:
            raise TelegramNotReadyError("telegram is not authorized")
        if ctx.drive_auth is None or not ctx.drive_auth.connected:
            raise DriveNotReadyError("drive is not connected")
        if self.running():
            return {"status": "running", "started": 0}
        folder = ctx.drive_folders.require_selected()
        ctx.drive_client = DriveService.from_auth(ctx.drive_auth)
        pending = self.pending()
        ctx.transfer_manager = TransferManager(
            ctx.telegram_auth.client, ctx.drive_client, folder.id
        )
        ctx.transfer_manager.set_workers(ctx.config.concurrency_value())
        self._future = ctx.aio.submit(ctx.transfer_manager.run())
        self._status = "running"
        db.add_event("", "transfer", "started", {"count": len(pending)})
        return {"status": "running", "started": len(pending)}

    def _manager(self):
        return getattr(self._require_ctx(), "transfer_manager", None)

    def pause(self) -> dict:
        manager = self._manager()
        if manager is not None:
            manager.pause()
        self._status = "paused"
        return self.snapshot()

    def resume(self) -> dict:
        manager = self._manager()
        if manager is not None:
            manager.resume()
        self._status = "running"
        return self.snapshot()

    def stop(self) -> dict:
        manager = self._manager()
        if manager is not None:
            manager.stop()
        self._status = "stopped"
        return self.snapshot()

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
        retried = 0
        for item in db.items_in_states(["Failed", "NeedsRetry", "Stopped"]):
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

    def snapshot(self) -> dict:
        return {
            "status": self._status,
            "counts": db.counts_by_state(),
            "active": [i.id for i in self.active()],
            "pending": len(self.pending()),
        }


QUEUE = QueueManager()
