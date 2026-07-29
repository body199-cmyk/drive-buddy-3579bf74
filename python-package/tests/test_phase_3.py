"""PHASE 3 proofs: one owned QueueManager/TransferManager, real queue controls.

PROVES = (
    "queue.resume",
    "queue.stop",
    "queue.pause_item",
    "queue.resume_item",
    "queue.stop_item",
    "queue.retry_item",
    "queue.clear_completed",
    "queue.refresh",
)
"""
from __future__ import annotations

import asyncio

import pytest

from teledrive import database as db
from teledrive.config import HARD_CONCURRENCY_CAP
from teledrive.errors import DriveNotReadyError, LocalDiskError
from teledrive.models import MediaItem
from teledrive.queue_manager import QueueManager
from teledrive.transfer_manager import TransferManager

from .mocks.fake_drive import FakeDrive
from .mocks.fake_telegram import FakeDoc, FakeMsg, FakeTelegram

PROVES = (
    "queue.resume",
    "queue.stop",
    "queue.pause_item",
    "queue.resume_item",
    "queue.stop_item",
    "queue.retry_item",
    "queue.clear_completed",
    "queue.refresh",
)

SIZE = 1024


def _item(queue: QueueManager, mid: int) -> MediaItem:
    item = MediaItem(
        source_key=f"tg:77:{mid}",
        chat_id=77,
        message_id=mid,
        original_name=f"p{mid}.bin",
        safe_name=f"p{mid}.bin",
        media_type="document",
        extension="bin",
        size_bytes=SIZE,
    )
    queue.enqueue(item)
    return item


def _telegram(*mids: int) -> FakeTelegram:
    return FakeTelegram({m: FakeMsg(id=m, document=FakeDoc(id="d", size=SIZE)) for m in mids})


# ------------------------------------------- one manager, never rebuilt


def test_context_reuses_the_same_transfer_manager_across_starts(ctx):
    ctx.drive_client = FakeDrive()
    first = ctx.ensure_transfer_manager("fld_a")
    second = ctx.ensure_transfer_manager("fld_b")
    assert first is second, "Start must reuse the one TransferManager"
    assert second.drive_folder_id == "fld_b", "folder must be refreshed in place"
    assert second.queue is ctx.queue_manager, "the manager must drain the owned queue"


def test_transfer_manager_state_is_instance_scoped():
    a = TransferManager(_telegram(1), FakeDrive(), "fld", queue=QueueManager())
    b = TransferManager(_telegram(1), FakeDrive(), "fld", queue=QueueManager())
    a.stop_item("x")
    a._status = "running"
    assert not b.item_stopped("x")
    assert a.queue is not b.queue


# ------------------------------------------------------ concurrency <= 4


def test_worker_count_is_clamped_between_one_and_four():
    mgr = TransferManager(_telegram(1), FakeDrive(), "fld", queue=QueueManager())
    assert mgr.set_workers(99) == HARD_CONCURRENCY_CAP
    assert mgr.worker_count() == HARD_CONCURRENCY_CAP
    assert mgr.set_workers(0) == 1
    assert mgr.set_workers(3) == 3


def test_apply_concurrency_forwards_the_clamped_value_to_the_manager(ctx):
    ctx.drive_client = FakeDrive()
    manager = ctx.ensure_transfer_manager("fld")
    assert ctx.queue_manager.apply_concurrency(10) == HARD_CONCURRENCY_CAP
    assert manager.worker_count() == HARD_CONCURRENCY_CAP


# --------------------------------------------------------- preflight gate


def _ready_ctx(ctx, monkeypatch):
    """Telegram + Drive + folder all satisfied, so only the resource gate is left."""
    class _Auth:
        authorized = True
        connected = True
        client = None

    class _Folder:
        id = "fld_target"

    monkeypatch.setattr(ctx, "telegram_auth", _Auth(), raising=False)
    monkeypatch.setattr(ctx, "drive_auth", _Auth(), raising=False)
    monkeypatch.setattr(ctx.drive_folders, "require_selected", lambda: _Folder())
    ctx.drive_client = FakeDrive()
    return ctx


def test_preflight_refuses_when_the_local_disk_reserve_is_not_met(ctx, monkeypatch):
    from teledrive import storage_manager

    _ready_ctx(ctx, monkeypatch)
    monkeypatch.setattr(storage_manager, "preflight", lambda need: (False, 0))
    item = _item(ctx.queue_manager, 20)
    with pytest.raises(LocalDiskError):
        ctx.queue_manager.batch_preflight([item])


def test_preflight_reports_totals_for_the_selected_items_only(ctx, monkeypatch):
    _ready_ctx(ctx, monkeypatch)
    chosen = _item(ctx.queue_manager, 21)
    _item(ctx.queue_manager, 22)
    report = ctx.queue_manager.batch_preflight([chosen])
    assert report["items"] == 1
    assert report["total_bytes"] == SIZE
    assert report["folder_id"] == "fld_target"


