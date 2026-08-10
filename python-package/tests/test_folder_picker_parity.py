"""The four Drive destination panels are one renderer and one action contract.

DOC-39 (M18-T01) §4: the folder target lives inside transfers/dashboard as
well as settings and connection — all four panels share the SAME named
handlers, and create/select broadcast the ONE persisted folder truth to every
panel plus the top bar chip.
"""
from __future__ import annotations

import pytest

gr = pytest.importorskip("gradio")

from teledrive import ui
from teledrive.handlers import ERROR_ARITY
from teledrive.i18n import t


def _render(ctx):
    with gr.Blocks() as demo:
        refs = ui._render_shell(ctx, ctx.binder, gr.State("en"), "en")
    return demo, refs


def _wired_fns(demo):
    return [bf for bf in demo.fns.values() if getattr(bf.fn, "action_id", None)]


def test_all_four_suffixes_are_rendered_and_exported_as_refs(ctx):
    _demo, refs = _render(ctx)
    pickers = [
        refs["folder_dash"], refs["folder_transfer"],
        refs["folder_settings"], refs["folder_conn"],
    ]
    assert [p["suffix"] for p in pickers] == ["dash", "transfer", "settings", "conn"]
    for picker in pickers:
        assert set(picker) >= {"choice", "current", "message", "list_btn", "create_btn", "select_btn"}


def test_every_picker_uses_the_same_named_drive_handlers(ctx):
    _demo, _refs = _render(ctx)
    assert len(ctx.binder.wired["drive.list_folders"]) == 4
    assert len(ctx.binder.wired["drive.create_folder"]) == 4
    assert len(ctx.binder.wired["drive.select_folder"]) == 4


def test_create_and_select_have_the_broadcast_output_contract(ctx):
    """Each create/select wire carries the DOC-39 §4 broadcast: own panel
    (choice/current/message) + top chip + the other three panels' current +
    message = 10 outputs, identical for all four pickers."""
    demo, refs = _render(ctx)
    assert ERROR_ARITY["drive.create_folder"] == 10
    assert ERROR_ARITY["drive.select_folder"] == 10
    fns = _wired_fns(demo)
    folder_chip = refs["folder_chip"]
    for action_id in ("drive.create_folder", "drive.select_folder"):
        matches = [bf for bf in fns if bf.fn.action_id == action_id]
        assert len(matches) == 4
        for bf in matches:
            assert len(bf.outputs) == 10
            # every broadcast output set includes the top chip
            assert folder_chip in bf.outputs


def test_disconnected_drive_is_visible_but_not_interactive_with_a_reason(ctx):
    _demo, refs = _render(ctx)
    for picker in (refs["folder_dash"], refs["folder_transfer"],
                   refs["folder_settings"], refs["folder_conn"]):
        assert picker["message"].value == t("err.drive_not_ready")
        for key in ("parent_id", "choice", "new_name", "list_btn", "create_btn", "select_btn"):
            assert picker[key].interactive is False


def test_current_folder_is_id_authoritative_and_name_is_display_only(ctx):
    ctx.config.drive_folder_id = "folder-id-42"
    # No cached name means the safe ID fallback is rendered uniformly.
    _demo, refs = _render(ctx)
    assert all(p["current"].value == "folder-id-42" for p in (
        refs["folder_dash"], refs["folder_transfer"],
        refs["folder_settings"], refs["folder_conn"],
    ))
    ctx.config.drive_folder_id = None  # process-shared CONFIG: clean up


def test_connected_without_folder_shows_no_folder_selected_message(ctx):
    """DOC-39 §4.1: with Drive connected but no target, the panel says
    «لم يتم اختيار مجلد» — it never invents a folder name."""
    from teledrive.drive_auth import DriveAuth
    from teledrive.drive_folders import FOLDER_MIME  # noqa: F401 (contract marker)

    class _Exec:
        def __init__(self, fn):
            self._fn = fn

        def execute(self):
            return self._fn()

    class FakeDriveService:
        def about(self):
            class _Get:
                def get(self, fields=None):
                    return _Exec(lambda: {
                        "user": {"emailAddress": "user@example.com", "displayName": "User"},
                        "storageQuota": {"limit": "100", "usage": "40"},
                    })
            return _Get()

        def files(self):
            return type("_F", (), {"list": lambda *a, **k: _Exec(lambda: {"files": []})})()

    service = FakeDriveService()
    ctx.drive_auth = DriveAuth(ctx, service_factory=lambda: service)
    ctx.handlers.h_drive_connect()
    assert ctx.drive_auth.connected is True

    _demo, refs = _render(ctx)
    for picker in (refs["folder_dash"], refs["folder_transfer"],
                   refs["folder_settings"], refs["folder_conn"]):
        assert picker["current"].value == t("msg.no_folder_selected")
        assert picker["message"].value == ""
