"""Proof tests for analyze.select_all and analyze.clear_selection (M13-T03)."""
from __future__ import annotations

import pytest
from teledrive import action_registry
from teledrive.errors import TeleDriveError
from teledrive.i18n import t
from teledrive.models import MediaItem
from teledrive.services import candidate_rows_for, rows_for

PROVES = (
    "analyze.select_all",
    "analyze.clear_selection",
)


def _make_item(
    id_val: str,
    media_type: str = "photo",
    extension: str = "jpg",
    size_bytes: int = 1000,
) -> MediaItem:
    return MediaItem(
        id=id_val,
        original_name=f"{id_val}.{extension}",
        safe_name=f"{id_val}.{extension}",
        media_type=media_type,
        extension=extension,
        size_bytes=size_bytes,
    )


def test_select_all_visible_only(ctx):
    item1 = _make_item("id-1", media_type="photo")
    item2 = _make_item("id-2", media_type="video")
    item3 = _make_item("id-3", media_type="photo")

    ctx.selection.set_candidates([item1, item2, item3])
    ctx.selection.apply_filters(media_types=["photo"])

    visible = ctx.selection.visible()
    assert len(visible) == 2
    assert {i.id for i in visible} == {"id-1", "id-3"}

    summary, rows, preview, enqueue_update, _groups = ctx.handlers.h_analyze_select_all()

    assert ctx.selection.selected_ids == {"id-1", "id-3"}
    assert "id-2" not in ctx.selection.selected_ids
    assert summary == f"{t('btn.select_all')}: 2"
    assert rows == candidate_rows_for(visible, ctx.selection.selected_ids)
    assert len(rows) == 2
    assert rows[0][0] == "☑"  # selection marker is table value, not a button
    # live gating: enabled only when selection AND a target folder exist
    assert enqueue_update.get("interactive") is False
    from teledrive import database as db
    db.set_setting("drive_folder_id", "folder-1")
    db.set_setting("drive_folder_name", "Target")
    ctx.config.drive_folder_id = "folder-1"
    _s2, _r2, _p2, enqueue_update2, _g2 = ctx.handlers.h_analyze_select_all()
    assert enqueue_update2.get("interactive") is True


def test_clear_selection_preserves_items_and_visible_rows(ctx):
    item1 = _make_item("id-1", media_type="photo")
    item2 = _make_item("id-2", media_type="video")
    item3 = _make_item("id-3", media_type="photo")

    ctx.selection.set_candidates([item1, item2, item3])
    ctx.selection.apply_filters(media_types=["photo"])
    ctx.selection.select_all_visible()
    assert ctx.selection.selected_ids == {"id-1", "id-3"}

    before_candidates = list(ctx.selection.candidates)
    before_visible = list(ctx.selection.visible())
    before_rows = candidate_rows_for(before_visible, {"id-1", "id-3"})

    summary, rows, preview, enqueue_update, _groups = ctx.handlers.h_analyze_clear_selection()

    assert ctx.selection.selected_ids == set()
    assert ctx.selection.candidates == before_candidates
    assert ctx.selection.visible() == before_visible
    assert summary == f"{t('btn.clear_selection')}: 0"
    # same candidates are still shown; only the selection markers cleared
    assert [r[1:] for r in rows] == [r[1:] for r in before_rows]
    assert all(r[0] == "☐" for r in rows)
    assert len(rows) == len(before_visible)
    assert enqueue_update.get("interactive") is False


def test_select_all_and_clear_resolve_through_ctx(ctx, monkeypatch):
    for action_id in ("analyze.select_all", "analyze.clear_selection"):
        spec = action_registry.get(action_id)
        assert spec is not None
        assert callable(ctx.resolve(spec.service_path))

    resolved_paths = []
    orig_resolve = ctx.resolve

    def spy_resolve(path):
        resolved_paths.append(path)
        return orig_resolve(path)

    monkeypatch.setattr(ctx, "resolve", spy_resolve)

    calls_select = []
    orig_select_all = ctx.selection.select_all_visible

    def spy_select_all(*args, **kwargs):
        calls_select.append(("select_all_visible", args, kwargs))
        return orig_select_all(*args, **kwargs)

    monkeypatch.setattr(ctx.selection, "select_all_visible", spy_select_all)

    calls_clear = []
    orig_clear = ctx.selection.clear

    def spy_clear(*args, **kwargs):
        calls_clear.append(("clear", args, kwargs))
        return orig_clear(*args, **kwargs)

    monkeypatch.setattr(ctx.selection, "clear", spy_clear)

    ctx.handlers.h_analyze_select_all()
    assert "selection.select_all_visible" in resolved_paths
    assert len(calls_select) == 1

    resolved_paths.clear()

    ctx.handlers.h_analyze_clear_selection()
    assert "selection.clear" in resolved_paths
    assert len(calls_clear) == 1


def test_error_path_arity_and_redaction(ctx, monkeypatch):
    def boom_runtime(*args, **kwargs):
        raise RuntimeError("api_hash=SECRET_API_HASH_99999 database failure")

    monkeypatch.setattr(ctx.selection, "select_all_visible", boom_runtime)
    result = ctx.handlers.h_analyze_select_all()
    assert isinstance(result, tuple)
    assert len(result) == 5
    assert "SECRET_API_HASH_99999" not in str(result)
    assert "Traceback" not in str(result)

    def boom_teledrive(*args, **kwargs):
        raise TeleDriveError("api_hash=SECRET_API_HASH_88888 failed", "err.unknown")

    monkeypatch.setattr(ctx.selection, "clear", boom_teledrive)
    result = ctx.handlers.h_analyze_clear_selection()
    assert isinstance(result, tuple)
    assert len(result) == 5
    assert "SECRET_API_HASH_88888" not in str(result)
    assert "Traceback" not in str(result)


def test_select_all_and_clear_empty_candidates(ctx):
    ctx.selection.set_candidates([])

    summary, rows, preview, enqueue_update, _groups = ctx.handlers.h_analyze_select_all()
    assert ctx.selection.selected_ids == set()
    assert summary == f"{t('btn.select_all')}: 0"
    assert rows == []
    assert enqueue_update.get("interactive") is False

    summary, rows, preview, enqueue_update, _groups = ctx.handlers.h_analyze_clear_selection()
    assert ctx.selection.selected_ids == set()
    assert summary == f"{t('btn.clear_selection')}: 0"
    assert rows == []
