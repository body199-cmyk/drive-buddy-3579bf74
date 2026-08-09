# PHASE M15-T07 — post-merge CI repair + constitutional Colab package update path

Executor: LM Arena Agent · Branch: `arena/019fe79f-drive-buddy-3579bf74`
Base SHA: `333cd753c51b8c56fd1a48a1f7924c44b28e1290` (== `origin/main` == HEAD at session start; clean tree)
Canonical repo: `body199-cmyk/drive-buddy-3579bf74` (public — verified via `gh repo view --json isPrivate`).

## 1. Diagnosis (evidence first — no inference from previous reports)

Post-merge `main` CI run **65** = Actions run id `31326929948` (`event: push`, `headSha: 333cd753`),
job `Python package (tests + Colab contract)` id `93278678720`, **one** failed step:

```
##[group]Run python -m teledrive.package_service --build --output teledrive_v4.5.zip
...
teledrive/package_service.py", line 109, in build_tested_archive
    raise TeleDriveError(
teledrive.errors.TeleDriveError: test suite failed; archive not produced
...
FAILED tests/test_telegram_flow_contract.py::test_phone_code_hash_stays_in_memory_and_out_of_the_event_log
    assert 'abc' not in '[{"id": "ab...epted\\"}"}]'
E   'abc' is contained here:
E     [{"id": "abc91a3a-5727-4ba5-bb4c-8c0a593597c7", ...}]
1 failed, 379 passed, 1 warning in 12.70s
##[error]Process completed with exit code 1.
```

Log fetch note: the sandbox cannot reach the Actions log hosts directly; the job log was
retrieved through a short-lived signed URL (REST `GET /actions/jobs/{id}/logs`) via the
platform fetch path, chunks 0, 6, 7 (start, test-step, build-step + pytest tail).

**Root cause — a statistically flaky assertion, not a product regression.**
`test_phone_code_hash_stays_in_memory_and_out_of_the_event_log` called
`set_credentials("12345", "abc")` and asserted the api_hash sentinel `"abc"` never appears in
the serialized event log. Event rows carry a random **UUID4** `id`. Any UUID containing the
3-hex substring `abc` (e.g. `abc91a3a-…`) trips the assertion. Probability ≈ 1 − (4095/4096)^(3 rows × 30 positions) ≈ 2 % per test run — so the **same commit** passed the
standalone `Run test suite` step (`380 passed, 1 warning in 14.03s`) and failed the build
step's constitution-mandated suite re-run (`build_tested_archive` runs `pytest -q tests`
before archiving). Artifact upload was correctly skipped.

Local reproduction (pre-fix), exact single test at iteration 40:

```
E  'abc' is contained here:
E    "fcaabbe1-abc8-4732-bc0b-b0187ba3550c", ... "READY_FOR_PHONE->SENDING_CODE" ...
tests/test_telegram_flow_contract.py:110: AssertionError
1 failed in 0.06s
```

## 2. The smallest constitutional fix

* `tests/test_telegram_flow_contract.py`: the fake api_hash is now a realistic
  **32-hex sentinel** `0123456789abcdef0123456789abcdef`. A random UUID4 can only collide
  by full-string equality (probability 16^-32 ≈ 0), so the check is now a deterministic
  permission test of exactly what the constitution forbids (api_hash in the event log).
  Added regression `test_api_hash_never_reaches_the_event_log_across_repeated_logins`
  (48 login/logout cycles, whole-log scan — with the old sentinel this loop fails within
  ~40 iterations ≈ the run-65 failure mode).
* No production code was changed for Phase A; no protected file was touched; the workflow
  file is untouched (the failure was not workflow-caused).

## 3. Phase B — safe, verified package update path for Colab (implemented)

* `package_service.build_archive`: sorted, de-duplicated entries; fixed zip metadata
  (`date_time=(2020,1,1)`, `create_system=0`, `external_attr=0o644<<16`, posix arcnames)
  → the artifact is a **reproducible release object**; same tree ⇒ same sha256
  (proven below). CI artifact stays the reproducible fallback (requirement 1).
