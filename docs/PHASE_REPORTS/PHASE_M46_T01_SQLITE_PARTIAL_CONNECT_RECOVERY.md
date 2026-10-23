# PHASE M46-T01 — SQLite partial-connection recovery hardening

**Status:** Code change prepared on an isolated branch; runtime issue NOT yet verified fixed.  
**Branch:** `fix/sqlite-partial-connect-recovery`  
**Date (UTC):** 2026-10-23

## Evidence motivating this change

The live Colab runtime reported repeated `sqlite3.OperationalError: attempt to write a readonly database` while processing queue records. The database and WAL files appeared to have writable permission bits, but that does not prove the underlying mount or SQLite connection can write. Existing recovery reconnects after an operational error, but the existing `_connect()` assigns the module singleton before running all PRAGMAs.

## Change

- Keep the newly opened SQLite connection local until every initialization step succeeds.
- Verify that `PRAGMA journal_mode=WAL` actually reports `wal`.
- If any connection initialization step fails, close the new connection and leave the singleton `_conn` as `None`, so a later attempt cannot reuse a partially initialized connection.
- Add tests for a real temporary on-disk SQLite database across close/reopen, and for cleanup after a simulated WAL initialization failure.

## Safety / limitations

- No changes were made to the live Colab runtime, its queue, or its database.
- No runtime restart, database deletion, queue reset, or automatic resume was performed.
- This patch prevents a partial connection from being cached; it does **not** by itself repair a filesystem or mount that has genuinely become readonly. If the operating system refuses writes, the app must surface that as a storage failure and preserve the queue rather than retrying indefinitely.
- Tests have been added but have not been executed by this assistant in a Python/Colab runtime. Treat this as a candidate patch, not a verified permanent fix.
- Do not publish a new runtime package or switch the active Colab session to this code until CI and a safe runtime verification pass.
