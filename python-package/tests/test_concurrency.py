import asyncio

from teledrive.config import CONFIG, CONCURRENCY_WARN_ABOVE, HARD_CONCURRENCY_CAP


def test_hard_cap_is_the_adr_0001_value():
    """ADR-0001: the owner raised the v4.5 cap of 4 to 100."""
    assert HARD_CONCURRENCY_CAP == 100
    assert CONCURRENCY_WARN_ABOVE < HARD_CONCURRENCY_CAP


def test_concurrency_values():
    CONFIG.concurrency = "safe"; assert CONFIG.concurrency_value() == 1
    CONFIG.concurrency = "balanced"; assert CONFIG.concurrency_value() == 2
    CONFIG.concurrency = "fast"; assert CONFIG.concurrency_value() == 3
    CONFIG.concurrency = "turbo"; assert CONFIG.concurrency_value() == 16
    CONFIG.concurrency = "max"; assert CONFIG.concurrency_value() == 100
    CONFIG.concurrency = "balanced"


def test_manual_value_is_honoured_up_to_the_cap():
    CONFIG.manual_concurrency = 37
    assert CONFIG.concurrency_value() == 37
    CONFIG.manual_concurrency = 100
    assert CONFIG.concurrency_value() == 100
    CONFIG.manual_concurrency = 5000
    assert CONFIG.concurrency_value() == HARD_CONCURRENCY_CAP
    CONFIG.manual_concurrency = 0
    assert CONFIG.concurrency_value() == 1
    CONFIG.manual_concurrency = None


def test_semaphore_bound_never_exceeded():
    async def run(limit: int, tasks: int) -> int:
        sem = asyncio.Semaphore(limit)
        active = 0
        peak = 0

        async def task():
            nonlocal active, peak
            async with sem:
                active += 1
                peak = max(peak, active)
                await asyncio.sleep(0.005)
                active -= 1

        await asyncio.gather(*(task() for _ in range(tasks)))
        return peak

    assert asyncio.run(run(2, 10)) <= 2
    assert asyncio.run(run(HARD_CONCURRENCY_CAP, 250)) <= HARD_CONCURRENCY_CAP
