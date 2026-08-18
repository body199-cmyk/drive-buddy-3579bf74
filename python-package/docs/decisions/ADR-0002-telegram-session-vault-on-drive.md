# ADR-0002: Telegram session vault on the user's own Google Drive

## Status
Accepted

## Context
TeleDrive runs on ephemeral Colab runtimes. The local Telethon session file is lost on runtime restart, causing repeated Telegram login prompts and risk of account throttling.

ADR-004 already persists an obfuscated session blob and relies on Colab Secrets for `api_id` / `api_hash`. That still requires re-entering credentials when Secrets are missing. This ADR adds an explicit, user-owned backup of the session file plus a small credentials JSON so the same Drive account can restore without a new Telegram code.

## Decision
Persist a backup of the local `telegram.session` SQLite file and a minimal `telegram_creds.json` payload inside the existing `TeleDrive_AppData` folder on the user's own Drive account.

Restore the backup onto local `/content` before reuse. The session file is never executed from Drive directly.

## Consequences
- Same Drive account: Telegram can auto-restore without a new code.
- Different Drive account: no restore occurs.
- If the Telegram session is revoked externally, the app falls back to manual login.
- This is an intentional deviation from the earlier "credentials live in memory only" rule, but it is scoped to user-owned Drive persistence and does not introduce a second auth mechanism.
- The ADR-004 obfuscated blob and keepalive hooks remain because `telegram_auth.py` is a protected file and still calls them.
- M24-T03: the restore now runs at UI build time (before the first paint), so the feature does not depend on a Gradio page-load event firing.
- M24-T03: logout deletes the vault through the logout handler, because `telegram_auth.py` is protected and only knows the ADR-004 blob.
- M24-T03: a restored blob is written to the local session path only when it starts with the SQLite magic header; otherwise the manual login path stays intact.
- M24-T03: saving falls back to the credentials already held in TelegramAuth memory, and a successful login saves the vault automatically when the account has none.
- M24-T05: `persist_from_context()` is the one persistence path after authorization; the legacy ADR-004 blob is no longer written, and pending saves are retried after Drive becomes ready.
- M24-T05: the default format is 2. The session snapshot is wrapped with an `api_hash` retained only in live memory or Colab Secrets, while `telegram_creds.json` stores no `api_hash`. Format 1 remains readable for migration and `TELEDRIVE_VAULT_PLAINTEXT=1` is an owner-only legacy escape hatch.
- M24-T05: snapshotting resists a locked live SQLite file; a restore only swaps a released client path, and a restored session that fails authorization is removed locally and from the vault.
- M24-T05: logout/forget remove the current vault pair and the residual legacy `td_telegram.session.vault` blob.
- Status: Implemented + fake-tested. Not live-verified; the owner must complete M24-T06 on a real Colab VM before any Colab-ready claim.
