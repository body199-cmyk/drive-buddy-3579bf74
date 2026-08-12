"""Proof for flow.sync (M20-T03) and for the step machine in flow.py."""
from __future__ import annotations

import pytest

from teledrive import drive_auth, telegram_auth
from teledrive.flow import STEP_ORDER, FlowService
from teledrive.models import MediaItem

PROVES = ("flow.sync",)


def _telegram_ready(ctx):
    """Drive the REAL state machine, not a fake attribute.

    ``TelegramAuth.authorized`` and ``DriveAuth.connected`` are read-only
    properties derived from the live state, so a test may only reach them by
    setting the state they read — which is exactly what FlowService trusts.
    """
    ctx.telegram_auth.state = telegram_auth.AUTHORIZED


def _drive_ready(ctx):
    ctx.drive_auth.service = object()
    ctx.drive_auth.state = drive_auth.CONNECTED


def _connect(ctx, folder_id="folder-1"):
    _telegram_ready(ctx)
    _drive_ready(ctx)
    ctx.config.drive_folder_id = folder_id


def _item(item_id="a", size=10):
    return MediaItem(
        id=item_id, size_bytes=size, media_type="video", safe_name=f"{item_id}.mp4",
    )


def test_step_is_connect_until_all_three_connections_are_real(ctx):
    service = FlowService(ctx)
    assert service.state().step == "connect"
    _telegram_ready(ctx)
    assert service.state().step == "connect"
    _drive_ready(ctx)
    assert service.state().step == "connect", "a missing folder must not unlock step 2"
    ctx.config.drive_folder_id = "folder-1"
    assert service.state().step == "analyze"


def test_step_advances_to_select_once_candidates_exist(ctx):
    _connect(ctx)
    ctx.selection.set_candidates([_item()])
    assert FlowService(ctx).state().step == "select"


def test_step_advances_to_queue_once_something_is_selected(ctx):
    _connect(ctx)
    ctx.selection.set_candidates([_item()])
    ctx.selection.select_all_visible()
    state = FlowService(ctx).state()
    assert state.step == "queue"
    assert state.selected == 1
    assert state.selected_bytes == 10


def test_flow_sync_reads_live_context_state(ctx):
    """flow.sync must return 12 updates derived from the live context only."""
    _connect(ctx)
    handler = ctx.handlers.h_flow_sync
    assert handler.action_id == "flow.sync"
    assert handler.service_path == "flow.state"
    updates = handler()
    assert isinstance(updates, tuple)
    assert len(updates) == 12, "flow_outputs in ui.py declares exactly 12 outputs"


def test_flow_sync_reveals_step_two_only_after_a_real_connection(ctx):
    """The reveal is derived, never optimistic: index 3 is step2_group."""
    before = ctx.handlers.h_flow_sync()
    assert before[3]["visible"] is False
    _connect(ctx)
    after = ctx.handlers.h_flow_sync()
    assert after[3]["visible"] is True
    # ... and it disappears again the moment Drive drops.
    ctx.drive_auth.state = drive_auth.DISCONNECTED
    assert ctx.handlers.h_flow_sync()[3]["visible"] is False


def test_flow_state_never_raises_on_a_bare_context(ctx):
    state = FlowService(ctx).state()
    assert state.analyzed == 0
    assert state.queued == 0
    assert state.running is False


def test_step_order_is_the_five_documented_steps():
    assert STEP_ORDER == ("connect", "analyze", "select", "queue", "monitor")
