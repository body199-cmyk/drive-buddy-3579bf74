"""Central error taxonomy per Constitution D6."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ClassifiedError:
    code: str
    category: str  # transient | permanent | reauth
    user_message_key: str
    is_transient: bool
    retryable: bool
    suggested_action: str
    raw: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "category": self.category,
            "user_message_key": self.user_message_key,
            "is_transient": self.is_transient,
            "retryable": self.retryable,
            "suggested_action": self.suggested_action,
        }


TRANSIENT_MARKERS = (
    "timeout", "timed out", "temporarily", "reset by peer", "connection aborted",
    "connection reset", "connection error", "eof", "ssl", "broken pipe",
    "429", "500", "502", "503", "504", "floodwait", "flood wait",
)

PERMANENT_MARKERS = (
    "invalid link", "not found", "no access", "no permission", "forbidden",
    "insufficient storage", "quota exceeded", "invalid credential", "no media",
    "unsupported", "too large",
)

REAUTH_MARKERS = (
    "unauthorized", "invalid_grant", "authuserrequired", "session expired",
    "expired token", "revoked", "authkey", "auth key",
)


def classify(exc: BaseException) -> ClassifiedError:
    text = f"{type(exc).__name__}: {exc}".lower()

    # Telethon FloodWait — respect the wait seconds if attached.
    if "floodwait" in text or "flood wait" in text:
        seconds = getattr(exc, "seconds", None)
        return ClassifiedError(
            code="TG_FLOOD_WAIT",
            category="transient",
            user_message_key="err.floodwait",
            is_transient=True,
            retryable=True,
            suggested_action=f"wait_{int(seconds) if seconds else 30}s",
            raw=str(exc),
        )

    for m in REAUTH_MARKERS:
        if m in text:
            return ClassifiedError(
                code="AUTH_REQUIRED",
                category="reauth",
                user_message_key="err.reauth",
                is_transient=False,
                retryable=False,
                suggested_action="login_again",
                raw=str(exc),
            )

    for m in PERMANENT_MARKERS:
        if m in text:
            return ClassifiedError(
                code="PERMANENT",
                category="permanent",
                user_message_key="err.permanent",
                is_transient=False,
                retryable=False,
                suggested_action="fix_input_or_permissions",
                raw=str(exc),
            )

    for m in TRANSIENT_MARKERS:
        if m in text:
            return ClassifiedError(
                code="TRANSIENT",
                category="transient",
                user_message_key="err.transient",
                is_transient=True,
                retryable=True,
                suggested_action="auto_retry",
                raw=str(exc),
            )

    # Default: treat as transient once, then it'll drop out via retry cap.
    return ClassifiedError(
        code="UNKNOWN",
        category="transient",
        user_message_key="err.unknown",
        is_transient=True,
        retryable=True,
        suggested_action="auto_retry",
        raw=str(exc),
    )
