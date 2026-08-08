# KNOWN_ISSUES — مشاكل مؤكدة (مع الأدلة)

> تُسجَّل هنا المشاكل المؤكدة بفحص مباشر أو مخرجات أمر فقط. لا شكوك نظرية.
> لا يُحذف بند إلا بعد إثبات الإصلاح في شجرة GitHub.

| # | المشكلة | الدليل | الحالة |
|---|---|---|---|
| 1 | تضارب أرقام الإصدار داخل الحزمة (`config.py` = 3.1.0، `__init__.py` = 1.0.0/2.0) | فحص 2026-08-06 | ✅ مُصلَحة في الحزمة والمولد والنوت‌بوك واللوك |
| 2 | الريبو لا يحوي دستورًا محدَّثًا | مقارنة 2026-08-06 | ✅ مُصلَحة — `docs/CONSTITUTION.md` = v5.0.0 |
| 3 | لا بيت توثيق جذري | `ls` الجذر | ✅ مُصلَحة — ADR-001 |
| 4 | "177 passed" غير مُعاد إثباته بمثبتات `requirements.lock` الحالية | `docs/PHASE_REPORTS/PHASE_9.md` | **مفتوحة** — M13-T01 |
| 5 | Gradio 6.20.0 و`prevent_thread_lock` لم يُبنيا في بيئة حقيقية | PHASE_9 "Not verified" | **مفتوحة** — M13-T01 |
| 6 | README الجذر بهوية قديمة "Drive Buddy" ورابط لريبو آخر | README.md | ✅ مُصلَحة |
| 7 | تحقق حقيقي (Telegram/Drive/نقل) غائب تمامًا | لا دليل Colab في الريبو | **مفتوحة** — M15-T01، بيد المالك |
| 8 | **CI كان يبني `teledrive_v3.1.zip`** بينما `AI_HANDOFF` و`TODO #2` ادّعيا تحديثه إلى v4.5 | شجرة `.github` عند HEAD 4cacc58 = `86abde40`، مطابقة لما قبل PR#3؛ blob `ci.yml` = `5dec51e` | **مفتوحة** — الحل مجهَّز ومتحقق محليًا (sed سطران v4.5)؛ الدفع مُنع: GitHub App بلا صلاحية `workflows` (دليل الطرفية في PHASE_12). يُغلق عند الهبوط في main |
| 9 | **الأرشيف الموزَّع يشحن مؤشرات بدل توثيق**: `INCLUDE_FILES` و`INCLUDE_DIRS` في `package_service.py` تشير إلى ملفات `python-package/` التي صارت مؤشرات سطر واحد بعد ADR-001 | أحجام blobs: `python-package/README.md` وCHANGELOG وHANDOFF وdocs/* كلها 205–454 بايت | **مفتوحة** — M14-T01 |
| 10 | **`launcher --check` يحل 22 إجراءً من 41 فقط** — 19 إجراءً غير جاهز، وحالتها (ميت/غير مطبَّق/غير مختبَر) غير مصنَّفة | مخرجات الجلسة السابقة | **مفتوحة** — M13-T02، §14 |
| 11 | **pytest لم يُشغَّل في جلسة PR#3** — البوابات المسجَّلة كانت compileall + launcher + notebook + cmp فقط | `docs/AI_HANDOFF.md` قائمة البوابات | ✅ أُغلقت في M12-T01 — pytest شُغِّل فعلًا بمثبتات `requirements.lock`: **299 passed in 7.58s** (§9.7) |
| 12 | مخاطرة بنية تحتية: checkpoint تالف في بيئة تشغيل سابقة | رسالة المنصة | خارج الريبو؛ البيئة الحالية نظيفة |
| 13 | **CI لا يبدأ أصلًا (Invalid workflow file) على كل الفروع بما فيها main**: التعليق التوضيحي على run 31241947281 = `Invalid workflow file: .github/workflows/ci.yml#L1 (Line: 16, Col: 23): Unrecognized named-value: 'runner'. Located at position 1 within expression: runner.temp` — سياق `runner` غير متاح في `jobs.<id>.env` | runs 31129230384 (دفعة المالك نفسه، 1 يوم)، 31237246480 (PR#2 merge)، 31239298725 (PR#3 merge)، 31241771183/31240323871 (PR#4 merge) كلها 0s بنفس الفشل؛ آخر run أخضر = 30496659877 بملف blob 1caddeb الذي كان يستخدم `${{ github.workspace }}` | **مفتوحة** — مكتشَفة في M12-T01 أثناء مراقبة CI؛ الإصلاح يتطلب تعديل workflow (ممنوع منصّيًا على الـ App، مثل #8). أوثقها PHASE_12. المقترح: إعادة `TELEDRIVE_ROOT` إلى `${{ github.workspace }}` أو نقل env لمستوى الخطوة (سياق runner متاح هناك) |
