# AI_HANDOFF — Live handoff

> Latest session only. Historical evidence is under `docs/PHASE_REPORTS/`.

## Session card — M27-T01 Transfer hardening

| Field | Value |
|---|---|
| UTC date | 2026-08-19 |
| TASK ID | `M27-T01` |
| Repository | `body199-cmyk/drive-buddy-3579bf74` |
| Branch | `arena/m27-t01-final-hardening` |
| Base SHA | `85822af73326d60894bde9737a35672a4aae1e08` (`origin/main`) |
| HEAD before work | `85822af73326d60894bde9737a35672a4aae1e08` |
| HEAD after work | تغييرات محلية غير ملتزم بها؛ راجع `git rev-parse HEAD` بعد إنشاء الالتزام |
| Status | **ACTIVE — local/fake-tested. Not live-verified.** |
| Honest status | ليس Colab-ready ولا Complete؛ لم تُجرَ جولة Telegram أو Drive أو Colab حية. |

## Changes applied

| محور | التغيير |
|---|---|
| ضغط SQLite | `TransferManager._record_progress()` يقيّد الاستمرار إلى `0.5s` لكل عنصر، مع كتابة فورية في النهاية وحدود المرحلة. |
| عطل المحرك | `TransferManager.run()` يعيد الاستثناء غير الملغى من العامل؛ `QueueManager._on_run_done()` يسجل `transfer run crashed` ويعيد `idle`. |
| القنوات الخاصة | `TelegramService.resolve_entity()` يسخّن cache من dialogs مرة واحدة، و`peer_id()` يكوّن `-100<channel_id>` قبل تخزين العنصر. |
| failure مترجم | `PrivateChannelUnresolvedError` دائم وغير قابل لإعادة المحاولة، ومفتاحه موجود في `ar.json` و`en.json`. |
| استئناف التنزيل | `download_partial()` يحاذي offset إلى `4096`، يحافظ على `.part`، ويتابع `iter_download(offset=...)`؛ الصور والحالات غير المناسبة تبقى على المسار الكامل. |

## Verification (real output)

| Command | Result |
|---|---|
| `python3 -m pytest -q tests/test_m27_hardening.py -v` | `16 passed` |
| `python3 -m pytest -q tests/test_transfer_control.py tests/test_m26_t03_rebased.py -v` | `18 passed` |
| `python3 -m pytest -q tests/test_i18n.py tests/test_no_ad_hoc_loops.py -v` | `5 passed` |
| `python3 -m pytest -q tests` | `734 passed in 34.81s` |
| `python3 -m compileall teledrive` | PASS |
| `python3 teledrive_launcher.py --check` | `binding check ok: 51/51 ready actions resolve` |
| `python3 -m teledrive.notebook_cells --check` / `cmp` | PASS / PASS |
| `python3 -m teledrive.package_service --build --output teledrive_v4.5.zip` | PASS؛ حُذف ناتج التحقق المحلي بعدها |
| `pnpm run lint && pnpm run build` | PASS؛ Bun غير متاح محليًا |

## Files and safety boundary

المتوقع تضمينه: `telegram_client.py` و`telegram_links.py` و`media_scanner.py` و`transfer_manager.py` و`queue_manager.py` و`errors.py` وملفا locale و`tests/test_m27_hardening.py` ووثائق M27. لا تعديل على workflows أو lockfiles أو النوتبوكات أو `action_registry.py` أو `handlers.py` أو `services.py` أو واجهات Gradio أو `drive_client.py` أو `progress_tracker.py`. لا يوجد `asyncio.run()` داخل `teledrive/**`، ولا تنظيف `.part` أو Google Drive في Pause/Stop.

## Next exact step

نفّذ تدقيق diff أخيرًا بما فيه الأسرار والحالة، وأنشئ الالتزام بالرسالة المتفق عليها. ادفع الفرع وافتح PR إلى `main`، ثم راقب CI فقط. ادمج رسميًا إذا وفقط إذا كانت جميع فحوص CI خضراء. نقطة التراجع قبل الالتزام هي `85822af73326d60894bde9737a35672a4aae1e08`.
