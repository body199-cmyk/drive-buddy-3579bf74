"""Retry policy: 5 attempts, base 2s, x2, cap 60s, jitter, transient-only."""
from __future__ import annotations

import asyncio
import random

from .config import RETRY_BASE_SECONDS, RETRY_CAP_SECONDS, RETRY_MAX_ATTEMPTS, RETRY_MULTIPLIER
from .error_handler import ClassifiedError, classify


def next_delay(attempt: int) -> float:
    """attempt is 1-based."""
    d = RETRY_BASE_SECONDS * (RETRY_MULTIPLIER ** (attempt - 1))
    d = min(d, RETRY_CAP_SECONDS)
    jitter = random.uniform(0, min(1.0, d * 0.25))
    return d + jitter


def should_retry(err: ClassifiedError, attempt: int) -> bool:
    if not err.retryable or not err.is_transient:
        return False
    return attempt < RETRY_MAX_ATTEMPTS


async def sleep_for_error(err: ClassifiedError, attempt: int) -> None:
    # FloodWait carries its own wait via suggested_action="wait_<n>s".
    if err.code == "TG_FLOOD_WAIT" and err.suggested_action.startswith("wait_"):
        try:
            secs = int(err.suggested_action.split("_", 1)[1].rstrip("s"))
        except ValueError:
            secs = 30
        await asyncio.sleep(min(secs, RETRY_CAP_SECONDS * 3))
        return
    await asyncio.sleep(next_delay(attempt))
