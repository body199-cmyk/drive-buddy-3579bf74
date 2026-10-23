# Active Task Update — M52-T03 per-task Drive folders and final monitor cell (2026-10-23)

## Current status — draft PR, validation pending

- PR [#136](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/136) is open as a draft on `feat/per-task-drive-folders-monitor-cell`, based on `feat/auto-colab-tunnel-handoff`. It is intentionally not merged to production.
- Universal Downloader now has an independent Drive folder picker. Choosing a folder only affects that downloader task; it does not mutate the shared Telegram/global destination. Folder ID and name are stored on the task and retained for retries.
- The requested monitor cell is appended as the final cell via the canonical notebook generator; both notebook copies and `colab_cells.json` are synchronized. The existing experimental Vercel cell and existing Cell 4 / cleanup behavior were preserved in the generator.
- Regression tests were added/updated for per-task folder selection, retry destination preservation, and notebook cell counts.
- CI run #769 was in progress at the time of this update. No claim is made that pytest or live Colab/Drive transfer succeeded.
- Next: wait for CI, fix any failure, then run a live test with two small files to two distinct Drive folders while Telegram and Universal Downloader run together. Verify both final Drive paths and run the monitor during active transfers. Do not publish a new package before CI passes and owner-run live validation is recorded.

Detailed report: `docs/PHASE_REPORTS/PHASE_M52_T03_PER_TASK_DRIVE_DESTINATIONS_AND_MONITOR_CELL.md`.

---

# Active Task Update — M52-T02 universal downloader controls (2026-10-21)

## Current status — merged and published

Next action: owner-run live Colab test after runtime restart and normal package update/bootstrap; do not claim live behavior until download controls and Drive upload are observed.
- PR [#124](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/124) merged as `08363cdffa4653f95db39e88e0e124022dc86afe`.
- Compare Telegram's per-item pause/resume/stop/retry with the Universal URL Downloader. Added real per-task and bulk manager actions, cooperative pause gates for yt-dlp/direct HTTP, resume, cancel that wakes paused tasks, retry from stored URL/quality/folder, and UI/API wiring.
- gdown pause is deliberately unavailable because the blocking backend has no safe pause callback. Drive upload is not force-cancelled. Retry is a new download, not byte-level resume.
- CI [run #39627612669](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39627612669) passed (`876 passed, 1 warning`); package publication [run #39627612843](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39627612843) passed; release [pkg-2026.08.09-m15t07](https://github.com/body199-cmyk/drive-buddy-3579bf74/releases/tag/pkg-2026.08.09-m15t07) verified, 674316 bytes, SHA-256 `6b0ede407ea2e68af03f93c88041824c9328140bef5bc35e6b45bb069f9a9be6`. Live Colab/Drive test remains pending.
- Detailed report: `docs/PHASE_REPORTS/PHASE_M52_T02_UNIVERSAL_DOWNLOAD_CONTROLS.md`.

---

# Active Task Update — YouTube downloader bot-challenge fallback (2026-10-21)

## Current change

- Updated `python-package/teledrive/universal_downloader.py` to use yt-dlp's documented `sleep_interval_requests` option and retry a YouTube bot/login challenge once with the alternate `tv,web_safari` player profile after the default profile fails.
- Added a regression test in `python-package/tests/test_universal_downloader.py` that simulates a bot challenge on the first attempt and a successful second attempt.
- Rationale: previous changes updated the package but still failed immediately on the first bot challenge. A fallback profile is now attempted automatically without forcing that profile on every YouTube video.
- Safety: user cookies are not collected, logged, or stored in GitHub. If YouTube rejects both attempts due to Colab IP reputation/session checks, software changes alone cannot guarantee access.
- Commits: implementation `48c8eb9962e28d18c7a2f3a7d4b0f3a5f57eed3b`; tests `41eb47c7eee5ac9a3c0db84cefb1c0ca416fe7e5`; test assertion correction `86c5ba58eaf538f416efb57225c1487f1502fef6`.
- Status at writing: CI and release workflow results still pending. Do not mark the issue resolved until the workflow is green and an owner-run Colab test confirms the specific public video downloads successfully.

---

# المهمة النشطة

## بطاقة M48-T01 — أقسام تنقّل مستقلة للوحة الويب الحديثة (جلسة Arena 2026-10-21)

| الحقل | القيمة |
|---|---|
| TASK ID | `M48-T01` |
| العنوان | تحويل لوحة الويب الحديثة من صفحة طويلة إلى أقسام مستقلة، مع تنقل جانبي وسفلي متجاوب، وحفظ كل الوظائف والثيمات والمصادقة الآمنة |
| الأساس | `d6320963e2e8c8b97ea7410e0fd02b537a241ba1` — `main` بعد PR #111 |
| الفرع | `arena/f4d7af29-drive-buddy-3579bf74` |
| التقرير | `docs/PHASE_REPORTS/PHASE_M48_T01_WEB_DASHBOARD_SECTIONS.md` |
| الحالة | **IMPLEMENTED + LOCALLY VERIFIED (`854 passed`); PR/CI/merge in progress** |

---

## بطاقة M46-T03 — مراجعة الواجهتين وإصلاح الصفحة الحديثة والتوزيع (جلسة Arena 2026-10-20)

| الحقل | القيمة |
|---|---|
| TASK ID | `M46-T03` |
| العنوان | أوضاع تحليل قانونية + جدول نتائج في الواجهة الحديثة + بوابة خلية 1 بلا حد API وباختيار الأحدث بـ`build_run_id` + افتراضي الخلية 4 = الواجهتان معًا |
| الأساس | `1f337c4` — main بعد PR #107 |
| الفرع | `arena/955ee77e-drive-buddy-3579bf74` |
| التقرير | `docs/PHASE_REPORTS/PHASE_M46_T03_DUAL_UI_AUDIT_AND_DISTRIBUTION.md` |
| الحالة | **MERGED + CI-PASSED** — PR [#108](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/108) → `d8c22df`; PR CI `39452872933` وmain CI `39453144455` نجاح؛ يبقى نشر الحزمة (dispatch من الوكيل 403) وإثبات Colab الحي بيد المالك |

---

## بطاقة M46-T02 — إصلاح غياب الحديثة وتجمّد Gradio (جلسة Arena 2026-10-19)

| الحقل | القيمة |
|---|---|
| TASK ID | `M46-T02` |
| العنوان | عزل سيرفر الويب عن حلقة التطبيق + تحقق استماع + إطلاق Gradio أولًا/idempotent + بوابة تحديث تتبع أحدث إصدار pkg-* (و الـWorkflow المصحح محفوظ للتبني) |
| الأساس | `106d8f8` — main بعد PR #105/#106 |
| الفرع | `arena/529afe25-drive-buddy-3579bf74` |
| التقرير | `docs/PHASE_REPORTS/PHASE_M46_T02_WEB_DASHBOARD_ISOLATION_AND_DISTRIBUTION.md` |
| الحالة | **FIXED + GATES GREEN محليًا** — العطل أُعيد إنتاجه وأُثبت زواله؛ إثبات Colab الحي بيد المالك بعد الدمج |

---


## بطاقة M46-T01 — Modern Web Dashboard (جلسة Arena 2026-10-19)

| الحقل | القيمة |
|---|---|
| TASK ID | `M46-T01` |
| العنوان | دمج واجهة الويب الحديثة (FastAPI + AJAX Polling) من Drive WebUI Bridge، مع إبقاء Gradio احتياطيًا |
| الأساس | `337c19e7d69a903c1b7c5060e572d17f09ff8f86` — main بعد PR #104 |
| الفرع | `arena/137aa454-drive-buddy-3579bf74` |
| التقرير | `docs/PHASE_REPORTS/PHASE_M46_T01_MODERN_WEB_DASHBOARD.md` |
| الحالة | **IMPLEMENTED + GATES GREEN** — `web_dashboard.py` على الحلقة الواحدة عبر `bridge_request`، خلية 4 بـ `UI_MODE`، `823 passed`، حزمة مختبرة `614404` بايت |

---


## بطاقة الاستئناف — M45-T01 (جلسة Arena 2026-10-19T16:32Z)

| الحقل | القيمة |
|---|---|
| TASK ID | `M45-T01` (استئناف تنفيذ DOC مكتوب ضد baseline قديم) |
| الأساس | `d991cf4783545ee838d3c2eeaf3b98fc0c22cf6f` — main بعد PR #100 |
| الفرع | `arena/3befa0b6-drive-buddy-3579bf74` (**MERGED** عبر PR #104 → main `337c19e`) |
| الحالة | **VERIFIED COMPLETE** — RESUME_VERIFIED؛ الفجوة الحرفية الوحيدة (`serverresent`) أُغلقت باختبارها؛ كل البوابات خضراء (`813 passed`) |
| Release | `pkg-2026.08.09-m15t07` منشور (أحدث manifest من `33bf50d`: sha256 `7774a340…`، `600312` bytes) — KNOWN_ISSUES #79 مغلقة؛ إعادة نشر من `337c19e` بخطوة واحدة بيد المالك (dispatch من الجلسة 403) |

> المهمة الأصلية M45-T01 دُمجت ومنشورة بالفعل (PRs #93/#95/#98/#100). DOC الاستئناف
> افترض أن M44-T01 غير مدمج — هذا غير صحيح للشجرة الحية. لا إعادة تطبيق؛ ما دُوّن
> في تقرير المرحلة §9 هو ما أُضيف فعليًا في هذه الجلسة فقط.

---

| الحقل | القيمة |
|---|---|
| TASK ID | `M45-T04` |
| العنوان | محرك FastTelethon المباشر: 12 اتصال `MTProtoSender` مستقل مباشر إلى داتا سنتر الملف + Pipelining مزدوج لكل اتصال + نافذة 72 قطعة (`36 MiB`) |
| الأساس | `e177dec8503ab37ca3156c5035e918babf4e2265` — main بعد M45-T03 |
| التقرير | `docs/PHASE_REPORTS/PHASE_M45_T04_FASTTELETHON_DIRECT_MTPROTOSENDER_POOL.md` |
