"""C-02 regression: vault forget must never fake success (§17, ADR-004).

Audit 2026-08-23 (HIGH): forget() swallowed delete_file failures with
``except: pass`` and always reported ``forgotten=True``, so a Drive hiccup
left the saved Telegram session on Drive while the UI claimed deletion.
"""
from __future__ import annotations

from tests.mocks.fake_drive import FakeDrive
from teledrive.session_vault import VAULT_CREDS_NAME, VAULT_SESSION_NAME


class _DeletingDrive(FakeDrive):
    """FakeDrive whose delete_file always fails."""

    def __init__(self):
        super().__init__()
        self.delete_calls = 0

    def delete_file(self, file_id):  # noqa: D102 - test double
        self.delete_calls += 1
        raise RuntimeError("drive delete rejected")


def test_forget_reports_failure_when_drive_delete_fails(ctx):
    drive = _DeletingDrive()
    folder_id = drive.ensure_folder("TeleDrive_AppData")
    drive.upsert_bytes(VAULT_SESSION_NAME, b"x", folder_id)
    drive.upsert_bytes(VAULT_CREDS_NAME, b"{}", folder_id)
    from tests.test_session_vault import _connect_fake_drive

    _connect_fake_drive(ctx, drive=drive)

    result = ctx.session_vault.forget()

    assert result.ok is False
    assert result.forgotten is not True
    assert result.message_key == "err.session_forget_failed"
    assert drive.delete_calls >= 2
    # nothing was actually deleted — the sensitive files remain observable
    names = {meta["name"] for meta in drive.files.values()}
    assert VAULT_SESSION_NAME in names
    assert VAULT_CREDS_NAME in names


def test_forget_quiet_preserves_failed_result_without_raising(ctx):
    drive = _DeletingDrive()
    folder_id = drive.ensure_folder("TeleDrive_AppData")
    drive.upsert_bytes(VAULT_SESSION_NAME, b"x", folder_id)
    from tests.test_session_vault import _connect_fake_drive

    _connect_fake_drive(ctx, drive=drive)

    result = ctx.session_vault.forget_quiet()  # must not raise

    assert result.ok is False
    assert result.message_key == "err.session_forget_failed"


def test_successful_delete_still_reports_forgotten(ctx):
    from tests.test_session_vault import _connect_fake_drive

    drive = _connect_fake_drive(ctx)
    folder_id = drive.ensure_folder("TeleDrive_AppData")
    drive.upsert_bytes(VAULT_SESSION_NAME, b"x", folder_id)
    drive.upsert_bytes(VAULT_CREDS_NAME, b"{}", folder_id)

    result = ctx.session_vault.forget()

    assert result.ok is True and result.forgotten
    assert result.message_key == "msg.session_forgotten"
