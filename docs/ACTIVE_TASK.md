# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

> هذا الملف قفل **معلوماتي** فقط (§7)، وليس mutex runtime. مهمة واحدة نشطة في كل لحظة.
> عند بدء مهمة: املأ الجدول. عند إغلاقها: انقلها إلى CHANGELOG واضبط الحالة على `NONE`.

| الحقل | القيمة |
|---|---|
| TASK ID | M13-T01 |
| العنوان | توثيق أول تشغيل CI حقيقي وتحليل نتائج البوابات |
| الحالة | VERIFIED COMPLETE |
| المالك التنفيذي | LM Arena Agent |
| المهندس | Brain (ClickUp DOC) |
| Base SHA | ff6a484abbeae666b9151e0f729ac07b28c57e9c |
| الفرع | arena/019fdfff-drive-buddy-3579bf74 |
| فتح بتاريخ (UTC) | 2026-08-08 |
| النطاق | docs/ فقط (TODO.md, KNOWN_ISSUES.md, AI_HANDOFF.md, ACTIVE_TASK.md, CHANGELOG.md, PHASE_14.md) |
| خارج النطاق | .github/**, docs/CONSTITUTION.md, docs/CONSTITUTION_V4.5_ARCHIVE.md, تقارير PHASE_0-12, python-package/**, public/**, src/**, package.json, bun.lock, AGENTS.md |
| الخطوة التالية | M13-T02 (تدقيق Action Registry زرًا-زرًا وحصر الـ19 إجراءً غير الجاهزة) |

> ملاحظة توثيقية: تم التحقق من نجاح أول تشغيل GitHub Actions حقيقي (run `31243523514` على commit `ff6a484`) واستغرق 1m21s بنجاح كامل للوظيفتين (Python 1m17s, Frontend 16s) وتوليد artifact `teledrive-package`. المهمة مكتملة وموثقة في PHASE_14.

## قاعدة الاستخدام

- إذا كانت الحالة `ACTIVE` لمهمة أخرى، لا تبدأ مهمة جديدة قبل إغلاقها أو تعليمها `BLOCKED` بسبب مكتوب.
- إذا اختلف `Base SHA` هنا عن `git rev-parse HEAD`، فالملف متقادم ويجب إعادة التدقيق قبل أي تعديل.
- الحالات المسموحة: PLANNED, ACTIVE, VERIFIED COMPLETE, PARTIALLY COMPLETE, FAILED, BLOCKED, CANCELLED.
