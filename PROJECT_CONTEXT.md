# PROJECT_CONTEXT — TeleDrive / drive-buddy continuation file

Authority: `python-package/docs/CONSTITUTION.md` + Lovable Build Order v3.1.
Read this file, the constitution, `docs/AUDIT.md`, the newest phase report,
`python-package/CHANGELOG.md` and `python-package/HANDOFF.md` before editing anything.

## Status

- Phase 0: COMPLETE (docs, requirements.lock, spec_version/version 3.1.0).
- Phase 1: COMPLETE — one `ApplicationContext`, one asyncio loop, no ad-hoc loops.
- Phases 2–8: COMPLETE — action registry, handlers, ui_binder, v3.1 Telegram
  state machine, native Colab Drive auth (`drive_auth.adopt_service`), scoped
  analysis/selection, queue/recovery, UI/theme/export, 7-cell notebook, CI.
- Phase 9 (Colab readiness repair): COMPLETE in code — see
  `python-package/docs/PHASE_REPORTS/PHASE_9.md`.
  - Cell 4 is non-blocking (`launch(..., blocking=False)` →
    `prevent_thread_lock=True`); cells 5–7 run while the UI serves; the handle
    lives on `ctx.ui` and `ctx.shutdown()` closes it.
  - `requirements.lock` is the ONE dependency source; no notebook cell or
    `colab_cells.json` entry may hold a `package==version` literal (test-guarded).
  - CI runs pytest, `--check` binding, notebook sync, `bun run lint`, `bun run build`.

## Not verified (never claim otherwise)

- Real Telegram login: NOT verified.
- Real Drive authorization and a real upload/transfer: NOT verified.
- Gradio 6.20.0 pin and its `prevent_thread_lock` behaviour: NOT verified
  (gradio is not installed in the build sandbox).
- A real end-to-end Colab run of cells 1–7: NOT verified. It needs an
  interactive Colab runtime, Google consent and live Telegram credentials, so
  the operator must run it and record the redacted output in PHASE_9.md.

## Frontend

`src/` is a reference/download landing page only. It must never become the
Telegram/Drive runtime.

## Protocol per session

One phase, one focused change. End every session by updating this file,
`CHANGELOG.md`, `HANDOFF.md` and the phase report with real command output, real
Telegram/Drive verification status, blockers, and the next smallest step.
