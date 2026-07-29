"""Scan a Telegram link and produce MediaItem candidates."""
from __future__ import annotations

import mimetypes
from typing import Any, Optional

from .logging_config import get_logger
from .models import MediaItem
from .telegram_links import ParsedLink
from .utils import sanitize_filename, slugify, source_key

_log = get_logger("teledrive.scanner")


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


async def scan_link(telegram, parsed: ParsedLink, chat_title_hint: str = "") -> list[MediaItem]:
    """Return MediaItem candidates from a parsed link."""
    items: list[MediaItem] = []
    entity = await telegram.get_entity(parsed.chat)
    chat_id = int(getattr(entity, "id", 0))
    chat_title = getattr(entity, "title", None) or getattr(entity, "username", None) or chat_title_hint or "chat"

    async def _add(msg):
        if msg is None or not (getattr(msg, "media", None)):
            return
        orig, ext, size, unique = _file_meta(msg)
        mt = _media_type_of(msg)
        safe = sanitize_filename(orig or f"{slugify(chat_title)}_{msg.id}_{mt}.{ext}")
        item = MediaItem(
            source_key=source_key(chat_id, msg.id, unique),
            chat_id=chat_id,
            chat_title=str(chat_title),
            message_id=int(msg.id),
            file_unique_id=unique,
            original_name=orig,
            safe_name=safe,
            media_type=mt,
            extension=ext,
            size_bytes=size,
            message_date=str(getattr(msg, "date", "") or ""),
        )
        items.append(item)

    if parsed.message_id is not None:
        # Single message; if it's a grouped album, gather siblings.
        msg = await telegram.get_message(parsed.chat, parsed.message_id)
        grouped_id = getattr(msg, "grouped_id", None) if msg else None
        if grouped_id:
            # Fetch a small window around the message to find album siblings.
            async for m in telegram.iter_messages(
                parsed.chat, min_id=max(0, parsed.message_id - 20), max_id=parsed.message_id + 20
            ):
                if getattr(m, "grouped_id", None) == grouped_id:
                    await _add(m)
        else:
            await _add(msg)
    else:
        # Whole chat, capped
        count = 0
        async for m in telegram.iter_messages(parsed.chat, limit=1000):
            await _add(m)
            count += 1
            if count >= 1000:
                break
    return items
