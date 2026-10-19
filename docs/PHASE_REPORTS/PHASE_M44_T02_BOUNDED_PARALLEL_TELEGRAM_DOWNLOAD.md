# PHASE M44-T02 — Bounded parallel Telegram downloads for large files

**Date (UTC):** 2026-10-19  
**Task:** `M44-T02`  
**Base:** `db0f2a02502b94d2975fa23d7bce5d6af9b24e52`  
**Branch:** `arena/360d78bc-drive-buddy-3579bf74`  
**PR/merge:** [#95](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/95), merged as `a032caf3be5f0b55b8b85af64dc134de2fb6a006`  
**CI:** [#39271630415](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39271630415) SUCCESS

## Trigger and measured report

The owner shared a Colab screenshot showing one `1.3 GB` Telegram media file at `41%` after about ten minutes. That implies an approximate rate of `0.9 MB/s` if the displayed size and elapsed time are accurate; it is an owner-reported estimate, not an independently captured benchmark. The M44-T01 path already requests MTProto's 512 KiB maximum, but it does so sequentially per file. Queue concurrency applies to separate items and does not split a single file into ranges.

GitHub release state was verified before the code change: `pkg-2026.08.09-m15t07` contained the 580737-byte archive and 378-byte manifest, target `db0f2a0`; workflow run [#39263636789](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39263636789) concluded SUCCESS, including the public verification job. Thus the speed report is downstream of the corrected M44-T01 package, not the former empty-release condition.

## Implementation

- `TelegramService.download_media_fast()` keeps the 512 KiB request size and preserves sequential transfer for files smaller than 32 MiB.
- For known files at least 32 MiB, it opens two offset/stride MTProto range iterators. Each stripe covers disjoint chunks; a shared per-client semaphore caps in-flight media requests at two in total, even if queue concurrency is higher.
- A bounded four-chunk reorder window writes only a contiguous prefix to the existing `.part` path. Pause/Stop callback exceptions cancel both readers and leave the valid prefix. Any range/transport/length mismatch propagates to the existing `TransferManager` fallback, whose legacy download opens the file from byte zero. It does not append potentially corrupt or sparse content.
- No new dependencies; no changes to the notebook, GitHub workflows, Telegram auth, Drive upload, SQLite schema, or session vault.

## Local proof

All commands ran in `python-package` with pinned `requirements.lock` installed in an isolated `/tmp/teledrive-venv`:

```text
python -m compileall -q teledrive                         PASS
python -m pytest -q tests                                 798 passed
python teledrive_launcher.py --check                      54/54 ready actions resolve
python -m teledrive.notebook_cells --check                notebooks are in sync
cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb    PASS
python -m teledrive.package_service --build --output /tmp/teledrive-m44-t02.zip  PASS
archive size                                               583226 bytes
archive SHA-256                                            d77a4e29e63ae17b48b2720ddce52a443eee5302bd26f256fb9c9103b0480dd3
```

Targeted download tests: `8 passed`; they cover exact ordered reassembly, overlapping range requests capped at two, contiguous-prefix integrity on Pause, and transport failure propagation. The full suite includes legacy fallback and control-signal tests.

`bun run lint` was attempted from repository root and could not start: `/bin/bash: bun: command not found`. There are no frontend changes. PR #95 is merged and both CI jobs passed. The candidate ZIP and matching manifest were uploaded to the owner's private Drive folder. The GitHub Release has NOT yet been updated; no real Colab/Telegram/Drive transfer or live before/after benchmark has been run for M44-T02.

## Risks and acceptance boundary

This remains a code-complete candidate, not a proven performance win. Telethon's real file-reference/DC behavior and rate-limits need a controlled Colab trial. Owner acceptance requires:

1. Merge this candidate and publish a ZIP + manifest pair built from the exact merged SHA.
2. Restart Colab and confirm Cell 1 installs the new commit.
3. Confirm Telegram log `telethon crypto backend=cryptg`.
4. Transfer one large file and record total bytes, elapsed time, reported rate, and final local size; confirm upload and Drive verification.
5. Test Pause then Resume, and test Stop/fallback without data corruption.

Do not claim a particular speedup until those measurements exist. Do not increase beyond two simultaneous media requests without a separate rate-limit analysis and owner approval.

## Rollback

Revert the M44-T02 commit. Small files already remain sequential; a failed parallel attempt uses the existing legacy full-download fallback. No Drive object is deleted by fallback, Pause, Stop, or rollback.
