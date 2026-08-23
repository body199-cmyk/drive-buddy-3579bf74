# ACTIVE TASK

| الحقل | القيمة |
|---|---|
| TASK ID | `M39-T01` |
| العنوان | صفوف التحويل المتجاوبة ووصول React الآمن إلى لوحة Telegram الأصلية |
| الحالة | **MERGED + CI-PASSED + PACKAGE-PUBLISHED**؛ اختبار Colab والنقل الحي خارج نطاق M39 وغير مثبتين |
| code commit / merge | `113c0e311fb6f76d26d9e877572fb2c6fb7acc8e` → main `4b490a03aa76b0d3e5cf58b4d251a401a19abfb2` عبر PR [#83](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/83) |
| Publish | release `pkg-2026.08.09-m15t07` محدث يدويًا؛ manifest/ZIP العامان commit `4b490a0` وSHA `dfc1f133…051ee9` وحجم `561162` bytes |

## النطاق المثبت

1. عرض صف الطابور بالكامل على سطح المكتب، ثم تحويله إلى بطاقة هاتف عند أقل من 621px، من دون حذف عمود أو زر أو تغيير action ID أو payload.
2. زر React ظاهر يفتح `td-secure-telegram-auth`، أي Accordion Gradio الآمن الموجود فقط. لا يمرر أسرارًا عبر bridge ولا يضيف endpoint أو storage أو transport.
3. تحقق Gradio 6.20 الحي المحلي: الزر فتح Accordion الأصلي ثم ظل `telegram.status` عاملاً (`Action completed`) بلا إدخال بيانات اعتماد.
4. لم تُمس ملفات النقل أو المصادقة الخلفية أو `react_bridge.py` أو النوتبوك أو الاعتماديات أو جلسات Telegram/Drive.

## الأدلة المنفذة

`746 passed` · `51/51` launcher · notebook check + cmp PASS · React contracts `29/29` · lint/build PASS (0 errors، 7 warnings baseline) · معاينة CSS/markup لسطح المكتب والهاتف · CI 4/4 لــPR #83 SUCCESS · manifest وZIP عامان تطابقا بايتًا بعد النشر.

## حدان باقيان

1. لم يحدث Colab Cell 4 أو Telegram/Drive transfer حي في M39؛ لا `Colab-ready` أو `Complete`.
2. نبض React كل ثانية أثناء النقل لا يزال موضوع تشخيص منفصل (#72): يحتاج repro حي يتحقق من Pause/Resume/Stop خلال النبض؛ M39 لا يغيره.

## نقطة التراجع

عكس merge `4b490a0…` للكود. وللتراجع الكامل في Colab، يلزم إعادة رفع archive/manifest مطابقين لـSHA سابق؛ لا توجد بيانات حساب أو مسح ضمن التغيير.

## الخطوة التالية

اختبار Colab حي قابل للرصد للحزمة المنشورة، ثم repro نقل حي لمسار التحكم مع نبض الثانية الواحدة قبل تنفيذ أي إصلاح منفصل له.
