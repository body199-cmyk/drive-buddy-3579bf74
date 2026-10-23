"""Adaptive, context-wide GetFile request budget with FloodWait backpressure."""
from __future__ import annotations
import asyncio, os, time

def _max_flood_wait() -> int:
    try: value = int(os.environ.get("TELEDRIVE_TG_FLOODWAIT_MAX", "3600"))
    except (TypeError, ValueError): value = 3600
    return max(1, min(value, 86400))

class TelegramRequestPool:
    """Loop-local request gate that freezes on FloodWait and backs off adaptively."""
    def __init__(self, limit: int, max_flood_wait_seconds: int | None = None):
        self.configured_limit = max(1, min(int(limit), 100))
        self.limit = self.configured_limit
        self.max_flood_wait_seconds = max_flood_wait_seconds or _max_flood_wait()
        self._active = 0
        self._blocked_until = 0.0
        self._successes = 0
        self._condition = asyncio.Condition()
    async def acquire(self) -> None:
        async with self._condition:
            while True:
                wait_seconds = self._blocked_until - time.monotonic()
                if wait_seconds > 0:
                    try: await asyncio.wait_for(self._condition.wait(), timeout=wait_seconds)
                    except asyncio.TimeoutError: pass
                    continue
                if self._active < self.limit:
                    self._active += 1
                    return
                await self._condition.wait()
    async def release(self, error: BaseException | None = None) -> None:
        async with self._condition:
            self._active = max(0, self._active - 1)
            seconds = getattr(error, "seconds", None) if error is not None else None
            flood = error is not None and ("floodwait" in type(error).__name__.lower() or "flood wait" in str(error).lower())
            if flood and seconds is not None:
                self.limit = max(1, self.limit // 2)
                self._blocked_until = max(self._blocked_until, time.monotonic() + max(1, min(int(seconds), self.max_flood_wait_seconds)))
            elif error is None:
                self._successes += 1
                if self._successes >= 50:
                    self._successes = 0
                    if self.limit < self.configured_limit: self.limit += 1
            self._condition.notify_all()
    async def __aenter__(self):
        await self.acquire()
        return self
    async def __aexit__(self, exc_type, exc, _tb):
        await self.release(exc)
        return False
    async def snapshot(self) -> dict[str, int]:
        async with self._condition:
            return {"configured_limit": self.configured_limit, "current_limit": self.limit, "active": self._active, "waiting_seconds": max(0, int(self._blocked_until - time.monotonic()))}
