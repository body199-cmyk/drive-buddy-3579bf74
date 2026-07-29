# AUDIT — Ground truth as of commit `0a3eee0` (2026-07-29)

Reproduced verbatim from Section 1 of the **Lovable Build Order v3.1 (Single-File
Execution Brief)**. Do not re-argue this; use it.

## 1.1 What is REAL and must be KEPT

`python-package/` contains a genuine, working-shaped Python package. These files exist as
real `.py` files:

```plain
python-package/
  requirements.txt
  README.md  CHANGELOG.md  HANDOFF.md
  .env.example
  docs/ARCHITECTURE.md  docs/RUNBOOK.md  docs/TROUBLESHOOTING.md
  notebook/TeleDrive.ipynb
  teledrive/
    __init__.py  app.py  auth_manager.py  bootstrap.py
    checkpoint_manager.py  config.py  database.py  migrations.py
    drive_client.py  drive_quota.py  duplicate_detector.py
    error_handler.py  filters.py  handoff.py  i18n.py
    locale/ar.json  locale/en.json
    logging_config.py  media_scanner.py  models.py
    progress_tracker.py  queue_manager.py  retry_policy.py
    snapshot.py  state_machine.py  storage_manager.py
    telegram_client.py  telegram_links.py  transfer_manager.py
    ui.py  utils.py
  tests/
    conftest.py  mocks/{fake_clock,fake_drive,fake_fs,fake_telegram}.py
    test_concurrency.py  test_config.py  test_drive_quota.py
    test_duplicate_detector.py  test_error_messages.py
    test_filters.py  test_i18n.py  (+ others)
```

**Verdict: the backend services layer is roughly 60% correct.** `queue_manager.py`,
`state_machine.py`, `database.py`, `migrations.py`, `filters.py`, `retry_policy.py`,
`duplicate_detector.py`, `storage_manager.py`, `checkpoint_manager.py`,
`progress_tracker.py`, `telegram_links.py`, `media_scanner.py`, `transfer_manager.py`,
`i18n.py` and the two locale files are acceptable foundations. Improve them only where a
task in the build order says so.

## 1.2 What is WRONG — the 10 confirmed defects

| # | Defect | Evidence in repo | Constitution rule violated |
| ---| ---| ---| --- |
| D1 | Section 4A does not exist at all. No Action Registry, no UI Binder, no named-handler layer. `ui.py` calls `.click(...)` directly and even uses an inline `lambda`. | `ui.py` lines with `refresh_q.click(lambda: ui_queue_rows(), ...)` | Rules 17, 19; Section 4A entirely |
| D2 | No ApplicationContext. Runtime state is module-level singletons `AUTH`, `CONFIG`, `QUEUE`, `PROGRESS` plus module globals `_transfer_mgr`, `_transfer_thread`, `_transfer_loop`. | `auth_manager.py`, `ui.py` top | Section 2 "Shared ApplicationContext" |
| D3 | Broken async model — this will actually fail at runtime. Every handler creates `asyncio.new_event_loop()` and calls `run_until_complete`. The Telethon client is bound to the loop that created it, so `send_code` then `verify_code` run on different loops. Login will hang or raise. | `ui_connect_telegram`, `ui_send_code`, `ui_verify_code`, `ui_analyze` in `ui.py` | Section 4A.2 proof requirement |
| D4 | `phone_code_hash` is thrown away. `start_login()` returns the hash, `ui_send_code` ignores it, `complete_login()` calls `sign_in(phone=..., code=...)` without it. Code+2FA are collapsed into one call. No 10-state machine, no resend cooldown, no change-number, no change-account. | `telegram_client.py`, `ui.py` | Section 5 |
| D5 | Wrong Google Drive auth. Uses a user-uploaded OAuth `client_secret.json` desktop flow, paste-the-code textbox, and a persisted `drive_token.json`. Constitution mandates native Colab auth and forbids persisted tokens. There is no `about.get()` gate before showing "Connected". | `drive_client.py`, `ui_drive_start`, `ui_drive_complete`, `DRIVE_TOKEN` in `config.py` | Section 6, Rules 7/11 |
| D6 | No folder management, no quota UI. `_ensure_drive_folder()` silently hardcodes a folder named `TeleDrive_Transfers`. No browse, no create, no choose, no persisted folder ID chosen by the user, no quota refresh button, no 90% warning, no insufficient-space refusal. | `ui.py` | Section 4 Connection Center |
| D7 | Raw exceptions leak into the UI. Handlers return `f"{t('err.unknown')}: {e}"`. Tracebacks reach the browser. | every handler in `ui.py` | Rules 8, 16 |
| D8 | Analyze auto-enqueues everything. `ui_analyze` calls `QUEUE.bulk_enqueue(items)` immediately. There is no selection step, no filter apply, no scope control (message / group / bounded range). | `ui_analyze` in `ui.py` | Section 4 Analyze |
| D9 | Wrong concurrency control + wrong spec version. Settings is a Radio of `safe/balanced/fast`; constitution requires a slider 1–4, default 2. `config.py` still says `spec_version = "2.0"` and the notebook title says "TeleDrive v2". | `config.py`, `ui.py` | Rule 15, Section 3 |
| D10 | UI is nothing like the approved design. `gr.Blocks(theme=gr.themes.Soft())` with plain `gr.Tab`s. Missing: right-side nav rail, graphite dark theme, coordinated light theme, lime accent, slim top bar with Drive/Telegram chips + ZIP export + language + theme, engine badge reading real runtime values, and the whole Colab Code / Export section. | `ui.py` `build()` | Section 3 |

## 1.3 Missing files the constitution requires

Not present anywhere: `app_context.py`, `action_registry.py`, `ui_binder.py`,
`handlers.py`, `theme.py`, `redaction.py`, `errors.py`, `telegram_auth.py`,
`drive_auth.py`, `drive_folders.py`, `log_service.py`, `package_service.py`,
`colab_export.py`, `notebook_cells.py`, `teledrive_launcher.py`, `requirements.lock`,
`docs/CONSTITUTION.md`, `docs/AUDIT.md`, `docs/PHASE_REPORTS/`,
`.github/workflows/ci.yml`, and binding tests (`tests/test_bindings.py`,
`tests/test_telegram_auth.py`, `tests/test_drive_auth.py`, `tests/test_recovery.py`).

## 1.4 One more thing to fix quietly

`public/teledrive-package.zip` is a **static 51 KB zip committed into the frontend**. It
will be stale the moment you change any Python file. It must be generated by
`package_service.build_tested_archive()` from the live tree, never hand-committed. Remove
it from git and generate on demand.

---

## Phase 0 verification of 1.1 (performed 2026-07-29)

Every file listed in 1.1 was confirmed present on disk. The `tests/` "(+ others)" resolve
to: `__init__.py`, `test_filters.py`, `test_i18n.py`, `test_queue.py`, `test_resume.py`,
`test_retry.py`, `test_snapshot.py`, `test_state_machine.py`, `test_storage.py`,
`test_telegram_links.py`. `requirements.lock` and the three Phase 0 docs now exist; the
remaining items in 1.3 are still missing by design and are scheduled to their phases.
