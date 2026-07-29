"""Atomic checkpoint export + reconcile with Drive.

Local SQLite is runtime state. Durable state is a JSON snapshot uploaded to
Drive folder DRIVE_APPDATA_FOLDER after every completed transfer.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from . import database as db
from .config import CHECKPOINTS_DIR, DRIVE_APPDATA_FOLDER
from .logging_config import get_logger
from .models import MediaItem
from .utils import atomic_write_bytes, now_iso

_log = get_logger("teledrive.checkpoint")

CHECKPOINT_PREFIX = "teledrive_checkpoint_"


def _snapshot_items() -> list[dict[str, Any]]:
    return [i.to_dict() for i in db.list_items(limit=10_000)]


def make_snapshot() -> dict[str, Any]:
    return {
        "generated": now_iso(),
        "counts": db.counts_by_state(),
        "items": _snapshot_items(),
    }


def persist_local() -> Path:
    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
    snap = make_snapshot()
    path = CHECKPOINTS_DIR / f"{CHECKPOINT_PREFIX}{snap['generated'].replace(':', '-')}.json"
    atomic_write_bytes(path, json.dumps(snap, ensure_ascii=False, indent=2).encode("utf-8"))
    # prune older than 10
    files = sorted(CHECKPOINTS_DIR.glob(f"{CHECKPOINT_PREFIX}*.json"))
    for old in files[:-10]:
        try:
            old.unlink()
        except Exception:
            pass
    return path


def persist(drive=None) -> Optional[str]:
    """Best-effort checkpoint. Never used as a durability guarantee."""
    path = persist_local()
    if drive is None:
        return None
    try:
        folder_id = drive.ensure_folder(DRIVE_APPDATA_FOLDER)
        data = path.read_bytes()
        file_id = drive.upload_bytes(path.name, data, folder_id)
        return file_id
    except Exception as e:
        _log.warning("checkpoint drive upload failed: %s", e)
        return None


def persist_durable(drive) -> str:
    """Export a checkpoint that is PROVEN to be on Drive.

    Any failure raises :class:`CheckpointError`; it never returns ``None``
    silently, because the caller deletes temp files on success only.
    """
    from .errors import CheckpointError
    from .redaction import scan_for_secrets

    if drive is None:
        raise CheckpointError("durable checkpoint requires a Drive service")

    snap = make_snapshot()
    payload = json.dumps(snap, ensure_ascii=False, indent=2)
    hits = scan_for_secrets(payload)
    if hits:
        raise CheckpointError(f"checkpoint refused: {len(hits)} secret pattern(s) matched")

    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
    path = CHECKPOINTS_DIR / f"{CHECKPOINT_PREFIX}{snap['generated'].replace(':', '-')}.json"
    atomic_write_bytes(path, payload.encode("utf-8"))
    for old in sorted(CHECKPOINTS_DIR.glob(f"{CHECKPOINT_PREFIX}*.json"))[:-10]:
        try:
            old.unlink()
        except Exception:
            pass

    try:
        folder_id = drive.ensure_folder(DRIVE_APPDATA_FOLDER)
        file_id = drive.upload_bytes(path.name, payload.encode("utf-8"), folder_id)
    except Exception as exc:
        raise CheckpointError(f"checkpoint upload failed: {exc}") from exc
    if not file_id:
        raise CheckpointError("checkpoint upload returned no file id")
    return file_id



def latest_local() -> Optional[Path]:
    if not CHECKPOINTS_DIR.exists():
        return None
    files = sorted(CHECKPOINTS_DIR.glob(f"{CHECKPOINT_PREFIX}*.json"))
    return files[-1] if files else None


def restore_from_drive(drive) -> Optional[dict[str, Any]]:
    """Pull newest checkpoint from Drive, return parsed dict."""
    try:
        folder_id = drive.find_folder(DRIVE_APPDATA_FOLDER)
        if not folder_id:
            return None
        children = drive.list_children(folder_id)
        candidates = [c for c in children if c["name"].startswith(CHECKPOINT_PREFIX)]
        if not candidates:
            return None
        candidates.sort(key=lambda x: x.get("modifiedTime", ""), reverse=True)
        data = drive.download_bytes(candidates[0]["id"])
        return json.loads(data.decode("utf-8"))
    except Exception as e:
        _log.warning("checkpoint restore failed: %s", e)
        return None


def apply_snapshot(snap: dict[str, Any]) -> int:
    """Import checkpoint items into SQLite (if not present)."""
    n = 0
    for row in snap.get("items", []):
        try:
            item = MediaItem(**{k: v for k, v in row.items() if k in MediaItem.__dataclass_fields__})
            if db.get_item(item.id):
                continue
            db.upsert_item(item)
            n += 1
        except Exception:
            continue
    return n


def reconcile_with_drive(drive) -> dict[str, int]:
    """Reconcile in-flight items against Drive.

    State is NEVER written here: every change goes through QueueManager, the
    only owner of transitions (Constitution Section 9).
    """
    from .queue_manager import QUEUE

    result = {"marked_uploaded": 0, "marked_needsretry": 0, "checked": 0}
    in_flight = ["Downloading", "Uploading", "Downloaded", "Verifying",
                 "UploadedPendingCheckpoint"]
    for item in db.items_in_states(in_flight):
        result["checked"] += 1
        try:
            existing = drive.find_by_source_key(item.source_key)
            found = (
                existing
                and item.size_bytes > 0
                and int(existing.get("size") or 0) == item.size_bytes
            )
            if found:
                moved = QUEUE.try_transition(
                    item.id, "Uploaded",
                    drive_file_id=existing["id"], upload_pct=100.0,
                )
                if moved is None and item.state == "Uploading":
                    QUEUE.try_transition(item.id, "Verifying")
                    QUEUE.try_transition(item.id, "UploadedPendingCheckpoint",
                                         drive_file_id=existing["id"])
                    moved = QUEUE.try_transition(item.id, "Uploaded", upload_pct=100.0)
                if moved is not None:
                    db.add_event(item.id, "reconcile", "found_on_drive")
                    result["marked_uploaded"] += 1
                    continue
            if QUEUE.try_transition(item.id, "NeedsRetry") is not None:
                db.add_event(item.id, "reconcile", "not_found_on_drive")
                result["marked_needsretry"] += 1

        except Exception as e:
            _log.warning("reconcile failed for %s: %s", item.id, e)
    return result
