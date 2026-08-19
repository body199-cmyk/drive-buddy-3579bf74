# PHASE M29-T01 — سلامة مقاعد الطابور وحجم الصور

**التاريخ:** 2026-08-19 UTC

**حالة الكود:** `MERGED + CI-PASSED + live sandbox-verified`

**المصدر:** مراجعة وثيقة إصلاحات M27 المقدمة من المالك، بعد مواءمتها مع `main` الفعلي بدل تطبيقها حرفيًا.

## خط الأساس وقرار المواءمة

| البند | القيمة |
|---|---|
| Base SHA | `cdbe86404a0a06bae951cd6629e5d736cde4ef70` |
| Code PR | [#67](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/67) — MERGED |
| Source SHA | `02d2a67ddaac994617539dc076eccad79e1059ba` |
| Merge SHA | `1ba3fd0bf80bfb84593ff7f13a52958de947cbf4` |

الوثيقة المقدمة بُنيت على شجرة قديمة. لذلك لم تُطبّق باتشاتها كاملة أو تعاد كتابة ملفات موجودة. تبيّن من فحص `main` أن Drive calls خارج event loop، وخنق SQLite، والتحقق قبل cleanup، واستئناف offset، وإيقاف Pause/Stop داخل الملف، وبطاقة التسليم الحية كانت موجودة أصلًا ومغطاة باختبارات؛ لم تُعد هذه الإصلاحات.

## الفجوات الفعلية المعالجة

| الفجوة المثبتة | التعديل الأدنى | الاختبار التنفيذي |
|---|---|---|
| العنصر الموقوف مؤقتًا قد يحجز مقعد التزامن قبل انتظار Pause الفردي | ينتظر `_process()` بوابتي pause/stop قبل `async with self._semaphore()` | عنصر Paused مع `workers=1` لا يمنع عنصرًا لاحقًا من الوصول إلى `Uploaded` |
| تغيير عدد workers أثناء عمل مهام قد يستبدل semaphore حيًا ويقسم السقف بين كائنين | `set_workers()` لا يعيد تعيين `_sema` إلا إن لم توجد مهام أو كانت كلها منتهية | تغيير القيمة أثناء task حي يُبقي نفس semaphore؛ وبعد انتهائه يعاد بناؤه للـrun التالي |
| حجم الصورة المصحح بعد تنزيلها يبقى في الذاكرة فقط | حفظ `item.size_bytes` إلى SQLite قبل upload/verification | صورة بتقدير أولي مختلف تنتهي Uploaded ويخزن الصف الحجم الفعلي |

## التحقق

| البوابة | النتيجة |
|---|---|
| اختبارات النقل الموجهة | `26 passed` |
| مجموعة Python الكاملة | `743 passed` |
| launcher | `51/51 ready actions resolve` |
| compileall / notebook / byte comparison / package | PASS |
| React contracts | `26 passed` |
| Frontend | `pnpm lint` و`pnpm build` ناجحان |
| CI | Python وFrontend نجحا على push وpull_request لطلب #67 |
| تحقق حي معزول | Pause حفظ `.part` بلا ملف Drive، Resume استأنف من offset ووصل Uploaded بملف Drive واحد، Stop بقي Stopped بلا ملف Drive |
| أمن الفرق | `git diff --check` وفحص الأسرار نجحا؛ لا sessions أو tokens أو اعتمادات في Git |

## الحدود والتراجع

> يثبت التشغيل الحي هنا Telegram→Drive في runtime معزول، وليس تشغيل Colab browser الحقيقي. لا تزال إعادة تشغيل Colab واختبار المسار من الواجهة النهائية مطلوبة بعد نشر الحزمة النهائية.

نقطة التراجع هي revert لالتزام المصدر `02d2a67` أو لدمج PR #67. لا يلمس التراجع `.part` أو بيانات SQLite أو ملفات Drive أو جلسات Telegram/Drive.

## الخطوة التالية

تُدمج وثائق الإغلاق، ثم يعاد تشغيل workflow **Publish current TeleDrive package** من `main` بعد هذا الدمج فقط. بعدها يعاد تشغيل Runtime في Colab لتلتقط Cell 1 الـmanifest والحزمة النهائية، ويتبع ذلك smoke test حي في Colab.
