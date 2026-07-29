# Architecture

## Layers
1. **UI** (`ui.py`, `app.py`): Gradio components + i18n. Zero transfer logic.
2. **Services**: `telegram_client`, `media_scanner`, `drive_client`, `drive_quota`, `duplicate_detector`, `storage_manager`, `auth_manager`.
3. **Domain**: `models`, `state_machine`, `retry_policy`, `error_handler`.
4. **Persistence**: `database`, `migrations`, `checkpoint_manager`.
5. **Orchestration**: `queue_manager`, `transfer_manager`, `progress_tracker`.
6. **Meta**: `snapshot`, `handoff`, `logging_config`, `config`, `utils`, `i18n`.

## Transfer flow
```
parse link -> scan messages -> apply filters -> duplicate check
  -> drive quota preflight -> disk preflight
  -> enqueue (SQLite Pending)
  -> transfer worker (Semaphore-bounded)
      -> Downloading -> temp/<item_id>/<safe_name>.part
      -> verify size
      -> Uploading -> Drive resumable upload
      -> verify id + size + appProperties
      -> Uploaded -> checkpoint (SQLite atomic write -> Drive)
      -> cleanup temp
```

## Crash recovery
1. Bootstrap.
2. `restore_from_drive()` → newest checkpoint imported.
3. `reconcile_with_drive()` → items stuck in Downloading/Uploading either mark Uploaded (found + size matches) or NeedsRetry.
4. Orphan `temp/` dirs are quarantined.
5. UI shows the recovery summary.

Invariant: a restart NEVER assumes an in-flight transfer finished. Always reconcile.

## State machine
See `state_machine.LEGAL`.

## Data model
See `models.MediaItem` and `migrations.SCHEMA`.

## Error taxonomy
`error_handler.classify()` returns `{code, category, user_message_key, is_transient, retryable, suggested_action}`.

- **Transient**: network timeouts, resets, 429/500/502/503, FloodWait.
- **Permanent**: invalid link, no access, no media, storage full, oversized.
- **Reauth**: expired session / revoked token.
