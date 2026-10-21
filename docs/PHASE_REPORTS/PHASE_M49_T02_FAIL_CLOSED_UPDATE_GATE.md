# M49-T02 — Fail closed when Cell 1 cannot verify the current package

**Date:** 2026-10-21  
**Branch:** `fix/colab-stop-on-any-update-refusal`  
**Base:** `3265d97a2d1fa43b3a8c0b6392936970d7ba2824`  
**Status:** Implemented on branch; CI and live Colab verification pending.

## Why this follow-up is required

M49-T01 prevented a stale local ZIP from being restored when the updater refused because TeleDrive modules were already imported. A second stale-package path remained: network errors, missing/untrusted manifests, archive download failures, and SHA-256/size mismatches could also return `REFUSED`, after which Cell 1 continued to `resolve_package_zip()` and restore a cached ZIP.

That behavior cannot guarantee that a fresh runtime starts from the latest published package.

## Change

- Cell 1 now raises a clear error for **every** `outcome == "refused"` before calling `resolve_package_zip()`.
- If the current package cannot be verified, the notebook stops instead of silently using a local or Drive ZIP whose age cannot be proven.
- Successful verified updates and `ALREADY CURRENT` continue normally; the updater still validates manifest trust, archive size, and SHA-256 before changing the package.
- Updated the generator, regression contract, both distributed notebooks, and `colab_cells.json`.

## Verification

- Main currently has M49-T01 merged at `3265d97a2d1fa43b3a8c0b6392936970d7ba2824`.
- CI for M49-T01: [run 39528529651](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39528529651) — SUCCESS.
- Package publication: [run 39528529604](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39528529604) — SUCCESS. Stable release assets were updated; ZIP is 661229 bytes with SHA-256 `a43223c1459e4af11d01a6455a1bfb8fa8ed1f3989a4bae7609edb2f6d86dc70`.
- M49-T02 has not yet run CI. No claim is made that its tests pass until the new PR CI finishes.
- No live Google Colab runtime was operated here, so Telegram login, Drive restore, and a real file transfer remain unverified.

## Closure checklist

1. CI passes `compileall`, `pytest`, launcher checks, notebook generator check, byte-identical notebook comparison, frontend checks, and package build.
2. After merge, publication succeeds and the stable release manifest and ZIP match the same commit and SHA-256.
3. In Colab, restart the runtime and run Cells 1–4. Verify Cell 1 reports `SUCCESS` or `ALREADY CURRENT`; deliberately unavailable update endpoints must produce a clear stop, not restore an older ZIP.
4. Verify both UI URLs and transfer one small real file to Drive before calling the project Colab-ready.
