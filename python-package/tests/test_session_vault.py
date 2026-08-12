"""ADR-004: obfuscated Telegram session vault + keep-alive."""
from __future__ import annotations

import json
from pathlib import Path

from teledrive import database as db
from teledrive import session_vault
from teledrive.config import SESSION_VAULT_NAME
from teledrive.session_vault import MAGIC

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
    drive = FakeDrive()
    ctx.drive_client = drive

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
    assert any(m["name"] == SESSION_VAULT_NAME for m in drive.files.values())

    dumped = json.dumps(db.recent_events(limit=500), ensure_ascii=False, default=str)
    assert "vault-hash" not in dumped
    assert SQLITE_HDR.decode("latin1") not in dumped

    auth.logout()
    assert not session_path.exists()
    assert all(m["name"] != SESSION_VAULT_NAME for m in drive.files.values())


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
