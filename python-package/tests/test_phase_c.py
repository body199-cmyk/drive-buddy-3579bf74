"""PHASE C proofs: one context, no singletons, real queue semantics.

PROVES = (
    "queue.start_selected",
    "queue.pause",
    "queue.retry_failed",
)
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest

from teledrive import database as db
from teledrive.errors import DriveNotReadyError, TelegramNotReadyError
from teledrive.models import MediaItem
from teledrive.queue_manager import QueueManager
from teledrive.state_machine import can_transition as can
from teledrive.transfer_manager import TransferManager

from .mocks.fake_drive import FakeDrive
from .mocks.fake_telegram import FakeDoc, FakeMsg, FakeTelegram

PROVES = ("queue.start_selected", "queue.pause", "queue.retry_failed")

SIZE = 1024
PKG = Path(__file__).resolve().parents[1] / "teledrive"


def _item(queue: QueueManager, mid: int) -> MediaItem:
    item = MediaItem(
        source_key=f"tg:42:{mid}",
        chat_id=42,
        message_id=mid,
        original_name=f"c{mid}.bin",
        safe_name=f"c{mid}.bin",
        media_type="document",
        extension="bin",
        size_bytes=SIZE,
    )
    queue.enqueue(item)
    return item


def _telegram(*mids: int) -> FakeTelegram:
    return FakeTelegram({m: FakeMsg(id=m, document=FakeDoc(id="d", size=SIZE)) for m in mids})


# --------------------------------------------------------- no singletons


def test_no_module_level_queue_singleton():
    import teledrive.queue_manager as qm

    assert not hasattr(qm, "QUEUE"), "the QUEUE singleton must not come back"


def test_package_never_imports_a_queue_singleton():
    bad = re.compile(r"import\s+QUEUE\b|\bQUEUE\s*=")
    for path in PKG.glob("*.py"):
        assert not bad.search(path.read_text(encoding="utf-8")), path.name


def test_two_queue_managers_do_not_share_runtime_state():
    a, b = QueueManager(), QueueManager()
    a._status = "running"
    assert b.status_label() != "running"
    assert a is not b


def test_context_owns_one_queue_and_one_transfer_manager(ctx):
    assert ctx.queue_manager.ctx is ctx
    ctx.drive_client = FakeDrive()
    first = ctx.ensure_transfer_manager("fld_target")
    second = ctx.ensure_transfer_manager("fld_target")
    assert first is second
    assert first.queue is ctx.queue_manager


# ------------------------------------------------------------- preflight


def test_preflight_refuses_without_telegram(ctx):
    with pytest.raises(TelegramNotReadyError):
        ctx.queue_manager.batch_preflight([_item(ctx.queue_manager, 1)])


def test_preflight_refuses_without_drive(ctx):
    from teledrive.telegram_auth import AUTHORIZED

    ctx.telegram_auth.state = AUTHORIZED
    with pytest.raises(DriveNotReadyError):
        ctx.queue_manager.batch_preflight([_item(ctx.queue_manager, 2)])


def test_unbound_queue_manager_raises_instead_of_guessing():
    with pytest.raises(RuntimeError):
        QueueManager().batch_preflight([])


# ------------------------------------------------------------ selection


def test_start_selected_never_processes_the_whole_table():
    queue = QueueManager()
    wanted = _item(queue, 3)
    _item(queue, 4)
    picked = queue.selected_pending([wanted.id])
    assert [i.id for i in picked] == [wanted.id]


def test_empty_selection_starts_nothing(ctx):
    _item(ctx.queue_manager, 5)
    result = ctx.queue_manager.start_selected([])
    assert result["started"] == 0
    assert result["status"] == "idle"


def test_transfer_manager_scope_excludes_unselected_items():
    queue = QueueManager()
    chosen = _item(queue, 6)
    other = _item(queue, 7)
    mgr = TransferManager(_telegram(6, 7), FakeDrive(), "fld_target", queue=queue)
    mgr.set_scope([chosen.id])
    assert mgr.in_scope(chosen.id)
    assert not mgr.in_scope(other.id)

    asyncio.run(mgr.run())
    assert db.get_item(chosen.id).state == "Uploaded"
    assert db.get_item(other.id).state == "Pending"


# ------------------------------------------------------------ drain loop


def test_run_drains_items_enqueued_after_the_run_started():
    queue = QueueManager()
    first = _item(queue, 8)
    mgr = TransferManager(_telegram(8, 9), FakeDrive(), "fld_target", queue=queue)

    async def drive_it():
        task = asyncio.create_task(mgr.run())
        await asyncio.sleep(0)
        later = _item(queue, 9)
        await task
        return later

    later = asyncio.run(drive_it())
    assert db.get_item(first.id).state == "Uploaded"
    assert db.get_item(later.id).state == "Uploaded", "the drain loop must pick up late work"


# ------------------------------------------------------ stopped is final


def test_stopped_is_terminal():
    assert can("Stopped", "Deleted")
    for target in ("Pending", "Downloading", "Uploading", "Uploaded"):
        assert not can("Stopped", target), f"Stopped must never go to {target}"


def test_retry_failed_never_revives_a_stopped_item():
    queue = QueueManager()
    stopped = _item(queue, 10)
    queue.try_transition(stopped.id, "Stopped")
    failed = _item(queue, 11)
    queue.try_transition(failed.id, "Downloading")
    queue.try_transition(failed.id, "Failed")

    queue.retry_failed()
    assert db.get_item(stopped.id).state == "Stopped"
    assert db.get_item(failed.id).state == "Pending"


# ----------------------------------------------------- pause checkpoints


def test_pause_exports_a_checkpoint_before_reporting_paused(ctx):
    _item(ctx.queue_manager, 12)
    snapshot = ctx.queue_manager.pause()
    assert snapshot["status"] == "paused"
    assert snapshot["checkpoint"]["local"], "pause must write a local checkpoint"
    assert Path(snapshot["checkpoint"]["local"]).exists()
    assert any(e["kind"] == "checkpoint" for e in db.recent_events(50))
