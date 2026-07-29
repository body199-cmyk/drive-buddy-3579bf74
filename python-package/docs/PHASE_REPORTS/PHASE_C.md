# PHASE C — Single context, real queue, no singletons

Status: **complete (code-level). Live Colab integrations still unverified.**

## What Phase C required

1. One `ApplicationContext` owns one `QueueManager`, one Drive client and one
   `TransferManager`. No module-level singletons.
2. `Start` runs a **batch preflight** (Telegram, Drive, folder, quota, local
   disk reserve) before any worker starts, and processes **only the selected
   items** — never the whole table.
3. `run()` is a **drain loop**: work enqueued after the run started is picked
   up, instead of a one-shot snapshot of `pending()`.
4. `Pause` exports a safe checkpoint **before** the queue reports `paused`.
5. `Stopped` is **terminal**. `Retry failed` never resurrects a stopped item.

## What changed

| File | Change |
|---|---|
| `teledrive/queue_manager.py` | `QUEUE` singleton deleted; all state on the instance. Added `bind_context`, `batch_preflight`, `selected_pending`, scope-aware `start_selected`, checkpoint-on-`pause`, `Stopped`-safe `retry_failed`. |
| `teledrive/app_context.py` | `QueueManager(self)` bound at construction; added `ensure_drive_client()` and `ensure_transfer_manager()` — the one factory for the run. |
| `teledrive/transfer_manager.py` | Queue is **injected** (`queue=`). Added `set_scope`/`in_scope` and the drain loop in `run()`. |
| `teledrive/checkpoint_manager.py` | `reconcile_with_drive(drive, queue)` takes the queue; no singleton import. |
| `teledrive/state_machine.py` | `Stopped -> {Deleted}` only. |
| `teledrive/redaction.py` | Session pattern narrowed to URL-safe base64 so filesystem paths stop false-positiving durable checkpoints. |
| `tests/test_phase_c.py` | 14 new proofs (see below). |

## Proofs

`tests/test_phase_c.py` proves: no `QUEUE` attribute and no `QUEUE =` anywhere
in the package; two managers do not share state; the context reuses one
transfer manager bound to its own queue; preflight raises without Telegram or
Drive; an unbound manager raises instead of guessing; selection never widens to
the whole table; scope excludes unselected items end-to-end; the drain loop
picks up a late enqueue; `Stopped` is terminal; `retry_failed` skips stopped
items; and `pause` writes a checkpoint before reporting `paused`.

## Gates

```
python -m compileall -q teledrive     -> 0
python -m pytest -q tests             -> 225 passed
python teledrive_launcher.py --check  -> binding check ok: 14/41 ready actions resolve
bun run lint                          -> 0 errors
bun run build                         -> ok
```

`queue.start_selected`, `queue.pause` and `queue.retry_failed` moved to
`tested=True` with a named `proof_test`; `queue.resume`, `queue.stop` and the
per-item controls stay `tested=False` and remain hidden in the UI.

## Not claimed

A real Colab run against live Telegram and Google Drive credentials has still
not been executed here. Phase C is a code-level completion.
