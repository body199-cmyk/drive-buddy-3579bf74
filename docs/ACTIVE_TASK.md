# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

| الحقل | القيمة |
|---|---|
| TASK ID | `M27-T02` |
| العنوان | إصلاح شحن بندل React ليحدّث تقدم النقل تلقائيًا |
| الحالة | **ACTIVE — local/fake-tested. Not live-verified** |
| الفرع | `arena/react-auto-refresh-bundle` |
| Base SHA | `50cb7657f07c4e2432e875c0ad36e876e4aac652` (`origin/main`) |
| السبب المثبت | مصدر `TeleDriveSandbox.tsx` يحتوي نبض `setInterval` كل ثانيتين، لكن `react_panel.py` يحمّل `panel.bundle.gz` وقد كان البندل المشحون لا يحتوي `setInterval`؛ لذلك يعمل زر «تحديث» اليدوي بينما لا يصل أي طلب دوري. |
| التغيير | أعيد بناء `panel.bundle.gz` و`panel.css.gz` من مدخل Gradio الحقيقي، وأضيف مولّد ثابت وعقد يفك البندل ويثبت وجود global `TeleDriveGradioPanel` و`setInterval` و`queue.refresh`. |
| الخطوة التالية | تدقيق الفرق وإنشاء commit/PR ثم الدمج فقط بعد CI؛ وبعده يجب إعادة نشر حزمة Colab وتشغيل runtime جديد لاختبار حي. |

## التحقق المحلي

| البوابة | النتيجة |
|---|---|
| عقد لوحة React | `25 passed` عبر `node --experimental-strip-types --test` |
| lint + frontend build | PASS؛ مع 7 تحذيرات Fast Refresh موجودة مسبقًا بلا errors |
| Python suite | `734 passed` |
| compileall وlauncher | PASS؛ `51/51 ready actions resolve` |
| notebook check و`cmp` وبناء الحزمة | PASS |

> لا تثبت هذه البوابات تشغيل Colab الحي. بعد الدمج، يلزم نشر الحزمة من `main` ثم Restart للـruntime؛ البندل القديم في جلسة المتصفح الحالية لن يتحول تلقائيًا إلى النسخة الجديدة.
