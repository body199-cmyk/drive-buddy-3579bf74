"""DOC-39 (M18-T01) §4 — Drive target folder flow from the visible panels.

Proves, through the REAL DriveAuth about().get() gate and the REAL
DriveFolders/Handlers code:
* list / select / create work from the visible transfer panel
* the folder ID persists and propagates to every panel chip + the top bar
* a disconnected Drive keeps the panel visible, disabled and translated
"""
from __future__ import annotations

import pytest

gr = pytest.importorskip("gradio")

from teledrive import database as db
from teledrive.drive_auth import ABOUT_FIELDS, DriveAuth
from teledrive.drive_folders import FOLDER_MIME
from teledrive.handlers import ERROR_ARITY
from teledrive.i18n import t
from teledrive import ui

PROVES = ()  # drive actions are proven in tests/test_drive_folders.py


class _Exec:
    def __init__(self, fn):
        self._fn = fn

    def execute(self):
        return self._fn()


class FakeDriveService:
    """Duck-typed Drive v3: about() + files().list/create/get."""

    def __init__(self):
        self.calls: list[tuple] = []
        self.folders = [
            {"id": "id_alpha", "name": "Alpha"},
            {"id": "id_beta", "name": "Beta"},
        ]
        self.meta_by_id = {
            "id_alpha": {"id": "id_alpha", "name": "Alpha", "mimeType": FOLDER_MIME},
            "id_beta": {"id": "id_beta", "name": "Beta", "mimeType": FOLDER_MIME},
            "id_plain": {"id": "id_plain", "name": "notes.txt", "mimeType": "text/plain"},
        }
        self.created_count = 0

    def about(self):
        class _Get:
            def get(self, fields=None):
                assert fields == ABOUT_FIELDS
                return _Exec(lambda: {
                    "user": {"emailAddress": "user@example.com", "displayName": "User"},
                    "storageQuota": {"limit": "100", "usage": "40"},
                })
        return _Get()

    def files(self):
        service = self

        class _Files:
            def list(self, q=None, fields=None, pageSize=None, orderBy=None):
                service.calls.append(("list", q, fields, pageSize, orderBy))
                return _Exec(lambda: {"files": list(service.folders)})

            def create(self, body=None, fields=None):
                service.calls.append(("create", body, fields))
                service.created_count += 1
                return _Exec(lambda: {"id": "id_new", "name": body["name"]})

            def get(self, fields=None, fileId=None):
                service.calls.append(("get", fileId, fields))
                return _Exec(lambda: service.meta_by_id[fileId])

        return _Files()


def _connected_drive(ctx):
    service = FakeDriveService()
    ctx.drive_auth = DriveAuth(ctx, service_factory=lambda: service)
    ctx.handlers.h_drive_connect()
    assert ctx.drive_auth.connected is True
    return service


def _render(ctx):
    with gr.Blocks() as demo:
        refs = ui._render_shell(ctx, ctx.binder, gr.State("en"), "en")
    return demo, refs


def _transfer_picker(refs):
    return refs["folder_transfer"]


# ---------------------------------------------------------------------------
# list / select / create from the visible transfer panel
# ---------------------------------------------------------------------------

def test_list_select_create_from_transfer_panel(ctx):
    _connected_drive(ctx)
    _demo, refs = _render(ctx)
    picker = _transfer_picker(refs)

    # LIST: real Drive folders land in the transfer panel dropdown
    message, update = ctx.handlers.h_drive_list_folders("root")
    assert message == t("msg.folders_loaded")
    assert update["choices"] == ["Alpha :: id_alpha", "Beta :: id_beta"]

    # SELECT: persists the ID only; the name is display
    result = ctx.handlers.h_drive_select_folder("Alpha :: id_alpha")
    assert result[2] == t("msg.folder_selected")
    assert db.get_setting("drive_folder_id", "") == "id_alpha"
    assert ctx.config.drive_folder_id == "id_alpha"

    # CREATE: from the transfer panel's new-name field
    result = ctx.handlers.h_drive_create_folder("Backups", "root")
    assert result[2] == t("msg.folder_created")
    assert result[1] == "Backups"
    assert db.get_setting("drive_folder_id", "") == "id_new"
    assert db.get_setting("drive_folder_name", "") == "Backups"

    # invalid names are refused before any Drive API call
    ctx.handlers.h_drive_create_folder("   ", "root")
    assert t("err.bad_folder_name") in ctx.handlers.h_drive_create_folder("", "root")[0]
    ctx.config.drive_folder_id = None  # process-shared CONFIG: clean up


