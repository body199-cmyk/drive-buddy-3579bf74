"""Google Drive v3 file operations.

Authentication is NOT performed here. Constitution Section 6 allows exactly one
Drive credential path (native Colab auth in `drive_auth.py`); this module is a
thin, injected wrapper around the resulting `drive` API service object.
"""
from __future__ import annotations

import io
import os
from typing import Any, Callable, Optional

from .config import UPLOAD_CHUNK
from .logging_config import get_logger

_log = get_logger("teledrive.drive")

try:
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    _GDRIVE_AVAILABLE = True
except Exception:  # pragma: no cover
    _GDRIVE_AVAILABLE = False
    MediaFileUpload = None  # type: ignore
    MediaIoBaseDownload = None  # type: ignore

SCOPES = ["https://www.googleapis.com/auth/drive"]


class DriveService:
    """Wraps an already-authenticated Drive API service object."""

    def __init__(self, service: Any):
        if service is None:
            raise RuntimeError("DriveService requires an authenticated drive service")
        self.service = service

    @classmethod
    def from_auth(cls, drive_auth) -> "DriveService":
        return cls(drive_auth.require_service())

    def revoke(self) -> None:
        self.service = None

    # ---------- Metadata ----------

    def about(self) -> dict[str, Any]:
        assert self.service
        return self.service.about().get(fields="storageQuota,user").execute()

    def storage_quota(self) -> dict[str, int]:
        info = self.about().get("storageQuota", {}) or {}
        return {
            "limit": int(info.get("limit", 0) or 0),
            "usage": int(info.get("usage", 0) or 0),
        }

    # ---------- Folders ----------

    def find_folder(self, name: str, parent: str | None = None) -> str | None:
        assert self.service
        q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent:
            q += f" and '{parent}' in parents"
        r = self.service.files().list(q=q, fields="files(id,name)", pageSize=1).execute()
        files = r.get("files", [])
        return files[0]["id"] if files else None

    def create_folder(self, name: str, parent: str | None = None) -> str:
        assert self.service
        body = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
        if parent:
            body["parents"] = [parent]
        r = self.service.files().create(body=body, fields="id").execute()
        return r["id"]

    def ensure_folder(self, name: str, parent: str | None = None) -> str:
        return self.find_folder(name, parent) or self.create_folder(name, parent)

    def list_folders(self, parent: str | None = None) -> list[dict[str, Any]]:
        assert self.service
        q = "mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent:
            q += f" and '{parent}' in parents"
        r = self.service.files().list(q=q, fields="files(id,name)", pageSize=200).execute()
        return r.get("files", [])

    # ---------- Duplicate lookup ----------

    def find_by_source_key(self, source_key: str) -> dict[str, Any] | None:
        assert self.service
        q = f"appProperties has {{ key='source_key' and value='{source_key}' }} and trashed=false"
        r = self.service.files().list(
            q=q, fields="files(id,name,size,appProperties)", pageSize=1
        ).execute()
        files = r.get("files", [])
        return files[0] if files else None

    # ---------- Upload ----------

    def upload_resumable(
        self,
        file_path: str,
        drive_name: str,
        parent_id: str,
        source_key: str,
        progress_cb: Callable[[int, int], None] | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any]:
        assert self.service
        media = MediaFileUpload(
            file_path,
            mimetype=mime_type or "application/octet-stream",
            chunksize=UPLOAD_CHUNK,
            resumable=True,
        )
        body = {
            "name": drive_name,
            "parents": [parent_id],
            "appProperties": {
                "source_key": source_key,
                "teledrive_source_key": source_key,
            },
        }
        request = self.service.files().create(
            body=body, media_body=media,
            fields="id,name,size,parents,appProperties,trashed"
        )
        response = None
        total = os.path.getsize(file_path) or 1
        while response is None:
            status, response = request.next_chunk()
            if status and progress_cb:
                try:
                    progress_cb(int(status.resumable_progress), total)
                except Exception:
                    pass
        if progress_cb:
            try:
                progress_cb(total, total)
            except Exception:
                pass
        return response

    # ---------- Download small files (checkpoint retrieval) ----------

    def download_bytes(self, file_id: str) -> bytes:
        assert self.service
        req = self.service.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        dl = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
        return buf.getvalue()

    def upload_bytes(self, name: str, data: bytes, parent_id: str) -> str:
        assert self.service
        from googleapiclient.http import MediaInMemoryUpload
        media = MediaInMemoryUpload(data, mimetype="application/json", resumable=False)
        body = {"name": name, "parents": [parent_id]}
        r = self.service.files().create(body=body, media_body=media, fields="id").execute()
        return r["id"]

    def list_children(self, parent_id: str) -> list[dict[str, Any]]:
        assert self.service
        r = self.service.files().list(
            q=f"'{parent_id}' in parents and trashed=false",
            fields="files(id,name,size,modifiedTime,appProperties)",
            pageSize=1000,
        ).execute()
        return r.get("files", [])
