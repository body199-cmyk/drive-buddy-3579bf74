# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

| الحقل | القيمة |
|---|---|
| TASK ID | `M27-T04` |
| العنوان | إصلاح عيوب النقل والقناة الخاصة وتحميل لوحة React المكتشفة بالتحقق الحي |
| الحالة | **ACTIVE — local gates + live sandbox-verified؛ CI/Colab النهائيان pending** |
| الفرع | `fix/m27-t04-live-defects` |
| Base SHA | `3bbe69b91159fb519e2d7fb6efab9835ad7788f5` (`origin/main` عند البدء) |

## العيوب المثبتة

| المسار | السبب الذي ثبت | الإصلاح الجاري |
|---|---|---|
| Pause / Resume | إعادة إحياء صف `Paused` قد تتقاطع مع drain سابق لم يغلق بعد | تشغيل drain الاستئناف فقط بعد استقرار المستقبل السابق، ومنع callback قديم من إطفاء محرك أحدث |
| رابط دعوة قناة خاصة | `ScannerService` كان يرفض `t.me/+…` حتى لو كان الحساب عضوًا والقناة قابلة للحل | `CheckChatInviteRequest` لحساب عضو فقط ثم InputPeer؛ لا Join تلقائي ولا مسح غير محدود |
| React داخل Gradio | الأصل المدمج استدعى `process.env.NODE_ENV` في المتصفح فحجب تركيب اللوحة | بناء Production صريح وحارس عقد يمنع المرجع غير المتاح |

## الأدلة المتاحة قبل GitHub

| البوابة أو السيناريو | النتيجة |
|---|---|
| نقل Telegram إلى Drive ضمن مساحة اختبار معزولة | PASS؛ الملف البعيد تحقق من وجوده وحجمه |
| Pause → Resume من offset | PASS؛ `.part` محفوظ وحالة نهائية `Uploaded` |
| Stop أثناء تنزيل | PASS؛ `Stopped` نهائي، `.part` محفوظ، لا ملف جديد على Drive |
| Analyze لرابط دعوة خاص | PASS؛ مرشح محدود ثم Dedupe حقيقي للملف الموجود |
| تركيب لوحة React في متصفح محلي | PASS؛ اللوحة الكاملة مرئية ولا خطأ `process is not defined` |
| بوابات Python | `738 passed`، launcher `51/51`، notebook/cmp/package PASS |
| بوابات الواجهة | lint/build PASS، React contracts `26 passed` |

## الخطوة التالية

فحص diff والأسرار، تحديث `TODO` و`AI_HANDOFF` و`CHANGELOG` و`KNOWN_ISSUES`، ثم commit وpush وPR. لا يجوز وصف النتيجة `Colab-ready` أو `Complete` قبل اختبار Colab ونشر الحزمة من `main`.
