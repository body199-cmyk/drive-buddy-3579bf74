"""Entry point: launches the Gradio UI on the single ApplicationContext.

Colab proxy contract (M15-T06):

Gradio's default Colab flow prints ``https://localhost:<port>/`` and renders an
inline iframe whose ``src`` is built client-side from
``google.colab.kernel.proxyPort(port)``. That localhost link is NOT a reliable
browser endpoint — the browser must use the official ``*.prod.colab.dev`` proxy
URL — and the inline iframe is fragile behind VPN/proxy settings. This module
instead:

* binds the server to ``0.0.0.0:<port>`` (default 7860) so the Colab runtime
  proxy can reach it;
* obtains the official ``proxyPort(port)`` URL from Python (off Colab it stays
  ``None`` and ``google.colab`` is never imported);
* passes that URL as Gradio's ``root_path`` so assets, ``/config``, events and
  queue requests resolve through the proxy instead of localhost;
* launches with ``share=False`` (no public tunnel, no secrets exposed) and
  ``inline=False`` (a clickable external proxy URL beats a broken iframe);
* prints ONE clear ``TeleDrive URL: <proxy>`` line after the server is
  listening — never a misleading localhost link as the primary URL;
* appends the loopback hosts to ``NO_PROXY``/``no_proxy`` so Gradio's own
  localhost readiness probes ignore the owner's VPN/HTTP proxy. This exempts
  ONLY loopback; it never disables the VPN for external traffic.
"""
from __future__ import annotations

import os
from typing import Any, Optional

from . import bootstrap
from .app_context import ApplicationContext
from .logging_config import get_logger
from .ui import build

_log = get_logger("teledrive.app")

#: Fixed, configurable port the Gradio server binds to. Colab's ``proxyPort``
#: is called with this exact value, so it must be stable and predictable.
DEFAULT_PORT = 7860

#: Bind on every interface so the Colab runtime proxy (which forwards browser
#: requests to the loopback inside the runtime) can reach the server. Gradio
#: maps ``0.0.0.0`` back to ``localhost`` for its own ``local_url`` probes.
BIND_ADDRESS = "0.0.0.0"

#: Loopback hosts that must bypass any HTTP proxy so Gradio's launch-time
#: localhost probes succeed. Scoped to loopback only — external traffic still
#: honours the owner's ``HTTP_PROXY``/``HTTPS_PROXY``.
_LOCALHOST_NO_PROXY = "localhost,127.0.0.1,::1"


def is_colab() -> bool:
    """True only when running inside Google Colab; never imports off Colab.

    ``google.colab`` is imported lazily inside the try-block, so a non-Colab
    runtime never successfully imports it — the attempt fails fast with no side
    effects. This is the safe detection used before touching ``proxyPort``.
    """
    try:
        import google.colab  # type: ignore[import-not-found]  # noqa: F401
        return True
    except Exception:
        return False


def colab_proxy_url(port: int = DEFAULT_PORT) -> str | None:
    """Return the official Colab ``proxyPort(port)`` URL, or ``None`` off Colab.

    Safe to call on any runtime: ``google.colab.output.eval_js`` is imported
    lazily inside the try-block, so a non-Colab machine never imports it and
    never raises. On Colab this evaluates the kernel's ``proxyPort`` JS helper,
    which returns the ``https://...prod.colab.dev/`` URL the browser must use.
    On any failure (not Colab, JS error, kernel unavailable) it returns
    ``None`` so the caller can print an actionable failure instead of guessing.
    """
    try:
        from google.colab.output import eval_js  # type: ignore[import-not-found]
        return str(eval_js(f"google.colab.kernel.proxyPort({int(port)})"))
    except Exception:
        return None


def _merge_no_proxy(existing: str, hosts: str) -> str:
    """Return ``existing`` with every host in ``hosts`` appended, de-duplicated.

    Pure helper so the proxy-bypass logic is unit-testable without touching the
    real environment. Order is preserved; already-present hosts are not added
    again.
    """
    parts = [p.strip() for p in existing.split(",") if p.strip()]
    for host in hosts.split(","):
        host = host.strip()
        if host and host not in parts:
            parts.append(host)
    return ",".join(parts)


def _ensure_localhost_bypasses_proxy() -> None:
    """Append loopback hosts to ``NO_PROXY``/``no_proxy`` before launching.

    Gradio 6.20.0 makes two ``httpx`` calls against ``http://localhost:<port>``
    during ``launch()`` — a ``startup-events`` probe and a ``url_ok`` readiness
    check. If the owner runs a VPN/corporate proxy via ``HTTP_PROXY`` /
    ``HTTPS_PROXY``, those loopback requests are routed through the proxy and
    fail, aborting launch with a misleading "localhost not accessible" error.
    We merge the loopback hosts into ``NO_PROXY``/``no_proxy`` so ONLY loopback
    bypasses the proxy. External traffic (Drive, Telegram) is untouched — this
    is not disabling the VPN globally.
    """
    for var in ("NO_PROXY", "no_proxy"):
        os.environ[var] = _merge_no_proxy(os.environ.get(var, ""), _LOCALHOST_NO_PROXY)


