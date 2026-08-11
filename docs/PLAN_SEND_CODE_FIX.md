# Plan — send_code-only Telegram fix

## Scope

Fix only the `send_code` path. Preserve the existing M18-T02 classification in `handlers.py`; do not apply the obsolete TD-FIX-01 document wholesale.

## Intended changes

1. Reuse one Telethon client in `telegram_client.py` and add an explicit timeout around `start_login()`.
2. In `telegram_auth.py`, retry `AuthRestartError` exactly once, then classify every remaining `start_login()` failure with a dedicated typed error instead of `err.unknown`.
3. Add the typed error and Arabic/English locale messages.
4. Add focused tests if the local test environment permits; otherwise record pytest as NOT ATTEMPTED.

## Verification

Run compileall and the focused pytest command. Report only commands that actually produced output. No Complete/success claim without output.
