"""ADR-004 obfuscated vault + M24-T01 SessionVault (creds JSON on Drive)."""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from teledrive import database as db
from teledrive import session_vault
from teledrive.config import SESSION_VAULT_NAME
from teledrive.errors import TeleDriveError
from teledrive.session_vault import (
    MAGIC,
    VAULT_CREDS_NAME,
    VAULT_FORMAT_ENCRYPTED,
    VAULT_SESSION_NAME,
)

PROVES = (
    "session.save",
    "session.autorestore",
    "session.forget",
)

from .mocks.fake_drive import FakeDrive
from .test_telegram_auth import FakeClient
from teledrive import telegram_auth as ta


SQLITE_HDR = b"SQLite format 3\x00fake-session-bytes-not-a-real-login"


def _write_local_session(path: Path, payload: bytes = SQLITE_HDR) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def test_wrap_roundtrip_and_wrong_secret_is_rejected():
    blob = session_vault.wrap_blob(SQLITE_HDR, "hash-one")
    assert blob.startswith(MAGIC)
    assert SQLITE_HDR not in blob
    assert session_vault.unwrap_blob(blob, "hash-one") == SQLITE_HDR
    assert session_vault.unwrap_blob(blob, "hash-two") is None


def test_save_restore_via_fake_drive(tmp_path):
    local = tmp_path / "telegram.session"
    _write_local_session(local)
    drive = FakeDrive()
    file_id = session_vault.save_session(drive, secret="abc", local_path=local)
    assert file_id
    names = [m["name"] for m in drive.files.values()]
    assert names == [SESSION_VAULT_NAME]
    stored = next(iter(drive.files.values()))["_bytes"]
    assert SQLITE_HDR not in stored
    assert b"abc" not in stored

    dest = tmp_path / "restored.session"
    assert session_vault.restore_session(drive, secret="abc", local_path=dest)
    assert dest.read_bytes() == SQLITE_HDR


def test_wrong_secret_does_not_write_local_file(tmp_path):
    local = tmp_path / "telegram.session"
    _write_local_session(local)
    drive = FakeDrive()
    session_vault.save_session(drive, secret="right", local_path=local)
    dest = tmp_path / "out.session"
    assert session_vault.restore_session(drive, secret="wrong", local_path=dest) is False
    assert not dest.exists()


def test_wipe_removes_local_and_remote(tmp_path):
    local = tmp_path / "telegram.session"
    _write_local_session(local)
    drive = FakeDrive()
    session_vault.save_session(drive, secret="k", local_path=local)
    session_vault.wipe_session(drive, local_path=local)
    assert not local.exists()
    assert all(m["name"] != SESSION_VAULT_NAME for m in drive.files.values())


def test_missing_local_session_is_a_noop():
    drive = FakeDrive()
    assert session_vault.save_session(drive, secret="k", local_path=Path("/no/such/session")) is None
    assert drive.files == {}


def test_keepalive_is_idempotent():
    session_vault.reset_keepalive_for_tests()
    first = session_vault.start_keepalive(interval_seconds=3600)
    second = session_vault.start_keepalive(interval_seconds=3600)
    assert first["started"] is True
    assert second["started"] is False
    assert second["reason"] == "already-running"
    session_vault.reset_keepalive_for_tests()


def test_authorize_uploads_vault_and_logout_wipes_it(ctx, tmp_path):
    from teledrive import config

    session_path = Path(config.TELEGRAM_SESSION)
    _write_local_session(session_path)
    drive = _connect_fake_drive(ctx, FakeDrive())

    created = []

    def factory(api_id, api_hash):
        client = FakeClient(api_id, api_hash)
        created.append(client)
        return client

    auth = ta.TelegramAuth(ctx, client_factory=factory)
    ctx.telegram_auth = auth
    auth.set_credentials("12345", "vault-hash")
    auth.send_code("+971500000000")
    auth.verify_code("55555")
    assert auth.state == ta.AUTHORIZED
    names = {m["name"] for m in drive.files.values()}
    assert VAULT_SESSION_NAME in names
    assert VAULT_CREDS_NAME in names
    assert SESSION_VAULT_NAME not in names

    dumped = json.dumps(db.recent_events(limit=500), ensure_ascii=False, default=str)
    assert "vault-hash" not in dumped
    assert SQLITE_HDR.decode("latin1") not in dumped

    auth.logout()
    assert not session_path.exists()
    names = {m["name"] for m in drive.files.values()}
    assert VAULT_SESSION_NAME not in names
    assert VAULT_CREDS_NAME not in names
    assert SESSION_VAULT_NAME not in names


