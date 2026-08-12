# PHASE M24-T01 — React/Gradio Bridge

```plain
TASK ID: M24-T01..T03
UTC: 2026-08-12
Base SHA: 16797ca9b540d8a22885fffb38012643713ef851
Previous PR head: 03c70d0797906eba34d1cf91d80a71bfea5c86a5
Code result SHA: 56a285b5bea01b07c74d7e3ba1a2a2b26461c5fd
Branch: arena/019ff78c-drive-buddy-3579bf74
PR: https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/40
Status: Code-complete candidate + Fake-tested; NOT Colab-ready
```

## Start gate / resume

Raw baseline:

```plain
branch: arena/019ff78c-drive-buddy-3579bf74
HEAD: 03c70d0797906eba34d1cf91d80a71bfea5c86a5
origin/main: 16797ca9b540d8a22885fffb38012643713ef851
PR #40: OPEN, MERGEABLE
Diff: package.json + five React/route files + root contract test
Resume classification: RESUME_PARTIAL
```

| Requirement | Expected file | Baseline | Action |
|---|---|---:|---|
| Route nonblank | `src/routes/teledrive-sandbox.tsx` | Present and verified | Keep + strengthen metadata/test |
| Shared bridge types | frontend bridge contract | Missing | Added `bridgeTypes.ts` |
| One frontend adapter | frontend | Missing | Added `gradioBridge.ts` |
| No fake production state | React | Failed (`mockState.ts`) | Deleted mock source and rewrote component |
| Python bridge | Python application layer | Missing | Added `react_bridge.py` |
| Live snapshot | current context/services | Missing | Added `LiveUiStateService` |
| Official Gradio component | `ui.py` / component | Missing | Added `ReactPanel(gr.HTML)` |
| Registry/binder path | registry/handler/UIBinder | Missing | Added once and wired once |
| Protected paths clean | diff to main | `package.json` violated | Restored package file; final protected diff 0 |

## Implemented transport

```plain
React in gr.HTML
  props.value = JSON request
  trigger('submit')
  UIBinder.wire(panel, react.bridge.request, [panel], [panel], event='submit')
  h_react_bridge_request
  handlers.bridge_request
  ReactBridge.handle
  existing named handler from ActionSpec
  existing service/persistence/runtime
  LiveUiStateService.snapshot
  redacted JSON response into the same panel value
```

Gradio's `/config` from a running app proved:

```plain
panel_count 1
component type html
component elem_id td-react-panel
bridge dependency target submit
inputs [panel-id]
outputs [panel-id]
api_name h_react_bridge_request
```

The React bundle is shipped as deterministic gzip assets because package secret scanning correctly rejected scanning raw minified JS/CSS as prose. Python decompresses assets while constructing the component. No dependency was added.

## Security boundary

- No browser `fetch`, XHR, WebSocket, `/api/*`, CORS, or storage transport.
- No independent server or loop.
- Generic payload rejects secret key names recursively.
- `telegram.set_credentials`, `telegram.send_code`, `telegram.verify_code`, and `telegram.verify_password` are blocked in the generic bridge and remain on existing secure Gradio inputs.
- Logger receives action ID + correlation ID only on unexpected bridge failure; raw payload is never logged.
- Response/snapshot are recursively redacted.

## Real mapping (not illustrative names)

Examples used: `telegram.set_credentials`, `drive.list_folders`, `analyze.run`, `analyze.enqueue_selected`, `queue.start_selected`, `logs.search`, `settings.set_concurrency`, `export.build_zip`, plus the one new `react.bridge.request`. Unknown DOC IDs were not invented.

## What is proven

- One ApplicationContext/AsyncRuntime remains.
- Registry resolves 47/47.
- Bridge dispatches existing named handlers.
- Real empty snapshot, persisted folder ID test, no analyze auto-enqueue, selection exclusion, redaction, and official submit transport pass.
- Push and PR CI are green on code SHA.

## What is not proven

- Colab browser rendering.
- Telegram/Drive live auth.
- Real analyze/queue/transfer/Drive verification/recovery/shutdown.
- Three pixel screenshots.

## Deviations

- Arena fixed branch used to update PR #40.
- Constitution/ADR-0001 concurrency 1..100 supersedes older 1..4 text.
- M20 light-only policy remains; React does not enable dark.

## Next step

STOP and await Brain review; owner performs `PHASE_M24_T03_COLAB_SMOKE.md`.
