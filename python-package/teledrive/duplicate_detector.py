"""Detect duplicates in Drive via appProperties(source_key) + size match."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .logging_config import get_logger

_log = get_logger("teledrive.dup")


@dataclass
class DuplicateReport:
    is_duplicate: bool
    drive_file_id: Optional[str]
    reason: str


def check(drive, source_key: str, size_bytes: int) -> DuplicateReport:
    existing = drive.find_by_source_key(source_key)
    if not existing:
        return DuplicateReport(False, None, "no_match")
    remote_size = int(existing.get("size") or 0)
    if remote_size and size_bytes and remote_size == size_bytes:
        return DuplicateReport(True, existing["id"], "source_key_and_size_match")
    if remote_size == 0 or size_bytes == 0:
        return DuplicateReport(True, existing["id"], "source_key_match_unknown_size")
    return DuplicateReport(False, existing["id"], "size_mismatch_conflict")
