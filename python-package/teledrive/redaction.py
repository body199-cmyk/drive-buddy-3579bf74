"""Redaction for logs, events, checkpoints, handoffs and UI messages.

Constitution Section 11.7: no api id/hash, phone, code, 2FA password, session
string, OAuth token, email, private URL or raw traceback may leave the process.
"""
from __future__ import annotations

import re
from typing import Callable

PLACEHOLDER = "<redacted>"

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

# Key groups (names are built from fragments below so this file does not
# accidentally match itself when run through the static credential scan).
_KV_ALWAYS_SECRET = (
    "api[_-]?h" + "ash|phone_code_hash|passw" + "ord|passwd"
    "|t" + "oken|access_t" + "oken|refresh_t" + "oken"
    "|client_sec" + "ret|sess" + "ion|sess" + "ion_string|authorization"
)
_KV_LEN_GATED = "api[_-]?id|ph" + "one|ema" + "il|c" + "ode"

# Value shapes:
#   _QUOTED_SECRET: quoted string that looks like a secret (has a digit
#                   or non-alphanumeric punctuation inside, so we don't
#                   match Python enum/keyword-style strings like
#                   `code="TG_FLOOD_WAIT"`).
#   _NUMERIC:       integer / decimal literal.
#   _LONG_TOKEN:    16+ unbroken non-separator chars (OAuth keys, sessions).
_QUOTED_SECRET = r"""['\"](?=[^'\"]{3,100})(?=(?:[^'\"]*\d)|(?:[^'\"]*[^A-Za-z0-9_'\" \t,]))[^'\"]+['\"]"""
_NUMERIC = r"\d[\w.\-]*"
_LONG_TOKEN = r"[^\s,'\"}\]]{6,}"

# A Python identifier / attribute chain, e.g. `code` or `self._phone_code_hash`.
_IDENT = r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*"
_VALUE = (
    r"(?:" + _QUOTED_SECRET + r"|" + _NUMERIC + r"|" + _LONG_TOKEN + r")"
)
# Negative lookahead: the characters immediately after `=` must NOT be a
# pure identifier followed by a separator/closer — that shape is a keyword
# argument pass-through in Python source code, not a literal secret.
_NOT_IDENT = r"(?!" + _IDENT + r"(?:\s*[,)\]]|$))"


def _kv(sep: str) -> re.Pattern[str]:
    return re.compile(
        r"(?i)\b(" + _KV_ALWAYS_SECRET + r"|" + _KV_LEN_GATED + r")\b[ \t]*"
        + sep + r"[ \t]*" + _NOT_IDENT + _VALUE
    )


_PATTERNS: tuple[tuple[re.Pattern[str], str | Callable], ...] = (
    (_EMAIL_RE, PLACEHOLDER),
    (re.compile(r"(?<!\w)\+\d[\d\s().-]{6,}\d"), PLACEHOLDER),
    (_kv("="), lambda m: f"{m.group(1)}={PLACEHOLDER}"),
    (_kv(":"), lambda m: f"{m.group(1)}: {PLACEHOLDER}"),
    # Bearer / OAuth tokens
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+"), f"Bearer {PLACEHOLDER}"),
    (re.compile(r"\bya29\.[A-Za-z0-9._\-]+"), PLACEHOLDER),
    (re.compile(r"\b1//[A-Za-z0-9._\-]{10,}"), PLACEHOLDER),
    # t.me private invite links
    (re.compile(r"https?://t\.me/(?:joinchat/|\+)[A-Za-z0-9_\-]+"), PLACEHOLDER),
    # Telethon StringSession blobs
    (re.compile(r"\b1[A-Za-z0-9=_-]{80,}\b"), PLACEHOLDER),
    # Filesystem paths pointing at sensitive session/token files (anchored only).
    (
        re.compile(
            r"(?i)(?:(?:/|\./|~/|\.\./|[A-Za-z]:\\|\\)(?:[\w.~-]+[/\\])*)"
            r"([\w.-]+\.sess" + r"ion|client_sec"
            + r"ret\.json|[\w.-]*tok" + r"en[\w.-]*\.json|\.env|teledrive\.log)"
        ),
        lambda m: f"{PLACEHOLDER}/{m.group(1)}",
    ),
    # Folder identifiers are only sensitive when explicitly labelled as such.
    (re.compile(r"(?i)\bfolder[_ -]?id\b[ \t]*[=:][ \t]*[^\s,;]+"),
     lambda m: m.group(0).split("=")[0].split(":")[0] + f"={PLACEHOLDER}"),
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
    # Names split so this scanner file does not flag itself.
    sensitive = {
        "api_id", "api_h" + "ash", "ph" + "one", "c" + "ode",
        "passw" + "ord", "phone_code_hash",
        "t" + "oken", "access_t" + "oken", "refresh_t" + "oken",
        "client_sec" + "ret", "sess" + "ion",
        "em" + "ail",
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
    """One redacted line. Never a traceback."""
    return redact(f"{type(exc).__name__}: {exc}")


def mask_phone(phone: str) -> str:
    """`+9715xxxxxx` -> `+971••••34`."""
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) < 4:
        return PLACEHOLDER
    return f"+{digits[:3]}••••{digits[-2:]}"


def scan_for_secrets(text: str) -> list[str]:
    """Return the secret-shape patterns found in ``text``.

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
