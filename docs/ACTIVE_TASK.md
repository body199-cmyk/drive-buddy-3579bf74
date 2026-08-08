# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

> هذا الملف قفل **معلوماتي** فقط (§7)، وليس mutex runtime. مهمة واحدة نشطة في كل لحظة.
> عند بدء مهمة: املأ الجدول. عند إغلاقها: انقلها إلى CHANGELOG واضبط الحالة على `NONE`.

| الحقل | القيمة |
|---|---|
| TASK ID | M12-T02 |
| العنوان | تصحيح AI_RULES لترقيم v5.0 + تنظيف docs/ من التلوث + توثيق السبب الجذري لانكسار CI |
| الحالة | ACTIVE |
| المالك التنفيذي | LM Arena Agent |
| المهندس | Brain (ClickUp DOC) |
| Base SHA | ad3a454f40b8d4c8dd051f5ba94ceb0c7cd6c250 |
| الفرع | arena/019fdff4-drive-buddy-3579bf74 |
| فتح بتاريخ (UTC) | 2026-08-08 |
| النطاق | docs/ فقط (AI_RULES.md, KNOWN_ISSUES.md, TODO.md, ACTIVE_TASK.md, AI_HANDOFF.md, CHANGELOG.md, PHASE_13.md) |
| خارج النطاق | .github/**, docs/CONSTITUTION.md, الأرشيف, تقارير PHASE_0-12, python-package/**, public/**, src/**, package.json, bun.lock, AGENTS.md |

> ملاحظة توثيقية 1: اسم الفرع المقترح في DOC كان `arena/M12-T02-docs-hygiene`، لكن جلسة Arena مثبَّتة على الفرع أعلاه ولا تسمح بتبديل الفروع أو إنشاء فرع آخر للعمل نفسه. سُجِّل الانحراف في PHASE_13 وAI_HANDOFF.

> ملاحظة توثيقية 2 (الجزء أ — CI): DOC يقسم المهمة إلى جزء (أ) بيد المالك حصريًا (استبدال ci.yml) وجزء (ب) بيد LM Arena (هذا الجزء). الجزء (أ) لم يُنفَّذ بعد عند كتابة هذا الملف — `runner.temp` لا يزال في السطر 16 من ci.yml. لا أدّعي أن CI أخضر.

## قاعدة الاستخدام

- إذا كانت الحالة `ACTIVE` لمهمة أخرى، لا تبدأ مهمة جديدة قبل إغلاقها أو تعليمها `BLOCKED` بسبب مكتوب.
- إذا اختلف `Base SHA` هنا عن `git rev-parse HEAD`، فالملف متقادم ويجب إعادة التدقيق قبل أي تعديل.
- الحالات المسموحة: PLANNED, ACTIVE, VERIFIED COMPLETE, PARTIALLY COMPLETE, FAILED, BLOCKED, CANCELLED.
