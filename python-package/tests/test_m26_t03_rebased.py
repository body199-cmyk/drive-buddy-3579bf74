"""M26-T03 rebased: regression coverage for gaps left after M26-T01.

These are local/fake contract tests. They do not prove live Telegram, Drive, or
Colab behaviour.
"""
from __future__ import annotations

import asyncio
import threading
from pathlib import Path

import pytest

from teledrive import database as db
from teledrive.errors import NothingSelectedError
from teledrive.models import MediaItem
from teledrive.progress_tracker import PROGRESS
from teledrive.queue_manager import QueueManager
from teledrive.transfer_manager import TransferManager
from teledrive import ui_binder


def _item(queue: QueueManager, suffix: str = "one") -> MediaItem:
    item = MediaItem(
        source_key=f"m26:{suffix}",
        chat_id=1,
        message_id=1,
        original_name="clip.bin",
        safe_name="clip.bin",
        media_type="document",
        extension="bin",
        size_bytes=10,
    )
    queue.enqueue(item)
    return item


def test_drive_calls_use_a_worker_thread():
    manager = TransferManager(None, None, "folder")
    caller_thread = threading.get_ident()

    async def probe():
        return await manager._drive_call(threading.get_ident)

    assert asyncio.run(probe()) != caller_thread


def test_item_control_sets_are_safe_across_threads():
    manager = TransferManager(None, None, "folder")
    done = threading.Event()

    def ui_thread():
        manager.pause_item("row-1")
        done.set()

    thread = threading.Thread(target=ui_thread, daemon=True)
    thread.start()
    assert done.wait(1.0)
    assert manager.item_paused("row-1")
    manager.stop_item("row-1")
    assert manager.item_stopped("row-1")
    assert not manager.item_paused("row-1")


def test_stop_fallback_parks_a_cancelled_worker_as_stopped():
    queue = QueueManager()
    item = _item(queue, "stalled")
    manager = TransferManager(None, None, "folder", queue=queue)

    async def blocked(_item):
        await asyncio.Event().wait()

    manager._do_item = blocked

    async def probe():
        task = asyncio.create_task(manager._process(item))
        manager._tasks = [task]
        await asyncio.sleep(0)
        manager.stop()
        manager.request_stop_cancel(0)
        with pytest.raises(asyncio.CancelledError):
            await task
        assert all(worker.done() for worker in manager._tasks)
        await asyncio.sleep(0)

    asyncio.run(probe())
    assert db.get_item(item.id).state == "Stopped"
    # A final Stopped row must not be revived by late cancellation cleanup.
    assert db.get_item(item.id).state == "Stopped"


def test_start_without_pending_raises_localized_typed_error(ctx):
    with pytest.raises(NothingSelectedError):
        ctx.queue_manager.start_selected()


def test_context_dashboard_uses_the_engine_progress_singleton(ctx):
    assert ctx.progress is PROGRESS
    PROGRESS.start_item("live", "live.bin", 100, phase="download")
    assert ctx.progress.snapshot()["active"][0]["id"] == "live"


def test_binder_supports_timer_tick():
    assert "tick" in ui_binder._EVENTS


def test_ui_does_not_attach_global_refresh_timer_to_the_whole_page():
    source = (Path(__file__).resolve().parents[1] / "teledrive" / "ui.py").read_text(
        encoding="utf-8"
    )
    assert "live_timer = gr.Timer(1.0)" not in source
    assert 'binder.wire(queue["refresh_q_btn"], "queue.refresh", [], q_out)' in source
    assert 'binder.wire(monitor["dash_btn"], "dashboard.refresh", [], [monitor["dashboard_json"]])' in source