* `notebook_cells.CELL_1_PACKAGE_UPDATER` + regenerated notebooks (single generator,
  byte-identical copies + `colab_cells.json`): a **pre-bootstrap update gate** in Cell 1 that:
  * refuses to act while any `teledrive*` module is imported (a live ApplicationContext /
    event loop / UI is never hot-swapped) — owner restarts the runtime and re-runs Cell 1;
  * reads a **versioned manifest** (`schema`, `release`, `commit`, `sha256`, `size_bytes`,
    `archive_url`) from the pinned GitHub release `pkg-2026.08.09-m15t07` — a stable public
    endpoint, not an ephemeral Actions URL (requirement 2); the archive itself is a second
    asset of the same release (separate endpoint from the manifest, requirement 5);
  * downloads to updater-owned `.part` files only (requirement 4), verifies size **and**
    sha256 before changing anything (requirement 6), rejects untrusted manifests
    (schema/digest/url-prefix/size), checks the tested-archive layout;
  * atomically replaces only `/content/teledrive_v4.5.zip` and `/content/teledrive-v4.5/`
    (`os.replace`, staged extraction, traversal-safe member check) (requirement 7);
  * preserves `/content/teledrive_runtime`, SQLite, checkpoints, logs, quarantine and all
    Drive data (requirement 8); cleans only updater-owned `.part`/staging leftovers;
  * prints exactly one redacted line: `Package update: SUCCESS|ALREADY CURRENT …` or
    `Package update: REFUSED <reason>; current package unchanged` (requirement 10);
  * Cell 1 then prints `package reference: <release> commit=<12> sha256=<12>` from the
    updater-written state file `/content/teledrive_package_state.json` (requirement 11);
  * REFUSED is never fatal: `resolve_package_zip()` still restores the tested Drive ZIP /
    CI-artifact wrapper exactly as before (documented fallback). No owner hand-editing —
    the gate is generated code (requirement 13).
* Focused tests: `tests/test_package_update.py` (success, already-current,
  crash-convergence without re-download, digest mismatch, truncation, interrupted download,
  unreachable endpoint, 7 untrusted-manifest variants, loaded-runtime refusal before any
  fetch, runtime-data preservation + leftover cleanup, no-secret-leak, lift-safety,
  Cell-1 wiring order) and `tests/test_package_service_determinism.py`.

## 4. Gates — exact outputs (from `python-package/`, venv Python 3.11, lock-pinned deps)

```
$ python -m compileall -q teledrive                    → OK
$ python -m pytest -q tests                            → 402 passed, 1 warning in 12.30s
$ python teledrive_launcher.py --check                 → binding check ok: 24/41 ready actions resolve
$ python -m teledrive.notebook_cells --check           → notebooks are in sync
$ cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb → IDENTICAL
$ python -m teledrive.package_service --build --output teledrive_v4.5.zip
  → 2026-08-09T18:27:18+00:00 tests passed / archive: teledrive_v4.5.zip
  sha256 (twice, identical): 3452060306c38bd4789bb49e28a66a7f48935623ba6915e5fdd4d20be85baa84
```

(`TELEDRIVE_ROOT` was pointed at a workspace temp dir for launcher/build, mirroring CI's
job env; the Gradio 6 deprecation warning is pre-existing and documented since M15-T04.)

`bun run lint` / `bun run build`: **not affected** — zero frontend files changed; CI runs them.

## 5. GitHub verification trail

PR artifact / post-merge run / release digests are verified AFTER PR CI + merge and are
recorded in the session's final Arena report (HEAD, run id+URL, artifact id, artifact
sha256, `gh release` id, manifest content, endpoint reachability). This report is written
pre-merge by design; nothing here claims post-merge facts.

## 6. Honest status

`Code-complete candidate`. Real Colab execution through the official proxy with a live
Telegram + Drive run (M15-T01, owner hand) remains the missing proof. No claim of
`Colab-ready` is made for this change; the update gate itself must also see one real
Colab run before it can be called `Colab-ready`.
