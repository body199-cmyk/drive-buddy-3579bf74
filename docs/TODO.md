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
| M13-T01 | توثيق أول تشغيل CI حقيقي وتحليل نتائج البوابات | VERIFIED COMPLETE | PR #7 merge `61df83e` · run 31243921611 بعد الدمج · PHASE_14 |
| M13-T02 | تدقيق Action Registry زرًا-زرًا (§14) وتصنيف كل الـ41 | VERIFIED COMPLETE | PHASE_15 · `all_specs()=41`, `22 READY`, `6 BLOCKED`, `13 NOT_TESTED`; `299 passed` |
| M13-T03 | إصلاح analyze.select_all وanalyze.clear_selection مع اختبارات binding حقيقية | VERIFIED COMPLETE | PHASE_16 · `24/41 READY` · proof tests في `python-package/tests/test_selection.py` · `306 passed` |
| M13-T04 | مجموعة صغيرة أخرى مثبتة الحاجة من الإجراءات المتبقية (`11 NOT_TESTED`) | PLANNED | لا إصلاح جماعي؛ التقييم حسب الحاجة قبل Colab الحقيقي |
| M14-T01 | إصلاح محتوى الأرشيف الموزَّع: `package_service` يشحن مؤشرات بدل توثيق حقيقي | PLANNED | KNOWN_ISSUES #9 |
| M15-T01 | **المرحلة 10 — تشغيل Colab الحقيقي** (Telegram + Drive + نقل ملف واحد) | PLANNED — بيد المالك | يلزم حساب حي؛ القالب في `docs/PHASE_REPORTS/PHASE_10.md` |

## ملاحظات أمان

- ممنوع تغيير `requirements.lock` أو `bun.lock` في أي بند حالي.
- كل جلسة تنتهي بتحديث: `AI_HANDOFF.md` + `ACTIVE_TASK.md` + `CHANGELOG.md` + `KNOWN_ISSUES.md` + تقرير مرحلة.
- الحالات المسموحة: PLANNED, ACTIVE, VERIFIED COMPLETE, PARTIALLY COMPLETE, FAILED, BLOCKED, CANCELLED.
