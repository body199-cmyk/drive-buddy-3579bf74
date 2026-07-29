# PHASE B — Durability and post-upload verification

Contract: a temp file may be deleted **only after** Drive proved the upload and a
durable checkpoint reached Drive.

## Transfer sequence (enforced in `transfer_manager.py`)

```text
Downloading -> Uploading -> Verifying -> UploadedPendingCheckpoint -> Uploaded -> cleanup_item()
```

| Failure point | Resulting state | Temp file | Event |
|---|---|---|---|
| verification (id/size/parent/appProperties/trashed) | `Failed` (`VERIFY_FAILED`) | kept | `RECOVERY` |
| durable checkpoint upload | `UploadedPendingCheckpoint` | kept | `RECOVERY` |
| checkpoint snapshot contains a secret shape | `CheckpointError`, no cleanup | kept | `RECOVERY` |

## What changed

- `models.py` / `state_machine.py` — added `Verifying` and `UploadedPendingCheckpoint`
  with explicit legal transitions.
- `drive_client.py` — `verify_metadata()` / `verify_uploaded()`; uploads tag both
  `source_key` and `teledrive_source_key` in `appProperties`.
- `checkpoint_manager.py` — `persist_durable()` raises `CheckpointError` instead of
  returning `None`, and refuses to export a snapshot that matches a secret pattern.
  `reconcile_with_drive()` now routes every state change through `QUEUE`.
- `redaction.py` — `scan_for_secrets()` / `assert_no_secrets()`.
- `storage_manager.py` — temp root and quarantine are resolved from live config
  (`temp_root()`, `quarantine_dir()`), so no stale path can be wiped.
- No module outside the queue assigns `.state` — enforced by a test.

## Gates (real output)

```text
python -m compileall -q teledrive        -> 0
python -m pytest -q tests                -> 208 passed in 4.33s
python teledrive_launcher.py --check     -> binding check ok: 11/41 ready actions resolve
bun run lint                             -> 0 errors, 6 warnings (pre-existing)
```

## New proof tests — `tests/test_transfer_manager.py`

- success path deletes temp only after a checkpoint exists on Drive
- state order never reaches `Uploaded` before the checkpoint
- checkpoint failure keeps temp and leaves `UploadedPendingCheckpoint`
- `persist_durable` raises on failure and on a secret-bearing snapshot
- size mismatch / wrong parent / missing appProperties / trashed file all fail verification
- crash-and-restart and interrupted download never produce a duplicate upload

## Still unverified

Live Colab run with real Telegram + Drive credentials (operator step).
