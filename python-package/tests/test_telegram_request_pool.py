"""Adaptive Telegram GetFile request budget tests."""
from __future__ import annotations
import asyncio, time
from teledrive.telegram_request_pool import TelegramRequestPool

class FakeFloodWaitError(Exception):
    def __init__(self, seconds: int):
        super().__init__(f"FloodWaitError: wait {seconds} seconds")
        self.seconds = seconds

def test_pool_never_exceeds_configured_inflight_limit():
    pool, active, peak = TelegramRequestPool(3), 0, 0
    async def worker():
        nonlocal active, peak
        async with pool:
            active += 1; peak = max(peak, active)
            await asyncio.sleep(0.005); active -= 1
    async def scenario(): await asyncio.gather(*(worker() for _ in range(20)))
    asyncio.run(scenario())
    assert peak == 3

def test_flood_wait_freezes_new_requests_and_reduces_live_limit():
    pool, elapsed = TelegramRequestPool(8, max_flood_wait_seconds=1), []
    async def scenario():
        try:
            async with pool: raise FakeFloodWaitError(1)
        except FakeFloodWaitError: pass
        assert (await pool.snapshot())["current_limit"] == 4
        started = time.monotonic()
        async with pool: elapsed.append(time.monotonic() - started)
    asyncio.run(scenario())
    assert elapsed and elapsed[0] >= 0.85

def test_flood_wait_cap_is_configurable_and_successes_recover_limit():
    pool = TelegramRequestPool(4, max_flood_wait_seconds=1)
    async def scenario():
        try:
            async with pool: raise FakeFloodWaitError(10)
        except FakeFloodWaitError: pass
        snap = await pool.snapshot()
        assert snap["current_limit"] == 2
        assert snap["waiting_seconds"] <= 1
        for _ in range(100):
            async with pool: pass
        assert (await pool.snapshot())["current_limit"] == 4
    asyncio.run(scenario())
