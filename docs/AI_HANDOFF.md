# AI_HANDOFF — Live handoff

> Latest session only. Historical evidence is under `docs/PHASE_REPORTS/`.

## Session card — M27-T01 Transfer hardening

| Field | Value |
|---|---|
| UTC date | 2026-08-19 |
| TASK ID | `M27-T01` |
| Repository | `body199-cmyk/drive-buddy-3579bf74` |
| Base SHA | `85822af73326d60894bde9737a35672a4aae1e08` |
| Source branch / commit | `arena/m27-t01-final-hardening` / `f6bf28161dc3c632cf27ebef505587493c208142` |
| Pull Request | [#54](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/54) — `MERGED` at `2026-08-19T03:29:45Z` |
| Merge SHA / current main | `e230ce9da90da5b1ea2e43c0879a5930c57f9104` |
| CI | `4/4 SUCCESS`: Python and Frontend on both push and pull request workflows |
| Status | **MERGED + CI-passed + local/fake-tested. Not live-verified.** |
| Honest status | ليس Colab-ready ولا Complete؛ لم تُجرَ جولة Telegram أو Drive أو Colab حية. |

## Changes merged

| محور | التغيير |
|---|---|
| ضغط SQLite | `TransferManager._record_progress()` يقيّد الاستمرار إلى `0.5s` لكل عنصر، مع كتابة فورية في النهاية وحدود المرحلة. |
| عطل المحرك | `TransferManager.run()` يعيد الاستثناء غير الملغى من العامل؛ `QueueManager._on_run_done()` يسجل `transfer run crashed` ويعيد `idle`. |
| القنوات الخاصة | `TelegramService.resolve_entity()` يسخّن cache من dialogs مرة واحدة عند إخفاق lookup فقط؛ أخطاء النقل العابرة تبقى قابلة لمسار retry. و`peer_id()` يكوّن `-100<channel_id>`. |
| failure مترجم | `PrivateChannelUnresolvedError` دائم وغير قابل لإعادة المحاولة، ومفتاحه موجود في `ar.json` و`en.json`. |
| استئناف التنزيل | `download_partial()` يحاذي offset إلى `4096`، يحافظ على `.part`، ويتابع `iter_download(offset=...)`؛ الصور والحالات غير المناسبة تبقى على المسار الكامل. |

## Verification (real output)

| Command or check | Result |
|---|---|
| `python3 -m pytest -q tests/test_m27_hardening.py -v` | `16 passed` |
| `python3 -m pytest -q tests/test_transfer_control.py tests/test_m26_t03_rebased.py -v` | `18 passed` |
| `python3 -m pytest -q tests/test_i18n.py tests/test_no_ad_hoc_loops.py -v` | `5 passed` |
| `python3 -m pytest -q tests` | `734 passed in 34.81s` |
| `python3 -m compileall teledrive` | PASS |
| `python3 teledrive_launcher.py --check` | `binding check ok: 51/51 ready actions resolve` |
| notebook check / `cmp` / package build | PASS / PASS / PASS |
| `pnpm run lint && pnpm run build` | PASS؛ Bun غير متاح محليًا |
| CI PR #54 | كل الفحوص المكتملة الأربع `SUCCESS`؛ [run 32212207136](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32212207136) و[run 32212200555](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32212200555) |

## Safety boundary and next proof

لم تُمس workflows أو lockfiles أو النوتبوكات أو `action_registry.py` أو `handlers.py` أو `services.py` أو واجهات Gradio أو `drive_client.py` أو `progress_tracker.py` ضمن الالتزام المصدر. لا يوجد `asyncio.run()` داخل `teledrive/**`، ولا تنظيف `.part` أو Google Drive في Pause/Stop.

الخطوة التالية للمالك هي تحقق حي من حساب Telegram مخوّل على قناة خاصة، ومن ملف كبير يُوقف ويستأنف من `.part`، ومن وصول Google Drive، ثم جولة Colab نظيفة. نقطة التراجع للوظيفة الجديدة هي revert للـmerge commit `e230ce9da90da5b1ea2e43c0879a5930c57f9104`؛ لا يُتخذ هذا الإجراء إلا عند ظهور فشل حي مثبت.
