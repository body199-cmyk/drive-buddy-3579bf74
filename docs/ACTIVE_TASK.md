# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

> هذا الملف قفل **معلوماتي** فقط (§7)، وليس mutex runtime. عند إغلاق المهمة يبقى الدليل التاريخي في `CHANGELOG.md` و`PHASE_REPORTS/`، وتصبح الخطوة التالية هي القفل النشط الجديد.

| الحقل | القيمة |
|---|---|
| TASK ID | M17-T02 (شريحة Drive فقط، بتعليمة Brain) |
| العنوان | **إثبات وإظهار أزرار Google Drive السبعة** — قلب 6 أفعال إلى `tested=True` ببراهين handler-level (fake-factory عبر بوابة `about().get` الحقيقية) + إصلاح `h_drive_list_folders` (dropdown update payload) |
| الحالة | VERIFIED COMPLETE (نطاق Drive السبعة) — بانتظار مراجعة Brain |
| المالك التنفيذي | LM Arena Agent (نفّذ) → Brain (يراجع التقرير ويقرر الخطوة التالية) |
| المهندس | Brain (M17-T02 DOC) |
| Base SHA | `e097b3d6391c0cb85ac785c605ea76f017d23f0b` (= رأس PR #26؛ `origin/main`=37377cb حينها وPR #26 ما زال OPEN — انحراف موثق: الشرط تحقق بالمحتوى لا بالدمج؛ صفر فروق كود منتج) |
| الفرع | `arena/019febba-drive-buddy-3579bf74` (فرع الجلسة المثبَّت من المنصة — اسم DOC `arena/m17-t02-drive-actions` غير قابل للاستخدام، نفس انحراف M16-T01) |
| فتح بتاريخ (UTC) | 2026-08-10 |
| النطاق | `action_registry.py` (6 قلوب فقط) · `handlers.py` (سطران) · 3 ملفات اختبار (2 معدَّل + 1 جديد) · الذاكرة · `docs/PHASE_REPORTS/PHASE_M17_T02.md` (+مؤشر python-package) |
| خارج النطاق | كل المحمي (notebooks, telegram_auth, queue/transfer, database/migrations, lockfiles, workflows, package.json, Release) · locale (لم تُحتَج) · `UI_ACTION_INVENTORY.md` (ليس في قائمة §5) · M17-T03/T04/React · باقي أولويات T02 (P2–P6) |
| الدليل الرئيسي | بوابة Drive `19 passed` · بوابة T02 الخماسية `69 passed` · كامل `462 passed` · launcher `32/42 ready` · smoke عربي ناجح للسبعة · التقرير في `docs/PHASE_REPORTS/PHASE_M17_T02.md` |
| الخطوة السابقة (مُغلَقة) | M17-T01 — جرد 42 إجراءً (PR #26؛ بانتظار دمج المالك له) |
| الخطوة التالية | **STOP — بانتظار مراجعة Brain ودمج المالك؛ M17-T02-REST (Dashboard/Logs/Settings/Export/Recovery) وT03/T04 لا تبدأ إلا بموافقة صريحة** |

## قاعدة الاستخدام

- OTP و 2FA مشروطان دائمًا بحالة آلة الحالة الحية في الإقلاع وفي كل إعادة رسم.
- كل زر ظاهر له مسار تحكم فعلي أو يكون مخفيًا/معطَّل بوضوح (`common.unavailable`).
- لا تدّعِ `Colab-ready` — الإصدار المثبَّت `pkg-2026.08.09-m15t07` منشور على main HEAD لكنه لم يُستهلك من Colab حقيقي بعد (M15-T01 بيد المالك).
- إذا اختلف `Base SHA` هنا عن `git rev-parse HEAD` عند بدء جلسة لاحقة، فالملف متقادم ويجب إعادة التدقيق.
- الحالة الصادقة للمشروع: `Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.` — 26/42 إجراءً جاهزًا ظاهرًا، 16/42 مخفيًا عمدًا بانتظار proofs.
- الحالات المسموحة: `PLANNED`, `ACTIVE`, `VERIFIED COMPLETE`, `PARTIALLY COMPLETE`, `FAILED`, `BLOCKED`, `CANCELLED`.
