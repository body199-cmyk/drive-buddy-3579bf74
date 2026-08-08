# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

> هذا الملف قفل **معلوماتي** فقط (§7)، وليس mutex runtime. عند إغلاق المهمة يبقى الدليل التاريخي في `CHANGELOG.md` و`PHASE_REPORTS/`، وتصبح الخطوة التالية هي القفل النشط الجديد.

| الحقل | القيمة |
|---|---|
| TASK ID | M15-T03 |
| العنوان | إصلاح تدفق تسجيل Telegram داخل Colab: API، الهاتف، OTP، و2FA شرطي |
| الحالة | VERIFIED COMPLETE — بوابات محلية كاملة خضراء (pytest 338 passed + launcher + notebooks sync + package build + lint + build) |
| المالك التنفيذي | LM Arena Agent |
| المهندس | Brain (ClickUp DOC) |
| Base SHA | `8fbd18595c3b6d32d20f1c3319d0b551dee4dfa6` |
| الفرع | `arena/019fe1f1-drive-buddy-3579bf74` (الفرع الجانبي الثابت لهذه الجلسة — لا يُنشأ فرع آخر) |
| فتح بتاريخ (UTC) | 2026-08-08 |
| النطاق | `python-package/teledrive/ui_binder.py`, `python-package/teledrive/handlers.py`, `python-package/teledrive/ui.py`, `python-package/teledrive/redaction.py`, `python-package/tests/test_telegram_flow_contract.py`, `python-package/tests/test_no_hardcoded_credentials.py`, `docs/{CHANGELOG,TODO,KNOWN_ISSUES,ACTIVE_TASK,AI_HANDOFF}.md`, `docs/PHASE_REPORTS/PHASE_18.md` |
| خارج النطاق | `.github/workflows/**`، `docs/CONSTITUTION.md`، `docs/CONSTITUTION_V4.5_ARCHIVE.md`، `docs/TeleDrive-v5.md`، `python-package/teledrive/telegram_auth.py`، `python-package/teledrive/telegram_client.py`، `python-package/teledrive/notebook_cells.py`، `python-package/teledrive/action_registry.py`، `python-package/notebook/TeleDrive.ipynb`، `public/TeleDrive.ipynb`، `python-package/requirements.txt`، `python-package/requirements.lock`، `bun.lock` |
| النتيجة | لوحة OTP تظهر حصريًا عند `CODE_REQUESTED` وتُغلق بعد التحقق؛ لوحة 2FA تظهر حصريًا عند `PASSWORD_REQUIRED` بعد `SessionPasswordNeededError` حقيقي؛ 15 اختبار contract + اختبار فحص الأسرار الثابت؛ 338 passed محليًا |
| الدليل الرئيسي | `docs/PHASE_REPORTS/PHASE_18.md` + `pytest` = `338 passed` محليًا |
| الخطوة التالية | M15-T01 التشغيلي (المرحلة 10 — Colab حقيقي بحساب حي، بيد المالك) أو M13-T04 |

## قاعدة الاستخدام

- OTP و 2FA مشروطان دائمًا بحالة آلة الحالة الحية.
- لا تدّعِ `Colab-ready` — التفعيل على Colab حقيقي لم يُختبر بعد.
- إذا اختلف `Base SHA` هنا عن `git rev-parse HEAD` عند بدء جلسة لاحقة، فالملف متقادم ويجب إعادة التدقيق.
- الحالة الصادقة للمشروع: `Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.`
- الحالات المسموحة: `PLANNED`, `ACTIVE`, `VERIFIED COMPLETE`, `PARTIALLY COMPLETE`, `FAILED`, `BLOCKED`, `CANCELLED`.
