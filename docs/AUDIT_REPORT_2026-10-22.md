# تقرير المشاكل والتدقيق الشامل — TeleDrive / Drive Buddy
# Problems & Full Technical Audit Report

**التاريخ / Date:** 2026-10-22
**النوع:** تقرير بالمشاكل (Audit + Problems Report) + إصلاحان آمنان معزولان
**Repository:** https://github.com/body199-cmyk/drive-buddy-3579bf74
**Audited base:** `main` @ `0e22c1a893ac9ed8d76cf0df1cb61c7325fd6617` (2026-10-21 18:42 +0300)
**Auditor branch:** `genspark_ai_developer` (fixes F-01/F-02 only, see §4 and §6)

> ملخص بالعربي: المشروع شغّال كودياً على `main` (876 اختبار ناجح + 18 اختبار جديد = 894)، والحزمة المنشورة لـColab مطابقة لكود البايثون الحالي. أخطر مشكلتين قابلتين للإصلاح وجدتهما في `main` (رفع ملفات "التحميل الشامل" على نفس اتصال Drive مع Telegram بدون قفل، وثغرة SSRF تسمح بتحميل روابط داخلية زي سيرفر metadata بتاع Colab) — **اتصلحوا** في فرع منفصل باختبارات، بدون لمس مسار Telegram. بوابة Vercel **مش شغالة كمنتج**: موجودة كفروع وPRs مفتوحة فقط، وفيها مخاطر أمنية لازم تتراجع قبل أي دمج. **لم يتم** أي تشغيل لـColab أو Telegram أو Drive حقيقي، ولا أي نشر.

---

## Section 1 — Executive Summary

**Overall status.** TeleDrive is a Google-Colab-hosted Python application (Telethon + Google Drive API) with two in-runtime UIs: a Gradio/React panel and a FastAPI "Modern Web Dashboard" (vanilla HTML/JS embedded in `web_dashboard.py`). A separate TanStack Start (React) site in `src/` is a Lovable-era frontend that today contains only a landing page and a sandbox preview of the panel. There is **no `vercel.json`**, no Vercel API, no OAuth, and no server-side portal on `main`.

**Demonstrably implemented (source-verified) on `main`:** Telegram link analysis/selection/queue/transfer to Drive; Drive auth via native Colab credentials; Telegram session vault on Drive; FastAPI dashboard with queue and universal-download endpoints; universal downloader (yt-dlp / gdown / direct HTTP) with cancel, cooperative pause/resume, retry, bulk actions, speed/progress; package build + SHA-256-verified Cell-1 install gate; CI + automatic release on `main`.

**Tested (in this audit, isolated Level 2 only):** 876/876 Python tests on `main` pass; 894/894 after my fixes; `launcher --check` 54/54; notebooks in sync; Vite production build OK; frontend contract tests 34/34; ESLint 0 errors (9 warnings) on `src tests`.

