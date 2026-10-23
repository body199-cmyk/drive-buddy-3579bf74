# TeleDrive Disconnect & Recovery — Durable Context / Handoff

> **Purpose:** This is the durable, project-local context for the recurring Colab/dashboard disconnect (often noticed around 30 minutes), the failed keep-alive experiment, and the safe recovery plan. Read this before changing notebook startup, dashboard polling, the application context, downloads, checkpoints, or session-vault behavior.
>
> **Status at creation (2026-10-23): DOCUMENTATION / INVESTIGATION ONLY.** No runtime test was performed in this task. No application code, notebook cell, package release, Google Drive file, or Telegram session was changed. Work is on branch `docs/tele-drive-disconnect-recovery-context`; `main` is untouched.

## 1. Owner goal and non-negotiable constraints

The owner reports that the TeleDrive web interface / Colab connection often becomes unavailable after roughly half an hour. Recovery has sometimes meant refreshing/reconnecting and rerunning Cells 1–4, after which downloads may need manual resumption. A prior heartbeat/keep-alive cell did not solve the problem.

The goal is **safe, evidence-led recovery**, not a promise of unlimited Colab uptime:

1. Identify which layer failed before selecting recovery.
2. If only the browser view or proxy link failed, reconnect the view to the **existing** live application context and transfer engine.
3. Do not reinstall packages or create a second context, event loop, Telegram client, Drive client, transfer manager, worker set, or dashboard server as a first response.
4. Preserve the existing Colab pipeline, local runtime state where it survives, Google Drive contents, the Drive session-vault manifest/files, Telegram authorization/session, queue/checkpoints, and completed uploads.
5. Never edit `main` directly. Use a separate branch and PR; owner approval is required before merge or live Colab actions.
6. Do not claim tests passed unless actually run. CI/unit tests are not a substitute for an owner-run live Colab + Drive + Telegram test.
7. Keep the current Colab solution as the baseline. Any always-on VM is a separate, optional future project, not a migration hidden inside this repair.
8. No attempt to bypass Colab's published or unpublished usage/session limits with fake activity. Keep-alive is not an uptime guarantee and may be ineffective or contrary to platform expectations.

## 2. Current source-of-truth findings verified by reading GitHub files

Repository: `body199-cmyk/drive-buddy-3579bf74`  
Default branch inspected: `main`  
Key files inspected:
- `python-package/teledrive/web_dashboard.py`
- `python-package/teledrive/colab_cells.json`
- `python-package/teledrive/app_context.py`
- `python-package/teledrive/bootstrap.py`
- `python-package/teledrive/session_vault.py` (path/role reviewed; re-read before editing)
- `python-package/tests/test_web_dashboard.py`
- `docs/PROJECT_CONTEXT.md`, `docs/ARCHITECTURE.md`, `docs/CONSTITUTION.md`, `docs/TODO.md`, `docs/AI_HANDOFF.md`, `README.md`

These are **source inspections**, not live-runtime observations.

### 2.1 The primary dashboard contract is HTTP polling, not WebSocket

- `web_dashboard.py` describes the dashboard as FastAPI + AJAX polling.
- The page requests relative `api/metrics?t=...` with `cache: "no-store"`.
- The existing polling uses `setInterval(pollMetrics, interval)`; the default is 1000 ms and persisted settings allow off / 1000 / 2000 / 5000 ms.
- Poll failures currently update a simple status label; there is no robust classified retry/backoff chain or visibility/online/pageshow recovery confirmed in the inspected source.
- `/api/metrics` composes real snapshots from the context's progress tracker, queue manager and live UI state; it is not intended to fabricate queue state.
- `/api/health` currently returns only `ok`, service name and package version. It does **not** currently expose a process/runtime identity, uptime, PID, actual port, or engine-loop status.
- `/api/state` and `/api/metrics` already exist.
- The `/ws` endpoint is optional and one-way: it sends metrics every second, catches exceptions, and explicitly treats polling as the contract. Losing only this WebSocket should not be treated as proof that the page or transfer engine is dead.
- Existing test `test_page_is_self_contained_and_polls_relative_metrics` asserts the polling implementation, including `setInterval(pollMetrics,interval)`. Any polling redesign must update that test in the same change.

