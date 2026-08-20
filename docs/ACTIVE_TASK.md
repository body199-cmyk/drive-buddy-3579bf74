# Active Task

| الحقل | القيمة |
|---|---|
| TASK ID | `M31` |
| العنوان | إيقاف عاصفة التحديث العالمي وإصلاح استئناف drain من داخل runtime loop |
| الحالة | **Code MERGED + CI-PASSED + live sandbox-verified؛ توثيق الإغلاق والنشر النهائي وColab pending** |
| PR | [#69](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/69) — MERGED |
| Merge SHA | `397b97fa806a0d624f93d6f1afe839d9e5639577` |

## الإصلاحات المدمجة

| المسار | السلوك المدمج | الدليل |
|---|---|---|
| نبض الواجهة | إزالة Timer Gradio العالمي الذي كان يحدّث queue وdashboard كل ثانية أثناء الخمول؛ heartbeat React المشروط بالنقل وأزرار التحديث اليدوية باقيان | عقد UI ناجح، `pnpm lint/build`، وفحص متصفح حي ثابت بلا console errors |
| Resume | جدولة drain الاستئناف عبر `AsyncRuntime.schedule()` عند callback داخل الحلقة، مع إبقاء submit الآمن من خارجها | `34 passed` مستهدفة، واختبار حي استأنف من offset `8192` |

## أدلة النقل الحي

| الاختبار | النتيجة |
|---|---|
| Start | بدأ نقل عشرة ملفات حقيقية عبر Handler الإنتاج |
| Pause | عنصران دخلا `Paused` والملفات الجزئية محفوظة |
| Resume | عادت العناصر إلى المسار ووصلت المجموعة إلى `Uploaded` مع استئناف offset |
| Stop | بقي العنصر `Stopped`، والملف الجزئي محفوظ، وعدد ملفات الوسائط الجديدة في Drive يساوي صفرًا |
| Drive | [مجلد TeleDrive-M31-Resume-Controls-20260820](https://drive.google.com/drive/folders/10QE4oPbkQ6zNkmBYaRGPX19Icl1_mQQ8) |

## البوابات

Python `743 passed`، وعقود React `26/26`، و`pnpm lint` و`pnpm build`، وlauncher `51/51`، وCI Python/Frontend ناجحان على push وpull request.

## الخطوة المتبقية

بعد دمج وثائق M31، شغّل **Publish current TeleDrive package** من `main` النهائي، ثم أعد تشغيل Runtime في Colab الحقيقي وشغّل الخلايا بالترتيب. تبقى الحالة غير `Colab-ready` وغير `Complete` حتى يثبت ذلك الاختبار المستقل.
