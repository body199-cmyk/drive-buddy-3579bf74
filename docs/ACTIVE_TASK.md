# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

| الحقل | القيمة |
|---|---|
| TASK ID | `M29-T01` |
| العنوان | منع احتجاز مقاعد الطابور عند Pause وتبديل semaphore الحي، وحفظ حجم الصور الفعلي |
| الحالة | **Code MERGED + CI-PASSED + live sandbox-verified؛ توثيق الإغلاق والنشر النهائي وColab pending** |
| PR | [#67](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/67) — MERGED |
| Merge SHA | `1ba3fd0bf80bfb84593ff7f13a52958de947cbf4` |
| Base SHA | `cdbe86404a0a06bae951cd6629e5d736cde4ef70` |

## النطاق المغلق

| المسار | السلوك المدمج | الدليل |
|---|---|---|
| انتظار Pause الفردي | ينتظر العنصر المؤقت قبل الاستحواذ على semaphore، فلا يمنع عنصرًا runnable لاحقًا عند `workers=1` | اختبار تنفيذ طابور من عنصرين |
| تغيير workers | لا يستبدل `set_workers()` semaphore حيًا؛ القيمة الجديدة تطبق عند run لاحق فقط | اختبار هوية semaphore أثناء task حي وبعد انتهائه |
| حجم الصور | يسجل `size_bytes` الفعلي بعد تنزيل صورة بتقدير مختلف قبل upload/verification | اختبار مسار صورة كامل يثبت قيمة SQLite النهائية |

## الأدلة

| البوابة | النتيجة |
|---|---|
| اختبارات النقل الموجهة | `26 passed` |
| Python | `743 passed`؛ launcher `51/51`؛ compileall/notebook/package ناجحة |
| React/Frontend | contracts `26 passed`؛ `pnpm lint` و`pnpm build` ناجحان |
| CI | أربع فحوص ناجحة: Python وFrontend لكل من push وpull_request على PR #67 |
| اختبار حي معزول | Pause أبقى `.part` بلا ملف Drive؛ Resume استأنف من offset ووصل Uploaded؛ Stop بقي Stopped بلا ملف Drive |
| تقرير المرحلة | `docs/PHASE_REPORTS/PHASE_M29_T01.md` |

## الخطوة التالية

بعد دمج وثائق M29-T01، شغّل **Publish current TeleDrive package** من `main` لمرة واحدة فقط، ثم أعد تشغيل Runtime في **Colab الحقيقي** ليجلب manifest/archive النهائيين واختبر UI ونقل Telegram→Drive. وحتى نجاح ذلك، الحالة **ليست `Colab-ready` وليست `Complete`**.
