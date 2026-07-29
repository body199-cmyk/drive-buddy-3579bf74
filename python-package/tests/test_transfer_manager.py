"""PHASE B proof: download -> upload -> verify -> durable checkpoint -> cleanup.

The temp file is deleted ONLY after `persist_durable()` proved the checkpoint
reached Drive. Every failure path keeps the temp file and leaves a RECOVERY
event behind.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from teledrive import checkpoint_manager, database as db
from teledrive.config import TEMP_DIR
from teledrive.errors import CheckpointError, VerificationError
from teledrive.models import MediaItem
from teledrive.queue_manager import QUEUE
from teledrive.transfer_manager import TransferManager

from .mocks.fake_drive import FakeDrive
from .mocks.fake_telegram import FakeDoc, FakeMsg, FakeTelegram

SIZE = 2048


def _item(mid: int = 7, size: int = SIZE) -> MediaItem:
    item = MediaItem(
        source_key=f"tg:42:{mid}",
        chat_id=42,
        message_id=mid,
        original_name=f"clip{mid}.bin",
        safe_name=f"clip{mid}.bin",
        media_type="document",
        extension="bin",
        size_bytes=size,
    )
    QUEUE.enqueue(item)
    return item


def _telegram(mid: int = 7, size: int = SIZE) -> FakeTelegram:
    return FakeTelegram({mid: FakeMsg(id=mid, document=FakeDoc(id="d", size=size))})


def _manager(drive: FakeDrive, tg: FakeTelegram, folder: str = "fld_target") -> TransferManager:
    return TransferManager(tg, drive, folder)


def _run(mgr: TransferManager) -> None:
    asyncio.run(mgr.run())


def _temp_exists(item_id: str) -> bool:
    return (TEMP_DIR / item_id).exists()


def _events(item_id: str, kind: str) -> list[dict]:
    return [e for e in db.recent_events(500) if e["item_id"] == item_id and e["kind"] == kind]


# ---------------------------------------------------------------- happy path


def test_success_verifies_then_checkpoints_then_deletes_the_temp_file():
    item = _item()
    drive = FakeDrive()
    _run(_manager(drive, _telegram()))

    row = db.get_item(item.id)
    assert row.state == "Uploaded"
    assert row.drive_file_id in drive.files
    assert drive.checkpoints, "a durable checkpoint must be uploaded before cleanup"
    assert not _temp_exists(item.id)
    kinds = [e["message"] for e in _events(item.id, "state")]
    assert any("Uploading->Verifying" in k for k in kinds)
    assert any("Verifying->UploadedPendingCheckpoint" in k for k in kinds)
    assert any("UploadedPendingCheckpoint->Uploaded" in k for k in kinds)


def test_state_order_never_reaches_uploaded_before_the_checkpoint():
    item = _item()
    drive = FakeDrive()
    _run(_manager(drive, _telegram()))
    order = [e["message"] for e in reversed(_events(item.id, "state"))]
    seq = [m.split()[0] for m in order]
    assert seq.index("Uploading->Verifying") < seq.index("Verifying->UploadedPendingCheckpoint")
    assert seq.index("Verifying->UploadedPendingCheckpoint") < seq.index(
        "UploadedPendingCheckpoint->Uploaded"
    )


# ------------------------------------------------------------ checkpoint fail


def test_checkpoint_failure_keeps_temp_and_leaves_uploaded_pending_checkpoint():
    item = _item()
    drive = FakeDrive()
    drive.fail_checkpoint = True
    _run(_manager(drive, _telegram()))

    row = db.get_item(item.id)
    assert row.state == "UploadedPendingCheckpoint"
    assert _temp_exists(item.id), "temp MUST survive a failed durable checkpoint"
    assert _events(item.id, "RECOVERY"), "a RECOVERY event must be written"


def test_persist_durable_raises_instead_of_returning_none():
    drive = FakeDrive()
    drive.fail_checkpoint = True
    with pytest.raises(CheckpointError):
        checkpoint_manager.persist_durable(drive)
    with pytest.raises(CheckpointError):
        checkpoint_manager.persist_durable(None)


def test_persist_durable_refuses_a_snapshot_that_contains_a_secret():
    item = _item()
    item.last_error_msg = "login failed api_hash=0123456789abcdef0123456789abcdef"
    db.upsert_item(item)
    with pytest.raises(CheckpointError):
        checkpoint_manager.persist_durable(FakeDrive())


# ------------------------------------------------------------------ mismatch


def test_size_mismatch_on_drive_fails_verification_and_keeps_temp():
    item = _item()
    drive = FakeDrive()
    original = drive.upload_resumable

    def shrink(**kwargs):
        meta = original(**kwargs)
        drive.files[meta["id"]]["size"] = 1
        return meta

    drive.upload_resumable = lambda **kw: shrink(**kw)
    _run(_manager(drive, _telegram()))

    row = db.get_item(item.id)
    assert row.state == "Failed"
    assert row.last_error_code == "VERIFY_FAILED"
    assert _temp_exists(item.id)
    assert _events(item.id, "RECOVERY")


def test_wrong_parent_folder_fails_verification():
    item = _item()
    drive = FakeDrive()
    original = drive.upload_resumable

    def reparent(**kwargs):
        meta = original(**kwargs)
        drive.files[meta["id"]]["parents"] = ["fld_somewhere_else"]
        return meta

    drive.upload_resumable = lambda **kw: reparent(**kw)
    _run(_manager(drive, _telegram()))

    assert db.get_item(item.id).state == "Failed"
    assert _temp_exists(item.id)


def test_missing_app_properties_fails_verification():
    item = _item()
    drive = FakeDrive()
    original = drive.upload_resumable

    def strip(**kwargs):
        meta = original(**kwargs)
        drive.files[meta["id"]]["appProperties"] = {}
        return meta

    drive.upload_resumable = lambda **kw: strip(**kw)
    _run(_manager(drive, _telegram()))

    assert db.get_item(item.id).state == "Failed"


def test_trashed_remote_file_fails_verification():
    drive = FakeDrive()
    meta = drive.upload_resumable(
        file_path=str(_write_temp()), drive_name="a.bin",
        parent_id="fld_target", source_key="tg:42:7",
    )
    drive.files[meta["id"]]["trashed"] = True
    with pytest.raises(VerificationError):
        drive.verify_uploaded(meta["id"], SIZE, "fld_target", "tg:42:7")


def _write_temp() -> Path:
    p = TEMP_DIR / "probe" / "a.bin"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x" * SIZE)
    return p


# --------------------------------------------------------- crash and restart


def test_restart_after_a_crash_does_not_upload_a_duplicate():
    item = _item()
    drive = FakeDrive()
    _run(_manager(drive, _telegram()))
    uploaded = len([f for f in drive.files.values() if f["name"] == item.safe_name])

    # Simulate a crash right after Drive succeeded: the row is back in Pending.
    row = db.get_item(item.id)
    row.state = "Pending"
    db.upsert_item(row)

    _run(_manager(drive, _telegram()))
    again = len([f for f in drive.files.values() if f["name"] == item.safe_name])
    assert again == uploaded, "duplicate detection must skip the already uploaded file"
    assert db.get_item(item.id).state == "Skipped"


def test_interrupted_download_restarts_without_duplicating():
    item = _item(mid=9)
    drive = FakeDrive()
    tg = _telegram(mid=9)
    stalled = {"hit": False}
    real_download = tg.download_media

    async def half_then_fail(message, file_path, progress_cb=None):
        if not stalled["hit"]:
            stalled["hit"] = True
            if progress_cb:
                progress_cb(int(SIZE * 0.42), SIZE)
            raise RuntimeError("connection reset at 42%")
        return await real_download(message, file_path, progress_cb)

    tg.download_media = half_then_fail
    _run(_manager(drive, tg))

    row = db.get_item(item.id)
    assert row.state in ("Uploaded", "Failed", "NeedsRetry", "Pending")
    assert len([f for f in drive.files.values() if f["name"] == item.safe_name]) <= 1


# ------------------------------------------------------- ownership of state


def test_transfer_and_checkpoint_modules_never_write_state_directly():
    root = Path(__file__).resolve().parents[1] / "teledrive"
    for name in ("transfer_manager.py", "checkpoint_manager.py"):
        text = (root / name).read_text(encoding="utf-8")
        assert "item.state =" not in text, f"{name} must not assign item.state"
        assert ".state =" not in text.replace("item.state =", ""), name
