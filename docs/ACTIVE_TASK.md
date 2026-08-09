# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

> هذا الملف قفل **معلوماتي** فقط (§7)، وليس mutex runtime. عند إغلاق المهمة يبقى الدليل التاريخي في `CHANGELOG.md` و`PHASE_REPORTS/`، وتصبح الخطوة التالية هي القفل النشط الجديد.

| الحقل | القيمة |
|---|---|
| TASK ID | M15-T04 |
| العنوان | تشخيص اتصال Telegram وإعادة بناء واجهة Colab الاحترافية مع الحفاظ على التحكم الحقيقي |
| الحالة | VERIFIED COMPLETE — بوابات Python المحلية كاملة خضراء (pytest 360 passed + launcher + notebooks sync + package build + Gradio smoke حقيقي)؛ بوابتا bun مؤجلتان إلى CI على الـPR (حاجز شبكة الحاوية، PHASE_19 §5) |
| المالك التنفيذي | LM Arena Agent |
| المهندس | Brain (ClickUp DOC) |
| Base SHA | `a8929521359b0eab184e800412d2e0e829b0312a` |
| الفرع | `arena/019fe6c5-drive-buddy-3579bf74` (الفرع الجانبي الثابت لهذه الجلسة — لا يُنشأ فرع آخر) |
| فتح بتاريخ (UTC) | 2026-08-09 |
| النطاق | `python-package/teledrive/ui.py`, `python-package/teledrive/handlers.py`, `python-package/teledrive/progress_tracker.py` (عيب deadlock مثبت — DEVIATION موثق), `python-package/teledrive/locale/{ar,en}.json`, `python-package/tests/test_ui_shell_contract.py`, `python-package/tests/test_drive_connection_gate.py`, `docs/{CHANGELOG,TODO,KNOWN_ISSUES,ACTIVE_TASK,AI_HANDOFF}.md`, `docs/PHASE_REPORTS/PHASE_19.md` |
| خارج النطاق | `.github/workflows/**`، `docs/CONSTITUTION.md`، `docs/CONSTITUTION_V4.5_ARCHIVE.md`، `docs/TeleDrive-v5.md`، `python-package/teledrive/{notebook_cells,action_registry,telegram_auth,telegram_client,services,app,ui_binder}.py`، `python-package/notebook/TeleDrive.ipynb`، `public/TeleDrive.ipynb`، `python-package/requirements.txt`، `python-package/requirements.lock`، `bun.lock`، كل الواجهة الأمامية |
| النتيجة | قشرة Gradio غرافيت RTL افتراضيًا/LTR بشريط علوي وتنقل جانبي و7 صفحات؛ كل مكوّن حقيقي مربوط أو مخفي/معطَّل بوضوح؛ OTP/2FA مشروطان بالحالة الحية في كل render pass؛ تبديل اللغة يحفظ الحالة؛ `360 passed` |
| الدليل الرئيسي | `docs/PHASE_REPORTS/PHASE_19.md` + `pytest` = `360 passed` محليًا |
| الخطوة التالية | دمج الـPR بيد المالك بعد مراجعة SHA والملفات ومخرجات CI · ثم M15-T01 التشغيلي (المرحلة 10 — Colab حقيقي بحساب حي، بيد المالك) أو M13-T04 |

## قاعدة الاستخدام

- OTP و 2FA مشروطان دائمًا بحالة آلة الحالة الحية في الإقلاع وفي كل إعادة رسم.
- كل زر ظاهر له مسار تحكم فعلي أو يكون مخفيًا/معطَّل بوضوح (`common.unavailable`).
- لا تدّعِ `Colab-ready` — التفعيل على Colab حقيقي لم يُختبر بعد.
- إذا اختلف `Base SHA` هنا عن `git rev-parse HEAD` عند بدء جلسة لاحقة، فالملف متقادم ويجب إعادة التدقيق.
- الحالة الصادقة للمشروع: `Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.`
- الحالات المسموحة: `PLANNED`, `ACTIVE`, `VERIFIED COMPLETE`, `PARTIALLY COMPLETE`, `FAILED`, `BLOCKED`, `CANCELLED`.
