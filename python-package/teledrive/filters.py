"""User filters over MediaItem candidates."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

from .models import MediaItem


@dataclass
class FilterSet:
    media_types: set[str] = field(default_factory=set)     # empty = all
    extensions: set[str] = field(default_factory=set)      # lowercase, no dot; empty = all
    min_size: int | None = None
    max_size: int | None = None
    date_from: str | None = None  # ISO
    date_to: str | None = None
    id_from: int | None = None
    id_to: int | None = None
    include_substr: list[str] = field(default_factory=list)
    exclude_substr: list[str] = field(default_factory=list)


def _iso_lt(a: str, b: str) -> bool:
    try:
        return datetime.fromisoformat(a.replace("Z", "+00:00")) < datetime.fromisoformat(b.replace("Z", "+00:00"))
    except Exception:
        return False


def match(item: MediaItem, f: FilterSet) -> bool:
    if f.media_types and item.media_type not in f.media_types:
        return False
    if f.extensions and item.extension.lower().lstrip(".") not in f.extensions:
        return False
    if f.min_size is not None and item.size_bytes < f.min_size:
        return False
    if f.max_size is not None and item.size_bytes > f.max_size:
        return False
    if f.date_from and item.message_date and _iso_lt(item.message_date, f.date_from):
        return False
    if f.date_to and item.message_date and _iso_lt(f.date_to, item.message_date):
        return False
    if f.id_from is not None and item.message_id < f.id_from:
        return False
    if f.id_to is not None and item.message_id > f.id_to:
        return False
    name = (item.original_name or item.safe_name or "").lower()
    if f.include_substr and not any(s.lower() in name for s in f.include_substr):
        return False
    if f.exclude_substr and any(s.lower() in name for s in f.exclude_substr):
        return False
    return True


def apply(items: Iterable[MediaItem], f: FilterSet) -> list[MediaItem]:
    return [it for it in items if match(it, f)]
