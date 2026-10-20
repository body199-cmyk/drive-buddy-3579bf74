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
        state["webTheme"] = web_theme if web_theme in {"light", "dark"} else "light"
        return {
            "ok": True,
            "version": __version__,
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
  --text:#172033; --muted:#64748b; --blue:#2563eb; --green:#15803d;
  --red:#b91c1c; --amber:#b45309; --input:#fff; --surface-2:#e9eef6;
  --log-bg:#f8fafc; --bar-bg:#dbe3ee; --glow:rgba(59,130,246,.12);
  --radius:14px;
}
:root[data-theme="dark"]{
  color-scheme:dark;
  --bg:#070b14; --card:rgba(15,23,42,.94); --border:rgba(255,255,255,.10);
  --text:#f1f5f9; --muted:#94a3b8; --blue:#3b82f6; --green:#22c55e;
  --red:#ef4444; --amber:#f59e0b; --input:#0b1222; --surface-2:#1e293b;
  --log-bg:#020617; --bar-bg:#1e293b; --glow:rgba(30,58,138,.34);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:16px}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Tahoma,Arial,sans-serif;
  background:radial-gradient(1200px 600px at 80% -10%,var(--glow),transparent),var(--bg);color:var(--text)}
.wrap{max-width:1120px;margin:0 auto;padding:18px 14px 40px}
header{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between;margin:8px 0 12px}
h1{font-size:22px;margin:0}
.sub{color:var(--muted);font-size:12.5px}
.pill{border:1px solid var(--border);border-radius:999px;padding:6px 12px;font-size:12.5px;background:var(--card)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:12px 0}
.feature-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:10px;margin:10px 0}
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:14px}
.card h3{margin:0 0 8px;font-size:13px;color:var(--muted);font-weight:600}
.big{font-size:24px;font-weight:800}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
input,select{background:var(--input);color:var(--text);border:1px solid var(--border);
  border-radius:10px;padding:10px 12px;font-size:14px;min-width:0}
