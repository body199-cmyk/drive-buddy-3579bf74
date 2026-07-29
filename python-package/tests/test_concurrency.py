import asyncio
from teledrive.config import CONFIG, HARD_CONCURRENCY_CAP


def test_concurrency_values():
    CONFIG.concurrency = "safe"; assert CONFIG.concurrency_value() == 1
    CONFIG.concurrency = "balanced"; assert CONFIG.concurrency_value() == 2
    CONFIG.concurrency = "fast"; assert CONFIG.concurrency_value() == 3
    CONFIG.manual_concurrency = 10
    assert CONFIG.concurrency_value() == HARD_CONCURRENCY_CAP
    CONFIG.manual_concurrency = None


def test_semaphore_bound_never_exceeded():
    async def run():
        sem = asyncio.Semaphore(2)
        active = 0
        peak = 0

        async def task():
            nonlocal active, peak
            async with sem:
                active += 1
                peak = max(peak, active)
                await asyncio.sleep(0.01)
                active -= 1

        await asyncio.gather(*(task() for _ in range(10)))
        return peak
    peak = asyncio.get_event_loop().run_until_complete(run()) if False else asyncio.run(run())
    assert peak <= 2