def test_existing_session_label_is_not_a_phone(ctx):
    created = []

    def factory(api_id, api_hash):
        client = FakeClient(api_id, api_hash)
        client.authorized = True
        created.append(client)
        return client

    auth = ta.TelegramAuth(ctx, client_factory=factory)
    status = auth.set_credentials("12345", "h")
    assert status.authorized
    assert status.account_label == "saved-session"


def _sqlite_session(path: Path, payload: bytes = b"vault-bytes") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS sessions (data BLOB)")
        conn.execute("DELETE FROM sessions")
        conn.execute("INSERT INTO sessions(data) VALUES (?)", (payload,))
        conn.commit()
    finally:
        conn.close()
    return path


def _connect_fake_drive(ctx, drive=None):
    from teledrive.drive_auth import CONNECTED

    drive = drive or FakeDrive()
    ctx.drive_client = drive
    ctx.drive_auth.state = CONNECTED
    ctx.drive_auth.service = object()
    return drive


def test_save_now_rejects_when_telegram_is_not_authorized(ctx):
    vault = ctx.session_vault
    assert ctx.telegram_auth.authorized is False
    try:
        vault.save_now("1234567", "testhash", "+201234567890")
        raise AssertionError("save_now must refuse when telegram is not authorized")
    except TeleDriveError as exc:
        assert exc.message_key == "err.session_not_authorized"


def test_save_now_uploads_session_and_creds(ctx, caplog):
    from teledrive import config

    local = _sqlite_session(Path(config.TELEGRAM_SESSION), b"session-blob")
    ctx.telegram_auth.state = ta.AUTHORIZED
    ctx.telegram_auth.client = type("C", (), {"session_path": str(local)})()
    drive = _connect_fake_drive(ctx)
    caplog.set_level(logging.INFO)
    result = ctx.session_vault.save_now("1234567", "testhash", "+201234567890")
    assert result.ok and result.saved
    assert result.message_key == "msg.session_saved"
    names = {meta["name"] for meta in drive.files.values()}
    assert VAULT_SESSION_NAME in names
    assert VAULT_CREDS_NAME in names
    creds_meta = next(m for m in drive.files.values() if m["name"] == VAULT_CREDS_NAME)
    payload = json.loads(creds_meta["_bytes"].decode("utf-8"))
    assert payload["api_id"] == "1234567"
    assert payload["format"] == VAULT_FORMAT_ENCRYPTED
    assert "api_hash" not in payload
    assert payload["session_file"] == VAULT_SESSION_NAME
    session_meta = next(m for m in drive.files.values() if m["name"] == VAULT_SESSION_NAME)
    assert b"session-blob" not in session_meta["_bytes"]
    logged = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "+201234567890" not in logged
    assert "testhash" not in logged


def test_autorestore_skips_when_drive_is_disconnected(ctx):
    result = ctx.session_vault.autorestore()
    assert result.ok is False
    assert result.message_key == "msg.session_restore_skipped_no_drive"


def test_autorestore_reports_not_saved_when_vault_is_empty(ctx):
    _connect_fake_drive(ctx)
    result = ctx.session_vault.autorestore()
    assert result.ok is False
    assert result.message_key == "msg.session_not_saved"


def test_autorestore_writes_local_session_and_calls_set_credentials(ctx, monkeypatch):
    from teledrive import config

    drive = _connect_fake_drive(ctx)
    folder_id = drive.ensure_folder("TeleDrive_AppData")
    raw = b"SQLite format 3\x00restored-session"
    drive.upsert_bytes(VAULT_SESSION_NAME, raw, folder_id)
    creds = {
        "api_id": "7654321",
        "api_hash": "restoredhash",
        "phone": "+201111111111",
        "saved_at": "2026-08-18T00:00:00Z",
        "format": 1,
        "session_file": VAULT_SESSION_NAME,
    }
    drive.upsert_bytes(VAULT_CREDS_NAME, json.dumps(creds).encode("utf-8"), folder_id)

    def fake_set_credentials(api_id, api_hash):
        ctx.telegram_auth.state = "AUTHORIZED"
        return type("S", (), {"authorized": True, "state": "AUTHORIZED", "account_label": ""})()

    monkeypatch.setattr(ctx.telegram_auth, "set_credentials", fake_set_credentials)
    dest = Path(config.TELEGRAM_SESSION)
    if dest.exists():
        dest.unlink()
    result = ctx.session_vault.autorestore()
    assert result.ok and result.restored
    assert result.message_key == "msg.session_restored"
    assert dest.read_bytes() == raw
    assert dest.name == "telegram.session"
    assert dest.parent.name == "session"
    assert "/content/drive" not in str(dest)


