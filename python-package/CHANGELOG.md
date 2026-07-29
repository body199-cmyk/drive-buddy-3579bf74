# Changelog

## v3.1.0-phase9 — 2026-07-29 (audit repair)

- `app.launch()` gained `blocking` (default False) and now passes
  `prevent_thread_lock` to Gradio; the handle is kept on `ctx.ui` and closed by
  `ctx.shutdown()`. Notebook cell 4 no longer blocks cells 5-7.
- `teledrive_launcher.py` launches with `blocking=True` (process must stay alive).
- `requirements.lock` is the single dependency source: notebook cells (and the
  generated `colab_cells.json`) may not contain any `package==version` literal.
- CI runs `bun run lint` before `bun run build`.
- Tests: 177 passed. Real Telegram/Drive Colab run still NOT verified.

## v3.1.0-phase1 — 2026-07-29

- Added `teledrive/async_runtime.py`: the single background event loop for the process.
- Added `teledrive/app_context.py`: one `ApplicationContext` owning config, aio, db,
  auth, queue_manager, progress and `UIState`, with strict `resolve()`.
- `bootstrap.run()` now returns the context; `app.launch()` and `ui.build(ctx)` use it.
- Removed all six ad-hoc `asyncio.new_event_loop()` calls and the transfer worker
  thread from `ui.py`; removed the inline lambda handler.
- Added `tests/test_no_ad_hoc_loops.py` (permanent Section 3 guard) and
  `tests/test_app_context.py`. 48 tests pass.
- Not done: action registry / UI binder, v3.1 Telegram auth, native Colab Drive auth.

## v3.1.0-phase0 — 2026-07-29

- Audit and alignment only: CONSTITUTION.md, AUDIT.md, PHASE_0 report,
  requirements.lock, spec_version/version = 3.1.0.

## v1.0.0 — 2026-07-29

- Initial release per Constitution v2.0.
- Telethon user-account client + Google Drive OAuth Desktop.
- SQLite (WAL) + atomic checkpoints exported to Drive `TeleDrive_AppData`.
- State machine with 12 states and strict transitions.
- Concurrency Safe/Balanced/Fast/Manual, hard cap 4.
- Retry: 5 attempts, base 2s, x2, cap 60s, jitter, transient-only.
- FloodWait honored, reauth surfaced, duplicates detected via `appProperties.source_key`.
- Gradio UI in Arabic + English (live toggle, RTL for Arabic).
- 6-cell Colab notebook, camera cell handoff generator, maintenance cell.
