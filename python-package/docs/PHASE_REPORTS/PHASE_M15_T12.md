# PHASE M15-T12 — Publish the current main package for the Colab updater

**TASK ID:** `M15-T12`
**Title:** Publish the current main package for the Colab updater
**Executor:** LM Arena Agent · Brain (engineer / code author / reviewer)
**Canonical repo:** `https://github.com/body199-cmyk/drive-buddy-3579bf74`
**UTC date:** 2026-08-10T01:01Z
**Fixed branch (Arena session):** `arena/019fe912-drive-buddy-3579bf74`
**Base SHA (origin/main at start):** `5fd064a3e1934fe47934e004b808bb7b05d9eebc`
**Current main SHA used for build:** `f8c0ec2de972c6e7a5b14752742cc5ad48e7cc93`
**Status:** `VERIFIED COMPLETE` (publication verified) — final product status stays **Code-complete candidate / NOT Colab-ready**

> **Authority:** Task spec M15-T12. The old pinned release `pkg-2026.08.09-m15t07` targeted `10b5d3b…` (M15-T07), which did **not** contain M15-T11. This task republishes the **same tag** (so the Cell-1 updater keeps using it) with assets built from current main, so Cell 1 can update the local Colab package without a manual ZIP upload.

---

## 1. Why this task existed

- Cell 1 of the Colab notebook is pinned to the stable endpoint `/releases/download/pkg-2026.08.09-m15t07/teledrive_v4.5.zip` and `teledrive_manifest.json`.
- The old release on that tag pointed at `10b5d3b…` (M15-T07 tree) — it predated the M15-T11 scoped Telegram analysis UI and bounded scan implementation.
- A new tag would make the updater ignore the package, so this task **reused the same tag** and replaced its assets from current main, exactly as the spec required.
- This task only publishes the current package; it does **not** prove Telegram, Drive, analyze, enqueue, or transfer in a live Colab runtime.

## 2. Files / source the package was built from (current main `f8c0ec2`)

Verified present in the build tree by the workflow gate and locally:

- `python-package/teledrive/media_scanner.py` — contains `ScanRequest`
- `python-package/teledrive/services.py`
- `python-package/teledrive/handlers.py`
- `python-package/teledrive/ui.py`
- `python-package/tests/test_scoped_scan.py` — contains `test_handler_passes_bounded_scan_request`
- `python-package/tests/test_analyze_ui_contract.py`

M15-T11 implementation (ScanRequest; message/range/latest/chat modes; bounded max 1000; media type filtering; selection table; select-all/clear/enqueue-selected; Analyze UI controls) is therefore included in the published package.

## 3. Workflow used

File: `.github/workflows/release-current.yml` (manual-only, `workflow_dispatch`).

