# PHASE 9 — Colab readiness repair (final audit follow-up)

Audit source: drive-buddy-3579bf74 @ 2c9f33be13aae6be3f4c8ff60918d82c9a53d09a
Destination repo commit at time of verification: `7b1825d0676aabc6ee0597825cdbc5026f5e3737`

## Blockers addressed

1. **Cell 4 blocked cells 5–7.** `app.launch()` now takes `blocking` (default
   `False`) and calls Gradio with `prevent_thread_lock=not blocking`. The launch
   handle is stored on `ctx.ui` and closed by `ApplicationContext.shutdown()`,
   so cell 7 tears the UI down cleanly. The CLI launcher passes `blocking=True`
   because nothing runs after it and the process must stay alive.
   Guards: `tests/test_launcher.py::test_launch_defaults_to_non_blocking_and_stores_the_handle`,
   `::test_cli_launcher_blocks_so_the_process_stays_alive`,
   `tests/test_notebook.py::test_cell_4_is_non_blocking_so_cells_5_to_7_stay_runnable`.

2. **Dependency version drift.** `requirements.lock` is the single dependency
   source. Cell 1 installs from it and prints its path; no cell (and therefore
   no `colab_cells.json` entry, since that file is generated from the same
   `notebook_cells.CELLS`) may contain a `package==version` literal.
   Guards: `test_requirements_lock_is_the_only_dependency_source`,
   `test_colab_cells_json_carries_no_dependency_versions`.

3. **CI gates.** `.github/workflows/ci.yml` runs, with no `continue-on-error`:
   `python -m compileall teledrive`, `python -m pytest -q tests`,
   `python teledrive_launcher.py --check`,
   `python -m teledrive.notebook_cells --check`,
   `cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb`,
   `python -m teledrive.package_service --build`, then
   `bun install --frozen-lockfile`, `bun run lint`, `bun run build`.

4. **Real Colab execution.** STILL NOT VERIFIED — see below.

## Command output (run from `python-package/`, this repo, this commit)

```text
$ python -m compileall teledrive
exit 0

$ python -m pytest -q tests
........................................................................ [ 40%]
........................................................................ [ 81%]
.................................                                        [100%]
177 passed in 1.96s

$ python teledrive_launcher.py --check
bootstrap: {'schema_version': 1, 'dirs': ['/content/teledrive_runtime/data',
 '/content/teledrive_runtime/logs', '/content/teledrive_runtime/temp',
 '/content/teledrive_runtime/checkpoints', '/content/teledrive_runtime/session'],
 'free_bytes': 9223372036414439424}
binding check ok: 41/41 ready actions resolve

$ python -m teledrive.notebook_cells --check
notebooks are in sync

$ cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb
(no output — identical)

$ bun run lint
✖ 6 problems (0 errors, 6 warnings)
# all 6 are pre-existing react-refresh/only-export-components warnings in
# src/components/ui/* (badge, button, form, navigation-menu, sidebar, toggle).
# No new warnings introduced.

$ bun run build
[nitro] ✔ You can deploy this build using npx nitro deploy --prebuilt
exit 0
```

## File tree (python-package/)

```text
python-package/
├── requirements.lock          # sole dependency source
├── requirements.txt
├── teledrive_launcher.py
├── notebook/TeleDrive.ipynb   # byte-identical to ../public/TeleDrive.ipynb
├── docs/{ARCHITECTURE,AUDIT,CONSTITUTION,RUNBOOK,TROUBLESHOOTING}.md
├── docs/PHASE_REPORTS/{PHASE_0,PHASE_1,PHASE_2_TO_8,PHASE_9}.md
├── teledrive/  (44 modules: app, app_context, action_registry, async_runtime,
│                auth_manager, bootstrap, checkpoint_manager, colab_cells.json,
│                config, database, drive_auth, drive_client, drive_folders,
│                drive_quota, duplicate_detector, error_handler, errors,
│                filters, handlers, handoff, i18n, locale/, logging_config,
│                media_scanner, migrations, models, notebook_cells,
│                package_service, progress_tracker, queue_manager, redaction,
│                retry_policy, services, snapshot, state_machine,
│                storage_manager, telegram_auth, telegram_client,
│                telegram_links, transfer_manager, ui, ui_binder, utils)
└── tests/  (conftest, mocks/, test_app_context, test_bindings, test_concurrency,
             test_config, test_drive_quota, test_duplicate_detector,
             test_error_messages, test_filters, test_handlers_contract, test_i18n,
             test_launcher, test_no_ad_hoc_loops, test_notebook, test_queue,
             test_resume, test_retry, test_snapshot, test_state_machine,
             test_storage, test_storage_cleanup, test_telegram_auth,
             test_telegram_links)
```

## Not verified (do not claim otherwise)

- Real Telegram login (API ID/hash, code, 2FA): NOT verified.
- Real native Colab Drive authorization, folder browse, and an actual
  one-file transfer with Drive file ID / appProperties / size checks: NOT verified.
- Gradio 6.20.0 behaviour of `prevent_thread_lock`: NOT verified against a real
  install (gradio is not installed in this sandbox); the flag is passed through
  and asserted only against a fake demo object.

A real Colab smoke test cannot be run from this environment: it requires an
interactive Colab runtime, a Google account consent screen and live Telegram
credentials. The operator must run it and record the result here.

## Final status

**Code-complete candidate — real integrations unverified.** All fake tests and
CI gates pass. "Colab-ready" may only be claimed after the controlled Colab
test below passes.

## Next smallest step

Operator-run Colab smoke test: cells 1→7 in one runtime, confirming cells 5–7
execute while the UI from cell 4 is still serving, plus native Drive
`about().get()`, Telegram authorized state, one-file transfer, SQLite `Uploaded`
state, durable checkpoint, redacted logs and quarantine of unknown temp files.
Paste the redacted outputs into this report. Never paste credentials, phone
numbers, codes, session strings, tokens or raw tracebacks.
