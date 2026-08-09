"""M15-T05 — CheckpointService lazily builds the one context Drive client.

Regression for the real Cell 4 failure: ``restore_and_reconcile()`` raised
``DriveNotReadyError`` even though ``drive_auth.adopt_service()`` had already
succeeded, because ``CheckpointService._drive()`` returned the not-yet-built
``ctx.drive_client`` (``None``) instead of routing through the single
construction path ``ApplicationContext.ensure_drive_client()``.

Fake connectors only: an in-memory googleapiclient-shaped Drive service that
passes the ``about().get()`` gate and answers the tiny files() surface the
checkpoint code needs. These tests flip NO action-registry flags —
``recovery.restore`` stays ``tested=False`` until a real owner-run Colab
session proves it. This module guards the initialization-order contract, not
the Colab gate.
"""
from __future__ import annotations

import json
import re
import uuid

import pytest

from teledrive import database as db
from teledrive.drive_auth import ABOUT_FIELDS
from teledrive.errors import DriveNotReadyError
from teledrive.models import MediaItem

# Actions proven by this module (see teledrive/action_registry.proof_test):
# none — fake connectors cannot mark anything Colab-ready.
PROVES: tuple = ()

ABOUT_RESPONSE = {
    "user": {"emailAddress": "fake@example.com", "displayName": "Fake User"},
    "storageQuota": {"limit": "100", "usage": "40"},
}


# --------------------------------------------------------------------------
# In-memory googleapiclient-shaped Drive service
# --------------------------------------------------------------------------

class _FakeResponse:
    """Minimal httplib2-style response object for MediaIoBaseDownload."""

    def __init__(self, status=200, headers=None):
        self.status = status
        self._headers = headers or {}

    def __contains__(self, key):
        return key in self._headers

    def __getitem__(self, key):
        return self._headers[key]


class _FakeHttp:
    """Serves get_media downloads straight out of the in-memory file store."""

    def __init__(self, drive):
        self.drive = drive

    def request(self, uri, method="GET", headers=None):
        file_id = uri.rsplit("/files/", 1)[-1].split("?")[0]
        meta = self.drive.file_store.get(file_id, {})
        data = meta.get("_bytes", b"")
        size = len(data)
        if size == 0:
            return _FakeResponse(416, {"content-range": "bytes */0"}), b""
        return _FakeResponse(200, {"content-range": f"bytes 0-{size - 1}/{size}"}), data


class _ListResult:
    def __init__(self, files):
        self._files = files

    def execute(self):
        return {"files": self._files}


class _CreateRequest:
    def __init__(self, drive, body, media_body):
        self.drive = drive
        self.body = body
        self.media_body = media_body

    def execute(self):
        file_id = f"fake_{uuid.uuid4().hex[:8]}"
        if self.media_body is not None:
            stream = self.media_body.stream()
            stream.seek(0)
            data = stream.read()
            self.drive.file_store[file_id] = {
                "name": self.body.get("name", ""),
                "size": len(data),
                "parent": (self.body.get("parents") or [None])[0],
                "appProperties": dict(self.body.get("appProperties", {}) or {}),
                "_bytes": data,
                "modifiedTime": "2026-01-01T00:00:00Z",
            }
        else:
            self.drive.folders[file_id] = self.body.get("name", "")
        return {"id": file_id}


class _GetMediaRequest:
    def __init__(self, drive, file_id):
        self.uri = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        self.headers = {}
        self.http = _FakeHttp(drive)


class _AboutGet:
    def __init__(self, fields=None):
        self.fields = fields

    def execute(self):
        assert self.fields == ABOUT_FIELDS, "the gate must use the canonical fields"
        return ABOUT_RESPONSE


class _About:
    def get(self, fields=None):
        return _AboutGet(fields)


class _FilesApi:
    def __init__(self, drive):
        self.drive = drive

    def list(self, q=None, fields=None, pageSize=None):
        q = q or ""
        if "appProperties has" in q:
            match = re.search(r"value='([^']*)'", q)
            source_key = match.group(1) if match else None
            for file_id, meta in self.drive.file_store.items():
                props = meta.get("appProperties", {})
                if source_key and props.get("source_key") == source_key:
                    return _ListResult([{
                        "id": file_id,
                        "name": meta["name"],
                        "size": str(meta["size"]),
                        "appProperties": props,
                    }])
            return _ListResult([])
        if "mimeType='application/vnd.google-apps.folder'" in q:
            return _ListResult([
                {"id": file_id, "name": name}
                for file_id, name in self.drive.folders.items()
            ])
        if "in parents" in q:
            parent_id = q.split("'", 1)[1].split("'", 1)[0] if "'" in q else ""
            return _ListResult([
                {
                    "id": file_id,
                    "name": meta["name"],
                    "size": str(meta["size"]),
                    "modifiedTime": meta.get("modifiedTime", "2026-01-01T00:00:00Z"),
                    "appProperties": meta.get("appProperties", {}),
                }
                for file_id, meta in self.drive.file_store.items()
                if meta.get("parent") == parent_id
            ])
        return _ListResult([])

    def create(self, body=None, media_body=None, fields=None, **kwargs):
        return _CreateRequest(self.drive, body or {}, media_body)

    def get_media(self, fileId=None, **kwargs):
        return _GetMediaRequest(self.drive, fileId or "")


