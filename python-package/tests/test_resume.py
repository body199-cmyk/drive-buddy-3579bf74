"""Interrupt at 42% -> restart -> reconcile via Drive -> exactly one Drive file."""
import asyncio
from pathlib import Path

import pytest

from teledrive import database as db, checkpoint_manager
from teledrive.models import MediaItem
from teledrive.queue_manager import QUEUE
from teledrive.state_machine import can_transition
from tests.mocks.fake_drive import FakeDrive


def test_reconcile_marks_uploaded_when_found(tmp_path):
    item = QUEUE.enqueue(MediaItem(
        source_key="tg:1:1:u", chat_id=1, message_id=1, file_unique_id="u",
        original_name="a.bin", safe_name="a.bin", media_type="document",
        extension="bin", size_bytes=100,
    ))
    QUEUE.transition(item.id, "Downloading")
    QUEUE.transition(item.id, "Downloaded")
    QUEUE.transition(item.id, "Uploading")
    # simulate crash: leave Uploading

    drive = FakeDrive()
    folder = drive.ensure_folder("TeleDrive_Transfers")
    f = tmp_path / "a.bin"; f.write_bytes(b"y" * 100)
    drive.upload_resumable(str(f), "a.bin", folder, "tg:1:1:u")

    result = checkpoint_manager.reconcile_with_drive(drive)
    assert result["marked_uploaded"] == 1
    assert db.get_item(item.id).state == "Uploaded"
    # Exactly one drive file with this source_key
    hits = [f for f in drive.files.values()
            if f.get("appProperties", {}).get("source_key") == "tg:1:1:u"]
    assert len(hits) == 1


def test_reconcile_marks_needsretry_when_missing():
    item = QUEUE.enqueue(MediaItem(
        source_key="tg:2:2:z", chat_id=2, message_id=2, file_unique_id="z",
        original_name="b.bin", safe_name="b.bin", media_type="document",
        extension="bin", size_bytes=100,
    ))
    QUEUE.transition(item.id, "Downloading")

    drive = FakeDrive()
    drive.ensure_folder("TeleDrive_Transfers")
    result = checkpoint_manager.reconcile_with_drive(drive)
    assert result["marked_needsretry"] == 1
    assert db.get_item(item.id).state == "NeedsRetry"
