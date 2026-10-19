# PHASE M45-T03 — Multi-Connection MTProto Media Pool, 36-Chunk Sliding Window, and Drive Checkpoint Pruning

**Date (UTC):** 2026-10-19  
**Task:** `M45-T03`  
**Base:** `f272e87823fd1249be6bd115e0892a3edb82daba` (`main` after M45-T02)  

## 1. Root Cause of Residual Telegram Download Slowness

Even after M45-T01 and M45-T02 decoupled the download/upload pipeline and aligned 512 KiB resume offsets, two bottlenecks still capped single-file Telegram download throughput on Colab:

1. **Barrier Stall in the Reorder Window (`PARALLEL_DOWNLOAD_WINDOW_CHUNKS == PARALLEL_DOWNLOAD_STREAMS == 4`):**
   - In `_download_media_parallel()`, `window = asyncio.Semaphore(PARALLEL_DOWNLOAD_WINDOW_CHUNKS)` had only 4 permits for 4 streams, and `window.release()` was only called inside `while next_offset in pending:` after chunk 0 was written to disk.
   - As a result, Lanes 1, 2, and 3 could never start their second 512 KiB chunk until Lane 0 finished its first chunk — turning 4 parallel streams into a lock-step barrier every 2 MiB!
2. **Single MTProto TCP Socket (`self.client`):**
   - All striped range readers called `self.client.iter_download()`, multiplexing all `upload.getFile` requests over a single TCP socket and single `MTProtoSender` lock.
3. **High Parallel Threshold (`32 MiB`):**
   - `PARALLEL_DOWNLOAD_MIN_BYTES = 32 MiB` forced all files between `1 MiB` and `32 MiB` onto a single sequential reader.

## 2. Implemented Changes (`M45-T03`)

1. **`python-package/teledrive/config.py`:**
   - Lowered `PARALLEL_DOWNLOAD_MIN_BYTES` from `32 MiB` to `4 MiB` (`4 * 1024 * 1024`).
   - Raised default `PARALLEL_DOWNLOAD_STREAMS` from `4` to `6` (bounded `1..8`) and `TG_INFLIGHT_REQUESTS` from `8` to `16` (bounded `1..24`).
   - Raised `PARALLEL_DOWNLOAD_WINDOW_CHUNKS` to `max(PARALLEL_DOWNLOAD_STREAMS * 6, 24)` (`36` chunks = `18 MiB` sliding window) so fast lanes never stall waiting for a slower lane.
2. **`python-package/teledrive/telegram_client.py`:**
   - Added `_get_lane_client(lane)` and `_close_media_pool()`: Lane 0 uses `self.client`, while Lanes `1..N-1` lazily connect independent in-memory `MemorySession`-backed `TelegramClient` instances (`receive_updates=False`, sharing `(dc_id, server_address, port, auth_key)` from `self.client.session` without touching the SQLite session file on disk).
   - Added automatic mid-stream fallback in `produce()`: if any secondary media client raises an error (or if `self.client` is a test double without `session.auth_key`), that lane seamlessly continues its remaining stripes on `self.client`.
   - Released `window.release()` immediately after writing contiguous bytes to the `4 MiB`-buffered file handle before invoking `progress_cb`.
3. **`python-package/teledrive/checkpoint_manager.py`:**
   - Added best-effort pruning of stale Drive checkpoints (`> 15`) during `restore_from_drive()` so `TeleDrive_AppData` does not accumulate hundreds of old JSON snapshots.
4. **`python-package/tests/test_fast_download.py`:**
   - Added `test_parallel_download_uses_independent_media_clients_and_falls_back_cleanly`.
