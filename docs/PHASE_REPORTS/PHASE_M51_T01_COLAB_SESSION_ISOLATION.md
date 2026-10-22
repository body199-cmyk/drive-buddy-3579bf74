# M51-T01 — Colab per-runtime privacy hardening

- Date: 2026-10-22
- Branch: `fix/colab-user-session-isolation`
- Status: **Implemented on branch; CI and live Colab verification pending**
- Scope: dashboard access control, repository hygiene, handoff documentation
- Explicit non-scope: no transfer-engine rewrite, no Telegram/Drive schema migration, no deletion of the owner's Drive vault, no changes to the Colab notebook cells.

## Problem confirmed

The modern FastAPI dashboard served a shared `ApplicationContext` but had no application-level authentication on its metrics, state, logs, queue, Universal Downloader, compatibility, and WebSocket routes. Anyone who could reach a runtime dashboard URL could potentially inspect or mutate the same runtime's tasks.

The architecture is one owner per Colab runtime, not multi-tenant. Separate users must run separate Colab runtimes and authorize their own Google Drive and Telegram accounts.

## Session and Drive findings

- Runtime SQLite, logs, temporary files, checkpoints, and local Telethon session live under the local runtime root (normally `/content/teledrive_runtime`), not in the repository.
- Telegram resume data is persisted through the existing SessionVault to `TeleDrive_AppData` in the currently connected Google Drive account. That storage boundary is account-specific when each user authorizes their own Drive.
- Existing vault format 3 is an owner-approved Drive-managed convenience format, not independent cryptographic protection from anyone with full access to the Drive vault.
- `.gitignore` already ignored `*.session`, `telegram_creds.json`, and `/content/teledrive_runtime/`; added ignores for session journals/WAL/SHM/snapshots, Telegram session variants, vault metadata, SQLite database artifacts, and environment files.
- No actual user session file or Drive-side data was found or deleted as part of this GitHub-only change. Tests and source code mentioning session filenames remain intentionally tracked.

## Implemented changes

1. Each dashboard launch creates a fresh high-entropy token.
2. The owner receives a URL containing the token only in the URL fragment, which browsers do not send in HTTP requests.
3. The page exchanges the fragment token for a short-lived HttpOnly, SameSite=Strict cookie, then removes the fragment from browser history.
4. A default-deny HTTP middleware protects every endpoint except the data-free HTML shell and the authentication exchange. This includes health, metrics, state, logs, action/queue aliases, Universal Downloader tasks and controls.
5. WebSocket authorization is enforced separately before accepting a connection.
6. Added regression tests for anonymous denial, invalid-token denial, authenticated access, cookie attributes, and anonymous WebSocket denial.
7. Updated `docs/AI_HANDOFF.md` with findings, limits, non-destructive scope, and verification requirements.

## Verification plan

- Run the complete Python test suite and frontend contracts in CI.
- Confirm the dashboard JavaScript bootstraps authentication before its first API polling/action calls.
- Restart a fresh Colab runtime from the published package.
- Confirm the owner URL works, then make unauthenticated requests to `/api/metrics`, `/api/state`, `/api/logs`, `/api/universal/tasks`, `/api/action`, and `/ws`; HTTP data routes must return 401 and WebSocket must refuse the connection.
- Confirm Telegram login/session restore, Drive connection, queue pause/resume/retry, and a small test transfer still work in the owner's runtime.

## Rollback

Revert the dashboard authentication change if it blocks the owner UI. No Drive vault or Telegram session cleanup is required for rollback; the transfer engine and stored account data are unchanged.

## Important boundary

This protects access to a single owner's dashboard; it does not turn one shared Colab runtime into a multi-user service. The safe operating model remains **one Colab runtime + one user's Drive + that user's Telegram session per person**.