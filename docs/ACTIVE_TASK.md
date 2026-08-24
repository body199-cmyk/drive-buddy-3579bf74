# المهمة النشطة

| الحقل | القيمة |
|---|---|
| TASK ID | `M43` |
| العنوان | Vault Telegram ذاتية الاكتفاء على Drive + حفظ آخر رابط فحص في الواجهة الحقيقية |
| code commit / merge | `e974dfd` → `2d5893d` عبر PR [#91](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/91) |
| الحالة | **MERGED + CI-PASSED + PACKAGE-PUBLISHED — Colab live pending** |
| CI | push [#32689166257](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689166257) وPR [#32689176699](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689176699) SUCCESS |
| Publish | [#32689575111](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689575111) SUCCESS؛ manifest/ZIP: commit `2d5893d…`، SHA `28d94129…90b79`، `570612` bytes |

## النطاق المثبت

1. Vault format 3 Drive-managed تجعل Drive مصدر الاستعادة الكامل لجلسة Telegram؛ لا تحتاج Runtime جديدة إلى Colab Secrets أو OTP حين تكون الجلسة صالحة.
2. Vault format 2 القديمة تبقى مدعومة وتُهجّر بعد نجاح الاستعادة فقط. لا تُحذف النسخة النشطة قبل نجاح زوج versioned بديل وmanifest جديد.
3. Cell 3 يفضّل API metadata من Vault format 3 ويعامل Colab Secrets كوسيلة ترقية اختيارية فقط للـformat 2 القديمة. لا يطبع API Hash.
4. React وGradio يعرضان حالة Telegram من ApplicationContext نفسه، لذلك تظهر الحالة المستعادة في واجهة المشروع بدل طلب تسجيل منفصل.
5. رابط التحليل المحفوظ يدخل من action registry إلى `ScannerService` وSQLite settings ثم live snapshot؛ هناك زر مسح صريح في الواجهتين، ولا يوجد localStorage أو backend موازٍ.

## الأدلة

`779 passed` محليًا، وCI Python/Frontend نجحا في push وPR. launcher `53/53`، notebook check + cmp PASS، React contracts `34/34` محليًا، lint/build PASS، وarchive مطابق للـmanifest العام. workflow النشر الأول توقف fail-closed لاختلاف الحجم؛ استُبدل الزوج المتطابق معًا فقط، ثم تحقق workflow #32689575111 من الأصول العامة بنجاح.

## حد الأمان والتحقق المتبقي

صيغة Drive-managed قرار مالك موثق في ADR-004: حماية حساب Drive هي حد الوصول العملي. لا تُطبع أو تُرسل API Hash/session/OTP إلى الواجهة أو السجلات أو Git. لا تحذف M43 `.part` أو Vault أو release/tag.

لم يثبت بعد تشغيل Cells 1–4 بالحزمة M43 المنشورة، ولم يظهر `Gradio · Live bridge` في هذا التعديل. لا تستخدم **Colab-ready** أو **Complete** قبل هذا الدليل.

## نقطة التراجع

يعكس merge `2d5893d…` ثم ينشر ZIP/manifest متطابقان مع SHA المستهدف، دون حذف release/tag أو Vault تلقائيًا.
