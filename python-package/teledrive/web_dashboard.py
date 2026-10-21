# -*- coding: utf-8 -*-
"""TeleDrive v5.0 Turbo — Modern Web Dashboard (FastAPI + AJAX Polling).

Provenance: merged from the owner's Google Drive WebUI bridge payload
(``TeleDrive_WebUI_GitHub_Bridge.ipynb``), then adapted to this package's
Constitution instead of being copied verbatim:

* **One ApplicationContext, one *application* event loop.** All
  Telegram/Drive/transfer work stays on ``ctx.aio`` — the single shared
  ``AsyncRuntime`` loop. The HTTP server itself runs in its own daemon
  thread with a framework-owned loop, exactly like Gradio's internal
  server thread (M46-T02). This isolation is load-bearing, not
  cosmetic: uvicorn calls ``sys.exit`` when startup fails (e.g. the
  port is taken), and when ``serve()`` previously ran as a task on
  ``ctx.aio`` that ``SystemExit`` tore down the whole application loop
  — the web page never came up *and* the classic Gradio UI froze
  because its handlers marshal work onto the now-dead loop (proven by
  direct reproduction). In a dedicated thread, a dead web server is
  just a dead web server; the application loop is untouched. The sync
  HTTP endpoints still execute in a threadpool and reach application
  coroutines only through the existing handlers, i.e. via
  ``ctx.aio`` — this module never creates a second Telegram client,
  Drive service, or SQLite connection.
* **One transfer engine.** The Drive payload carried its own ad-hoc
  download runner that wrote files straight onto the mounted Drive
  folder and guessed state by scanning checkpoint files on disk. That
  bypassed ``QueueManager`` / ``TransferManager`` (dedupe, resumable
  Drive upload, checkpoints, and the FastTelethon direct-DC
  ``MTProtoSender`` pool inside ``telegram_client.py``). Here every
  action is dispatched through the already-registered handlers via
  ``ctx.handlers.bridge_request`` — the same validated, redacted bridge
  the React panel uses — so the Web UI and Gradio can never diverge.
* **Live data only.** ``/api/metrics`` composes
  ``ctx.progress.snapshot()``, ``ctx.queue_manager.snapshot()`` and the
  browser-safe ``LiveUiStateService`` snapshot. Nothing is synthesized:
  an idle runtime reports an empty queue and zero speed.
* **AJAX polling first.** The browser obeys the persisted refresh setting
  (off, 1s, 2s or 5s; one second by default) and fetches ``api/metrics``
  relative to this page with ``cache: no-store``. This survives the Colab
  ``proxyPort`` proxy where long-lived sockets can be dropped. The ``/ws``
  endpoint stays as an optional enhancement and serves the same payload.
* **No secrets over HTTP.** Authentication actions keep the React
  bridge's secure-Gradio-only refusal, there is no CORS wildcard, log
  lines come from the redacted ``LogService``, and the page renders
  every server string with ``textContent`` (never ``innerHTML``).

FastAPI/uvicorn are imported lazily inside the factory/launch
functions: importing this module — and therefore the classic Gradio
fallback — never depends on them. They are pinned in
``requirements.lock`` like every other dependency.
"""
from __future__ import annotations

import html
import hashlib
from pathlib import Path

import json
import socket
import threading
import time
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from . import __version__
from .logging_config import get_logger
from .redaction import redact

_log = get_logger("teledrive.web_dashboard")

# Fingerprint the actual dashboard module loaded by this runtime. Unlike a
# marketing version label, this changes whenever the shipped dashboard code changes.
try:
    DASHBOARD_BUILD_ID = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
except OSError:  # pragma: no cover - defensive fallback for unusual loaders
    DASHBOARD_BUILD_ID = "unavailable"

#: Fixed port for the Modern Web Dashboard. Distinct from Gradio's 7860
#: so ``Run_Both_Together`` can serve both UIs from the one runtime.
DEFAULT_WEB_PORT = 8765

#: Bind every interface so the Colab runtime proxy can reach the server,
#: exactly like the Gradio launcher (``share=False``: no public tunnel).
BIND_ADDRESS = "0.0.0.0"

#: Queue controls exposed as convenient ``POST /api/queue/<name>``
#: routes. Each maps to the already-registered bridge action id; the
#: mapping is an allowlist — arbitrary action ids stay behind
#: ``/api/action`` with the bridge's own validation.
QUEUE_ACTIONS: dict[str, str] = {
    "start": "queue.start_selected",
    "pause": "queue.pause",
    "resume": "queue.resume",
    "stop": "queue.stop",
    "retry_failed": "queue.retry_failed",
    "refresh": "queue.refresh",
}

_NO_STORE = {"Cache-Control": "no-store, no-cache, must-revalidate"}

#: The three persisted appearance choices shared with the classic UI:
#: light, X-style dim (moderate blue-grey dark), and full dark.
WEB_THEMES = {"light", "dim", "dark"}


def _missing_deps_message() -> str:
    return (
        "Modern Web Dashboard needs fastapi + uvicorn, which are pinned in "
        "requirements.lock; re-run notebook Cell 1 to install them, or "
        "choose Classic_Gradio_Backup in Cell 4."
    )


class TeleDriveWebBridge:
    """Adapt the one live ``ApplicationContext`` to JSON for the Web UI.

    Read paths compose existing snapshots; write paths delegate to
    ``Handlers.bridge_request``. This class owns no runtime, no client,
    no database and no transfer state of its own.
    """

    def __init__(self, ctx: Any) -> None:
        self.ctx = ctx

    # -- read ---------------------------------------------------------

    def _live_state(self) -> dict[str, Any]:
        """Browser-safe snapshot (telegram/drive/queue/candidates)."""
        try:
            return dict(self.ctx.handlers.live_ui_state.snapshot())
        except Exception:  # noqa: BLE001 - metrics must stay available
            _log.warning("web dashboard live-state snapshot failed", exc_info=True)
            return {}

    def get_system_metrics(self) -> dict[str, Any]:
        """The live ``/api/metrics`` payload used by the configurable browser poll."""
        from .config import TEMP_DIR
        from .utils import safe_disk_free

        # TEMP_DIR is created by bootstrap; before that, measure the
        # nearest existing ancestor so the disk card never reports a
        # fabricated 0 on a healthy filesystem.
        disk_path = TEMP_DIR
        while not disk_path.exists() and disk_path.parent != disk_path:
            disk_path = disk_path.parent

        progress: dict[str, Any] = {}
        try:
            progress = dict(self.ctx.progress.snapshot())
            progress.pop("session_start", None)  # monotonic clock, not JSON-meaningful
        except Exception:  # noqa: BLE001
            _log.warning("web dashboard progress snapshot failed", exc_info=True)
        queue: dict[str, Any] = {}
        try:
            queue = dict(self.ctx.queue_manager.snapshot())
        except Exception:  # noqa: BLE001
            _log.warning("web dashboard queue snapshot failed", exc_info=True)

        logs: list[str] = []
        try:
            logs = self.ctx.log_service.tail(40).splitlines()
        except Exception:  # noqa: BLE001
            logs = []

        instant = float(progress.get("instant_speed") or 0.0)
        state = self._live_state()
        preferences = getattr(self.ctx, "preferences", None)
        web_theme = preferences.current_theme() if preferences is not None else "light"
        state["webTheme"] = web_theme if web_theme in WEB_THEMES else "light"
        return {
            "ok": True,
            "version": __version__,
            "build_id": DASHBOARD_BUILD_ID,
            "server_time": time.strftime("%H:%M:%S"),
            "engine": str(queue.get("status") or ""),
            "is_running": bool(getattr(self.ctx.queue_manager, "running", lambda: False)()),
            "counts": {str(k): int(v) for k, v in dict(queue.get("counts") or {}).items()},
            "pending": int(queue.get("pending") or 0),
            "progress": progress,
            "total_speed_mbps": round(instant / (1024 * 1024), 2),
            "free_disk_bytes": int(safe_disk_free(disk_path)),
            "state": state,
            "logs": [redact(line) for line in logs],
        }

    def tail_logs(self, level: str = "ALL", lines: int = 120) -> str:
        return redact(str(self.ctx.log_service.tail(int(lines or 120), str(level or "ALL"))))

    # -- write --------------------------------------------------------

    def action(self, payload: Any) -> dict[str, Any]:
        """Dispatch one ``{requestId, actionId, payload, language}`` request.

        Validation, secret refusal and response redaction are the React
        bridge's — identical semantics to the embedded panel.
        """
        if not isinstance(payload, dict):
            return {
                "requestId": "invalid-request",
                "actionId": "unknown",
                "status": "error",
                "errorKey": "bridge.invalid_request",
                "message": "Invalid bridge request",
            }
        if not str(payload.get("requestId") or "").strip():
            payload = {**payload, "requestId": f"web-{uuid4().hex[:12]}"}
        return dict(self.ctx.handlers.bridge_request(payload))

    def queue_action(self, name: str) -> dict[str, Any]:
        action_id = QUEUE_ACTIONS.get(str(name or "").strip().lower())
        if action_id is None:
            return {
                "ok": False,
                "status": "error",
                "errorKey": "web.unknown_queue_action",
                "message": f"Unknown queue action: {redact(str(name or ''))[:40]}",
            }
        result = self.action(
            {
                "requestId": f"web-queue-{uuid4().hex[:12]}",
                "actionId": action_id,
                "payload": {},
                "language": "ar",
            }
        )
        return {"ok": result.get("status") == "ok", "result": result, "metrics": self.get_system_metrics()}


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl" data-theme="__INITIAL_THEME__">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TeleDrive v5.0 Turbo | لوحة التحكم الحية</title>
<style>
:root{
  color-scheme:light;
  --bg:#f3f6fb; --card:rgba(255,255,255,.96); --border:rgba(15,23,42,.12);
  --text:#172033; --muted:#64748b; --blue:#2563eb; --primary-2:#4f46e5; --green:#15803d;
  --red:#b91c1c; --amber:#b45309; --input:#fff; --surface-2:#e9eef6;
  --log-bg:#f8fafc; --bar-bg:#dbe3ee; --glow:rgba(59,130,246,.12);
  --header-bg:rgba(255,255,255,.90); --selected:rgba(37,99,235,.09);
  --shadow:0 10px 28px rgba(15,23,42,.07); --radius:16px;
}
:root[data-theme="dim"]{
  /* Medium neutral grey: clearly lighter than black, with readable contrast. */
  color-scheme:dark;
  --bg:#383b40; --card:rgba(67,71,77,.98); --border:#62666d;
  --text:#f7f7f7; --muted:#d0d2d5; --blue:#58a6ff; --primary-2:#388bfd; --green:#3fb950;
  --red:#ff7b72; --amber:#e3b341; --input:#50545b; --surface-2:#4a4e55;
  --log-bg:#41454b; --bar-bg:#747982; --glow:rgba(140,170,210,.12);
  --header-bg:rgba(56,59,64,.96); --selected:rgba(88,166,255,.18);
  --shadow:0 12px 30px rgba(0,0,0,.18);
}
:root[data-theme="dark"]{
  color-scheme:dark;
  --bg:#070b14; --card:rgba(15,23,42,.94); --border:rgba(255,255,255,.10);
  --text:#f1f5f9; --muted:#94a3b8; --blue:#3b82f6; --primary-2:#2563eb; --green:#22c55e;
  --red:#ef4444; --amber:#f59e0b; --input:#0b1222; --surface-2:#1e293b;
  --log-bg:#020617; --bar-bg:#1e293b; --glow:rgba(30,58,138,.34);
  --header-bg:rgba(7,11,20,.94); --selected:rgba(59,130,246,.14);
  --shadow:0 12px 30px rgba(0,0,0,.28);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:90px}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Tahoma,Arial,sans-serif;line-height:1.55;
  background:radial-gradient(1200px 600px at 80% -10%,var(--glow),transparent),var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden}
body.drawer-open{overflow:hidden}
*{scrollbar-color:var(--bar-bg) transparent}
.app-shell{width:min(100%,1540px);min-height:100vh;margin:0 auto;display:grid;grid-template-columns:250px minmax(0,1fr);align-items:start}
.sidebar{position:sticky;top:0;height:100vh;height:100dvh;overflow-y:auto;padding:19px 13px 16px;
  border-inline-start:1px solid var(--border);background:var(--header-bg);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px)}
