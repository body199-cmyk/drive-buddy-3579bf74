# المهمة النشطة

## بطاقة الاستئناف — M45-T01 (جلسة Arena 2026-10-19T16:32Z)

| الحقل | القيمة |
|---|---|
| TASK ID | `M45-T01` (استئناف تنفيذ DOC مكتوب ضد baseline قديم) |
| الأساس | `d991cf4783545ee838d3c2eeaf3b98fc0c22cf6f` — main بعد PR #100 |
| الفرع | `arena/3befa0b6-drive-buddy-3579bf74` |
| الحالة | **RESUME_VERIFIED** — كل بنود DOC §3 موجودة مسبقًا ومثبتة بالقراءة والاختبارات؛ أُغلقت الفجوة الحرفية الوحيدة (`serverresent`) وأُضيف اختبارها؛ كل البوابات خضراء |
| Release | `pkg-2026.08.09-m15t07` **موجود ومنشور** من `d991cf4` عبر run 39278373927 (المالك نفّذ خطوة الاسترداد) — KNOWN_ISSUES #79 أُغلقت |

> المهمة الأصلية M45-T01 دُمجت ومنشورة بالفعل (PRs #93/#95/#98/#100). DOC الاستئناف
> افترض أن M44-T01 غير مدمج — هذا غير صحيح للشجرة الحية. لا إعادة تطبيق؛ ما دُوّن
> في تقرير المرحلة §9 هو ما أُضيف فعليًا في هذه الجلسة فقط.

---

| الحقل | القيمة |
|---|---|
| TASK ID | `M45-T01` |
| العنوان | خط أنابيب تنزيل/رفع منفصل، محاذاة offset صحيحة لـ512 KiB، حفظ `.part` عند التعثر، وتصفية الوسائط الوهمية |
| الأساس | `acab9d228e45a5a77a5fef9198cf3df9dd1f4729` — main بعد PR #97 |
| الفرع | `arena/5b79cd32-drive-buddy-3579bf74` |
| الحالة | **MERGED + CI-PASSED (main run 39275554488); release asset republish needs ONE owner click; Colab live benchmark pending** |
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

## حادث النشر (2026-10-19) — يجب على المالك تنفيذ خطوة واحدة

- محاولة رفع الأصول من sandbox فشلت لأن `uploads.github.com` محجوب في بيئة التنفيذ
  (`SSL_ERROR_SYSCALL`)، ومع `--clobber` حُذف `teledrive_manifest.json` القديم قبل فشل الرفع.
- لتجنّب ترك أصل واحد فقط، حُذف الـrelease والـtag `pkg-2026.08.09-m15t07` كاملًا بقصد
  إعادة إنشائهما ذريًا عبر `release-current.yml`، لكن `workflow_dispatch` أعاد HTTP 403
  («Resource not accessible by integration») من رمز الجلسة.
- **الإصلاح المطلوب (خطوة واحدة من المالك):** Actions → «Publish current TeleDrive package»
  → Run workflow على `main`. سيبني من `main` الحالي (M45-T01) ويُنشئ الـrelease بالأصلين
  معًا ثم يتحقق منهما علنًا (المسار «release absent → create atomically»).
- حتى ذلك الحين: Cell 1 تطبع `Package update: REFUSED update endpoint unreachable; current
  package unchanged` ثم تعمل بالحزمة المحفوظة/المُستعادة — لا انهيار ولا تغيير صامت.