def test_forget_deletes_vault_files(ctx):
    drive = _connect_fake_drive(ctx)
    folder_id = drive.ensure_folder("TeleDrive_AppData")
    drive.upsert_bytes(VAULT_SESSION_NAME, b"x", folder_id)
    drive.upsert_bytes(VAULT_CREDS_NAME, b"{}", folder_id)
    result = ctx.session_vault.forget()
    assert result.ok and result.forgotten
    assert result.message_key == "msg.session_forgotten"
    names = {meta["name"] for meta in drive.files.values()}
    assert VAULT_SESSION_NAME not in names
    assert VAULT_CREDS_NAME not in names


def test_probe_works_from_external_service_before_adopt(ctx):
    drive = FakeDrive()
    folder_id = drive.ensure_folder("TeleDrive_AppData")
    drive.upsert_bytes(VAULT_SESSION_NAME, b"x", folder_id)
    creds = {"api_id": "1", "api_hash": "h", "phone": "+201234567890", "format": 1}
    drive.upsert_bytes(VAULT_CREDS_NAME, json.dumps(creds).encode("utf-8"), folder_id)
    probe = ctx.session_vault.probe(drive)
    assert probe["has_session"] is True
    assert probe["has_creds"] is True
    assert probe["phone"] == "+201234567890"
    assert "+201234567890" not in probe["phone_label"]
    assert ctx.drive_auth.connected is False


def test_restored_session_stays_on_local_runtime_not_mounted_drive(ctx, monkeypatch):
    from teledrive import config

    path = ctx.session_vault._write_session_bytes(b"local-only")
    assert path == Path(config.TELEGRAM_SESSION)
    assert not str(path).startswith("/content/drive")
    assert "MyDrive" not in str(path)


def test_save_now_falls_back_to_in_memory_credentials(ctx, caplog):
    from teledrive import config

    local = _sqlite_session(Path(config.TELEGRAM_SESSION), b"memory-blob")
    ctx.telegram_auth.state = ta.AUTHORIZED
    ctx.telegram_auth.client = type("C", (), {"session_path": str(local)})()
    ctx.telegram_auth._api_id = 7654321
    ctx.telegram_auth._api_hash = "memoryhash"
    ctx.telegram_auth._phone = "+201234567890"
    drive = _connect_fake_drive(ctx)
    caplog.set_level(logging.INFO)

    result = ctx.session_vault.save_now("", "", "")

    assert result.ok and result.saved
    creds_meta = next(m for m in drive.files.values() if m["name"] == VAULT_CREDS_NAME)
    payload = json.loads(creds_meta["_bytes"].decode("utf-8"))
    assert payload["api_id"] == "7654321"
    assert payload["format"] == VAULT_FORMAT_ENCRYPTED
    assert "api_hash" not in payload
    logged = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "memoryhash" not in logged
    assert "+201234567890" not in logged


def test_autorestore_rejects_bytes_that_are_not_a_sqlite_session(ctx):
    from teledrive import config

    drive = _connect_fake_drive(ctx)
    folder_id = drive.ensure_folder("TeleDrive_AppData")
    drive.upsert_bytes(VAULT_SESSION_NAME, b"this-is-not-a-session", folder_id)
    creds = {
        "api_id": "1234567",
        "api_hash": "h",
        "phone": "+201234567890",
        "format": 1,
        "session_file": VAULT_SESSION_NAME,
    }
    drive.upsert_bytes(VAULT_CREDS_NAME, json.dumps(creds).encode("utf-8"), folder_id)
    dest = Path(config.TELEGRAM_SESSION)
    if dest.exists():
        dest.unlink()

    result = ctx.session_vault.autorestore()

    assert result.ok is False
    assert result.message_key == "err.session_vault_invalid"
    assert not dest.exists()


def test_forget_quiet_never_raises_without_drive(ctx):
    result = ctx.session_vault.forget_quiet()
    assert result.ok is False
    assert result.message_key == "msg.session_restore_skipped_no_drive"


