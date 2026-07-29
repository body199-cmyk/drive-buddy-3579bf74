# PHASE 3: Queue and Transfer

Status: COMPLETE (in working tree; GitHub push/CI proof pending)

Claim being verified: no QUEUE singleton anywhere in the runtime, one
ApplicationContext-owned QueueManager / TransferManager / Drive client, a
TransferManager that is reused instead of rebuilt on every Start, selection-only
starts, a real batch preflight, a draining worker loop, safe pause checkpoints,
and permanent Stopped.

GitHub branch: edit/edt-e6ba1fa6-15aa-4f10-a51b-0c4a8b5de147
GitHub HEAD SHA (parent of this work): 53ede7ec09f96fa153342830b8a7a9817037e03c
Parent SHA: 53ede7ec09f96fa153342830b8a7a9817037e03c

## Code audit (code, not reports)
    grep -rn "QUEUE" teledrive/*.py
    -> only handlers.py DEFAULT_QUEUE_ARITY / ERROR_ARITY (naming, not a singleton)
No module-level `QUEUE =`, no `from .queue_manager import QUEUE`, no runtime
import of a singleton. `_future`, `_status`, `ctx`, `_scope`, `_paused`,
`_stop`, `_paused_items`, `_stopped_items` are all instance attributes.

## Files changed
- teledrive/queue_manager.py — `apply_concurrency()` now clamps to
  1..HARD_CONCURRENCY_CAP before forwarding. It previously returned the raw
  value (10 -> 10), so the UI could report a concurrency the manager never used.
- tests/test_phase_3.py — new, 16 proofs.
- teledrive/action_registry.py — 8 controls promoted to tested=True, each with a
  real proof_test naming its action_id (see below).
- src/routes/index.tsx — the landing page claim moved from 14/41 to 22/41 to
  match `--check`.

## Actions promoted (action_id -> implemented,tested,proof_test)
- queue.resume            -> True,True, tests/test_phase_3.py::test_resume_clears_the_pause_gate_on_the_owned_manager
- queue.stop              -> True,True, tests/test_phase_3.py::test_stop_sets_the_manager_stop_flag_and_reports_stopped
- queue.pause_item        -> True,True, tests/test_phase_3.py::test_pause_item_marks_an_in_flight_item_paused
- queue.resume_item       -> True,True, tests/test_phase_3.py::test_pause_item_and_resume_item_only_touch_that_item
- queue.stop_item         -> True,True, tests/test_phase_3.py::test_stop_item_is_permanent_for_that_item
- queue.retry_item        -> True,True, tests/test_phase_3.py::test_retry_item_returns_a_failed_item_to_pending
- queue.clear_completed   -> True,True, tests/test_phase_3.py::test_clear_completed_removes_finished_rows_only
- queue.refresh           -> True,True, tests/test_phase_3.py::test_refresh_snapshot_reports_live_counts
No action was promoted without a service that really runs and a test that
really exercises it.

## Required proofs
- concurrency <= 4: test_worker_count_is_clamped_between_one_and_four,
  test_apply_concurrency_forwards_the_clamped_value_to_the_manager
- selection only: test_start_selected_never_processes_the_whole_table,
  test_transfer_manager_scope_excludes_unselected_items (Phase C)
- preflight: test_preflight_refuses_when_the_local_disk_reserve_is_not_met,
  test_preflight_reports_totals_for_the_selected_items_only,
  test_preflight_refuses_when_drive_is_not_connected
- late enqueue: test_run_drains_items_enqueued_after_the_run_started (Phase C)
- pause checkpoint: test_pause_exports_a_checkpoint_before_reporting_paused (Phase C)
- Stopped permanence: test_stop_item_is_permanent_for_that_item,
  test_stopped_item_is_skipped_by_the_drain_loop,
  test_retry_failed_never_revives_a_stopped_item (Phase C)
- one manager: test_context_reuses_the_same_transfer_manager_across_starts,
  test_transfer_manager_state_is_instance_scoped

## Real stdout
    python -m compileall -q teledrive           -> COMPILE_OK
    python -m pytest -q tests                   -> 299 passed in 11.01s
    python teledrive_launcher.py --check        -> binding check ok: 22/41 ready actions resolve
    python -m teledrive.notebook_cells --check  -> notebooks are in sync

## Not proven
- CI run on GitHub (needs push).
- Real Colab execution with live Telegram / Drive credentials.