**Consequence:** Do not spend the first fix on WebSocket ping/pong or a new WebSocket reconnect protocol. Diagnose the HTTP poll/proxy/runtime path first.

### 2.2 Dashboard server lifecycle and port reporting

- Uvicorn runs in a dedicated daemon thread named `teledrive-web-dashboard`; the application work remains owned by the single `ctx.aio` loop. This separation is deliberate: a Uvicorn startup failure must not kill the transfer/application loop.
- `_run_server_isolated` records an exception on the server handle; startup is checked by `_wait_until_started`.
- `launch_web_dashboard(ctx, port=...)` reuses the server already attached to **that same context** if it is marked started, not exiting, and its thread is alive.
- On the reuse path it returns early and does **not** re-print the Colab proxy URL.
- If the requested port is occupied, `_select_dashboard_port` tries the requested port, then 8766–8800, then an OS-assigned port. This is not the 8765–8795 range mentioned in an earlier report.
- The launcher prints the actual fallback port in a warning, and creates the proxy URL for the actual port when it launches a new server.
- **Confirmed notebook output bug:** Cell 4 calls `launch_web_dashboard(ctx, port=WEB_DASHBOARD_PORT)` but then prints `WEB_DASHBOARD_PORT`, not `web_server.config.port`. If a fallback port is chosen, the subsequent “web dashboard: OK on port …” line can be wrong even though the launcher separately prints the actual port and URL.
- A server in a different/stale context is not automatically discoverable through the new context's `ctx.web_dashboard`. A new context plus an old listening server could therefore create port drift; this is a hypothesis to test, not a confirmed live incident.
- `stop_web_dashboard` requests exit, joins for five seconds, and clears the context handle. Do not build a watchdog that starts a second server merely because an HTTP request failed.

### 2.3 Notebook startup / the destructive recovery trap

The current `python-package/teledrive/colab_cells.json` contains these important behaviors:

- **Cell 1** checks whether any `teledrive` modules are already imported. If so, it refuses package replacement and tells the owner to restart the runtime, then run Cells 1–4 again. This fail-closed update gate is intentional: package replacement must not hot-swap imported modules.
- Cell 1 says it changes the package extraction/install area (for example `/content/teledrive-v4.5/`) and uses `TELEDRIVE_ROOT=/content/teledrive_runtime`; it is explicitly designed not to replace the runtime state/SQLite/checkpoints or Drive files during package update.
- **Cell 2** calls `bootstrap.run()`, which creates a new `ApplicationContext` through `create_context()` and runs DB migrations. The inspected `bootstrap.run()` itself does not show an idempotent context-reuse guard.
- **Cell 3** performs native Colab Drive auth and probes the Telegram session vault.
- **Cell 4** adopts the Drive service, attempts session restore / credentials setup, calls `ctx.checkpoints.restore_and_reconcile()`, then launches the chosen UI(s). The checkpoint call is documented in the notebook as “safe state, no auto-resume.”
- Cell 4's normal flow launches Classic Gradio and/or the modern dashboard on the one context. Cell 7 calls `ctx.shutdown()` and is a cleanup/shutdown cell, not a reconnect cell.
- Re-running Cells 1–4 is therefore not a safe first-line recovery for a browser-only problem: it can force a runtime restart due to Cell 1's gate, or create a new context if run in a live process; the latter's consequences need a live check. A runtime restart terminates in-memory workers, the asyncio runtime, client objects and dashboard thread.
- `restore_and_reconcile()` must be read and its live/running-item semantics verified before any recovery path invokes it. The proposed recovery cell below deliberately omits it.

### 2.4 Context ownership and persistent state

- `ApplicationContext` is designed as the owner of one `AsyncRuntime`, queue manager, Telegram auth/client, Drive auth/client, session vault, transfer manager, handlers and dashboard handle. The dashboard adapter should not instantiate its own transfer engine.
- The current architecture describes SQLite as local-first under `/content/teledrive_runtime` with WAL and local checkpoints, plus durable per-item checkpoints on Drive. The session vault separately stores a versioned Drive backup of Telegram session/credentials according to its documented manifest/commit protocol.
- A browser refresh does not itself imply that SQLite or the engine was reset.
- A Python process/runtime replacement loses in-memory objects and local `/content` data may not survive a VM recycle. Drive checkpoints/session vault can support recovery but are not proof that every active partial download is resumable.
- Do not describe all queue state as “in-memory only”: the source architecture has SQLite and checkpoints. Equally, do not promise complete recovery after a VM recycle without verifying checkpoint coverage and each downloader's resume semantics.
- Current documentation says auto-resume is deliberately not performed after checkpoint reconciliation. Keep that policy until deduplication and downloader-specific resume are proved.

