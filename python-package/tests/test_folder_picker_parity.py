"""The three Drive destination panels are one renderer and one action contract."""
from __future__ import annotations

import pytest

gr = pytest.importorskip("gradio")

from teledrive import ui
from teledrive.handlers import ERROR_ARITY
from teledrive.i18n import t


def _render(ctx):
    with gr.Blocks():
        return ui._render_shell(ctx, ctx.binder, gr.State("en"), "en")


def test_all_three_suffixes_are_rendered_and_exported_as_refs(ctx):
    refs = _render(ctx)
    pickers = [refs["folder_dash"], refs["folder_settings"], refs["folder_conn"]]
    assert [p["suffix"] for p in pickers] == ["dash", "settings", "conn"]
    for picker in pickers:
        assert set(picker) >= {"choice", "current", "message", "list_btn", "create_btn", "select_btn"}


def test_every_picker_uses_the_same_named_drive_handlers(ctx):
    _render(ctx)
    assert len(ctx.binder.wired["drive.list_folders"]) == 3
    assert len(ctx.binder.wired["drive.create_folder"]) == 3
    assert len(ctx.binder.wired["drive.select_folder"]) == 3


def test_create_and_select_have_the_three_output_sync_contract(ctx):
    _render(ctx)
    assert ERROR_ARITY["drive.create_folder"] == 3
    assert ERROR_ARITY["drive.select_folder"] == 3
    for record in ctx.binder.wired["drive.create_folder"] + ctx.binder.wired["drive.select_folder"]:
        assert record.handler_name in {"h_drive_create_folder", "h_drive_select_folder"}


def test_disconnected_drive_is_visible_but_not_interactive_with_a_reason(ctx):
    refs = _render(ctx)
    for picker in (refs["folder_dash"], refs["folder_settings"], refs["folder_conn"]):
        assert picker["message"].value == t("err.drive_not_ready")
        for key in ("parent_id", "choice", "new_name", "list_btn", "create_btn", "select_btn"):
            assert picker[key].interactive is False


def test_current_folder_is_id_authoritative_and_name_is_display_only(ctx):
    ctx.config.drive_folder_id = "folder-id-42"
    # No cached name means the safe ID fallback is rendered uniformly.
    refs = _render(ctx)
    assert all(p["current"].value == "folder-id-42" for p in (
        refs["folder_dash"], refs["folder_settings"], refs["folder_conn"],
    ))
