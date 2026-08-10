"""Drive folder browse / create / select. Persists a folder ID, never a name."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import database as db
from .errors import DriveNotReadyError, TeleDriveError
from .logging_config import get_logger

_log = get_logger("teledrive.drive_folders")

FOLDER_MIME = "application/vnd.google-apps.folder"
SETTING_FOLDER_ID = "drive_folder_id"
SETTING_FOLDER_NAME = "drive_folder_name"  # display only; the ID is authoritative


@dataclass
class FolderRef:
    id: str
    name: str


def _escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("'", "\\'")


class DriveFolders:
    def __init__(self, ctx) -> None:
        self.ctx = ctx

    def _service(self):
        drive_auth = self.ctx.drive_auth
        if drive_auth is None:
            raise DriveNotReadyError("drive auth service missing")
        return drive_auth.require_service()

    def list_children(self, parent_id: str = "root") -> list[FolderRef]:
        service = self._service()
        query = (
            f"mimeType='{FOLDER_MIME}' and trashed=false "
            f"and '{_escape(parent_id or 'root')}' in parents"
        )
        result = service.files().list(
            q=query, fields="files(id,name)", pageSize=200, orderBy="name"
        ).execute()
        return [FolderRef(f["id"], f.get("name", "")) for f in (result.get("files") or [])]

    def create(self, name: str, parent_id: str = "root") -> FolderRef:
        name = (name or "").strip()
        if not name:
            raise TeleDriveError("folder name required", "err.bad_folder_name")
        service = self._service()
        body: dict[str, Any] = {"name": name, "mimeType": FOLDER_MIME}
        if parent_id:
            body["parents"] = [parent_id]
        created = service.files().create(body=body, fields="id,name").execute()
        ref = FolderRef(created["id"], created.get("name", name))
        db.add_event("", "drive.folder", "created", {"folder_id": ref.id})
        return ref

    def select(self, folder_id: str, folder_name: str = "") -> FolderRef:
        folder_id = (folder_id or "").strip()
        if not folder_id:
            raise TeleDriveError("folder id required", "err.bad_folder_id")
        service = self._service()
        meta = service.files().get(fields="id,name,mimeType", fileId=folder_id).execute()
        if meta.get("mimeType") != FOLDER_MIME:
            raise TeleDriveError("target is not a folder", "err.bad_folder_id")
        ref = FolderRef(meta["id"], meta.get("name", folder_name))
        # ID is what we persist. The name is cached for the chip label only.
        self.ctx.config.drive_folder_id = ref.id
        db.set_setting(SETTING_FOLDER_ID, ref.id)
        db.set_setting(SETTING_FOLDER_NAME, ref.name)
        db.add_event("", "drive.folder", "selected", {"folder_id": ref.id})
        _log.info("drive folder selected id=%s", ref.id)
        return ref

    def selected(self) -> FolderRef | None:
        folder_id = self.ctx.config.drive_folder_id or db.get_setting(SETTING_FOLDER_ID, "")
        if not folder_id:
            return None
        self.ctx.config.drive_folder_id = folder_id
        return FolderRef(folder_id, db.get_setting(SETTING_FOLDER_NAME, ""))

    def require_selected(self) -> FolderRef:
        ref = self.selected()
        if ref is None:
            raise TeleDriveError("no destination folder selected", "err.no_folder")
        return ref

    def current_folder_name(self) -> str:
        """Return the cached name of the selected folder, or the id as LTR fallback."""
        ref = self.selected()
        if ref is None:
            return ""
        return ref.name or ref.id
