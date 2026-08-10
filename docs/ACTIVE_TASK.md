# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

> هذا الملف قفل **معلوماتي** فقط (§7)، وليس mutex runtime. عند إغلاق المهمة يبقى الدليل التاريخي في `CHANGELOG.md` و`PHASE_REPORTS/`، وتصبح الخطوة التالية هي القفل النشط الجديد.

| الحقل | القيمة |
|---|---|
| TASK ID | M16-T01 |
| العنوان | **إصلاح Analyze الحي** — `analyze.set_mode` + حقول حسب النمط + تعريب + أخطاء مترجمة (من ملف M16 MASTER، المرجع الوحيد بقرار M16 AUTHORITY) |
| الحالة | VERIFIED COMPLETE — **PR #23 MERGED في main `4a2dac6`** (موافقة Brain) — الخطوة الحية (إعادة النشر + Colab) بيد المالك |
| المالك التنفيذي | LM Arena Agent (نفّذ ودمج) → المالك (إعادة نشر + Colab حي) → Brain (موافقة T02) |
| المهندس | Brain (ClickUp DOC — M16 MASTER) |
| Base SHA | `f8c0ec2de972c6e7a5b14752742cc5ad48e7cc93` (متوقع من MASTER) — HEAD الفعلي عند البدء `612115941af6747fdf4719576cdf10f6fbd21a21` (تغييرات ما بعد f8c0ec2 docs-only فقط: PR #21 + PR #22) |
| الفرع | `arena/019fe96c-drive-buddy-3579bf74` (فرع الجلسة المثبَّت من المنصة — اسم فرع MASTER غير قابل للاستخدام) |
| فتح بتاريخ (UTC) | 2026-08-10T02:45Z |
| النطاق | كتلة Analyze في `ui.py` (بدون `minimum=`/`maximum=` على الحقول الاختيارية، اختيارات مترجمة، حقول حسب النمط، افتراضي `message`) + `DEFAULT_SCAN_MODE`/`MODE_FIELDS`/`fields_for_mode()` في `media_scanner.py` + `ScannerService.mode_fields()` وأخطاء مترجمة (`err.bad_link`/`err.link_invite_unsupported`/`err.scan_*`) في `services.py` + action `analyze.set_mode` + مفاتيح ar/en + الاختبارات (`test_analyze_ui_modes.py` جديد، `test_analyze_ui_contract.py` مشدَّد، سطر `ARGS` في `test_handlers_contract.py`) |
| خارج النطاق | Notebooks، `PKG_RELEASE_TAG`، workflows، lockfiles، `package.json`، Release، أي ملف محمي في M16 MASTER؛ وM16-T02/T03/T04 حتى موافقة Brain |
| الدليل الرئيسي | بوابة T01 `97 passed` · كامل `443 passed` · launcher `26/42 ready` · notebooks identical · package build OK · التقرير الكامل في `docs/PHASE_REPORTS/PHASE_M16_T01.md` |
| الخطوة السابقة (مُغلَقة) | M15-T12: نشر حزمة الـmain الحالية على التاج `pkg-2026.08.09-m15t07` — VERIFIED COMPLETE (run `31345898521`) |
| الخطوة التالية | **بيد المالك:** تشغيل `Publish current TeleDrive package` على `main` (نفس التاج `pkg-2026.08.09-m15t07`) ثم Colab: Restart → Cells 1–4 → اختبار حي بنقل ملف واحد → إرسال المخرجات إلى Brain → **موافقة منفصلة لـM16-T02** (M16-T02/T03/T04 متوقفة) |

## قاعدة الاستخدام

- OTP و 2FA مشروطان دائمًا بحالة آلة الحالة الحية في الإقلاع وفي كل إعادة رسم.
- كل زر ظاهر له مسار تحكم فعلي أو يكون مخفيًا/معطَّل بوضوح (`common.unavailable`).
- لا تدّعِ `Colab-ready` — التفعيل على Colab حقيقي لم يُختبر بعد (بوابة التحديث الجديدة ضمنًا؛ الإصدار الحي منشور لكن لم يُستهلك بعد من Colab حقيقي).
- إذا اختلف `Base SHA` هنا عن `git rev-parse HEAD` عند بدء جلسة لاحقة، فالملف متقادم ويجب إعادة التدقيق.
- الحالة الصادقة للمشروع: `Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.`
- الحالات المسموحة: `PLANNED`, `ACTIVE`, `VERIFIED COMPLETE`, `PARTIALLY COMPLETE`, `FAILED`, `BLOCKED`, `CANCELLED`.