def test_preflight_refuses_when_drive_is_not_connected(ctx, monkeypatch):
    class _On:
        authorized = True
        client = None

    monkeypatch.setattr(ctx, "telegram_auth", _On(), raising=False)
    monkeypatch.setattr(ctx, "drive_auth", None, raising=False)
    with pytest.raises(DriveNotReadyError):
        ctx.queue_manager.batch_preflight([])


# ------------------------------------------------------- queue controls


def test_resume_clears_the_pause_gate_on_the_owned_manager(ctx):
    ctx.drive_client = FakeDrive()
    manager = ctx.ensure_transfer_manager("fld")
    manager.pause()
    assert not manager._paused.is_set()
    snapshot = ctx.queue_manager.resume()
    assert manager._paused.is_set(), "queue.resume must release the manager gate"
    assert snapshot["status"] == "running"


def test_stop_sets_the_manager_stop_flag_and_reports_stopped(ctx):
    ctx.drive_client = FakeDrive()
    manager = ctx.ensure_transfer_manager("fld")
    snapshot = ctx.queue_manager.stop()
    assert manager._stop.is_set(), "queue.stop must signal the manager"
    assert snapshot["status"] == "stopped"


def test_pause_item_and_resume_item_only_touch_that_item(ctx):
    ctx.drive_client = FakeDrive()
    manager = ctx.ensure_transfer_manager("fld")
    one = _item(ctx.queue_manager, 30)
    other = _item(ctx.queue_manager, 31)

    ctx.queue_manager.pause_item(one.id)
    assert manager.item_paused(one.id)
    assert not manager.item_paused(other.id)
    # A Pending item is not in flight, so the row stays Pending by design
    # (state_machine has no Pending -> Paused edge); the manager flag is what
    # holds the item back.
    assert db.get_item(one.id).state == "Pending"

    ctx.queue_manager.resume_item(one.id)
    assert not manager.item_paused(one.id)
    assert db.get_item(one.id).state == "Pending"


def test_pause_item_marks_an_in_flight_item_paused(ctx):
    ctx.drive_client = FakeDrive()
    manager = ctx.ensure_transfer_manager("fld")
    item = _item(ctx.queue_manager, 40)
    ctx.queue_manager.try_transition(item.id, "Downloading")
    ctx.queue_manager.pause_item(item.id)
    assert manager.item_paused(item.id)
    assert db.get_item(item.id).state == "Paused"
    ctx.queue_manager.resume_item(item.id)
    assert db.get_item(item.id).state == "Pending"



def test_stop_item_is_permanent_for_that_item(ctx):
    ctx.drive_client = FakeDrive()
    manager = ctx.ensure_transfer_manager("fld")
    item = _item(ctx.queue_manager, 32)
    ctx.queue_manager.stop_item(item.id)
    assert manager.item_stopped(item.id)
    assert db.get_item(item.id).state == "Stopped"

    ctx.queue_manager.retry_item(item.id)
    assert db.get_item(item.id).state == "Stopped", "Stopped must never be revived"


def test_retry_item_returns_a_failed_item_to_pending(ctx):
    item = _item(ctx.queue_manager, 33)
    ctx.queue_manager.try_transition(item.id, "Downloading")
    ctx.queue_manager.try_transition(item.id, "Failed")
    ctx.queue_manager.retry_item(item.id)
    assert db.get_item(item.id).state == "Pending"


def test_stopped_item_is_skipped_by_the_drain_loop():
    queue = QueueManager()
    running = _item(queue, 34)
    stopped = _item(queue, 35)
    mgr = TransferManager(_telegram(34, 35), FakeDrive(), "fld_target", queue=queue)
    mgr.stop_item(stopped.id)
    asyncio.run(mgr.run())
    assert db.get_item(running.id).state == "Uploaded"
    assert db.get_item(stopped.id).state != "Uploaded"


def test_clear_completed_removes_finished_rows_only(ctx):
    done = _item(ctx.queue_manager, 36)
    pending = _item(ctx.queue_manager, 37)
    for state in ("Downloading", "Downloaded", "Uploading", "Verifying",
                  "UploadedPendingCheckpoint", "Uploaded"):
        ctx.queue_manager.try_transition(done.id, state)
    assert db.get_item(done.id).state == "Uploaded"

    result = ctx.queue_manager.clear_completed_metadata()
    assert result["removed"] >= 1
    assert db.get_item(done.id) is None
    assert db.get_item(pending.id) is not None, "pending work must survive"


def test_refresh_snapshot_reports_live_counts(ctx):
    _item(ctx.queue_manager, 38)
    _item(ctx.queue_manager, 39)
    snapshot = ctx.queue_manager.snapshot()
    assert snapshot["pending"] == 2
    assert snapshot["counts"].get("Pending") == 2
    assert "status" in snapshot
