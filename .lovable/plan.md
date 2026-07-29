## Verified current state (checked against the source repo, not assumed)

- `main` is at `24b5557a0ce55722ff873203298faf45aae77eeb` ("Implemented phase 2-8 in TeleDrive"), public, 166 tracked files. Same stack as this project (TanStack Start + shadcn), so a file-level copy is clean.
- `teledrive_launcher.py` does `from teledrive.bootstrap import bootstrap`, but `bootstrap.py` only defines `run()` → **ImportError on every launch, including `--check`**. Confirmed.
- Worse (not in the brief): `app.launch()` itself calls `bootstrap.run()`, so even after fixing the import the launcher would build **two** ApplicationContexts. The launcher also defaults to `share=True` (it passes `share=not args.no_share`).
- Both `public/TeleDrive.ipynb` and `python-package/notebook/TeleDrive.ipynb` are **identical stale v2 notebooks**: 7 cells, titled "TeleDrive v2", OAuth wording, blind `shutil.rmtree(TEMP_DIR)` in the maintenance cell, no native Colab Drive auth, no test cell. They do already use `share=False`.
- `teledrive/colab_cells.json` is a separate v3.1 draft that **does** use native Colab auth but **does** contain `share=True`, and is not rendered into either `.ipynb`.
- No `.github/` directory at all → CI is missing.
- `public/teledrive-package.zip` is tracked as a static binary artifact.

Note on repositories: I can only write into this Lovable project. The copy lands here, and this project is then connected to your new GitHub repo via GitHub sync; the source `body199-cmyk/drive-buddy` is never written to.

## Step 1 — Copy the source repository into this project

Download all 166 files at commit `24b5557a` into this project (excluding `.lovable/`, `bun.lock` conflicts resolved in favour of source). Then verify the copy: file count, and a SHA-256 manifest diff against the GitHub blobs. Report any unexpected difference and stop if the tree does not contain the Phase 2–8 implementation.

## Step 2 — Repair the single launcher

- `from teledrive import bootstrap` / `ctx = bootstrap.run()`.
- Split `app.py` so the context is created once and passed in: `launch(ctx, share=False, inline=True)` (keep a back-compat path that bootstraps only when no context is given). The launcher creates the one context and hands it to `launch`.
- Invert the share default: `--share` opt-in, default `share=False`. Keep `--no-share` as a no-op alias for compatibility.
- `--check` must work with no credentials: bootstrap in check mode, resolve every `action_registry.ready_specs()` service path, print the count, exit 0.
- New `tests/test_launcher.py`: module imports, `--check` runs without credentials, exactly one `ApplicationContext` is constructed in a normal launch (patched Gradio), default launch is `share=False`.

## Step 3 — One notebook source, two generated notebooks

- Make `teledrive/notebook_cells.py` the single authority (it reads/replaces `colab_cells.json` and exposes `build_notebook() -> dict`), plus `python -m teledrive.notebook_cells --write` to emit both files.
- Generate byte-identical `python-package/notebook/TeleDrive.ipynb` and `public/TeleDrive.ipynb` with exactly the 7 required cells: (1) mount Drive + restore tested archive into local `/content` + install from `requirements.lock` with SQLite kept on local disk; (2) bootstrap dirs/logging/migrations/WAL; (3) hidden-input Telegram API ID/hash + native Colab Drive auth verified by `about().get()`; (4) one `ApplicationContext` with the verified Drive service and Telegram config injected, then `launch(ctx, share=False)` with no auto-resume; (5) redacted handoff/snapshot; (6) `python -m pytest -q tests` with real stdout/stderr and cell failure on non-zero; (7) safe maintenance — checkpoint, delete only temp files belonging to verified `Uploaded` items, quarantine unknown/incomplete files, clean SQLite close. Optional cells 8/9 only if `CONSTITUTION.md` requires them, and they reuse the existing context/clients.
- `tests/test_notebook.py` parses both `.ipynb` files and asserts: title says v3.1, no OAuth-JSON upload, no pasted OAuth code, no `share=True`, no blind `rmtree`, expected cell count/order, and the two files are identical to the generator output.

## Step 4 — Native Drive only

Audit `drive_auth.py` / `drive_client.py` for `InstalledAppFlow`, `client_secret.json`, `drive_token.json` and remove any remaining paths. Keep only `colab_auth.authenticate_user` + `google.auth.default` + `build("drive","v3", cache_discovery=False)`. Status is `Connected` only after `about().get()` succeeds; the verified service is injected into the single context. Add an import/build smoke test plus fake tests for gating, folder ops, quota, and account-switch guidance.

## Step 5 — Telegram runtime and UI/runtime boundary

Verify against `CONSTITUTION.md` and repair as needed: exact `phone_code_hash` preserved, invalid code keeps the flow alive, expired code clears the hash, 2FA reuses the same client with no new code, explicit cooldown-protected resend, no secrets anywhere in logs/snapshots/checkpoints/ZIPs. Keep `ui.py` layout-only with every control wired through `UIBinder.wire()` + `binder.assert_complete()`; add a test that fails on any unwired visible control. Prove the UI auth path writes the AUTH event to local SQLite (fake connector test). Real Telegram success stays unclaimed until you run the controlled smoke test.

## Step 6 — Packaging and the React landing page

`PackageService.build_tested_archive()` runs the full fake suite first and fails closed; the archive contains the current Python package, notebook source, `requirements.lock`, docs and tests, and excludes secrets, `.git`, runtime DBs, sessions, tokens and temp files. The download button serves the generated archive; `public/teledrive-package.zip` is untracked only after the generated replacement is proven. Frontend stays a reference/download page with no runtime logic — its stale v2/OAuth/"running" copy is rewritten to honest v3.1 native-Colab wording, and the route gets proper `head()` metadata.

## Step 7 — CI and verification

Add `.github/workflows/ci.yml` (push + PR, no `continue-on-error`): `python -m compileall teledrive`, `python -m pytest -q tests`, `npm run build`, `npm run lint`; plus a separate clean-environment job installing `requirements.lock` and running the minimal `gradio.Blocks` build smoke.

Locally I will run and paste real output for `compileall`, `pytest -q tests`, `bun run build`, `bun run lint`, `python teledrive_launcher.py --check`, and the Gradio build smoke in a clean venv. I will not fabricate Colab, Telegram, or Drive results.

## Step 8 — Honest reporting

Update `PROJECT_CONTEXT.md`, `python-package/CHANGELOG.md`, `python-package/HANDOFF.md`, and add `python-package/docs/PHASE_REPORTS/PHASE_9.md` with actual commands and redacted stdout/stderr, and separate statuses for: fake tests, Gradio build smoke, Telegram real integration, Drive real integration, controlled Colab transfer. Expected final status is **code-complete, real integrations unverified** until you run the Colab smoke test.

## Stop conditions

I stop and report instead of guessing if the copy differs unexpectedly, Gradio cannot import/build in the sandbox, a service path fails to resolve, any test fails, or any credential would be required from you.
