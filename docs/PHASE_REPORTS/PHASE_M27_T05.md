# M27-T05 — تصحيح حالة الطابور الخامل ورسائل تحقق Analyze

**التاريخ:** 2026-08-19 UTC

**فرع الكود:** `fix/m27-t05-queue-analyze-ux`

**Base SHA:** `fba83eaad2980a20ca60a62b60ef318d0386eef2`

**Source SHA:** `b853208df1e640c9bc12aa51169394634f7e453e`

**PR:** [#61](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/61) — **MERGED**

**Merge SHA:** `c9034234a6a1a2e487b94719c223356cdeeb84d5`

**الحالة:** **MERGED + CI-PASSED + live sandbox-verified؛ تحقق Colab النهائي ما زال pending.**

## الهدف

إغلاق عيبين مثبتين في اختبار الاستخدام الحقيقي للوحة React، من دون تغيير مسارات Telegram أو Drive أو النقل: أولًا، منع شارة المحرك من الادعاء بأنه `paused` أو `running` عند ضغط Pause أو Resume وطابور النقل فارغ. ثانيًا، عرض سبب إدخال Analyze غير المكتمل للمستخدم بلغته بدل تجاهل الطلب وترك إشعار نجاح عام قديم ظاهرًا.

| العيب المثبت | السبب المؤكد | الإصلاح النهائي |
|---|---|---|
| Pause/Resume على طابور بلا عامل نقل يحوّل الشارة إلى `paused` ثم `running` | `QueueManager.pause()` كان يعلن الإيقاف ويكتب checkpoint بلا `Future` عامل، و`resume()` كان يفرض `running` حتى عند عدم إحياء أي صف | Pause خامل صار no-op يحافظ على اللقطة `idle` ولا ينشئ checkpoint؛ Resume يعلن `running` فقط إن كان drain فعليًا قائمًا أو بدأ لاستيعاب صفوف `Paused` المستأنفة |
| Analyze بإدخال ناقص لا يعرض سبب الخطأ | تحقق React الأمامي كان يعيد reason code ثم ينهي الدالة بصمت؛ وبالمسار الخلفي كان خطأ `TeleDriveError` المتحوّل إلى مخرجات Gradio غير معلم للـbridge فيعود `ok/Action completed` | React يعرض إشعارًا محليًا مترجمًا لكل سبب إدخال؛ ووسم `status_error` يحافظ على شكل مخرجات Gradio ويجعل bridge يعيد خطأ التطبيق المترجم كـnon-success |

## الملفات المعدلة في إصلاح الكود

| الملف | التغيير |
|---|---|
| `python-package/teledrive/queue_manager.py` | حارس للطابور الخامل في `pause()`، وحالة Resume مشتقة من `running()` بدل فرض تشغيل وهمي |
| `python-package/teledrive/handlers.py` | تمييز أخطاء التطبيق المحلية القائمة بوسم التحذير الموجود، مع بقاء arity ومخرجات Gradio كما هما |
| `src/components/teleDrive/TeleDriveSandbox.tsx` | تمرير إشعار خطأ مترجم من تحقق Analyze الأمامي لقناة notices الحالية؛ يغطي الرابط، رقم الرسالة، النطاق والحد |
| `python-package/teledrive/react_panel_assets/panel.bundle.gz` | بندل React المضمن معاد بناؤه حتميًا من المصدر المعدل |
| `python-package/tests/test_phase_c.py` | إثبات أن Pause الخامل لا ينشئ checkpoint ويبقي `idle`؛ واختبار checkpoint أثناء Future عامل |
| `python-package/tests/test_phase_3.py` | إثبات أن Resume يحرر بوابة المدير من دون ادعاء محرك `running` عند غياب صف مستأنف |
| `python-package/tests/test_react_bridge.py` | إثبات أن خطأ Analyze المترجم يعود `status=error` وليس `Action completed` |
| `tests/teledrive-sandbox.contract.test.mjs` | عقد يثبت أن تحقق Analyze الأمامي يرسل رسالة error مرئية بدل تجاهل reason code |

## التحقق الحي المعزول

لم تُكتب أي بيانات اعتماد أو جلسات أو أرقام أو رموز في الشجرة أو هذا التقرير. استخدمت البيئة المحلية المعزولة فقط جلسات الاختبار المعتمدة الموجودة خارج المستودع.

| السيناريو | النتيجة الفعلية |
|---|---|
| جاهزية البيئة | واجهة Gradio أعيد تشغيلها من أصل React المضمن الجديد؛ Telegram ظهر `AUTHORIZED` وDrive ظهر `CONNECTED` في ApplicationContext الحي |
| Pause لطابور فارغ | **PASS:** ظل المحرك `idle` مع صفر صفوف و0 عامل نشط؛ لم تتحول الشارة إلى `paused` |
| Resume لطابور فارغ بعد Pause | **PASS:** ظل المحرك `idle` ولم تتحول الشارة إلى `running` |
| Analyze بلا رابط | **PASS:** ظهر إشعار خطأ عربي مرئي: `ألصق رابط رسالة أو قناة صالحًا.` |
| Analyze برابط مع ترك رقم رسالة واحدة فارغًا | **PASS:** ظهر إشعار خطأ عربي مرئي: `وضع الرسالة يحتاج رقم رسالة موجبًا، أو الصق رابط رسالة مباشرًا.` |

لم يُنفذ في هذه الجولة أي رفع أو إنشاء ملف Drive أو logout أو حذف جلسة أو تصدير ZIP أو تصدير Colab؛ بقي نطاق الاختبار مقصورًا على العيبين المعتمدين.

## بوابات محلية فعلية

| الأمر | النتيجة |
|---|---|
| `python -m compileall teledrive` | PASS |
| `python -m pytest -q tests` | **740 passed** |
| `python teledrive_launcher.py --check` | **51/51 ready actions resolve** |
| `python -m teledrive.notebook_cells --check` | PASS |
| `cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb` | PASS، النوت‌بوكان متزامنان |
| `python -m teledrive.package_service --build ...` | PASS، الأرشيف بني خارج المستودع |
| `pnpm lint` | PASS مع **0 errors** و7 تحذيرات موجودة مسبقًا خارج نطاق المهمة |
| `vite build` | اكتملت مراحل client وSSR وNitro وولّدت المخرجات؛ عملية shell المحلية بقيت معلّقة بعد رسائل نجاح Nitro في هذا sandbox، ولذلك كانت CI البعيدة هي بوابة رمز الخروج الحاسمة |
| `node --experimental-strip-types --test tests/teledrive-sandbox.contract.test.mjs` | **26 passed** |

## CI وGitHub

| التشغيل | المشغّل | Python package | Frontend build | النتيجة |
|---|---|---:|---:|---|
| `32280815115` | push | PASS | PASS | SUCCESS |
| `32280845863` | pull_request | PASS | PASS | SUCCESS |

التحذير الوحيد في CI هو انتقال Actions من Node.js 20 إلى Node.js 24، وهو تحذير منصة خارج نطاق هذا التعديل، ولم يفشل أي job.

## ما لا يثبته هذا التقرير

هذا التقرير ليس اختبار Google Colab حقيقيًا، ولا يعني نشر حزمة Colab أو نجاح Cell 1..7 في runtime جديد. لذلك يبقى المشروع **ليس `Colab-ready` وليس `Complete`**. كما أن اختبار Telegram وDrive الحي هنا أثبت جاهزية الاتصال والواجهة المعزولة، وليس إعادة اختبار نقل ملف كامل لأن ذلك خارج نطاق العيبين ولا يلزم لإثباتهما.

## نقطة التراجع

الرجوع الآمن بعد الدمج هو `git revert c9034234a6a1a2e487b94719c223356cdeeb84d5` عبر PR جديد. لا تستخدم إعادة كتابة التاريخ، ولا توجد في المهمة عمليات حذف لملفات Drive أو `.part` أو جلسات Telegram.
