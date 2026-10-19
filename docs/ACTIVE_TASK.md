# المهمة النشطة

| الحقل | القيمة |
|---|---|
| TASK ID | `M45-T01` |
| العنوان | خط أنابيب تنزيل/رفع منفصل، محاذاة offset صحيحة لـ512 KiB، حفظ `.part` عند التعثر، وتصفية الوسائط الوهمية |
| الأساس | `acab9d228e45a5a77a5fef9198cf3df9dd1f4729` — main بعد PR #97 |
| الفرع | `arena/5b79cd32-drive-buddy-3579bf74` |
| الحالة | **MERGED + CI-PASSED; release publish and Colab live benchmark pending** |
| التقرير | `docs/PHASE_REPORTS/PHASE_M45_T01_TELEGRAM_SPEED_AND_STABILITY.md` |

## النطاق

- **حدود ثلاثية بدل سيمافور واحد:** `MAX_CONCURRENT_TG_DOWNLOADS=4` ملفات،
  `PARALLEL_DOWNLOAD_STREAMS=4` قارئات لملف واحد ≥32 MiB، `TG_INFLIGHT_REQUESTS=8`
  طلب `GetFile` جارٍ على مستوى العميل كله (يشمل الملفات الصغيرة والاستئناف).
- **خط أنابيب مرحلتين:** إذن العامل يغطي التنزيل فقط؛ الرفع يجري بعد تحريره تحت بوابة
  Drive واحدة وحاجز `MAX_PENDING_UPLOADS=4` للملفات الجاهزة.
- **لا نداء Drive حاجب في مسار التنزيل:** فحص التكرار استباقي فقط عندما يكون خدمة Drive
  خاملة؛ وإلا يُعاد استخدام الملف الموجود على Drive في مرحلة الرفع مع حدث `duplicate`.
- **محاذاة 512 KiB** لاستئناف الملفات >512 KiB (و4 KiB للملفات الأصغر حتى لا ينكسر عقد M27).
- **إعادة استخدام `.part` الكامل** بدل تنزيله من جديد بعد فشل رفع أو Restart.
- **`_has_downloadable_media()`** تمنع تحويل Web Page/Poll/Geo/Contact إلى صف 0 بايت `.bin`.
- **تصنيف أخطاء Telethon الحقيقية**: transient لـ`request was unsuccessful`، وpermanent
  لـ`invalid limit` و`downloaded file missing`.

## الأدلة المحلية

`809 passed` · compileall PASS · launcher `54/54` · notebook check + `cmp` PASS ·
`node --test` 34/34. اختبارات M45 الجديدة تثبت المحاذاة، حفظ البادئة، حد الطلبات
العالمي، حد الملفات عند workers=20، استمرار التنزيل أثناء رفع محجوب، إعادة استخدام
`.part` الكامل، تصفية الوسائط الوهمية، وتصنيف الأخطاء.
`bun run lint/build` NOT RUN: `bun: command not found`، ولا تغييرات frontend.

## ما لم يثبت / المطلوب قبل إغلاق المهمة

- لا اختبار حي على Telegram أو Colab ولا قياس benchmark؛ كل أدلة السرعة عقدية.
- يلزم إعادة نشر ZIP/manifest من SHA المدموج، ثم Restart Colab والتأكد من
  `telethon crypto backend=cryptg` ووجود سطر `parallel download complete ... mbps=`.
- يلزم A/B فعلي: ملف ≥100 MB، وتسجيل الحجم/الزمن/المعدل، ثم Pause/Resume، ثم التحقق من
  وصول الملف إلى Drive واكتمال checkpoint.
- لا ادعاء نسبة تسريع قبل هذا القياس.

## التراجع

Revert commit M45-T01. السلوك السابق يعود بالكامل: سيمافور عامل واحد يغطي التنزيل والرفع،
محاذاة 4 KiB، fallback من الصفر، وفحص تكرار حاجب قبل التنزيل. لا حذف من Drive أو Vault.
