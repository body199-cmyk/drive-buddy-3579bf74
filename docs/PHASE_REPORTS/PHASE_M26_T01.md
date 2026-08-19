# PHASE_M26_T01 — Transfer control: real Pause / Stop / Resume

## Session and baseline

| Field | Value |
|---|---|
| TASK ID | `M26-T01` |
| Session type | New coding session after merged PR #51 |
| Resume status | `RESUME_VERIFIED` |
| Base SHA | `26fd421e68637f5d6b40b25864f6252613081fb3` |
| Branch | `arena/m26-t01-transfer-control` |
| Result SHA | Not created; local change pending owner approval |
| Honest status | Implemented + fake-tested. Not live-verified. |

PR #51 was confirmed merged into `main`; its merge SHA is the baseline. The prior handoff claim that push/PR/merge had not happened was stale and has been corrected in `docs/AI_HANDOFF.md`.

## Baseline table

| Requirement | Expected file | Present | Verified | Action |
|---|---|---:|---:|---|
| Cooperative control exception outside `TeleDriveError` | `errors.py` | No | Yes | Add control hierarchy. |
| Remove in-flight progress without counter mutation | `progress_tracker.py` | No | Yes | Add `release_item()`. |
| Upload callback rethrows control signals only | `drive_client.py` | No | Yes | Rethrow `TransferControlSignal`; retain cosmetic-error swallowing. |
| Thread-safe global flags and callback gates | `transfer_manager.py` | No | Yes | Use `threading.Event` and control signals. |
| Resume Paused rows and reset stale stop state | `queue_manager.py` | No | Yes | Revive rows/restart drain and reset flags. |
| Pause/stop control coverage | `tests/test_transfer_control.py` | No | Yes | Add unit and fake integration tests. |

## Root-cause implementation

| Root cause | Change |
|---|---|
| RC-1 | Replaced cross-thread `asyncio.Event` control flags with `threading.Event`; pause waits by asynchronous polling. |
| RC-2 | Download and resumable-upload progress callbacks invoke `_raise_if_interrupted()` at chunk boundaries. |
| RC-3 | No task cancellation was added; `run()` drains cooperative workers with `gather()`. |
| RC-4 | Queue resume transitions every Paused row to Pending and launches a new drain loop when the old one ended. |
| RC-5 | `start_selected()` calls `reset_run_flags()` on the reused context-owned manager. |
| RC-6 | Pause/stop releases the active progress entry without adding done, skipped, or failed counters. |

No callback is inserted after `upload_resumable()` or inside `Verifying`/`UploadedPendingCheckpoint`. A file that reached Drive must complete verification and durable checkpointing to avoid an orphan remote file.

## Files

| Type | Paths |
|---|---|
| Created | `python-package/tests/test_transfer_control.py`; this phase report |
| Modified source | `errors.py`, `progress_tracker.py`, `drive_client.py`, `transfer_manager.py`, `queue_manager.py` |
| Modified memory | `AI_HANDOFF.md`, `ACTIVE_TASK.md`, `TODO.md`, `KNOWN_ISSUES.md`, `CHANGELOG.md` |
| Protected untouched | UI, handlers, action registry, session vault, Telegram/Drive auth, notebook/generator, state machine, lockfiles, workflows, frontend source |

## Commands and real output

```text
$ git status --short
<clean>
$ git branch --show-current
main
$ git rev-parse HEAD
26fd421e68637f5d6b40b25864f6252613081fb3
$ git log -5 --oneline --decorate
26fd421 (HEAD -> main, origin/main, origin/HEAD) Merge pull request #51 from body199-cmyk/arena/m24-t05-session-vault-determinism
...

$ cd python-package && python3 -m pytest -q tests   # baseline
700 passed in 35.05s

$ python3 -m pytest -q tests/test_transfer_control.py -v
11 passed in 0.40s

$ python3 -m pytest -q tests
711 passed in 34.98s

$ python3 -m compileall teledrive
PASS

$ python3 teledrive_launcher.py --check
binding check ok: 51/51 ready actions resolve

$ python3 -m teledrive.notebook_cells --check
notebooks are in sync

$ cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb
PASS

$ python3 -m teledrive.package_service --build --output teledrive_v4.5.zip
archive: teledrive_v4.5.zip

$ bun run lint && bun run build
NOT RUN: bun unavailable in sandbox

$ pnpm run lint && pnpm run build
PASS fallback
```

## Tests not run or not proven

No live Telegram, Drive, or Colab transfer was possible in this sandbox. The new tests are fake-based; they prove cooperative state handling, partial-file retention, no failed counter, no `delete_file` call, and callback propagation in controlled local scenarios. They do not prove a real network chunk or a real Google resumable-upload cancellation.

## Security and GitHub status

No secrets, IDs, phone numbers, codes, session strings, or tokens were added. No new control path calls `delete_file`; Pause/Stop retain `.part` and keep Drive untouched. No protected file was modified.

| Operation | Status |
|---|---|
| Commit | NOT ATTEMPTED |
| Push | NOT ATTEMPTED |
| Pull Request | NOT ATTEMPTED |
| Merge | NOT ATTEMPTED |

## Rollback and next step

Rollback before merge is discarding this branch. The last green merged SHA is `26fd421e68637f5d6b40b25864f6252613081fb3`; after merge use `git revert -m 1 <merge-sha>`. The next smallest step is owner review and explicit approval for commit, push/PR, and merge. A live owner-run Colab test remains required after merge.
