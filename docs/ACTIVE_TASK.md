# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

> هذا الملف قفل **معلوماتي** فقط (§7)، وليس mutex runtime. عند إغلاق المهمة يبقى الدليل التاريخي في `CHANGELOG.md` و`PHASE_REPORTS/`، وتصبح الخطوة التالية هي القفل النشط الجديد.

| الحقل | القيمة |
|---|---|
| TASK ID | M15-T07 |
| العنوان | إصلاح CI بعد الدمج (بناء حزمة `main` run 65) + مسار تحديث حزمة Colab دستوري وآمن |
| الحالة | ACTIVE — بوابات Python المحلية كلها خضراء (`402 passed` + launcher + notebooks sync/IDENTICAL + بناء أرشيف مُعاد إنتاجه)؛ CI على الـPR والتحقق ما بعد الدمج (run + artifact + release) يُثبَّت في تقرير الجلسة النهائي |
| المالك التنفيذي | LM Arena Agent |
| المهندس | Brain (ClickUp DOC — M15-T07) |
| Base SHA | `333cd753c51b8c56fd1a48a1f7924c44b28e1290` (طابق `origin/main` وHEAD عند البدء) |
| الفرع | `arena/019fe79f-drive-buddy-3579bf74` (الفرع الجانبي الثابت لهذه الجلسة — لا يُنشأ فرع آخر) |
| فتح بتاريخ (UTC) | 2026-08-09 |
| النطاق | `python-package/teledrive/package_service.py`، `python-package/teledrive/notebook_cells.py`، المخرجات المولَّدة (`python-package/notebook/TeleDrive.ipynb`، `public/TeleDrive.ipynb`، `python-package/teledrive/colab_cells.json`)، `python-package/tests/{test_telegram_flow_contract,test_package_update,test_package_service_determinism}.py`، `python-package/docs/PHASE_REPORTS/PHASE_M15_T07.md`، `docs/{CHANGELOG,TODO,KNOWN_ISSUES,ACTIVE_TASK,AI_HANDOFF}.md` |
| خارج النطاق (لم يُمس) | `.github/workflows/**`، `drive_auth.py`، `auth_manager.py`، `app_context.py`، `services.py`، `app.py`، `ui.py`، `telegram_auth.py`، `telegram_client.py`، `transfer_manager.py`، `requirements.lock`، `bun.lock`، كل الواجهة الأمامية |
| السبب الجذري (run 65) | اختبار قِلِق إحصائيًا: sentinel القصير `abc` اصطدم عشوائيًا بـUUID4 للأحداث (`abc91a3a-...`) داخل إعادة تشغيل الاختبارات في خطوة البناء — ليس regression منتج |
| الإصلاح | sentinel بطول 32 hex + اختبار regression (48 دورة)؛ `build_archive` حتمي (مدخلات مرتبة + metadata ثابتة)؛ بوابة تحديث Cell 1: manifest من release مثبَّت `pkg-2026.08.09-m15t07` + sha256/حجم + `.part` + استبدال ذري + رفض أثناء تشغيل الـruntime + سطر نتيجة واحد منقّح |
| الدليل الرئيسي | `python-package/docs/PHASE_REPORTS/PHASE_M15_T07.md` + `pytest` = `402 passed` محليًا |
| الخطوة التالية | PR → CI أخضر → دمج → تحقق مستقل من main HEAD وrun ما بعد الدمج وartifact + إنشاء release `pkg-2026.08.09-m15t07` بالأرشيف والـmanifest → تسليم التقرير النهائي بصيغة DOC؛ ثم M15-T01 التشغيلي بيد المالك |

## قاعدة الاستخدام

- OTP و 2FA مشروطان دائمًا بحالة آلة الحالة الحية في الإقلاع وفي كل إعادة رسم.
- كل زر ظاهر له مسار تحكم فعلي أو يكون مخفيًا/معطَّل بوضوح (`common.unavailable`).
- لا تدّعِ `Colab-ready` — التفعيل على Colab حقيقي لم يُختبر بعد (بوابة التحديث الجديدة ضمنًا).
- إذا اختلف `Base SHA` هنا عن `git rev-parse HEAD` عند بدء جلسة لاحقة، فالملف متقادم ويجب إعادة التدقيق.
- الحالة الصادقة للمشروع: `Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.`
- الحالات المسموحة: `PLANNED`, `ACTIVE`, `VERIFIED COMPLETE`, `PARTIALLY COMPLETE`, `FAILED`, `BLOCKED`, `CANCELLED`.
