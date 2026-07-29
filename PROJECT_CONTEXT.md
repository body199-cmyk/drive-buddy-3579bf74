# PROJECT_CONTEXT — TeleDrive / drive-buddy continuation file

Authority: `python-package/docs/CONSTITUTION.md` + Lovable Build Order v3.1.
Read this file, the constitution, `docs/AUDIT.md`, the newest phase report,
`python-package/CHANGELOG.md` and `python-package/HANDOFF.md` before editing anything.

## Status

- Phase 0: COMPLETE (docs, requirements.lock, spec_version/version 3.1.0).
- Phase 1: COMPLETE — see `python-package/docs/PHASE_REPORTS/PHASE_1.md`.
  - `teledrive/async_runtime.py`, `teledrive/app_context.py`,
    `tests/test_no_ad_hoc_loops.py`, `tests/test_app_context.py` exist.
  - `bootstrap.run()` returns the one `ApplicationContext`; `app.launch()` and
    `ui.build(ctx)` use it. Zero ad-hoc loops left in `teledrive/`.
- Phase 2: NOT STARTED. No `action_registry.py`, `handlers.py`, `ui_binder.py`.
- Phases 3–9: NOT STARTED. Telegram v3.1 state machine, native Colab Drive auth,
  scoped analysis/selection, queue/recovery hardening, UI/theme/export, notebook
  cells, CI — all still missing.

## Not verified (never claim otherwise)

- Real Telegram login: NOT verified.
- Real Drive authorization: NOT verified.
- Gradio 6.20.0 pin: NOT verified (gradio not installed in the build sandbox).

## Frontend

`src/` is intact and is a reference/download landing page only. It must never become
the Telegram/Drive runtime. Its copy is still stale (says v2, old OAuth flow, claims
buttons are connected) and is corrected in Phase 7, not before.

## Protocol per session

One phase, one focused change. End every session by updating this file,
`CHANGELOG.md`, `HANDOFF.md` and the phase report with real command output, real
Telegram/Drive verification status, blockers, and the next smallest step.
