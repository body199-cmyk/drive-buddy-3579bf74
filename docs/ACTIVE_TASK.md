# ACTIVE_TASK

| الحقل | القيمة |
|---|---|
| TASK ID | `M38-T01` |
| العنوان | إصلاح إعادة تركيب جسر React–Gradio في Colab ومنع بقاء واجهة مرتبطة بجسر مغلق |
| الحالة | **MERGED + CI-PASSED + PACKAGE-PUBLISHED**؛ اختبار Colab الحي حتى Cell 4 ما زال غير مثبت |
| code commit / merge | `8afa544ae36f7bf845b46f291af154f3a7d2a3b1` → main `0727eba4450bd95e4f269140745a43a219b63fcc` عبر PR [#81](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/81) |
| Publish | [#31](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32618829803) SUCCESS؛ manifest وZIP العامان تحققا على merge SHA |

## النطاق المثبت

1. لا Telegram ولا Drive هما سبب banner `Backend bridge unavailable`: السجل ربط `react.bridge.request` خلفيًا، وحالة Telegram غير المصرح بها يجب أن تبقى حالة واجهة قابلة للاستعمال.
2. `GradioTeleDriveBridge` لا يعلن unavailable إلا بعد `dispose()`. غلاف `ReactPanel` لم يكن يملك دورة حياة مثيل واحد عند إعادة تركيب Gradio في Colab.
3. الإصلاح يخزن المثيل على عنصر Gradio، يفك السابق قبل mount، ويعيد cleanup مملوكًا للمثيل الحالي فقط. لم يتغير نقل القيمة الرسمي أو أي API أو جلسة أو نوتبوك.
4. عقد React الجديد يثبت هذه الملكية والتنظيف؛ أُعيد بناء `panel.bundle.gz` من المصدر.

## الأدلة المنفذة

`746 passed` · `51/51` launcher · notebook check + cmp PASS · React contracts `27/27` · lint/build PASS. تحقق Gradio 6.20 مع external proxy/root_path بدأ بلوحة حية من دون banner blocked. اكتملت فحوص CI الأربعة لـPR #81 بنجاح قبل الدمج.

## الحد الحي الصادق

نجحت Cell 1 وCell 2 سابقًا في Colab حقيقي، لكن Cell 3 توقف عند fallback إدخال Telegram لغياب Vault لهذا الحساب. بعد نشر #31 أُعيد تشغيل Runtime، لكن سطح Colab المتاح لم يعرض عداد تنفيذ أو مخرجًا موثوقًا لـCell 1. لذا لا ادعاء تحقق Cell 4 أو `Colab-ready` أو نقل Telegram/Drive حي.

## نقطة التراجع

عكس merge `0727eba4450bd95e4f269140745a43a219b63fcc` أو commit الإصلاح `8afa544ae36f7bf845b46f291af154f3a7d2a3b1`؛ لا توجد بيانات حساب أو ملف Drive أو Session ضمن التعديل.

## الخطوة التالية

اختبار Colab حي قابل للرصد يصل إلى Cell 4 ويفتح الواجهة المنشورة. لا كود إضافي مطلوب ما لم يظهر عيب حي متكرر.