### 2.5 Keep-alive cell

- The source's optional keep-alive code includes notebook output/heartbeat behavior and browser-side JavaScript that attempts to click Colab's Connect control. It runs in the notebook tab, not the dashboard tab.
- That does not prove the dashboard HTTP poll works, does not prove the proxy session is valid, and cannot prevent Android from throttling/freezing/discarding a background tab or Colab from ending a runtime.
- A kernel printout is not evidence that the dashboard page is still authorized/reachable.
- Keep this feature optional and accurately labelled as best-effort. Do not add fake audio/activity or more aggressive click loops as the “fix.” No code should promise indefinite uptime on free Colab.

## 3. Comparison of the three external reports

The owner supplied three reports. The first two reports' author attribution is not established in this handoff; the third was introduced by the owner as the strongest Claude report. Their claims are input evidence, not automatically verified facts.

### Shared, useful conclusions
1. Diagnose first; distinguish browser/tab, network, Colab proxy/frontend, dashboard server, Python process/runtime, and task/worker state.
2. A keep-alive cell running in the notebook tab does not solve every layer.
3. A recovery operation should be lighter than full notebook startup and should never call package installation or context bootstrap when the existing engine is alive.
4. Improve the existing polling path before adding a WebSocket reconnection system.
5. A watchdog, Drive task journal and auto-resume are higher-risk follow-on work, not first steps.
6. External hosting may avoid Colab's runtime lifetime limits but is a separate architectural/security/cost project.

### Claims corrected or kept open after source inspection
- **Corrected:** The relevant fallback port range in current source is 8766–8800 (after preferred port), not 8766–8795 or 8765–8795.
- **Confirmed from source:** Polling is the page's primary contract; the WebSocket is optional and failures are swallowed.
- **Confirmed from source:** The health endpoint is currently too small to distinguish a changed process/runtime.
- **Confirmed from source:** Cell 4 reports the requested port variable after launch, which can disagree with the selected actual port.
- **Confirmed from source:** The launcher reuse path returns without printing a fresh proxy URL.
- **Not proven:** The recurring ~30-minute failure is caused by Android tab freezing, Colab idle reclamation, proxy URL expiration, a server crash, or a runtime reset. No live runtime/logs were available.
- **Not proven:** An orphan server or multiple Uvicorn instances are currently occurring. Port fallback and context ownership make this worth observing, not assuming.
- **Not proven:** `bootstrap.run()` is safe to run twice in the same live process; source suggests a fresh context is constructed.
- **Not proven:** Exactly which task rows/checkpoints and partial files survive each kind of Colab restart/recycle.
- **Not proven:** A notebook proxy URL will continue to answer after the notebook tab is closed/backgrounded.
- **Do not rely on exact Colab idle/maximum-lifetime numbers from the reports.** The reports themselves acknowledge limits may be unpublished and context-dependent. Confirm current official policy if discussing plan limits, but never promise code can defeat them.

## 4. Failure taxonomy and the recovery that matches each layer

| Observed evidence | Likely layer | Safe response |
|---|---|---|
| Page is asleep/offline, then works after foreground/network return; runtime stays alive | Browser / network | Resume polling on `visibilitychange`, `online`, `pageshow`; bounded retry/backoff; do not restart server/engine |
| `/api/health` returns 401/403, sign-in HTML, or non-JSON through the proxy while runtime is demonstrably alive | Colab proxy/auth/frontend | Reopen notebook, run a reattach cell to re-announce the official URL; no package update/bootstrap |
| Local/loopback health fails and the dashboard thread is confirmed dead, but `ctx.aio` and transfers are demonstrably alive | Dashboard server | First manual recovery; later consider a bounded watchdog that restarts only a provably dead server |
| Server thread is alive but loopback health fails | Hung server / overload / thread issue | Diagnose; do not bind a second server while the first thread may still own the port |
| Fresh kernel/process; runtime identity changes; in-memory objects absent | Runtime/process replaced | Normal startup path may be required; restore state paused and avoid auto-resume until dedupe/resume rules are verified |
| UI reports failure but `/api/metrics` still changes and transfer progress/bytes continue | UI/proxy/browser layer | Reattach UI only; don't interrupt the worker |
| Port in Cell 4 output differs from actual URL port | Reporting/port selection | Print `web_server.config.port`; use the URL emitted by launcher |