def _launch_kwargs(
    *, share: bool, inline: bool, blocking: bool, port: int, root_path: str | None
) -> dict[str, Any]:
    """Build the exact kwargs passed to ``demo.launch()`` for Gradio 6.20.0.

    The pinned Gradio 6.20.0 ``Blocks.launch`` signature is (positional head)
    ``inline, inbrowser, share, debug, max_threads, auth, auth_message,
    prevent_thread_lock, show_error, server_name, server_port`` and then
    keyword-only ``root_path`` (plus many others). We pass the proxy base as
    ``root_path`` so the frontend config prefixes every asset/API/event URL
    with the Colab proxy origin. ``share`` is always explicit (False by
    default) — Gradio never auto-switches to a public tunnel.
    """
    return {
        "share": share,
        "inline": inline,
        "quiet": True,
        "prevent_thread_lock": not blocking,
        "server_name": BIND_ADDRESS,
        "server_port": int(port),
        "root_path": root_path,
    }


def _print_primary_url(
    *, proxy_url: str | None, port: int, share: bool, on_colab: bool
) -> None:
    """Print exactly ONE usable URL line — never a misleading localhost link.

    * Colab + working proxy → the official ``prod.colab.dev`` URL.
    * Colab + proxy unavailable → a precise, actionable failure; the server is
      still listening on ``0.0.0.0:<port>``, so the state stays explicit.
    * Off Colab (local run) → the loopback URL, which is correct there.
    * ``share=True`` → Gradio prints its own public tunnel URL; we do not
      duplicate it.
    """
    if share:
        return
    if proxy_url:
        print(f"TeleDrive URL: {proxy_url}")
        return
    if on_colab:
        print(
            f"TeleDrive URL: UNAVAILABLE — the Colab proxy URL for port {port} "
            f"could not be obtained. The server is listening on "
            f"{BIND_ADDRESS}:{port}. In a Colab cell, run "
            f"`google.colab.kernel.proxyPort({port})` to fetch the URL, or "
            f"re-run this cell."
        )
    else:
        print(f"TeleDrive URL: http://localhost:{port}/")


def launch(
    ctx: Optional[ApplicationContext] = None,
    share: bool = False,
    inline: bool = False,
    blocking: bool = False,
    port: int = DEFAULT_PORT,
) -> ApplicationContext:
    """Build and launch the UI on ONE context.

    ``ctx`` is the context created by :func:`teledrive.bootstrap.run`. When it
    is omitted the bootstrap runs here, so exactly one context still exists —
    callers must never bootstrap and then let this function bootstrap again.

    ``share`` defaults to False: no public tunnel unless explicitly requested.
    ``inline`` defaults to False: a clickable Colab proxy URL is preferred over
    a fragile inline iframe (M15-T06).
    ``blocking`` defaults to False, so the notebook cell returns immediately and
    the following cells (handoff, tests, maintenance) stay runnable while the UI
    keeps serving. The launch handle is stored on ``ctx.ui`` and is closed by
    :meth:`ApplicationContext.shutdown`. The CLI launcher passes
    ``blocking=True`` because it has no cells after it and the process must stay
    alive.
    ``port`` defaults to 7860, the fixed port the Colab ``proxyPort`` helper is
    called with.

    On Colab this prints ``TeleDrive URL: https://...prod.colab.dev/...`` — the
    one URL that opens from the browser through the official proxy.
    """
    ctx = ctx or bootstrap.run()
    if share:
        from .i18n import t

        _log.warning(t("msg.share_warning"))

    # Detect Colab once; never import google.colab on a non-Colab runtime.
    on_colab = is_colab()
    # Obtain the official proxy URL (None off Colab / on failure). It seeds
    # Gradio's root_path BEFORE launch; it is printed AFTER the server listens.
    proxy_url = colab_proxy_url(port) if (on_colab and not share) else None

    # Loopback must bypass any VPN/HTTP proxy so Gradio's localhost probes pass.
    _ensure_localhost_bypasses_proxy()

    demo: Any = build(ctx)
    ctx.ui = demo
    demo.launch(
        **_launch_kwargs(
            share=share,
            inline=inline,
            blocking=blocking,
            port=port,
            root_path=proxy_url,
        )
    )
    _log.info(
        "ui launched share=%s blocking=%s port=%s colab=%s proxy=%s",
        share,
        blocking,
        port,
        on_colab,
        bool(proxy_url),
    )
    _print_primary_url(proxy_url=proxy_url, port=port, share=share, on_colab=on_colab)
    return ctx
