# PHASE M45-T04 — FastTelethon Direct-DC MTProtoSender Pool (12 Sockets) + 2-Request Per-Socket Pipelining

**Date (UTC):** 2026-10-19  
**Task:** `M45-T04`  
**Base:** `e177dec8503ab37ca3156c5035e918babf4e2265` (`main` after M45-T03)  

## 1. Deep Root Cause Analysis: Why `iter_download` and Secondary `TelegramClient` Remained Slow

1. **Why `self.client.iter_download()` is capped at ~1.5 MB/s regardless of `streams`:**
   - Inside Telethon (`telethon/client/downloads.py`), `_DirectDownloadIter` uses `self.client._sender` (when `dc_id == session.dc_id`) or `self.client._borrow_exported_sender(dc_id)` (when `dc_id != session.dc_id`).
   - Because `self.client._borrowed_senders` caches **one** `MTProtoSender` per `dc_id`, all parallel `iter_download` streams on `self.client` multiplex over a **single TCP socket**, which Telegram's Data Center rate-limits to ~1–1.5 MB/s.
2. **Why `M45-T03`'s `MemorySession` `TelegramClient` fell back on cross-DC channels:**
   - Many channels host media on a different DC (e.g. DC 4 while the user's account is on DC 2). A `MemorySession` populated only with the home DC's `auth_key` has neither `InitConnectionRequest` state nor exported cross-DC authorization, causing `worker.iter_download()` to fail on chunk 0 and fall back to `self.client`.
3. **Why Colab continued running old code (`2d5893dea014`) when Cell 1 was re-run without restarting the runtime:**
   - `_pkg_runtime_refusal_reason()` refuses to update when `teledrive` is already in `sys.modules`, and `resolve_package_zip()` prefers the cached local `/content/teledrive_v4.5.zip` over `/content/drive/MyDrive/TeleDrive/teledrive_v4.5.zip`.

## 2. Implemented Solution (`M45-T04`)

1. **Direct-DC `MTProtoSender` Pool (`_open_fast_senders` in `telegram_client.py`):**
   - Extracts `(dc_id, location)` via `telethon.utils.get_input_location(media)`.
   - Connects up to **`12` independent `MTProtoSender` TCP sockets** (`PARALLEL_DOWNLOAD_STREAMS = 12`, configurable up to `16`) directly to `dc = await self.client._get_dc(dc_id)`.
   - On the home DC (`dc_id == session.dc_id`), reuses `self.client.session.auth_key` immediately across all 12 sockets (zero DH handshake overhead).
   - On a foreign DC (`dc_id != session.dc_id`), exports and imports authorization once (`ExportAuthorizationRequest` + `ImportAuthorizationRequest` via `InvokeWithLayerRequest`), caches `self._dc_auth_keys[dc_id]`, and connects all remaining `MTProtoSender` sockets in parallel with `asyncio.gather`.
2. **2-Request Per-Socket Lookahead Pipelining (`_stream_from_sender`):**
   - Each of the 12 `MTProtoSender` lanes keeps `2` `GetFileRequest` RPCs in flight simultaneously (`TG_INFLIGHT_REQUESTS = 24`), eliminating network RTT idle gaps between consecutive 512 KiB chunks.
3. **72-Chunk (`36 MiB`) Non-Blocking Sliding Reorder Window (`config.py`):**
   - `PARALLEL_DOWNLOAD_WINDOW_CHUNKS = max(PARALLEL_DOWNLOAD_STREAMS * 6, 64)` (`72` chunks) and `PARALLEL_DOWNLOAD_MIN_BYTES = 2 MiB`.
4. **3-Tier Fail-Safe Fallback:**
   - If any `MTProtoSender` fails mid-stream after `done_chunks`, that lane seamlessly resumes its remaining stripes (`count - done_chunks`) via `iter_download` from `start + done_chunks * stride`.
