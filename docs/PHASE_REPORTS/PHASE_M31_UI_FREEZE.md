# Phase M31 — إيقاف عاصفة التحديث وإصلاح استئناف النقل

## النطاق والنتيجة

كشفت تجربة الاستخدام الحية أن الواجهة كانت تُحدّث نفسها كل ثانية حتى وهي خاملة، ما جعل الصفحة تبدو كأن زر «تحديث» يُضغط باستمرار وأفقد المستخدم القدرة على التفاعل. أثبت فحص الشجرة أن السبب هو وجود **Timer Gradio عالمي** يرسل `queue.refresh` و`dashboard.refresh` بالتوازي مع heartbeat React المشروط بالنقل الفعلي. أزيل هذا المسار العالمي فقط؛ بقي heartbeat React للتحديث التلقائي أثناء النقل، وبقيت أزرار التحديث اليدوية متاحة.

كشف اختبار أزرار النقل الحي أيضًا عيبًا مستقلًا في Resume: callback انتهاء drain القديم كان يعمل داخل حلقة TeleDrive ثم يستدعي `AsyncRuntime.submit()`، وهو مسار يرفض الاستدعاء من داخل الحلقة برسالة `submit() called from inside the runtime loop`. أضيفت واجهة `schedule()` التي تنشئ Task داخل الحلقة عند الحاجة وتستخدم submission الآمن من خارجها، واستُخدمت فقط لمسار drain الاستئناف.

## التغييرات

| الملف | التغيير |
|---|---|
| `python-package/teledrive/ui.py` | إزالة Timer Gradio العالمي الذي كان يحدّث كامل الصفحة في الخمول؛ الحفاظ على wiring الأزرار وheartbeat React النشط |
| `python-package/teledrive/async_runtime.py` | إضافة `schedule()` للتعامل الآمن مع coroutine من داخل أو خارج حلقة runtime الوحيدة |
| `python-package/teledrive/queue_manager.py` | استخدام `schedule()` عند إعادة تشغيل drain بعد Resume |
| `python-package/tests/test_m26_t03_rebased.py` | عقد يمنع عودة Timer العالمي ويثبت بقاء التحديث اليدوي |
| `python-package/tests/test_m27_hardening.py` | اختبار يثبت أن Resume يستخدم schedule ولا يعيد submit من callback الحلقة |

## الأدلة المحلية

| البوابة | النتيجة |
|---|---|
| اختبار Resume وAsyncRuntime وعقد UI | `34 passed` |
| Python الكامل | `743 passed` |
| Frontend | `pnpm lint` و`pnpm build` ناجحان، وعقود React `26/26` |
| Launcher | `51/51 ready actions resolve` |
| CI | Python وFrontend نجحا على push وpull request في PR #69 |
| فرق وأمان | `git diff --check` ناجح، ولا أسرار في الفرق |

## التحقق الحي

استُخدمت جلسة Telegram بديلة مستقلة بعد إبطال الجلسة القديمة من Telegram بسبب استخدام متزامن من عنواني IP. لم تُحذف الجلسة الأصلية.

اختبار التحكم الحي استخدم Handlers الإنتاج نفسها المرتبطة بأزرار الصفحة، واختبر عشرة ملفات صوتية حقيقية من القناة الخاصة إلى مجلد Drive مستقل. النتيجة كانت: عشرة ملفات وصلت إلى `Uploaded` مع checksums، وPause نقل عنصرين إلى `Paused` مع حفظ الملفات الجزئية، وResume أعاد النقل من offset `8192`، وStop بقي `Stopped` مع حفظ الملف الجزئي ومن دون إنشاء ملف وسائط بعيد.

مجلد الاختبار: [TeleDrive-M31-Resume-Controls-20260820](https://drive.google.com/drive/folders/10QE4oPbkQ6zNkmBYaRGPX19Icl1_mQQ8).

فحص المتصفح المحلي بعد إزالة Timer أثبت أن الصفحة بقيت ثابتة أثناء الخمول، وأن أزرار التحويلات ظهرت وتفاعلت، وأن التحليل أعاد 15 مرشحًا حقيقيًا، مع اختيار عشرة وإضافتها للطابور وتشغيل Start وتحديث الحالة تلقائيًا. الجولة المرئية نفسها واجهت Dedupe قديمًا، ولذلك لم تُستخدم بدل اختبار Handlers الحي الكامل المذكور أعلاه.

## الدمج

- PR الكود: [#69](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/69)
- Merge SHA: `397b97fa806a0d624f93d6f1afe839d9e5639577`
- `main` و`origin/main` متطابقان بعد الدمج.

## الحدود الصادقة

هذا الإصلاح لم يُعد نشره إلى حزمة Colab بعد. يجب تشغيل **Publish current TeleDrive package** من `main` النهائي ثم إعادة تشغيل Runtime حقيقي في Colab. لا يُستخدم وصف `Colab-ready` أو `Complete` قبل ذلك الاختبار المستقل.
