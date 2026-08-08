# PHASE 1: Single ApplicationContext + one AsyncRuntime

Date: 2026-07-29 · Repository: drive-buddy · Branch: main
Previous audited commit: 6ff9e7f5 (Phase 0 committed)
Commit SHA for this phase: not produced by this environment — git state is managed
by the Lovable platform, so no SHA can be pasted honestly here. The files below are
committed by the platform as one Phase 1 change.

## Files inspected

- python-package/teledrive/{config,bootstrap,app,ui,auth_manager,queue_manager,
  progress_tracker,transfer_manager,database}.py
- python-package/tests/conftest.py, python-package/tests/test_concurrency.py
- python-package/docs/CONSTITUTION.md, docs/PHASE_REPORTS/PHASE_0.md

## Files created

- `teledrive/async_runtime.py` — `AsyncRuntime`: one background daemon thread owning
  one event loop; `start/stop/run/submit/call_soon`; `AsyncRuntimeError` when used
  before start or after stop. The ONLY file allowed to call `asyncio.new_event_loop()`.
- `teledrive/app_context.py` — `ApplicationContext` (config, aio, db, auth,
  queue_manager, progress, ui_state, plus declared `telegram_auth`, `drive_auth`,
  `transfer_manager` slots for later phases), strict `resolve()` raising
  `ServicePathError` on typo / None service / non-callable, and
  `create_context()/get_context()/has_context()/reset_context()`.
- `tests/test_no_ad_hoc_loops.py` — permanent guard: no package file other than
  `async_runtime.py` may contain `asyncio.new_event_loop(`, `asyncio.run(` or
  `run_until_complete(`.
- `tests/test_app_context.py` — same-loop proof, singleton proof, resolve success and
  four resolve failure cases, stopped-runtime refusal.

## Files changed

- `teledrive/bootstrap.py` — now returns the single `ApplicationContext`; the previous
  dict is preserved as `ctx.bootstrap_info`.
- `teledrive/app.py` — `launch()` builds one context and passes it to `ui.build(ctx)`.
- `teledrive/ui.py` — every handler now uses `ctx.aio.run(...)`; six ad-hoc event loops
  and the transfer worker thread removed; `AUTH`/`QUEUE`/`PROGRESS` globals replaced by
  `ctx.auth` / `ctx.queue_manager` / `ctx.progress`; the inline `lambda` handler removed;
  `build(ctx)` signature.

## Behavior changed

- Exactly one asyncio loop for the process. Transfers run via `ctx.aio.submit(...)` on
  that loop instead of a per-start thread + loop.
- Nothing else changed: Telegram auth is still the old flow, Drive is still the old
  OAuth-JSON flow, analyze still auto-enqueues, ACTION_SPECS/UIBinder do not exist.
  Those remain Phase 2–5 work and are NOT claimed as fixed.

## Tests run (actual output)

```
$ python3 -m compileall -q teledrive
(exit 0, no output)

$ python3 -m pytest -q tests
................................................                         [100%]
48 passed in 0.66s

$ bun run build
[nitro] ✔ You can preview this build using npx vite preview
[nitro] ✔ You can deploy this build using npx nitro deploy --prebuilt
(exit 0)

$ bun run lint
✖ 6 problems (0 errors, 6 warnings)   # react-refresh warnings in src/components/ui/*
```

Gradio smoke check — FAILED TO RUN, not passed:

```
$ python3 -c "import gradio as gr
with gr.Blocks() as d: gr.Markdown('smoke')
print('gradio', gr.__version__)"
ModuleNotFoundError: No module named 'gradio'
```

Gradio is not installed in this sandbox and cannot be installed into the Colab runtime
from here. `requirements.lock` still pins `gradio==6.20.0`; that pin is UNVERIFIED
against the existing `gr.Blocks/Tab/Dataframe` usage and must be smoke-tested in a real
Colab session before Phase 7. No architecture change was made to work around it.

## Real connection status

- Telegram: NOT verified. No credentials touched, no login attempted.
- Drive: NOT verified. No authorization attempted.

## Remaining blockers

1. Gradio 6.20.0 pin unverified in Colab (import smoke check could not run here).
2. `ui.py` still has un-bound controls, old Drive OAuth flow, auto-enqueue on analyze.
3. `tests/test_concurrency.py` still calls `asyncio.run(` — allowed, the guard scopes to
   the `teledrive/` package only, but the test should move onto `AsyncRuntime` in Phase 6.
4. `public/teledrive-package.zip` still tracked despite .gitignore.

## Exact next smallest step

Phase 2: add `teledrive/action_registry.py` (ACTION_SPECS with
action_id/handler_name/service_path/label_key/section/implemented/tested),
`teledrive/handlers.py`, `teledrive/ui_binder.py` with `DeadControlError`,
`UnknownActionError`, `wire()` and `assert_complete()`, plus binding tests. No new
features — only move existing wiring behind the binder.

Stopping for owner approval.
