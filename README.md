# TeleDrive — Telegram & Universal Downloads → Google Drive

> أداة تعمل من **Google Colab** لنقل ملفات Telegram إلى Google Drive، مع لوحة تحكم لمتابعة المهام، بالإضافة إلى تحميل ملفات من روابط خارجية مدعومة مباشرةً إلى Drive.

<p align="center">
  <a href="https://colab.research.google.com/github/body199-cmyk/drive-buddy-3579bf74/blob/main/public/TeleDrive.ipynb">
    <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open TeleDrive in Google Colab">
  </a>
</p>

## 🚀 التشغيل — افتح أحدث Notebook من هنا

**[اضغط لفتح TeleDrive مباشرةً في Google Colab](https://colab.research.google.com/github/body199-cmyk/drive-buddy-3579bf74/blob/main/public/TeleDrive.ipynb)**

هذا الرابط يشير إلى ملف `public/TeleDrive.ipynb` على فرع `main`، لذلك يفتح آخر نسخة محفوظة من النوت‌بوك بعد تحديث المستودع. حزمة البرنامج التي تثبّتها الخلية الأولى تُنشر تلقائيًا من خلال سير عمل الإصدار بعد اجتياز الاختبارات؛ لا تعتمد على تنزيل ZIP قديم يدويًا.

**مهم:** إذا كانت لديك جلسة Colab قديمة تعمل بالفعل، فلن تتغير مكتباتها تلقائيًا بمجرد تحديث GitHub. لا تحدّث الحزم داخل Runtime حمّل وحدات TeleDrive بالفعل؛ افتح Runtime جديدًا عند الانتقال إلى نسخة جديدة. لا توقف جلسة تعمل تحتاجها قبل أن تكون مستعدًا لإعادة تشغيلها.

---

## ما الذي يقدمه TeleDrive؟

- **Telegram → Google Drive:** تحليل روابط Telegram واختيار الملفات ونقلها إلى مجلد Drive المحدد.
- **التحميل الشامل من أي رابط مدعوم:** لصق رابط خارجي، اختيار الجودة المتاحة، ومتابعة مهمة التحميل والرفع من لوحة التحكم.
- **متابعة المهام:** حالات العمل والتقدم والسرعة ورسائل الخطأ، مع إمكانية إلغاء المهام حيثما تسمح مرحلة التنزيل بذلك.
- **استعادة جلسة Telegram:** حفظ نسخة احتياطية من الجلسة وبيانات الاعتماد في مجلد التطبيق على Drive، لاستعادتها عند استخدام حساب Drive نفسه.
- **تشغيل من المتصفح:** يعتمد على Google Colab ولا يتطلب تثبيت Python أو إعداد خادم على جهازك.

> دعم الروابط والجودات يعتمد على المنصة والرابط والأدوات المتاحة في وقت التشغيل. إلغاء مهمة بعد بدء رفع الملف إلى Drive قد لا يكون متاحًا، وإلغاء تنزيل مجلد عبر `gdown` قد يتأخر حتى تنتهي العملية الجارية.

## قبل البدء

ستحتاج إلى:
1. حساب Google لاستخدام Colab وDrive.
2. حساب Telegram.
3. بيانات Telegram API (`api_id` و`api_hash`) من [my.telegram.org/apps](https://my.telegram.org/apps)، عند إعداد الاتصال لأول مرة.

احتفظ ببيانات الدخول ورموز التحقق لنفسك، ولا تلصقها في Issues أو الرسائل العامة.

## خطوات التشغيل

1. افتح [أحدث Notebook في Colab](https://colab.research.google.com/github/body199-cmyk/drive-buddy-3579bf74/blob/main/public/TeleDrive.ipynb).
2. من القائمة اختر **Runtime → Run all**، أو شغّل الخلايا من الأعلى إلى الأسفل بالترتيب. انتظر اكتمال كل خلية قبل الانتقال إلى التالية.
3. في خلية الإعداد الأولى، انتظر تنزيل حزمة TeleDrive والتحقق من سلامتها وتثبيت المتطلبات.
4. وافق على ربط Google Drive عندما يطلب Colab ذلك.
5. إذا لم تكن هناك جلسة Telegram محفوظة على حساب Drive الحالي، أدخل بيانات Telegram API واتبع خطوات التحقق. لا تشارك كود تسجيل الدخول أو كلمة مرور التحقق بخطوتين.
6. افتح رابط `TeleDrive URL` الذي يظهر عند تشغيل الواجهة.
7. استخدم تبويب Telegram لتحليل الروابط وتحديد الملفات ثم بدء النقل، أو افتح **التحميل الشامل** للصق رابط خارجي مدعوم ومتابعة المهمة.

### ملاحظات عن خلايا Notebook

- شغّل الخلايا بالترتيب من البداية، خصوصًا في Runtime جديد.
- الخلايا اللاحقة مخصصة لحفظ الحالة والاختبارات والتنظيف بحسب ما توضحه عناوينها؛ لا تشغّل خلية تنظيف أثناء وجود نقل تحتاج إلى استمراره.
- إذا ظهرت رسالة `REFUSED` تفيد بأن وحدات TeleDrive محمّلة بالفعل، استخدم **Runtime → Restart runtime** فقط عندما تكون مستعدًا لإنهاء الجلسة الحالية، ثم ابدأ من الخلية الأولى. هذه حماية تمنع خلط ملفات إصدار جديد بوحدات قديمة في الذاكرة.

## حفظ تسجيل Telegram واستعادته

بعد الاتصال بنجاح، استخدم خيار **حفظ تسجيل Telegram على Drive** داخل الواجهة.

- تُحفظ نسخة احتياطية من جلسة Telegram وبيانات الاعتماد داخل مجلد بيانات TeleDrive على Drive.
- في التشغيل التالي على **حساب Drive نفسه**، يستطيع التطبيق محاولة استعادة الجلسة المحفوظة بدل طلب تسجيل الدخول من البداية.
- الجلسة الفعلية تُستخدم محليًا داخل بيئة Colab؛ وجود نسخة احتياطية على Drive لا يعني تشغيل Telethon مباشرة من Drive.
- إذا سجّلت الخروج من Telegram أو ألغيت الجلسة من إعدادات Telegram، فقد تحتاج إلى تسجيل الدخول وحفظ الجلسة مجددًا.
- خيار **نسيان تسجيل Telegram المحفوظ** يحذف بيانات الجلسة المحفوظة من مجلد التطبيق؛ استخدمه فقط إذا كنت تريد إلغاء الاستعادة التلقائية.

## روابط مهمة

| الغرض | الرابط |
|---|---|
| **فتح أحدث Notebook في Colab** | [فتح TeleDrive](https://colab.research.google.com/github/body199-cmyk/drive-buddy-3579bf74/blob/main/public/TeleDrive.ipynb) |
| Notebook على GitHub | [public/TeleDrive.ipynb](https://github.com/body199-cmyk/drive-buddy-3579bf74/blob/main/public/TeleDrive.ipynb) |
| جميع إصدارات الحزمة | [GitHub Releases](https://github.com/body199-cmyk/drive-buddy-3579bf74/releases) |
| الإصدار المستقر الذي تحدّثه عملية النشر | [الحزمة وملف manifest](https://github.com/body199-cmyk/drive-buddy-3579bf74/releases/tag/pkg-2026.08.09-m15t07) |
| Google Colab | [colab.research.google.com](https://colab.research.google.com/) |
| Telegram API | [my.telegram.org/apps](https://my.telegram.org/apps) |
| Google Drive | [drive.google.com](https://drive.google.com/) |

## حل المشكلات الشائعة

- **ظهور `REFUSED` أو رسالة عن وحدات محمّلة:** Runtime → Restart runtime، ثم شغّل الخلايا بالترتيب. انتبه أن إعادة التشغيل تنهي الجلسة الحالية.
- **رابط الواجهة لا يفتح:** تأكد من اكتمال خلية تشغيل الواجهة، ثم افتح رابط `TeleDrive URL` كاملًا.
- **انقطاع Colab:** قد تنتهي جلسات Colab المجانية أو تنقطع؛ أعد فتح Notebook وابدأ Runtime جديدًا. تحقق من الملفات الموجودة في Drive قبل إعادة النقل لتجنب تكرار الملفات.
- **Telegram FloodWait:** انتظر المدة المطلوبة قبل تكرار الطلبات.
- **طلب تسجيل Telegram من جديد:** تأكد أنك ربطت حساب Google الصحيح وأنك حفظت الجلسة بعد تسجيل دخول ناجح.
- **فشل تنزيل رابط خارجي:** قد يكون الرابط خاصًا أو منتهي الصلاحية أو غير مدعوم، أو قد تتطلب المنصة ملفات إضافية/أداة مثل FFmpeg. جرّب رابطًا عامًا صالحًا وتحقق من رسالة الخطأ في المهمة.

## التوثيق للمطورين

التوثيق التفصيلي وحوكمة المشروع موجودان في مجلد [`docs/`](docs/):

- [سياق المشروع](docs/PROJECT_CONTEXT.md)
- [الخريطة المعمارية](docs/ARCHITECTURE.md)
- [قواعد الذكاء الاصطناعي](docs/AI_RULES.md)
- [الدستور](docs/CONSTITUTION.md)
- [سجل المهام](docs/TODO.md)
- [سجل التسليم](docs/AI_HANDOFF.md)
- [سجل التغييرات](docs/CHANGELOG.md)
- [تعليمات بدء العمل](docs/BOOTSTRAP_PROMPT.md)

### ملفات التشغيل الأساسية

- `public/TeleDrive.ipynb` — Notebook المستخدم، والرابط المباشر أعلاه يفتح نسخة `main`.
- `python-package/` — كود Python والاختبارات وبناء الحزمة.
- `.github/workflows/` — اختبارات المشروع ونشر حزمة Colab بعد اجتياز البوابات المطلوبة.

## مبدأ الأمان والاستقرار

التعديلات على ميزات التحميل الشامل يجب أن تحافظ على مسار Telegram الحالي. يتم نشر الحزمة من المصدر بعد اجتياز الاختبارات، وتتحقق خلية الإعداد من manifest وSHA-256 قبل التثبيت. لا تستبدل هذا التحقق بتنزيل ملفات Python عشوائية من `main`، ولا تنسخ أسرار Telegram إلى المستودع أو سجلات التشغيل.

---

**المستودع الرسمي:** [body199-cmyk/drive-buddy-3579bf74](https://github.com/body199-cmyk/drive-buddy-3579bf74) · **افتح أحدث Notebook:** [Google Colab](https://colab.research.google.com/github/body199-cmyk/drive-buddy-3579bf74/blob/main/public/TeleDrive.ipynb)
