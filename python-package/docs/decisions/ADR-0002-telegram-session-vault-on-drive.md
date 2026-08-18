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
