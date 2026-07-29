"""Entry point: launches the Gradio UI on the single ApplicationContext."""
from __future__ import annotations

from typing import Optional

from . import bootstrap
from .app_context import ApplicationContext
from .logging_config import get_logger
from .ui import build

_log = get_logger("teledrive.app")


def launch(
    ctx: Optional[ApplicationContext] = None,
    share: bool = False,
    inline: bool = True,
) -> ApplicationContext:
    """Build and launch the UI on ONE context.

    ``ctx`` is the context created by :func:`teledrive.bootstrap.run`. When it
    is omitted the bootstrap runs here, so exactly one context still exists —
    callers must never bootstrap and then let this function bootstrap again.

    ``share`` defaults to False: no public tunnel unless explicitly requested.
    """
    ctx = ctx or bootstrap.run()
    if share:
        from .i18n import t

        _log.warning(t("msg.share_warning"))
    demo = build(ctx)
    demo.launch(share=share, inline=inline, quiet=True)
    return ctx
