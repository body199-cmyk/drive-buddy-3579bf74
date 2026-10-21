# M49-T01 — منع تحميل حزمة Colab قديمة عند إعادة تشغيل الخلايا

**التاريخ:** 2026-10-21  
**الفرع:** `fix/colab-package-stale-fallback`  
**الأساس:** `main` عند `36b9aec7b031007fce4c9b7ba784dda8730bb78c`  
**الحالة:** إصلاح الكود والتوثيق مقترح على فرع؛ لم يُدمج بعد، ولم يُختبر Colab حيًا.

## العَرَض والسبب

كان Cell 1 يستدعي `pkg_try_update()`، لكن نتيجة `REFUSED` لم توقف الخلية. عندما تكتشف البوابة أن وحدات `teledrive` مستوردة بالفعل، ترفض التبديل الساخن حفاظًا على التطبيق الحي، ثم كان التنفيذ يكمل إلى `resolve_package_zip()` ويستعيد `/content/teledrive_v4.5.zip` الموجود. إذا كان هذا الملف قديمًا، يظهر للمستخدم أن تشغيل الخلية أعاد النسخة القديمة بدل أن يوضح أن الـRuntime يحتاج Restart.

هذا ليس دليلًا على أن كل حالة تحديث فاشلة سببها هذا المسار؛ لكنه مسار خطير ومثبت من ترتيب التعليمات في Cell 1، ويجب ألا يُسمح له بالرجوع إلى ZIP محلي في حالة runtime-loaded.

## التعديلات

1. `python-package/teledrive/notebook_cells.py`: حفظ نتيجة بوابة التحديث في `PACKAGE_UPDATE_RESULT`، وإذا كان سبب الرفض هو `runtime already loaded` تُرفع رسالة واضحة تطلب `Runtime > Restart session` ثم إعادة تشغيل Cells 1–4. تبقى سياسة fallback لأعطال الشبكة/الـmanifest كما هي؛ لا يجري تبديل runtime حي.
2. `python-package/tests/test_package_update.py`: إضافة عقد يثبت أن فحص رفض الـruntime يأتي بعد البوابة وقبل `resolve_package_zip`.
3. أُعيد توليد/تحديث النسختين الموزعتين `python-package/notebook/TeleDrive.ipynb` و`public/TeleDrive.ipynb`، و`python-package/teledrive/colab_cells.json` يدويًا من نفس التغيير. يجب أن يؤكد CI `notebook_cells --check` و`cmp` التطابق مع المولّد قبل الدمج.
4. `.github/workflows/release-current.yml`: استبدال سير العمل اليدوي القديم بنسخة النشر الآلي الموثقة في `docs/M46_T02_release_current_workflow.yml`: تشغيل عند تغييرات الحزمة على `main` أو dispatch يدوي، تشغيل بوابات الاختبار قبل النشر، إنشاء manifest يتضمن `build_run_id`، تحديث التاج الثابت مع رفع ZIP أولًا والـmanifest أخيرًا، ثم التحقق العام من البصمة والحجم. لا يُحذف التاج أو الـRelease.
5. تحديث سجل التسليم والتغييرات والمشكلات المفتوحة حتى يستطيع الوكيل التالي استكمال المهمة من هذه النقطة.

## التحقق الحالي

- GitHub Release الأحدث المرصود قبل هذا الفرع: [`pkg-39525758114`](https://github.com/body199-cmyk/drive-buddy-3579bf74/releases/tag/pkg-39525758114)، مبني من `36b9aec7b031007fce4c9b7ba784dda8730bb78c`؛ أصوله ZIP بحجم 660403 بايت وmanifest بحجم 366 بايت، وWorkflow run [39525758114](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39525758114) نجح. هذا يثبت نشر HEAD السابق فقط، وليس التعديلات الحالية.
- لم تُشغّل اختبارات Python داخل بيئة checkout في هذه الجلسة؛ لذلك لا يوجد ادعاء بأن بوابات الفرع نجحت.
- لم يُشغّل Google Colab فعليًا، ولم يتم التحقق من تسجيل Telegram أو Drive أو نقل ملف حقيقي.

## خطوات الإغلاق

1. افتح PR لهذا الفرع وانتظر Python/Frontend CI.
2. يجب أن تمر: `compileall`, `pytest -q`, `teledrive_launcher.py --check`, `python -m teledrive.notebook_cells --check`, تطابق النوتبوكين، واختبارات الواجهة الأمامية.
3. بعد الدمج، تحقق أن سير العمل الآلي نشر manifest وZIP يطابقان نفس commit والحجم وSHA-256.
4. في Colab: افتح نسخة `main` من النوتبوك، نفّذ **Runtime > Restart session**، ثم Cell 1–4 بالترتيب. تحقق من سطر `Package update: SUCCESS` أو `ALREADY CURRENT`، ومرجع الحزمة، وظهور رابط Gradio ورابط/زر Web. لا تعتبر المهمة Colab-ready قبل هذه الخطوة.
