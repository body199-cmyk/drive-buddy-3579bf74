# TODO — قائمة العمل المفتوح (مرتبة بالأولوية)

> القاعدة: **بند واحد لكل جلسة/commit**. ابدأ من أول بند غير مكتمل. كل بند له TASK ID (§6).
> لا يُعلَّم بند ✅ إلا بدليل في شجرة GitHub، لا بتقرير Agent ولا بـDOC.

| TASK ID | البند | الحالة | الدليل / الملاحظات |
|---|---|---|---|
| M09-T01 | نظام الاستمرارية متعدد الحسابات: حزمة `docs/` الجذرية + مؤشرات سطر واحد | VERIFIED COMPLETE | ADR-001 · PR #2 |
| M10-T01 | توحيد هوية v4.5.0 في الحزمة والمولد والنوت‌بوك والواجهة | VERIFIED COMPLETE | PR #3 · commit 936e78b |
| M10-T02 | توحيد هوية v4.5.0 **في CI** | BLOCKED — بانتظار المالك (صلاحية workflows) | إصلاح `ci.yml` (3 أسطر) مجهَّز ومتحقق محليًا وموثَّق في PHASE_12 وPHASE_13 وDOC M12-T02؛ الدفع مُنع: GitHub App بلا صلاحية `workflows`. يشمل: v3.1→v4.5 (سطران) + `runner.temp`→`github.workspace` (سطر). يُغلق عند هبوط الأسطر الثلاثة في main بيد المالك |
| M11-T01 | اعتماد دستور v5.0 مرجعًا أعلى في `docs/CONSTITUTION.md` | VERIFIED COMPLETE | PR #4 · commit 01c04d9 |
| M12-T01 | استكمال ملفات §7 الناقصة + أرشفة v4.5 + ADR-002 + إصلاح CI + تصحيح المؤشرات | PARTIALLY COMPLETE — docs سلِّمت ودُفعت (PR #5 مدموج ad3a454)؛ جزء CI معلَّق على M10-T02 | PHASE_12 |
| M12-T02 | تصحيح `AI_RULES.md` لترقيم v5.0 + تنظيف `docs/` من التلوث + توثيق السبب الجذري لانكسار CI | ACTIVE — هذا الفرع | PHASE_13 |
| M13-T01 | تحليل نتائج أول تشغيل CI حقيقي وإصلاح ما يظهر | PLANNED — يعتمد على أول تشغيل أخضر فعلي | لا معنى له قبل إصلاح ci.yml (M10-T02)؛ البوابات لم تُشغَّل على GitHub ولا مرة منذ إدخال `runner.temp` |
| M13-T02 | تدقيق Action Registry زرًا-زرًا (§14): `launcher --check` يقول 22/41 جاهزة فقط | PLANNED | حدد الـ19 الباقية: ميتة أم غير مطبَّقة أم غير مختبَرة |
| M14-T01 | إصلاح محتوى الأرشيف الموزَّع: `package_service` يشحن مؤشرات بدل توثيق حقيقي | PLANNED | KNOWN_ISSUES #9 |
| M15-T01 | **المرحلة 10 — تشغيل Colab الحقيقي** (Telegram + Drive + نقل ملف واحد) | PLANNED — بيد المالك | يلزم حساب حي؛ القالب في `docs/PHASE_REPORTS/PHASE_10.md` |

## ملاحظات أمان

- ممنوع تغيير `requirements.lock` أو `bun.lock` في أي بند حالي.
- كل جلسة تنتهي بتحديث: `AI_HANDOFF.md` + `ACTIVE_TASK.md` + `CHANGELOG.md` + `KNOWN_ISSUES.md` + تقرير مرحلة.
- الحالات المسموحة: PLANNED, ACTIVE, VERIFIED COMPLETE, PARTIALLY COMPLETE, FAILED, BLOCKED, CANCELLED.
