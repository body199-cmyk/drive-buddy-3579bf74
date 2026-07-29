# PHASE 9 — Colab readiness repair (audit follow-up)

Audit source: drive-buddy-3579bf74 @ 2c9f33be13aae6be3f4c8ff60918d82c9a53d09a

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

3. **CI missing lint.** `.github/workflows/ci.yml` now runs `bun run lint`
   before `bun run build`. Local run: 0 errors, 6 pre-existing
   `react-refresh/only-export-components` warnings in `src/components/ui/*`.

4. **Real Colab execution.** STILL NOT VERIFIED — see below.

## Command output

- `python -m pytest -q tests` → `177 passed`
- `python teledrive_launcher.py --check` → binding check ok
- `python -m teledrive.notebook_cells --check` → notebooks are in sync
- `bun run lint` → 0 errors / 6 warnings
- `bun run build` → ok

## Not verified (do not claim otherwise)

- Real Telegram login (API ID/hash, code, 2FA): NOT verified.
- Real native Colab Drive authorization and an actual upload/transfer: NOT verified.
- Gradio 6.20.0 behaviour of `prevent_thread_lock`: NOT verified against a real
  install (gradio is not installed in this sandbox); the flag is passed through
  and asserted only against a fake demo object.

A real Colab smoke test cannot be run from this environment: it requires an
interactive Colab runtime, a Google account consent screen and live Telegram
credentials. The operator must run it and record the result here.

## Next smallest step

Operator-run Colab smoke test: cells 1→7 in one runtime, confirming cells 5–7
execute while the UI from cell 4 is still serving, then paste the redacted
outputs into this report.
