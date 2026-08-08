# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

> هذا الملف قفل **معلوماتي** فقط (§7)، وليس mutex runtime. عند إغلاق المهمة يبقى الدليل التاريخي في `CHANGELOG.md` و`PHASE_REPORTS/`، وتصبح الخطوة التالية هي القفل النشط الجديد.

| الحقل | القيمة |
|---|---|
| TASK ID | M13-T02 |
| العنوان | تدقيق Action Registry زرًا-زرًا وتصنيف الإجراءات غير الجاهزة |
| الحالة | VERIFIED COMPLETE |
| المالك التنفيذي | LM Arena Agent |
| المهندس | Brain (ClickUp DOC) |
| Base SHA | `61df83e0912debede0e7e41b8bfde5e6bfabcee9` |
| الفرع | `arena/019fe010-drive-buddy-3579bf74` |
| فتح بتاريخ (UTC) | 2026-08-08 |
| النطاق | `docs/` فقط: `TODO.md`, `KNOWN_ISSUES.md`, `AI_HANDOFF.md`, `ACTIVE_TASK.md`, `CHANGELOG.md`, `PHASE_REPORTS/PHASE_15.md` |
| خارج النطاق | `python-package/**`, `.github/workflows/ci.yml`, `docs/CONSTITUTION.md`, `docs/CONSTITUTION_V4.5_ARCHIVE.md`, `docs/PHASE_REPORTS/PHASE_10.md`, `public/**`, `src/**`, `requirements*.txt`, `bun.lock` |
| النتيجة | جدول كامل لـ41 إجراءً: 22 READY، 6 BLOCKED، 13 NOT_TESTED؛ لا DEAD_CONTROL أو NOT_IMPLEMENTED أو NOT_WIRED |
| الدليل الرئيسي | `docs/PHASE_REPORTS/PHASE_15.md` + `python teledrive_launcher.py --check` = `22/41` + `299 passed in 8.22s` من البيئة المثبتة |
| الخطوة التالية | M13-T03 — DOC إصلاحي منفصل لأصغر مجموعة مترابطة (`analyze.select_all` و`analyze.clear_selection`) |

## قاعدة الاستخدام

- لا تعدّل flags أو تضف handlers/services/tests ضمن M13-T02؛ هذه المهمة تشخيص وتصنيف فقط.
- لا تعتبر أي إجراء من الـ19 غير الجاهزة جاهزًا بسبب وجود declaration أو generic binding test.
- إذا اختلف `Base SHA` هنا عن `git rev-parse HEAD` عند بدء جلسة لاحقة، فالملف متقادم ويجب إعادة التدقيق.
- الحالة الصادقة للمشروع: `Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.`
- الحالات المسموحة: `PLANNED`, `ACTIVE`, `VERIFIED COMPLETE`, `PARTIALLY COMPLETE`, `FAILED`, `BLOCKED`, `CANCELLED`.
