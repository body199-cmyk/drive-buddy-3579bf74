# TODO — قائمة العمل المفتوح (مرتبة بالأولوية)

> القاعدة: **بند واحد لكل جلسة/commit**. ابدأ من أول بند غير مكتمل. كل بند له TASK ID (§6).
> لا يُعلَّم بند ✅ إلا بدليل في شجرة GitHub، لا بتقرير Agent ولا بـDOC.

| TASK ID | البند | الحالة | الدليل / الملاحظات |
|---|---|---|---|
| M09-T01 | نظام الاستمرارية متعدد الحسابات: حزمة `docs/` الجذرية + مؤشرات سطر واحد | VERIFIED COMPLETE | ADR-001 · PR #2 |
| M10-T01 | توحيد هوية v4.5.0 في الحزمة والمولد والنوت‌بوك والواجهة | VERIFIED COMPLETE | PR #3 · commit 936e78b |
| M10-T02 | توحيد هوية v4.5.0 **في CI** | VERIFIED COMPLETE | commit ff6a484 · run 31243523514 (نجاح Python وFrontend وبناء teledrive_v4.5.zip) |
| M11-T01 | اعتماد دستور v5.0 مرجعًا أعلى في `docs/CONSTITUTION.md` | VERIFIED COMPLETE | PR #4 · commit 01c04d9 |
| M12-T01 | استكمال ملفات §7 الناقصة + أرشفة v4.5 + ADR-002 + إصلاح CI + تصحيح المؤشرات | VERIFIED COMPLETE | PR #5 mrg ad3a454 · run 31243523514 |
| M12-T02 | تصحيح `AI_RULES.md` لترقيم v5.0 + تنظيف `docs/` من التلوث + توثيق السبب الجذري لانكسار CI | VERIFIED COMPLETE | PR #6 mrg 35ba04c · commit ff6a484 |
| M13-T01 | توثيق أول تشغيل CI حقيقي وتحليل نتائج البوابات | VERIFIED COMPLETE | هذا الفرع · run 31243523514 (نجاح الوظيفتين 1m21s) · PHASE_14 |
| M13-T02 | تدقيق Action Registry زرًا-زرًا (§14): `launcher --check` يقول 22/41 جاهزة فقط | PLANNED — الخطوة التالية | حدد الـ19 الباقية: ميتة أم غير مطبَّقة أم غير مختبَرة |
| M14-T01 | إصلاح محتوى الأرشيف الموزَّع: `package_service` يشحن مؤشرات بدل توثيق حقيقي | PLANNED | KNOWN_ISSUES #9 |
| M15-T01 | **المرحلة 10 — تشغيل Colab الحقيقي** (Telegram + Drive + نقل ملف واحد) | PLANNED — بيد المالك | يلزم حساب حي؛ القالب في `docs/PHASE_REPORTS/PHASE_10.md` |

## ملاحظات أمان

- ممنوع تغيير `requirements.lock` أو `bun.lock` في أي بند حالي.
- كل جلسة تنتهي بتحديث: `AI_HANDOFF.md` + `ACTIVE_TASK.md` + `CHANGELOG.md` + `KNOWN_ISSUES.md` + تقرير مرحلة.
- الحالات المسموحة: PLANNED, ACTIVE, VERIFIED COMPLETE, PARTIALLY COMPLETE, FAILED, BLOCKED, CANCELLED.
