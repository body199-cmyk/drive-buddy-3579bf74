# PHASE M39-T01 — صفوف طابور متجاوبة ووصول آمن لمصادقة Telegram

> **الحالة عند إعداد التقرير:** `CODE-COMPLETE CANDIDATE + FAKE-TESTED + LOCAL-GRADIO-VERIFIED`.
> لا يوجد commit أو push أو PR أو merge لهذه المهمة وقت كتابة هذا التقرير.

## الهدف والنطاق

عالجت هذه المهمة مشكلتين مرئيتين محددتين من دون تغيير أي منطق نقل أو مصادقة أو عقد Bridge. كانت صفوف الطابور على سطح المكتب تسمح بتمرير أفقي يجعل أزرار `إيقاف` و`استئناف` و`إعادة` تقع خارج الرؤية. كما كانت لوحة مصادقة Telegram الآمنة موجودة في Accordion Gradio السفلي فقط، فلا يصل المستخدم إليها من لوحة React الظاهرة.

يقتصر النطاق على التخطيط المتجاوب والوصول الأمامي. لا توجد تغييرات في `transfer_manager.py` أو `telegram_auth.py` أو `react_bridge.py` أو النوتبوك أو الاعتماديات أو الجلسات أو بيانات Drive.

| المتطلب المعتمد | التنفيذ | ما لم يتغير |
|---|---|---|
| صف ملف كامل على سطح المكتب بلا سحب أفقي | جدول session بعرض ثابت داخل 621px فأعلى؛ نسب عرض موزونة، التفاف اسم الملف، progress بعرض العمود، وأزرار التحكم تبقى في السطر | action IDs وpayloads وhandlers وحالات الصف |
| بطاقة مرتبة على الهاتف | أقل من 621px يتحول الصف نفسه إلى بطاقة معنونة: ملف، حالة، تقدم، حجم، ثم شبكة الأزرار الثلاثة | البيانات الحية نفسها وترتيب أزرار الصف |
| وصول مباشر آمن إلى تسجيل Telegram | زر React مرئي يستهدف Accordion Gradio ذي المعرف `td-secure-telegram-auth`، يفتحه ويُمرر إليه محليًا في DOM | حقول API hash/الهاتف/OTP/2FA لا تدخل React ولا bridge |

## التغيير الفني

### صفوف التحويل

أضيفت فئة `td-queue-row` ووسوم `data-label` مترجمة و`aria-label` للتحكم في الصف إلى markup الموجود. عند سطح المكتب يُفرض `table-layout: fixed` على جدول session ويُلغى التمرير الأفقي داخل هذا الجدول فقط. لا يحذف هذا أي عمود أو زر؛ بل يعطي الملف 35%، والحالة 12%، والتقدم 22%، والحجم 10%، والتحكم 21% من العرض.

عند الهاتف لا يبقى صف الجدول ضيقًا؛ يتحول إلى بطاقة رأسها اسم الملف ومعرفه، ثم حقول معنونة، وفي النهاية أزرار التحكم الثلاثة على شبكة عرض كامل. هذه CSS فقط، ولا تغير نداءات `queue.pause_item` أو `queue.resume_item` أو `queue.retry_item`.

### مصادقة Telegram

أضيف `elem_id="td-secure-telegram-auth"` إلى Accordion Gradio الموجود أصلًا. زر React لا يرسل طلب bridge ولا يحمل إدخالًا حساسًا؛ يحدد Accordion في `document` وينقر عنصر الفتح المحلي الذي أثبته Gradio 6.20 (`button.label-wrap`)، ثم ينفذ `scrollIntoView`. يدعم أيضًا مسار `details/summary` و`aria-expanded` إن تغير تركيب Gradio مستقبلًا.

> لا تنتقل API hash أو رقم الهاتف أو رمز OTP أو 2FA أو session إلى React، ولا توجد شبكة أو WebSocket أو local/session storage جديدة في حدود المتصفح.

## اختبارات وأدلة فعلية

| الفحص | النتيجة | ما يثبته |
|---|---|---|
| `python3 -m compileall teledrive` | PASS | سلامة حزم Python |
| `python3 -m pytest -q tests` | `746 passed` | الانحدار الكامل لـPython |
| `python3 teledrive_launcher.py --check` | `51/51 ready actions resolve` | بقاء جميع الأفعال الجاهزة موصولة |
| notebook check + cmp | PASS | لا تغيير غير مقصود في النوتبوك المولد أو العام |
| `pnpm run lint` | PASS مع 7 warnings baseline فقط، 0 errors | صياغة TypeScript وCSS |
| `pnpm run build` | PASS | بناء الواجهة الإنتاجي |
| React contracts | `29/29 PASS` | عقود M39 للوصول الآمن والتخطيط، مع الحفاظ على كل action IDs |
| تحقق سطح المكتب محليًا | PASS | صفان من نفس markup/CSS أظهرا كل الأعمدة وأزرار `إيقاف/استئناف/إعادة` بلا شريط أفقي |
| تحقق الهاتف المحلي بعرض 390px | PASS | كل صف ظهر كبطاقة معنونة مع شبكة الأزرار كاملة بلا تمرير أفقي |
| Gradio 6.20 محلي حي | PASS | زر React ظهر، فتح Accordion الآمن الأصلي، و`telegram.status` أعاد `Action completed` بعد ذلك |

ملف ملاحظات الفحص البصري خارج المستودع: `/home/ubuntu/m39_visual_findings.md`. لم يدخل أي screenshot أو بيانات اعتماد أو جلسة إلى Git.

## ما لم يثبت

لم يُدخل أي اعتماد Telegram أو Drive ولم يبدأ نقل أو إيقاف أو استئناف في هذا التحقق؛ لذلك لا يمثل الدليل اختبار نقل حي. لم يُشغَّل Runtime Colab جديد لمهمة M39، ولا تغير هذه المهمة حد M38 الخاص بإثبات Cell 4 داخل Colab المنشور. الحالة الصحيحة هي **Implemented + fake-tested + local-Gradio-verified**، وليست `Colab-ready` أو `Complete`.

## ملفات التغيير

| الملف | التغيير |
|---|---|
| `src/components/teleDrive/TeleDriveSandbox.tsx` | زر الوصول الآمن، helper DOM محلي، وفئات/labels صفوف الطابور |
| `src/components/teleDrive/teleDrive.css` | تخطيط سطح المكتب والهاتف للصفوف مع إبقاء التحكم كاملًا |
| `python-package/teledrive/ui.py` | معرف ثابت للـAccordion الآمن الموجود |
| `tests/teledrive-sandbox.contract.test.mjs` | عقدا M39؛ العدد 27 → 29 |
| `python-package/teledrive/react_panel_assets/panel.bundle.gz` | React bundle معاد بناؤه من المصدر |
| `python-package/teledrive/react_panel_assets/panel.css.gz` | CSS bundle معاد بناؤه من المصدر |

## التراجع

قبل الدمج: حذف فرع `fix/m39-t01-responsive-queue-auth-access`. بعد الدمج: عكس commit M39 فقط. لا توجد عملية بيانات أو مسح أو تحديث حزمة منشورة ضمن هذه المهمة.

## حالة GitHub عند إعداد التقرير

| العملية | الحالة |
|---|---|
| Commit | NOT ATTEMPTED |
| Push | NOT ATTEMPTED |
| Pull Request | NOT ATTEMPTED |
| Merge | NOT ATTEMPTED |
| Publish | NOT APPLICABLE — لا تغيير للنوتبوك أو التحديث التلقائي للحزمة |
