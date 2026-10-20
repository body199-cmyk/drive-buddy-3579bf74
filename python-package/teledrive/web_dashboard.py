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
* **AJAX polling first.** The page polls ``api/metrics`` about once a
  second with plain ``fetch`` (relative URL, ``cache: no-store``), which
  survives the Colab ``proxyPort`` proxy where long-lived sockets can
  be dropped. The ``/ws`` WebSocket endpoint stays as an optional
  enhancement and serves the exact same payload.
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
        """The ``/api/metrics`` payload the page polls about once a second."""
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
            "state": self._live_state(),
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
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TeleDrive v5.0 Turbo | لوحة التحكم الحية</title>
<style>
:root{
  --bg:#070b14; --card:rgba(15,23,42,.92); --border:rgba(255,255,255,.09);
  --text:#f1f5f9; --muted:#94a3b8; --blue:#3b82f6; --green:#22c55e;
  --red:#ef4444; --amber:#f59e0b; --radius:14px;
}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Tahoma,Arial,sans-serif;
  background:radial-gradient(1200px 600px at 80% -10%,#1e3a8a55,transparent),var(--bg);color:var(--text)}
.wrap{max-width:1060px;margin:0 auto;padding:18px 14px 40px}
header{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between;margin:8px 0 16px}
h1{font-size:22px;margin:0}
.sub{color:var(--muted);font-size:12.5px}
.pill{border:1px solid var(--border);border-radius:999px;padding:6px 12px;font-size:12.5px;background:var(--card)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:12px 0}
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:14px}
.card h3{margin:0 0 8px;font-size:13px;color:var(--muted);font-weight:600}
.big{font-size:24px;font-weight:800}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
input,select{background:#0b1222;color:var(--text);border:1px solid var(--border);
  border-radius:10px;padding:10px 12px;font-size:14px;min-width:0}
input[type=text]{flex:1 1 280px}
button{cursor:pointer;border:0;border-radius:10px;padding:10px 14px;font-size:13.5px;font-weight:700;
  background:linear-gradient(90deg,#2563eb,#4f46e5);color:#fff}
button.alt{background:#1e293b;border:1px solid var(--border)}
button.warn{background:linear-gradient(90deg,#b45309,#d97706)}
button.danger{background:linear-gradient(90deg,#b91c1c,#dc2626)}
button:disabled{opacity:.55;cursor:wait}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{text-align:right;padding:7px 8px;border-bottom:1px solid var(--border);vertical-align:top}
.bar{height:7px;border-radius:99px;background:#1e293b;overflow:hidden;min-width:110px}
.bar i{display:block;height:100%;background:linear-gradient(90deg,#22c55e,#3b82f6)}
#logsBox{background:#020617;border:1px solid var(--border);border-radius:10px;padding:10px;
  font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px;line-height:1.7;
  max-height:260px;overflow:auto;white-space:pre-wrap;word-break:break-word;direction:ltr;text-align:left}
.note{color:var(--muted);font-size:12px;line-height:1.8}
.msg{min-height:20px;font-size:13px}
.ok{color:var(--green)} .err{color:var(--red)} .warnT{color:var(--amber)}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>⚡ TeleDrive v5.0 Turbo — لوحة التحكم الحية</h1>
      <div class="sub">FastAPI + تحديث لحظي عبر AJAX Polling كل ثانية (بدون ريفرش) — نفس محرك النقل والطابور، بلا أي بيانات وهمية</div>
    </div>
    <div class="pill" id="syncClock">⏳ الاتصال…</div>
  </header>

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

  <div class="card">
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
    <p class="note">تسجيل دخول Telegram (الهاتف/الكود/كلمة السر) يبقى دائمًا داخل حقول Gradio الآمنة ولا يسافر عبر هذه الواجهة.
    إذا استُعيدت جلستك من Drive في الخلية 4 فستظهر الحالة «متصل» هنا مباشرة. اختر مجلد Drive الهدف من واجهة Gradio أو شغّل الوضعين معًا <b>Run_Both_Together</b>.</p>
  </div>

  <div class="card" style="margin-top:12px">
    <h3>📦 طابور النقل الحي (<span id="qCount">0</span>)</h3>
    <div style="overflow:auto">
      <table><thead><tr><th>الملف</th><th>الحالة</th><th>التقدم</th><th>الحجم</th></tr></thead>
      <tbody id="qBody"><tr><td colspan="4" class="note">لا توجد عناصر بعد — هذا يعكس قاعدة البيانات الحقيقية.</td></tr></tbody></table>
    </div>
  </div>

  <div class="card" style="margin-top:12px">
    <h3>🧾 السجلات الحية (منقّحة)</h3>
    <div id="logsBox">…</div>
  </div>
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
  setText("mTg", friendlyStatus(st.telegram && st.telegram.status));
  setText("mDrive", friendlyStatus(st.drive && st.drive.status));
  renderCandidates(st);
  renderQueue(st);
  const lb=$("logsBox");
  lb.textContent=(data.logs||[]).join("\n");
  lb.scrollTop=lb.scrollHeight;
}

// ---- AJAX Polling: short JSON requests the Colab proxy never blocks ----
let busyPoll=false;
async function pollMetrics(){
  if(busyPoll) return;
  busyPoll=true;
  try{
    const res=await fetch("api/metrics?t="+Date.now(),{cache:"no-store"});
    if(res.ok){ applyData(await res.json()); }
    else { setText("syncClock","🟡 إعادة محاولة…"); }
  }catch(e){ setText("syncClock","🔴 انقطع الاتصال — إعادة محاولة…"); }
  busyPoll=false;
}
setInterval(pollMetrics,1000);
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
        return HTMLResponse(HTML_PAGE)

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
