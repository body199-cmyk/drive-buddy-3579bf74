# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

> هذا الملف قفل **معلوماتي** فقط (§7)، وليس mutex runtime. عند إغلاق المهمة يبقى الدليل التاريخي في `CHANGELOG.md` و`PHASE_REPORTS/`، وتصبح الخطوة التالية هي القفل النشط الجديد.

| الحقل | القيمة |
|---|---|
| TASK ID | M13-T03 |
| العنوان | إصلاح `analyze.select_all` و`analyze.clear_selection` مع اختبارات binding حقيقية |
| الحالة | VERIFIED COMPLETE |
| المالك التنفيذي | LM Arena Agent |
| المهندس | Brain (ClickUp DOC) |
| Base SHA | `86005ff6ef5eb55ddfd639f306c85ff17acadc4c` |
| الفرع | `arena/019fe024-drive-buddy-3579bf74` |
| فتح بتاريخ (UTC) | 2026-08-08 |
| النطاق | `python-package/teledrive/action_registry.py`, `python-package/tests/test_selection.py`, `docs/` |
| خارج النطاق | كود المنتج في `handlers.py` و`services.py` وباقي الحزمة، `.github/workflows/ci.yml`, `docs/CONSTITUTION.md`, `docs/CONSTITUTION_V4.5_ARCHIVE.md`, `docs/PHASE_REPORTS/PHASE_10.md`, `public/**`, `src/**`, `requirements*.txt`, `bun.lock` |
| النتيجة | إثبات صحة التنفيذ الحالي في كود المنتج، إضافة 5 اختبارات إثبات حقيقية في `test_selection.py`، وترقية إجرائي التحديد إلى `READY` (`24/41` جاهزة في `launcher --check` و `306 passed` في pytest) |
| الدليل الرئيسي | `docs/PHASE_REPORTS/PHASE_16.md` + `python teledrive_launcher.py --check` = `24/41` + `306 passed in 8.66s` من البيئة المثبتة |
| الخطوة التالية | M13-T04 — مجموعة صغيرة أخرى مثبتة الحاجة من الإجراءات المتبقية (`11 NOT_TESTED`) أو الانتقال إلى Colab الحقيقي (M15-T01) |

## قاعدة الاستخدام

- لا تعدّل flags أو تضف handlers/services/tests خارج نطاق إجرائي التحديد المحددين في M13-T03.
- لا تعتبر أي إجراء من الـ17 غير الجاهزة جاهزًا بسبب وجود declaration أو generic binding test.
- إذا اختلف `Base SHA` هنا عن `git rev-parse HEAD` عند بدء جلسة لاحقة، فالملف متقادم ويجب إعادة التدقيق.
- الحالة الصادقة للمشروع: `Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.`
- الحالات المسموحة: `PLANNED`, `ACTIVE`, `VERIFIED COMPLETE`, `PARTIALLY COMPLETE`, `FAILED`, `BLOCKED`, `CANCELLED`.
