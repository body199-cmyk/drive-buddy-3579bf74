"""Local disk management: preflight, temp path, orphan quarantine, cleanup."""
from __future__ import annotations

import shutil
from pathlib import Path

from .config import TEMP_DIR
from .logging_config import get_logger
from .utils import safe_disk_free

_log = get_logger("teledrive.storage")

RESERVE_BYTES = 200 * 1024 * 1024  # keep 200 MB headroom
QUARANTINE = TEMP_DIR / "_quarantine"


def preflight(required_bytes: int) -> tuple[bool, int]:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    free = safe_disk_free(TEMP_DIR)
    return (free >= required_bytes + RESERVE_BYTES, free)


def temp_path_for(item_id: str, safe_name: str) -> Path:
    d = TEMP_DIR / item_id
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{safe_name}.part"


def cleanup_item(item_id: str) -> None:
    d = TEMP_DIR / item_id
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)


def cleanup_verified_temp() -> dict[str, list[str]]:
    """Delete ONLY temp folders whose item is verified Uploaded on Drive.

    Everything else (unknown folders, incomplete transfers, stray files) is
    moved to the quarantine directory for manual review. There is deliberately
    no blind recursive wipe of the temp root anywhere in TeleDrive.
    """
    from . import database as db  # local import keeps module import cheap

    deleted: list[str] = []
    quarantined: list[str] = []
    if not TEMP_DIR.exists():
        return {"deleted": deleted, "quarantined": quarantined}

    QUARANTINE.mkdir(parents=True, exist_ok=True)
    for entry in sorted(TEMP_DIR.iterdir()):
        if entry.name.startswith("_"):
            continue
        item = db.get_item(entry.name) if entry.is_dir() else None
        if item is not None and item.state == "Uploaded" and item.drive_file_id:
            shutil.rmtree(entry, ignore_errors=True)
            deleted.append(entry.name)
            continue
        target = QUARANTINE / entry.name
        try:
            if target.exists():
                shutil.rmtree(target, ignore_errors=True) if target.is_dir() else target.unlink()
            shutil.move(str(entry), str(target))
            quarantined.append(entry.name)
        except Exception as exc:  # pragma: no cover - defensive
            _log.warning("quarantine move failed for %s: %s", entry, exc)
    _log.info("temp cleanup deleted=%d quarantined=%d", len(deleted), len(quarantined))
    return {"deleted": deleted, "quarantined": quarantined}


def quarantine_orphans(known_item_ids: set[str]) -> list[str]:
    QUARANTINE.mkdir(parents=True, exist_ok=True)
    moved: list[str] = []
    if not TEMP_DIR.exists():
        return moved
    for entry in TEMP_DIR.iterdir():
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        if entry.name not in known_item_ids:
            target = QUARANTINE / entry.name
            try:
                if target.exists():
                    shutil.rmtree(target, ignore_errors=True)
                shutil.move(str(entry), str(target))
                moved.append(entry.name)
            except Exception as e:
                _log.warning("quarantine move failed for %s: %s", entry, e)
    return moved
