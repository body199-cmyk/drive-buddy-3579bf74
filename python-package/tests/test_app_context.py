"""Phase 1 tests: one shared runtime, one context, strict service resolution."""
from __future__ import annotations

import asyncio

import pytest

from teledrive.app_context import ServicePathError, create_context, reset_context
from teledrive.async_runtime import AsyncRuntime, AsyncRuntimeError


@pytest.fixture()
def ctx():
    c = create_context()
    yield c
    reset_context()


def test_runtime_runs_coroutines_on_one_loop(ctx):
    async def where():
        return id(asyncio.get_running_loop())

    first = ctx.aio.run(where())
    second = ctx.aio.run(where())
    assert first == second == id(ctx.aio.loop)


def test_context_is_a_singleton(ctx):
    assert create_context() is ctx


def test_resolve_returns_bound_method(ctx):
    fn = ctx.resolve("queue_manager.enqueue")
    assert callable(fn)
    assert fn.__self__ is ctx.queue_manager


@pytest.mark.parametrize(
    "path",
    ["queue_manager", "nope.enqueue", "queue_manager.nope", "transfer_manager.run"],
)
def test_resolve_raises(ctx, path):
    with pytest.raises(ServicePathError):
        ctx.resolve(path)


def test_stopped_runtime_refuses_work():
    rt = AsyncRuntime("test-loop")
    rt.start()
    assert rt.run(asyncio.sleep(0, result=7)) == 7
    rt.stop()
    orphan = asyncio.sleep(0)
    try:
        with pytest.raises(AsyncRuntimeError):
            rt.run(orphan)
    finally:
        orphan.close()