.sidebar-brand{display:flex;align-items:center;gap:11px;padding:4px 9px 18px;border-bottom:1px solid var(--border);margin-bottom:15px}
.brand-mark{width:42px;height:42px;display:inline-flex;align-items:center;justify-content:center;border-radius:14px;
  background:linear-gradient(135deg,var(--blue),var(--primary-2));color:#fff;font-size:21px;box-shadow:0 8px 18px var(--glow)}
.sidebar-brand strong{display:block;font-size:16px;line-height:1.3}
.sidebar-brand small{display:block;color:var(--muted);font-size:11px;margin-top:2px}
.sidebar-caption{padding:0 10px;color:var(--muted);font-size:10px;font-weight:800;letter-spacing:.06em;margin:14px 0 7px}
.side-nav,.drawer-nav{display:grid;gap:5px}
.nav-item{width:100%;min-height:44px;justify-content:flex-start;text-align:right;padding:8px 9px;border:1px solid transparent;
  border-radius:12px;background:transparent;color:var(--muted);box-shadow:none;font-family:inherit;font-size:13px;font-weight:700}
.nav-item:hover{background:var(--surface-2);color:var(--text)}
.nav-item.is-active{background:var(--selected);border-color:var(--border);color:var(--blue)}
.nav-icon{width:29px;height:29px;flex:0 0 auto;display:inline-flex;align-items:center;justify-content:center;border-radius:9px;
  background:var(--surface-2);color:var(--muted);font-size:16px;font-weight:800;line-height:1}
.nav-item.is-active .nav-icon{background:var(--blue);color:#fff}
.nav-label{min-width:0}
.nav-count{margin-inline-start:auto;min-width:22px;padding:2px 6px;border-radius:999px;background:var(--blue);color:#fff;font-size:10px;line-height:1.4;text-align:center}
.nav-count[hidden]{display:none}
.sidebar-footer{margin-top:20px;padding:12px 10px;border:1px solid var(--border);border-radius:14px;background:var(--surface-2)}
.sidebar-state{display:flex;gap:9px;align-items:center}
.sidebar-state strong{display:block;font-size:12px;line-height:1.4}
.sidebar-state small{display:block;color:var(--muted);font-size:10px;margin-top:1px}
.state-dot{width:10px;height:10px;border-radius:50%;flex:0 0 auto;background:var(--amber);box-shadow:0 0 0 4px color-mix(in srgb,var(--amber) 15%,transparent)}
.state-dot.is-good{background:var(--green);box-shadow:0 0 0 4px color-mix(in srgb,var(--green) 15%,transparent)}
.state-dot.is-partial{background:var(--amber);box-shadow:0 0 0 4px color-mix(in srgb,var(--amber) 15%,transparent)}
.sidebar-footer p{margin:9px 0 0;color:var(--muted);font-size:10px;line-height:1.7}
.main-content{min-width:0}
.wrap{width:100%;max-width:1280px;margin:0 auto;padding:14px 16px 44px}
.tab-panel[hidden]{display:none!important}
.mobile-tabs{display:none}
.mobile-drawer{position:fixed;inset:0;z-index:85;display:flex;align-items:center;justify-content:center;padding:24px}
.mobile-drawer[hidden]{display:none!important}
.drawer-backdrop{position:absolute;inset:0;width:100%;height:100%;padding:0;border:0;border-radius:0;background:rgba(0,0,0,.48);box-shadow:none;backdrop-filter:blur(2px)}
.drawer-panel{position:relative;width:min(100%,620px);max-height:min(86vh,820px);overflow:auto;padding:20px;border:1px solid var(--border);border-radius:22px;background:var(--card);box-shadow:0 18px 55px rgba(0,0,0,.24)}
.drawer-handle{display:none}
.drawer-header{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:12px}
.drawer-header p{margin:2px 0 0;color:var(--muted);font-size:12px}
.drawer-tools{padding:12px;margin-bottom:14px;border:1px solid var(--border);border-radius:14px;background:var(--surface-2)}
.drawer-tools h3{font-size:13px;margin:0 0 8px}
.drawer-system-row{display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin-top:10px}
.drawer-nav{grid-template-columns:repeat(2,minmax(0,1fr))}
.app-header{position:static;display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;
  margin:2px 0 14px;padding:12px 14px;border:1px solid var(--border);border-radius:18px;background:var(--header-bg);
  box-shadow:var(--shadow);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px)}
.brand-block{min-width:min(100%,330px);flex:1 1 330px}
h1{font-size:21px;line-height:1.35;margin:0}
h2{font-size:18px;line-height:1.4;margin:0}
.sub{color:var(--muted);font-size:12.5px;margin-top:2px}
.header-actions{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:flex-end}
.pill{border:1px solid var(--border);border-radius:999px;padding:7px 12px;font-size:12.5px;background:var(--card);white-space:nowrap}
.theme-switch{display:inline-flex;gap:3px;align-items:center;border:1px solid var(--border);border-radius:999px;padding:3px;background:var(--surface-2)}
.theme-switch button{background:transparent;color:var(--muted);border-radius:999px;padding:7px 9px;font-size:12px;box-shadow:none}
.theme-switch button[aria-pressed="true"]{background:var(--card);color:var(--text);box-shadow:0 2px 8px rgba(0,0,0,.12)}
.theme-swatch{width:13px;height:13px;border-radius:50%;border:1px solid var(--border);display:inline-block;flex:0 0 auto}
.sw-light{background:#f8fafc}.sw-dim{background:#15202b}.sw-dark{background:#020617}
.overview-panel{padding-top:4px}
.overview-heading{display:flex;align-items:center;gap:12px;margin:4px 1px 11px}
.overview-heading .step-badge{width:40px;height:40px}
.overview-heading p{margin:2px 0 0;color:var(--muted);font-size:12.5px}
.workflow{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin:10px 0}
.workflow-step{display:flex;gap:9px;align-items:center;min-width:0;width:100%;min-height:62px;color:var(--text);text-align:right;
  border:1px solid var(--border);border-radius:14px;padding:9px 10px;background:var(--card);box-shadow:none;font-family:inherit}
.workflow-step:hover{border-color:var(--blue);background:var(--selected)}
.workflow-step.is-active{outline:2px solid var(--blue);outline-offset:1px}
.workflow-step strong{display:block;font-size:13px;line-height:1.35}
.workflow-step small{display:block;color:var(--muted);font-size:11.5px;line-height:1.45;margin-top:1px}
.step-number{width:30px;height:30px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;flex:0 0 auto;
  background:var(--surface-2);color:var(--muted);font-weight:800;border:1px solid var(--border)}
.workflow-step.is-current{border-color:var(--blue)}
.workflow-step.is-current .step-number{background:var(--blue);border-color:var(--blue);color:#fff}
.workflow-step.is-done .step-number{background:var(--green);border-color:var(--green);color:#fff}
.next-step{border:1px solid var(--border);border-radius:14px;padding:10px 13px;background:var(--selected);font-size:13.5px;margin:8px 0 12px}
.next-step strong{color:var(--blue)}
.stats-grid{display:grid;grid-template-columns:repeat(4,minmax(140px,1fr));gap:9px;margin:10px 0 14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:12px 0}
.feature-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:10px;margin:10px 0}
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:15px}
.step-card{margin-top:14px;box-shadow:var(--shadow);scroll-margin-top:118px}
.step-card .feature-grid{margin-bottom:0}
.stat-card{min-height:84px}
.card h3{margin:0 0 8px;font-size:13px;color:var(--muted);font-weight:700}
.section-head{display:flex;gap:11px;align-items:flex-start;margin-bottom:12px}
.section-head p{margin:2px 0 0;color:var(--muted);font-size:12.5px}
.step-badge{width:34px;height:34px;border-radius:12px;display:inline-flex;align-items:center;justify-content:center;flex:0 0 auto;
  background:linear-gradient(135deg,var(--blue),var(--primary-2));color:#fff;font-weight:900;box-shadow:0 6px 16px var(--glow)}
.section-status{margin-inline-start:auto;border:1px solid var(--border);border-radius:999px;padding:5px 10px;color:var(--muted);font-size:12px;white-space:nowrap;background:var(--surface-2)}
.big{font-size:23px;font-weight:800;line-height:1.25;overflow-wrap:anywhere}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
input,select{background:var(--input);color:var(--text);border:1px solid var(--border);
  border-radius:10px;padding:10px 12px;font-size:14px;min-width:0}
input[type=text],input[type=search],input[type=url]{flex:1 1 280px}
input[type=range]{accent-color:var(--blue);padding:0;min-width:180px;flex:1 1 220px}
input[type=checkbox]{width:18px;height:18px;accent-color:var(--blue);padding:0}
button,.link-btn{cursor:pointer;border:0;border-radius:10px;padding:10px 14px;font-size:13.5px;font-weight:700;
  background:linear-gradient(90deg,var(--blue),var(--primary-2));color:#fff;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;gap:6px}
button.alt,.link-btn.alt{background:var(--surface-2);color:var(--text);border:1px solid var(--border)}
button.warn{background:linear-gradient(90deg,#b45309,#d97706)}
button.danger{background:linear-gradient(90deg,#b91c1c,#dc2626)}
button.small{padding:7px 9px;font-size:12px;border-radius:8px}
button:disabled,.link-btn.disabled{opacity:.5;cursor:not-allowed;pointer-events:none}
button:focus-visible,.link-btn:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible,.scroll-pane:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
.analyze-main{display:grid;grid-template-columns:minmax(260px,1fr) minmax(210px,280px) auto;gap:9px;align-items:stretch}
.analyze-main input,.analyze-main select,.analyze-main button{width:100%;height:100%}
.mode-fields{display:flex;flex-wrap:wrap;gap:8px;margin-top:9px}
.mode-fields label{display:flex;flex-direction:column;gap:4px}
.mode-fields input{width:160px;max-width:100%}
.ltr-input{direction:ltr;text-align:left}
.link-hint{border:1px solid var(--border);border-radius:12px;padding:9px 11px;margin-top:9px;background:var(--surface-2);color:var(--muted);font-size:12.5px}
.media-types{border:1px solid var(--border);border-radius:12px;margin:11px 0 0;padding:9px 11px 11px}
.media-types legend{color:var(--muted);font-size:12px;font-weight:700;padding:0 5px}
.chip-check{display:inline-flex;gap:6px;align-items:center;border:1px solid var(--border);border-radius:999px;padding:6px 9px;margin:3px;background:var(--input);font-size:12.5px;cursor:pointer}
.tool-details{border:1px solid var(--border);border-radius:12px;margin-top:11px;background:var(--surface-2);overflow:hidden}
.tool-details summary{cursor:pointer;padding:10px 12px;font-weight:800;font-size:13px}
.tool-details-body{border-top:1px solid var(--border);padding:11px;background:var(--card)}
.filter-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:9px}
.filter-grid label{display:flex;flex-direction:column;gap:4px;color:var(--muted);font-size:12px}
.filter-grid input,.filter-grid select{width:100%}
.detail-line{margin:5px 0;overflow-wrap:anywhere}
.feature-actions{margin-top:10px}
.destination-summary{display:flex;flex-wrap:wrap;gap:8px;align-items:center;border:1px solid var(--border);border-radius:10px;padding:10px 12px;margin:10px 0;background:var(--surface-2)}
.destination-summary strong{overflow-wrap:anywhere}
.folder-list{display:grid;gap:8px;margin:10px 0;height:300px;max-height:48vh;overflow:auto;overscroll-behavior:contain;padding-inline-end:3px}
.folder-row{display:flex;gap:8px;align-items:center;justify-content:space-between;border:1px solid var(--border);border-radius:10px;padding:8px 10px;background:var(--surface-2)}
.folder-name{min-width:0;flex:1;overflow-wrap:anywhere;font-weight:600}
.folder-actions{display:flex;flex-wrap:wrap;gap:6px}
.folder-actions button{padding:7px 10px;font-size:12px}
.results-toolbar,.queue-toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0}
.results-toolbar input[type=search]{flex:1 1 260px}
.results-summary{color:var(--muted);font-size:12.5px}
.scroll-pane{overflow:auto;border:1px solid var(--border);border-radius:13px;background:var(--input);
  overscroll-behavior:contain;scrollbar-gutter:stable}
.candidate-pane{height:430px;max-height:62vh}
.queue-pane{height:350px;max-height:54vh}
.scroll-pane table{min-width:780px}
.scroll-pane thead th{position:sticky;top:0;z-index:3;background:var(--surface-2);box-shadow:0 1px 0 var(--border)}
.scroll-pane tbody tr:hover{background:var(--selected)}
.scroll-pane tbody tr.is-selected{background:var(--selected)}
.pane-footer{display:flex;flex-wrap:wrap;gap:8px;justify-content:space-between;color:var(--muted);font-size:12px;margin-top:7px}
.file-name{font-weight:650;overflow-wrap:anywhere;max-width:460px}
.mono{font-variant-numeric:tabular-nums;white-space:nowrap}
.queue-actions{display:flex;flex-wrap:wrap;gap:5px;min-width:190px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{text-align:right;padding:8px;border-bottom:1px solid var(--border);vertical-align:middle}
.bar{height:7px;border-radius:99px;background:var(--bar-bg);overflow:hidden;min-width:110px}
.bar i{display:block;height:100%;background:linear-gradient(90deg,var(--green),var(--blue))}
#logsBox,.output-box{background:var(--log-bg);border:1px solid var(--border);border-radius:10px;padding:10px;
  font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px;line-height:1.7;
  max-height:280px;overflow:auto;overscroll-behavior:contain;white-space:pre-wrap;word-break:break-word;direction:ltr;text-align:left}
.output-box{max-height:300px}
.note{color:var(--muted);font-size:12px;line-height:1.8}
.msg{min-height:20px;font-size:13px;overflow-wrap:anywhere}
.ok{color:var(--green)} .err{color:var(--red)} .warnT{color:var(--amber)}
.settings-card label{font-weight:750}
.secondary-section{margin-top:14px;scroll-margin-top:118px}
@media(max-width:960px){
  .app-shell{display:block;width:100%}
  .sidebar{display:none}
  .wrap{max-width:none;padding-bottom:100px}
  .mobile-tabs{position:fixed;inset-inline:0;bottom:0;z-index:70;display:grid;grid-template-columns:repeat(6,minmax(0,1fr));
    gap:2px;padding:6px 6px calc(6px + env(safe-area-inset-bottom));border-top:1px solid var(--border);
    background:var(--header-bg);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);box-shadow:0 -8px 24px rgba(0,0,0,.12)}
  .mobile-tab{min-width:0;min-height:48px;display:flex;flex-direction:column;gap:2px;padding:4px 2px;border:0;border-radius:10px;
    background:transparent;color:var(--muted);font-size:10px;line-height:1.1;box-shadow:none}
  .mobile-tab .nav-icon{width:22px;height:22px;border:0;background:transparent;color:currentColor;font-size:16px}
  .mobile-tab.is-active{background:var(--selected);color:var(--blue)}
  .mobile-tab.is-active .nav-icon{background:transparent;color:var(--blue)}
  .mobile-tab:focus-visible{outline:2px solid var(--blue);outline-offset:-2px}
  .mobile-drawer{position:fixed;inset:0;z-index:85;display:flex;align-items:flex-end;justify-content:center}
  .mobile-drawer[hidden]{display:none!important}
  .drawer-backdrop{position:absolute;inset:0;width:100%;height:100%;padding:0;border:0;border-radius:0;background:rgba(0,0,0,.48);box-shadow:none;backdrop-filter:blur(2px)}
  .drawer-panel{position:relative;width:min(100%,600px);max-height:min(78vh,680px);overflow:auto;padding:17px 17px calc(18px + env(safe-area-inset-bottom));
    border:1px solid var(--border);border-bottom:0;border-radius:24px 24px 0 0;background:var(--card);box-shadow:0 -15px 40px rgba(0,0,0,.2)}
  .drawer-handle{width:40px;height:4px;border-radius:99px;margin:0 auto 14px;background:var(--bar-bg)}
  .drawer-header{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:12px}
  .drawer-header p{margin:2px 0 0;color:var(--muted);font-size:12px}
  .drawer-nav{grid-template-columns:repeat(2,minmax(0,1fr))}
  .workflow{grid-template-columns:repeat(2,minmax(0,1fr))}
  .stats-grid{grid-template-columns:repeat(2,minmax(140px,1fr))}
}
/* Universal downloader: keep the core workflow compact on desktop and thumb-friendly on phones. */
#universal .destination-summary{padding:12px;border:1px solid var(--border);border-radius:14px;background:var(--surface-2)}
#universal .destination-summary strong{overflow-wrap:anywhere}
#universal .url-tools{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:0 0 9px;color:var(--muted);font-size:13px}
#universal .url-tools button{flex:0 0 auto;min-height:40px}
#universal .analyze-main{align-items:stretch;gap:10px}
#universal #udlUrlIn{min-width:0;width:100%;min-height:48px}
#universal #udlQualityIn{min-width:0;min-height:46px}
#universal #btnUdlStart{min-height:46px;white-space:normal}
#universal .queue-toolbar{flex-wrap:wrap;align-items:center;gap:8px}
#universal .queue-toolbar h3{flex:1 1 100%;font-size:15px}
#universal .queue-toolbar button{min-height:40px}
#universal .queue-pane{max-width:100%;overscroll-behavior-x:contain}
#universal .queue-pane table{min-width:760px}
#universal .queue-pane th,#universal .queue-pane td{padding:9px 8px;vertical-align:middle}
@media(max-width:720px){
  #universal{padding:13px 11px}
  #universal .section-head{gap:8px}
  #universal .section-head>div{flex:1 1 calc(100% - 55px);min-width:0}
  #universal .section-head h2{font-size:18px;line-height:1.45}
  #universal .section-head p{font-size:12px}
  #universal .section-status{margin-inline-start:0}
  #universal .destination-summary{align-items:stretch!important;gap:9px!important}
  #universal .destination-summary>div{line-height:1.7}
  #universal .destination-summary button{width:100%;min-height:42px}
  #universal .url-tools{align-items:stretch;flex-direction:column;gap:7px;font-size:12px}
  #universal .url-tools button{width:100%;min-height:44px}
  #universal .analyze-main{grid-template-columns:minmax(0,1fr)!important;gap:10px}
  #universal #udlUrlIn{font-size:14px;padding:12px;direction:ltr}
  #universal #udlQualityIn{width:100%;font-size:13px;white-space:normal}
  #universal #btnUdlStart{width:100%;min-height:48px}
  #universal .queue-toolbar{display:flex;align-items:stretch}
  #universal .queue-toolbar h3{flex-basis:100%;font-size:14px}
  #universal .queue-toolbar>span{display:none}
  #universal .queue-toolbar button{flex:1 1 calc(50% - 8px);padding:9px 7px}
  #universal .queue-pane{height:auto;max-height:48vh;min-height:170px;border-radius:12px}
  #universal .queue-pane table{min-width:700px;font-size:12px}
  #universal .queue-pane th,#universal .queue-pane td{padding:8px 7px}
  #universal .msg{overflow-wrap:anywhere}
}
@media(max-width:720px){
  .app-header{align-items:flex-start;gap:9px}
  .brand-block{min-width:0;flex-basis:100%}
  .header-actions{width:100%;gap:6px}
  .header-actions .pill{font-size:11px;padding:6px 8px}
  .build-pill{white-space:normal;overflow-wrap:anywhere;max-width:100%}
  html{scroll-padding-top:100px}
  .wrap{padding:10px 9px 100px}
  .app-header{padding:10px}
  .header-actions{justify-content:flex-start}
  h1{font-size:18px}
  .analyze-main{grid-template-columns:1fr}
  .candidate-pane{height:390px;max-height:58vh}
  .queue-pane{height:330px}
  .folder-row{align-items:flex-start;flex-direction:column}.folder-actions{width:100%}
  .feature-grid{grid-template-columns:1fr}
  .section-head{flex-wrap:wrap}.section-status{margin-inline-start:45px}
}
@media(max-width:480px){
  .workflow{grid-template-columns:1fr 1fr}
  .overview-heading p{font-size:11.5px}
  .drawer-panel{padding-inline:12px}
  .mobile-drawer{align-items:flex-end;padding:0}
  .drawer-panel{width:min(100%,600px);max-height:min(78vh,680px);padding:17px 17px calc(18px + env(safe-area-inset-bottom));border-bottom:0;border-radius:24px 24px 0 0}
  .drawer-handle{display:block;width:40px;height:4px;border-radius:99px;margin:0 auto 14px;background:var(--bar-bg)}
  .drawer-nav{grid-template-columns:repeat(2,minmax(0,1fr))}
  .mobile-tab{font-size:9px}
  .workflow-step{min-height:58px;padding:8px}.step-number{width:27px;height:27px}
  .theme-switch button{padding:6px 7px}.theme-switch .theme-name{display:none}
  .stats-grid{gap:7px}.big{font-size:19px}
}
</style>

</head>
<body data-gradio-available="__GRADIO_AVAILABLE__">
<div class="app-shell">
  <aside class="sidebar" aria-label="التنقل الرئيسي">
    <div class="sidebar-brand">
      <span class="brand-mark" aria-hidden="true">⚡</span>
      <span><strong>TeleDrive</strong><small>لوحة التحكم الحية</small></span>
    </div>
    <p class="sidebar-caption">مساحة العمل</p>
    <nav class="side-nav" aria-label="أقسام TeleDrive">
      <button class="nav-item is-active" type="button" data-section-target="overview" aria-current="page"><span class="nav-icon" aria-hidden="true">⌂</span><span class="nav-label">نظرة عامة</span></button>
      <button class="nav-item" type="button" data-section-target="universal"><span class="nav-icon" aria-hidden="true">🌐</span><span class="nav-label">التحميل الشامل (أي رابط)</span></button>
        <button class="nav-item" type="button" data-section-target="connections"><span class="nav-icon" aria-hidden="true">◎</span><span class="nav-label">الحسابات</span></button>
      <button class="nav-item" type="button" data-section-target="destination"><span class="nav-icon" aria-hidden="true">▣</span><span class="nav-label">مجلد الحفظ</span></button>
      <button class="nav-item" type="button" data-section-target="analyze"><span class="nav-icon" aria-hidden="true">⌕</span><span class="nav-label">تحليل رابط</span></button>
      <button class="nav-item" type="button" data-section-target="results"><span class="nav-icon" aria-hidden="true">☷</span><span class="nav-label">نتائج التحليل</span><span class="nav-count" id="navCandidateCount" hidden></span></button>
      <button class="nav-item" type="button" data-section-target="transfer"><span class="nav-icon" aria-hidden="true">⇄</span><span class="nav-label">الطابور والنقل</span><span class="nav-count" id="navQueueCount" hidden></span></button>
      <button class="nav-item" type="button" data-section-target="settings"><span class="nav-icon" aria-hidden="true">⚙</span><span class="nav-label">الإعدادات</span></button>
      <button class="nav-item" type="button" data-section-target="logs"><span class="nav-icon" aria-hidden="true">≡</span><span class="nav-label">السجلات</span></button>
      <button class="nav-item" type="button" data-section-target="maintenance"><span class="nav-icon" aria-hidden="true">✚</span><span class="nav-label">الصيانة والتصدير</span></button>
    </nav>
    <div class="sidebar-footer">
      <div class="sidebar-state"><span class="state-dot" id="sidebarStateDot" aria-hidden="true"></span><span><strong id="sidebarStateText">جارٍ التحقق…</strong><small>حالة الحسابات</small></span></div>
      <p>تسجيل Telegram يتم عبر واجهة Gradio الآمنة فقط.</p>
    </div>
  </aside>
  <main class="main-content">
    <div class="wrap">
  <header class="app-header">
    <div class="brand-block">
      <h1>⚡ TeleDrive v5.0 Turbo — لوحة التحكم الحية</h1>
      <div class="sub">نفس محرك النقل والطابور الحقيقي، بلا أي بيانات وهمية</div>
    </div>
    <div class="header-actions">
      <div class="pill" id="syncClock">⏳ الاتصال…</div>
      <button class="alt" id="btnHeaderMenu" type="button" aria-haspopup="dialog" aria-expanded="false" aria-controls="mobileMoreDrawer">⚙ الخيارات</button>
    </div>
  </header>

  <nav class="mobile-tabs" aria-label="التنقل بين الأقسام">
    <button class="mobile-tab is-active" type="button" data-section-target="overview" aria-current="page"><span class="nav-icon" aria-hidden="true">⌂</span><span>الرئيسية</span></button>
    <button class="mobile-tab" type="button" data-section-target="destination"><span class="nav-icon" aria-hidden="true">▣</span><span>الوجهة</span></button>
    <button class="mobile-tab" type="button" data-section-target="analyze"><span class="nav-icon" aria-hidden="true">⌕</span><span>تحليل</span></button>
    <button class="mobile-tab" type="button" data-section-target="universal"><span class="nav-icon" aria-hidden="true">🌐</span><span>تحميل شامل</span></button>
    <button class="mobile-tab" type="button" data-section-target="results"><span class="nav-icon" aria-hidden="true">☷</span><span>النتائج</span></button>
    <button class="mobile-tab" type="button" data-section-target="transfer"><span class="nav-icon" aria-hidden="true">⇄</span><span>الطابور</span></button>
    <button class="mobile-tab" id="btnMobileMore" type="button" aria-haspopup="dialog" aria-expanded="false" aria-controls="mobileMoreDrawer"><span class="nav-icon" aria-hidden="true">⋯</span><span>المزيد</span></button>
  </nav>
  <div class="mobile-drawer" id="mobileMoreDrawer" hidden>
    <button class="drawer-backdrop" id="btnCloseMoreBackdrop" type="button" aria-label="إغلاق قائمة الأقسام"></button>
    <section class="drawer-panel" role="dialog" aria-modal="true" aria-labelledby="drawerTitle" tabindex="-1">
      <div class="drawer-handle" aria-hidden="true"></div>
      <div class="drawer-header"><div><h2 id="drawerTitle">القائمة والإعدادات</h2><p>اختصارات الأقسام، المظهر، وتحديث حالة النظام.</p></div><button class="alt small" id="btnCloseMore" type="button">إغلاق</button></div>
      <section class="drawer-tools" aria-label="إعدادات سريعة">
        <h3>مظهر الواجهة</h3>
        <div class="theme-switch" role="group" aria-label="اختيار لون الواجهة">
          <button type="button" data-theme-choice="light" aria-pressed="false" title="المظهر الفاتح"><span class="theme-swatch sw-light"></span><span class="theme-name">فاتح</span></button>
          <button type="button" data-theme-choice="dim" aria-pressed="false" title="رمادي متوسط بين الأسود والأبيض"><span class="theme-swatch sw-dim"></span><span class="theme-name">رمادي متوسط</span></button>
          <button type="button" data-theme-choice="dark" aria-pressed="false" title="المظهر الداكن الكامل"><span class="theme-swatch sw-dark"></span><span class="theme-name">داكن</span></button>
        </div>
        <div class="drawer-system-row">
          <button class="alt" id="btnRefreshMetrics" type="button">🔄 تحديث الحالة الآن</button>
          <div class="pill build-pill" id="buildInfo" title="بصمة كود الواجهة المحمّل">الإصدار: جارٍ التحقق…</div>
        </div>
      </section>
      <nav class="drawer-nav" aria-label="أقسام إضافية">
        <button class="nav-item" type="button" data-section-target="universal"><span class="nav-icon" aria-hidden="true">🌐</span><span class="nav-label">التحميل الشامل (أي رابط)</span></button>
        <button class="nav-item" type="button" data-section-target="connections"><span class="nav-icon" aria-hidden="true">◎</span><span class="nav-label">الحسابات</span></button>
        <button class="nav-item" type="button" data-section-target="settings"><span class="nav-icon" aria-hidden="true">⚙</span><span class="nav-label">الإعدادات</span></button>
        <button class="nav-item" type="button" data-section-target="logs"><span class="nav-icon" aria-hidden="true">≡</span><span class="nav-label">السجلات</span></button>
        <button class="nav-item" type="button" data-section-target="maintenance"><span class="nav-icon" aria-hidden="true">✚</span><span class="nav-label">الصيانة والتصدير</span></button>
      </nav>
    </section>
  </div>

  <section class="tab-panel overview-panel" id="overview" data-tab-panel="overview" aria-labelledby="overviewTitle">
    <div class="overview-heading">
      <span class="step-badge" aria-hidden="true">⌂</span>
      <div><h2 id="overviewTitle" tabindex="-1">نظرة عامة</h2><p>حالة المحرك والحسابات، مع مسار سريع لأهم خطوات النقل.</p></div>
    </div>
    <nav class="workflow" aria-label="مسار العمل بالترتيب">
      <button class="workflow-step is-current" type="button" id="stepLinkConnect" data-section-target="connections"><span class="step-number">1</span><span><strong>الاتصال بالحسابات</strong><small id="stepConnectHint">Telegram وDrive</small></span></button>
      <button class="workflow-step" type="button" id="stepLinkDestination" data-section-target="destination"><span class="step-number">2</span><span><strong>اختيار مجلد Drive</strong><small id="stepDestinationHint">وجهة الحفظ</small></span></button>
      <button class="workflow-step" type="button" id="stepLinkAnalyze" data-section-target="analyze"><span class="step-number">3</span><span><strong>تحليل الرابط</strong><small id="stepAnalyzeHint">رسالة أو قناة</small></span></button>
      <button class="workflow-step" type="button" id="stepLinkResults" data-section-target="results"><span class="step-number">4</span><span><strong>تحديد الملفات</strong><small id="stepResultsHint">راجع واختر المطلوب</small></span></button>
      <button class="workflow-step" type="button" id="stepLinkTransfer" data-section-target="transfer"><span class="step-number">5</span><span><strong>النقل والمتابعة</strong><small id="stepTransferHint">الطابور والتقدم</small></span></button>
    </nav>
    <div class="next-step" id="nextStep" role="status"><strong>الخطوة التالية:</strong> <span id="nextStepText">جارٍ قراءة الحالة الحية…</span></div>
  <div class="stats-grid" aria-label="نظرة سريعة على الحالة">
    <div class="card stat-card"><h3>حالة المحرك</h3><div class="big" id="mState">—</div></div>
    <div class="card stat-card"><h3>السرعة اللحظية</h3><div class="big"><span id="mSpeed">0</span> <small>MB/s</small></div></div>
    <div class="card stat-card"><h3>اكتمل</h3><div class="big" id="mDone">0</div></div>
    <div class="card stat-card"><h3>فشل / تم تخطيه</h3><div class="big"><span id="mFail">0</span> / <span id="mSkip">0</span></div></div>
    <div class="card stat-card"><h3>في الانتظار</h3><div class="big" id="mPending">0</div></div>
    <div class="card stat-card"><h3>مساحة حرة</h3><div class="big"><span id="mDisk">—</span></div></div>
    <div class="card stat-card"><h3>Telegram</h3><div class="big" id="mTg" style="font-size:16px">—</div></div>
    <div class="card stat-card"><h3>Google Drive</h3><div class="big" id="mDrive" style="font-size:16px">—</div></div>
  </div>
  </section>

  <section class="card step-card tab-panel" id="connections" data-tab-panel="connections" hidden aria-labelledby="connectionsTitle">
    <div class="section-head"><span class="step-badge">1</span><div><h2 id="connectionsTitle" tabindex="-1">الاتصال بالحسابات</h2><p>تأكد أن Telegram وGoogle Drive متصلان قبل التحليل والنقل.</p></div><span class="section-status" id="connectionsStatus">جارٍ التحقق…</span></div>
    <div class="feature-grid">
    <section class="card" aria-labelledby="telegramTitle">
      <h3 id="telegramTitle">🔐 حساب Telegram</h3>
      <p class="detail-line">الحالة: <strong id="telegramStatus">—</strong></p>
      <p class="detail-line">الحساب الحالي: <strong id="telegramAccount">—</strong></p>
      <div class="row feature-actions">
        <a class="link-btn" id="telegramLoginLink" href="__GRADIO_URL__" target="_blank" rel="noopener noreferrer">🔑 تسجيل الدخول / تبديل الحساب بأمان ↗</a>
        <button class="alt" id="btnTelegramStatus" type="button">تحديث الحالة</button>
        <button class="danger" id="btnTelegramLogout" type="button">تسجيل الخروج</button>
      </div>
      <p class="note">لأمان الحساب، إدخال API ID وAPI Hash والهاتف ورمز التحقق وكلمة مرور 2FA يتم في حقول Gradio الآمنة فقط، وليس هنا. تسجيل الخروج يمسح الجلسة المحفوظة للحساب الحالي.</p>
      <div class="msg" id="telegramMsg"></div>
    </section>

    <section class="card" aria-labelledby="driveTitle">
      <h3 id="driveTitle">☁️ حساب Google Drive</h3>
      <p class="detail-line">الحالة: <strong id="driveStatus">—</strong></p>
      <p class="detail-line">الحساب: <strong id="driveAccount">—</strong></p>
      <p class="detail-line">المساحة: <strong id="driveQuota">—</strong></p>
      <div class="row feature-actions">
        <button id="btnDriveConnect" type="button">ربط Drive</button>
        <button class="alt" id="btnDriveReconnect" type="button">إعادة الربط</button>
        <button class="alt" id="btnDriveStatus" type="button">تحديث الحالة</button>
        <button class="alt" id="btnDriveQuota" type="button">تحديث المساحة</button>
      </div>
      <div class="msg" id="driveMsg"></div>
    </section>
    </div>
  </section>

  <section class="card step-card tab-panel" id="destination" data-tab-panel="destination" hidden aria-labelledby="destinationTitle">
    <div class="section-head"><span class="step-badge">2</span><div><h2 id="destinationTitle" tabindex="-1">اختيار مجلد الحفظ في Google Drive</h2><p>حدّد المكان الذي ستصل إليه الملفات بعد اكتمال النقل.</p></div><span class="section-status" id="destinationStatus">لم يتم الاختيار</span></div>
    <div class="destination-summary">
      <span>المجلد المحدد للنقل:</span>
      <strong id="selectedFolderName" class="err">لم يتم اختيار مجلد</strong>
    </div>
    <p class="note">افتح المجلد للدخول إليه، أو اختره مباشرة كوجهة للحفظ. إنشاء مجلد جديد سيختاره تلقائيًا.</p>
    <div class="row">
      <button class="alt" id="btnFolderUp" type="button" disabled>⬆ المجلد الأعلى</button>
      <button class="alt" id="btnFolderRefresh" type="button" disabled>🔄 تحديث المجلدات</button>
      <span class="note" id="folderBreadcrumb">My Drive</span>
    </div>
    <div class="folder-list" id="folderList" aria-live="polite"><div class="note">اربط Google Drive أولًا لعرض المجلدات.</div></div>
    <div class="row">
      <input type="text" id="newFolderName" placeholder="اسم المجلد الجديد" aria-label="اسم المجلد الجديد" disabled>
      <button id="btnCreateFolder" type="button" disabled>＋ إنشاء مجلد هنا</button>
    </div>
    <div class="msg" id="folderMsg"></div>
  </section>

  <section class="card step-card tab-panel" id="analyze" data-tab-panel="analyze" hidden aria-labelledby="analyzeTitle">
    <div class="section-head"><span class="step-badge">3</span><div><h2 id="analyzeTitle" tabindex="-1">تحليل رابط تيليجرام</h2><p>الصق رابط قناة أو مجموعة أو رسالة. الوضع التلقائي يتعرف على نوع الرابط ويختار طريقة الفحص المناسبة.</p></div><span class="section-status" id="analyzeStatus">بانتظار رابط</span></div>
    <div class="analyze-main">
      <input class="ltr-input" type="text" id="linkIn" dir="ltr" inputmode="url" autocomplete="off" spellcheck="false" placeholder="https://t.me/channel أو https://t.me/channel/123 أو @channel" aria-label="رابط تيليجرام">
      <select id="modeIn" aria-label="وضع التحليل">
        <option value="auto" selected>تلقائي — يتعرف على الرابط (موصى به)</option>
        <option value="message">رسالة محددة</option>
        <option value="range">نطاق رسائل</option>
        <option value="latest">أحدث رسائل</option>
        <option value="chat">قناة/محادثة حتى حد الرسائل</option>
      </select>
      <button id="btnAnalyze" type="button">🔍 تحليل الرابط</button>
    </div>
    <div class="row" style="margin-top:8px">
      <button class="alt small" id="btnRememberLink" type="button">💾 تذكّر هذا الرابط</button>
      <button class="alt small" id="btnClearRememberedLink" type="button">مسح الرابط المحفوظ</button>
    </div>
    <div class="link-hint" id="linkHint" role="status">الصق رابطًا وسيظهر هنا ما سيتم تحليله بالضبط قبل التنفيذ.</div>
    <div class="mode-fields">
      <label class="note" id="fldMessageId">رقم الرسالة (اختياري إن كان داخل الرابط)
        <input type="number" id="messageIdIn" min="1"></label>
      <label class="note" id="fldStartId">من رسالة رقم
        <input type="number" id="startIdIn" min="1"></label>
      <label class="note" id="fldEndId">إلى رسالة رقم
        <input type="number" id="endIdIn" min="1"></label>
      <label class="note" id="fldLimit">أقصى عدد رسائل للفحص (1–1000)
        <input type="number" id="limitIn" min="1" max="1000" value="200"></label>
    </div>
    <fieldset class="media-types">
      <legend>أنواع الملفات المطلوبة في التحليل والتصفية</legend>
      <label class="chip-check"><input type="checkbox" class="media-type-in" value="all" checked> الكل</label>
      <label class="chip-check"><input type="checkbox" class="media-type-in" value="video"> فيديو</label>
      <label class="chip-check"><input type="checkbox" class="media-type-in" value="audio"> صوت</label>
      <label class="chip-check"><input type="checkbox" class="media-type-in" value="document"> مستندات</label>
      <label class="chip-check"><input type="checkbox" class="media-type-in" value="photo"> صور</label>
      <label class="chip-check"><input type="checkbox" class="media-type-in" value="voice"> رسائل صوتية</label>
      <label class="chip-check"><input type="checkbox" class="media-type-in" value="animation"> متحركة</label>
      <label class="chip-check"><input type="checkbox" class="media-type-in" value="sticker"> ملصقات</label>
    </fieldset>
    <div class="msg" id="analyzeMsg" role="status"></div>
  </section>

  <section class="card step-card tab-panel" id="results" data-tab-panel="results" hidden aria-labelledby="resultsTitle">
    <div class="section-head"><span class="step-badge">4</span><div><h2 id="resultsTitle" tabindex="-1">نتائج التحليل وتحديد الملفات</h2><p>النتيجة <strong id="cCount">0</strong> ملف · المحدد <strong id="cSel">0</strong> · حجم المحدد <strong id="cSelectedSize">—</strong></p></div><span class="section-status" id="resultsStatus">لا توجد نتائج</span></div>
    <div class="results-toolbar">
      <input type="search" id="candidateSearchIn" placeholder="ابحث داخل النتائج بالاسم أو النوع أو رقم الرسالة…" aria-label="بحث داخل نتائج التحليل">
      <button class="alt" id="btnSelectAll" type="button">تحديد الكل</button>
      <button class="alt" id="btnClearSel" type="button">مسح التحديد</button>
      <button id="btnEnqueue" type="button">➕ إضافة المحدد للطابور</button>
    </div>
    <div class="msg" id="selectionMsg" role="status"></div>
    <div class="scroll-pane candidate-pane" id="candidatePane" tabindex="0" aria-label="قائمة نتائج التحليل القابلة للتمرير داخليًا">
      <table><thead><tr><th>تحديد</th><th>الملف</th><th>رقم الرسالة</th><th>النوع</th><th>الحجم</th><th>المصدر والتاريخ</th></tr></thead>
      <tbody id="cBody"><tr><td colspan="6" class="note">لا نتائج بعد — الصق رابطًا واضغط «تحليل الرابط» وستظهر الملفات هنا.</td></tr></tbody></table>
    </div>
    <div class="pane-footer"><span id="candidateVisible">عرض 0 من 0</span><span>القائمة تعرض نحو عشرة صفوف؛ مرّر داخل هذا الصندوق فقط، وتبقى بقية الصفحة ثابتة.</span></div>
    <details class="tool-details" id="selectionTools">
      <summary>أدوات تصفية وتحديد متقدمة</summary>
      <div class="tool-details-body">
        <div class="filter-grid">
          <label>امتدادات مطلوبة (مثال: mp4,pdf)<input type="text" id="filterExtensionsIn" dir="ltr" placeholder="mp4,pdf"></label>
          <label>الحد الأدنى للحجم (MB)<input type="number" id="filterMinSizeIn" min="0" step="0.1"></label>
          <label>الحد الأقصى للحجم (MB)<input type="number" id="filterMaxSizeIn" min="0" step="0.1"></label>
          <label>من تاريخ<input type="date" id="filterDateFromIn"></label>
          <label>إلى تاريخ<input type="date" id="filterDateToIn"></label>
          <label>يحتوي الاسم على<input type="text" id="filterIncludeIn"></label>
          <label>استبعاد ما يحتوي على<input type="text" id="filterExcludeIn"></label>
        </div>
        <div class="row" style="margin-top:9px">
          <button class="alt" id="btnApplyFilters" type="button">تطبيق التصفية</button>
          <button class="alt" id="btnResetFilters" type="button">إعادة تعيين التصفية</button>
        </div>
        <div class="filter-grid" style="margin-top:12px">
          <label>تحديد من رسالة رقم<input type="number" id="selectStartIn" min="1"></label>
          <label>تحديد إلى رسالة رقم<input type="number" id="selectEndIn" min="1"></label>
          <label>المجموعة/القناة في النتائج<select id="selectGroupIn"><option value="">اختر مجموعة…</option></select></label>
        </div>
        <div class="row" style="margin-top:9px">
          <button class="alt" id="btnSelectRange" type="button">تحديد نطاق الرسائل</button>
          <button class="alt" id="btnSelectGroup" type="button">تحديد المجموعة</button>
        </div>
      </div>
    </details>
  </section>

  <section class="card step-card tab-panel" id="transfer" data-tab-panel="transfer" hidden aria-labelledby="transferTitle">
    <div class="section-head"><span class="step-badge">5</span><div><h2 id="transferTitle" tabindex="-1">التحكم في النقل ومتابعة الطابور</h2><p>بعد إضافة الملفات للطابور ابدأ النقل وتابِع التقدم والحالة من هنا.</p></div><span class="section-status" id="transferStatus">الطابور فارغ</span></div>
    <div class="row">
      <button id="btnStart" type="button">▶️ بدء النقل</button>
      <button class="warn" id="btnPause" type="button">⏸️ إيقاف مؤقت</button>
      <button class="alt" id="btnResume" type="button">⏩ استئناف</button>
      <button class="danger" id="btnStop" type="button">🛑 إيقاف</button>
      <button class="alt" id="btnRetry" type="button">🔁 إعادة الفاشل</button>
      <button class="alt" id="btnQueueRefresh" type="button">↻ تحديث الطابور</button>
    </div>
    <div class="msg" id="actionMsg" role="status"></div>
    <div id="queue">
      <div class="queue-toolbar">
        <h3 style="margin:0">📦 طابور النقل الحي (<span id="qCount">0</span>)</h3>
        <span style="flex:1"></span>
        <button class="alt small" id="btnClearCompleted" type="button">مسح المكتمل</button>
        <button class="alt small" id="btnClearIncomplete" type="button">مسح غير المكتمل</button>
      </div>
      <div class="scroll-pane queue-pane" id="queuePane" tabindex="0" aria-label="قائمة طابور النقل القابلة للتمرير داخليًا">
        <table><thead><tr><th>الملف</th><th>الحالة</th><th>التقدم</th><th>الحجم</th><th>تحكم بالعنصر</th></tr></thead>
        <tbody id="qBody"><tr><td colspan="5" class="note">لا توجد عناصر بعد — هذا يعكس قاعدة البيانات الحقيقية.</td></tr></tbody></table>
      </div>
      <div class="pane-footer"><span>قائمة الطابور تمرّر داخل صندوقها مستقلًا عن الصفحة.</span><span>أزرار كل صف تتحكم في ذلك العنصر وحده.</span></div>
    </div>
    <p class="note">بيانات الدخول السرية لا تمر عبر هذه الواجهة. يجب اختيار مجلد Drive قبل إضافة العناصر إلى الطابور.</p>
  </section>


  <section class="card step-card tab-panel" id="universal" data-tab-panel="universal" hidden aria-labelledby="universalTitle">
    <div class="section-head">
      <span class="step-badge">🌐</span>
      <div>
        <h2 id="universalTitle" tabindex="-1">التحميل الشامل من أي رابط إلى Google Drive</h2>
        <p>حمّل الفيديوهات أو الصوتيات (MP3) أو الملفات المباشرة من يوتيوب، فيسبوك، منصات الكورسات، أو Google Drive مباشرة إلى مجلدك.</p>
      </div>
      <span class="section-status" id="universalStatus">جاهز للتحميل</span>
    </div>

    <div class="destination-summary" style="margin-bottom:12px;display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between">
      <div>
        <span>📁 مجلد الحفظ الحالي في Google Drive: </span>
        <strong id="udlSelectedFolderName">نفس المجلد المحدد في قسم «الوجهة»</strong>
      </div>
      <button class="alt small" type="button" data-section-target="destination" onclick="document.querySelector('[data-section-target=destination]').click()">تغيير مجلد الحفظ ↗</button>
    </div>

    <div class="url-tools">
      <span>الصق رابط الفيديو أو الملف هنا، ثم اختر الجودة ومجلد الحفظ.</span>
      <button class="alt small" id="btnUdlPaste" type="button">📋 لصق من الحافظة</button>
    </div>
    <div class="analyze-main" style="grid-template-columns:1fr auto auto">
      <input class="ltr-input" type="url" id="udlUrlIn" dir="ltr" autocomplete="url" autocapitalize="off" spellcheck="false" placeholder="https://…" aria-label="الرابط الخارجي">
      <select id="udlQualityIn" aria-label="اختيار الجودة أو الصوت">
        <option value="best" selected>🎬 أعلى جودة فيديو متاحة (Best MP4)</option>
        <option value="1080p">🎬 فيديو جودة عالية (1080p Full HD)</option>
        <option value="720p">🎬 فيديو جودة متوسطة (720p للمحاضرات)</option>
        <option value="480p">🎬 فيديو جودة اقتصادية (480p لتوفير المساحة)</option>
        <option value="audio_mp3">🎵 صوت فقط — تحويل إلى MP3</option>
        <option value="audio_m4a">🎵 صوت فقط — جودة أصلية سريعة (M4A)</option>
      </select>
      <button id="btnUdlStart" type="button">🚀 بدء التحميل والرفع</button>
    </div>

    <div class="msg" id="udlMsg" role="status" style="margin-top:10px"></div>

    <div style="margin-top:16px">
      <div class="queue-toolbar">
        <h3 style="margin:0">⚡ مهام التحميل الخارجي (<span id="udlCount">0</span>)</h3>
        <span style="flex:1"></span>
        <button class="alt small" id="btnUdlPauseAll" type="button">⏸ إيقاف مؤقت للكل</button>
        <button class="alt small" id="btnUdlResumeAll" type="button">▶ استئناف الكل</button>
        <button class="danger small" id="btnUdlCancelAll" type="button">⏹ إيقاف الكل</button>
        <button class="alt small" id="btnUdlRetryFailed" type="button">🔁 إعادة محاولة الفاشل</button>
        <button class="alt small" id="btnUdlRefresh" type="button">🔄 تحديث</button>
        <button class="alt small" id="btnUdlClear" type="button">🧹 مسح المكتمل</button>
      </div>
      <div class="scroll-pane queue-pane" style="max-height:320px">
        <table>
          <thead>
            <tr><th>العنوان / الرابط</th><th>الجودة</th><th>الحالة</th><th>التقدم</th><th>السرعة</th><th>المجلد</th><th>إجراء</th></tr>
          </thead>
          <tbody id="udlBody">
            <tr><td colspan="5" class="note">لا توجد مهام تحميل خارجية حالياً — الصق أي رابط بالأعلى واضغط «بدء التحميل والرفع».</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>

  <section class="card secondary-section tab-panel" id="settings" data-tab-panel="settings" hidden aria-labelledby="settingsTitle">
    <div class="section-head"><span class="step-badge">⚙</span><div><h2 id="settingsTitle" tabindex="-1">الإعدادات</h2><p>المظهر وسرعة التحديث وعدد عمليات النقل المتوازية.</p></div></div>
    <div class="feature-grid">
      <div class="card settings-card">
        <label for="themeIn">لون الواجهة</label>
        <div class="row" style="margin-top:8px">
          <select id="themeIn" aria-label="المظهر">
            <option value="light">فاتح</option>
            <option value="dim">رمادي متوسط بين الأسود والأبيض</option>
            <option value="dark">داكن كامل</option>
          </select>
        </div>
        <p class="note">الثلاثة متاحة أيضًا من مبدّل الألوان أعلى الصفحة، ويُحفظ الاختيار ويُطبّق فورًا في لوحة الويب الحديثة.</p>
        <div class="msg" id="themeMsg"></div>
      </div>
      <div class="card settings-card">
        <label for="concurrencyIn">عدد عمليات النقل المتوازية (1–100): <strong id="concurrencyValue">2</strong></label>
        <div class="row" style="margin-top:8px">
          <input type="range" id="concurrencyIn" min="1" max="100" step="1" value="2">
          <button id="btnConcurrency" type="button">حفظ التوازي</button>
        </div>
        <p class="note" id="concurrencyRisk">القيم الأعلى من 8 قد تزيد استهلاك الذاكرة واحتمال FloodWait.</p>
        <div class="msg" id="concurrencyMsg"></div>
      </div>
      <div class="card settings-card">
        <label for="autoRefreshIn">تحديث الحالة تلقائيًا</label>
        <div class="row" style="margin-top:8px">
          <select id="autoRefreshIn">
            <option value="0">إيقاف (التحديث اليدوي متاح)</option>
            <option value="1000">كل ثانية</option>
            <option value="2000">كل ثانيتين</option>
            <option value="5000">كل 5 ثوانٍ</option>
          </select>
        </div>
        <p class="note">يُحفظ الفاصل على الخادم؛ زر «تحديث الآن» يبقى متاحًا عند الإيقاف.</p>
        <div class="msg" id="refreshMsg"></div>
      </div>
    </div>
  </section>

  <section class="card secondary-section tab-panel" id="logs" data-tab-panel="logs" hidden aria-labelledby="logsTitle">
    <div class="section-head"><span class="step-badge">☰</span><div><h2 id="logsTitle" tabindex="-1">السجلات الحية (منقّحة)</h2><p>ابحث وصفِّ وصدّر السجل عند الحاجة للتشخيص.</p></div></div>
    <div class="row" style="margin-bottom:8px">
      <select id="logsLevel" aria-label="مستوى السجل">
        <option value="ALL">كل المستويات</option>
        <option value="INFO">معلومات</option>
        <option value="WARNING">تحذيرات</option>
        <option value="ERROR">أخطاء</option>
        <option value="RECOVERY">استعادة</option>
      </select>
      <input type="text" id="logsQuery" placeholder="ابحث في السجلات…" aria-label="بحث في السجلات">
      <button class="alt" id="btnLogsRefresh" type="button">تحديث</button>
      <button class="alt" id="btnLogsSearch" type="button">بحث</button>
      <button class="alt" id="btnLogsDownload" type="button">تصدير ملف السجل</button>
    </div>
    <div class="msg" id="logsMsg"></div>
    <div id="logsBox">…</div>
  </section>

  <section class="card secondary-section tab-panel" id="maintenance" data-tab-panel="maintenance" hidden aria-labelledby="maintenanceTitle">
    <div class="section-head"><span class="step-badge">✚</span><div><h2 id="maintenanceTitle" tabindex="-1">الاستعادة والصيانة والتصدير</h2><p>أدوات إضافية منفصلة عن خطوات النقل اليومية حتى لا تزحم سير العمل.</p></div></div>
    <div class="row">
      <button class="alt" id="btnRecovery" type="button">استعادة نقطة الحفظ</button>
      <button class="alt" id="btnCheckpoint" type="button">إنشاء نقطة حفظ</button>
      <button class="alt" id="btnBuildZip" type="button">بناء حزمة ZIP مختبرة</button>
      <button class="alt" id="btnColabCells" type="button">عرض خلايا Colab</button>
    </div>
    <p class="note">بناء ZIP يشغّل مجموعة الاختبارات كاملة قبل إنشاء الحزمة وقد يستغرق وقتًا.</p>
    <div class="msg" id="maintenanceMsg"></div>
    <pre class="output-box" id="packagePath" hidden></pre>
    <pre class="output-box" id="colabCellsBox" hidden></pre>
  </section>
    </div>
  </main>
</div>

<script>
"use strict";
const $ = (id) => document.getElementById(id);
const DASHBOARD_SECTIONS=["overview","universal","connections","destination","analyze","results","transfer","settings","logs","maintenance"];
const MOBILE_PRIMARY_SECTIONS=["overview","destination","analyze","results","transfer"];
let activeDashboardSection="overview";
let drawerTriggerId="btnMobileMore";
function closeMoreDrawer(restoreFocus){
  const drawer=$("mobileMoreDrawer");
  if(!drawer || drawer.hidden) return;
  drawer.hidden=true;
  document.body.classList.remove("drawer-open");
  ["btnMobileMore","btnHeaderMenu"].forEach(function(id){
    const trigger=$(id);
    if(!trigger) return;
    trigger.setAttribute("aria-expanded","false");
    if(id==="btnMobileMore") trigger.classList.toggle("is-active",!MOBILE_PRIMARY_SECTIONS.includes(activeDashboardSection));
  });
  const trigger=$(drawerTriggerId);
  if(restoreFocus && trigger) trigger.focus();
}
function openMoreDrawer(triggerId){
  const drawer=$("mobileMoreDrawer");
  if(!drawer) return;
  drawerTriggerId=triggerId||"btnMobileMore";
  drawer.hidden=false;
  document.body.classList.add("drawer-open");
  ["btnMobileMore","btnHeaderMenu"].forEach(function(id){
    const trigger=$(id);
    if(trigger) trigger.setAttribute("aria-expanded",String(id===drawerTriggerId));
  });
  const mobileTrigger=$("btnMobileMore");
  if(mobileTrigger) mobileTrigger.classList.add("is-active");
  const panel=drawer.querySelector(".drawer-panel");
  if(panel) panel.focus();
}
function activateSection(section,options){
  const opts=options||{};
  const name=DASHBOARD_SECTIONS.includes(section)?section:"overview";
  activeDashboardSection=name;
  document.querySelectorAll("[data-tab-panel]").forEach(function(panel){
    panel.hidden=panel.dataset.tabPanel!==name;
  });
  document.querySelectorAll("[data-section-target]").forEach(function(button){
    const active=button.dataset.sectionTarget===name;
    button.classList.toggle("is-active",active);
    if(active) button.setAttribute("aria-current","page");
    else button.removeAttribute("aria-current");
  });
  closeMoreDrawer(false);
  const moreButton=$("btnMobileMore");
  if(moreButton) moreButton.classList.toggle("is-active",!MOBILE_PRIMARY_SECTIONS.includes(name));
  if(opts.pushHistory!==false && window.history && typeof window.history.pushState==="function" && window.location.hash!=="#"+name){
    window.history.pushState({teledriveSection:name},"","#"+name);
  }
  if(opts.focusHeading){
    const panel=document.querySelector('[data-tab-panel="'+name+'"]');
    const heading=panel&&panel.querySelector("h2");
    if(heading) heading.focus({preventScroll:true});
  }
  if(opts.scroll!==false && typeof window.scrollTo==="function") window.scrollTo({top:0,behavior:"smooth"});
  return name;
}
document.querySelectorAll("[data-section-target]").forEach(function(button){
  button.addEventListener("click",function(){
    activateSection(this.dataset.sectionTarget,{focusHeading:!!this.closest(".drawer-nav")});
  });
});
$("btnMobileMore").addEventListener("click",function(){openMoreDrawer("btnMobileMore");});
$("btnHeaderMenu").addEventListener("click",function(){openMoreDrawer("btnHeaderMenu");});
$("btnCloseMore").addEventListener("click",function(){closeMoreDrawer(true);});
$("btnCloseMoreBackdrop").addEventListener("click",function(){closeMoreDrawer(true);});
document.addEventListener("keydown",function(event){
  const drawer=$("mobileMoreDrawer");
  if(!drawer || drawer.hidden) return;
  if(event.key==="Escape"){
    event.preventDefault();
    closeMoreDrawer(true);
    return;
  }
  if(event.key!=="Tab") return;
  const focusable=Array.from(drawer.querySelectorAll('button:not(.drawer-backdrop):not([disabled]),a[href],input:not([disabled]),select:not([disabled])'));
  if(!focusable.length) return;
  const first=focusable[0],last=focusable[focusable.length-1];
  const dialog=drawer.querySelector(".drawer-panel");
  if(event.shiftKey && (document.activeElement===first || document.activeElement===dialog)){event.preventDefault();last.focus();}
  else if(!event.shiftKey && (document.activeElement===last || document.activeElement===dialog)){event.preventDefault();first.focus();}
});
window.addEventListener("popstate",function(){
  activateSection(window.location.hash.slice(1),{pushHistory:false});
});
activateSection(window.location.hash.slice(1),{pushHistory:false,scroll:false});
function humanBytes(n){
  if(n==null) return "—";
  const u=["B","KB","MB","GB","TB"]; let i=0; let v=Number(n)||0;
  while(v>=1024 && i<u.length-1){ v/=1024; i++; }
  return v.toFixed(v>=100?0:1)+" "+u[i];
}
function setText(id, value){ const el=$(id); if(el) el.textContent = (value==null ? "—" : String(value)); }
const THEMES=["light","dim","dark"];
const THEME_LABELS={light:"الفاتح",dim:"الخافت بأسلوب X",dark:"الداكن الكامل"};
function normalizeTheme(theme){ return THEMES.includes(theme)?theme:"light"; }
function applyTheme(theme){
  const chosen=normalizeTheme(theme);
  document.documentElement.dataset.theme=chosen;
  const control=$("themeIn");
  if(control && document.activeElement!==control) control.value=chosen;
  document.querySelectorAll("[data-theme-choice]").forEach(function(button){
    button.setAttribute("aria-pressed",button.dataset.themeChoice===chosen?"true":"false");
  });
}
applyTheme(document.documentElement.dataset.theme);
function setMessage(el, text, ok){
  if(!el) return;
  el.className="msg "+(ok?"ok":"err");
  el.textContent=(ok?"✅ ":"⚠️ ")+String(text||"");
}

let queueSignature="";
function queueButton(action,label,title,className,itemId){
  const button=document.createElement("button");
  button.type="button"; button.className=className||"alt small";
  button.textContent=label; button.title=title;
  button.dataset.queueAction=action; button.dataset.itemId=String(itemId||"");
  return button;
}
function renderQueue(state){
  const rows=(state && state.queue) || [];
  setText("qCount", rows.length);
  const signature=rows.map(function(item){
    return [item.id,item.status,Number(item.progress||0).toFixed(1),item.sizeBytes,item.name].join(":");
  }).join("|");
  if(signature===queueSignature) return;
  queueSignature=signature;
  const body=$("qBody");
  const pane=$("queuePane");
  const previousScroll=pane?pane.scrollTop:0;
  body.textContent="";
  if(!rows.length){
    const tr=document.createElement("tr"); const td=document.createElement("td");
    td.colSpan=5; td.className="note"; td.textContent="لا توجد عناصر بعد — هذا يعكس قاعدة البيانات الحقيقية.";
    tr.appendChild(td); body.appendChild(tr); return;
  }
  const fragment=document.createDocumentFragment();
  for(const item of rows.slice(0,500)){
    const tr=document.createElement("tr");
    const name=document.createElement("td"); name.className="file-name"; name.textContent=item.name||item.id||"";
    const status=document.createElement("td"); status.textContent=item.status||"";
    const prog=document.createElement("td");
    const bar=document.createElement("div"); bar.className="bar";
    const fill=document.createElement("i");
    const pct=Math.max(0,Math.min(100,Number(item.progress)||0));
    fill.style.width=pct+"%"; bar.appendChild(fill); prog.appendChild(bar);
    const pctT=document.createElement("div"); pctT.className="mono"; pctT.textContent=pct.toFixed(1)+"%"; prog.appendChild(pctT);
    const size=document.createElement("td"); size.className="mono"; size.textContent=humanBytes(item.sizeBytes);
    const actions=document.createElement("td");
    const actionBox=document.createElement("div"); actionBox.className="queue-actions";
    actionBox.append(
      queueButton("pause","⏸","إيقاف هذا العنصر مؤقتًا","alt small",item.id),
      queueButton("resume","▶","استئناف هذا العنصر","alt small",item.id),
      queueButton("retry","↻","إعادة محاولة هذا العنصر","alt small",item.id),
      queueButton("stop","■","إيقاف هذا العنصر","danger small",item.id)
    );
    actions.appendChild(actionBox);
    tr.append(name,status,prog,size,actions); fragment.appendChild(tr);
  }
  body.appendChild(fragment);
  if(pane) pane.scrollTop=previousScroll;
}

// Raw state-machine strings -> friendly Arabic (raw kept as fallback).
const TG_LABELS={AUTHORIZED:"✅ متصل",CONNECTED:"✅ متصل",DISCONNECTED:"غير متصل",
  READY_FOR_PHONE:"بانتظار تسجيل الدخول (من Gradio)",SENDING_CODE:"جارٍ إرسال الكود…",
  CODE_REQUESTED:"بانتظار إدخال الكود (من Gradio)",VERIFYING_CODE:"جارٍ التحقق من الكود…",
  PASSWORD_REQUIRED:"بانتظار كلمة سر 2FA (من Gradio)",VERIFYING_PASSWORD:"جارٍ التحقق…",
  REAUTH_REQUIRED:"يلزم إعادة تسجيل الدخول",ERROR:"خطأ — راجع Gradio"};
function friendlyStatus(raw){ return TG_LABELS[raw] || raw || "—"; }

let folderStack=[{id:"root",name:"My Drive"}];
let lastDriveConnected=false;
let driveAvailable=false;
let folderRequestSequence=0;
function renderFolderBreadcrumb(){
  setText("folderBreadcrumb",folderStack.map(function(item){return item.name;}).join(" / "));
  const up=$("btnFolderUp");
  if(up) up.disabled=!driveAvailable||folderStack.length<=1;
}
function renderFolders(folders){
  const list=$("folderList");
  list.replaceChildren();
  if(!folders.length){
    const empty=document.createElement("div");
    empty.className="note";
    empty.textContent="لا توجد مجلدات في هذا المستوى.";
    list.appendChild(empty);
    return;
  }
  for(const folder of folders){
    const row=document.createElement("div"); row.className="folder-row";
    const name=document.createElement("div"); name.className="folder-name";
    name.textContent="📁 "+(folder.name||"مجلد بدون اسم");
    const actions=document.createElement("div"); actions.className="folder-actions";
    const open=document.createElement("button"); open.type="button"; open.className="alt"; open.textContent="فتح";
    open.addEventListener("click",function(){
      folderStack.push({id:String(folder.id||""),name:String(folder.name||"مجلد")});
      void refreshDriveFolders();
    });
    const choose=document.createElement("button"); choose.type="button"; choose.textContent="اختيار وجهة";
    choose.addEventListener("click",async function(){
      const result=await bridgeAction("drive.select_folder",{folderId:folder.id},$("folderMsg"),this);
      if(result && result.status==="ok") setMessage($("folderMsg"),"تم اختيار «"+(folder.name||"المجلد")+"» وجهةً للحفظ.",true);
    });
    actions.append(open,choose); row.append(name,actions); list.appendChild(row);
  }
}
async function refreshDriveFolders(btn){
  const current=folderStack[folderStack.length-1]||{id:"root",name:"My Drive"};
  renderFolderBreadcrumb();
  const request=++folderRequestSequence;
  const result=await bridgeAction("drive.list_folders",{parentId:current.id||"root"},$("folderMsg"),btn);
  if(request!==folderRequestSequence) return;
  if(result && result.status==="ok"){
    const folders=(result.data && Array.isArray(result.data.folders))?result.data.folders:[];
    renderFolders(folders);
    setMessage($("folderMsg"),"تم تحميل "+folders.length+" مجلدًا.",true);
  }else{
    renderFolders([]);
  }
}

// Analyze candidates: re-render ONLY when the visible signature changes,
// so polling never clobbers a checkbox mid-click or resets the inner
// scroll position while the user is reviewing a long channel result.
let candSignature="";
let lastCandidates=[];
let candidateSearch="";
let groupSignature="";
function candidateSignature(rows){
  return candidateSearch+"\n"+rows.map(function(c){
    return [c.sourceId,c.selected,c.status,c.name,c.mediaType,c.sizeBytes,c.messageId,c.groupId].join(":");
  }).join("|");
}
function candidateMatches(item){
  if(!candidateSearch) return true;
  const haystack=[item.name,item.mediaType,item.groupLabel,item.dateLabel,item.messageId,item.status]
    .filter(Boolean).join(" ").toLocaleLowerCase();
  return haystack.includes(candidateSearch);
}
function updateCandidateSummary(rows,visibleCount){
  const selected=rows.filter(function(c){return c.selected;});
  setText("cCount", rows.length);
  setText("cSel", selected.length);
  const selectedBytes=selected.reduce(function(sum,item){return sum+(Number(item.sizeBytes)||0);},0);
  setText("cSelectedSize", selected.length?humanBytes(selectedBytes):"—");
  setText("candidateVisible", "عرض "+visibleCount+" من "+rows.length);
  setText("resultsStatus", !rows.length?"لا توجد نتائج":(selected.length?selected.length+" محدد":"اختر الملفات المطلوبة"));
  const all=$("btnSelectAll"), clear=$("btnClearSel"), enqueue=$("btnEnqueue");
  if(all) all.disabled=!rows.length;
  if(clear) clear.disabled=!selected.length;
  if(enqueue) enqueue.disabled=!selected.length;
}
function renderGroupOptions(rows){
  const select=$("selectGroupIn");
  if(!select) return;
  const seen=new Map();
  for(const item of rows){
    if(item.groupId) seen.set(String(item.groupId),String(item.groupLabel||item.groupId));
  }
  const signature=Array.from(seen.entries()).map(function(pair){return pair.join(":");}).join("|");
  if(signature===groupSignature) return;
  groupSignature=signature;
  const previous=select.value;
  select.replaceChildren();
  const placeholder=document.createElement("option");
  placeholder.value=""; placeholder.textContent="اختر مجموعة…"; select.appendChild(placeholder);
  for(const [id,label] of seen){
    const option=document.createElement("option");
    option.value=id; option.textContent=label; select.appendChild(option);
  }
  if(seen.has(previous)) select.value=previous;
}
function renderCandidates(state){
  const rows=(state && state.candidates) || [];
  lastCandidates=rows;
  const visibleRows=rows.filter(candidateMatches);
  updateCandidateSummary(rows,visibleRows.length);
  renderGroupOptions(rows);
  const sig=candidateSignature(visibleRows);
  if(sig===candSignature) return;
  candSignature=sig;
  const body=$("cBody");
  const pane=$("candidatePane");
  const previousScroll=pane?pane.scrollTop:0;
  body.textContent="";
  if(!visibleRows.length){
    const tr=document.createElement("tr"); const td=document.createElement("td");
    td.colSpan=6; td.className="note";
    td.textContent=rows.length
      ? "لا توجد ملفات مطابقة لبحثك داخل النتائج الحالية."
      : "لا نتائج بعد — الصق رابطًا واضغط «تحليل الرابط» وستظهر الملفات هنا لتحديدها قبل الإضافة للطابور.";
    tr.appendChild(td); body.appendChild(tr); return;
  }
  const fragment=document.createDocumentFragment();
  for(const item of visibleRows.slice(0,1000)){
    const tr=document.createElement("tr");
    tr.classList.toggle("is-selected",!!item.selected);
    const pick=document.createElement("td");
    const box=document.createElement("input");
    box.type="checkbox"; box.checked=!!item.selected;
    box.setAttribute("aria-label","تحديد الملف "+(item.name||""));
    box.addEventListener("change",async function(){
      const desired=this.checked;
      const result=await bridgeAction("analyze.toggle_row",{sourceId:item.sourceId},$("selectionMsg"),this);
      if(result && result.status==="ok"){
        item.selected=desired;
        tr.classList.toggle("is-selected",desired);
        candSignature=candidateSignature(lastCandidates.filter(candidateMatches));
        updateCandidateSummary(lastCandidates,lastCandidates.filter(candidateMatches).length);
      }else{
        this.checked=!desired;
      }
    });
    pick.appendChild(box);
    const name=document.createElement("td"); name.className="file-name"; name.textContent=item.name||item.sourceId||"";
    const message=document.createElement("td"); message.className="mono"; message.textContent=item.messageId==null?"—":String(item.messageId);
    const kind=document.createElement("td"); kind.textContent=item.mediaType||"";
    const size=document.createElement("td"); size.className="mono"; size.textContent=humanBytes(item.sizeBytes);
    const src=document.createElement("td");
    src.textContent=[item.groupLabel,item.dateLabel].filter(Boolean).join(" · ");
    tr.append(pick,name,message,kind,size,src); fragment.appendChild(tr);
  }
  body.appendChild(fragment);
  if(pane) pane.scrollTop=previousScroll;
}

let showFilteredLogs=false;
let linkTouched=false;
function setWorkflowStep(linkId,hintId,state,hint){
  const link=$(linkId);
  if(link){
    link.classList.toggle("is-done",state==="done");
    link.classList.toggle("is-current",state==="current");
  }
  if(hint!=null) setText(hintId,hint);
}
function updateWorkflow(state,data){
  const telegram=state.telegram||{};
  const drive=state.drive||{};
  const telegramOk=["AUTHORIZED","CONNECTED"].includes(telegram.status);
  const driveOk=drive.status==="CONNECTED";
  const folder=state.folder||{};
  const folderOk=!!(folder.id||folder.name);
  const candidates=state.candidates||[];
  const selected=candidates.filter(function(item){return item.selected;});
  const queue=state.queue||[];
  const running=!!data.is_running;
  const allAccountsReady=telegramOk&&driveOk;
  setText("connectionsStatus",allAccountsReady?"متصل بالحسابين":(telegramOk||driveOk?"متبقٍّ حساب واحد":"غير متصل"));
  setText("sidebarStateText",allAccountsReady?"الحسابان متصلان":(telegramOk||driveOk?"حساب واحد يحتاج ربطًا":"الحسابات غير متصلة"));
  const sidebarDot=$("sidebarStateDot");
  if(sidebarDot){
    sidebarDot.classList.toggle("is-good",allAccountsReady);
    sidebarDot.classList.toggle("is-partial",!allAccountsReady&&(telegramOk||driveOk));
  }
  const resultsBadge=$("navCandidateCount");
  if(resultsBadge){resultsBadge.textContent=String(candidates.length);resultsBadge.hidden=candidates.length===0;}
  const queueBadge=$("navQueueCount");
  if(queueBadge){queueBadge.textContent=String(queue.length);queueBadge.hidden=queue.length===0;}
  setText("destinationStatus",folderOk?("المجلد: "+(folder.name||"محدد")):"لم يتم الاختيار");
  setText("analyzeStatus",candidates.length?("تم العثور على "+candidates.length+" ملف"):"بانتظار تحليل");
  setText("transferStatus",running?"النقل جارٍ الآن":(queue.length?queue.length+" عنصر في الطابور":"الطابور فارغ"));
  setWorkflowStep("stepLinkConnect","stepConnectHint",telegramOk&&driveOk?"done":"current",
    telegramOk&&driveOk?"Telegram وDrive جاهزان":(!telegramOk?"سجّل Telegram أولًا":"اربط Google Drive"));
  setWorkflowStep("stepLinkDestination","stepDestinationHint",folderOk?"done":(driveOk?"current":"todo"),
    folderOk?(folder.name||"تم اختيار المجلد"):"اختر وجهة الحفظ");
  setWorkflowStep("stepLinkAnalyze","stepAnalyzeHint",candidates.length?"done":(telegramOk?"current":"todo"),
    candidates.length?candidates.length+" نتيجة جاهزة":"الصق رابط قناة أو رسالة");
  setWorkflowStep("stepLinkResults","stepResultsHint",selected.length?"done":(candidates.length?"current":"todo"),
    selected.length?selected.length+" ملف محدد":"راجع واختر المطلوب");
  setWorkflowStep("stepLinkTransfer","stepTransferHint",running?"current":(queue.length?"current":"todo"),
    running?"النقل جارٍ الآن":(queue.length?"جاهز للبدء أو المتابعة":"الطابور والتقدم"));
  let next="جاهز لتحليل رابط جديد أو متابعة الطابور.";
  if(!telegramOk) next="سجّل دخول Telegram من زر تسجيل الدخول الآمن في الخطوة 1.";
  else if(!driveOk) next="اربط Google Drive في الخطوة 1.";
  else if(!folderOk) next="اختر مجلد الحفظ في الخطوة 2 قبل إضافة الملفات للطابور.";
  else if(!candidates.length) next="الصق رابط القناة أو الرسالة في الخطوة 3 واضغط «تحليل الرابط» — الوضع التلقائي سيتعرف عليه.";
  else if(!selected.length) next="حدّد الملفات المطلوبة من صندوق نتائج التحليل في الخطوة 4.";
  else if(running) next="النقل جارٍ الآن؛ تابع التقدم من الخطوة 5.";
  else if(queue.length) next="أضف المحدد إن لم يكن في الطابور، ثم ابدأ النقل من الخطوة 5.";
  else next="اضغط «إضافة المحدد للطابور» في الخطوة 4، ثم «بدء النقل» في الخطوة 5.";
  setText("nextStepText",next);
}
function applyData(data){
  if(!data) return;
  setText("buildInfo","الإصدار "+(data.version||"؟")+" • Build "+(data.build_id||"غير معروف"));
  setText("syncClock","🟢 متصل لحظياً • "+(data.server_time||""));
  setText("mState", data.is_running ? "🔥 يعمل" : (data.engine || "جاهز"));
  setText("mSpeed", data.total_speed_mbps || 0);
  const p=data.progress||{};
  setText("mDone", p.done_files || 0);
  setText("mFail", p.failed_files || 0);
  setText("mSkip", p.skipped_files || 0);
  setText("mPending", data.pending || 0);
  setText("mDisk", humanBytes(data.free_disk_bytes));
  const st=data.state||{};
  const telegram=st.telegram||{};
  const drive=st.drive||{};
  setText("mTg", friendlyStatus(telegram.status));
  setText("mDrive", friendlyStatus(drive.status));
  setText("telegramStatus", friendlyStatus(telegram.status));
  setText("telegramAccount", telegram.accountLabel||"—");
  setText("driveStatus", friendlyStatus(drive.status));
  setText("driveAccount", drive.accountLabel||"—");
  const used=drive.quotaUsed, limit=drive.quotaLimit;
  setText("driveQuota", used!=null&&limit!=null ? humanBytes(used)+" / "+humanBytes(limit) : "غير متاح");
  const folderName=st.folder && st.folder.name;
  const folderLabel=$("selectedFolderName");
  if(folderLabel){
    folderLabel.textContent=folderName||"لم يتم اختيار مجلد";
    folderLabel.classList.toggle("ok",!!folderName);
    folderLabel.classList.toggle("err",!folderName);
  }
  if(THEMES.includes(st.webTheme)) applyTheme(st.webTheme);
  const rememberedLink=st.analyze && st.analyze.sourceLink;
  if(rememberedLink && !linkTouched && document.activeElement!==$("linkIn") && $("linkIn").value!==rememberedLink){
    $("linkIn").value=rememberedLink;
    updateLinkHint();
  }
  if(Number.isFinite(Number(st.concurrency))){
    if(document.activeElement!==$("concurrencyIn")) $("concurrencyIn").value=String(st.concurrency);
    setText("concurrencyValue",st.concurrency);
    setText("concurrencyRisk",Number(st.concurrency)>8 ? "⚠️ التوازي أعلى من 8: قد يزيد استهلاك الذاكرة واحتمال FloodWait." : "القيم الأعلى من 8 قد تزيد استهلاك الذاكرة واحتمال FloodWait.");
  }
  if(Number.isFinite(Number(st.autoRefreshMs))){
    if(document.activeElement!==$("autoRefreshIn")) $("autoRefreshIn").value=String(st.autoRefreshMs);
    configurePolling(Number(st.autoRefreshMs));
  }
  const driveConnected=drive.status==="CONNECTED";
  driveAvailable=driveConnected;
  $("btnFolderRefresh").disabled=!driveConnected;
  $("btnCreateFolder").disabled=!driveConnected;
  $("newFolderName").disabled=!driveConnected;
  $("btnDriveQuota").disabled=!driveConnected;
  if(driveConnected&&!lastDriveConnected){
    folderStack=[{id:"root",name:"My Drive"}];
    void refreshDriveFolders();
  }else if(!driveConnected&&lastDriveConnected){
    folderRequestSequence++;
    renderFolders([]);
    setMessage($("folderMsg"),"اربط Google Drive لعرض المجلدات.",false);
  }
  lastDriveConnected=driveConnected;
  renderFolderBreadcrumb();
  updateWorkflow(st,data);
  renderCandidates(st);
  renderQueue(st);
  if(!showFilteredLogs){
    const lb=$("logsBox");
    lb.textContent=(data.logs||[]).join("\n")||"لا توجد سجلات بعد.";
    lb.scrollTop=lb.scrollHeight;
  }
}

// ---- AJAX Polling: the saved setting controls the browser heartbeat ----
let busyPoll=false;
let pollTimer=null;
let configuredPollMs=null;
function configurePolling(ms){
  const interval=[0,1000,2000,5000].includes(Number(ms))?Number(ms):1000;
  if(configuredPollMs===interval) return;
  configuredPollMs=interval;
  if(pollTimer){ clearInterval(pollTimer); pollTimer=null; }
  if(interval>0) pollTimer=setInterval(pollMetrics,interval);
}
async function pollMetrics(){
  if(busyPoll) return;
  busyPoll=true;
  try{
    const res=await fetch("api/metrics?t="+Date.now(),{cache:"no-store"});
    if(res.ok){ applyData(await res.json()); }
    else { setText("syncClock","🟡 إعادة محاولة…"); }
  }catch(e){ setText("syncClock","🔴 انقطع الاتصال — إعادة محاولة…"); }
  finally{ busyPoll=false; }
}
configurePolling(1000);
pollMetrics();

// ---- actions (same validated bridge actions as the Gradio/React UI) ----
async function postJson(url, body){
  const res=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify(body||{})});
  return await res.json().catch(()=>({}));
}
function showAction(el, data){
  if(!el) return;
  const ok = data && (data.ok===true || data.status==="ok" || (data.result && data.result.status==="ok"));
  el.className="msg "+(ok?"ok":"err");
  const msg=(data && (data.message || (data.result && (data.result.message||data.result.errorKey)))) || "";
  el.textContent=(ok?"✅ ":"⚠️ ")+msg;
  pollMetrics();
}
async function bridgeAction(actionId, payload, el, btn){
  if(btn) btn.disabled=true;
  try{
    const data=await postJson("api/action",{actionId:actionId,payload:payload||{},language:"ar"});
    showAction(el,data);
    return data;
  }catch(error){
    setMessage(el,"تعذر الاتصال بخادم TeleDrive الآن. تأكد أن Colab ما زال يعمل ثم أعد المحاولة.",false);
    return null;
  }finally{ if(btn) btn.disabled=false; }
}
async function queueAction(name, btn){
  if(btn) btn.disabled=true;
  try{
    const data=await postJson("api/queue/"+name,{});
    if(data && data.metrics) applyData(data.metrics);
    showAction($("actionMsg"),data);
    return data;
  }catch(error){
    setMessage($("actionMsg"),"تعذر الاتصال بخادم TeleDrive الآن. تأكد أن Colab ما زال يعمل ثم أعد المحاولة.",false);
    return null;
  }finally{ if(btn) btn.disabled=false; }
}

// Telegram authentication remains in the secure Gradio controls. The modern
// page can safely inspect status or sign out before switching accounts.
const telegramLoginLink=$("telegramLoginLink");
if(document.body.dataset.gradioAvailable!=="true"){
  telegramLoginLink.classList.add("disabled");
  telegramLoginLink.href="#";
  telegramLoginLink.setAttribute("aria-disabled","true");
  telegramLoginLink.title="شغّل الواجهة الكلاسيكية للحصول على تسجيل الدخول الآمن.";
  telegramLoginLink.addEventListener("click",function(event){
    event.preventDefault();
    setMessage($("telegramMsg"),"واجهة Gradio الآمنة غير متاحة الآن. شغّل الواجهتين معًا أو الواجهة الكلاسيكية.",false);
  });
}
$("btnTelegramStatus").addEventListener("click",function(){
  bridgeAction("telegram.status",{},$("telegramMsg"),this);
});
$("btnTelegramLogout").addEventListener("click",function(){
  if(!window.confirm("سيتم تسجيل الخروج ومسح نسخة الجلسة المحفوظة لهذا الحساب. هل تريد المتابعة لتبديله؟")) return;
  const button=this;
  bridgeAction("telegram.logout",{},$("telegramMsg"),button).then(function(result){
    if(result && result.status==="ok"){
      const detail=result.data&&result.data.detail;
      setMessage($("telegramMsg"),detail||"تم تسجيل الخروج. افتح تسجيل الدخول الآمن لإضافة الحساب الجديد.",true);
    }
  });
});

$("btnDriveConnect").addEventListener("click",function(){ bridgeAction("drive.connect",{},$("driveMsg"),this); });
$("btnDriveReconnect").addEventListener("click",function(){ bridgeAction("drive.reconnect",{},$("driveMsg"),this); });
$("btnDriveStatus").addEventListener("click",function(){ bridgeAction("drive.status",{},$("driveMsg"),this); });
$("btnDriveQuota").addEventListener("click",function(){ bridgeAction("drive.refresh_quota",{},$("driveMsg"),this); });
$("btnFolderRefresh").addEventListener("click",function(){ refreshDriveFolders(this); });
$("btnFolderUp").addEventListener("click",function(){
  if(folderStack.length>1){ folderStack.pop(); refreshDriveFolders(this); }
});
$("btnCreateFolder").addEventListener("click",async function(){
  const name=$("newFolderName").value.trim();
  if(!name){ setMessage($("folderMsg"),"اكتب اسم المجلد أولًا.",false); return; }
  const current=folderStack[folderStack.length-1]||{id:"root",name:"My Drive"};
  const result=await bridgeAction("drive.create_folder",{name:name,parentId:current.id||"root"},$("folderMsg"),this);
  if(result && result.status==="ok"){
    $("newFolderName").value="";
    setMessage($("folderMsg"),"تم إنشاء المجلد واختياره وجهةً للحفظ.",true);
    await refreshDriveFolders();
  }
});

async function saveTheme(chosen,control){
  const previous=normalizeTheme(document.documentElement.dataset.theme||"light");
  const next=normalizeTheme(chosen);
  applyTheme(next);
  const result=await bridgeAction("settings.set_theme",{theme:next},$("themeMsg"),control);
  if(result && result.status==="ok") setMessage($("themeMsg"),"تم حفظ المظهر "+THEME_LABELS[next]+".",true);
  else applyTheme(previous);
}
$("themeIn").addEventListener("change",function(){ saveTheme(this.value,this); });
document.querySelectorAll("[data-theme-choice]").forEach(function(button){
  button.addEventListener("click",function(){ saveTheme(this.dataset.themeChoice,this); });
});
$("concurrencyIn").addEventListener("input",function(){ setText("concurrencyValue",this.value); });
$("btnConcurrency").addEventListener("click",async function(){
  const value=Number($("concurrencyIn").value);
  if(!Number.isInteger(value)||value<1||value>100){ setMessage($("concurrencyMsg"),"أدخل عددًا صحيحًا من 1 إلى 100.",false); return; }
  const result=await bridgeAction("settings.set_concurrency",{value:value},$("concurrencyMsg"),this);
  if(result && result.status==="ok"){
    setText("concurrencyValue",value);
    setText("concurrencyRisk",value>8 ? "⚠️ التوازي أعلى من 8: قد يزيد استهلاك الذاكرة واحتمال FloodWait." : "القيم الأعلى من 8 قد تزيد استهلاك الذاكرة واحتمال FloodWait.");
    setMessage($("concurrencyMsg"),"تم حفظ عدد العمليات المتوازية: "+value+".",true);
  }
});
$("autoRefreshIn").addEventListener("change",async function(){
  const value=Number(this.value);
  const result=await bridgeAction("settings.set_auto_refresh",{value:value},$("refreshMsg"),this);
  if(result && result.status==="ok"){
    configurePolling(value);
    setMessage($("refreshMsg"),value===0?"تم إيقاف التحديث التلقائي؛ استخدم زر «تحديث الآن» عند الحاجة.":"تم ضبط التحديث كل "+(value/1000)+" ثانية.",true);
  }
});
$("btnRefreshMetrics").addEventListener("click",function(){ pollMetrics(); });

async function runLogAction(actionId, payload, button){
  const result=await bridgeAction(actionId,payload,$("logsMsg"),button);
  if(!result||result.status!=="ok") return;
  if(result.data && typeof result.data.logs==="string"){
    const box=$("logsBox"); box.textContent=result.data.logs||"لا توجد سجلات مطابقة."; box.scrollTop=box.scrollHeight;
    showFilteredLogs=true;
    setMessage($("logsMsg"),"تم تحميل السجلات المنقّحة.",true);
  }else if(result.data && result.data.path){
    setMessage($("logsMsg"),"تم إنشاء ملف السجل: "+result.data.path,true);
  }
}
$("btnLogsRefresh").addEventListener("click",function(){
  runLogAction("logs.refresh",{level:$("logsLevel").value},this);
});
$("btnLogsSearch").addEventListener("click",function(){
  runLogAction("logs.search",{query:$("logsQuery").value.trim(),level:$("logsLevel").value},this);
});
$("btnLogsDownload").addEventListener("click",function(){
  runLogAction("logs.download",{level:$("logsLevel").value},this);
});

$("btnRecovery").addEventListener("click",function(){ bridgeAction("recovery.restore",{},$("maintenanceMsg"),this); });
$("btnCheckpoint").addEventListener("click",function(){ bridgeAction("maintenance.checkpoint",{},$("maintenanceMsg"),this); });
$("btnBuildZip").addEventListener("click",async function(){
  if(!window.confirm("سيتم تشغيل مجموعة الاختبارات كاملة قبل إنشاء الحزمة وقد يستغرق ذلك وقتًا. متابعة؟")) return;
  const result=await bridgeAction("export.build_zip",{},$("maintenanceMsg"),this);
  if(result && result.status==="ok" && result.data && result.data.zipPath){
    const output=$("packagePath"); output.hidden=false; output.textContent="تم إنشاء الحزمة المختبرة: "+result.data.zipPath;
  }
});
$("btnColabCells").addEventListener("click",async function(){
  const result=await bridgeAction("export.colab_cells",{},$("maintenanceMsg"),this);
  if(result && result.status==="ok" && result.data && result.data.cells){
    const output=$("colabCellsBox"); output.hidden=false; output.textContent=result.data.cells;
  }
});

// Smart default for the common failure reported by the owner: a channel
// link has no message id, so leaving the old default on "one message"
// made channel analysis look broken. Auto resolves to a canonical
// scanner mode from the link itself before anything reaches the bridge.
function inspectTelegramLink(raw){
  const original=String(raw||"").trim();
  if(!original) return {kind:"empty",messageId:null};
  if(/^(saved|me)$/i.test(original)) return {kind:"channel",messageId:null};
  if(/^@[A-Za-z0-9_]+$/.test(original)) return {kind:"channel",messageId:null};
  let path=original.replace(/^https?:\/\//i,"");
  if(!/^(www\.)?(telegram\.me|t\.me)\//i.test(path)) return {kind:"unknown",messageId:null};
  path=path.replace(/^(www\.)?(telegram\.me|t\.me)\//i,"");
  path=path.split(/[?#]/)[0].replace(/\/+$/,"");
  let parts=path.split("/").filter(Boolean);
  if(parts[0]==="s") parts=parts.slice(1);
  if(!parts.length) return {kind:"unknown",messageId:null};
  if(parts[0]==="joinchat" || parts[0].startsWith("+")) return {kind:"invite",messageId:null};
  const numeric=function(value){ return /^\d+$/.test(value||""); };
  if(parts[0]==="c"){
    if(parts.length>=3 && numeric(parts[parts.length-1])) return {kind:"message",messageId:Number(parts[parts.length-1])};
    if(parts.length===2 && numeric(parts[1])) return {kind:"channel",messageId:null};
    return {kind:"unknown",messageId:null};
  }
  if(parts.length>=2 && numeric(parts[parts.length-1])) return {kind:"message",messageId:Number(parts[parts.length-1])};
  if(parts.length===1) return {kind:"channel",messageId:null};
  return {kind:"unknown",messageId:null};
}
function resolveAnalyzeMode(selectedMode,info){
  if(selectedMode!=="auto") return selectedMode;
  return info.kind==="message" ? "message" : "chat";
}
function updateLinkHint(){
  const hint=$("linkHint");
  if(!hint) return;
  const link=$("linkIn").value.trim();
  const info=inspectTelegramLink(link);
  const selected=$("modeIn").value;
  const resolved=resolveAnalyzeMode(selected,info);
  const limit=numOrNull("limitIn")||200;
  let text="الصق رابط قناة أو مجموعة أو رسالة؛ الوضع التلقائي سيتعرف عليه ويختار الفحص المناسب.";
  if(info.kind==="message"){
    text=selected==="auto"
      ? "تم التعرف على رابط رسالة مباشرة رقم "+info.messageId+" — سيتم تحليل هذه الرسالة فقط."
      : "الرابط يحتوي رسالة رقم "+info.messageId+".";
  }else if(info.kind==="channel"){
    text=selected==="auto"
      ? "تم التعرف على رابط قناة/مجموعة — سيتم فحص أحدث ما يصل إلى "+limit+" رسالة واستخراج الملفات القابلة للتنزيل."
      : "هذا رابط قناة/مجموعة بلا رقم رسالة.";
    if(selected==="message") text+=" وضع «رسالة محددة» لن يعمل وحده هنا؛ اختر «تلقائي» أو «قناة/محادثة» أو أدخل رقم رسالة.";
  }else if(info.kind==="invite"){
    text="تم التعرف على رابط دعوة خاصة — سيتم فحص المحادثة إذا كان حساب Telegram عضوًا فيها بالفعل.";
  }else if(info.kind==="unknown" && link){
    text="لم يتم التعرف على صيغة الرابط بعد. استخدم https://t.me/channel أو رابط رسالة أو @username.";
  }
  if(selected!=="auto" && info.kind!=="empty" && info.kind!=="unknown"){
    const labels={message:"رسالة محددة",range:"نطاق رسائل",latest:"أحدث رسائل",chat:"قناة/محادثة حتى الحد"};
    text+=" الوضع اليدوي الحالي: "+(labels[resolved]||resolved)+".";
  }
  hint.textContent=text;
}
// Mirror of the scanner's MODE_FIELDS, plus Auto which needs the bounded
// limit because a channel link resolves to chat under that same bound.
function syncModeFields(){
  const mode=$("modeIn").value;
  const show=function(id,on){ const el=$(id); if(el) el.style.display=on?"":"none"; };
  show("fldMessageId", mode==="message");
  show("fldStartId", mode==="range");
  show("fldEndId", mode==="range");
  show("fldLimit", mode==="auto" || mode==="latest" || mode==="chat");
  updateLinkHint();
}
$("modeIn").addEventListener("change",syncModeFields);

function numOrNull(id){
  const input=$(id);
  if(!input) return null;
  const raw=input.value.trim();
  if(!raw) return null;
  const value=Number(raw);
  return Number.isFinite(value) ? Math.trunc(value) : null;
}
function floatOrNull(id){
  const input=$(id);
  if(!input) return null;
  const raw=input.value.trim();
  if(!raw) return null;
  const value=Number(raw);
  return Number.isFinite(value) ? value : null;
}
function selectedMediaTypes(){
  const values=Array.from(document.querySelectorAll(".media-type-in"))
    .filter(function(box){return box.checked;})
    .map(function(box){return box.value;});
  return (!values.length || values.includes("all")) ? ["all"] : values;
}
function setAllMediaTypes(){
  document.querySelectorAll(".media-type-in").forEach(function(box){ box.checked=box.value==="all"; });
}
document.querySelectorAll(".media-type-in").forEach(function(box){
  box.addEventListener("change",function(){
    if(this.value==="all" && this.checked){
      document.querySelectorAll(".media-type-in").forEach(function(other){ if(other!==box) other.checked=false; });
    }else if(this.checked){
      const all=document.querySelector('.media-type-in[value="all"]');
      if(all) all.checked=false;
    }else if(!document.querySelector(".media-type-in:checked")){
      setAllMediaTypes();
    }
  });
});
$("linkIn").addEventListener("input",function(){ linkTouched=true; updateLinkHint(); });
$("linkIn").addEventListener("paste",function(){ linkTouched=true; window.setTimeout(updateLinkHint,0); });
$("linkIn").addEventListener("keydown",function(event){
  if(event.key==="Enter"){ event.preventDefault(); $("btnAnalyze").click(); }
});
$("limitIn").addEventListener("input",updateLinkHint);
$("btnRememberLink").addEventListener("click",async function(){
  const link=$("linkIn").value.trim();
  if(!link){ setMessage($("analyzeMsg"),"الصق رابطًا أولًا ثم اضغط «تذكّر هذا الرابط».",false); return; }
  const result=await bridgeAction("analyze.remember_link",{link:link},$("analyzeMsg"),this);
  if(result && result.status==="ok") setMessage($("analyzeMsg"),"تم تذكّر الرابط لهذا الحساب.",true);
});
$("btnClearRememberedLink").addEventListener("click",async function(){
  const result=await bridgeAction("analyze.clear_remembered_link",{},$("analyzeMsg"),this);
  if(result && result.status==="ok"){
    linkTouched=true; $("linkIn").value=""; updateLinkHint();
    setMessage($("analyzeMsg"),"تم مسح الرابط المحفوظ.",true);
  }
});

$("btnAnalyze").addEventListener("click",async function(){
  const msg=$("analyzeMsg");
  const selectedMode=$("modeIn").value;
  const info=inspectTelegramLink($("linkIn").value);
  const mode=resolveAnalyzeMode(selectedMode,info);
  const payload={link:$("linkIn").value.trim(),mode:mode,mediaTypes:selectedMediaTypes(),
    messageId:numOrNull("messageIdIn"),startId:numOrNull("startIdIn"),
    endId:numOrNull("endIdIn"),limit:numOrNull("limitIn")};
  const fail=function(text){ setMessage(msg,text,false); };
  if(!payload.link) return fail("الصق رابط تيليجرام أولًا.");
  if(info.kind==="unknown") return fail("صيغة الرابط غير معروفة. استخدم https://t.me/channel أو رابط رسالة كاملًا أو @username.");
  if(payload.messageId!=null && payload.messageId<=0) return fail("رقم الرسالة يجب أن يكون أكبر من صفر.");
  if(mode==="message"){
    if(payload.messageId==null) payload.messageId=info.messageId;
    if(payload.messageId==null) return fail("هذا رابط قناة بلا رقم رسالة. اختر «تلقائي» أو «قناة/محادثة حتى حد الرسائل»، أو أدخل رقم الرسالة يدويًا.");
  }
  if(mode==="range"){
    if(payload.startId==null || payload.endId==null) return fail("وضع النطاق يحتاج رقمي «من رسالة» و«إلى رسالة».");
    if(payload.startId<=0 || payload.endId<payload.startId) return fail("نطاق الرسائل غير صحيح: «إلى» يجب ألا تقل عن «من».");
    if(payload.endId-payload.startId+1>1000) return fail("النطاق أكبر من الحد الأقصى 1000 رسالة.");
  }
  if(mode==="chat" || mode==="latest") payload.limit=payload.limit==null?200:payload.limit;
  if(payload.limit!=null && (payload.limit<1 || payload.limit>1000))
    return fail("حد الرسائل يجب أن يكون بين 1 و1000.");
  msg.className="msg note";
  msg.textContent="⏳ جارٍ تحليل الرابط الآن… قد يستغرق فحص القنوات الكبيرة بعض الوقت بحسب حد الرسائل.";
  const result=await bridgeAction("analyze.run",payload,msg,this);
  if(!result || result.status!=="ok") return;
  const rows=(result.state && result.state.candidates)||[];
  if(result.state) renderCandidates(result.state);
  if(rows.length){
    const bytes=rows.reduce(function(sum,item){return sum+(Number(item.sizeBytes)||0);},0);
    const modeText=selectedMode==="auto" ? (mode==="message"?"رسالة مباشرة":"قناة/محادثة") : mode;
    const summary="اكتمل تحليل "+modeText+": وجدنا "+rows.length+" ملف قابل للتنزيل"+(bytes?" بحجم تقريبي "+humanBytes(bytes):"")+". حدّد المطلوب من النتائج.";
    setMessage(msg,summary,true);
    setMessage($("selectionMsg"),summary,true);
    activateSection("results");
  }else{
    setMessage(msg,"اكتمل التحليل لكن لم نجد ملفات قابلة للتنزيل في النطاق المفحوص. جرّب زيادة حد الرسائل، أو تغيير الوضع/أنواع الملفات، وتأكد أن حسابك يستطيع فتح القناة.",false);
  }
});
$("candidateSearchIn").addEventListener("input",function(){
  candidateSearch=this.value.trim().toLocaleLowerCase();
  candSignature="";
  renderCandidates({candidates:lastCandidates});
  const pane=$("candidatePane"); if(pane) pane.scrollTop=0;
});
$("btnSelectAll").addEventListener("click",function(){ bridgeAction("analyze.select_all",{},$("selectionMsg"),this); });
$("btnClearSel").addEventListener("click",function(){ bridgeAction("analyze.clear_selection",{},$("selectionMsg"),this); });
$("btnEnqueue").addEventListener("click",async function(){
  const result=await bridgeAction("analyze.enqueue_selected",{},$("selectionMsg"),this);
  if(result && result.status==="ok"){
    const queuedMessage="تمت إضافة الملفات المحددة إلى الطابور.";
    setMessage($("selectionMsg"),queuedMessage,true);
    setMessage($("actionMsg"),queuedMessage,true);
    activateSection("transfer");
  }
});
function currentFilterPayload(){
  return {
    mediaTypes:selectedMediaTypes(),
    extensions:$("filterExtensionsIn").value.trim(),
    minSizeMb:floatOrNull("filterMinSizeIn"),
    maxSizeMb:floatOrNull("filterMaxSizeIn"),
    dateFrom:$("filterDateFromIn").value,
    dateTo:$("filterDateToIn").value,
    include:$("filterIncludeIn").value.trim(),
    exclude:$("filterExcludeIn").value.trim()
  };
}
$("btnApplyFilters").addEventListener("click",async function(){
  const payload=currentFilterPayload();
  if(payload.minSizeMb!=null && payload.minSizeMb<0) return setMessage($("selectionMsg"),"الحد الأدنى للحجم لا يمكن أن يكون سالبًا.",false);
  if(payload.maxSizeMb!=null && payload.maxSizeMb<0) return setMessage($("selectionMsg"),"الحد الأقصى للحجم لا يمكن أن يكون سالبًا.",false);
  if(payload.minSizeMb!=null && payload.maxSizeMb!=null && payload.maxSizeMb<payload.minSizeMb)
    return setMessage($("selectionMsg"),"الحد الأقصى للحجم يجب ألا يقل عن الحد الأدنى.",false);
  if(payload.dateFrom && payload.dateTo && payload.dateTo<payload.dateFrom)
    return setMessage($("selectionMsg"),"تاريخ الانتهاء يجب ألا يسبق تاريخ البدء.",false);
  const result=await bridgeAction("analyze.apply_filters",payload,$("selectionMsg"),this);
  if(result && result.state) renderCandidates(result.state);
});
$("btnResetFilters").addEventListener("click",async function(){
  ["filterExtensionsIn","filterMinSizeIn","filterMaxSizeIn","filterDateFromIn","filterDateToIn","filterIncludeIn","filterExcludeIn"]
    .forEach(function(id){ $(id).value=""; });
  setAllMediaTypes();
  $("candidateSearchIn").value=""; candidateSearch=""; candSignature="";
  const result=await bridgeAction("analyze.apply_filters",currentFilterPayload(),$("selectionMsg"),this);
  if(result && result.state) renderCandidates(result.state);
});
$("btnSelectRange").addEventListener("click",function(){
  const startId=numOrNull("selectStartIn"), endId=numOrNull("selectEndIn");
  if(startId==null || endId==null) return setMessage($("selectionMsg"),"أدخل رقمي بداية ونهاية نطاق الرسائل المراد تحديده.",false);
  if(startId<=0 || endId<startId) return setMessage($("selectionMsg"),"نطاق التحديد غير صحيح: النهاية يجب ألا تقل عن البداية.",false);
  bridgeAction("analyze.select_range",{startId:startId,endId:endId},$("selectionMsg"),this);
});
$("btnSelectGroup").addEventListener("click",function(){
  const groupId=$("selectGroupIn").value;
  if(!groupId) return setMessage($("selectionMsg"),"اختر القناة/المجموعة من قائمة النتائج أولًا.",false);
  bridgeAction("analyze.select_group",{groupId:groupId},$("selectionMsg"),this);
});
syncModeFields();

$("btnStart").addEventListener("click",function(){ queueAction("start",this); });
$("btnPause").addEventListener("click",function(){ queueAction("pause",this); });
$("btnResume").addEventListener("click",function(){ queueAction("resume",this); });
$("btnStop").addEventListener("click",function(){ queueAction("stop",this); });
$("btnRetry").addEventListener("click",function(){ queueAction("retry_failed",this); });
$("btnQueueRefresh").addEventListener("click",function(){ bridgeAction("queue.refresh",{},$("actionMsg"),this); });
$("btnClearCompleted").addEventListener("click",function(){ bridgeAction("queue.clear_completed",{},$("actionMsg"),this); });
$("btnClearIncomplete").addEventListener("click",function(){
  if(!window.confirm("سيتم مسح العناصر غير المكتملة من الطابور. هل تريد المتابعة؟")) return;
  bridgeAction("queue.clear_incomplete",{},$("actionMsg"),this);
});
$("qBody").addEventListener("click",function(event){
  const button=event.target.closest ? event.target.closest("[data-queue-action]") : null;
  if(!button) return;
  const actions={pause:"queue.pause_item",resume:"queue.resume_item",stop:"queue.stop_item",retry:"queue.retry_item"};
  const actionId=actions[button.dataset.queueAction];
  if(actionId) bridgeAction(actionId,{itemId:button.dataset.itemId},$("actionMsg"),button);
});

// --- Universal URL Downloader UI Logic ---
(function(){
  const btnStart = $("btnUdlStart");
  const btnPaste = $("btnUdlPaste");
  const btnRefresh = $("btnUdlRefresh");
  const btnClear = $("btnUdlClear");
  const btnPauseAll = $("btnUdlPauseAll");
  const btnResumeAll = $("btnUdlResumeAll");
  const btnCancelAll = $("btnUdlCancelAll");
  const btnRetryFailed = $("btnUdlRetryFailed");
  const urlIn = $("udlUrlIn");
  const qualIn = $("udlQualityIn");
  const msgEl = $("udlMsg");
  const bodyEl = $("udlBody");
  const countEl = $("udlCount");
  const folderLabel = $("udlSelectedFolderName");

  function syncFolderLabel(){
    const mainFolder = $("selectedFolderName");
    if(mainFolder && folderLabel){
      folderLabel.textContent = mainFolder.textContent || "نفس المجلد المحدد في قسم الوجهة";
      folderLabel.className = mainFolder.className;
    }
  }

  function renderUdlTasks(tasks){
    syncFolderLabel();
    if(!bodyEl) return;
    if(!Array.isArray(tasks) || tasks.length === 0){
      if(countEl) countEl.textContent = "0";
      bodyEl.replaceChildren();
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 7;
      td.className = "note";
      td.textContent = "لا توجد مهام تحميل خارجية حالياً — الصق أي رابط بالأعلى واضغط «بدء التحميل والرفع».";
      tr.appendChild(td);
      bodyEl.appendChild(tr);
      return;
    }
    if(countEl) countEl.textContent = String(tasks.length);
    bodyEl.replaceChildren();
    tasks.forEach(function(t){
      const tr = document.createElement("tr");
      const tdTitle = document.createElement("td");
      tdTitle.textContent = t.title || t.url || "—";
      const tdQual = document.createElement("td");
      tdQual.textContent = t.quality || "best";
      const tdStatus = document.createElement("td");
      tdStatus.textContent = t.status_ar || t.status || "—";
      const tdProg = document.createElement("td");
      tdProg.textContent = (typeof t.progress === "number" ? t.progress.toFixed(1) : "0") + "%";
      const tdSpeed = document.createElement("td");
      const speed = Number(t.speed_bps || 0);
      tdSpeed.textContent = speed <= 0 ? "—" : speed >= 1024 * 1024
        ? (speed / (1024 * 1024)).toFixed(2) + " MB/s"
        : (speed / 1024).toFixed(1) + " KB/s";
      const tdFolder = document.createElement("td");
      tdFolder.textContent = t.folder_name || "Drive";
      const tdAction = document.createElement("td");
      function addTaskAction(label, action, className){
        const actionBtn = document.createElement("button");
        actionBtn.type = "button";
        actionBtn.className = (className || "small") + " small";
        actionBtn.textContent = label;
        actionBtn.addEventListener("click", async function(){
          actionBtn.disabled = true;
          try{
            const response = await fetch("api/universal/" + action, {
              method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify({id: t.id})
            });
            const result = await response.json();
            if(msgEl){
              msgEl.textContent = (result && result.message) || "تم إرسال الأمر.";
              msgEl.className = result && result.ok ? "msg ok" : "msg err";
            }
          }catch(_e){
            if(msgEl){ msgEl.textContent = "تعذر الاتصال بمحرك التحميل لتنفيذ الأمر."; msgEl.className = "msg err"; }
          }finally{
            fetchUdlTasks();
          }
        });
        tdAction.appendChild(actionBtn);
      }
      if(t.status === "queued" || t.status === "downloading"){
        if(t.pause_supported){
          addTaskAction("إيقاف مؤقت", "pause", "secondary");
        }else{
          const pauseNote = document.createElement("span");
          pauseNote.textContent = "الإيقاف المؤقت غير مدعوم لهذا المصدر";
          tdAction.appendChild(pauseNote);
        }
        addTaskAction("إيقاف", "cancel", "danger");
      }else if(t.status === "paused"){
        addTaskAction("استئناف", "resume", "primary");
        addTaskAction("إيقاف", "cancel", "danger");
      }else if(t.status === "failed" || t.status === "cancelled"){
        addTaskAction("إعادة المحاولة", "retry", "primary");
      }else if(t.status === "uploading"){
        tdAction.textContent = "جاري الرفع إلى Drive؛ الإيقاف غير مدعوم بأمان أثناء هذه المرحلة";
      }else if(t.status === "completed"){
        tdAction.textContent = "اكتمل";
      }else if(!t.pause_supported && (t.status === "queued" || t.status === "downloading")){
        tdAction.textContent = "الإيقاف المؤقت غير مدعوم لهذا النوع";
      }else{
        tdAction.textContent = "—";
      }
      tr.append(tdTitle, tdQual, tdStatus, tdProg, tdSpeed, tdFolder, tdAction);
      bodyEl.appendChild(tr);
    });
  }

  async function fetchUdlTasks(){
    try{
      const r = await fetch("api/universal/tasks", {cache:"no-store"});
      const d = await r.json();
      if(d && Array.isArray(d.tasks)) renderUdlTasks(d.tasks);
    }catch(_e){}
  }

  if(btnPaste){
    btnPaste.addEventListener("click", async function(){
      if(!urlIn) return;
      try{
        if(!navigator.clipboard || typeof navigator.clipboard.readText !== "function"){
          throw new Error("clipboard unavailable");
        }
        const copied = (await navigator.clipboard.readText()).trim();
        if(!copied){
          if(msgEl){msgEl.textContent="الحافظة فارغة؛ انسخ الرابط أولًا ثم اضغط لصق.";msgEl.className="msg err";}
          return;
        }
        urlIn.value = copied;
        urlIn.focus();
        if(msgEl){msgEl.textContent="✅ تم لصق الرابط. اختر الجودة ثم ابدأ التحميل.";msgEl.className="msg ok";}
      }catch(_e){
        if(msgEl){msgEl.textContent="تعذر الوصول للحافظة من المتصفح. اضغط مطولًا داخل خانة الرابط واختر «لصق».";msgEl.className="msg err";}
        if(urlIn) urlIn.focus();
      }
    });
  }

  if(btnStart){
    btnStart.addEventListener("click", async function(){
      const url = (urlIn ? urlIn.value : "").trim();
      const quality = qualIn ? qualIn.value : "best";
      if(!url){
        if(msgEl){ msgEl.textContent = "⚠️ يرجى لصق الرابط أولاً."; msgEl.className = "msg err"; }
        return;
      }
      btnStart.disabled = true;
      if(msgEl){ msgEl.textContent = "⏳ جاري إرسال الرابط لمحرك التحميل..."; msgEl.className = "msg"; }
      try{
        const r = await fetch("api/universal/start", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({url: url, quality: quality})
        });
        const d = await r.json();
        if(d && d.ok){
          if(msgEl){ msgEl.textContent = "✅ " + (d.message || "بدأ التحميل!"); msgEl.className = "msg ok"; }
          if(urlIn) urlIn.value = "";
          fetchUdlTasks();
        } else {
          if(msgEl){ msgEl.textContent = "⚠️ " + ((d && d.message) || "تعذر بدء التحميل"); msgEl.className = "msg err"; }
        }
      }catch(e){
        if(msgEl){ msgEl.textContent = "⚠️ خطأ في الاتصال بالخادم."; msgEl.className = "msg err"; }
      }finally{
        btnStart.disabled = false;
      }
    });
  }

  async function runBulkAction(action, button){
    if(button) button.disabled = true;
    try{
      const r = await fetch("api/universal/bulk", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({action: action})
      });
      const d = await r.json();
      if(msgEl){
        msgEl.textContent = (d && d.message) || "تم إرسال الأمر الجماعي.";
        msgEl.className = d && d.ok ? "msg ok" : "msg err";
      }
    }catch(_e){
      if(msgEl){msgEl.textContent="تعذر الاتصال بمحرك التحميل لتنفيذ الأمر الجماعي.";msgEl.className="msg err";}
    }finally{
      if(button) button.disabled = false;
      fetchUdlTasks();
    }
  }

  if(btnPauseAll) btnPauseAll.addEventListener("click", function(){runBulkAction("pause", this);});
  if(btnResumeAll) btnResumeAll.addEventListener("click", function(){runBulkAction("resume", this);});
  if(btnCancelAll) btnCancelAll.addEventListener("click", function(){
    if(window.confirm("سيتم طلب إيقاف كل مهام التنزيل النشطة. هل تريد المتابعة؟")) runBulkAction("cancel", this);
  });
  if(btnRetryFailed) btnRetryFailed.addEventListener("click", function(){runBulkAction("retry_failed", this);});
  if(btnRefresh) btnRefresh.addEventListener("click", fetchUdlTasks);
  if(btnClear){
    btnClear.addEventListener("click", async function(){
      await fetch("api/universal/clear", {method:"POST"});
      fetchUdlTasks();
    });
  }

  setInterval(fetchUdlTasks, 2500);
  setTimeout(fetchUdlTasks, 800);
})();
</script>
</body>
</html>
"""


def create_web_app(ctx: Any):
    """Build the FastAPI app bound to the ONE ``ApplicationContext``.

    Sync ``def`` endpoints run in Starlette's threadpool — the same
    threading model Gradio handlers already assume when they marshal
    coroutines onto ``ctx.aio``. Only the WebSocket endpoint is async,
    and it reads snapshots via ``asyncio.to_thread``.
    """
    try:
        from fastapi import FastAPI, Request, WebSocket
        from fastapi.responses import HTMLResponse, JSONResponse
    except ImportError as exc:  # pragma: no cover - lock installs it
        raise RuntimeError(_missing_deps_message()) from exc

    bridge = TeleDriveWebBridge(ctx)
    app = FastAPI(title="TeleDrive v5.0 Turbo Web Dashboard", version=__version__)
    app.state.bridge = bridge
    app.state.ctx = ctx

    @app.get("/", response_class=HTMLResponse)
    def index():
        preferences = getattr(ctx, "preferences", None)
        theme = preferences.current_theme() if preferences is not None else "light"
        if theme not in WEB_THEMES:
            theme = "light"
        raw_gradio_url = str(getattr(ctx, "gradio_proxy_url", "") or "").strip()
        parsed_gradio_url = urlsplit(raw_gradio_url)
        gradio_available = (
            parsed_gradio_url.scheme in {"http", "https"}
            and bool(parsed_gradio_url.netloc)
        )
        gradio_url = html.escape(raw_gradio_url, quote=True) if gradio_available else "#"
        page = HTML_PAGE.replace("__INITIAL_THEME__", theme)
        page = page.replace("__GRADIO_URL__", gradio_url)
        page = page.replace("__GRADIO_AVAILABLE__", "true" if gradio_available else "false")
        return HTMLResponse(page)

    @app.get("/api/health")
    def api_health():
        return {"ok": True, "service": "teledrive-web-dashboard", "version": __version__}

    @app.get("/api/metrics")
    def api_metrics():
        return JSONResponse(bridge.get_system_metrics(), headers=_NO_STORE)

    @app.get("/api/state")
    def api_state():
        return JSONResponse(ctx.handlers.bridge_initial_response(), headers=_NO_STORE)

    @app.get("/api/logs")
    def api_logs(level: str = "ALL", lines: int = 120):
        return JSONResponse({"logs": bridge.tail_logs(level, lines)}, headers=_NO_STORE)

    @app.post("/api/action")
    def api_action(payload: dict):
        return JSONResponse(bridge.action(payload), headers=_NO_STORE)

    @app.post("/api/queue/{name}")
    def api_queue(name: str):
        return JSONResponse(bridge.queue_action(name), headers=_NO_STORE)

    # Compatibility aliases kept from the Drive bridge payload.
    @app.post("/api/start")
    def api_start():
        return JSONResponse(bridge.queue_action("start"), headers=_NO_STORE)

    @app.post("/api/pause")
    def api_pause():
        return JSONResponse(bridge.queue_action("pause"), headers=_NO_STORE)

    @app.post("/api/stop")
    def api_stop():
        return JSONResponse(bridge.queue_action("stop"), headers=_NO_STORE)


    @app.get("/api/universal/tasks")
    def api_universal_tasks():
        from .universal_downloader import get_universal_downloader
        mgr = get_universal_downloader(ctx)
        return JSONResponse({"ok": True, "tasks": mgr.list_tasks()}, headers=_NO_STORE)

    @app.post("/api/universal/start")
    def api_universal_start(payload: dict):
        from .universal_downloader import get_universal_downloader
        mgr = get_universal_downloader(ctx)
        url = str((payload or {}).get("url") or "")
        quality = str((payload or {}).get("quality") or "best")
        folder_id = (payload or {}).get("folder_id")
        return JSONResponse(mgr.start_download(url=url, quality=quality, folder_id=folder_id), headers=_NO_STORE)

    @app.post("/api/universal/cancel")
    def api_universal_cancel(payload: dict):
        from .universal_downloader import get_universal_downloader
        mgr = get_universal_downloader(ctx)
        task_id = str((payload or {}).get("id") or "")
        return JSONResponse(mgr.cancel_task(task_id), headers=_NO_STORE)

    @app.post("/api/universal/pause")
    def api_universal_pause(payload: dict):
        from .universal_downloader import get_universal_downloader
        mgr = get_universal_downloader(ctx)
        task_id = str((payload or {}).get("id") or "")
        return JSONResponse(mgr.pause_task(task_id), headers=_NO_STORE)

    @app.post("/api/universal/resume")
    def api_universal_resume(payload: dict):
        from .universal_downloader import get_universal_downloader
        mgr = get_universal_downloader(ctx)
        task_id = str((payload or {}).get("id") or "")
        return JSONResponse(mgr.resume_task(task_id), headers=_NO_STORE)

    @app.post("/api/universal/retry")
    def api_universal_retry(payload: dict):
        from .universal_downloader import get_universal_downloader
        mgr = get_universal_downloader(ctx)
        task_id = str((payload or {}).get("id") or "")
        return JSONResponse(mgr.retry_task(task_id), headers=_NO_STORE)

    @app.post("/api/universal/bulk")
    def api_universal_bulk(payload: dict):
        from .universal_downloader import get_universal_downloader
        mgr = get_universal_downloader(ctx)
        action = str((payload or {}).get("action") or "")
        return JSONResponse(mgr.bulk_action(action), headers=_NO_STORE)

    @app.post("/api/universal/clear")
    def api_universal_clear():
        from .universal_downloader import get_universal_downloader
        mgr = get_universal_downloader(ctx)
        cleared = mgr.clear_finished()
        return JSONResponse({"ok": True, "cleared": cleared, "tasks": mgr.list_tasks()}, headers=_NO_STORE)

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        import asyncio

        await ws.accept()
        try:
            while True:
                metrics = await asyncio.to_thread(bridge.get_system_metrics)
                await ws.send_text(json.dumps(metrics))
                await asyncio.sleep(1.0)
        except Exception:  # client went away; polling remains the contract
            return

    return app


def _run_server_isolated(server: Any) -> None:
    """Thread target: run uvicorn in THIS thread, capturing every exit.

    uvicorn terminates startup failures with ``sys.exit``; catching
    ``BaseException`` here keeps that ``SystemExit`` inside the server
    thread where it belongs, and records it for the launcher to report
    instead of letting it escape silently (M46-T02).
    """
    try:
        server.run()
    except BaseException as exc:  # noqa: BLE001 - includes SystemExit by design
        server._td_error = exc
        _log.error(
            "web dashboard server thread exited: %s: %s",
            type(exc).__name__,
            redact(str(exc))[:300],
        )


def _wait_until_started(server: Any, thread: threading.Thread, timeout: float = 10.0) -> None:
    """Block the *caller* briefly until the server really listens.

    Raises RuntimeError with the captured thread exception when the
    server dies during startup, so notebook Cell 4 can fall back to
    Gradio with a visible reason instead of printing a dead link.
    """
    deadline = time.monotonic() + float(timeout)
    while time.monotonic() < deadline:
        if getattr(server, "started", False):
            return
        error = getattr(server, "_td_error", None)
        if error is not None:
            raise RuntimeError(
                f"server thread failed during startup: "
                f"{type(error).__name__}: {redact(str(error))[:300]}"
            ) from error
        if not thread.is_alive():
            raise RuntimeError("server thread exited during startup without listening")
        time.sleep(0.05)
    raise RuntimeError(f"server did not start listening within {float(timeout):.0f}s")


def _ensure_port_free(port: int) -> None:
    """Raise a clear error if a requested dashboard port is occupied."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind((BIND_ADDRESS, int(port)))
    except OSError as exc:
        raise RuntimeError(
            f"port {int(port)} is already in use ({exc.strerror or exc})"
        ) from exc
    finally:
        probe.close()


def _select_dashboard_port(preferred: int) -> int:
    """Try preferred port, a deterministic fallback range, then an OS port."""
    preferred = int(preferred)
    candidates = [preferred] + [p for p in range(8766, 8801) if p != preferred]
    for candidate in candidates:
        try:
            _ensure_port_free(candidate)
            return candidate
        except RuntimeError:
            continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((BIND_ADDRESS, 0))
        return int(probe.getsockname()[1])


def stop_web_dashboard(ctx: Any) -> bool:
    """Ask the running dashboard server (if any) to exit. Idempotent."""
    server = getattr(ctx, "web_dashboard", None)
    if server is None:
        return False
    try:
        server.should_exit = True
        thread = getattr(server, "_td_thread", None)
        if (
            thread is not None
            and thread.is_alive()
            and thread is not threading.current_thread()
        ):
            thread.join(timeout=5)
    finally:
        ctx.web_dashboard = None
    _log.info("web dashboard stop requested")
    return True


def launch_web_dashboard(ctx: Any, port: int = DEFAULT_WEB_PORT, open_iframe: bool = False):
    """Serve the Modern Web Dashboard in its own isolated server thread.

    Non-blocking for notebook use after a short startup verification:
    this returns only once the server is actually listening, and
    raises RuntimeError when it is not — Cell 4 then falls back to the
    classic Gradio UI with the reason printed. The handle is stored on
    ``ctx.web_dashboard`` (closed by ``ApplicationContext.shutdown``).
    Calling launch twice returns the already-running server; a stale
    dead handle is discarded and relaunched instead of being returned.
    """
    existing = getattr(ctx, "web_dashboard", None)
    if existing is not None:
        existing_thread = getattr(existing, "_td_thread", None)
        if (
            getattr(existing, "started", False)
            and not getattr(existing, "should_exit", True)
            and (existing_thread is None or existing_thread.is_alive())
        ):
            _log.info("web dashboard already running; returning existing handle")
            return existing
        # Stale/dead handle (e.g. its startup failed earlier): never
        # hand it back as if it were serving.
        ctx.web_dashboard = None
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - lock installs it
        raise RuntimeError(_missing_deps_message()) from exc

    from .app import _ensure_localhost_bypasses_proxy, colab_proxy_url, is_colab

    requested_port = int(port)
    actual_port = _select_dashboard_port(requested_port)
    if actual_port != requested_port:
        _log.warning("requested dashboard port %s is occupied; using fallback port %s", requested_port, actual_port)
        print(f"⚠️ المنفذ {requested_port} مشغول؛ تم اختيار منفذ بديل تلقائيًا: {actual_port}")
    app = create_web_app(ctx)
    config = uvicorn.Config(
        app, host=BIND_ADDRESS, port=actual_port, log_level="warning", access_log=False
    )
    server = uvicorn.Server(config)
    server._td_error = None
    _ensure_localhost_bypasses_proxy()
    if not ctx.aio.is_running:
        ctx.aio.start()
    thread = threading.Thread(
        target=_run_server_isolated,
        args=(server,),
        name="teledrive-web-dashboard",
        daemon=True,
    )
    server._td_thread = thread
    ctx.web_dashboard = server
    thread.start()
    try:
        _wait_until_started(server, thread)
    except BaseException:
        try:
            server.should_exit = True
        finally:
            ctx.web_dashboard = None
        raise
    _log.info("web dashboard listening port=%s thread=%s", actual_port, thread.name)

    if is_colab():
        proxy_url = colab_proxy_url(actual_port)
        if proxy_url:
            # Keep notebook output plain-text only. Rendering an IPython HTML
            # card here relies on Colab's JavaScript output renderer and can
            # make the entire cell output disappear on mobile browsers when
            # that renderer fails. Colab auto-links this official proxy URL.
            print(f"TeleDrive Web Dashboard URL: {proxy_url}")
        else:  # pragma: no cover - Colab-only branch
            print(
                f"TeleDrive Web Dashboard URL: UNAVAILABLE — proxy URL for port "
                f"{actual_port} could not be obtained; server listens on "
                f"{BIND_ADDRESS}:{actual_port}."
            )
        if open_iframe:  # pragma: no cover - Colab-only branch
            try:
                from google.colab import output  # type: ignore[import-not-found]

                output.serve_kernel_port_as_iframe(actual_port, height="760")
            except Exception:
                pass
    else:
        print(f"TeleDrive Web Dashboard URL: http://localhost:{actual_port}/")
    return server
