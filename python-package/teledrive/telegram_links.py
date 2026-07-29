"""Parse Telegram links into (kind, chat, message_id?)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


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
_RE_CHANNEL_TOPIC = re.compile(r"^https?://t\.me/c/(?P<cid>\d+)/(?P<thread>\d+)/(?P<mid>\d+)/?$")
_RE_USER = re.compile(r"^https?://t\.me/(?P<user>[A-Za-z0-9_]+)/?$")
_RE_INVITE = re.compile(r"^https?://t\.me/(joinchat/|\+)(?P<hash>[A-Za-z0-9_-]+)/?$")
_RE_SAVED = re.compile(r"^(saved|me)$", re.IGNORECASE)


class InvalidLink(Exception):
    pass


def parse(link: str) -> ParsedLink:
    if not link or not link.strip():
        raise InvalidLink("empty link")
    s = link.strip()

    if _RE_SAVED.match(s):
        return ParsedLink(kind="saved", chat="me", raw=s)

    m = _RE_INVITE.match(s)
    if m:
        return ParsedLink(kind="invite", chat=m.group("hash"), raw=s)

    m = _RE_CHANNEL_TOPIC.match(s)
    if m:
        cid = int(m.group("cid"))
        internal = int(f"-100{cid}")
        return ParsedLink(
            kind="private", chat=internal,
            thread_id=int(m.group("thread")), message_id=int(m.group("mid")), raw=s,
        )

    m = _RE_CHANNEL.match(s)
    if m:
        cid = int(m.group("cid"))
        internal = int(f"-100{cid}")
        return ParsedLink(kind="private", chat=internal, message_id=int(m.group("mid")), raw=s)

    m = _RE_TOPIC.match(s)
    if m:
        return ParsedLink(
            kind="public", chat=m.group("user"),
            thread_id=int(m.group("thread")), message_id=int(m.group("mid")), raw=s,
        )

    m = _RE_MESSAGE.match(s)
    if m:
        return ParsedLink(kind="public", chat=m.group("user"), message_id=int(m.group("mid")), raw=s)

    m = _RE_USER.match(s)
    if m:
        return ParsedLink(kind="username_only", chat=m.group("user"), raw=s)

    raise InvalidLink(f"unrecognized link: {s}")
