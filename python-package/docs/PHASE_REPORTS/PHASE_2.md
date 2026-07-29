# PHASE 2: Action Contract audit and completion

Status: COMPLETE (in working tree; GitHub push/CI proof pending)

Claim being verified: ActionSpec/UIBinder/proof-gate satisfy Constitution 4A.1,
with no `ready=True` shortcut, no lambda handlers, no direct `.click()` in ui.py,
and a handler-to-service spy that reaches the real service object.

GitHub branch: edit/edt-e6ba1fa6-15aa-4f10-a51b-0c4a8b5de147
GitHub HEAD SHA (parent of this work): 53ede7ec09f96fa153342830b8a7a9817037e03c
Parent SHA: 53ede7ec09f96fa153342830b8a7a9817037e03c

REPORT MISMATCH: none. The audit commands returned exactly the claimed Phase 1
state — no `ready=True`, no runtime `QUEUE =` singleton (the three hits are
local test fixtures in tests/test_queue.py, tests/test_resume.py,
tests/test_transfer_manager.py), no `from ...queue_manager import QUEUE`,
`proof_test` enforced in action_registry.

## Files inspected
- teledrive/action_registry.py, teledrive/ui_binder.py, teledrive/ui.py,
  teledrive/handlers.py, teledrive/app_context.py, teledrive/errors.py
- tests/test_action_proofs.py, tests/test_bindings.py, tests/test_handlers_contract.py

## Files changed
- teledrive/app_context.py — removed the duplicate local `ServicePathError`
  (RuntimeError) and imported the canonical `errors.ServicePathError`.
  Two classes with the same name meant `except errors.ServicePathError`
  never caught resolution failures.
- tests/test_handlers_contract.py — added
  `test_handler_reaches_the_real_service_object`: for all 41 specs it patches
  the actual service method on the live context (not `Handlers.call`) and
  asserts exactly one hit.
- tests/test_bindings.py — added
  `test_wire_rejects_an_unresolvable_service_path`.

## Contract state
- ActionSpec fields: action_id, handler_name, service_path, label_key, section,
  implemented, tested, proof_test. No `ready=` constructor shortcut; `ready` is a
  read-only property.
- `tested=True` without `proof_test` -> ValueError in `__post_init__`.
- `tested=True` without `implemented=True` -> ValueError.
- UIBinder.validate rejects unknown action, not-ready action, missing/undecorated
  handler, and unresolvable service_path.
- assert_complete() fails on ready-but-unwired and on rendered-but-unwired orphans.
- Unready specs render hidden + non-interactive with `common.unavailable`.
- ui.py contains no `.click(` and no `lambda`.
- Ready count unchanged at 14/41 — no action was promoted to satisfy the UI.

## Real stdout
    python -m compileall -q teledrive      -> COMPILE_OK
    python -m pytest -q tests              -> 275 passed in 13.26s
    python teledrive_launcher.py --check   -> binding check ok: 14/41 ready actions resolve
    python -m teledrive.notebook_cells --check -> notebooks are in sync

## Not proven
- CI run on GitHub (needs push).
- Real Colab execution (Telegram / Drive / transfer).
