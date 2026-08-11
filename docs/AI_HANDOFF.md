# AI_HANDOFF — Live handoff

> This file records the latest execution session only. Historical evidence is in `docs/PHASE_REPORTS/` and `python-package/docs/PHASE_REPORTS/PHASE_M18_T03.md`.

## Session card

| Field | Value |
|---|---|
| UTC date | 2026-08-12 |
| Session type | New session — owner report + §9 resume, then M18-T03 (owner-authorized protected-file classification) |
| TASK ID | `M18-T03` |
| Repository | `body199-cmyk/drive-buddy-3579bf74` |
| Branch (Arena, platform-pinned) | `arena/019ff2cd-drive-buddy-3579bf74` |
| Base SHA | `1d72ba12e93bb929f9392a1c67bae50fb998007b` (`main` = merged PR #31 = M18-T02) |
| Result SHA | **`6281a66`** — PR #33 **merged on the owner's instruction** (2026-08-12); post-merge CI green (run `31544521923`) |
| Status | **MERGED** — remaining owner-side only: manual tag re-publish (`gh workflow run` → HTTP 403, retried this session per KNOWN_ISSUES #27) + live Colab proof |
| Launcher | `binding check ok: 45/45 ready actions resolve` |

## §9 resume verification of the previous milestone (M18-T02)

- `git status --short` clean · branch as above · HEAD `1d72ba1` = "Merge pull request #31" — **PR #31 merged** ✅ (the stale handoff said "غير مدموج"; reality wins, handoff corrected).
- `gh release view pkg-2026.08.09-m15t07`: re-published 2026-08-10T23:13Z, built from `1d72ba1`, run `31441568038`, zip 403931 bytes — **the M18-T02 fix actually ships to Colab** ✅.
- Baseline gates re-run before edits: `582 passed` · launcher 45/45 — matches the old handoff ✅ → `RESUME_VERIFIED`.

## Owner report driving this session

> «الاتصال بالتليجرام بيفشل… أملأ البيانات المطلوبة وأضغط إرسال الكود لكن الكود لا يصل إلى تيليجرام ويظهر الخطأ عند طلب إرسال الكود» — then the literal UI text: `خطأ غير معروف. جرّب مرة أخرى. [fd41da8b]` — on the NEW package (owner restarted runtime + re-ran Cell 1–4).

## Root cause (proven from source before editing)

- The M18-T02 fix covered `telegram.set_credentials` only. The «send code» button runs
  `TelegramAuth.send_code → _do_send_code → client.start_login (Telethon send_code_request)`,
  whose failures land in `TelegramAuth._handle_send_error` (protected file) — it knew only
  `FloodWaitError`; **every other failure became `TeleDriveError` with the default
  `message_key = "err.unknown"`** and the wrapper renders `t('err.unknown') + [cid]` — exactly
  the owner's `fd41da8b`.
- `auth.sendCode` is the FIRST call carrying the `api_id`/`api_hash` pair, so the most likely
  real-world causes (bad API pair → `ApiIdInvalidError`, number rejected → `PhoneNumberInvalidError`,
  number rate-limited → `PhoneNumberFloodError`, transport → `ConnectionError`/`TimeoutError`/
  `IncompleteReadError`) were all being masked. `ctx.aio.run(coro)` has NO artificial timeout —
  the failure is genuinely returned by Telethon.

## What was done (M18-T03 — owner explicitly authorized touching `telegram_auth.py`, classification ONLY)

- `telegram_auth.py`: new module constants `_TRANSPORT_EXC` (isinstance: ConnectionError/
  TimeoutError/OSError/EOFError ⊃ asyncio.IncompleteReadError) and `_SEND_CODE_RPC_KEYS`
  (name-based, like the existing FloodWaitError branch): `ApiIdInvalidError→err.bad_api_pair`
  (state ERROR — fix credentials via Connect, which is allowed from any state),
  `PhoneNumberInvalidError→err.tg_phone_invalid`, `PhoneNumberFloodError→err.tg_phone_flood`
  (both → READY_FOR_PHONE). Transport in `_handle_send_error` → `err.tg_connect_failed` +
  READY_FOR_PHONE. `_handle_code_error` transport branch → `err.tg_connect_failed` + stays
  CODE_REQUESTED (phone_code_hash preserved — same code retries). `verify_password` transport →
  `err.tg_connect_failed` and FloodWait → `err.floodwait`, both staying PASSWORD_REQUIRED —
  no more false «كلمة المرور غير صحيحة». **Login logic, secrets, lock, finally-zeroing untouched.**
- `locale/ar.json` + `en.json`: `err.bad_api_pair` · `err.tg_phone_invalid` · `err.tg_phone_flood`.
- `tests/test_telegram_flow_contract.py`: **+7 proof tests** (each class named + recovery paths
  + happy path untouched). New name-based doubles (`ApiIdInvalidError`, `PhoneNumberInvalidError`,
  `PhoneNumberFloodError`) mirror the existing `FloodWaitError` double technique.
- Docs/memory: `PHASE_M18_T03.md` · `CHANGELOG.md` · `KNOWN_ISSUES.md` (#40 closed fully, #41 added) ·
  `TODO.md` (M18-T02 → VERIFIED COMPLETE; M18-T03 row) · `ACTIVE_TASK.md` · this file.

## Verification (raw)

```plain
$ python -m compileall -q teledrive          → exit 0
$ python -m pytest -q tests                  → 589 passed in 22.57s   (was 582; +7)
$ python teledrive_launcher.py --check       → binding check ok: 45/45 ready actions resolve
$ python -m teledrive.notebook_cells --check → notebooks are in sync
$ cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb → identical
$ python -m teledrive.package_service --build → tests passed · archive OK
$ git diff --stat                            → 4 files changed, 193 insertions(+), 0 deletions(-)
```

## Protected files

Only `telegram_auth.py` was touched — with the owner's explicit session authorization, and for
classification branches only (additive, no deletion, no logic change). Untouched per-path:
`notebook/TeleDrive.ipynb`, `public/TeleDrive.ipynb`, `notebook_cells.py`, `colab_cells.json`,
`database.py`, `migrations.py`, `queue_manager.py`, `transfer_manager.py`, `telegram_client.py`,
`drive_auth.py`, `requirements.*`, `bun.lock`, `package.json`, `.github/workflows/*`, all
React/frontend files.

## Known limitations (honest)

- The EXACT exception class behind the owner's `fd41da8b` was not captured (owner pasted the UI
  message, not the `failed:` log line). After this fix the UI itself names the cause; the Logs
  tab line remains the confirmation record.
- Rare `send_code` RPC classes (e.g. `ApiIdPublishedFloodError`) intentionally still fall back to
  `err.unknown` until seen in a live log.
- No browser/Colab in the sandbox → live proof stays owner-side (KNOWN_ISSUES #41, M15-T01).

## Next action (after the merge — owner-side only)

1. Owner dispatches **Actions → Publish current TeleDrive package → Run workflow (branch: main)**
   so the pinned tag `pkg-2026.08.09-m15t07` rebuilds from `6281a66` (expect ≈2m like run
   `31441568038`; zip should grow past 403931 bytes).
2. Owner in Colab: Runtime → Restart runtime → Cell 1 (update gate pulls the new manifest
   digest) → Cells 2–4.
3. Owner presses «إرسال الكود» — the UI MUST name the reason
   (`err.bad_api_pair` / `err.tg_phone_invalid` / `err.tg_phone_flood` / `err.tg_connect_failed`)
   instead of `err.unknown`; the redacted `failed:` line in the Logs tab confirms the class.

## GitHub handoff (this session)

- Branch: `arena/019ff2cd-drive-buddy-3579bf74`
- Commit: `c01a3b5` (code+tests+docs, prefixed `M18-T03`)
- PR: **#33 — MERGED** on the owner's instruction (merge commit `6281a66` on main; post-merge CI
  run `31544521923` success 1m33s)
- Tag re-publish attempt: `gh workflow run release-current.yml --ref main` → **HTTP 403**
  (KNOWN_ISSUES #27 stands — owner dispatches manually)
