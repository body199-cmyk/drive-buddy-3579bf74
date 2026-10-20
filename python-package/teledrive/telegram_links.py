"""Parse Telegram links into (kind, chat, message_id?)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ParsedLink:
    kind: str          # public | private | invite | saved | username_only
    chat: str | int    # username OR internal id (int) OR invite hash
    message_id: Optional[int] = None
    thread_id: Optional[int] = None
    raw: str = ""


_RE_MESSAGE = re.compile(r"^https?://t\.me/(?P<user>[A-Za-z0-9_]+)/(?P<mid>\d+)/?$")
_RE_TOPIC = re.compile(r"^https?://t\.me/(?P<user>[A-Za-z0-9_]+)/(?P<thread>\d+)/(?P<mid>\d+)/?$")
_RE_CHANNEL = re.compile(r"^https?://t\.me/c/(?P<cid>\d+)/(?P<mid>\d+)/?$")
_RE_CHANNEL_ONLY = re.compile(r"^https?://t\.me/c/(?P<cid>\d+)/?$")
_RE_CHANNEL_TOPIC = re.compile(r"^https?://t\.me/c/(?P<cid>\d+)/(?P<thread>\d+)/(?P<mid>\d+)/?$")
_RE_USER = re.compile(r"^https?://t\.me/(?P<user>[A-Za-z0-9_]+)/?$")
_RE_INVITE = re.compile(r"^https?://t\.me/(joinchat/|\+)(?P<hash>[A-Za-z0-9_-]+)/?$")
_RE_SAVED = re.compile(r"^(saved|me)$", re.IGNORECASE)
_RE_AT_USERNAME = re.compile(r"^@(?P<user>[A-Za-z0-9_]+)$")
_RE_TELEGRAM_HOST = re.compile(
    r"^(?:https?://)?(?:www\.)?(?:telegram\.me|t\.me)/", re.IGNORECASE
)


class InvalidLink(Exception):
    pass


def _normalize_for_matching(value: str) -> str:
    """Canonicalize only spellings Telegram users commonly copy/paste.

    The accepted host remains an allowlist (``t.me``/``telegram.me`` with an
    optional ``www.`` and scheme). Query strings and fragments (for example
    ``?single`` on an album message or tracking parameters copied from a
    browser) do not change the addressed chat/message, so they are ignored
    for matching while ``ParsedLink.raw`` keeps the user's original text.
    The public web-preview ``/s/<user>`` prefix addresses the same peer.
    """
    candidate = value.strip()
    at_match = _RE_AT_USERNAME.match(candidate)
    if at_match:
        return f"https://t.me/{at_match.group('user')}"
    candidate = candidate.split("#", 1)[0].split("?", 1)[0].rstrip()
    candidate = _RE_TELEGRAM_HOST.sub("https://t.me/", candidate, count=1)
    if candidate.startswith("https://t.me/s/"):
        candidate = "https://t.me/" + candidate.removeprefix("https://t.me/s/")
    return candidate


def parse(link: str) -> ParsedLink:
    if not link or not link.strip():
        raise InvalidLink("empty link")
    raw = link.strip()
    s = _normalize_for_matching(raw)

    if _RE_SAVED.match(s):
        return ParsedLink(kind="saved", chat="me", raw=raw)

    m = _RE_INVITE.match(s)
    if m:
        return ParsedLink(kind="invite", chat=m.group("hash"), raw=raw)

    m = _RE_CHANNEL_TOPIC.match(s)
    if m:
        cid = int(m.group("cid"))
        internal = int(f"-100{cid}")
        return ParsedLink(
            kind="private", chat=internal,
            thread_id=int(m.group("thread")), message_id=int(m.group("mid")), raw=raw,
        )

    m = _RE_CHANNEL.match(s)
    if m:
        cid = int(m.group("cid"))
        internal = int(f"-100{cid}")
        return ParsedLink(kind="private", chat=internal, message_id=int(m.group("mid")), raw=raw)

    m = _RE_CHANNEL_ONLY.match(s)
    if m:
        cid = int(m.group("cid"))
        internal = int(f"-100{cid}")
        return ParsedLink(kind="private", chat=internal, raw=raw)

    m = _RE_TOPIC.match(s)
    if m:
        return ParsedLink(
            kind="public", chat=m.group("user"),
            thread_id=int(m.group("thread")), message_id=int(m.group("mid")), raw=raw,
        )

    m = _RE_MESSAGE.match(s)
    if m:
        return ParsedLink(kind="public", chat=m.group("user"), message_id=int(m.group("mid")), raw=raw)

    m = _RE_USER.match(s)
    if m:
        return ParsedLink(kind="username_only", chat=m.group("user"), raw=raw)

    raise InvalidLink(f"unrecognized link: {raw}")


def peer_id(entity: Any) -> int:
    """Return Telethon's canonical marked integer id for a peer.

    Channels and supergroups use ``-100<id>``; legacy groups use ``-<id>``.
    Objects without recognized peer markers are preserved to keep test doubles
    and user references unchanged.
    """

    raw = int(getattr(entity, "id", 0) or 0)
    if raw <= 0:
        return raw
    is_channel = (
        getattr(entity, "broadcast", None) is not None
        or getattr(entity, "megagroup", None) is not None
    )
    if is_channel:
        return int(f"-100{raw}")
    if getattr(entity, "participants_count", None) is not None:
        return -raw
    return raw