def test_logout_handler_deletes_the_drive_vault(ctx, monkeypatch):
    drive = _connect_fake_drive(ctx)
    folder_id = drive.ensure_folder("TeleDrive_AppData")
    drive.upsert_bytes(VAULT_SESSION_NAME, SQLITE_HDR, folder_id)
    drive.upsert_bytes(VAULT_CREDS_NAME, b"{}", folder_id)
    monkeypatch.setattr(
        ctx.telegram_auth, "logout", lambda: ctx.telegram_auth.status()
    )

    ctx.handlers.h_telegram_logout()

    names = {meta["name"] for meta in drive.files.values()}
    assert VAULT_SESSION_NAME not in names
    assert VAULT_CREDS_NAME not in names


def test_autorestore_once_runs_at_most_one_time(ctx):
    calls = []

    def fake_autorestore():
        calls.append(1)
        return session_vault.VaultResult(False, "msg.session_not_saved")

    ctx.session_vault.autorestore = fake_autorestore
    ctx.session_vault.autorestore_once()
    ctx.session_vault.autorestore_once()

    assert len(calls) == 1


def test_autorestore_once_never_raises(ctx):
    def boom():
        raise RuntimeError("drive exploded")

    ctx.session_vault.autorestore = boom
    result = ctx.session_vault.autorestore_once()
    assert result.ok is False


def test_save_after_login_overwrites_a_preexisting_vault(ctx):
    from teledrive import config

    _sqlite_session(Path(config.TELEGRAM_SESSION), b"already-there")
    ctx.telegram_auth.state = ta.AUTHORIZED
    ctx.telegram_auth._api_id = 1234567
    ctx.telegram_auth._api_hash = "hash"
    drive = _connect_fake_drive(ctx)
    folder_id = drive.ensure_folder("TeleDrive_AppData")
    drive.upsert_bytes(VAULT_SESSION_NAME, SQLITE_HDR, folder_id)
    drive.upsert_bytes(VAULT_CREDS_NAME, b"{}", folder_id)
    before = {meta["name"]: meta["_bytes"] for meta in drive.files.values()}

    result = ctx.session_vault.save_after_login()

    assert result.saved is True
    after = {meta["name"]: meta["_bytes"] for meta in drive.files.values()}
    assert before != after


def test_save_after_login_uploads_when_the_vault_is_missing(ctx):
    from teledrive import config

    local = _sqlite_session(Path(config.TELEGRAM_SESSION), b"fresh-login")
    ctx.telegram_auth.state = ta.AUTHORIZED
    ctx.telegram_auth.client = type("C", (), {"session_path": str(local)})()
    ctx.telegram_auth._api_id = 1234567
    ctx.telegram_auth._api_hash = "hash"
    ctx.telegram_auth._phone = "+201234567890"
    drive = _connect_fake_drive(ctx)

    result = ctx.session_vault.save_after_login()

    assert result.ok and result.saved
    names = {meta["name"] for meta in drive.files.values()}
    assert VAULT_SESSION_NAME in names
    assert VAULT_CREDS_NAME in names


def test_save_after_login_is_quiet_without_drive(ctx):
    ctx.telegram_auth.state = ta.AUTHORIZED
    result = ctx.session_vault.save_after_login()
    assert result.ok is False
    assert result.message_key == "msg.session_restore_skipped_no_drive"


def test_snapshot_falls_back_when_backup_is_locked(ctx, monkeypatch):
    from teledrive import config

    vault = ctx.session_vault
    session = vault._local_session_path()
    _write_local_session(session)

    def boom(self, source, dest):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(type(vault), "_checkpoint_sqlite", boom)

    data = vault._snapshot_bytes()

    assert data.startswith(b"SQLite format 3")


def test_format_two_vault_omits_api_hash_and_restores_from_memory(ctx, monkeypatch):
    from teledrive import config

    local = _sqlite_session(Path(config.TELEGRAM_SESSION), b"format-two")
    ctx.telegram_auth.state = ta.AUTHORIZED
    ctx.telegram_auth.client = type("C", (), {"session_path": str(local)})()
    ctx.telegram_auth._api_id = 1234567
    ctx.telegram_auth._api_hash = "restore-hash"
    ctx.telegram_auth._phone = "+201234567890"
    drive = _connect_fake_drive(ctx)

    saved = ctx.session_vault.save_after_login()

    assert saved.saved is True
    creds_meta = next(m for m in drive.files.values() if m["name"] == VAULT_CREDS_NAME)
    payload = json.loads(creds_meta["_bytes"].decode("utf-8"))
    assert payload["format"] == VAULT_FORMAT_ENCRYPTED
    assert "api_hash" not in payload
    session_meta = next(m for m in drive.files.values() if m["name"] == VAULT_SESSION_NAME)
    assert b"format-two" not in session_meta["_bytes"]

    ctx.telegram_auth.state = ta.DISCONNECTED
    ctx.telegram_auth.client = None

    def fake_set_credentials(api_id, api_hash):
        assert api_id == "1234567"
        assert api_hash == "restore-hash"
        ctx.telegram_auth.state = ta.AUTHORIZED
        return type("S", (), {"authorized": True, "state": ta.AUTHORIZED, "account_label": ""})()

    monkeypatch.setattr(ctx.telegram_auth, "set_credentials", fake_set_credentials)
    restored = ctx.session_vault.autorestore()

    assert restored.restored is True
    assert Path(config.TELEGRAM_SESSION).exists()


