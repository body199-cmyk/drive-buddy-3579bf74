# PHASE 1: CI + runtime path repair

Status: COMPLETE in the working tree — pending push/CI run for GitHub proof.

## Claim being verified

Earlier report claimed the `/content` CI failure was fixed. Phase 0 re-check
below shows the current tree state; the audited GitHub HEAD
(`e91626214a71bc4c3dc60fd13388234962656f06`) predates it.

## Phase 0 — actual repository state

```
git branch --show-current -> edit/edt-88fa160b-c526-43d3-8378-0ad7d0909478
git log -1 --oneline       -> 3572704 Fixed CI Colab path error
git rev-parse HEAD         -> 3572704c4d01c0843678103aa23fbb6117a85f4b (parent of this phase)
PHASE_REPORTS              -> PHASE_0, PHASE_1, PHASE_2_TO_8, PHASE_9, PHASE_B, PHASE_C
grep "QUEUE ="             -> no singleton in teledrive/ (only instance-scoped test fixtures)
grep "ready=True"          -> none (ActionSpec requires implemented/tested/proof_test)
```

Mismatch between the audited GitHub HEAD and this tree: yes — the audited SHA is
older than `3572704`. No mismatch between this report and the tree.

## Files changed

- `python-package/teledrive/config.py`
  - `_default_root(env=None)` — side-effect-free, testable resolution:
    `TELEDRIVE_ROOT` -> writable `/content` -> `tempfile.gettempdir()/teledrive_runtime`.
  - `MOUNTED_PREFIXES`, `MountedRootError`, `is_mounted_drive()`, `assert_local_path()`.
  - Mounted Drive is never auto-selected and is refused when requested.
  - `QUARANTINE_DIR = TEMP_DIR/_quarantine`, `RUNTIME_DIRS`, `all_dirs()` now includes quarantine.
  - `DB_PATH` is validated as local at import.
- `python-package/teledrive/database.py` — `assert_local_path(DB_PATH)` before connecting.
- `.github/workflows/ci.yml` — job env `TELEDRIVE_ROOT: ${{ runner.temp }}/teledrive_runtime`,
  `TELEDRIVE_LANG: en`; new step printing `ROOT`/`DB_PATH` and asserting the root is not `/content`.
- `python-package/tests/test_config.py` — 8 Phase 1 proofs (fallback, explicit root,
  `/content` only when writable, mounted-Drive refusal for root and DB, quarantine in bootstrap).

## Commands and stdout

```
$ python -m compileall -q teledrive
compile_ok

$ TELEDRIVE_ROOT=/tmp/ci_root python -c "from teledrive.config import ROOT, DB_PATH; print(ROOT); print(DB_PATH)"
/tmp/ci_root
/tmp/ci_root/data/teledrive.db

$ TELEDRIVE_ROOT=/tmp/ci_root python -m pytest -q tests
233 passed in 8.90s

$ TELEDRIVE_ROOT=/tmp/ci_root python teledrive_launcher.py --check
binding check ok: 14/41 ready actions resolve

$ python -m teledrive.notebook_cells --check
notebooks are in sync

$ ls /tmp/ci_root/temp
_quarantine

$ TELEDRIVE_ROOT=/content/drive/MyDrive/td python -c "import teledrive.config"
teledrive.config.MountedRootError: TELEDRIVE_ROOT must stay on local disk ...
```

Dependencies used for these runs were the real pins from `requirements.lock`
(gradio 6.20.0, telethon 1.44.0, google-api-python-client 2.198.0, ...).

## Still unverified

- CI run URL/conclusion — requires the push to `main` on GitHub.
- Real Colab launch and single-file smoke test (Telegram/Drive/transfer).

## Next smallest step

Push this phase, capture the GitHub SHA + CI run conclusion, then start Phase 2
(Action contract re-audit) in a separate reply.