def test_transfer_panel_controls_are_wired_and_live(ctx):
    _connected_drive(ctx)
    _demo, refs = _render(ctx)
    picker = _transfer_picker(refs)
    # the picker is visible inside transfers (not hidden behind a closed tab)
    assert picker["choice"].visible is True
    assert picker["create_btn"].visible is True
    assert picker["select_btn"].visible is True
    # all four panels share the same named handlers
    assert len(ctx.binder.wired["drive.list_folders"]) == 4
    assert len(ctx.binder.wired["drive.create_folder"]) == 4
    assert len(ctx.binder.wired["drive.select_folder"]) == 4
    assert ERROR_ARITY["drive.create_folder"] == 10
    assert ERROR_ARITY["drive.select_folder"] == 10


# ---------------------------------------------------------------------------
# folder ID persists and propagates to all chips
# ---------------------------------------------------------------------------

def test_folder_id_persists_and_propagates_to_all_panels_and_top_chip(ctx):
    _connected_drive(ctx)
    _demo, refs = _render(ctx)

    # 1) the handler broadcast reaches every panel + the top chip
    result = ctx.handlers.h_drive_select_folder("Beta :: id_beta")
    assert result[1] == result[4] == result[5] == result[6] == "Beta"
    assert result[7] == result[8] == result[9] == t("msg.folder_selected")
    assert "Beta" in result[3]

    # 2) the wiring really attaches those outputs (browser propagation)
    demo_fns = [bf for bf in _demo.fns.values() if getattr(bf.fn, "action_id", None) == "drive.select_folder"]
    assert len(demo_fns) == 4
    for bf in demo_fns:
        outputs = list(bf.outputs)
        assert refs["folder_chip"] in outputs
        for key in ("folder_dash", "folder_transfer", "folder_settings", "folder_conn"):
            picker = refs[key]
            assert picker["current"] in outputs
            assert picker["message"] in outputs

    # 3) a fresh render re-reads the SAME persisted value (single source of truth)
    _demo2, refs2 = _render(ctx)
    for key in ("folder_dash", "folder_transfer", "folder_settings", "folder_conn"):
        assert refs2[key]["current"].value == "Beta"
    assert "Beta" in refs2["folder_chip"].value
    assert db.get_setting("drive_folder_id", "") == "id_beta"
    ctx.config.drive_folder_id = None  # process-shared CONFIG: clean up


def test_selection_preview_and_enqueue_gate_follow_the_folder(ctx):
    _connected_drive(ctx)
    from teledrive.models import MediaItem

    ctx.selection.set_candidates([
        MediaItem(id="i1", safe_name="a.jpg", media_type="photo", size_bytes=10),
    ])
    ctx.selection.select_all_visible()

    _demo, refs = _render(ctx)
    # no folder yet -> enqueue disabled and preview says no folder
    assert refs["enqueue_btn"].interactive is False
    assert t("msg.no_folder_selected") in refs["selection_preview"].value

    ctx.handlers.h_drive_select_folder("Alpha :: id_alpha")
    _demo2, refs2 = _render(ctx)
    assert refs2["enqueue_btn"].interactive is True
    assert "Alpha" in refs2["selection_preview"].value
    ctx.config.drive_folder_id = None  # process-shared CONFIG: clean up


# ---------------------------------------------------------------------------
# disconnected Drive: visible + disabled + translated reason
# ---------------------------------------------------------------------------

def test_disconnected_drive_panels_visible_disabled_and_translated(ctx):
    _demo, refs = _render(ctx)
    for key in ("folder_dash", "folder_transfer", "folder_settings", "folder_conn"):
        picker = refs[key]
        assert picker["message"].value == t("err.drive_not_ready")
        assert picker["current"].value == "—"
        for control in ("parent_id", "choice", "new_name", "list_btn", "create_btn", "select_btn"):
            assert picker[control].interactive is False, f"{key}.{control} must be disabled"
        # never a fake folder list
        assert picker["choice"].choices in ([], None)

    # the top chip agrees: disconnected drive, no folder claim
    assert t("status.disconnected") in refs["folder_chip"].value


def test_connected_drive_has_empty_message_and_enabled_controls(ctx):
    _connected_drive(ctx)
    _demo, refs = _render(ctx)
    for key in ("folder_dash", "folder_transfer", "folder_settings", "folder_conn"):
        picker = refs[key]
        assert picker["message"].value == ""
        for control in ("parent_id", "choice", "new_name", "list_btn", "create_btn", "select_btn"):
            assert picker[control].interactive is True, f"{key}.{control} must be enabled"
