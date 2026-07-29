# TeleDrive Master Constitution v3.1 (Code-Bound Edition)

> **Provenance note (honest):** the authoritative v3.1 constitution text was not supplied
> verbatim to this repo. This file is the code-bound restatement of every rule that the
> **Lovable Build Order v3.1 (Single-File Execution Brief, audit commit `0a3eee0`,
> 2026-07-29)** binds the implementation to. Where the brief quotes the constitution, the
> quote is reproduced exactly. If the owner supplies the original v3.1 document, replace
> this file with it verbatim — no rule below may be weakened in that replacement.

## Section 1 — Identity

- Product: **TeleDrive v3.1** — a Telegram → Google Drive transfer engine that runs
  entirely inside a single Google Colab Python process.
- `spec_version = "3.1.0"`, `version = "3.1.0"`. The string "TeleDrive v2" is retired
  everywhere, including the notebook title.
- The React app in `src/` is a **marketing/reference landing page only**. It is not the
  runtime and must never claim to be. No Telegram, Drive, queue, progress, quota or log
  logic may exist in TypeScript.

## Section 2 — Shared ApplicationContext

One `ApplicationContext`, created exactly once per Colab session, owns every service:
config, i18n, db, telegram_auth, drive_auth, drive_folders, drive_quota, queue_manager,
transfer_manager, checkpoint_manager, storage_manager, media_scanner, filters, selection,
scan_policy, settings, log_service, package_service, colab_export, connection_service,
account_service, preferences, and a `UIState`.

- Module-level mutable singletons (`AUTH`, `CONFIG`, `QUEUE`, `PROGRESS`, `_transfer_mgr`,
  `_transfer_thread`, `_transfer_loop`) are forbidden after Phase 9.
- `ctx.resolve("queue_manager.start_selected")` returns a bound method and **raises** on a
  typo, a `None` service, or a non-callable target.
- **Single-process rule:** one Telethon client, one Drive service, one asyncio event loop
  for the whole session. A handler that constructs a client or a loop is a build-breaking
  bug.

## Section 3 — Async runtime

`teledrive/async_runtime.py` owns one background event loop started at bootstrap. Every
coroutine is marshalled onto it via `ctx.aio.run(...)` / `ctx.aio.submit(...)`.
`asyncio.new_event_loop()` and `asyncio.run(` may appear in **no file other than**
`async_runtime.py`; `tests/test_no_ad_hoc_loops.py` enforces this permanently.

## Section 4 — Control surface

Every visible control is declared once in `ACTION_SPECS` with an `action_id`,
`handler_name`, `service_path`, `label_key`, `section`, and the `implemented` / `tested`
flags.

- `implemented=True` only in the commit that adds both the named handler and the service
  method. `tested=True` only in the commit that adds a passing test asserting the handler
  calls that exact service.
- `UIBinder.wire()` refuses to render a control whose spec is not implemented **and**
  tested (`DeadControlError`) or whose `action_id` is undeclared (`UnknownActionError`),
  and resolves the `service_path` against the live context at build time.
- `binder.assert_complete()` fails the build if a ready action was never wired.
- `ui.py` contains zero `.click(`, `.change(`, `.submit(`, `.select(` and zero `lambda`.
  Those belong only to `ui_binder.py`.

### Section 4A.2 — the five-link proof

A feature is done only when all five links exist and are demonstrated:
UI action → same-process real API call → local SQLite row → UI state updated from the
**real** returned value → redacted event on the Logs page.

## Section 5 — Telegram authentication

States, exactly: `DISCONNECTED, READY_FOR_PHONE, SENDING_CODE, CODE_REQUESTED,
VERIFYING_CODE, PASSWORD_REQUIRED, VERIFYING_PASSWORD, AUTHORIZED, REAUTH_REQUIRED, ERROR`.

- `api_id` / `api_hash` live in protected memory only: never persisted, logged or
  checkpointed. Phone must be international format with `+`.
- `send_code()` fires `send_code_request()` once per request and stores
  `phone_code_hash`; `verify_code()` **must** pass that hash to `sign_in`.
- `PhoneCodeInvalidError` keeps the hash and the `CODE_REQUESTED` state;
  `PhoneCodeExpiredError` clears the hash and returns to `READY_FOR_PHONE`.
- `SessionPasswordNeededError` → `PASSWORD_REQUIRED`; `verify_password()` reuses the same
  client, requests no new code, and zeroes the password immediately after use.
- `resend_code()` is a separate action with a ≥60s cooldown that respects
  `FloodWaitError.seconds`. Double-clicks fire once.
- Session file lives at `config.TELEGRAM_SESSION` on local `/content`, never on Drive.

## Section 6 — Google Drive authentication

