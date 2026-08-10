"""DOC-39 (M18-T01) §5 — file selection flow before transfer.

Proves the real selection stage:
* select all / clear all (visible-only, live gating)
* manual individual row selection (row-based toggle, not filename-based)
* range from/to with validation and the declared 1000-message cap
* group selection (chat grouping the source supports today)
* count + total size preview
* enqueue refuses empty selection / missing folder / bad space
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from teledrive import action_registry
from teledrive.errors import TeleDriveError
from teledrive.i18n import t
from teledrive.models import MediaItem
from teledrive.services import candidate_rows_for
from teledrive.utils import human_bytes

PROVES = (
    "analyze.toggle_row",
    "analyze.select_range",
    "analyze.select_group",
)


def _item(
    id_val: str,
    *,
    message_id: int = 1,
    chat_id: int = 100,
    chat_title: str = "Channel A",
    media_type: str = "photo",
    size_bytes: int = 1000,
) -> MediaItem:
    return MediaItem(
        id=id_val,
        source_key=f"tg:{chat_id}:{message_id}:{id_val}",
        chat_id=chat_id,
        chat_title=chat_title,
        message_id=message_id,
        file_unique_id=id_val,
        original_name=f"{id_val}.jpg",
        safe_name=f"{id_val}.jpg",
        media_type=media_type,
        extension="jpg",
        size_bytes=size_bytes,
    )


def _three_chats(ctx) -> list[MediaItem]:
    items = [
        _item("a1", message_id=1, chat_id=100, chat_title="Channel A", size_bytes=100),
        _item("a2", message_id=2, chat_id=100, chat_title="Channel A", size_bytes=200),
        _item("a3", message_id=3, chat_id=100, chat_title="Channel A", size_bytes=300),
        _item("b1", message_id=10, chat_id=200, chat_title="Saved Msgs", size_bytes=500),
        _item("b2", message_id=11, chat_id=200, chat_title="Saved Msgs", size_bytes=700),
    ]
    ctx.selection.set_candidates(items)
    return items


# ---------------------------------------------------------------------------
# select all / clear all (extended proof on top of tests/test_selection.py)
# ---------------------------------------------------------------------------

def test_select_all_then_clear_all_updates_count_and_gating(ctx):
    _three_chats(ctx)
    ctx.selection.select_all_visible()
    summary = ctx.selection.summary()
    assert summary["count"] == 5
    assert summary["total_bytes"] == 1800

    ctx.selection.clear()
    assert ctx.selection.summary()["count"] == 0


# ---------------------------------------------------------------------------
# manual individual selection — row-based, never filename-based
# ---------------------------------------------------------------------------

def test_manual_row_toggle_updates_selection(ctx):
    """Clicking table row N toggles the Nth visible candidate (DOC-39 §5.1)."""
    _three_chats(ctx)
    handler = ctx.handlers.h_analyze_toggle_row
    assert handler.action_id == "analyze.toggle_row"

    # a valid target folder lets the enqueue gate open with a selection
    from teledrive import database as db
    db.set_setting("drive_folder_id", "folder-1")
    db.set_setting("drive_folder_name", "Target")
    ctx.config.drive_folder_id = "folder-1"

    # toggle row 0 (a1) on
    result = handler(SimpleNamespace(index=(0, 0), value="☐"))
    assert ctx.selection.selected_ids == {"a1"}
    assert result[0] == f"{t('btn.toggle_row')}: 1"
    rows = result[1]
    assert rows[0][0] == "☑" and rows[1][0] == "☐"
    # preview shows count + size + folder
    assert t("sel.count") in result[2] and "1" in result[2].split("·")[0]
    # enqueue gate opens as soon as something is selected AND a folder exists
    assert result[3].get("interactive") is True
    ctx.config.drive_folder_id = None

    # toggle the same row again (off)
    result = handler(SimpleNamespace(index=(0, 0), value="☑"))
    assert ctx.selection.selected_ids == set()
    assert result[0] == f"{t('btn.toggle_row')}: 0"
    assert result[3].get("interactive") is False

    # manual selection is by row, not by filename: two items may share a name,
    # toggling the row still flips exactly that candidate.
    dup = _item("dup1", message_id=50, chat_id=100, chat_title="Channel A")
    dup2 = _item("dup2", message_id=51, chat_id=100, chat_title="Channel A")
    ctx.selection.set_candidates([dup, dup2])
    handler(SimpleNamespace(index=(1, 0), value="☐"))
    assert ctx.selection.selected_ids == {"dup2"}


def test_toggle_row_out_of_bounds_returns_localized_error(ctx):
    _three_chats(ctx)
    result = ctx.handlers.h_analyze_toggle_row(SimpleNamespace(index=(99, 0), value="☐"))
    assert len(result) == 5
    assert t("err.bad_scan_request") in result[0]


# ---------------------------------------------------------------------------
# range from/to — validation + declared cap
# ---------------------------------------------------------------------------

def test_range_from_to_valid_invalid_and_cap(ctx):
    """Proof test for analyze.select_range (registry proof_test target)."""
    _three_chats(ctx)
    handler = ctx.handlers.h_analyze_select_range
    assert handler.action_id == "analyze.select_range"

    from teledrive import database as db
    db.set_setting("drive_folder_id", "folder-1")
    ctx.config.drive_folder_id = "folder-1"

    # valid range selects only candidates inside [start, end]
    result = handler(2, 10)
    assert ctx.selection.selected_ids == {"a2", "a3", "b1"}
    assert result[0] == f"{t('btn.select_range')}: 3"
    markers = {r[0] for r in result[1]}
    assert markers == {"☑", "☐"}
    assert result[3].get("interactive") is True
    ctx.config.drive_folder_id = None

    # range REPLACES the selection (predictable from/to semantics)
    result = handler(11, 11)
    assert ctx.selection.selected_ids == {"b2"}

    # invalid: end before start -> localized refusal, selection untouched
    result = handler(10, 2)
    assert t("err.selection_range_invalid") in result[0]
    assert ctx.selection.selected_ids == {"b2"}

    # invalid: non-numeric ids -> localized refusal
    result = handler("abc", 5)
    assert t("err.selection_range_invalid") in result[0]

    # invalid: non-positive ids
    result = handler(0, 5)
    assert t("err.selection_range_invalid") in result[0]

    # declared cap: ranges wider than 1000 messages are refused
    result = handler(1, 2000)
    assert t("err.selection_range_too_large") in result[0]
    assert ctx.selection.selected_ids == {"b2"}

    # service-level refusal raises the typed error with the same keys
    with pytest.raises(TeleDriveError) as exc:
        ctx.selection.select_range(5, 2)
    assert exc.value.message_key == "err.selection_range_invalid"
    with pytest.raises(TeleDriveError) as exc:
        ctx.selection.select_range(1, 1001)
    assert exc.value.message_key == "err.selection_range_too_large"


def test_range_with_no_matching_candidates_selects_nothing(ctx):
    _three_chats(ctx)
    result = ctx.handlers.h_analyze_select_range(1000, 1001)
    assert result[0] == f"{t('btn.select_range')}: 0"
    assert ctx.selection.selected_ids == set()
    assert result[3].get("interactive") is False


# ---------------------------------------------------------------------------
# group selection — the grouping the source supports today (chat)
# ---------------------------------------------------------------------------

def test_group_selection_selects_all_in_chat(ctx):
    """Proof test for analyze.select_group (registry proof_test target)."""
    _three_chats(ctx)
    handler = ctx.handlers.h_analyze_select_group
    assert handler.action_id == "analyze.select_group"

    # group choices are derived from the visible candidates, never fabricated
    _, _rows, _preview, _enqueue, group_update = ctx.handlers.h_analyze_select_all()
    assert group_update["choices"] == [("Channel A", "100"), ("Saved Msgs", "200")]

    result = handler("Channel A :: 100")
    assert ctx.selection.selected_ids == {"a1", "a2", "a3"}
    assert result[0] == f"{t('btn.select_group')}: 3"
    assert all(r[0] == "☑" for r in result[1][:3])

    # switching group replaces the selection
    result = handler("Saved Msgs :: 200")
    assert ctx.selection.selected_ids == {"b1", "b2"}

    # unknown group -> no match, selection becomes empty (replace semantics)
    result = handler("Nowhere :: 999")
    assert result[0] == f"{t('btn.select_group')}: 0"
    assert ctx.selection.selected_ids == set()


def test_group_choices_empty_when_no_candidates(ctx):
    _three_chats(ctx)
    ctx.selection.clear()
    ctx.selection.set_candidates([])
    _summary, _rows, _preview, _enqueue, group_update = ctx.handlers.h_analyze_select_all()
    assert group_update["choices"] == []


# ---------------------------------------------------------------------------
# count + total size preview
# ---------------------------------------------------------------------------

def test_preview_shows_count_size_and_target_folder(ctx):
    from teledrive import database as db
    ctx.config.drive_folder_id = "folder-9"
    db.set_setting("drive_folder_id", "folder-9")
    db.set_setting("drive_folder_name", "Backups")

    _three_chats(ctx)
    ctx.selection.select_all_visible()
    result = ctx.handlers.h_analyze_select_all()

    preview = result[2]
    assert f"{t('sel.count')}: 5" in preview
    assert human_bytes(1800) in preview
    assert f"{t('sel.target_folder')}: Backups" in preview

    # no folder -> preview says so honestly
    from teledrive import database as db2
    db2.set_setting("drive_folder_id", "")
    ctx.config.drive_folder_id = None
    _summary, _rows, preview2, enqueue_update, _g = ctx.handlers.h_analyze_select_all()
    assert f"{t('sel.target_folder')}: {t('msg.no_folder_selected')}" in preview2
    assert enqueue_update.get("interactive") is False


# ---------------------------------------------------------------------------
# enqueue guards (DOC-39 §5.3)
# ---------------------------------------------------------------------------

def test_enqueue_refuses_empty_selection(ctx):
    ctx.selection.set_candidates([])
    with pytest.raises(TeleDriveError) as exc:
        ctx.selection.enqueue_selected()
    assert exc.value.message_key == "err.nothing_selected"

    result = ctx.handlers.h_analyze_enqueue_selected()
    assert len(result) == 5
    assert t("err.nothing_selected") in result[0]


def test_enqueue_refuses_missing_folder(ctx):
    _three_chats(ctx)
    ctx.selection.select_all_visible()
    # no folder selected anywhere
    ctx.config.drive_folder_id = None
    from teledrive import database as db
    db.set_setting("drive_folder_id", "")

    with pytest.raises(TeleDriveError) as exc:
        ctx.selection.enqueue_selected()
    assert exc.value.message_key == "err.no_folder"

    result = ctx.handlers.h_analyze_enqueue_selected()
    assert t("err.no_folder") in result[0]
    assert len(ctx.handlers.queue_rows()) == 0  # nothing reached the queue


def test_enqueue_succeeds_with_valid_folder_without_starting_transfers(ctx):
    _three_chats(ctx)
    ctx.selection.select_all_visible()
    from teledrive import database as db
    db.set_setting("drive_folder_id", "folder-9")
    db.set_setting("drive_folder_name", "Backups")
    ctx.config.drive_folder_id = "folder-9"

    items = ctx.selection.enqueue_selected()
    assert len(items) == 5
    queued = ctx.handlers.queue_rows()
    assert len(queued) == 5
    # enqueue is a local queue row — transfers have not started
    assert ctx.queue_manager._future is None
    assert ctx.queue_manager.status_label() == "idle"
    ctx.config.drive_folder_id = None  # process-shared CONFIG: clean up


def test_enqueue_refuses_insufficient_local_disk(ctx, monkeypatch):
    _three_chats(ctx)
    ctx.selection.select_all_visible()
    from teledrive import database as db
    db.set_setting("drive_folder_id", "folder-9")
    ctx.config.drive_folder_id = "folder-9"

    from teledrive import storage_manager
    monkeypatch.setattr(storage_manager, "preflight", lambda need: (False, 1))

    with pytest.raises(TeleDriveError) as exc:
        ctx.selection.enqueue_selected()
    assert exc.value.message_key == "err.disk_full"

    result = ctx.handlers.h_analyze_enqueue_selected()
    assert t("err.disk_full") in result[0]
    assert len(ctx.handlers.queue_rows()) == 0
    ctx.config.drive_folder_id = None  # process-shared CONFIG: clean up


def test_registry_entries_are_ready_and_resolve(ctx):
    for action_id in ("analyze.toggle_row", "analyze.select_range", "analyze.select_group"):
        spec = action_registry.get(action_id)
        assert spec is not None and spec.ready
        assert callable(ctx.resolve(spec.service_path))
