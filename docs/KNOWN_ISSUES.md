# KNOWN_ISSUES — مشاكل مؤكدة (مع الأدلة)

> تُسجَّل هنا المشاكل المؤكدة بفحص مباشر أو مخرجات أمر فقط. لا شكوك نظرية.
> لا يُحذف بند إلا بعد إثبات الإصلاح في شجرة GitHub.

| # | المشكلة | الدليل | الحالة |
|---|---|---|---|
| 1 | تضارب أرقام الإصدار داخل الحزمة (`config.py` = 3.1.0، `__init__.py` = 1.0.0/2.0) | فحص 2026-08-06 | ✅ مُصلَحة في الحزمة والمولد والنوت‌بوك واللوك |
| 2 | الريبو لا يحوي دستورًا محدَّثًا | مقارنة 2026-08-06 | ✅ مُصلَحة — `docs/CONSTITUTION.md` = v5.0.0 |
| 3 | لا بيت توثيق جذري | `ls` الجذر | ✅ مُصلَحة — ADR-001 |
| 4 | "177 passed" غير مُعاد إثباته بمثبتات `requirements.lock` الحالية | `docs/PHASE_REPORTS/PHASE_9.md` | **مفتوحة** — 299 passed محليًا وفي CI، لكن بيئة Colab الحية لم تُختبر بعد (M15-T01) |
| 5 | Gradio 6.20.0 و`prevent_thread_lock` لم يُبنيا في بيئة حقيقية | PHASE_9 "Not verified" | **مفتوحة** — M15-T01 |
| 6 | README الجذر بهوية قديمة "Drive Buddy" ورابط لريبو آخر | README.md | ✅ مُصلَحة |
| 7 | تحقق حقيقي (Telegram/Drive/نقل) غائب تمامًا | لا دليل Colab في الريبو | **مفتوحة** — M15-T01، بيد المالك |
| 8 | **CI كان يبني `teledrive_v3.1.zip`** بينما `AI_HANDOFF` و`TODO #2` ادّعيا تحديثه إلى v4.5 | شجرة `.github` عند HEAD 4cacc58 = `86abde40`، مطابقة لما قبل PR#3؛ blob `ci.yml` = `5dec51e` | ✅ **مُصلَحة** — commit `ff6a484` حدّث `ci.yml` إلى `teledrive_v4.5.zip`؛ تحققت في run `31243523514` ورُفعت الحزمة كـartifact |
| 9 | **الأرشيف الموزَّع يشحن مؤشرات بدل توثيق**: `INCLUDE_FILES` و`INCLUDE_DIRS` في `package_service.py` تشير إلى ملفات `python-package/` التي صارت مؤشرات سطر واحد بعد ADR-001 | أحجام blobs: `python-package/README.md` وCHANGELOG وHANDOFF وdocs/* كلها 205–454 بايت | **مفتوحة** — M14-T01 |
| 10 | **`launcher --check` كان يحل 22 إجراءً من 41 فقط** — الـ19 الباقية كانت بلا تصنيف موثق | baseline `61df83e`: `22/41`. التدقيق الكامل في `PHASE_15.md`، وفي **M13-T03 (PHASE_16)** أُضيفت اختبارات إثبات لإجرائي التحديد ورُقِّيا إلى READY فصارت النتيجة: `24/41 ready actions resolve` (6 `BLOCKED` و11 `NOT_TESTED`) | ✅ **مُغلقة في M13-T02 ومُحدَّثة في M13-T03** — 24 READY، 6 BLOCKED بسبب native Colab/Drive live gate، و11 NOT_TESTED، ولا dead/missing/unwired |
| 11 | **pytest لم يُشغَّل في جلسة PR#3** — البوابات المسجَّلة كانت compileall + launcher + notebook + cmp فقط | `docs/AI_HANDOFF.md` قائمة البوابات | ✅ أُغلقت في M12-T01 — 299 passed محليًا وفي CI (run 31243523514) |
| 12 | مخاطرة بنية تحتية: checkpoint تالف في بيئة تشغيل سابقة | رسالة المنصة | خارج الريبو؛ البيئة الحالية نظيفة |
| 13 | **CI لا يبدأ أصلًا (Invalid workflow file) على كل الفروع بما فيها main**: التعليق التوضيحي على run 31241947281 = `Invalid workflow file: .github/workflows/ci.yml#L1 (Line: 16, Col: 23): Unrecognized named-value: 'runner'. Located at position 1 within expression: runner.temp` — سياق `runner` غير متاح في `jobs.<id>.env` | runs 31129230384، 31237246480، 31239298725، 31241771183/31240323871، 31243142711 كلها 0s | ✅ **مُصلَحة** — commit المالك `ff6a484` استبدل `runner.temp` بـ `github.workspace`. أول run أخضر حقيقي `31243523514` نجح في 1m21s (Python 1m17s, Frontend 16s) |
| 14 | **تلوث بيت الذاكرة:** commit المالك `afde5fe` أنشأ `docs/pic for frontend` (بايت واحد، بلا محتوى أو مرجع) | `ls -la "docs/pic for frontend"` = 1 بايت؛ لا مرجع في أي ملف | ✅ **مُصلَحة** — حُذف في M12-T02 (PR #6) |
| 15 | **صلاحية المنصة:** تطبيق GitHub الخاص بـArena لا يملك `workflows`، فلا يستطيع تسليم أي تعديل على `.github/workflows/*` | `git push` → remote rejected refusing to allow a GitHub App to create or update workflow; REST API → HTTP 403 Resource not accessible by integration | ✅ **مُصلَحة بتطبيق المالك** — طبّق المالك commit `ff6a484` مباشرة على GitHub لفك العائق وتفعيل CI |
| 16 | **فخ غلاف GitHub Artifact:** تنزيل Actions يعطي `teledrive-package.zip` (غلاف يحوي `teledrive_v4.5.zip`) بينما Cell 1 كانت تقبل الملف الحقيقي فقط → `AssertionError` بعد mount، وإعادة التسمية تسبب `EOFError` (قراءة/كتابة على الملف نفسه) | محاكاة M15-T01 للسيناريوهات A–F من main النظيفة `1f60a37` على منطق Cell 1 حرفيًا | ✅ **مُصلَحة في M15-T02** — Cell 1 تكتشف الغلاف بالمحتوى وتستخرجه عبر temp + `os.replace` مع رفض traversal؛ 16 اختبارًا في `tests/test_restore_package.py` |