**Biggest confirmed problems.**
1. (Fixed on branch) Universal-download uploads used the single shared, non-thread-safe Drive service **without** the lock the Telegram engine uses → possible corrupted/failed concurrent uploads when both features run at once.
2. (Fixed on branch) No SSRF protection: any URL including `http://169.254.169.254/...` (Colab metadata server) or `http://127.0.0.1:8765/...` was fetched and uploaded to the user's Drive.
3. The FastAPI dashboard binds `0.0.0.0` with **no authentication** (relies entirely on the Colab proxy being private). Acceptable only while it is reachable *only* through Colab's proxy — becomes Critical the moment any public tunnel is attached (which the open portal branches do).
4. Open portal branches/PRs (#128, `feat/auto-colab-tunnel-handoff`) contain security-sensitive designs (header-based auth bypass, `allow_credentials=True`, bearer token printed to notebook output, public Cloudflare quick tunnel). Tunnel branch CI is **failing** (lint).
5. PR #126 (TanStack security bump) **deletes `bun.lock`** while CI runs `bun install --frozen-lockfile` → merge risk for CI.

**Most important unknowns.** Whether anything works in a real Colab runtime today (no Level-3 evidence exists in the repo for the current package); real Telegram throughput; real yt-dlp platform behavior from Colab IPs; whether the Vercel project `abdullah-74f3/teledrive` is publicly reachable and what it serves.

**Can the project safely continue?** Yes — from `main`, in small additive steps. Do **not** merge the portal/tunnel branches as-is.

---

## Section 2 — Repository Inventory

**Branches.** `main` (default) + ~95 remote branches (≈55 `arena/*` agent branches, plus `feat/*`, `fix/*`, `docs/*`). Total commits on `main`: 454.

**Open PRs (verified via `gh pr list`, 2026-10-22):**
| PR | Branch | Purpose | Checks |
|---|---|---|---|
| #128 | `feat/colab-runtime-pairing` | Pairing portal + bearer-token middleware in `web_dashboard.py` | Python ✅ Frontend ✅ Vercel ✅ (preview) |
| #127 | `feat/per-user-colab-control-plan` | Architecture doc | — |
| #126 | `fix/vercel-tanstack-security` | Bump `@tanstack/react-start` to ^1.168.60, **removes `bun.lock`** | ✅ (but see D-07) |
| #125 (draft) | `feat/m52-t01-vercel-portal-foundation` | `/portal` static RTL page + doc | — |
| #121 | `fix/facebook-cookie-download-support` | Optional FB cookies | CI ✅, no live proof |
| #120 | `fix/gemini-audit-release-pipeline` | Build release from `github.sha` | not merged |
| #103 | `arena/a295b500-…` | Old M46 doc PR | stale |
| (no PR) | `feat/auto-colab-tunnel-handoff` | Cloudflare tunnel + handoff token + `HANDOFF_2026-10-21.md` | **CI failing** (Prettier error `src/routes/connect.tsx:73`) |

**Key paths.**
- Notebook: `public/TeleDrive.ipynb` ≡ `python-package/notebook/TeleDrive.ipynb` (byte-identical, generated by `teledrive/notebook_cells.py`).
- Python engine: `python-package/teledrive/` — `app.py`, `app_context.py`, `transfer_manager.py` (875 LOC), `telegram_client.py`, `telegram_auth.py`, `session_vault.py` (1091), `drive_auth.py`, `drive_client.py`, `queue_manager.py`, `handlers.py`, `action_registry.py`, `universal_downloader.py`, `web_dashboard.py` (2365), `package_service.py`, `notebook_cells.py` (1181).
- Tests: `python-package/tests/` (≈95 files, mocks in `tests/mocks/`), `tests/teledrive-sandbox.contract.test.mjs`.
- Frontend: `src/routes/{__root,index,teledrive-sandbox}.tsx`, `src/components/teleDrive/*`, `scripts/build-react-panel.mjs` (builds `react_panel_assets/*.gz`).
- CI/CD: `.github/workflows/ci.yml` (every push/PR), `release-current.yml` (push to `main` on `python-package/**`), `release.yml` (manual). `github/workflows/release.yml` is a **dead duplicate** (wrong directory, never executed).
- Deploy config: `vite.config.ts` via `@lovable.dev/vite-tanstack-config` → nitro, Cloudflare default target. **No `vercel.json`, no `wrangler.*`.**
- Dependencies: `python-package/requirements.lock` (pinned, except `yt-dlp` and `gdown` **unpinned**), `package.json` + `bun.lock`.
- Governance docs: `docs/CONSTITUTION.md`, `AI_RULES.md`, `AI_HANDOFF.md`, `TODO.md`, `KNOWN_ISSUES.md`, `PHASE_REPORTS/*`.

**FastAPI routes (`web_dashboard.py:2059-2172`):** `GET /`, `GET /api/health`, `GET /api/metrics`, `GET /api/state`, `GET /api/logs`, `POST /api/action`, `POST /api/queue/{name}`, `POST /api/start|pause|stop`, `GET /api/universal/tasks`, `POST /api/universal/{start,cancel,pause,resume,retry,bulk,clear}`, `WS /ws`. No auth dependency on any route. No CORS middleware on `main`.

**Published package.** Release `pkg-2026.08.09-m15t07` (stable tag Cell 1 reads): manifest `commit=08363cd…`, `build_run_id=39627612843`, `size_bytes=674316`, sha256 `6b0ede40…`. `git diff 08363cd 0e22c1a -- python-package public` is **empty** → the published package matches current `main` Python source. (Note: `gh release list` shows `pkg-39525758114` as "Latest"; Cell 1 ranks manifests by `build_run_id`, so the stable tag wins — by design.)

---

## Section 3 — Feature Status Matrix

| Feature | Status | Evidence | Missing work | Risk |
|---|---|---|---|---|
| Colab notebook / Cell 1 install gate | IMPLEMENTED, TESTED (L2) | `notebook_cells.py:105-300`, manifest+sha256+size+zip-traversal checks; `test_restore_package.py`, `test_package_update.py` | Fresh-runtime L3 run on current package | Med |
| Google Drive auth | IMPLEMENTED | `drive_auth.py:42-50` native Colab creds | L3 | Low |
| Drive resumable upload | IMPLEMENTED, TESTED (mock) | `drive_client.py:100-157` | L3 large file | Med |
| Telegram auth + vault | IMPLEMENTED, TESTED (mock) | `telegram_auth.py`, `session_vault.py`, ADR-004 | L3 restore after restart | Med (vault = Drive is trust boundary, owner-accepted) |
| Telegram → Drive transfer | IMPLEMENTED, TESTED (mock) | `transfer_manager.py`, `test_transfer_*`, `test_fast_download.py` | L3 throughput & stability | **Protect** |
| Queue / pause / stop / retry | IMPLEMENTED, TESTED (mock) | `queue_manager.py`, `test_queue.py`, `test_transfer_control.py` | L3 | Protect |
| Universal downloader (yt-dlp/gdown/direct) | IMPLEMENTED, PARTIALLY TESTED | `universal_downloader.py`; tests mock yt-dlp/gdown/Drive | Any real download; FFmpeg presence check; size/disk limits | Med |
| UD cancel | IMPLEMENTED (cooperative) | `cancel_task` + hooks; gdown cannot be interrupted mid-call (documented) | — | Low |
| UD pause/resume | IMPLEMENTED (yt-dlp/direct only) | `pause_supported` flag, `_begin_upload` race test | — | Low |
| UD progress/speed | IMPLEMENTED | real bytes from yt-dlp hooks / chunk reads; 85–99% band = upload | Accuracy unverified live | Low |
| UD quality / MP3 | IMPLEMENTED, UNVERIFIED | `fmt_map`, `FFmpegExtractAudio` | FFmpeg not checked before run | Low |
| UD SSRF protection | **BROKEN on main → FIXED on branch** | F-02 | DNS-rebinding/redirect hardening | High→Low |
| UD Drive thread-safety | **BROKEN on main → FIXED on branch** | F-01 | — | High→Low |
| FastAPI dashboard | IMPLEMENTED, TESTED (TestClient) | `test_web_dashboard.py` | Auth (only if exposed beyond Colab proxy) | Med |
| Packaging / release | IMPLEMENTED, VERIFIED (manifest ↔ source) | §2 | PR #120 decision; pin yt-dlp/gdown | Low |
| CI | IMPLEMENTED, green on `main` | runs 39628121525, 39627612669 | CI writes to `main` (`contents: write`) | Low |
| `src/` TanStack site | IMPLEMENTED (landing + sandbox) | build OK | — | Low |
| Vercel portal (`/portal`) | PLANNED / PARTIAL (static page on draft PR #125) | branch diff: 1 route, no fetch, sign-in disabled | Everything functional | — |
| Google sign-in (portal) | PLANNED ONLY | no OAuth code anywhere | — | — |
| Portal ↔ Colab engine | PARTIAL, UNVERIFIED, security-sensitive | PR #128, tunnel branch | see §5 | **High** |
| Vercel deployment | UNVERIFIED | commit status on `0e22c1a`: "Vercel — Deployment has failed"; PR previews report "completed" | Owner access to Vercel logs | Med |

---

## Section 4 — Confirmed Defects and Security Findings

### F-01 — Universal-download uploads bypass the shared Drive lock — **High · Confirmed · FIXED on branch**
- **Location:** `universal_downloader.py` `_run_task` (former `drive_svc.upload_resumable(...)` call); compare `transfer_manager.py:76,286-297,812` and `app_context.py:118-124`.
- **Evidence:** `AppContext` owns ONE `DriveService` wrapping one `googleapiclient` service (httplib2 transport is not thread-safe). `TransferManager` serializes every Drive call with `_drive_lock`, passing `chunk_lock=self._drive_lock` into `upload_resumable`. The universal downloader runs in its own `threading.Thread` and called `upload_resumable` on the *same* `ctx.drive_client` with no lock.
- **Impact:** Running a Telegram transfer and a universal download simultaneously can interleave requests on one HTTP connection → random upload failures, SSL errors, or corrupted responses — **affecting the protected Telegram flow too**.
- **Fix (applied):** `_SharedDriveChunkLock` resolves `ctx.transfer_manager._drive_lock` per chunk (fallback module lock if no TransferManager yet) and is passed as `chunk_lock`; legacy doubles without `chunk_lock` run under the lock for the whole call. Telegram code untouched.
- **Regression risk:** Low. Universal uploads now wait ≤1 chunk (8 MiB) behind Telegram chunks — same contention model Telegram already uses internally. Lock is a plain `threading.Lock` acquired/released per chunk, non-reentrant usage verified (no nested acquisition in `upload_resumable`).
- **Verification:** `tests/test_universal_downloader_safety.py::test_universal_upload_passes_shared_chunk_lock`, `::test_legacy_drive_without_chunk_lock_runs_under_shared_lock`. L3: start a Telegram transfer and a small direct-URL download together in a test runtime; both must complete.

### F-02 — SSRF via universal downloader — **High · Confirmed · FIXED on branch**
- **Location:** `universal_downloader.py` `start_download` (validation was only `startswith("http")`), direct path `urllib.request.urlopen`.
- **Evidence:** Any URL accepted. On Colab, `169.254.169.254` / `metadata.google.internal` is the GCE metadata server; `127.0.0.1:8765` is the unauthenticated dashboard itself. Content is uploaded into the user's Drive.
- **Impact:** Today the dashboard is reachable only by the runtime owner, so practical exploitability is limited (self-SSRF). It becomes significant when the dashboard is exposed via a tunnel/portal (open branches) — anyone with access could pull runtime-internal data into Drive.
- **Fix (applied):** `_url_targets_private_network()` rejects non-global IPs (loopback, RFC1918, link-local, ULA, unspecified, IPv4-mapped), `localhost`, `*.localhost`, `*.internal`, `metadata`, and hostnames resolving to such addresses; refusal happens before any task/Drive access.
- **Residual:** DNS rebinding and server-side redirects to private IPs are not covered (documented in the docstring). Full fix = custom opener that re-validates each redirect + yt-dlp `--match-filter` is out of scope.
- **Verification:** 14 parametrized/unit tests in the new test file.

### F-03 — Dashboard API has no authentication and binds 0.0.0.0 — **Medium (Critical if publicly exposed) · Confirmed**
- **Location:** `web_dashboard.py:85` `BIND_ADDRESS="0.0.0.0"`, routes `2059-2172`.
- **Impact:** Safe only behind Colab's authenticated proxy. Any tunnel (`share=True` Gradio, Cloudflare, ngrok) gives full control: start transfers, read redacted logs, drive universal downloads.
- **Fix:** Before any public exposure, require a per-runtime secret on every `/api/*` and `/ws` route, validated server-side (not header heuristics). Not applied — would change protected flows and the open PR #128 is touching the same code.
- **Verification:** TestClient tests for 401 on every route without token.

### F-04 — Open portal/tunnel branches contain unsafe auth patterns — **High · Confirmed (in unmerged code)**
- **Location:** `feat/colab-runtime-pairing` (PR #128) and `feat/auto-colab-tunnel-handoff`, `web_dashboard.py` middleware.
- **Evidence:** (a) bypass when `Sec-Fetch-Site: same-origin` — a client-controlled header, trivially forged by non-browser clients (tunnel branch narrows it with `Host` suffix checks, also client-controlled); (b) `CORSMiddleware(... allow_credentials=True)`; (c) runtime bearer token `print()`ed to notebook output (persisted in saved notebook output / screenshots); (d) public `trycloudflare.com` quick tunnel; (e) PR #128 diff also removes `bun.lock` (1172 deletions).
- **Fix:** Do not merge. If continued: token required for *all* requests (no header bypass), `allow_credentials=False`, token shown via `getpass`-style ephemeral display or one-time handoff only, never printed persistently.

### D-05 — Unpinned `yt-dlp` / `gdown` + runtime `pip install --upgrade yt-dlp[default]` — **Medium · Confirmed**
- **Location:** `requirements.lock` (last lines), `universal_downloader.py::_ensure_packages`.
- **Impact:** Supply-chain/non-reproducibility; runtime pip upgrade inside a live process can also change shared transitive deps (e.g., `requests`, `urllib3`) used by Google client libs. Intentional (yt-dlp extractors break often), but should be bounded.
- **Fix:** Pin a minimum (`yt-dlp>=2026.x`) and install into an isolated target dir, or run yt-dlp as subprocess. Needs owner decision.

### D-06 — No size / disk limit for universal downloads — **Medium · Confirmed**
- `_run_task` writes to `TEMP_DIR/universal_dl/<id>` with no free-space or max-size check (Telegram path has disk guards). A large/playlist URL (`noplaylist=False`) can fill the Colab disk and break concurrent Telegram transfers. Fix: check `shutil.disk_usage` before and during download; set `noplaylist=True` by default or cap `playlistend`.

### D-07 — PR #126 deletes `bun.lock` while CI uses `bun install --frozen-lockfile` — **Medium · Strongly indicated**
- `git show origin/fix/vercel-tanstack-security:bun.lock` → not present; `ci.yml:95`. PR checks passed, so bun may regenerate silently, but the lockfile loss removes reproducibility. Fix: regenerate `bun.lock` with `bun install` and commit it in the PR.

### D-08 — Vercel status failing on `main` HEAD — **Low/Medium · Confirmed status, cause unknown**
- Commit status for `0e22c1a`: `Vercel: failure — Deployment has failed`. Logs require Vercel access (owner). Likely the nitro Cloudflare-default target / TanStack version (PR #126 rationale). No `vercel.json` exists.

### D-09 — Dead duplicate workflow — **Low · Confirmed**
- `github/workflows/release.yml` (no leading dot) is identical to `.github/workflows/release.yml` and never runs. Remove when convenient.

### D-10 — Root noise files — **Informational**
- `ARENA_GITHUB_TEST.md`, `ARENA_GITHUB_TEST_2.md` are test artifacts; ~55 stale `arena/*` branches.

### D-11 — Drive query string interpolation — **Low · Confirmed**
- `drive_client.py:61,91` builds Drive `q` with f-strings (`name='{name}'`). A folder name with `'` breaks the query. Not an injection into anything dangerous (Drive query language, user's own account). Escape `\\` and `'`.

### Secrets scan — **No real secrets found**
- `git log --all -p` regex scan for Telegram api_hash, Google API keys, GitHub tokens, private keys, OAuth client secrets, bot tokens, StringSession blobs → **0 hits**. No `.session`, creds, cookies or `.env` files ever added. `.env.example` contains only empty placeholders. `.gitignore` excludes `*.session`, `telegram_creds.json`.

---

## Section 5 — Architecture and Integration Gaps

```
Current (main) — works without any portal
┌────────── Google Colab VM (ephemeral) ──────────┐
│ Cell1 verify+install pkg ─ Cell3 Drive auth      │
│ ApplicationContext (ONE)                          │
│  ├ Telethon client ──────────► Telegram MTProto   │
│  ├ DriveService (ONE, locked) ► Google Drive API  │
│  ├ TransferManager / Queue                        │
│  ├ UniversalDownloader ──────► Internet (yt-dlp)  │
│  ├ Gradio+React panel :7860                       │
│  └ FastAPI dashboard  :8765 (no auth)             │
└───────────────▲──────────────────────────────────┘
                │ Colab proxy (*.prod.colab.dev) — authenticated by the user's Google session
          User's browser

Proposed (branches, NOT on main)
Browser ─► Vercel (static TanStack page, /connect) ─► trycloudflare.com tunnel ─► FastAPI :8765
            (no server API, no OAuth, no DB)            (public URL, changes each run)
```

**Gaps.** (1) No server-side portal component exists: Vercel serves static/SSR pages only; there is no API, persistent storage, or OAuth. (2) The engine is reachable only from the Colab proxy URL, which is per-user, per-session and cookie-protected — a Vercel page cannot call it cross-origin. (3) A tunnel makes it reachable but turns F-03 into Critical. (4) Colab sessions end (idle/12h limits) → the "engine" disappears; Vercel cannot start Colab.

**Minimum viable path (no new infrastructure):** keep Colab + its proxy URL as the product; Vercel page acts as a *launcher/guide* (open notebook, explain steps, deep-link). This is honest and zero-risk.

**Next step if remote control is required:** outbound connection *from* Colab to a broker (the worker dials out; nothing is exposed), with a server-side broker that has auth + storage (e.g., Vercel Functions + a hosted DB/queue such as Upstash/Supabase free tiers). Long-running work stays in Colab; Vercel Functions only relay short requests. This requires real OAuth, per-user isolation and is a Large task.

**Long-term reliable/multi-user:** a persistent worker (small VM/container) replaces Colab; costs money and changes Telegram/Drive auth (no native Colab creds → OAuth refresh tokens stored server-side).

---

## Section 6 — Test and Validation Results

| # | Command (exact) | Ran? | Result | Scope/limits |
|---|---|---|---|---|
| 1 | `python3 -m venv .venv && .venv/bin/pip install -r python-package/requirements.lock pytest` | Yes | OK (Python 3.13; CI uses 3.11) | isolated venv |
| 2 | `cd python-package && TELEDRIVE_ROOT=/tmp/td_rt TELEDRIVE_LANG=en ../.venv/bin/python -m pytest -q -p no:cacheprovider tests -x` (main) | Yes | **876 passed** | mocks only |
| 3 | `../.venv/bin/python teledrive_launcher.py --check` | Yes | 54/54 ready actions | binding only |
| 4 | `python -m teledrive.notebook_cells --check` + `cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb` | Yes | in sync / identical | structure |
| 5 | `npx vite build` | Yes | EXIT 0 | build ≠ deploy |
| 6 | `node --test tests/teledrive-sandbox.contract.test.mjs` | Yes | 34 pass / 0 fail | (`node --test tests/` fails only because a dir is passed) |
| 7 | `npx eslint src tests` | Yes | 0 errors, 9 warnings | `eslint .` also scans `.venv/.output` — avoid |
| 8 | Secret regex over `git log --all -p` | Yes | 0 hits | regex-based |
| 9 | `gh release download pkg-2026.08.09-m15t07 -p teledrive_manifest.json` + `git diff 08363cd 0e22c1a -- python-package public` | Yes | manifest commit 08363cd; no source diff to HEAD | rebuilding the ZIP locally timed out; byte-identity of ZIP not re-proven |
| 10 | `gh pr checks 126/128`, `gh run list`, commit status | Yes | see §2, D-08 | |
| 11 | After fixes: full pytest | Yes | **894 passed** (876 + 18 new) | |
| 12 | After fixes: launcher, notebook check, `compileall` | Yes | 54/54, in sync, OK | |

**Levels completed:** Level 1 ✅, Level 2 ✅, **Level 3 ❌ (none)** — no Colab, Telegram, Drive, media platform or Vercel deployment was accessed.

**Manual Level-3 checklist (owner, in a NEW test runtime — do not touch the running one):**
1. Open the notebook from the README link in a fresh runtime → Cell 1 prints manifest commit and "verified". Expected: no REFUSED.
2. Cells 2–4 → Drive connected, `TeleDrive Web Dashboard URL` printed.
3. Telegram: restore vault or log in; analyze a link to your own test channel; transfer one small file to a dedicated test folder → file appears in Drive with correct size.
4. Universal: paste a public direct `.pdf` URL → completes. Paste `http://169.254.169.254/` → refused immediately (F-02).
5. Run step 3 and 4 together → both complete (F-01).
6. MP3: a public, authorized video, quality `audio_mp3` → `.mp3` in Drive (confirms FFmpeg).
7. Cancel a running yt-dlp download → status `cancelled`, no Drive file.
Rollback: close the test runtime; nothing in the working runtime changes.

---

## Section 7 — Previous Work and Outstanding Tasks

| Claim | Verified state |
|---|---|
| Universal downloader (yt-dlp+gdown), quality fallback, MP3 | Present on `main` (`08363cd` and earlier). Mock-tested. Not live-tested. |
| Background jobs, progress, speed, cancel | Present; cancel/pause/retry/bulk via `/api/universal/*` (M52-T02, `08363cd`). |
| Dependency detection fix (gdown) | Present: `_ensure_packages` checks both modules; test `test_ensure_packages_installs_gdown_when_yt_dlp_already_exists`. |
| Packaging guards / manifest verification | Present in Cell 1 + `release-current.yml` (idempotent, no delete). Manifest ↔ source verified. |
| Merged to main | Yes — CI runs 39627612669 / 39628121525 green; publish run 39627612843 green. |
| "595 lint/build checks" | **Not verifiable** — no artifact or log in the repo matches this number. Treat as unverified. |
| M52-T01 Vercel portal foundation | Branch exists, **draft PR #125**, one static route, OAuth/worker/deploy **not implemented**; doc states Vercel linking was blocked by permissions. Later superseded in practice by PR #128 and the tunnel branch (both unmerged). |
| Facebook cookies | PR #121 open, no live proof (KNOWN_ISSUES #83). |
| Release-from-source pipeline | PR #120 open (KNOWN_ISSUES #84). |
| Live Colab proof | Still open (KNOWN_ISSUES #7, #38, #71, #73, #80, #81). |

---

## Section 8 — Prioritized Remediation Plan

| P | Task | Files | Change | Tests | Rollback | Owner needed | Size |
|---|---|---|---|---|---|---|---|
| P0 | ✅ F-01 shared Drive lock | `universal_downloader.py` | done on branch | new tests + full suite | revert commit | Merge approval | S |
| P0 | ✅ F-02 SSRF guard | `universal_downloader.py` | done on branch | new tests | revert commit | Merge approval | S |
| P0 | Freeze tunnel/pairing branches | PR #128, tunnel branch | do not merge; fix F-04 first | 401-on-every-route tests | — | Yes | M |
| P1 | L3 smoke test of current package | none | checklist §6 | manual | close test runtime | Yes | S |
| P1 | Disk/size guard + `noplaylist=True` | `universal_downloader.py` | `shutil.disk_usage` check, abort on threshold | unit tests | revert | No | S |
| P1 | Fix PR #126 lockfile | `bun.lock` | regenerate & commit | CI frontend job | revert | Maybe | S |
| P2 | Pin yt-dlp/gdown floors; isolate runtime upgrades | `requirements.lock`, `_ensure_packages` | min pins | `test_universal_downloader.py` | revert | Decision | M |
| P2 | FFmpeg preflight for `audio_mp3`/merges | `universal_downloader.py` | `shutil.which("ffmpeg")` → clear error | unit | revert | No | S |
| P2 | Decide Vercel role (launcher vs control plane) | docs | ADR | — | — | **Yes** | S |
| P2 | Dashboard auth (only if exposure is approved) | `web_dashboard.py` | token on all routes, no header bypass | TestClient | revert | Yes | M |
| P3 | Remove `github/workflows/`, test MD files, stale branches | repo root | delete | CI | revert | Yes | S |
| P3 | Escape Drive `q` strings | `drive_client.py` | escape `'`/`\` | unit | revert | No | S |

---

## Section 9 — Questions Requiring Owner Input

1. **Is remote control from Vercel actually required, or is "open Colab and use its dashboard" acceptable?** Decides whether any server/broker/DB is built at all.
2. **Single user (you) or public multi-user?** Multi-user needs real OAuth, server-side token storage and is not achievable for free with Colab as the engine.
3. **Do you accept a public tunnel exposing your runtime?** If not, close the tunnel branch.
4. **Can you share the Vercel build log for `dpl_9yTHSqLdx5TuDMdik9TWeFq4yocz`?** Required to fix D-08; I have no Vercel access.
5. **May yt-dlp keep auto-upgrading at runtime?** Trade-off: extractor freshness vs. reproducibility (D-05).

---

## Section 10 — Safe Handoff for the Next AI Coding Agent

- **Repo:** https://github.com/body199-cmyk/drive-buddy-3579bf74 · **Base:** `main` @ `0e22c1a` · **Fix branch:** `genspark_ai_developer`.
- **Architecture:** see §5 diagram. One `ApplicationContext`, one Drive service, one Telethon client, all inside Colab.
- **Protect (do not modify casually):** `transfer_manager.py`, `telegram_client.py`, `telegram_auth.py`, `session_vault.py`, `drive_auth.py`, `drive_client.py`, `queue_manager.py`, `notebook_cells.py` + both notebooks (generated — never hand-edit), `colab_cells.json`, `requirements.lock`, `.github/workflows/*`, `react_panel_assets/*`.
- **Rules from repo governance (`AGENTS.md`):** no force-push to published history; rollback = revert/new PR.
- **Before merging any PR:** `pytest -q tests` (≥894 pass), `teledrive_launcher.py --check` 54/54, `notebook_cells --check`, `cmp` notebooks, `bun run lint`, `bun run build`.
- **Before deploying/publishing:** L3 checklist §6 in a separate runtime.
- **Blockers:** no Colab/Telegram/Drive access from sandboxes; Vercel logs need owner; GitHub App may lack `workflows` permission (KNOWN_ISSUES #15).
- **Recommended next task:** merge the fix PR after review → owner runs L3 checklist → then P1 disk guard.

Checklist:
- [ ] Read `docs/AI_RULES.md`, `docs/CONSTITUTION.md`, this report
- [ ] Confirm `main` HEAD and open PRs again (`gh pr list`)
- [ ] Run the merge gates above locally
- [ ] Never print/commit tokens, cookies, sessions
- [ ] Never restart the owner's running Colab

---

## Section 11 — Exact Next Steps

1. **(Safe now)** Review & merge the PR from `genspark_ai_developer` (F-01, F-02). Release workflow will republish the package automatically after CI.
2. **(Owner)** In a *new* Colab runtime, run the §6 checklist; keep the current runtime untouched.
3. **(Owner decision)** Answer §9 Q1–Q3; until then, leave PR #125/#128 and the tunnel branch unmerged.
4. **(Agent)** Add disk/size guard + FFmpeg preflight in `universal_downloader.py` (P1/P2).
5. **(Agent)** Regenerate `bun.lock` on PR #126; then fix Vercel build using owner-provided logs.
6. **(Agent, after approval)** If remote access is wanted: design outbound-worker broker ADR; implement auth on all dashboard routes first.

---

## Section 12 — Final Answers to the Owner's Questions

- **A. Current state?** Default branch `main`, HEAD `0e22c1a`. Working implementation is on `main`. 7 open PRs (§2). Portal branch exists (draft #125). Release artifact matches current Python source. Internally consistent (tests/notebooks/manifest agree).
- **B. Is Colab workflow safe to continue?** Yes, code-wise. Everything is tested only with mocks; nothing is proven live for the current package. Restarting loses in-memory queue and the running Telethon session (vault on Drive should restore it — unproven live). A fresh runtime can be validated separately without touching the current one. The install mechanism (manifest + SHA-256 + size + traversal checks, fail-closed) is sound.
- **C. Universal downloader end to end?** Controls are wired to real backend actions; cancel works cooperatively (gdown not interruptible mid-call); progress/speed come from real byte counts; files are uploaded to the selected Drive folder. Quality/MP3 are configured but unverified live (FFmpeg not pre-checked). No platform is verified live. SSRF risk existed → fixed on branch.
- **D. Is the Vercel portal usable?** **No.** It builds; preview deploys reported "completed" for PR branches, but `main`'s Vercel status is *failed*. No authentication, no API, no Drive/Telegram linking, no job submission exist on `main`. The pairing/tunnel branches can technically connect a browser to a live runtime but are unproven and carry the F-04 risks.
- **E. Correct architecture?** Short-term: Colab remains the engine and UI; Vercel = launcher/guide. Medium: outbound worker → authenticated broker. Long-term reliable/multi-user: persistent paid worker.
- **F. API/routing config?** No `vercel.json`. Build uses nitro with Cloudflare default target via the Lovable config. No route rewrites, no backend handlers on Vercel. A separate "api" service is **not** genuinely required unless remote control is chosen.
- **G. Highest-priority defects?** Security/reliability: F-01, F-02 (fixed on branch), F-04 (unmerged code). Blocking Vercel only: D-08, D-07. Unreliable downloads: D-05, D-06. Cosmetic: D-09, D-10, D-11.
- **H. Unfinished previous work?** M52-T01 (static only, blocked by Vercel permissions), PR #120 release pipeline, PR #121 FB cookies, live Colab proof (multiple KNOWN_ISSUES), tunnel branch with failing CI and its own `HANDOFF_2026-10-21.md` (on that branch only).
- **I. Free?** Personal use: yes (Colab free tier, Drive quota, Telegram API free, Vercel hobby, GitHub Actions). No paid API or AI dependency in the code. Free Colab has session limits and is not guaranteed; public multi-user use is not realistically free.
- **J. Next?** Step 1 in §11: merge the two isolated safety fixes, then a live test in a separate runtime.
