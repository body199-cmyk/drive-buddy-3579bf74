"""M17-T02 — Drive folder actions: handler-level proofs with a fake Drive service.

The fake service still passes through the REAL ``DriveAuth`` ``about().get()``
gate (nothing reports Connected before it) and the REAL ``DriveFolders`` /
``Handlers`` code owns the query shapes, validation and persistence. What these
tests prove is the action contract:

  visible control → named handler → service_path → real service → localized output

What they still do NOT prove is the live native Colab flow (owner-side,
M15-T01) — no fake test ever claims that.
"""
from __future__ import annotations

from teledrive import database as db
from teledrive.drive_auth import ABOUT_FIELDS, DriveAuth
from teledrive.handlers import ERROR_ARITY
from teledrive.i18n import t
from teledrive.drive_folders import FOLDER_MIME

PROVES = (
    "drive.list_folders",
    "drive.create_folder",
    "drive.select_folder",
)


class _Exec:
    def __init__(self, fn):
        self._fn = fn

    def execute(self):
        return self._fn()


class FakeDriveService:
    """Duck-typed Drive v3 stand-in: about () + files().list/create/get."""

    def __init__(self):
        self.calls: list[tuple] = []
        self.folders = [
            {"id": "id_alpha", "name": "Alpha"},
            {"id": "id_beta", "name": "Beta"},
        ]
        self.meta_by_id = {
            "id_alpha": {"id": "id_alpha", "name": "Alpha", "mimeType": FOLDER_MIME},
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
    """Context with a DriveAuth that has passed the REAL about().get() gate."""
    service = FakeDriveService()
    drive = DriveAuth(ctx, service_factory=lambda: service)
    ctx.drive_auth = drive
    ctx.handlers.h_drive_connect()
    assert drive.connected is True
    return drive, service


def test_list_folders_action_returns_real_shaped_dropdown_choices(ctx):
    drive, service = _connected_drive(ctx)
    assert ctx.handlers.h_drive_list_folders.action_id == "drive.list_folders"

    message, update = ctx.handlers.h_drive_list_folders("root")

    assert message == t("msg.folders_loaded")
    list_calls = [c for c in service.calls if c[0] == "list"]
    assert list_calls, "list_folders must hit files().list"
    query = list_calls[0][1]
    assert FOLDER_MIME in query and "'root' in parents" in query
    # Gradio Dropdowns consume an update payload — never a bare list.
    assert isinstance(update, dict), "dropdown must receive an update payload"
    assert update["choices"] == ["Alpha :: id_alpha", "Beta :: id_beta"]
    assert ERROR_ARITY["drive.list_folders"] == 2


def test_create_folder_action_validates_name_and_parent(ctx):
    drive, service = _connected_drive(ctx)
    assert ctx.handlers.h_drive_create_folder.action_id == "drive.create_folder"

    # Empty / whitespace names are refused locally with the localized key.
    for bad in ("", "   "):
        message, choice, current = ctx.handlers.h_drive_create_folder(bad, "root")
        assert choice is None and current is None
        assert t("err.bad_folder_name") in message
    assert service.created_count == 0, "no Drive call may fire for an invalid name"

    # A real name creates the folder under the given parent, id-authoritative.
    choices, current, message = ctx.handlers.h_drive_create_folder("Backups", "root")
    assert message == t("msg.folder_created")
    assert choices["value"] == "Backups :: id_new"
    assert current == "Backups"
    body = [c for c in service.calls if c[0] == "create"][0][1]
    assert body["mimeType"] == FOLDER_MIME
    assert body["parents"] == ["root"]
    assert ERROR_ARITY["drive.create_folder"] == 3


def test_select_folder_action_validates_mimetype_and_stores_the_id(ctx):
    drive, service = _connected_drive(ctx)
    assert ctx.handlers.h_drive_select_folder.action_id == "drive.select_folder"

    # A non-folder target is refused with the localized key; nothing persists.
    message, choice, stored = ctx.handlers.h_drive_select_folder("notes.txt :: id_plain")
    assert choice is None and stored is None
    assert t("err.bad_folder_id") in message
    assert db.get_setting("drive_folder_id", "") == ""

    # A real folder stores the ID as the source of truth (name is display-only).
    choice, current, message = ctx.handlers.h_drive_select_folder("Alpha :: id_alpha")
    assert message == t("msg.folder_selected")
    assert choice["value"] == "Alpha :: id_alpha"
    assert current == "Alpha"
    get_calls = [c for c in service.calls if c[0] == "get"]
    assert get_calls and get_calls[-1][1] == "id_alpha"
    assert db.get_setting("drive_folder_id", "") == "id_alpha"
    assert db.get_setting("drive_folder_name", "") == "Alpha"
    assert ctx.config.drive_folder_id == "id_alpha", "the ID, never the name, is persisted"
    assert ERROR_ARITY["drive.select_folder"] == 3


def test_no_credentials_or_service_objects_reach_storage_or_logs(ctx):
    """§4.3: folder flows must never persist tokens/service objects."""
    drive, service = _connected_drive(ctx)
    ctx.handlers.h_drive_list_folders("root")
    ctx.handlers.h_drive_create_folder("Backups", "root")
    ctx.handlers.h_drive_select_folder("Alpha :: id_alpha")
    poison = db.get_setting("drive_folder_id", "") + db.get_setting("drive_folder_name", "")
    assert "FakeDriveService" not in poison and "token" not in poison.lower()
