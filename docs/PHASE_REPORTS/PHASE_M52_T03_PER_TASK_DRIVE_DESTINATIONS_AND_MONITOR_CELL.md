# M52-T03 — Per-task Google Drive destinations and final Colab monitor cell

**Date:** 2026-10-23  
**Repository:** https://github.com/body199-cmyk/drive-buddy-3579bf74  
**Branch:** `feat/per-task-drive-folders-monitor-cell`  
**PR:** [#136](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/136)  
**Status:** Draft PR; CI pending; live Colab/Drive test not performed.

## Request

Allow an active Telegram-to-Drive transfer to continue while a separate Universal Downloader task saves to a different Google Drive folder. Also append the user's monitoring code as the final notebook cell.

## Findings

- The Universal Downloader manager already accepted `folder_id` per task and stored it with task state, but the web UI posted only URL and quality, so the UI could not choose a different folder.
- Telegram queue transfers and Universal Downloader tasks use separate managers. That supports a design for concurrent work, but does not itself prove the two transfer paths succeed concurrently in the active Colab runtime.
- The repo has a canonical notebook generator, `python-package/teledrive/notebook_cells.py`, which produces both notebooks and `python-package/teledrive/colab_cells.json`. Editing only `public/TeleDrive.ipynb` would create drift. The branch also contained an experimental Vercel handoff cell and matching shutdown logic that were preserved and incorporated into the canonical source.

## Changes prepared

1. Added an independent Universal Downloader folder browser using the existing read-only `drive.list_folders` bridge action. It does not call `drive.select_folder`, so it does not change the global destination used by Telegram.
2. Sends the selected `folder_id` and `folder_name` with each new universal task.
3. Stores the folder name with task state and passes it through retry, preserving the original destination.
4. Added/updated regression tests for the picker contract and retry destination.
5. Added the monitoring cell as the final canonical notebook cell; synchronized both notebook copies and `colab_cells.json`.
6. Updated the notebook instructions: run the monitor after downloads start, and do not run the cleanup/shutdown cell until transfers are finished.
7. Updated the monitor cleanup block to restore `write`, `writelines`, and `flush` methods that it temporarily overrides.

## Validation and limits

- Confirmed through repository reads that the notebook JSON parses, the source and exported cell list agree on all 11 code cells, the monitor is the last cell, and both notebook copies are byte-identical.
- Added tests but did **not** execute pytest locally. GitHub Actions CI run #769 was in progress at the time this report was written.
- No live Colab runtime was attached. No real Telegram download and Universal Downloader download were run together. No claim is made that the two files have been written to separate Drive folders in a live account.
- The monitor aggregates `ctx.queue_manager.snapshot()` (Telegram queue) with `get_universal_downloader(ctx).list_tasks()` (Universal Downloader) so its active/remaining counts cover both separate managers. It still shows counts rather than per-file progress.

## Next actions

1. Wait for PR #136 CI; fix any failing checks before merge.
2. In Colab, run the normal verified package update/bootstrap and launch sequence.
3. Create or choose two distinct Drive folders. Start a small Telegram transfer to Folder A, then a small Universal Downloader transfer to Folder B without stopping the first.
4. Confirm both tasks progress concurrently and each completed file appears only in its intended folder.
5. Run the final monitor cell during active work; interrupt it manually when needed. Do not run cleanup/shutdown before transfers finish.
6. Do not publish a new release until CI and live verification are documented.

## Rollback

Close or abandon PR #136 without merging. Production `main` and the published package are unchanged by this draft PR. No Drive data or account credentials were changed.
