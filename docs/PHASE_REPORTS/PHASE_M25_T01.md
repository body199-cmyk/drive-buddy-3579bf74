# PHASE M25-T01 — queue sessions + start all pending + clear incomplete

```plain
TASK ID: M25-T01
UTC: 2026-08-12
Base SHA: 0c394a859770844a0526d54f4369923d05385138
Branch: arena/019ff846-drive-buddy-3579bf74
Status: Code-complete candidate + Fake-tested; NOT Colab-ready; NOT Complete
```

## Problem

After a Colab Restart, SQLite still holds leftover queue rows (owner report: 191 pending, 8 uploaded) while the in-memory analyze selection is empty. `queue.start_selected` resolved that empty selection to "start nothing". Pause keeps rows on purpose. Stop stopped workers only.

## Changes

### Start

`QueueManager.selected_pending`:

- explicit id list → hard filter (Phase C: never the whole table)
- explicit `[]` → start nothing (`test_empty_selection_starts_nothing`)
- `None` (Start button) → in-memory selection if it matches queue rows, else every startable Pending/NeedsRetry/Downloaded row

This is an explicit Start click after Restart, not auto-resume (Constitution §15).

### Clear incomplete

New ready action `queue.clear_incomplete` → `clear_incomplete_metadata()`.

Deletes unfinished SQLite rows only (`Pending`/`Failed`/`Paused`/`Stopped`/in-flight…). `Uploaded`/`Skipped` stay for `clear_completed`. `delete_item` never touches Drive.

### Stop choice

- React: Stop opens a confirm — stop only, or stop then `queue.clear_incomplete`.
- Gradio: Stop stays stop-only; new visible button «مسح غير المكتمل».

### Session grouping

`LiveUiState` queue rows now include `chatTitle` and `createdAt`. React `groupQueueSessions` groups by channel title + created date (`YYYY-MM-DD`).

## Proofs

- `tests/test_phase_c.py::test_start_without_ids_falls_back_to_all_pending_after_empty_selection`
- `tests/test_phase_3.py::test_clear_incomplete_removes_unfinished_rows_only`
- Frontend contracts 21 (grouping) and 22 (stop confirm + action id)

## Local gates

```plain
python -m compileall -q teledrive                         PASS
python -m pytest -q tests                                 652 passed
python teledrive_launcher.py --check                      48/48 ready
python -m teledrive.notebook_cells --check                in sync
cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb    IDENTICAL
node --test tests/teledrive-sandbox.contract.test.mjs     22/22
npx tsc --noEmit                                          PASS
npx eslint (teleDrive + contracts)                        0 errors
bundle TeleDriveGradioPanel.mount                         verified
```

## Protected

Untouched: notebooks, `notebook_cells.py`, `colab_cells.json`, `telegram_auth.py`, `transfer_manager.py`, `database.py`, `migrations.py`, `requirements.*`, `bun.lock`, `package.json`, workflows.

`queue_manager.py` changed on explicit owner instruction.

## Honest status

Not Colab-ready. Not Complete. Live Start of leftover pending rows and the Stop dialog must be checked by the owner after republish.
