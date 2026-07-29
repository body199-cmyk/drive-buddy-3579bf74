"""Domain data models."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from .utils import new_id, now_iso


STATES = (
    "Pending",
    "Analyzing",
    "Downloading",
    "Downloaded",
    "Uploading",
    "Uploaded",
    "Paused",
    "Failed",
    "Skipped",
    "NeedsRetry",
    "Stopped",
    "Deleted",
)

MEDIA_TYPES = ("photo", "video", "audio", "voice", "document", "animation", "sticker")


@dataclass
class MediaItem:
    id: str = field(default_factory=new_id)
    source_key: str = ""
    chat_id: int = 0
    chat_title: str = ""
    message_id: int = 0
    file_unique_id: str = ""
    original_name: str = ""
    safe_name: str = ""
    media_type: str = "document"
    extension: str = ""
    size_bytes: int = 0
    message_date: str = ""
    state: str = "Pending"
    download_pct: float = 0.0
    upload_pct: float = 0.0
    temp_path: str = ""
    drive_file_id: str = ""
    drive_folder_id: str = ""
    attempts: int = 0
    last_error_code: str = ""
    last_error_msg: str = ""
    priority: int = 100
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "MediaItem":
        return cls(**{k: row.get(k, getattr(cls(), k)) for k in cls.__dataclass_fields__})


@dataclass
class Event:
    id: str = field(default_factory=new_id)
    item_id: str = ""
    kind: str = "info"
    message: str = ""
    at: str = field(default_factory=now_iso)
    data: str = ""  # JSON string


@dataclass
class Settings:
    key: str = ""
    value: str = ""
    updated_at: str = field(default_factory=now_iso)
