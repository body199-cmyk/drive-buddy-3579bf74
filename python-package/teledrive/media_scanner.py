"""Scan a Telegram link and produce MediaItem candidates."""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from typing import Any

from .logging_config import get_logger
from .models import MediaItem
from .telegram_links import ParsedLink, peer_id
from .utils import sanitize_filename, slugify, source_key

_log = get_logger("teledrive.scanner")

SCAN_MODES = ("message", "range", "latest", "chat")
MEDIA_TYPES = ("all", "video", "audio", "document", "photo", "voice", "animation", "sticker")
MAX_SCAN_MESSAGES = 1000
MAX_RANGE_MESSAGES = 1000

DEFAULT_SCAN_MODE = "message"

SCAN_FIELDS = ("message_id", "start_id", "end_id", "limit")
MODE_FIELDS: dict[str, tuple[str, ...]] = {
    "message": ("message_id",),
    "range": ("start_id", "end_id"),
    "latest": ("limit",),
    "chat": ("limit",),
}


def fields_for_mode(mode: str) -> dict[str, bool]:
    """Return {field_name: is_used} for one scan mode. Pure lookup: no Telegram
    call, no I/O, no side effects. ``auto`` is the documented legacy alias of
    ``chat`` and is normalized here so callers never special-case it twice."""
    normalized = str(mode or "").strip().lower()
    if normalized == "auto":
        normalized = "chat"
    if normalized not in SCAN_MODES:
        raise ValueError("unsupported scan mode")
    used = MODE_FIELDS[normalized]
    return {name: (name in used) for name in SCAN_FIELDS}


@dataclass(frozen=True)
class ScanRequest:
    mode: str = "chat"
    message_id: int | None = None
    start_id: int | None = None
    end_id: int | None = None
    limit: int = MAX_SCAN_MESSAGES
    media_types: frozenset[str] = frozenset({"all"})

    def validate(self) -> "ScanRequest":
        mode = str(self.mode or "").strip().lower()
        if mode not in SCAN_MODES:
            raise ValueError("unsupported scan mode")
        selected = frozenset(str(x).strip().lower() for x in self.media_types if str(x).strip())
        if not selected:
            selected = frozenset({"all"})
        if "all" not in selected and not selected.issubset(set(MEDIA_TYPES) - {"all"}):
            raise ValueError("unsupported media type")
        limit = max(1, min(int(self.limit or MAX_SCAN_MESSAGES), MAX_SCAN_MESSAGES))
        if mode == "message":
            if self.message_id is None or int(self.message_id) <= 0:
                raise ValueError("message mode requires a positive message id")
        elif mode == "range":
            if self.start_id is None or self.end_id is None:
                raise ValueError("range mode requires start and end ids")
            start, end = int(self.start_id), int(self.end_id)
            if start <= 0 or end < start:
                raise ValueError("invalid message range")
            if end - start + 1 > MAX_RANGE_MESSAGES:
                raise ValueError("message range is too large")
        elif mode == "latest" and limit <= 0:
            raise ValueError("latest mode requires a positive limit")
        return ScanRequest(
            mode=mode,
            message_id=int(self.message_id) if self.message_id is not None else None,
            start_id=int(self.start_id) if self.start_id is not None else None,
            end_id=int(self.end_id) if self.end_id is not None else None,
            limit=limit,
            media_types=selected,
        )


def _media_type_of(msg: Any) -> str:
    if getattr(msg, "photo", None):
        return "photo"
    if getattr(msg, "video", None):
        return "video"
    if getattr(msg, "voice", None):
        return "voice"
    if getattr(msg, "audio", None):
        return "audio"
    if getattr(msg, "sticker", None):
        return "sticker"
    if getattr(msg, "gif", None) or getattr(msg, "animation", None):
        return "animation"
    if getattr(msg, "document", None):
        return "document"
    return "document"


def _matches_media_type(message: Any, requested: frozenset[str]) -> bool:
    return "all" in requested or _media_type_of(message) in requested


async def _iter_requested_messages(
    telegram, parsed: ParsedLink, request: ScanRequest, chat_ref=None
):
    """Iterate through the resolved peer when one is available."""

    request = request.validate()
    target = parsed.chat if chat_ref is None else chat_ref
    if request.mode == "message":
        yield await telegram.get_message(target, request.message_id)
        return
    if request.mode == "range":
        async for message in telegram.iter_messages(
            target,
            min_id=request.start_id - 1,
            max_id=request.end_id + 1,
            reverse=True,
        ):
            yield message
        return
    async for message in telegram.iter_messages(target, limit=request.limit):
        yield message
        if request.mode == "latest" and request.limit and request.limit <= 0:
            break


def _file_meta(msg: Any) -> tuple[str, str, int, str]:
    """(original_name, extension, size_bytes, file_unique_id)."""
    original = ""
    size = 0
    ext = ""
    unique = ""
    doc = getattr(msg, "document", None) or getattr(msg, "video", None) or getattr(msg, "audio", None)
    if doc is not None:
        size = getattr(doc, "size", 0) or 0
        unique = str(getattr(doc, "id", "") or getattr(doc, "file_unique_id", "") or "")
        for attr in getattr(doc, "attributes", []) or []:
            fn = getattr(attr, "file_name", None)
            if fn:
                original = fn
                break
        mime = getattr(doc, "mime_type", "") or ""
        if not ext and mime:
            g = mimetypes.guess_extension(mime) or ""
            ext = g.lstrip(".")
    photo = getattr(msg, "photo", None)
    if photo is not None:
        unique = unique or str(getattr(photo, "id", ""))
        ext = ext or "jpg"
    if original and "." in original:
        ext = original.rsplit(".", 1)[-1].lower()
    if not unique:
        unique = f"m{getattr(msg, 'id', 0)}"
    return original, (ext or "bin").lower(), int(size), unique


async def scan_link(
    telegram,
    parsed: ParsedLink,
    request: ScanRequest | None = None,
    chat_title_hint: str = "",
) -> list[MediaItem]:
    request = (request or ScanRequest()).validate()
    resolver = getattr(telegram, "resolve_entity", None)
    chat_ref = await resolver(parsed.chat) if callable(resolver) else parsed.chat
    entity = await telegram.get_entity(chat_ref)
    chat_id = peer_id(entity)
    chat_title = (
        getattr(entity, "title", None)
        or getattr(entity, "username", None)
        or chat_title_hint
        or "chat"
    )
    items: list[MediaItem] = []

    async def _add(message: Any) -> None:
        if message is None or not getattr(message, "media", None):
            return
        media_type = _media_type_of(message)
        if not _matches_media_type(message, request.media_types):
            return
        original, extension, size, unique = _file_meta(message)
        safe_name = sanitize_filename(
            original or f"{slugify(chat_title)}_{message.id}_{media_type}.{extension}"
        )
        items.append(MediaItem(
            source_key=source_key(chat_id, message.id, unique),
            chat_id=chat_id,
            chat_title=str(chat_title),
            message_id=int(message.id),
            file_unique_id=unique,
            original_name=original,
            safe_name=safe_name,
            media_type=media_type,
            extension=extension,
            size_bytes=size,
            message_date=str(getattr(message, "date", "") or ""),
        ))

    if request.mode == "message" and parsed.message_id is not None:
        # A direct message link remains authoritative when the user chose message mode.
        message = await telegram.get_message(chat_ref, parsed.message_id)
        await _add(message)
    else:
        async for message in _iter_requested_messages(
            telegram, parsed, request, chat_ref
        ):
            await _add(message)
            if len(items) >= MAX_SCAN_MESSAGES:
                break
    return items