def test_save_after_login_defers_then_flushes_when_drive_connects(ctx):
    from teledrive import config

    _sqlite_session(Path(config.TELEGRAM_SESSION), b"deferred")
    ctx.telegram_auth.state = ta.AUTHORIZED
    ctx.telegram_auth._api_id = 1234567
    ctx.telegram_auth._api_hash = "hash"

    deferred = ctx.session_vault.save_after_login()

    assert deferred.ok is False
    assert ctx.session_vault.pending is True

    drive = _connect_fake_drive(ctx)
    flushed = ctx.session_vault.flush_pending()

    assert flushed is not None and flushed.saved is True
    assert ctx.session_vault.pending is False
    assert {meta["name"] for meta in drive.files.values()} >= {VAULT_SESSION_NAME, VAULT_CREDS_NAME}


def test_forget_removes_the_legacy_competing_blob(ctx):
    drive = _connect_fake_drive(ctx)
    folder_id = drive.ensure_folder("TeleDrive_AppData")
    drive.upsert_bytes(VAULT_SESSION_NAME, b"session", folder_id)
    drive.upsert_bytes(VAULT_CREDS_NAME, b"{}", folder_id)
    drive.upsert_bytes(SESSION_VAULT_NAME, b"legacy", folder_id)

    result = ctx.session_vault.forget()

    assert result.forgotten is True
    assert {meta["name"] for meta in drive.files.values()} == set()


def test_autorestore_discards_a_revoked_vault(ctx, monkeypatch):
    drive = _connect_fake_drive(ctx)
    folder_id = drive.ensure_folder("TeleDrive_AppData")
    raw = b"SQLite format 3\x00revoked-session"
    drive.upsert_bytes(VAULT_SESSION_NAME, raw, folder_id)
    creds = {
        "api_id": "1234567",
        "api_hash": "legacy-hash",
        "phone": "+201234567890",
        "format": 1,
        "session_file": VAULT_SESSION_NAME,
    }
    drive.upsert_bytes(VAULT_CREDS_NAME, json.dumps(creds).encode("utf-8"), folder_id)

    monkeypatch.setattr(
        ctx.telegram_auth,
        "set_credentials",
        lambda api_id, api_hash: type("S", (), {"authorized": False, "state": ta.READY_FOR_PHONE})(),
    )
    result = ctx.session_vault.autorestore()

    assert result.ok is False
    assert result.message_key == "msg.session_restore_needs_login"
    assert {meta["name"] for meta in drive.files.values()} == set()


def test_action_wrapper_flushes_pending_save(ctx, monkeypatch):
    calls = []
    ctx.session_vault._pending_save = True
    monkeypatch.setattr(ctx.session_vault, "flush_pending", lambda: calls.append("flushed"))

    ctx.handlers.h_telegram_status()

    assert calls == ["flushed"]


def test_status_is_redacted_and_reports_vault_metadata(ctx):
    from teledrive import config

    _sqlite_session(Path(config.TELEGRAM_SESSION), b"status")
    ctx.telegram_auth.state = ta.AUTHORIZED
    ctx.telegram_auth._api_id = 1234567
    ctx.telegram_auth._api_hash = "hash"
    ctx.telegram_auth._phone = "+201234567890"
    _connect_fake_drive(ctx)
    ctx.session_vault.save_after_login()

    status = ctx.session_vault.status()

    assert status["vault_format"] == VAULT_FORMAT_ENCRYPTED
    assert status["phone_label"] != "+201234567890"
    assert {entry["name"] for entry in status["vault_files"]} >= {VAULT_SESSION_NAME, VAULT_CREDS_NAME}
