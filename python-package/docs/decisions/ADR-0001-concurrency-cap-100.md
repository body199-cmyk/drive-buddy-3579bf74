# ADR-0001 — Raise the hard concurrency cap from 4 to 100

- Status: Accepted
- Date: 2026-08-12
- Decider: project owner (explicit instruction)
- Supersedes: Constitution v4.5 section 12.8 ("default 2, hard cap 4")
- Implemented by: M20-T01

## Context

Constitution 12.8 fixed the transfer concurrency at a default of 2 and a hard
cap of 4. The cap was a safety margin for Colab RAM, local disk and
Telegram/Drive rate limits, not a protocol requirement.

The owner requires a cap of 100 and has acknowledged that this deviates from
the inherited product contract.

## Decision

`HARD_CONCURRENCY_CAP` becomes 100. The default stays 2. The UI exposes a
1..100 slider. Values above `CONCURRENCY_WARN_ABOVE` (8) are accepted but the
UI shows an explicit risk warning. Values outside 1..100 are rejected with a
localized error instead of being silently clamped, so the number on screen is
always the number the engine uses.

## Consequences

- The semaphore bound in `TransferManager` still holds; only its ceiling moved.
  `worker_count()` / `set_workers()` import `HARD_CONCURRENCY_CAP` from
  `config` at call time, so the protected transfer file needed no edit.
- Real risk at high values: Colab RAM (8 MiB upload chunk per in-flight item),
  local disk pressure in `/content`, Telegram FloodWait, Drive 403 rate limits.
  None of these are mitigated by this ADR. They are accepted by the owner.
- "Colab-ready" and "Complete" claims are NOT affected: a real Colab run at a
  high worker count has not been performed and must not be implied.
- Reverting is a one-line change to `HARD_CONCURRENCY_CAP` plus the tests in
  `tests/test_concurrency.py` and `tests/test_settings_concurrency.py`.

## Tests

- `tests/test_concurrency.py` — the cap, every named level, manual values up to
  and beyond the cap, and the semaphore bound at 100 workers / 250 tasks.
- `tests/test_settings_concurrency.py` — the 1..100 accept/refuse gate, the
  warning above 8, and the `{level, workers, cap, warn}` service contract.
- `tests/test_phase_3.py` — `TransferManager` and `QueueManager` clamp to the
  new ceiling.
- `tests/test_ui_layout_contract.py` — the slider is built from the constants,
  never from literals.
