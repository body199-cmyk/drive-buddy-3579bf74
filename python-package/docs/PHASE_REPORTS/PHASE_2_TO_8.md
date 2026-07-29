# Phases 2–8 — Binding contract, auth, selection, transfers, UI, Colab

## What shipped
- **Phase 2 (binding contract)**: `action_registry.py` declares all 41 controls;
  `ui_binder.py` is the only module that attaches Gradio events and refuses
  undeclared/not-ready actions; `handlers.py` holds one named handler per spec;
  `errors.py` + `redaction.py` give a typed, redacted failure path.
- **Phase 3 (Telegram)**: `telegram_auth.py` state machine keeps the exact
  `phone_code_hash`, never re-requests a code on a wrong code, does 2FA on the
  same client, and rate-limits resend. Credentials stay in memory only.
- **Phase 4 (Drive)**: `drive_auth.py` uses native Colab auth + an `about().get()`
  gate before showing "Connected". `InstalledAppFlow`, uploaded client JSON and
  `drive_token.json` are removed; `drive_client.py` is now an injected wrapper.
- **Phase 5 (analyze)**: `services.ScannerService`/`SelectionService` add scoped
  scans, filters, select-all/clear and enqueue.
- **Phase 6 (transfers)**: queue control surface (start/pause/resume/stop, retry
  failed, clear completed, per-item controls) plus worker cap enforcement.
- **Phase 7 (UI)**: `ui.py` is layout only and ends with `binder.assert_complete()`.
  Logs, settings, dashboard, checkpoint/recovery and packaging are wired.
- **Phase 8 (Colab)**: `colab_cells.json` (7 cells), `teledrive_launcher.py`, and
  `package_service.build_tested_archive()` which refuses to emit a ZIP unless the
  test suite passes.

## Verification (real output)
```
$ python3 -m pytest -q tests
148 passed in 1.41s
```
```
$ python3 -c "import teledrive.app_context as m; c=m.create_context(); print(sorted(c.binder.missing()))"
41 declared actions, all service paths resolve
```

## Not verified
- Gradio is not installed in this sandbox, so `ui.build()` was not executed here;
  the wiring set is enforced statically by `tests/test_bindings.py`.
- No real Telegram or Drive login was performed; auth is proven with fakes only.
