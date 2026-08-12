# PHASE M24-T03 — Live Colab smoke record

```plain
TASK ID: M24-T03
UTC: 2026-08-12
Reviewed code SHA: 56a285b5bea01b07c74d7e3ba1a2a2b26461c5fd
Status: NOT RUN — owner credentials and a real Colab browser are required
Secrets exposed: no
Colab-ready: NO
Complete: NO
```

## Sandbox evidence (not a substitute for Colab)

A pinned Gradio 6.20.0 server launched on `0.0.0.0:7860`, `share=False`, with one ApplicationContext. `/config` showed the `td-react-panel` HTML component and its official submit dependency. A `queue.refresh` request through Gradio client returned status `ok` and the actual disconnected/empty state. This proves the bridge transport in the sandbox only.

## Owner checklist — pending

Record sanitized output/evidence for every row. Do not paste credentials.

| # | Step | Result | Evidence |
|---:|---|---|---|
| 1 | Run current Notebook Cells 1..7 in order from reviewed main SHA | NOT RUN | — |
| 2 | Confirm React renders inside the same Gradio process, not a static page/server | NOT RUN | — |
| 3 | First render Arabic RTL with actual disconnected/empty state | NOT RUN | — |
| 4 | Telegram secure Gradio fields: chip stays disconnected until real authorization succeeds | NOT RUN | — |
| 5 | Native Colab Drive auth → `about.get()` → live list/select folder | NOT RUN | — |
| 6 | Bounded real Telegram analyze; candidates from service | NOT RUN | — |
| 7 | Manual real candidate selection → explicit enqueue → SQLite, no auto-start | NOT RUN | — |
| 8 | Start: disk reserve → `.part` → local size → resumable upload → Drive verification | NOT RUN | — |
| 9 | Live progress/queue/redacted logs visible in React | NOT RUN | — |
| 10 | Pause/resume/restart/reconcile; no auto-resume | NOT RUN | — |
| 11a | Sanitized screenshot 1280×768 | NOT RUN | — |
| 11b | Sanitized screenshot 768×768 | NOT RUN | — |
| 11c | Sanitized screenshot 390×844 | NOT RUN | — |
| 12 | Shutdown + checkpoint/recovery + handoff recorded | NOT RUN | — |

## Acceptance rule

Do not change this report to `Colab-ready` unless every required live step succeeds. Do not mark `Complete` until one real file is transferred and verified on Drive, then shutdown/recovery/logs/handoff all pass. A screenshot, build, CI run, mock, or sandbox Gradio request is insufficient.

## Current blocker

Owner-side live accounts/Colab browser are unavailable to Arena. This is an environment boundary, not hidden by disabling or simulating success. See KNOWN_ISSUES #46–#48.
