"""Entry point: launches the Gradio UI on the single ApplicationContext."""
from __future__ import annotations

from typing import Any, Optional

from . import bootstrap
from .app_context import ApplicationContext
from .logging_config import get_logger
from .ui import build

_log = get_logger("teledrive.app")


def launch(
    ctx: Optional[ApplicationContext] = None,
    share: bool = False,
    inline: bool = True,
    blocking: bool = False,
) -> ApplicationContext:
    """Build and launch the UI on ONE context.

    ``ctx`` is the context created by :func:`teledrive.bootstrap.run`. When it
    is omitted the bootstrap runs here, so exactly one context still exists —
    callers must never bootstrap and then let this function bootstrap again.

    ``share`` defaults to False: no public tunnel unless explicitly requested.

    ``blocking`` defaults to False, so the notebook cell returns immediately and
    the following cells (handoff, tests, maintenance) stay runnable while the UI
    keeps serving. The launch handle is stored on ``ctx.ui`` and is closed by
    :meth:`ApplicationContext.shutdown`. The CLI launcher passes
    ``blocking=True`` because it has no cells after it and the process must stay
    alive.
    """
    ctx = ctx or bootstrap.run()
    if share:
        from .i18n import t

        _log.warning(t("msg.share_warning"))
    demo: Any = build(ctx)
    ctx.ui = demo
    demo.launch(
        share=share,
        inline=inline,
        quiet=True,
        prevent_thread_lock=not blocking,
    )
    _log.info("ui launched share=%s blocking=%s", share, blocking)
    return ctx
