# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

> هذا الملف قفل **معلوماتي** فقط (§7)، وليس mutex runtime. مهمة واحدة نشطة في كل لحظة.
> عند بدء مهمة: املأ الجدول. عند إغلاقها: انقلها إلى CHANGELOG واضبط الحالة على `NONE`.

| الحقل | القيمة |
|---|---|
| TASK ID | M12-T01 |
| العنوان | إصلاح تعارضات ما بعد ترقية الدستور v5.0 واستكمال بيت الذاكرة |
| الحالة | ACTIVE |
| المالك التنفيذي | LM Arena Agent |
| المهندس | Brain (ClickUp DOC) |
| Base SHA | 4cacc584834a7fc8e0b8ccf36b53ca3808cbab77 |
| الفرع | arena/019fdfc5-drive-buddy-3579bf74 |
| فتح بتاريخ (UTC) | 2026-08-08 |
| النطاق | docs/ + .github/workflows/ci.yml فقط |
| خارج النطاق | كل كود المنتج، النوت‌بوك، الاعتماديات، الواجهة |

> ملاحظة توثيقية 1: اسم الفرع المقترح في DOC كان `task/M12-T01-constitution-v5-reconciliation`، لكن جلسة Arena مثبَّتة على الفرع أعلاه ولا تسمح بتبديل الفروع أو إنشاء فرع آخر للعمل نفسه. سُجِّل الانحراف في PHASE_12 وAI_HANDOFF.

> ملاحظة توثيقية 2 (عائق منصة مؤكد): إصلاح `.github/workflows/ci.yml` (سطران v4.5) مُجهَّز ومتحقق منه محليًا لكن دفعه مُنع: GitHub App بلا صلاحية `workflows` (`git push`: remote rejected — refusing to allow a GitHub App to create or update workflow؛ REST contents API: HTTP 403 Resource not accessible by integration). جزء docs/ من المهمة دُفع. المهمة تبقى ACTIVE حتى هبوط سطرَي CI (بعد إعادة ربط GitHub بصلاحية workflows، أو يدويًا بيد المالك بأمر sed الموثَّق في PHASE_12).

## قاعدة الاستخدام

- إذا كانت الحالة `ACTIVE` لمهمة أخرى، لا تبدأ مهمة جديدة قبل إغلاقها أو تعليمها `BLOCKED` بسبب مكتوب.
- إذا اختلف `Base SHA` هنا عن `git rev-parse HEAD`، فالملف متقادم ويجب إعادة التدقيق قبل أي تعديل.
- الحالات المسموحة: PLANNED, ACTIVE, VERIFIED COMPLETE, PARTIALLY COMPLETE, FAILED, BLOCKED, CANCELLED.