Native Colab auth only: `colab_auth.authenticate_user()` → `google.auth.default(scopes=
["https://www.googleapis.com/auth/drive"])` → `build("drive","v3",...)`. Uploaded OAuth
desktop client JSON, paste-the-code textboxes, and persisted `drive_token.json` are
forbidden. No "Connected" chip before a successful `about().get()` gate. Folder selection
persists a **folder ID**, never a name. Quota warns at ≥90% and refuses to enqueue when
remaining space < item size + reserve. Account switching requires an explicit restart +
re-auth, never a silent credential swap.

## Section 7 — Transfer order (sacred)

1 validate both connections · 2 scan · 3 create MediaItem · 4 duplicate check ·
5 Drive quota check · 6 local disk check · 7 enqueue · 8 download to `.part` ·
9 verify local size · 10 resumable Drive upload · 11 verify Drive file id +
appProperties + parent + size · 12 durable checkpoint · 13 mark Uploaded · 14 cleanup temp.

Only `QueueManager` mutates queue state. Cancel/stop/clear-completed never delete a Drive
file. Concurrency is a bounded worker pool, default 2, hard cap 4. Size mismatch keeps the
`.part` file; unknown temp files are quarantined, not deleted.

## Section 8 — Analyze and selection

Three scopes only: `message`, `group`, `range` (bounded, explicit start/end). A whole
channel is never crawled. Analyze **displays**; it never enqueues. The user filters,
selects, then enqueues explicitly. Dedupe uses deterministic MTProto identity — never a
filename and never a Bot API `file_unique_id`.

## Section 9 — Interface

Arabic RTL by default with a live English LTR switch that preserves runtime state. Right
side nav rail in RTL, graphite dark surfaces (never pure black), a coordinated light
theme, off-white text, quiet gray borders, restrained lime accent (`#C6F24E` family).
Slim top bar: ZIP export · theme · AR/EN · Drive status + default-folder chip · Telegram
status + safe account label · identity badge with version. Sections: Dashboard, Transfers,
Analyze, Connection Center, Logs, Settings, Colab Code/Export. Concurrency control is a
slider **1–4, default 2**. Empty runtime renders the localized empty component — no demo
rows, fake counters, fake connected dots or timer-based progress. The engine badge reads
real runtime values only.

## Section 10 — Notebook contract (seven-vs-nine conflict, resolved)

**Resolution:** the reproducible **seven-cell launcher contract** stands. The Drive and
Telegram fallbacks ship as **clearly marked optional cells 8 and 9** that call functions
reusing the same `ApplicationContext`; they never create a client per cell or per button.

Cells: 1 restore + install from `requirements.lock` · 2 bootstrap local runtime (dirs,
logging, SQLite migrations, WAL) · 3 hidden credentials via `getpass` + verified Drive ·
4 build the single context, restore + reconcile, launch Gradio `share=False`, no
auto-resume · 5 redacted handoff · 6 `python -m pytest -q tests` printing real stdout and
stderr and **failing the cell on failure** · 7 safe maintenance (checkpoint, clean only
verified Uploaded items, quarantine the rest, close SQLite — never a blind
`rmtree(TEMP_DIR)`). `teledrive_launcher.py` is the single stable entry point.

## Section 11 — Hard prohibitions (instant rejection)

1. No `app_v2.py`, `final_app.py`, second application, or static HTML runtime.
2. No Python logic written as a TypeScript string. Every module is a real `.py` file.
3. No demo rows, fake logs, fake quota, fake folder IDs, fake connected state, forced
   Telegram authorization, or timer-based fake progress.
4. No visible control without a named handler + resolvable service path + passing test.
5. No inline `lambda` as a handler. Ever.
6. No SQLite on mounted Drive or FUSE. Local `/content` only.
7. No API ID, API hash, phone number, login code, 2FA password, session string, OAuth
   token, private URL, raw credential, or unredacted traceback in code, logs, checkpoints,
   snapshots, handoffs, git, or notebook output.
8. No Bot API assumptions and no `file_unique_id` for dedupe.
9. No concurrency above 4.
10. No claim of "streaming Telegram → Drive" in v1. Disk-first with verified resumable
    upload.
11. Cancel/stop must never delete a Drive file.
12. No claim that login, upload, recovery, or a test passed without pasted real execution
    output.

## Section 12 — Verification

Every phase runs and pastes the actual output of:

```
python -m compileall teledrive
python -m pytest -q tests
npm run build
npm run lint
```

CI (`.github/workflows/ci.yml`) runs the same four commands on every push and PR with no
`continue-on-error`. `package_service.build_tested_archive()` refuses to build when tests
fail, so the ZIP button cannot ship a broken package. `public/teledrive-package.zip` is a
generated artifact and is never committed.

Each phase writes its report to `docs/PHASE_REPORTS/PHASE_<n>.md` using the Section 8
template of the build order.
