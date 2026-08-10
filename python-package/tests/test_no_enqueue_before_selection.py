"""DOC-39 (M18-T01) §5.3 + §7 — no enqueue before explicit selection.

Proves the safety rails of the selection stage:
* analyze NEVER enqueues automatically and never auto-selects
* no Telegram download and no transfer start before the explicit enqueue
* selection operations are pure in-memory state changes
"""
from __future__ import annotations

import pytest
from types import SimpleNamespace

from teledrive import telegram_auth as ta
from teledrive.models import MediaItem

PROVES = ()  # selection/analyze actions proven in their own files


class _Msg:
    def __init__(self, mid, media_type="document", size=1000):
        self.id = mid
        self.date = "2026-01-01T00:00:00+00:00"
        self.media = object()
        self.grouped_id = None
        self.photo = None
        self.video = None
        self.audio = None
        self.voice = None
        self.sticker = None
        self.animation = None
        self.document = None
        if media_type == "video":
            self.video = SimpleNamespace(
                id=f"v{mid}", file_unique_id=f"v{mid}", size=size,
                mime_type="video/mp4",
                attributes=[SimpleNamespace(file_name=f"v{mid}.mp4")],
            )
        else:
            self.document = SimpleNamespace(
                id=f"d{mid}", file_unique_id=f"d{mid}", size=size,
                mime_type="application/pdf",
                attributes=[SimpleNamespace(file_name=f"d{mid}.pdf")],
            )


class _Entity:
    id = 12345
    title = "TestChat"
    username = "testchat"


class _Telegram:
    """Fake Telegram that records every read; has NO download capability."""

    def __init__(self, messages):
        self.messages = list(messages)
        self.entity_calls = 0
        self.iter_calls = 0
        self.download_calls = 0

    async def get_entity(self, chat):
        self.entity_calls += 1
        return _Entity()

    async def iter_messages(self, chat, limit=None, min_id=None, max_id=None, reverse=False):
        self.iter_calls += 1
        for msg in self.messages[: int(limit or 10)]:
            yield msg

    async def get_message(self, chat, message_id):
        for msg in self.messages:
            if msg.id == int(message_id):
                return msg
        return None

    # If any code path tried to download before enqueue, this would raise —
    # the fake has no download surface at all.
    def download_media(self, *a, **k):  # pragma: no cover - must never be called
        self.download_calls += 1
        raise AssertionError("download_media called before explicit enqueue")


def _authorized_telegram(ctx, telegram):
    ctx.telegram_auth.state = ta.AUTHORIZED
    ctx.telegram_auth.client = telegram


def test_analyze_never_enqueues_and_never_auto_selects(ctx):
    tg = _Telegram([_Msg(1), _Msg(2), _Msg(3)])
    _authorized_telegram(ctx, tg)

    result = ctx.scanner.analyze(
        "https://t.me/testchat/1", mode="range", start_id=1, end_id=3,
        media_types=["all"],
    )
    assert result.total == 3
    # candidates exist, but NOTHING is selected and NOTHING is queued
    assert len(ctx.selection.candidates) == 3
    assert ctx.selection.selected_ids == set()
    assert ctx.handlers.queue_rows() == []
    assert tg.download_calls == 0
    assert ctx.queue_manager.status_label() == "idle"


def test_analyze_handler_does_not_touch_queue_or_telegram_downloads(ctx):
    tg = _Telegram([_Msg(1), _Msg(2)])
    _authorized_telegram(ctx, tg)

    enqueue_hits = []
    original = ctx.queue_manager.bulk_enqueue
    ctx.queue_manager.bulk_enqueue = lambda items: enqueue_hits.append(items) or original(items)  # type: ignore[method-assign]

    summary, rows, preview, enqueue_update, _groups = ctx.handlers.h_analyze_run(
        "https://t.me/testchat", "latest", None, None, None, 2, ["all"]
    )
    assert summary.startswith("2 ·")
    assert enqueue_hits == []
    assert tg.download_calls == 0
    assert enqueue_update.get("interactive") is False  # nothing selected yet
    assert all(r[0] == "☐" for r in rows)


def test_selection_ops_are_pure_in_memory(ctx):
    """Selecting rows must not create downloads, queue rows or Drive calls."""
    tg = _Telegram([_Msg(1)])
    _authorized_telegram(ctx, tg)
    ctx.scanner.analyze("https://t.me/testchat", mode="message", message_id=1,
                        media_types=["all"])

    queue_before = ctx.handlers.queue_rows()
    ctx.selection.select_all_visible()
    ctx.selection.toggle_by_index(0)  # on then off
    ctx.selection.select_range(1, 1)
    ctx.selection.select_group_by_chat(12345)
    ctx.selection.clear()

    assert ctx.handlers.queue_rows() == queue_before  # queue untouched
    assert tg.download_calls == 0
    assert ctx.queue_manager._future is None  # transfers never started
    assert ctx.queue_manager.status_label() == "idle"


def test_enqueue_is_the_only_gate_that_creates_queue_rows(ctx):
    tg = _Telegram([_Msg(1), _Msg(2)])
    _authorized_telegram(ctx, tg)
    ctx.scanner.analyze("https://t.me/testchat", mode="range", start_id=1, end_id=2,
                        media_types=["all"])

    # selection alone: no queue rows
    ctx.selection.select_all_visible()
    assert ctx.handlers.queue_rows() == []

    # enqueue without a folder: refused, no queue rows
    from teledrive.errors import TeleDriveError
    with pytest.raises(TeleDriveError) as exc:
        ctx.selection.enqueue_selected()
    assert exc.value.message_key == "err.no_folder"
    assert ctx.handlers.queue_rows() == []

    # enqueue with a folder: queue rows appear, but no transfer starts
    from teledrive import database as db
    db.set_setting("drive_folder_id", "folder-1")
    db.set_setting("drive_folder_name", "Target")
    ctx.config.drive_folder_id = "folder-1"
    ctx.selection.enqueue_selected()
    assert len(ctx.handlers.queue_rows()) == 2
    assert tg.download_calls == 0
    assert ctx.queue_manager._future is None
    assert ctx.queue_manager.status_label() == "idle"
    # the queue rows are Pending — nothing downloaded or uploaded
    assert all(row[4] == "بانتظار" or "Pending" in str(row) for row in ctx.handlers.queue_rows())
    ctx.config.drive_folder_id = None  # process-shared CONFIG: clean up
