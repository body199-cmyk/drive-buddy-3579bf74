# تحقيق هندسي: انقطاع الاتصال بعد ~30 دقيقة واستعادة TeleDrive تلقائيًا
# Engineering Investigation — Colab Runtime Persistence, Dashboard Connectivity, Recovery

**التاريخ / Date:** 2026-10-23
**Base:** `main` @ `5202e3f` (includes merged PR #129)
**Also inspected:** draft PR #130 `fix/colab-user-session-isolation` @ `0886351` (owner's newest work, 2026-10-22)
**Status:** Investigation only. **No code changes applied.** No live Colab was accessed.

> **الخلاصة بالعربي:**
> 1. **الواجهة الحديثة لا تستخدم WebSocket أصلًا.** الصفحة تعمل بـ HTTP polling كل ثانية (`fetch("api/metrics")`). فرضية "الـ WebSocket بيقع" غير صحيحة للواجهة الحالية — الـ `/ws` موجود في السيرفر ولا يفتحه أي كود في المتصفح.
> 2. **خلية الـ keep-alive (8) لا تلمس الواجهة ولا السيرفر أصلًا.** هي بتطبع سطر كل دقيقتين، وبتضغط زر Connect في صفحة Colab كل دقيقة، وبتشغل صوت صامت. ده بيأثر على تاب Colab بس، مش على تاب الداشبورد، ومش بيمنع حدود Google.
> 3. **اكتشاف خطير ومُثبت بالتجربة:** إعادة تشغيل الخلية 4 والتحميل شغال **بتحوّل الملفات الجارية إلى `NeedsRetry`** (دالة `reconcile_with_drive` بتفترض إن أي حالة "Downloading" معناها crash). يعني خطوة "أعيد تشغيل الأربع خلايا" نفسها ممكن تخرب الطابور لو الـ runtime كان لسه عايش.
> 4. **الحل الأأمن:** خلية "إعادة اتصال" صغيرة جديدة (بدون تثبيت، بدون reconcile، بدون سيرفر جديد) تطبع رابط الداشبورد فقط وتفحص صحته + تحسينات صغيرة في المتصفح (إعادة المزامنة عند رجوع التاب). ولو الـ runtime نفسه مات، لازم الأربع خلايا — ده حد من Google مش bug.

---

## 1. Executive Summary

The recurring "disconnect after ~30 minutes" is **not one problem**. The source shows four distinct layers, each with a different recovery path:

| Layer | What dies | Engine keeps running? | Correct recovery |
|---|---|---|---|
| L1 Browser tab (dashboard) | Polling stops (tab hidden/discarded/network) | **Yes** | Just reload the dashboard URL |
| L2 Colab notebook frontend | Notebook tab's kernel connection | **Yes**, usually | Reopen notebook; **do not** rerun cells; reprint URL |
| L3 Dashboard server thread | uvicorn thread exited | **Yes** (isolated thread since M46-T02) | Relaunch only the server (idempotent function exists) |
| L4 Colab VM/runtime | Entire process, `/content`, in-memory state | **No** | Full Cells 1–4; restore from Drive checkpoint |

**Verified facts:**
- The modern dashboard uses **HTTP polling only**; `/ws` is never opened by any client code (`web_dashboard.py` contains zero `new WebSocket(`; docstring lines 37–41 state polling is the contract). So the WebSocket hypotheses (A, F, G as WS issues) do not apply to the current UI.
- The keep-alive (Cell 8 → `session_vault.start_keepalive`) prints to cell output and clicks Colab's Connect button. It does nothing for the dashboard tab.
- The server is launched with uvicorn defaults; the request path has no long blocking call for `/api/metrics` (SQLite reads + in-memory snapshots), so L3 hangs are unlikely but unproven.
- **Rerunning Cell 4 inside a still-alive runtime corrupts active task state.** `ctx.checkpoints.restore_and_reconcile()` (`notebook_cells.py:841`) calls `checkpoint_manager.reconcile_with_drive` (`checkpoint_manager.py:203-246`), which treats every `Downloading/Uploading/Downloaded/Verifying` row as an interrupted crash and moves it to `NeedsRetry` if not yet on Drive. **Reproduced in an isolated test** (item in `Downloading` → `NeedsRetry` after reconcile). The live worker keeps running while its row is now in the wrong state.
- Rerunning Cell 1 in a live runtime is **refused by design** (`_pkg_runtime_refusal_reason`, `notebook_cells.py:138-145`) and raises `RuntimeError` that tells the user to Restart, so the user's "rerun all four cells" path **forces a runtime restart**, destroying the live engine even when only L1/L2 failed. This is very likely the biggest cause of lost progress.

**Most likely explanation of the "~30 minutes" pattern (hypothesis, not proven):** the user's phone backgrounds the dashboard tab or the Colab tab (Android Chrome freezes/discards background tabs). Polling stops (L1), and the Colab notebook tab disconnects its kernel channel (L2). The runtime itself is usually still alive at that point; Colab's idle disconnect is documented as roughly 90 minutes of inactivity and 12 hours maximum on free tier, but Google does not publish exact numbers. The user then follows the recovery recipe, which hits the Cell 1 refusal → restart → real loss (L4 self-inflicted).

**Recommendation:** do not add more heartbeats. Ship a **"Reconnect" cell** that only reprints the URL and health-checks (no install, no reconcile, no new server), make Cell 4 safe to rerun (skip reconcile when the context is already live), and add small frontend resilience (visibility-triggered resync, clear "engine unreachable vs runtime gone" banner). These are small, isolated, reversible changes.

---

## 2. Verified Architecture and File Paths

```
Colab VM (one Python kernel process)
├─ Cell 1  notebook_cells.py:~95-720   update gate (REFUSES if teledrive already imported) → extract → pip install
├─ Cell 2  bootstrap.run()             create_context() — idempotent: returns existing _CONTEXT if loop alive (app_context.py:200-207)
├─ Cell 3  Drive auth (google.colab.auth) + SessionVault.probe; may prompt getpass
├─ Cell 4  adopt Drive → vault restore (autorestore_once: once per process) →
│          ctx.checkpoints.restore_and_reconcile()   ← unsafe on rerun (see §3-I)
│          launch() Gradio :7860 (idempotent) + launch_web_dashboard(:8765) (idempotent)
├─ Cell 8  start_keepalive(): print thread every 120 s + JS clicks colab-connect-button every 60 s + muted audio
└─ Threads: ctx.aio event loop (Telethon, TransferManager), uvicorn thread "teledrive-web-dashboard",
           Gradio thread, universal-dl-* threads, td-keepalive thread

Browser (separate tab) ── Colab proxy https://<port>-…prod.colab.dev ──► uvicorn :8765
   pollMetrics(): setInterval 1000 ms → GET api/metrics (web_dashboard.py:1390-1412)
   fetchUdlTasks(): setInterval 2500 ms → GET api/universal/tasks (web_dashboard.py:1934-2032)
   No WebSocket. No visibilitychange/online handlers. No backoff.
```

Key references:
- Server lifecycle: `web_dashboard.py:2188-2365` (`_run_server_isolated`, `_wait_until_started`, `_select_dashboard_port` 8765→8766..8800→OS port, `stop_web_dashboard`, `launch_web_dashboard` idempotent via `ctx.web_dashboard`).
- Proxy URL: `app.py:68-82` `colab_proxy_url()` → `google.colab.kernel.proxyPort(port)`; requires a live **notebook frontend** to evaluate JS (`eval_js`). This matters for a Reconnect cell: it must be run from the notebook.
- Persistence: SQLite `ROOT/data/teledrive.db` on local disk `/content/teledrive_runtime` (lost with VM). Durable checkpoints to Drive after each upload (`transfer_manager.py:765,849` → `checkpoint_manager.persist_durable`). Telegram session vault on Drive (`session_vault.py`).
- Universal downloader tasks: **memory only** (`UniversalDownloadManager._tasks`), lost with VM, survive page refresh.
- Telegram queue: SQLite → survives page refresh and server restart; survives VM loss only via Drive checkpoint.
- Startup paths observed: `/content/teledrive_runtime` (TELEDRIVE_ROOT), `/content/teledrive-v4.5/` (extracted package, `PKG_ARCHIVE_ROOT`).

**PR #130 (draft, owner's latest):** adds per-launch owner token in URL fragment `#td_token=…` → `POST /api/auth` → HttpOnly SameSite=Strict cookie (12 h). Everything except `/` and `/api/auth` returns 401 without the cookie. Relevance here: (a) the token is **regenerated on every server launch** (`launch_web_dashboard`: `access_token = secrets.token_urlsafe(32)`), so any server relaunch invalidates open tabs; a Reconnect cell must reprint the *current* tokenized URL; (b) cookie TTL 12 h exceeds Colab's free max, fine; (c) on a 401 the page shows a warning but has no re-auth path except a new link. Recovery design below accounts for this.

---

## 3. Root-Cause Hypotheses Ranked by Evidence

| # | Hypothesis | Likelihood | Impact | Evidence |
|---|---|---|---|---|
| **I** | Four-cell recovery does too much and is destructive in a live runtime | **High — confirmed in code + isolated repro** | **High** | Cell 1 refuses when modules loaded (`notebook_cells.py:138-145, 691-701`) → message instructs Restart → VM state lost. Cell 4 rerun → `reconcile_with_drive` → live rows to `NeedsRetry` (repro output: `STATE_AFTER_RECONCILE NeedsRetry {'marked_needsretry': 1}`). |
| **B / J** | Mobile browser backgrounds / freezes / discards the tab; network changes | **High (hypothesis)** | Medium | Android Chrome throttles timers in background and freezes/discards tabs; polling uses `setInterval` with no `visibilitychange` resync, so on return the UI may show stale data until next tick, or the page reloads (discard) and works again. User report: mobile usage (KNOWN_ISSUES, `app.py` comment about mobile renderer). |
| **C** | Colab notebook frontend disconnects while runtime stays alive | **Medium-High (hypothesis)** | Medium | Notebook tab is a separate tab; when backgrounded it loses its kernel WebSocket. Runtime continues. Dashboard proxy URL keeps working only while Colab's proxy still authorizes the session; unverified whether proxy access survives a notebook-frontend disconnect. |
| **D** | Colab actually terminates the VM (idle/usage/resource) | **Medium** | **High** | Free-tier idle disconnect + 12 h cap (docs/TROUBLESHOOTING.md:14). ~30 min is shorter than commonly reported idle limits, so D alone fits poorly unless the tab was closed or resources were exhausted (disk/RAM: universal downloader has no disk guard — audit D-06). |
| **E** | uvicorn exits or hangs | **Low** | Medium | Server runs in an isolated daemon thread; startup failures captured. Endpoints are sync defs in Starlette threadpool (40 threads default); `/api/metrics` is DB/in-memory; actions using `ctx.aio.run(...)` without timeout exist (`services.py:412,415`, `telegram_auth.py:128`) and could pin threadpool workers during Telegram FloodWait, but 40 slots make full starvation unlikely. No evidence of a crash. |
| **H** | Task state memory-only | **Partial** | Medium | Telegram queue: SQLite (survives refresh/server restart). Universal tasks: memory (survive refresh, not VM loss). After VM loss, Telegram rows restorable from Drive checkpoint but no auto-resume (by design, `queue_manager.py:152`). |
| **F** | Heartbeat at wrong layer | **Confirmed** | — | See §4. |
| **G** | Stale server / port collision prevents reconnection | **Low on rerun, Medium on misuse** | Low | `launch_web_dashboard` returns existing live handle; on dead handle selects free port (could move to 8766+ → old URL dead; user must use new URL). Orphans on 8765–8795 occur only if a context is recreated after `reset_context`/module reload. |
| **A** | WebSocket disconnects while engine alive | **Not applicable** | — | No client opens `/ws`. |

---

## 4. Why the Existing Heartbeat Did Not Solve It

`session_vault.start_keepalive()` (`session_vault.py:277-312`, JS at `1052-1076`) does three things:
1. Background thread `print("TeleDrive keep-alive …")` every 120 s → output in the notebook cell. Produces kernel output; does **not** count as user interaction for Colab's idle detection in any documented way.
2. Injected JS clicks `colab-connect-button` every 60 s **in the notebook tab** → only works while that tab is running JS. Mobile Chrome throttles/freezes background tabs, so this stops exactly when it's needed. Colab's UI selectors are undocumented and may change.
3. Muted silent audio loop (Cell 8) → muted media generally does **not** exempt a tab from background throttling; autoplay may be blocked.

None of these touch the **dashboard tab** (where the user is), the proxy, or the uvicorn server. They cannot fix L1 at all, only partially mitigate L2 when the notebook tab is foreground, and cannot override L4 limits. Per constraints, heartbeat/fake activity must not be presented as a guarantee — the code comment already says "best-effort", which is correct.

---

## 5. Recommended Design

### Quick fixes (small, isolated, no engine change)

**Q1. "Reconnect" cell (new optional Cell, e.g. Cell 4R).** Pure read + reprint, safe at any time:
```
from teledrive import app_context
if not app_context.has_context(): print("RUNTIME LOST → run Cells 1–4"); stop
ctx = app_context.get_context()
check: ctx.aio.is_running, telegram status, drive status, queue snapshot counts
server = ctx.web_dashboard; if alive → reprint proxy URL (+ current token on PR #130)
else → launch_web_dashboard(ctx, port) (idempotent) and print URL
```
No package update, no pip, no Drive auth, no vault restore, no reconcile, no second context. If `teledrive` is not even importable / `has_context()` is False → the VM was reset (L4) and the cell says so explicitly. **This one cell distinguishes L2/L3 from L4.**

**Q2. Make Cell 4 rerun-safe.** Guard reconcile: run `restore_and_reconcile()` only when the queue has no active drain (`ctx.queue_manager.snapshot()["status"]` idle and `active == []`) or only on first run per process (flag on ctx). Fixes the confirmed corruption. Engine code untouched; only the notebook generator.

**Q3. Change Cell 1 refusal message** to point to the Reconnect cell first ("TeleDrive is already running in this runtime — run the Reconnect cell; restart only to update"). Today it tells users to restart, which destroys live work.

**Q4. Frontend resilience (dashboard HTML/JS only):**
- `document.addEventListener("visibilitychange")` + `window.addEventListener("online")` → immediate `pollMetrics()` + `fetchUdlTasks()`.
- Failure counter with exponential backoff (1 s → 2 → 4 … cap 30 s) instead of hammering every second while unreachable; reset on success.
- Status banner distinguishing: *reachable* / *temporarily unreachable (retrying)* / *unreachable > 60 s → "open the notebook and run the Reconnect cell; if it says RUNTIME LOST, run Cells 1–4"* / *401 → "this link expired, use the newest link from the notebook"* (PR #130).
- Server-side `runtime_id` (random per process, set once on ctx) and `server_started_at` in `/api/metrics`; the page detects a changed `runtime_id` → "runtime was restarted; queue restored from checkpoint" instead of silently showing an empty queue.

### Architectural changes (later, optional)

**A1. Universal-download journal** (local SQLite table or JSON lines in `ROOT/data`): survives server restart; with Drive checkpoint it survives VM loss as "interrupted — retry?" (never auto-restart; URLs may contain tokens → redact/hash before writing to Drive).
**A2. Persistent worker (VM)**: only way to remove L4. See §5 comparison #6.

### Comparison of the six designs

| # | Design | Solves | Cannot solve | Risk / complexity | Safe alongside current Colab? | How to test |
|---|---|---|---|---|---|---|
| 1 | Frontend-only resilience (Q4) | L1 staleness, clearer state, less wasted polling | L2–L4 | Low / S | Yes (HTML string only) | Contract tests on HTML + manual mobile tests |
| 2 | Backend health + authoritative snapshot (`/api/metrics` already authoritative; add `runtime_id`, `/api/health` detail) | Detects runtime restart vs blip; correct re-render after reattach | L4 data loss | Low / S | Yes | TestClient tests |
| 3 | Runtime-local supervisor auto-restarting uvicorn | L3 without user action | L1, L2, L4 | Medium: a watchdog thread that relaunches the server must never run two servers; port moves change the URL; with PR #130, a relaunch rotates the token → open tabs get 401. **Not recommended now** (no evidence L3 happens). Q1 covers L3 manually and safely. | Yes if bounded (max N restarts, backoff, single lock) | Kill `server.should_exit=True` in test, assert one relaunch, one thread, one port |
| 4 | Notebook startup redesign (Q1–Q3) | The destructive recovery path (I), L2/L3 recovery without restart | L4 | Low / S–M; must regenerate both notebooks via `notebook_cells.py` and keep `colab_cells.json` contract tests green | Yes — additive cell + guard | `test_notebook.py` contracts, isolated reconcile test, manual Colab |
| 5 | Persistent task journal to Drive | After L4: knowing what was in flight; universal tasks recoverable | Not a live-resume; Drive latency/quotas; partial writes need atomic write+rename semantics (Drive has no rename-atomic → write new file, then delete old, keep last 2) | Medium. Telegram already has it (`persist_durable`). Extend only for universal tasks. | Yes | Simulate crash mid-download; restore; assert no duplicates via `source_key` |
| 6 | External always-on VM (e.g. Oracle Free Tier) | **L4 entirely**; no idle limits | Not free-guaranteed (free tier availability/terms vary); Drive auth needs OAuth refresh tokens (no native Colab creds); Telegram session must live on that server; you become responsible for security and updates | High / L | Can run in parallel as a separate deployment; Colab remains baseline | Staged: run same package headless on VM with test accounts |

**Frontend hosting (Vercel) is a separate question** and does not affect L4 at all; it only changes where the HTML comes from.

---

## 6. Minimal Implementation Plan (ordered by risk/benefit)

1. **Q2 — reconcile guard in Cell 4** (fixes confirmed corruption). Smallest high-value change.
2. **Q1 — Reconnect cell** + **Q3 — Cell 1 message**.
3. **Q4 + runtime_id** in dashboard (coordinate with PR #130; implement on top of it if it merges first, because its fetch wrapper changes how 401s surface).
4. Universal downloader disk guard (audit D-06) — removes one plausible cause of real VM trouble.
5. (Optional) universal-task journal locally; Drive journal only after measuring need.
6. (Optional, owner decision) VM pilot.

Each step: separate branch, separate PR, CI green, owner live test in a **new** runtime before merge.

---

## 7. Proposed Code Changes (NOT applied)

| File / function | Change | Rationale |
|---|---|---|
| `python-package/teledrive/notebook_cells.py` Cell 4 text (line ~841) | Replace unconditional `ctx.checkpoints.restore_and_reconcile()` with: `if not getattr(ctx, "_td_reconciled", False) and not ctx.queue_manager.snapshot()["active"]: ctx.checkpoints.restore_and_reconcile(); ctx._td_reconciled = True` else print "reconcile skipped: engine already running". | Confirmed corruption on rerun. |
| Same file: new Reconnect cell source + `colab_cells.json` + both notebooks regenerated via `python -m teledrive.notebook_cells --write` | As Q1. Uses only `app_context.has_context/get_context`, `launch_web_dashboard` (idempotent), `colab_proxy_url`. | Recover L2/L3 without restart. |
| Same file: Cell 1 refusal text (`~691-701`) | Mention Reconnect cell before Restart. | Stop self-inflicted L4. |
| `teledrive/app_context.py` `ApplicationContext.__init__` | `self.runtime_id = uuid4().hex[:12]`; `self.started_at = time.time()` | Let UI detect VM restart. |
| `teledrive/web_dashboard.py` `get_system_metrics` | add `runtime_id`, `server_started_at`, `uptime_s` | Same. |
| `teledrive/web_dashboard.py` HTML `pollMetrics`/`fetchUdlTasks` | visibility/online resync, backoff, banner states (incl. 401 if PR #130) | L1 resilience, honest status. |
| `teledrive/web_dashboard.py` launch (PR #130 variant) | Keep token stable across server relaunch within the same runtime (store on ctx, like PR #128 does) | Otherwise any relaunch logs out every tab. |
| Tests | `test_notebook.py` (new cell present, reconcile guarded), new `test_reconcile_rerun_guard.py`, `test_web_dashboard.py` (runtime_id present, stable across calls) | Regression protection. |

Untouched: `transfer_manager.py`, `telegram_*`, `session_vault.py` (except nothing), `drive_*`, `queue_manager.py`, `checkpoint_manager.py`.

---

## 8. Test Matrix

| # | Scenario | Procedure | Expected | Inspect | Pass criteria |
|---|---|---|---|---|---|
| 1 | "WebSocket" disconnect | N/A — no WS client. Instead: block `api/metrics` (DevTools offline 10 s) | Banner "retrying", then recovers; transfers continue | DevTools network, queue progress before/after | Progress advanced during outage; no duplicate rows |
| 2 | Browser refresh | Reload dashboard during active transfer | Full state restored from `/api/metrics` and `/api/universal/tasks` | Rows, percentages | Same items/states as before refresh |
| 3 | Brief network loss | Airplane mode 30 s on phone | Backoff then recovery | Banner transitions | No user action required |
| 4 | Android background/foreground | Switch apps 2, 10, 40 min | On return: immediate resync (Q4). If tab discarded → reload works | Banner; `runtime_id` unchanged | Same `runtime_id` ⇒ runtime alive; engine progress continued |
| 5 | Kill only dashboard server | In notebook: `from teledrive.web_dashboard import stop_web_dashboard; stop_web_dashboard(ctx)`; then run Reconnect cell | One new server; transfers unaffected | `threading.enumerate()` names; port | Exactly one `teledrive-web-dashboard` thread; engine counts unchanged |
| 6 | Runtime restart (real L4) | Runtime → Restart session in a test notebook | Reconnect cell prints RUNTIME LOST; Cells 1–4 restore checkpoint; `runtime_id` changes | Cell output, Drive checkpoint, queue | No duplicate Drive files (source_key), interrupted items in NeedsRetry, none auto-started |
| 7 | Reconnect while downloads active | Run Reconnect cell mid-transfer | URL reprinted; no reconcile; no new server | Logs "already running" | Item states unchanged before/after |
| 8 | No duplicates | Run Reconnect cell 5× and Cell 4 2× | One context, one server, one Gradio, no extra threads | `threading.enumerate()`, `ss -ltnp` ports | Thread/port counts stable; no `NeedsRetry` produced (Q2) |
| 9 | State restore | Refresh (#2) and VM restart (#6) | Refresh: exact; VM restart: Telegram rows from checkpoint, universal tasks absent (or "interrupted" if A1) | UI vs SQLite | Matches documented expectation |
| 10 | Sessions untouched | After all tests | Telegram still authorized; `TeleDrive_AppData` vault files unchanged (count + modified time) | Drive folder listing | No vault deletion/rewrite except normal autosave |

Isolated (CI) versions possible for 2, 5, 7, 8 (TestClient + fake context) and the reconcile guard. 1, 3, 4, 6, 10 require a real phone + Colab.

---

## 9. Limitations

- **Google Colab:** runtimes are not guaranteed; idle and maximum lifetimes are enforced by Google and not fully published; free tier can be reclaimed any time. Nothing in this repo can keep a free runtime alive indefinitely. `proxyPort` URLs are tied to the user's session and require the notebook frontend to obtain (`eval_js`).
- **Chrome/Android:** background tabs get timers throttled, can be frozen and discarded; no web API can prevent this for a normal page. Muted audio is not a reliable exemption.
- **Current architecture:** single process; universal tasks are in memory; SQLite on ephemeral disk; Drive checkpoint written after uploads only, not on every progress tick (partial downloads are not resumable after VM loss — they restart).
- **This investigation:** source inspection + one isolated test. No live Colab, proxy behavior, or phone behavior was observed. The ~30 minute figure is unexplained by code; the ranking above is evidence-weighted, not proven.

---

## 10. Effort and Unknowns

| Item | Size |
|---|---|
| Q2 reconcile guard + test | Small |
| Q1 Reconnect cell + Q3 message + notebook regen + contract tests | Small–Medium |
| Q4 frontend resilience + runtime_id | Small–Medium (more if rebased on PR #130) |
| Disk guard (D-06) | Small |
| Universal-task journal (local) | Medium |
| Supervisor | Medium (not recommended now) |
| VM migration | Large |

**Unknowns that need owner data:** (1) In the failing moment, does the dashboard URL still load if opened fresh? (yes ⇒ L1/L2; no ⇒ L3/L4). (2) Does the notebook show "Reconnect"/"Runtime disconnected" banner, and do variables like `ctx` still exist (`print(ctx)`)? (3) Phone or desktop? Which tab is in the foreground? (4) Free or Pro Colab?

---

## 11. Handoff Summary (for the coordinating assistant)

- **Strongest evidence:** (a) no WebSocket is used by the dashboard — polling only (`web_dashboard.py:1390-1412`, docstring 37-41); (b) Cell 1 refuses in a live runtime and tells the user to restart (`notebook_cells.py:138-145, 691-701`) → the documented recovery recipe destroys a still-running engine; (c) rerunning Cell 4 runs `reconcile_with_drive`, which flips live in-flight rows to `NeedsRetry` — **reproduced** in an isolated test.
- **Heartbeat** acts on the notebook tab only and cannot help the dashboard tab or Colab's limits.
- **Next safest action:** implement Q2 (reconcile guard) + Q1 (Reconnect cell) on a new branch, with tests, no engine changes; owner validates in a fresh test runtime. Then ask the owner the 4 diagnostic questions in §10 at the next disconnect to classify it as L1/L2/L3/L4.
- **Do not:** add more keep-alive tricks, auto-restart loops, module reloads, or a second uvicorn instance.