input[type=text]{flex:1 1 280px}
input[type=range]{accent-color:var(--blue);padding:0;min-width:180px;flex:1 1 220px}
button,.link-btn{cursor:pointer;border:0;border-radius:10px;padding:10px 14px;font-size:13.5px;font-weight:700;
  background:linear-gradient(90deg,#2563eb,#4f46e5);color:#fff;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;gap:6px}
button.alt,.link-btn.alt{background:var(--surface-2);color:var(--text);border:1px solid var(--border)}
button.warn{background:linear-gradient(90deg,#b45309,#d97706)}
button.danger{background:linear-gradient(90deg,#b91c1c,#dc2626)}
button:disabled,.link-btn.disabled{opacity:.55;cursor:not-allowed;pointer-events:none}
button:focus-visible,.link-btn:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
.section-nav{display:flex;gap:7px;overflow:auto;padding:4px 0 10px;margin-bottom:4px;scrollbar-width:thin}
.section-nav a{white-space:nowrap;color:var(--text);text-decoration:none;border:1px solid var(--border);border-radius:999px;padding:7px 11px;background:var(--card);font-size:12.5px}
.section-nav a:hover{border-color:var(--blue)}
.detail-line{margin:5px 0;overflow-wrap:anywhere}
.feature-actions{margin-top:10px}
.destination-summary{display:flex;flex-wrap:wrap;gap:8px;align-items:center;border:1px solid var(--border);border-radius:10px;padding:10px 12px;margin:10px 0;background:var(--surface-2)}
.destination-summary strong{overflow-wrap:anywhere}
.folder-list{display:grid;gap:8px;margin:10px 0;max-height:340px;overflow:auto}
.folder-row{display:flex;gap:8px;align-items:center;justify-content:space-between;border:1px solid var(--border);border-radius:10px;padding:8px 10px;background:var(--surface-2)}
.folder-name{min-width:0;flex:1;overflow-wrap:anywhere;font-weight:600}
.folder-actions{display:flex;flex-wrap:wrap;gap:6px}
.folder-actions button{padding:7px 10px;font-size:12px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{text-align:right;padding:7px 8px;border-bottom:1px solid var(--border);vertical-align:top}
.bar{height:7px;border-radius:99px;background:var(--bar-bg);overflow:hidden;min-width:110px}
.bar i{display:block;height:100%;background:linear-gradient(90deg,#22c55e,#3b82f6)}
#logsBox,.output-box{background:var(--log-bg);border:1px solid var(--border);border-radius:10px;padding:10px;
  font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px;line-height:1.7;
  max-height:260px;overflow:auto;white-space:pre-wrap;word-break:break-word;direction:ltr;text-align:left}
.output-box{max-height:300px}
.note{color:var(--muted);font-size:12px;line-height:1.8}
.msg{min-height:20px;font-size:13px}
.ok{color:var(--green)} .err{color:var(--red)} .warnT{color:var(--amber)}
@media(max-width:620px){.wrap{padding:12px 9px 28px}h1{font-size:19px}.folder-row{align-items:flex-start;flex-direction:column}.folder-actions{width:100%}.feature-grid{grid-template-columns:1fr}}
</style>
</head>
<body data-gradio-available="__GRADIO_AVAILABLE__">
<div class="wrap">
  <header>
    <div>
      <h1>⚡ TeleDrive v5.0 Turbo — لوحة التحكم الحية</h1>
      <div class="sub">FastAPI + تحديث مباشر بالإعدادات المحفوظة — نفس محرك النقل والطابور، بلا أي بيانات وهمية</div>
    </div>
    <div class="row">
      <button class="alt" id="btnRefreshMetrics" type="button">🔄 تحديث الآن</button>
      <div class="pill" id="syncClock">⏳ الاتصال…</div>
    </div>
  </header>

  <nav class="section-nav" aria-label="أقسام لوحة التحكم">
    <a href="#connections">الحسابات</a>
    <a href="#destination">وجهة Drive</a>
    <a href="#analyze">التحليل</a>
    <a href="#queue">الطابور</a>
    <a href="#settings">الإعدادات</a>
    <a href="#logs">السجلات</a>
    <a href="#maintenance">أدوات إضافية</a>
  </nav>

  <div class="grid">
    <div class="card"><h3>حالة المحرك</h3><div class="big" id="mState">—</div></div>
    <div class="card"><h3>السرعة اللحظية</h3><div class="big"><span id="mSpeed">0</span> <small>MB/s</small></div></div>
    <div class="card"><h3>اكتمل</h3><div class="big" id="mDone">0</div></div>
    <div class="card"><h3>فشل / تم تخطيه</h3><div class="big"><span id="mFail">0</span> / <span id="mSkip">0</span></div></div>
    <div class="card"><h3>في الانتظار</h3><div class="big" id="mPending">0</div></div>
    <div class="card"><h3>مساحة حرة</h3><div class="big"><span id="mDisk">—</span></div></div>
    <div class="card"><h3>Telegram</h3><div class="big" id="mTg" style="font-size:16px">—</div></div>
    <div class="card"><h3>Google Drive</h3><div class="big" id="mDrive" style="font-size:16px">—</div></div>
  </div>

  <div class="feature-grid" id="connections">
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

  <section class="card" id="destination" aria-labelledby="destinationTitle">
    <h3 id="destinationTitle">📁 وجهة الحفظ في Google Drive</h3>
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

  <div class="card" id="analyze">
    <h3>🔍 تحليل رابط تيليجرام (نفس خدمة Scanner الرسمية)</h3>
    <div class="row">
      <input type="text" id="linkIn" placeholder="الصق رابط رسالة/قناة تيليجرام… مثال: https://t.me/channel/123">
      <select id="modeIn">
        <option value="message">رسالة واحدة</option>
        <option value="range">نطاق رسائل</option>
        <option value="latest">أحدث رسائل</option>
        <option value="chat">قناة/محادثة كاملة</option>
      </select>
      <button id="btnAnalyze">تحليل</button>
      <button class="alt" id="btnSelectAll">تحديد الكل</button>
      <button class="alt" id="btnClearSel">مسح التحديد</button>
      <button class="alt" id="btnEnqueue">إضافة للطابور</button>
    </div>
    <div class="row" style="margin-top:8px">
      <label class="note" id="fldMessageId">رقم الرسالة (اختياري إن كان في الرابط)
        <input type="number" id="messageIdIn" min="1" style="width:150px"></label>
      <label class="note" id="fldStartId">من رسالة رقم
        <input type="number" id="startIdIn" min="1" style="width:130px"></label>
      <label class="note" id="fldEndId">إلى رسالة رقم
        <input type="number" id="endIdIn" min="1" style="width:130px"></label>
      <label class="note" id="fldLimit">حد الرسائل (1–1000)
        <input type="number" id="limitIn" min="1" max="1000" value="200" style="width:130px"></label>
    </div>
    <div class="msg note" id="analyzeMsg"></div>
    <div style="overflow:auto;margin-top:8px">
      <table><thead><tr><th>تحديد</th><th>نتيجة التحليل (<span id="cCount">0</span> · محدد <span id="cSel">0</span>)</th><th>النوع</th><th>الحجم</th><th>المصدر</th></tr></thead>
      <tbody id="cBody"><tr><td colspan="5" class="note">لا نتائج بعد — الصق رابطًا واضغط «تحليل» وستظهر الملفات هنا لتحديدها قبل الإضافة للطابور.</td></tr></tbody></table>
    </div>
    <div class="row" style="margin-top:8px">
      <button id="btnStart">▶️ بدء النقل</button>
      <button class="warn" id="btnPause">⏸️ إيقاف مؤقت</button>
      <button class="alt" id="btnResume">⏩ استئناف</button>
      <button class="danger" id="btnStop">🛑 إيقاف</button>
      <button class="alt" id="btnRetry">🔁 إعادة الفاشل</button>
    </div>
    <div class="msg" id="actionMsg"></div>
    <p class="note">بيانات الدخول السرية لا تمر عبر هذه الواجهة. حالة Telegram وإدارة مجلد وجهة Drive متاحتان أعلاه؛ يجب اختيار مجلد قبل إضافة العناصر إلى الطابور.</p>
  </div>

  <div class="card" id="queue" style="margin-top:12px">
    <h3>📦 طابور النقل الحي (<span id="qCount">0</span>)</h3>
    <div style="overflow:auto">
      <table><thead><tr><th>الملف</th><th>الحالة</th><th>التقدم</th><th>الحجم</th></tr></thead>
      <tbody id="qBody"><tr><td colspan="4" class="note">لا توجد عناصر بعد — هذا يعكس قاعدة البيانات الحقيقية.</td></tr></tbody></table>
    </div>
  </div>

  <section class="card" id="settings" style="margin-top:12px" aria-labelledby="settingsTitle">
    <h3 id="settingsTitle">⚙️ الإعدادات</h3>
    <div class="feature-grid">
      <div class="card">
        <label for="themeIn">المظهر</label>
        <div class="row" style="margin-top:8px">
          <select id="themeIn" aria-label="المظهر">
            <option value="light">فاتح</option>
            <option value="dark">داكن</option>
          </select>
        </div>
        <p class="note">يُحفظ الاختيار ويُطبّق على لوحة الويب الحديثة.</p>
        <div class="msg" id="themeMsg"></div>
      </div>
      <div class="card">
        <label for="concurrencyIn">عدد عمليات النقل المتوازية (1–100): <strong id="concurrencyValue">2</strong></label>
        <div class="row" style="margin-top:8px">
          <input type="range" id="concurrencyIn" min="1" max="100" step="1" value="2">
          <button id="btnConcurrency" type="button">حفظ التوازي</button>
        </div>
        <p class="note" id="concurrencyRisk">القيم الأعلى من 8 قد تزيد استهلاك الذاكرة واحتمال FloodWait.</p>
        <div class="msg" id="concurrencyMsg"></div>
      </div>
      <div class="card">
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

  <section class="card" id="logs" style="margin-top:12px" aria-labelledby="logsTitle">
    <h3 id="logsTitle">🧾 السجلات الحية (منقّحة)</h3>
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

  <section class="card" id="maintenance" style="margin-top:12px" aria-labelledby="maintenanceTitle">
    <h3 id="maintenanceTitle">🧰 الاستعادة والصيانة والتصدير</h3>
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

<script>
"use strict";
const $ = (id) => document.getElementById(id);
function humanBytes(n){
  if(n==null) return "—";
  const u=["B","KB","MB","GB","TB"]; let i=0; let v=Number(n)||0;
  while(v>=1024 && i<u.length-1){ v/=1024; i++; }
  return v.toFixed(v>=100?0:1)+" "+u[i];
}
function setText(id, value){ const el=$(id); if(el) el.textContent = (value==null ? "—" : String(value)); }
function applyTheme(theme){
  const chosen=theme==="dark"?"dark":"light";
  document.documentElement.dataset.theme=chosen;
  const control=$("themeIn");
  if(control && document.activeElement!==control) control.value=chosen;
}
applyTheme(document.documentElement.dataset.theme);
function setMessage(el, text, ok){
  if(!el) return;
  el.className="msg "+(ok?"ok":"err");
  el.textContent=(ok?"✅ ":"⚠️ ")+String(text||"");
}

function renderQueue(state){
  const body=$("qBody"); body.textContent="";
  const rows=(state && state.queue) || [];
  setText("qCount", rows.length);
  if(!rows.length){
    const tr=document.createElement("tr"); const td=document.createElement("td");
    td.colSpan=4; td.className="note"; td.textContent="لا توجد عناصر بعد — هذا يعكس قاعدة البيانات الحقيقية.";
    tr.appendChild(td); body.appendChild(tr); return;
  }
  for(const item of rows.slice(0,80)){
    const tr=document.createElement("tr");
    const name=document.createElement("td"); name.textContent=item.name||item.id||"";
    const status=document.createElement("td"); status.textContent=item.status||"";
    const prog=document.createElement("td");
    const bar=document.createElement("div"); bar.className="bar";
    const fill=document.createElement("i");
    const pct=Math.max(0,Math.min(100,Number(item.progress)||0));
    fill.style.width=pct+"%"; bar.appendChild(fill); prog.appendChild(bar);
    const pctT=document.createElement("div"); pctT.textContent=pct.toFixed(1)+"%"; prog.appendChild(pctT);
    const size=document.createElement("td"); size.textContent=humanBytes(item.sizeBytes);
    tr.append(name,status,prog,size); body.appendChild(tr);
  }
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
// so the 1s polling never clobbers a checkbox mid-click.
let candSignature="";
function renderCandidates(state){
  const rows=(state && state.candidates) || [];
  const sig=rows.map(function(c){return [c.sourceId,c.selected,c.status].join(":");}).join("|");
  setText("cCount", rows.length);
  setText("cSel", rows.filter(function(c){return c.selected;}).length);
  if(sig===candSignature) return;
  candSignature=sig;
  const body=$("cBody"); body.textContent="";
  if(!rows.length){
    const tr=document.createElement("tr"); const td=document.createElement("td");
    td.colSpan=5; td.className="note";
    td.textContent="لا نتائج بعد — الصق رابطًا واضغط «تحليل» وستظهر الملفات هنا لتحديدها قبل الإضافة للطابور.";
    tr.appendChild(td); body.appendChild(tr); return;
  }
  for(const item of rows.slice(0,300)){
    const tr=document.createElement("tr");
    const pick=document.createElement("td");
    const box=document.createElement("input");
    box.type="checkbox"; box.checked=!!item.selected;
    box.addEventListener("change",function(){
      bridgeAction("analyze.toggle_row",{sourceId:item.sourceId},$("analyzeMsg"),this);
    });
    pick.appendChild(box);
    const name=document.createElement("td"); name.textContent=item.name||item.sourceId||"";
    const kind=document.createElement("td"); kind.textContent=item.mediaType||"";
    const size=document.createElement("td"); size.textContent=humanBytes(item.sizeBytes);
    const src=document.createElement("td");
    src.textContent=[item.groupLabel,item.dateLabel].filter(Boolean).join(" · ");
    tr.append(pick,name,kind,size,src); body.appendChild(tr);
  }
}

let showFilteredLogs=false;
function applyData(data){
  if(!data) return;
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
  if(st.webTheme==="light"||st.webTheme==="dark") applyTheme(st.webTheme);
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
  }finally{ if(btn) btn.disabled=false; }
}
async function queueAction(name, btn){
  if(btn) btn.disabled=true;
  try{
    const data=await postJson("api/queue/"+name,{});
    if(data && data.metrics) applyData(data.metrics);
    showAction($("actionMsg"),data);
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

$("themeIn").addEventListener("change",async function(){
  const previous=document.documentElement.dataset.theme||"light";
  const chosen=this.value==="dark"?"dark":"light";
  applyTheme(chosen);
  const result=await bridgeAction("settings.set_theme",{theme:chosen},$("themeMsg"),this);
  if(result && result.status==="ok") setMessage($("themeMsg"),"تم حفظ المظهر "+(chosen==="dark"?"الداكن":"الفاتح")+".",true);
  else applyTheme(previous);
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

// Mirror of the scanner's MODE_FIELDS: show only the inputs the chosen
// canonical mode consumes (message / range / latest / chat).
function syncModeFields(){
  const mode=$("modeIn").value;
  const show=function(id,on){ const el=$(id); if(el) el.style.display=on?"":"none"; };
  show("fldMessageId", mode==="message");
  show("fldStartId", mode==="range");
  show("fldEndId", mode==="range");
  show("fldLimit", mode==="latest" || mode==="chat");
}
$("modeIn").addEventListener("change",syncModeFields);
syncModeFields();

function numOrNull(id){
  const raw=$(id).value.trim();
  if(!raw) return null;
  const value=Number(raw);
  return Number.isFinite(value) ? Math.trunc(value) : null;
}
$("btnAnalyze").addEventListener("click",function(){
  const msg=$("analyzeMsg");
  const mode=$("modeIn").value;
  const payload={link:$("linkIn").value.trim(),mode:mode,mediaTypes:["all"],
    messageId:numOrNull("messageIdIn"),startId:numOrNull("startIdIn"),
    endId:numOrNull("endIdIn"),limit:numOrNull("limitIn")};
  const fail=function(text){ msg.className="msg err"; msg.textContent="⚠️ "+text; };
  if(!payload.link) return fail("الصق رابط تيليجرام أولًا.");
  if(payload.messageId!=null && payload.messageId<=0) return fail("رقم الرسالة يجب أن يكون أكبر من صفر.");
  if(mode==="range"){
    if(payload.startId==null || payload.endId==null) return fail("وضع النطاق يحتاج رقمي «من رسالة» و«إلى رسالة».");
    if(payload.startId<=0 || payload.endId<payload.startId) return fail("نطاق الرسائل غير صحيح: «إلى» يجب ألا تقل عن «من».");
    if(payload.endId-payload.startId+1>1000) return fail("النطاق أكبر من الحد الأقصى 1000 رسالة.");
  }
  if(payload.limit!=null && (payload.limit<1 || payload.limit>1000))
    return fail("حد الرسائل يجب أن يكون بين 1 و1000.");
  bridgeAction("analyze.run",payload,msg,this);
});
$("btnSelectAll").addEventListener("click",function(){ bridgeAction("analyze.select_all",{},$("analyzeMsg"),this); });
$("btnClearSel").addEventListener("click",function(){ bridgeAction("analyze.clear_selection",{},$("analyzeMsg"),this); });
$("btnEnqueue").addEventListener("click",function(){ bridgeAction("analyze.enqueue_selected",{},$("analyzeMsg"),this); });
$("btnStart").addEventListener("click",function(){ queueAction("start",this); });
$("btnPause").addEventListener("click",function(){ queueAction("pause",this); });
$("btnResume").addEventListener("click",function(){ queueAction("resume",this); });
$("btnStop").addEventListener("click",function(){ queueAction("stop",this); });
$("btnRetry").addEventListener("click",function(){ queueAction("retry_failed",this); });
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
        if theme not in {"light", "dark"}:
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
    """Fail fast with a clear message when the dashboard port is taken.

    A stale server from an earlier Cell-4 run in the same Colab VM is
    the classic trigger; the remedy is a runtime restart or a
    different ``WEB_DASHBOARD_PORT`` — not a silent dead link.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind((BIND_ADDRESS, int(port)))
    except OSError as exc:
        raise RuntimeError(
            f"port {int(port)} is already in use ({exc.strerror or exc}); "
            "restart the Colab runtime or change WEB_DASHBOARD_PORT in Cell 4"
        ) from exc
    finally:
        probe.close()


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

    _ensure_port_free(int(port))
    app = create_web_app(ctx)
    config = uvicorn.Config(
        app, host=BIND_ADDRESS, port=int(port), log_level="warning", access_log=False
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
    _log.info("web dashboard listening port=%s thread=%s", int(port), thread.name)

    if is_colab():
        proxy_url = colab_proxy_url(int(port))
        if proxy_url:
            print(f"TeleDrive Web Dashboard URL: {proxy_url}")
            try:  # pragma: no cover - Colab-only display path
                from IPython.display import HTML, display

                display(
                    HTML(
                        '<div style="border:2px solid #3b82f6;border-radius:14px;'
                        'padding:16px;margin:10px 0;direction:rtl;text-align:right;'
                        'font-family:sans-serif">'
                        "<h3 style=\"margin:0 0 10px\">⚡ واجهة الويب الحديثة جاهزة "
                        "(TeleDrive Web Dashboard)</h3>"
                        f'<a href="{html.escape(proxy_url, quote=True)}" target="_blank" '
                        'style="display:inline-block;background:#2563eb;color:#fff;'
                        'padding:11px 22px;border-radius:10px;text-decoration:none;'
                        'font-weight:bold">🌐 افتح لوحة التحكم الحديثة ↗️</a></div>'
                    )
                )
            except Exception:
                pass
        else:  # pragma: no cover - Colab-only branch
            print(
                f"TeleDrive Web Dashboard URL: UNAVAILABLE — proxy URL for port "
                f"{int(port)} could not be obtained; server listens on "
                f"{BIND_ADDRESS}:{int(port)}."
            )
        if open_iframe:  # pragma: no cover - Colab-only branch
            try:
                from google.colab import output  # type: ignore[import-not-found]

                output.serve_kernel_port_as_iframe(int(port), height="760")
            except Exception:
                pass
    else:
        print(f"TeleDrive Web Dashboard URL: http://localhost:{int(port)}/")
    return server
