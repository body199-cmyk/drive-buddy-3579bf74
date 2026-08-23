"""C-01 regression: untrusted checkpoint ids must never escape TEMP_DIR.

Audit 2026-08-23 (HIGH): a crafted checkpoint row with id like ``../outside``
passed validate_snapshot, reached temp_path_for/cleanup_item and could create
or delete directory trees OUTSIDE the temp root.
"""
from __future__ import annotations

import json

import pytest

from teledrive import checkpoint_manager, database as db, storage_manager
from teledrive.models import MediaItem


def _row(item_id: str) -> dict:
    item = MediaItem(id=item_id, source_key="s1", state="Downloading")
    return item.to_dict()


UNSAFE_IDS = [
    "../outside",
    "..\\outside",
    "/absolute",
    "C:/outside",
    "",
    "a" * 129,
]

SAFE_ID = "itm-9f2c1a7b-0000-4a10-8e11-3f6c9d2b5e01"


@pytest.mark.parametrize("bad", UNSAFE_IDS)
def test_validate_snapshot_rejects_unsafe_item_ids(bad):
    snap = {"generated": "2026-08-23T00:00:00Z", "items": [_row(bad)]}
    with pytest.raises(checkpoint_manager.InvalidCheckpointError):
        checkpoint_manager.validate_snapshot(snap)


def test_validate_snapshot_accepts_current_uuid_ids():
    snap = {"generated": "2026-08-23T00:00:00Z", "items": [_row(SAFE_ID)]}
    out = checkpoint_manager.validate_snapshot(snap)
    assert out["items"][0]["id"] == SAFE_ID


@pytest.mark.parametrize("bad", UNSAFE_IDS)
def test_apply_snapshot_fail_closed_before_any_db_write(bad):
    snap = {"generated": "2026-08-23T00:00:00Z", "items": [_row(bad)]}
    with pytest.raises(checkpoint_manager.InvalidCheckpointError):
        checkpoint_manager.apply_snapshot(snap)
    # rejection happened BEFORE any row reached SQLite
    assert db.get_item(bad) is None if bad else True
    assert not db.list_items(limit=100)


def test_temp_path_for_refuses_unsafe_id():
    with pytest.raises(ValueError):
        storage_manager.temp_path_for("../outside", "file.bin")


def test_cleanup_item_refuses_unsafe_id():
    with pytest.raises(ValueError):
        storage_manager.cleanup_item("C:/outside")


def test_paths_stay_inside_temp_root_for_safe_ids():
    path = storage_manager.temp_path_for(SAFE_ID, "file.bin")
    resolved_root = storage_manager.temp_root().resolve()
    assert resolved_root in path.resolve().parents