The test needs to observe both the dashboard and the engine. A successful health response alone does not prove that transfer workers are healthy; a failed browser fetch alone does not prove the Python runtime died.

## 5. Proposed implementation plan — one independently reviewable step at a time

### Step 0 — Evidence and baseline (no Drive writes by default)
- Capture the exact failure moment: time, whether Colab says connected/reconnect/fresh kernel, whether the dashboard tab is backgrounded, and whether the notebook can still execute a harmless diagnostic cell.
- Query `/api/health` and `/api/metrics` from the dashboard link at the time of failure, where possible; note status code/content type and whether progress is still advancing.
- Add or test non-secret health identity fields only after the existing handler/tests are understood: a process/runtime UUID generated once per Python process, PID, process uptime, actual listening port, dashboard thread alive, and `ctx.aio.is_running`. Use names/semantics that don't imply a host reboot when only a Python process changed.
- Do **not** create a Drive heartbeat file in the first change. It writes to user data and introduces Drive lock/latency/cleanup considerations. Consider a new, dedicated, rate-limited diagnostic object only with owner approval and after deciding exactly what it stores. Never reuse or mutate the session-vault manifest.
- Establish a baseline of relevant existing CI/tests before code changes. The present inspection did not run them.

### Step 1 — Minimal, reversible notebook reattach cell
- Add a new cell at the end (or a clearly safe optional cell) in `python-package/teledrive/colab_cells.json` and regenerate the canonical notebook using the repository's documented generator/checks; do not hand-edit only the generated notebook.
- It must check that the existing `ctx` and expected modules are available, and report whether `ctx.aio.is_running` is true. If not, it must not claim that the engine is alive or silently start a new context.
- When the same context/server is alive, call the idempotent `launch_web_dashboard(ctx, port=8765)` only after verifying the API contract, and print the **actual** `srv.config.port`.
- Because the current reuse path does not reprint the URL, make the smallest source change to announce a fresh official proxy URL on reuse, using the existing `colab_proxy_url(actual_port)` mechanism. Check its behavior live; do not assume it renews expired authorization by itself.
- Never call `pkg_try_update`, `bootstrap.run()`, `restore_from_context`, `set_credentials`, `restore_and_reconcile()`, or `ctx.shutdown()` from this cell.
- Guard against stale/dead context, missing objects, dead event loop, and duplicate servers. A simplistic check for `"teledrive" in sys.modules` plus a global `ctx` is insufficient proof that the transfer engine is healthy.
- The current source has a deliberate single-context rule. Do not solve this by starting another application context or standalone supervisor.

### Step 2 — Browser polling resilience
- Replace the fixed interval with a bounded `setTimeout`-style loop only if the existing code/test contract is updated together.
- Classify offline/network errors, HTTP 401/403 or HTML sign-in responses, 5xx/502, and malformed JSON. Show actionable Arabic/English UI status; do not imply a runtime reset from one failed fetch.
- Use capped exponential backoff (e.g. 1, 2, 4, 8… up to 30 seconds, with jitter), avoid overlapping requests, pause or reduce polling while hidden, and poll immediately on `visibilitychange`, `online`, and `pageshow`.
- Preserve the saved auto-refresh setting (off / 1 / 2 / 5 seconds) and don't make hidden tabs poll aggressively. Preserve all current controls, Arabic RTL, security rules and relative API URLs.
- Next successful `/api/metrics` response is the current-state refresh; do not invent a second state store or WebSocket resync protocol.

