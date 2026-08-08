"""Redaction for logs, events, checkpoints, handoffs and UI messages.

Constitution Section 11.7: no api id/hash, phone, code, 2FA password, session
string, OAuth token, private URL or raw traceback may leave the process.
"""
from __future__ import annotations

import re

PLACEHOLDER = "<redacted>"

_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # +9715xxxxxxx / 00971... phone numbers
    (re.compile(r"(?<!\w)\+\d[\d\s().-]{6,}\d"), PLACEHOLDER),
    # api_id=... / api_hash=... / code=... / password=... / token=...
    (
        re.compile(
            r"(?i)\b(api[_-]?id|api[_-]?hash|phone|phone_code_hash|code|password|"
            r"passwd|token|access_token|refresh_token|client_secret|session|"
            r"session_string|authorization)\b\s*[:=]\s*['\"]?[^\s,'\"}\]]+"
        ),
        lambda m: f"{m.group(1)}={PLACEHOLDER}",
    ),
    # Bearer / OAuth tokens
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+"), f"Bearer {PLACEHOLDER}"),
    (re.compile(r"\bya29\.[A-Za-z0-9._\-]+"), PLACEHOLDER),
    (re.compile(r"\b1//[A-Za-z0-9._\-]{10,}"), PLACEHOLDER),
    # t.me private invite links
    (re.compile(r"https?://t\.me/(?:joinchat/|\+)[A-Za-z0-9_\-]+"), PLACEHOLDER),
    # Telethon StringSession blobs
    # Telethon StringSession: "1" + URL-safe base64 (no "/" or "+"). Excluding
    # those two characters keeps long filesystem paths from false-positiving.
    (re.compile(r"\b1[A-Za-z0-9=_\-]{80,}\b"), PLACEHOLDER),

)


def redact(text: str) -> str:
    """Redact every known secret shape from a free-text string."""
    if not text:
        return ""
    out = str(text)
    for pattern, repl in _PATTERNS:
        out = pattern.sub(repl, out)
    return out


def redact_mapping(data: dict) -> dict:
    """Redact both keys of interest and any secret-looking values."""
    sensitive = {
        "api_id", "api_hash", "phone", "code", "password", "phone_code_hash",
        "token", "access_token", "refresh_token", "client_secret", "session",
    }
    clean: dict = {}
    for key, value in (data or {}).items():
        if str(key).lower() in sensitive:
            clean[key] = PLACEHOLDER
        elif isinstance(value, dict):
            clean[key] = redact_mapping(value)
        elif isinstance(value, str):
            clean[key] = redact(value)
        else:
            clean[key] = value
    return clean


def safe_exception(exc: BaseException) -> str:
    """One redacted line. Never a traceback — tracebacks stay in the log file."""
    return redact(f"{type(exc).__name__}: {exc}")


def mask_phone(phone: str) -> str:
    """`+9715xxxxxx` -> `+971••••34`. Safe account label, never the full number."""
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) < 4:
        return PLACEHOLDER
    return f"+{digits[:3]}••••{digits[-2:]}"


def scan_for_secrets(text: str) -> list[str]:
    """Return the secret shapes found in ``text``.

    The single gate used before ANY durable export (checkpoint, handoff, ZIP).
    An empty list means the payload is safe to leave the process.
    """
    if not text:
        return []
    hits: list[str] = []
    for pattern, _ in _PATTERNS:
        if pattern.search(str(text)):
            hits.append(pattern.pattern)
    return hits


def assert_no_secrets(text: str, where: str = "payload") -> None:
    hits = scan_for_secrets(text)
    if hits:
        raise ValueError(f"{where}: refused, {len(hits)} secret pattern(s) matched")
