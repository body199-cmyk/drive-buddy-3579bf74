# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

> هذا الملف قفل **معلوماتي** فقط (§7)، وليس mutex runtime. عند إغلاق المهمة يبقى الدليل التاريخي في `CHANGELOG.md` و`PHASE_REPORTS/`، وتصبح الخطوة التالية هي القفل النشط الجديد.

| الحقل | القيمة |
|---|---|
| TASK ID | M15-T02 |
| العنوان | إصلاح استيراد حزمة TeleDrive في Colab عند تنزيل GitHub Artifact wrapper |
| الحالة | ACTIVE — بوابات Python المحلية خضراء؛ بانتظار CI الفعلي على الـPR |
| المالك التنفيذي | LM Arena Agent |
| المهندس | Brain (ClickUp DOC) |
| Base SHA | `1f60a37d91abeeb3cba5a0279fcdcf78f49d8264` |
| الفرع | `arena/019fe124-drive-buddy-3579bf74` (الفرع الجانبي الثابت لهذه الجلسة — لا يُنشأ فرع آخر) |
| فتح بتاريخ (UTC) | 2026-08-08 |
| النطاق | `python-package/teledrive/notebook_cells.py`, `python-package/tests/test_restore_package.py`, `python-package/notebook/TeleDrive.ipynb`, `public/TeleDrive.ipynb`, `python-package/teledrive/colab_cells.json`, `docs/RUNBOOK.md`, `docs/{CHANGELOG,TODO,KNOWN_ISSUES,ACTIVE_TASK,AI_HANDOFF}.md`, `docs/PHASE_REPORTS/PHASE_17.md` |
| خارج النطاق | Telegram/Drive auth/UI/queue/transfer manager، `.github/workflows/**`، Releases، `requirements.lock`/`bun.lock`/`requirements.txt`، الدستور، `docs/PHASE_REPORTS/PHASE_M15_T01.md` (تقرير تاريخي لا يُمس)، أي تعديل Gemini خارج هذه القائمة |
| النتيجة | Cell 1 تقبل الأرشيف الحقيقي والغلاف الرسمي (وحتى غلافًا مُعاد تسميته) عبر `resolve_package_zip()` — temp مختلف + نقل ذري + رفض traversal + تحقق بنية قبل الاعتماد؛ 16 اختبارًا جديدًا؛ `322 passed` محليًا |
| الدليل الرئيسي | `docs/PHASE_REPORTS/PHASE_17.md` + `python -m pytest -q tests` = `322 passed in 9.08s` + `notebook_cells --check` in sync + `cmp` IDENTICAL |
| الخطوة التالية | M15-T01 (المرحلة 10 — Colab حقيقي بيد المالك) بعد إثبات الغلاف على Colab فعلي؛ أو M13-T04 |

## قاعدة الاستخدام

- لا تعدّل Telegram أو Drive auth أو UI أو queue أو transfer manager.
- لا تعِد تسمية الغلاف كحل؛ الاكتشاف بالمحتوى + الاستخراج عبر temp هو العقد المثبت.
- لا تدّعِ `Colab-ready` — التفعيل على Colab حقيقي لم يُختبر بعد.
- إذا اختلف `Base SHA` هنا عن `git rev-parse HEAD` عند بدء جلسة لاحقة، فالملف متقادم ويجب إعادة التدقيق.
- الحالة الصادقة للمشروع: `Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.`
- الحالات المسموحة: `PLANNED`, `ACTIVE`, `VERIFIED COMPLETE`, `PARTIALLY COMPLETE`, `FAILED`, `BLOCKED`, `CANCELLED`.
