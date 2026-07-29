"""The one and only asyncio event loop for the whole TeleDrive process.

Constitution Section 3: `asyncio.new_event_loop()` and `asyncio.run(` may appear
in NO other file of the package. Every coroutine is marshalled onto this loop via
`ctx.aio.run(...)` (blocking) or `ctx.aio.submit(...)` (fire-and-forget future).
"""
from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future
from typing import Any, Awaitable, Coroutine, Optional

from .logging_config import get_logger

_log = get_logger("teledrive.async_runtime")


class AsyncRuntimeError(RuntimeError):
    """Raised when the shared runtime is used before start or after stop."""


class AsyncRuntime:
    """Owns a single background event loop running in a daemon thread."""

    def __init__(self, name: str = "teledrive-loop") -> None:
        self._name = name
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._lock = threading.Lock()

    # ---- lifecycle ----

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None or not self.is_running:
            raise AsyncRuntimeError("async runtime is not started")
        return self._loop

    @property
    def is_running(self) -> bool:
        return (
            self._loop is not None
            and self._thread is not None
            and self._thread.is_alive()
            and not self._loop.is_closed()
        )

    def start(self) -> "AsyncRuntime":
        with self._lock:
            if self.is_running:
                return self
            self._ready.clear()
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(
                target=self._run_forever, name=self._name, daemon=True
            )
            self._thread.start()
            if not self._ready.wait(timeout=10):
                raise AsyncRuntimeError("async runtime failed to start")
            _log.info("async runtime started thread=%s", self._name)
            return self

    def _run_forever(self) -> None:
        assert self._loop is not None
        asyncio.set_event_loop(self._loop)
        self._loop.call_soon(self._ready.set)
        try:
            self._loop.run_forever()
        finally:
            try:
                pending = [t for t in asyncio.all_tasks(self._loop) if not t.done()]
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
            finally:
                self._loop.close()

    def stop(self, timeout: float = 10.0) -> None:
        with self._lock:
            loop, thread = self._loop, self._thread
            if loop is None or thread is None:
                return
            if thread.is_alive() and not loop.is_closed():
                loop.call_soon_threadsafe(loop.stop)
                thread.join(timeout=timeout)
            self._loop = None
            self._thread = None
            self._ready.clear()
            _log.info("async runtime stopped")

    # ---- submission ----

    def submit(self, coro: Coroutine[Any, Any, Any] | Awaitable[Any]) -> "Future[Any]":
        """Schedule a coroutine on the shared loop; returns a concurrent Future."""
        loop = self.loop
        if threading.current_thread() is self._thread:
            raise AsyncRuntimeError("submit() called from inside the runtime loop")
        return asyncio.run_coroutine_threadsafe(coro, loop)

    def run(
        self,
        coro: Coroutine[Any, Any, Any] | Awaitable[Any],
        timeout: float | None = None,
    ) -> Any:
        """Run a coroutine on the shared loop and block for its result."""
        return self.submit(coro).result(timeout)

    def call_soon(self, fn, *args) -> None:
        self.loop.call_soon_threadsafe(fn, *args)
