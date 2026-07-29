"""Storage safety: verified temp cleanup never wipes unknown data."""
from __future__ import annotations

from teledrive import database as db, storage_manager
from teledrive.models import MediaItem


def _temp_file(item_id: str, name: str = "file.part"):
    d = storage_manager.temp_root() / item_id
    d.mkdir(parents=True, exist_ok=True)
    path = d / name
    path.write_bytes(b"x")
    return path


def test_only_verified_uploaded_temp_is_deleted():
    uploaded = MediaItem(id="itm-ok", source_key="s1", state="Uploaded")
    uploaded.drive_file_id = "drive-123"
    db.upsert_item(uploaded)
    pending = MediaItem(id="itm-pending", source_key="s2", state="Downloading")
    db.upsert_item(pending)

    _temp_file("itm-ok")
    _temp_file("itm-pending")
    _temp_file("itm-unknown")

    report = storage_manager.cleanup_verified_temp()

    assert report["deleted"] == ["itm-ok"]
    assert sorted(report["quarantined"]) == ["itm-pending", "itm-unknown"]
    assert not (storage_manager.temp_root() / "itm-ok").exists()
    assert (storage_manager.quarantine_dir() / "itm-pending").exists()
    assert (storage_manager.quarantine_dir() / "itm-unknown").exists()


def test_uploaded_without_drive_file_id_is_quarantined_not_deleted():
    item = MediaItem(id="itm-nofid", source_key="s3", state="Uploaded")
    db.upsert_item(item)
    _temp_file("itm-nofid")

    report = storage_manager.cleanup_verified_temp()

    assert "itm-nofid" not in report["deleted"]
    assert "itm-nofid" in report["quarantined"]


def test_cleanup_is_safe_on_an_empty_temp_dir():
    report = storage_manager.cleanup_verified_temp()
    assert report == {"deleted": [], "quarantined": []}


def test_no_blind_rmtree_of_temp_root():
    text = open(storage_manager.__file__, encoding="utf-8").read()
    code = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith(("#", "*"))
    )
    assert "rmtree(storage_manager.temp_root())" not in code
