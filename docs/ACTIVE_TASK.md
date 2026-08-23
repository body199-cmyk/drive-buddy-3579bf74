# ACTIVE_TASK

| الحقل | القيمة |
|---|---|
| TASK ID | `M38-T01` |
| العنوان | إصلاح إعادة تركيب جسر React–Gradio في Colab ومنع بقاء واجهة مرتبطة بجسر مغلق |
| الحالة | **CODE-COMPLETE CANDIDATE + FAKE-TESTED + PROXY-VERIFIED**؛ ينتظر commit/PR/CI/merge/publish |
| Branch | `fix/m38-t01-colab-bridge-remount` (base: main `c9c1a769eb9d646d8aa564a0a6e1fa94907486c9`) |

## النطاق المثبت

1. لا Telegram ولا Drive هما سبب banner `Backend bridge unavailable`: السجل ربط `react.bridge.request` خلفيًا، وحالة Telegram غير المصرح بها يجب أن تبقى حالة واجهة قابلة للاستعمال.
2. `GradioTeleDriveBridge` لا يعلن unavailable إلا بعد `dispose()`. غلاف `ReactPanel` لم يكن يملك دورة حياة مثيل واحد عند إعادة تركيب Gradio في Colab.
3. الإصلاح يخزن المثيل على عنصر Gradio، يفك السابق قبل mount، ويعيد cleanup مملوكًا للمثيل الحالي فقط. لم يتغير نقل القيمة الرسمي أو أي API أو جلسة أو نوتبوك.
4. عقد React الجديد يثبت هذه الملكية والتنظيف؛ أُعيد بناء `panel.bundle.gz` من المصدر.

## بوابات منفذة

`746 passed` · `51/51` launcher · notebook check + cmp PASS · React contracts `27/27` · lint/build PASS. تحقق Gradio 6.20 مع external proxy/root_path بدأ بلوحة حية من دون banner blocked.

## حد حي صادق

Cell 1 وCell 2 نجحتا في Colab حقيقي، لكن Cell 3 توقف عند fallback إدخال Telegram لغياب Vault لهذا الحساب؛ لذلك لا يُدعى تحقق Cell 4 أو Colab-ready قبل النشر وإعادة الاختبار.

## نقطة التراجع

إزالة فرع `fix/m38-t01-colab-bridge-remount` أو عكس commit M38؛ لا توجد بيانات حساب أو ملف Drive أو Session ضمن التعديل.
