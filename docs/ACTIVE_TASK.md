# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

> هذا الملف قفل **معلوماتي** فقط (§7)، وليس mutex runtime. عند إغلاق المهمة يبقى الدليل التاريخي في `CHANGELOG.md` و`PHASE_REPORTS/`، وتصبح الخطوة التالية هي القفل النشط الجديد.

| الحقل | القيمة |
|---|---|
| TASK ID | M17-T01 |
| العنوان | **جرد صادق لكل الأزرار/الإجراءات** — `python-package/docs/UI_ACTION_INVENTORY.md` (42 action × 17 حقلًا)، بلا أي تعديل على كود المنتج (من ملف M17 MASTER، المرجع الأعلى مع الدستور v5.0) |
| الحالة | VERIFIED COMPLETE (نطاق الجرد والتوثيق) — بانتظار مراجعة Brain |
| المالك التنفيذي | LM Arena Agent (نفّذ) → Brain (يراجع التقرير ويقرر T02) |
| المهندس | Brain (M17 MASTER) |
| Base SHA | `4a2dac62e0aa57092100d35a1726d464b742e48c` — تطابق تام مع `origin/main` عند البدء (= merge PR #23 / M16-T01) → `RESUME_VERIFIED` |
| الفرع | `arena/019febba-drive-buddy-3579bf74` (فرع الجلسة المثبَّت من المنصة) |
| فتح بتاريخ (UTC) | 2026-08-10 |
| النطاق | قراءة ملفات الذاكرة العشرة + فحص 13 ملفًا (`action_registry/ui/ui_binder/handlers/app_context/services/drive_auth/drive_folders/queue_manager/transfer_manager` + 3 ملفات اختبار) + إنشاء الـinventory + تشغيل بوابة T01 + تحديث الذاكرة |
| خارج النطاق | أي تعديل على `teledrive/` أو `tests/`، Notebooks، `PKG_RELEASE_TAG`، workflows، lockfiles، `package.json`، Release؛ وM17-T02/T03/T04 كلها حتى موافقة Brain صريحة |
| الدليل الرئيسي | بوابة T01 `61 passed` · كامل `443 passed` · `compileall` OK · launcher `26/42 ready actions resolve` · التقرير الكامل في `docs/PHASE_REPORTS/PHASE_M17_T01.md` |
| الخطوة السابقة (مُغلَقة) | M16-T01 — مُدموجة على main عبر PR #23 (`4a2dac6`) |
| الخطوة التالية | **STOP — بانتظار مراجعة Brain للـinventory وموافقته قبل بدء M17-T02** |

## قاعدة الاستخدام

- OTP و 2FA مشروطان دائمًا بحالة آلة الحالة الحية في الإقلاع وفي كل إعادة رسم.
- كل زر ظاهر له مسار تحكم فعلي أو يكون مخفيًا/معطَّل بوضوح (`common.unavailable`).
- لا تدّعِ `Colab-ready` — الإصدار المثبَّت `pkg-2026.08.09-m15t07` منشور على main HEAD لكنه لم يُستهلك من Colab حقيقي بعد (M15-T01 بيد المالك).
- إذا اختلف `Base SHA` هنا عن `git rev-parse HEAD` عند بدء جلسة لاحقة، فالملف متقادم ويجب إعادة التدقيق.
- الحالة الصادقة للمشروع: `Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.` — 26/42 إجراءً جاهزًا ظاهرًا، 16/42 مخفيًا عمدًا بانتظار proofs.
- الحالات المسموحة: `PLANNED`, `ACTIVE`, `VERIFIED COMPLETE`, `PARTIALLY COMPLETE`, `FAILED`, `BLOCKED`, `CANCELLED`.
