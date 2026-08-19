# AI_HANDOFF — Live handoff

> Latest session only. Historical evidence is under `docs/PHASE_REPORTS/`.

## Session card — M27-T02 React auto-refresh delivery fix

| Field | Value |
|---|---|
| UTC date | 2026-08-19 |
| Repository | `body199-cmyk/drive-buddy-3579bf74` |
| Branch | `arena/react-auto-refresh-bundle` |
| Base SHA | `50cb7657f07c4e2432e875c0ad36e876e4aac652` |
| Status | **ACTIVE — local/fake-tested. Not live-verified.** |

## Root cause confirmed

`TeleDriveSandbox.tsx` already contained a 2-second silent heartbeat: it gates on `hasActiveTransfer()` and sends `queue.refresh` through the Gradio bridge. Manual Refresh therefore worked because the Python snapshot contract was sound. However, Colab does **not** serve `src/` at runtime: `react_panel.py` decompresses and injects `python-package/teledrive/react_panel_assets/panel.bundle.gz`.

The shipped bundle was inspected directly and contained two `queue.refresh` markers but **no `setInterval` marker**. It was older than the source and omitted the heartbeat, which exactly explains the observed manual-only updates.

## Fix on the branch

| artifact | change |
|---|---|
| `scripts/build-react-panel.mjs` | Durable Vite/Oxc builder creates a minified IIFE named `TeleDriveGradioPanel`, then gzip-compresses JS/CSS deterministically (`mtime=0`). |
| `panel.bundle.gz` / `panel.css.gz` | Rebuilt from `gradioEntry.tsx`; shipped JS now contains `TeleDriveGradioPanel`, `setInterval`, and `queue.refresh`. |
| React contract | New test decompresses the actual shipped asset and fails if it lacks the global API or automatic heartbeat. |

## Verification (real output)

| Command | Result |
|---|---|
| `node --experimental-strip-types --test tests/teledrive-sandbox.contract.test.mjs` | `25 passed` |
| `pnpm run lint && pnpm run build` | PASS; 7 pre-existing Fast Refresh warnings, no errors |
| `python3 -m pytest -q tests` | `734 passed in 37.32s` |
| compileall / launcher / notebooks / cmp / package build | PASS; launcher `51/51` |

## Next exact steps

Run final diff and secret checks; commit, push, and open PR. Merge only after all CI checks pass. **After merge the owner must republish the Colab package from main and restart the runtime**; a currently open Colab session has the old injected bundle and cannot receive this JavaScript change until reloaded from the rebuilt archive.