### Step 3 — Fix the actual-port reporting bug
- Cell 4 should print `web_server.config.port` (when a server handle exists), not `WEB_DASHBOARD_PORT`.
- Test both the normal port and forced-port-conflict path. Verify that the printed URL and port correspond to the same server.

### Step 4 — Bounded watchdog (only if evidence justifies it)
- Prefer a small same-process watchdog over a separate supervisor, preserving one `ApplicationContext` and one application loop.
- Restart only after the server thread is **provably dead** and shutdown was not intentional. Use a strict attempt budget (suggested maximum 3 attempts per 10 minutes), structured recovery logs and shutdown integration.
- If the server thread is alive but unresponsive, do not bind another listener. Mark it hung and report it; recovery semantics for a hung Uvicorn thread need a tested design.
- Never let a health-check failure alone cause a second server while the original thread may still hold the port.
- Avoid creating two watchdogs on repeated calls to `launch_web_dashboard`.

### Step 5 — Durable DB snapshot / task journal (later, only if needed)
- First audit the existing SQLite schema, checkpoint service, Drive serialization lock, session-vault manifest commit protocol, and restore reconciliation.
- If needed, use SQLite's backup API to create a versioned consistent local snapshot and upload to a **separate** diagnostic/state location using a manifest/commit point. Rate-limit (for example 5–10 minutes plus meaningful state transitions), do not upload every second, and do not interfere with the one Drive writer lock.
- A Drive copy of SQLite does not restore local `.part` files, nor does it prove arbitrary downloader resume is safe.
- Keep Telegram session-vault files and manifest untouched by this feature.

### Step 6 — Opt-in auto-resume (last, high risk)
- Implement only after proving each downloader's pause/resume/retry semantics, Drive dedupe keys, checkpoint transitions, and behavior when a VM disappears during local download vs. Drive upload.
- Restore tasks as paused by default. Auto-resume must be explicit opt-in and idempotent; do not start two copies of one task or re-upload duplicates.
- Current universal downloader notes say gdown pause is not safely supported; retry may be a fresh task, not byte-level resume. Do not claim a universal resume capability.

### Step 7 — Optional always-on host pilot (separate project)
- An always-on VM is the architectural path to remove Colab lifetime dependency, but adds costs/ops, authentication, TLS, user isolation, secret management, Drive OAuth, Telegram session migration and security work.
- Hosting only the frontend elsewhere does not keep the Colab engine alive.
- Keep the current Colab workflow intact while evaluating any pilot.

## 6. Required test matrix before accepting changes

No tests in this matrix were run while preparing this document. Run applicable unit/CI tests and then owner-run live tests.

1. **Normal launch:** health, metrics and URL work; actual port equals the listener.
2. **Forced port conflict:** launcher selects fallback; both Cell 4 and launcher print the correct actual port and URL.
3. **Reuse path:** run reattach cell while the same server and active transfer are alive; same server handle/thread, no extra server, URL re-announced, worker count unchanged.
4. **Refresh page:** same runtime identity and queue state; no duplicate task.
5. **Brief network loss:** actionable offline status, bounded retry, automatic return, no transfer changes.
6. **Android background/foreground (5/15/35 min):** observe if polling resumes; record whether runtime and proxy are still alive. This is an experiment, not a guaranteed outcome.
7. **Proxy authorization failure:** distinguish 401/403/sign-in HTML from an actual dead runtime; reattach does not restart engine.
8. **Dashboard thread deliberately stopped in a test fixture:** application loop and transfer worker remain alive; no duplicate server; if watchdog exists, one bounded recovery.
9. **Hung server simulation:** no second listener while original server thread is alive.
10. **Fresh runtime/process:** new runtime identity; normal startup restores available state paused; no automatic duplicate task.
11. **Checkpoint reconciliation:** separately test active/running statuses before allowing any recovery cell to invoke it.
12. **Secrets/state preservation:** compare Git diff and relevant Drive/session-vault manifest/file metadata before and after; no credentials/tokens/session contents in logs or repository.
13. **Existing regressions:** full Python suite, notebook generation/checks, package build and frontend lint/build per repository Constitution/CI. Record exact commands, run links, commit SHA and result. CI success does not replace live Colab verification.

