# PHASE M44-T01 — auto-refresh switch + Telegram download throughput

**Date:** 2026-10-19
**Owner request (verbatim intent):** the one-second UI refresh during a transfer is annoying; add an option in settings to turn it off/on. Also investigate why transfers are very slow even with parallel transfers, probably Telegram limits, and use the available Colab/Google capacity.
**Scope:** one persisted preference + one download path change. No database migration, no Drive/Telegram schema change, no notebook cell change, no workflow change.

## 1. Diagnosis (evidence, not guesses)

| Finding | Evidence | Effect |
|---|---|---|
| Fresh Telegram downloads used 128 KiB requests for files ≤ 100 MB | Telethon 1.44 `_download_file()` → `utils.get_appropriated_part_size(file_size)` returns `128` below 100 MB, `256` below 750 MB, `512` only above that. `download_media()` has no public `part_size_kb` argument. | Each `upload.getFile` round trip carries only 128 KiB. With a Colab↔DC round trip in the tens of milliseconds, throughput is bounded by latency, not bandwidth. This is the largest removable ceiling. |
| Resumed downloads were already faster than fresh ones | `TelegramService.download_partial()` already used `iter_download` (default `request_size = 512 KiB`). | Inconsistent throughput: a pause/resume could be ~4× faster per request than the initial attempt. |
| Telethon decrypts every chunk in pure Python unless a C backend is importable | `telethon/crypto/aes.py` chooses `cryptg` → system `libssl` → `pyaes`. The pinned lock had neither `cryptg` nor a guaranteed libssl symbol path. | On a Colab VM without the deprecated `AES_ige_encrypt` symbol, every 128 KiB chunk pays Python AES cost, competing with other workers under the GIL. |
| Drive calls are serialized by one process-wide lock | `TransferManager._drive_call()` runs every Drive/googleapiclient call inside `self._drive_lock` because a Drive service object is not thread-safe. | `concurrency > 1` parallelizes Telegram downloads, but **not** Drive uploads. This is a real structural limit of the current one-Drive-service rule (Constitution §2/§5). Fixing it needs an ADR, not a local patch. |
| Per-file API overhead exists | Each item does `find_by_source_key` (Drive `files.list`), `preflight_or_raise` (`about.get`) and a durable checkpoint upload. | Dominant for many small files; secondary for large media. Not changed in this task. |

## 2. Changes

### 2.1 Persisted auto-refresh preference (owner request)
- New `SettingsService.auto_refresh_ms()` / `set_auto_refresh()` backed by SQLite setting `auto_refresh_ms`.
- Allowed values: `0` (off), `1000`, `2000`, `5000`; default `1000` preserves existing behaviour. Invalid values are rejected with a localized error, never clamped silently.
- `LiveUiStateService.snapshot()` exposes `autoRefreshMs` to React.
- New real action `settings.set_auto_refresh` (registry + named handler + service path + proof test), wired in both transports:
  - React settings page: selector + “Save in Python”, with a draft that a heartbeat snapshot cannot revert.
  - Gradio settings drawer: `gr.Radio` wired on `change`.
- React heartbeat: `setInterval(..., autoRefreshMs)` and returns early when `autoRefreshMs <= 0`. Manual `queue.refresh` remains. The one-shot post-action verification refresh still runs (it is not a loop).
- No browser storage: the value lives in the same backend SQLite settings store as concurrency/theme.

### 2.2 Telegram download throughput
- New `TelegramService.download_media_fast()` requests the MTProto maximum (`512 KiB`) through the public `iter_download` API, writing a sequential `.part` prefix so pause/stop/resume semantics are unchanged.
- `TransferManager._download()` prefers it for fresh non-photo media ≥ 1 MiB. On any non-control exception it writes a `RECOVERY` event and falls back to the legacy `download_media()` path, which rewrites the file from byte zero (no append/corruption). `TransferControlSignal` (pause/stop) is always re-raised.
- `download_partial()` now states the 512 KiB request size and total size explicitly.
- `cryptg==0.6.0` added to `requirements.lock`/`requirements.txt` (Telethon's own optional C AES-IGE backend; cp310–cp314 manylinux x86_64 wheels published). `crypto_backend()` logs which implementation is active on Telegram connect.

## 3. Gates (local, 2026-10-19)

| Gate | Result |
|---|---|
| `compileall` | PASS |
| `pytest -q tests` | `795 passed` |
| `teledrive_launcher.py --check` | `54/54 ready actions resolve` |
| `notebook_cells --check` + `cmp` internal/public | PASS, byte-identical |
| React contracts (`node --test`) | `34/34` |
| `bun run lint` | 0 errors, 8 pre-existing warnings |
| React panel bundle rebuild | `panel.bundle.gz` + `panel.css.gz` regenerated from source |
| `package_service --build` | PASS (`578225` bytes, `e4723b02…15f6`) |
| `bun run build` | Not runnable in this sandbox: the registry mirror refused `@lovable.dev/vite-tanstack-config@2.8.5`; `tsc --noEmit` reports only that missing module. CI installs it from `bun.lock`. |

## 4. What is NOT proven
- No live Colab, Telegram or Drive call was made in this session. Actual throughput improvement must be measured on the owner's Colab (see the runbook below).
- Parallel Drive uploads remain serialized by `_drive_lock`; changing that requires an ADR because the Constitution mandates one Drive service per context.
- Multi-stream (segmented) Telegram downloads were deliberately **not** implemented in this task: they add sparse-file/resume complexity and need live Telegram testing. The 512 KiB path is the low-risk first step.
- Per-file dedupe/quota/checkpoint API calls were not changed.

## 5. Live measurement runbook (owner)
1. Publish a package containing this commit, Restart the Colab runtime, run Cell 1 (installs `cryptg`), then Cells 2–4.
2. In **Logs**, look for `telethon crypto backend=cryptg`.
3. Transfer one file ≥ 100 MB and compare `dash.speed`/`dash.avg_speed` and wall time against the previous package.
4. In **Settings**, set auto-refresh to **Off**, start a transfer, and confirm the progress view no longer repaints every second; press the manual **Refresh** button and confirm the snapshot updates.
5. If download is still latency-bound, the next planned step is 2–4 parallel `iter_download` streams per file (owner-approved, with live tests) and an ADR for a bounded Drive upload service pool.

## 6. Rollback
Revert this commit. No migration runs; the stored `auto_refresh_ms` row is harmless and ignored by older code. Removing `cryptg` from the lock restores the previous AES backend selection automatically; the fast download path disappears with the code revert.