class _FakeRawDriveService:
    """Raw googleapiclient-shaped service owned by DriveAuth.

    Enough surface for the about() gate plus the files() operations the
    checkpoint code uses (find/create folder, upload, list, get_media).
    """

    def __init__(self):
        self.file_store: dict[str, dict] = {}
        self.folders: dict[str, str] = {}

    def about(self):
        return _About()

    def files(self):
        return _FilesApi(self)

    def seed_source_file(self, source_key: str, size: int) -> str:
        """Plant a completed upload so reconcile can find it on 'Drive'."""
        file_id = f"seed_{uuid.uuid4().hex[:8]}"
        self.file_store[file_id] = {
            "name": f"{source_key}.bin",
            "size": size,
            "parent": None,
            "appProperties": {
                "source_key": source_key,
                "teledrive_source_key": source_key,
            },
            "_bytes": b"x" * size,
            "modifiedTime": "2026-01-01T00:00:00Z",
        }
        return file_id


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _counting_drive_service(monkeypatch):
    """Replace the context's single client class with a counting subclass.

    ``ApplicationContext.ensure_drive_client()`` imports
    ``teledrive.drive_client.DriveService`` at call time, so patching the
    module attribute is picked up by the lazy construction path we test.
    """
    from teledrive import drive_client as drive_client_module

    class CountingDriveService(drive_client_module.DriveService):
        from_auth_calls = 0

        @classmethod
        def from_auth(cls, drive_auth):
            cls.from_auth_calls += 1
            return super().from_auth(drive_auth)

    monkeypatch.setattr(drive_client_module, "DriveService", CountingDriveService)
    return CountingDriveService


# --------------------------------------------------------------------------
# Regression tests
# --------------------------------------------------------------------------

def test_restore_and_reconcile_builds_the_lazy_client_once(ctx, monkeypatch):
    """Cell 4 flow: adopted+verified service, client still None -> works.

    Proves the client is lazily built exactly once, reuses the adopted
    service, and is reused on the next call.
    """
    counting = _counting_drive_service(monkeypatch)
    service = _FakeRawDriveService()
    ctx.drive_auth.adopt_service(service)
    assert ctx.drive_client is None  # the bug precondition

    result = ctx.checkpoints.restore_and_reconcile()

    assert result["message_key"] == "msg.recovery_none"
    assert result["imported"] == 0
    assert counting.from_auth_calls == 1, "client must be lazily built exactly once"
    assert ctx.drive_client is not None
    assert ctx.drive_client.service is service, (
        "must wrap the adopted service, never construct a second one"
    )

    first = ctx.drive_client
    again = ctx.checkpoints.restore_and_reconcile()
    assert again["message_key"] == "msg.recovery_none"
    assert ctx.drive_client is first, "second call must reuse the existing client"
    assert counting.from_auth_calls == 1


def test_disconnected_drive_raises_and_never_constructs_a_client(ctx, monkeypatch):
    counting = _counting_drive_service(monkeypatch)

    with pytest.raises(DriveNotReadyError):
        ctx.checkpoints.restore_and_reconcile()

    assert counting.from_auth_calls == 0, "no client may be built while disconnected"
    assert ctx.drive_client is None


def test_persist_and_restore_round_trip_uses_the_context_client(ctx, monkeypatch):
    """Full checkpoint round-trip through the lazy context client.

    persist() builds the client, restore_and_reconcile() reuses it, and the
    existing restore/reconcile behavior (import + mark-uploaded) is unchanged.
    """
    counting = _counting_drive_service(monkeypatch)
    service = _FakeRawDriveService()
    ctx.drive_auth.adopt_service(service)
    assert ctx.drive_client is None

    # An in-flight item that reconcile should find on Drive after the crash.
    item = ctx.queue_manager.enqueue(MediaItem(
        source_key="tg:9:9:rt",
        chat_id=9,
        message_id=9,
        file_unique_id="rt",
        original_name="roundtrip.bin",
        safe_name="roundtrip.bin",
        media_type="document",
        extension="bin",
        size_bytes=256,
    ))
    ctx.queue_manager.transition(item.id, "Downloading")
    ctx.queue_manager.transition(item.id, "Downloaded")
    ctx.queue_manager.transition(item.id, "Uploading")
    service.seed_source_file("tg:9:9:rt", size=256)

    persisted = ctx.checkpoints.persist()
    assert persisted["drive_file_id"] is not None
    assert ctx.drive_client is not None
    assert counting.from_auth_calls == 1

    restored = ctx.checkpoints.restore_and_reconcile()

    assert restored["message_key"] == "msg.recovery_ok"
    assert restored["imported"] == 0
    assert restored["reconciled"]["marked_uploaded"] == 1
    assert db.get_item(item.id).state == "Uploaded"
    assert counting.from_auth_calls == 1, "restore must reuse the client persist built"