For the decisive live diagnostic, at the moment the page fails, determine: (a) can the notebook still execute, (b) does the official proxy URL answer `/api/health`, (c) does `/api/metrics` advance, (d) is the same Python context/process alive, and (e) do transfer bytes/progress continue? These observations choose the correct recovery layer.

## 7. Files and areas that must be re-read before editing

- `python-package/teledrive/web_dashboard.py`: `create_web_app`, `/api/health`, `/api/metrics`, polling code inside `HTML_PAGE`, `/ws`, `_select_dashboard_port`, `launch_web_dashboard`, `stop_web_dashboard`, proxy URL helpers imported from `app.py`.
- `python-package/teledrive/colab_cells.json`: Cell 1 update gate, Cell 2 bootstrap, Cell 3 auth/vault, Cell 4 launch and `restore_and_reconcile()`, optional keep-alive/stop cells, cell titles/order.
- `python-package/teledrive/app_context.py`, `async_runtime.py`, `bootstrap.py`: context creation, loop state and shutdown.
- `python-package/teledrive/checkpoint_manager.py` / service implementation in `services.py`: restore/reconcile behavior and running item transitions.
- `python-package/teledrive/session_vault.py`: existing Drive manifest/commit semantics; do not reuse this vault for dashboard diagnostics.
- `python-package/teledrive/universal_downloader.py`, `transfer_manager.py`, `queue_manager.py`, `database.py`, `migrations.py`: worker and persistence contracts.
- `python-package/tests/test_web_dashboard.py`, related notebook generator tests and CI workflows.
- `docs/CONSTITUTION.md`, `docs/ARCHITECTURE.md`, `docs/PROJECT_CONTEXT.md`, `docs/TODO.md`, `docs/KNOWN_ISSUES.md`, and this file.

## 8. Explicitly prohibited shortcuts

- Do not change or merge to `main) without approval.
- Do not rerun Cells 1–4 as the first response to a browser-only disconnect.
- Do not call `bootstrap.run()` from a recovery cell.
- Do not call `restore_and_reconcile()` while existing transfers might be running until its behavior is proven.
- Do not create another `ApplicationContext`, AsyncRuntime, Telegram client, Drive service, transfer manager or worker set to “fix” the UI.
- Do not start a second Uvicorn server because a proxy fetch failed or an existing thread is merely slow.
- Do not add a WebSocket reconnect system as the primary fix while polling is the actual contract.
- Do not write diagnostic heartbeats into the user's Drive by default or mutate the session vault.
- Do not enable auto-resume before dedupe/resume proofs.
- Do not claim a live Colab test, a GitHub Actions pass, a successful reconnect, or an uninterrupted transfer without actual evidence.
- Do not promise that Colab or Android can be kept alive indefinitely by JavaScript, audio, clicks, or kernel prints.

## 9. Current decision and next action

**Decision:** Start with diagnosis plus a tiny, reversible recovery-cell/URL fix. The most valuable first user-visible improvement is to avoid the destructive full restart when only the dashboard link/view failed. Add runtime identity and classified polling after the baseline and API/test contracts are clear. Keep watchdog, Drive journaling and auto-resume out of the first PR.

**Next action for the implementing agent:**
1. Re-read this file and the repository Constitution.
2. Inspect current branch/HEAD and any open PRs before coding; this documentation PR may be separate from the future runtime-fix PR.
3. Re-read `restore_and_reconcile()` and the full notebook generator contract.
4. Propose the smallest implementation diff on a new feature branch, update tests in the same PR, and provide rollback instructions.
5. Do not merge or run live Colab/Drive operations until the owner approves.

## 10. Provenance and honesty record

- The three investigation reports were provided by the owner in chat; only report 3 was explicitly introduced as the strongest Claude report. Their claims were cross-checked against selected current GitHub files where possible.
- GitHub source reads confirmed the polling contract, the optional WebSocket behavior, the small health endpoint, the launch reuse behavior, the fallback port range, the Cell 4 requested-port print, and the Cell 1/2/4 startup behavior described above.
- No live Colab runtime, Android browser, proxy URL, active transfer, Drive metadata, Telegram session, or failure logs were accessible during this task.
- No tests were run in this task.
- This document is a context/handoff, not proof that the underlying failure is fixed.
