# PHASE_M24_T05 — Deterministic Telegram Session Vault

## Session identity

| Field | Value |
|---|---|
| TASK ID | `M24-T05` |
| Branch | `arena/m24-t05-session-vault-determinism` |
| Base SHA | `70e3406931134c289637d7892f6eeb5ebef7ae94` |
| Commit status | Local commit succeeded; push, PR, and merge are authorized and pending execution |
| Honest status | Implemented + fake-tested. Not live-verified. |

## STEP 0 diagnostic output — redacted

The owner ran the required read-only Colab diagnostic. It reported an authorized Telegram state, a connected Drive state, a present local `telegram.session` file with a valid SQLite header, one session-row, and an application-data folder containing `telegram.session`, `telegram_creds.json`, and `td_telegram.session.vault`. Account identity, folder identifier, and unrelated checkpoint filenames are intentionally omitted.

This excludes the hypothesis that the observed runtime never completed Telegram authorization. It confirms the competing-vault condition. It does not prove whether Drive was unavailable at the authorization instant, whether SQLite was locked during a write, or whether a restarted VM can restore the saved session; those remain the explicit M24-T06 live checks.

## Baseline comparison

| Requirement | Expected file | Present in baseline | Action |
|---|---|---:|---|
| User-facing vault pair | `session_vault.py` | Yes | Strengthen and migrate to format 2. |
| Automatic save hooks | `handlers.py`, protected auth hook | Yes | Preserve hooks; route protected integration to the modern vault and drain deferred saves. |
| Legacy blob compatibility | `session_vault.py` | Yes | Stop future writes, retain read compatibility, remove old blob on forget/logout. |
| Vault test surface | `tests/test_session_vault.py` | Yes | Extend coverage without shared-fixture changes. |
| Notebook visibility updates | `notebook_cells.py` | No approval | Not executed; protected optional Part B. |

## Files modified

| File | Change |
|---|---|
| `python-package/teledrive/session_vault.py` | Unified persistence, format 2, lock-resilient snapshots, deferred saves, checked restoration, redacted status, and legacy cleanup. |
| `python-package/teledrive/handlers.py` | Drains a pending vault save before the next UI action. |
| `python-package/tests/test_session_vault.py` | Adds and updates fake-tested M24-T05 coverage. |
| `python-package/docs/decisions/ADR-0002-telegram-session-vault-on-drive.md` | Documents the migration and constraints. |
| `docs/CHANGELOG.md` | Records the M24-T05 change. |
| `docs/TODO.md` | Records M24-T05 and M24-T06. |
| `docs/ACTIVE_TASK.md` | Moves the live task lock to M24-T05. |
| `docs/AI_HANDOFF.md` | Records branch, checks, and remote-operation status. |
| `docs/KNOWN_ISSUES.md` | Updates the legacy-blob and plaintext-credential risks; records the remaining live proof. |

No protected file, notebook, lockfile, workflow, action specification, i18n key, or `ERROR_ARITY` entry was changed.

## Verification results

| Command | Actual result |
|---|---|
| `python3 -m compileall teledrive` | PASS |
| `python3 -m pytest -q tests/test_session_vault.py -v` | `32 passed` |
| `python3 -m pytest -q tests` | `700 passed` |
| `python3 teledrive_launcher.py --check` | `binding check ok: 51/51 ready actions resolve` |
| `python3 -m teledrive.notebook_cells --check` | `notebooks are in sync` |
| `cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb` | PASS |
| `python3 -m teledrive.package_service --build --output teledrive_v4.5.zip` | `archive: teledrive_v4.5.zip` |
| `bun run lint && bun run build` | Not run: Bun is unavailable in the sandbox. |
| `pnpm run lint && pnpm run build` | PASS fallback; the project scripts completed successfully. |

## M24-T06 owner protocol

The owner should use a completely new Colab VM and the same Drive account. After one complete manual Telegram sign-in, the no-button path must save the vault in format 2. After a runtime restart, the same account must restore without a new OTP. Logout must leave the vault empty and force manual sign-in next time. A different Drive account must not restore the session.

> This report contains no API ID, API hash, phone number, OTP, session bytes, Drive account identifier, or Drive folder identifier.
