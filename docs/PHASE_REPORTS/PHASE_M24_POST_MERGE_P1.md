# PHASE M24 post-merge P1 — null safety + request ordering

```plain
TASK ID: M24 post-merge audit P0/P1
UTC: 2026-08-12
Base SHA: 504ec5e547b7b5270d3cd00fbdb69909bbe69621
Branch: arena/019ff805-drive-buddy-3579bf74
Status: Code-complete candidate + Fake-tested; NOT Colab-ready; NOT Complete
```

## Scope

Apply the post-merge Brain audit P1 fixes that were **not** present on merged main
`504ec5e` (the previously claimed local commit `acd6029` did not exist in git).

## Changes

### P0 route blank

- Already fixed since M24 merge: `src/routes/teledrive-sandbox.tsx` returns
  `<TeleDriveSandbox />`. Contract test 01 still guards against regression.
- No code change required.

### P1 null safety

Nested optional chaining on every `LiveUiState` read path in
`TeleDriveSandbox.tsx` and `viewModel.ts`:

```ts
state?.telegram?.status ?? "—"
state?.drive?.status ?? "—"
state?.folder?.id
state?.folder?.name ?? "—"
state?.drive?.quotaUsed ?? null
state?.drive?.quotaLimit ?? null
(state?.drive?.status?.toLowerCase?.() ?? "") !== "connected"
(candidate.status ?? "").toLowerCase()
(row.status ?? "").toLowerCase()
Number(row.progress) || 0
state?.folder?.id  // enqueueBlockReason
```

### P1 request ordering

In `TeleDriveSandbox.run()`:

```ts
const latestRequest = useRef(new Map<string, string>());
const requestId = newRequestId();
latestRequest.current.set(actionId, requestId);
// ... await bridge.request ...
if (latestRequest.current.get(actionId) !== requestId) return null;
// only then: setLiveState / success|error notice / clear busy
```

Prevents a slower older response from overwriting a newer one and from flashing
a success notice before `status === "ok"` of the latest request.

### Concurrency (documented non-change)

Audit text that asked for 1..4 was **not** applied. Constitution v5.0 + ADR-0001
remain the higher authority: range 1..100, default 2, mandatory warning above 8.

### Bundle rebuild

`python-package/teledrive/react_panel_assets/panel.bundle.gz` and `panel.css.gz`
rebuilt from the updated React source via esbuild IIFE
(`global-name=TeleDriveGradioPanel`, `mount` export verified under node:vm).
Gzip uses `mtime=0` for determinism. No new runtime dependency added to
`package.json` (esbuild invoked via `npx` only for the one-shot rebuild).

## Contract tests added

- **19** — nested `LiveUiState` fields use optional chaining; forbids
  `state?.telegram.` / `state?.drive.` / `state?.folder.` one-level patterns.
- **20** — `run()` owns a `latestRequest` Map and drops stale responses.

## Local gates (raw)

```plain
$ node --test tests/teledrive-sandbox.contract.test.mjs
20 tests, 20 pass, 0 fail

$ npx tsc --noEmit
exit 0

$ npm run lint
0 errors; 7 warnings (pre-existing react-refresh + one unused prettier directive)

$ npm run build
client + SSR + Nitro PASS

$ python teledrive_launcher.py --check
binding check ok: 47/47 ready actions resolve
```

Python pytest suite was not re-run end-to-end in this sandbox (no project venv /
gradio install). Launcher binding check and frontend contracts cover the changed
surface. CI on the PR is authoritative for the full Python matrix.

## Protected paths

Zero modifications to:

- notebooks / `notebook_cells.py` / `colab_cells.json`
- `telegram_auth.py` / `queue_manager.py` / `transfer_manager.py`
- `database.py` / `migrations.py`
- `requirements.*` / `bun.lock` / `package.json` / `.github/workflows/**`

## Network boundary

Unchanged and still enforced by contract test 15: no `fetch(` / `XMLHttpRequest(` /
`WebSocket(` / `localStorage` / `sessionStorage` / `/api/` in production React
bridge sources.

## Honest status

| Claim | Result |
|---|---|
| MERGED baseline | yes — work starts from `504ec5e` |
| P1 null safety | applied + tested |
| P1 request ordering | applied + tested |
| Bundle includes fixes | yes (`TeleDriveGradioPanel.mount` verified) |
| Colab-ready | **NO** |
| Complete | **NO** |
| Live transfer / Drive verify | **NOT PROVEN** |
| Screenshots 1280/768/390 | **NOT RUN** |

## Next step

Open PR from `arena/019ff805-drive-buddy-3579bf74` → `main`. Await Brain review.
Owner still owns the 12-step Colab smoke in `PHASE_M24_T03_COLAB_SMOKE.md`.
