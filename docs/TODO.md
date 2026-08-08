# TODO — قائمة العمل المفتوح (مرتبة بالأولوية)

> القاعدة: **بند واحد لكل جلسة/commit**. ابدأ من أول بند غير مكتمل. كل بند له TASK ID (§6).
> لا يُعلَّم بند ✅ إلا بدليل في شجرة GitHub، لا بتقرير Agent ولا بـDOC.

| TASK ID | البند | الحالة | الدليل / الملاحظات |
|---|---|---|---|
| M09-T01 | نظام الاستمرارية متعدد الحسابات: حزمة `docs/` الجذرية + مؤشرات سطر واحد | VERIFIED COMPLETE | ADR-001 · PR #2 |
| M10-T01 | توحيد هوية v4.5.0 في الحزمة والمولد والنوت‌بوك والواجهة | VERIFIED COMPLETE | PR #3 · commit 936e78b |
| M10-T02 | توحيد هوية v4.5.0 **في CI** | BLOCKED — بسبب منصة | إصلاح `ci.yml` (v4.5) مجهَّز ومتحقق محليًا؛ الدفع مُنع: GitHub App بلا صلاحية `workflows` (الدليل في PHASE_12). يُغلق عند هبوط السطرين في main |
| M11-T01 | اعتماد دستور v5.0 مرجعًا أعلى في `docs/CONSTITUTION.md` | VERIFIED COMPLETE | PR #4 · commit 01c04d9 |
| M12-T01 | استكمال ملفات §7 الناقصة + أرشفة v4.5 + ADR-002 + إصلاح CI + تصحيح المؤشرات | ACTIVE — docs سلِّمت، جزء CI معلَّق على M10-T02 | هذا الفرع |
| M13-T01 | تشغيل البوابات الست كاملة في CI حقيقي + تدقيق Gradio 6.20.0 + فحص الأسرار | PLANNED | يثبت أو ينفي "177 passed"؛ يعتمد على M12-T01 |
| M13-T02 | تدقيق Action Registry زرًا-زرًا (§14): `launcher --check` يقول 22/41 جاهزة فقط | PLANNED | حدد الـ19 الباقية: ميتة أم غير مطبَّقة أم غير مختبَرة |
| M14-T01 | إصلاح محتوى الأرشيف الموزَّع: `package_service` يشحن مؤشرات بدل توثيق حقيقي | PLANNED | KNOWN_ISSUES #9 |
| M15-T01 | **المرحلة 10 — تشغيل Colab الحقيقي** (Telegram + Drive + نقل ملف واحد) | PLANNED — بيد المالك | يلزم حساب حي؛ القالب في `docs/PHASE_REPORTS/PHASE_10.md` |

## ملاحظات أمان

- ممنوع تغيير `requirements.lock` أو `bun.lock` في أي بند حالي.
- كل جلسة تنتهي بتحديث: `AI_HANDOFF.md` + `ACTIVE_TASK.md` + `CHANGELOG.md` + `KNOWN_ISSUES.md` + تقرير مرحلة.
- الحالات المسموحة: PLANNED, ACTIVE, VERIFIED COMPLETE, PARTIALLY COMPLETE, FAILED, BLOCKED, CANCELLED.