Because the Arena GitHub App lacks `workflows:write` (KNOWN_ISSUES #15), the owner applied the workflow file to `main` via GitHub's web editor:

- `09c170d` `Create release-current.yml`
- `0b561df` `Update release-current.yml`
- `f8c0ec2` `Update release-current.yml` — added `actions/setup-python@v5` with `python-version: "3.11"` and `cache: pip` (the missing pin that caused earlier failures; same Python used by the passing CI workflow).

The workflow:
1. Checkout `main`, record exact `CURRENT_SHA`.
2. Verify M15-T11 files + proof greps (fail-closed).
3. Pin Python 3.11 (setup-python) → install pinned deps + pytest.
4. Run constitution gates: `compileall`, `pytest -q tests`, `teledrive_launcher.py --check`, `notebook_cells --check`, `cmp` notebooks.
5. Build archive via `package_service --build`.
6. Verify archive layout (`teledrive-v4.5/requirements.lock` present).
7. Measure exact archive bytes (sha256 + size).
8. Generate manifest from the exact archive bytes in the same job.
9. Validate manifest against the exact archive bytes.
10. Delete-then-create the release (idempotent `|| true`), publish the two assets to `pkg-2026.08.09-m15t07` targeting `CURRENT_SHA`.
11. Verify public manifest + archive through the unauthenticated download endpoints (digest/size/commit re-checked from the bytes actually served).

## 4. Publication evidence (from GitHub API, this session)

- Publish run: **`31345898521`** → `conclusion=success` · workflow `Publish current TeleDrive package` · event `workflow_dispatch` · `headSha=f8c0ec2de972c6e7a5b14752742cc5ad48e7cc93`
  - https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/31345898521
- Release: `pkg-2026.08.09-m15t07`
  - `target_commitish=f8c0ec2de972c6e7a5b14752742cc5ad48e7cc93` (current main)
  - `draft=false`, `prerelease=false`, `published_at=2026-08-10T01:00:50Z`
  - https://github.com/body199-cmyk/drive-buddy-3579bf74/releases/tag/pkg-2026.08.09-m15t07
- Assets (Releases API, both `uploaded`):
  - `teledrive_v4.5.zip` — **212474 bytes** — `digest: sha256:167d25d468f1a624f4f1a344d5b7c6531d1eb17f7990daaa891932e4b1c5cce3`
  - `teledrive_manifest.json` — **378 bytes** — `digest: sha256:bdba64a0a920a1f68649119dee9e2dd7a64cbcf488e73f048689fb4cef51b426`
- Release body (set by the workflow): `Current main package. Built from commit f8c0ec2de972c6e7a5b14752742cc5ad48e7cc93 by workflow run 31345898521. Archive sha256=167d25d468f1a624f4f1a344d5b7c6531d1eb17f7990daaa891932e4b1c5cce3 size_bytes=212474. This release is a code-complete candidate and is not Colab-ready until owner-run live proof.`
- **Manifest JSON values** (generated by the workflow from the exact archive bytes; the workflow's internal `Validate manifest against the exact archive` + `Verify public manifest and archive` steps passed, so commit/sha256/size match the uploaded bytes):
  ```json
  {
    "archive_url": "https://github.com/body199-cmyk/drive-buddy-3579bf74/releases/download/pkg-2026.08.09-m15t07/teledrive_v4.5.zip",
    "commit": "f8c0ec2de972c6e7a5b14752742cc5ad48e7cc93",
    "product_version": "4.5.0",
    "release": "pkg-2026.08.09-m15t07",
    "schema": 1,
    "sha256": "167d25d468f1a624f4f1a344d5b7c6531d1eb17f7990daaa891932e4b1c5cce3",
    "size_bytes": 212474
  }
  ```
- Digest/size/commit match: **YES** — the run's fail-closed gates measured the exact built bytes, generated the manifest from those bytes, and the final step re-fetched the public endpoints and asserted `manifest["commit"] == CURRENT_SHA`, `manifest["size_bytes"] == len(archive)`, `manifest["sha256"] == sha256(archive)`. The run concluded `success`. The Releases API digest for the zip asset (`sha256:167d25d4…`) matches the sha256 recorded in the manifest and release body.

## 5. Local reproduction of the gates (this sandbox, Python 3.11)

- `python -m compileall -q teledrive` → OK
- `python -m pytest -q tests` → **419 passed** (1 warning)
- `teledrive_launcher.py --check` → `binding check ok: 25/41 ready actions resolve`
- `python -m teledrive.notebook_cells --check` → `notebooks are in sync`
- `cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb` → OK

## 6. Known sandbox / platform limitations

- The Arena GitHub App has no `workflows:write`, so `.github/workflows/*` could not be pushed by the agent — the owner applied the workflow to `main` via the web editor (same mechanism as KNOWN_ISSUES #15 / earlier M15-T08 fix). No blind retries were made.
- The asset CDN (`release-assets.githubusercontent.com`) is unreachable from this sandbox (egress TLS reset), so the archive bytes cannot be downloaded here for a local hash. The sha256/size/commit are proven by the workflow's own fail-closed byte-identity + public-verification steps (run `success`) and by the Releases API digest — not by a sandbox-side download.
- Real Colab activation of the Cell-1 update gate against the live endpoint is still untested (owner-run, M15-T01).

## 7. Honest status

`Code-complete candidate / NOT Colab-ready`. This task published the current package; it does **not** prove live Telegram/Drive/transfer.

## 8. Mandatory final report (M15-T12)

```plain
GitHub Status:
Commit: SUCCESS (owner applied workflow: 09c170d, 0b561df, f8c0ec2 on main)
Push: SUCCESS (owner) — agent push of .github/workflows was rejected (no workflows:write)
Pull Request: NOT CREATED for the workflow (owner applied via web editor, as KNOWN_ISSUES #15)
Branch (workflow): main (owner-applied)
Base SHA: 5fd064a3e1934fe47934e004b808bb7b05d9eebc
Current main SHA used for build: f8c0ec2de972c6e7a5b14752742cc5ad48e7cc93
Workflow file: .github/workflows/release-current.yml (manual workflow_dispatch)
Workflow PR URL: (none — web editor apply)
Workflow run URL / ID: https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/31345898521 (ID 31345898521)
Workflow conclusion: success
Release: CREATED (replaced on same tag pkg-2026.08.09-m15t07)
Release tag: pkg-2026.08.09-m15t07
Release target SHA: f8c0ec2de972c6e7a5b14752742cc5ad48e7cc93
Assets and sizes: teledrive_v4.5.zip = 212474 bytes; teledrive_manifest.json = 378 bytes
Manifest JSON: see §4 above
Archive sha256: 167d25d468f1a624f4f1a344d5b7c6531d1eb17f7990daaa891932e4b1c5cce3
Archive size_bytes: 212474
Unauthenticated manifest endpoint: https://github.com/body199-cmyk/drive-buddy-3579bf74/releases/download/pkg-2026.08.09-m15t07/teledrive_manifest.json
Unauthenticated archive endpoint: https://github.com/body199-cmyk/drive-buddy-3579bf74/releases/download/pkg-2026.08.09-m15t07/teledrive_v4.5.zip
Digest matches exact uploaded bytes: YES (workflow public-verify step + Releases API digest)
Tests and gates: constitution gates ran in-run (compileall, 419 passed, launcher 25/41, notebook sync, cmp, package build + archive layout + byte identity + public verify) and reproduced locally on Python 3.11
Documentation commit / PR URL: docs updated in this session (see handoff)
Known limitations: agent lacks workflows:write (owner applied); CDN body not fetchable from sandbox; Colab live (M15-T01) pending
Honest status: Code-complete candidate / NOT Colab-ready
Next action: owner-run live Colab proof (M15-T01)
Operation error: earlier publish runs failed on "Run constitution gates" because Python was not pinned (defaulted to 3.12); fixed by adding actions/setup-python@v5 with 3.11 in commit f8c0ec2
```

No secret, token, signed artifact URL, or credential appears anywhere in this report.
