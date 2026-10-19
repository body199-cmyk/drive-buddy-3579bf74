# PHASE M45-T02 — Per-chunk Drive lock for duplicate precheck and SQLite readonly recovery

**Date (UTC):** 2026-10-19  
**Task:** `M45-T02`  
**Base:** `d991cf4783545ee838d3c2eeaf3b98fc0c22cf6f` (`main` after M45-T01 PR #100)  

## 1. Trigger & Live Evidence (`teledrive_checkpoint_2026-10-19T15-58-01+00-00.json`)

After `M45-T01` was merged and published (`d991cf478354`), the owner's live Colab run transferred three large video lectures (`Portal HTN.mp4` 1.40 GB, `Intro + LCF.mp4` 671 MB, `Miscellaneous.mp4` 1.34 GB = 3.41 GB total) without a single `Request was unsuccessful 6 time(s)` or `LimitInvalidError`. Two residual issues were exposed:

1. **Duplicate files downloaded while an upload is active:** `upload_resumable()` held `_drive_gate` and `_drive_lock` for the entire multi-minute file upload, causing `_duplicate_precheck()` to return `None` whenever an upload was in flight and forcing duplicate files to be downloaded from Telegram before being detected in `_run_upload()`.
2. **Stale readonly SQLite handle (`Hematology.mp4`, `msg=288`):** `last_error_msg: "attempt to write a readonly database"` (`last_error_code: "UNKNOWN"`). Once SQLite flagged the module-level `_conn` singleton as readonly, `_connect()` returned the same stale handle forever.

## 2. Implemented Fixes

1. **`python-package/teledrive/database.py`:**
   - Added `_ensure_writable_db_paths()`, `timeout=30.0`, `PRAGMA busy_timeout=30000`, `_reconnect()`, and `_RecoveringCursor` so any transient `readonly`, `locked`, or `disk i/o` `sqlite3.OperationalError` closes the stale connection, restores write permissions on the local runtime DB files, re-opens `_conn`, and retries the statement once.
2. **`python-package/teledrive/error_handler.py`:**
   - Added `"readonly database"`, `"database is locked"`, and `"disk i/o error"` to `TRANSIENT_MARKERS`.
3. **`python-package/teledrive/drive_client.py` & `python-package/teledrive/transfer_manager.py`:**
   - Added optional `chunk_lock` to `DriveService.upload_resumable()` so `self._drive_lock` is acquired per `8 MiB` chunk (`files().create()` and each `request.next_chunk()`) rather than held continuously across the entire file.
   - Updated `TransferManager._duplicate_precheck()` to run `dup_check()` under `self._drive_lock` between upload chunks, guaranteeing `Pending -> Skipped` without downloading duplicate files from Telegram.
4. **`python-package/tests/test_fast_download.py`:**
   - Added `test_duplicate_precheck_succeeds_during_active_upload_and_skips_download` and `test_database_recovers_from_readonly_sqlite_connection`.
