# PHASE M41-T01 — حماية جسر React–Gradio من watcher قديم في Colab

> **الحالة النهائية للكود:** `MERGED + CI-PASSED + PACKAGE-PUBLISHED`؛ يظل تحقق Colab المنشور والنقل الحي خارج نطاق الدليل الحالي.
> التزام المصدر `4fca8e6b1c899c1b54a1adfbb38c65e247472b96` دُمج إلى main عند `bc9fc5f42bcec51d2f7f6566021cf0f2433de9d1` عبر PR [#87](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/87).

## البلاغ وسبب التعامل العاجل

أظهرت لقطة المالك صفحة React محملة بالكامل لكن كل حالة فيها `—` ورسالة **`Backend bridge unavailable`**. هذه الرسالة لا تعني Telegram أو Drive غير متصلين؛ إنما تعني أن `TeleDriveSandbox` يرى `bridge.isLive() = false`، أي أن مثيل `GradioTeleDriveBridge` الذي يملكه React قد دخل `dispose()`.

تحققنا من أن الحزمة المنشورة الحالية كانت تشير إلى `main` عند `5b5d1b…`، ولذلك لم يكن السبب تثبيت إصدار قديم عمدًا. المسار المحلي العادي ومسار `is_colab=True` خلف proxy حمّلا bridge حيًا، لكن البلاغ الحي يثبت أن دورة lifecycle في Colab ما زالت تملك فجوة غير مغطاة بالعقد السابق.

## السبب الجذري المعالج

كان `js_on_load` ينشئ panel/bridge جديدًا كلما أعاد Gradio تنفيذ hook للـhost نفسه، ثم يتخلص من panel السابق فورًا. في حالات Colab التي تبقى فيها شجرة React المعروضة مرتبطة بالمثيل السابق، تصبح الشجرة مرئية لكنها تحمل bridge disposed؛ ولذلك تظهر الرسالة وتتعطل كل الأزرار.

الإصلاح لا ينقل أسرارًا ولا يفتح transport جديدًا. أضيفت دالة `isLive()` إلى panel المركب، وصار `js_on_load`:

1. يعيد استخدام panel الحي إذا أعيد تنفيذ hook لنفس عنصر Gradio.
2. يضع **lease** جديدًا لكل تنفيذ hook.
3. يمنع watcher قديمًا أو cleanup قديمًا من تسليم قيمة أو dispose للمالك الحالي.
4. لا ينشئ panel بديلًا إلا بعد أن يصبح المثيل السابق غير حي أو ينظف فعليًا.

## النطاق

| الملف | التغيير |
|---|---|
| `python-package/teledrive/react_panel.py` | إعادة استخدام panel الحي وlease آمن للـwatch/cleanup في `js_on_load` |
| `src/components/teleDrive/gradioEntry.tsx` | كشف `isLive()` من مثيل panel المركب فقط |
| `tests/teledrive-sandbox.contract.test.mjs` | اختبار M41 سلوكي يعيد نداء on-load مرتين لنفس host ويثبت watcher/cleanup lease |
| `python-package/teledrive/react_panel_assets/panel.bundle.gz` | bundle JavaScript معاد توليده من المصدر |
| `python-package/teledrive/react_panel_assets/panel.css.gz` | أصل CSS معاد توليده بواسطة الباني نفسه |

لا تغير في action IDs أو Python handlers أو Telegram/Drive أو notebook أو الاعتماديات أو الجلسات أو ملفات المستخدم.

## أدلة التنفيذ

| الفحص | النتيجة | ما يثبته |
|---|---|---|
| عقد lifecycle M41 | PASS | on-load المتكرر يحتفظ بمثيل حي واحد؛ watcher والـcleanup القديمان لا يؤذيان المالك الحالي |
| Python suite | `769 passed` | عدم وجود انحدار Python |
| launcher | `51/51 ready actions resolve` | بقاء كل أفعال الواجهة موصولة |
| notebook check + cmp | PASS | لا تغيير غير مقصود في النوتبوك |
| lint/build | PASS؛ 0 errors و9 warnings baseline | سلامة الواجهة والبناء |
| React contracts | `33/33 PASS` | عقود bridge وM39/M40/M41 مجتمعة |
| Gradio 6.20 محلي | PASS | بدأ بـ`Gradio · Live bridge`؛ زر `telegram.status` عاد بـ`Action completed` |
| محاكاة Colab محلية | PASS | `is_colab=True` + proxy خارجي بدأ بـ`Gradio · Live bridge`؛ زر `telegram.status` عمل بعد restart للبندل |

## الحدود الصادقة

لم تتوفر إعادة إنتاج مباشرة على Runtime Colab الخاص بالمالك بعد نشر M41؛ محاكاة proxy المحلية ليست إثباتًا كاملاً لنفس دورة Colab البعيدة. كذلك لم يُدخل اعتماد Telegram/Drive ولم يبدأ نقل حي أو Pause/Resume/Stop في هذه المهمة. الحالة ليست `Colab-ready` أو `Complete` حتى يظهر Cell 4 وسلوك الواجهة في Colab المنشور من دون رسالة unavailable.

## التراجع

عكس merge `bc9fc5f42bcec51d2f7f6566021cf0f2433de9d1` أو commit المصدر `4fca8e6b1c899c1b54a1adfbb38c65e247472b96` للكود. وللتراجع الكامل في Colab، أعد نشر archive/manifest مطابقين لـSHA سابق؛ release/tag لم يحذفا في M41. لا توجد عملية بيانات أو مسح ضمن المهمة.

## حالة GitHub والنشر

| العملية | الحالة |
|---|---|
| Commit | SUCCESS — `4fca8e6b1c899c1b54a1adfbb38c65e247472b96` |
| Push | SUCCESS — فرع M41 دُفع ثم حذف بعد الدمج |
| Pull Request | MERGED — [#87](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/87)؛ فحوص CI الأربعة SUCCESS |
| Merge | MERGED — `bc9fc5f42bcec51d2f7f6566021cf0f2433de9d1` |
| Publish | SUCCESS — [#32646821416](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32646821416)؛ ZIP/manifest العامان commit `bc9fc5f…`، SHA `ab3d3db2…d1529`، حجم `567611` bytes. التشغيل الأول [#32646652723](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32646652723) توقف fail-closed فقط لاختلاف الأصل السابق، ثم استبدلت الأصول المتطابقة معًا بإذن المالك. |
