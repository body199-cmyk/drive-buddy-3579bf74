# المهمة النشطة

| الحقل | القيمة |
|---|---|
| TASK ID | `M43` |
| العنوان | Vault Telegram ذاتية الاكتفاء على Drive + حفظ آخر رابط فحص في الواجهة الحقيقية |
| baseline | `7a0d645dce28c352f59e747244f8773fc36ae383` |
| branch | `fix/m43-drive-only-vault-and-link-memory` |
| الحالة | **LOCAL VERIFICATION COMPLETE — commit / PR / merge / publish pending** |

## النطاق المنفذ محليًا

1. Vault format 3 Drive-managed تجعل Drive مصدر الاستعادة الكامل لجلسة Telegram؛ لا تحتاج Runtime جديدة إلى Colab Secrets أو OTP حين تكون الجلسة صالحة.
2. Vault format 2 القديمة تبقى مدعومة وتُهجّر بعد نجاح الاستعادة فقط. لا تُحذف النسخة النشطة قبل نجاح زوج versioned بديل وmanifest جديد.
3. Cell 3 يفضّل API metadata من Vault format 3 ويعامل Colab Secrets كوسيلة ترقية اختيارية فقط للـformat 2 القديمة. لا يطبع API Hash.
4. React وGradio يعرضان حالة Telegram من ApplicationContext نفسه، لذلك تظهر الحالة المستعادة في واجهة المشروع بدل طلب تسجيل منفصل.
5. رابط التحليل المحفوظ يدخل من action registry إلى `ScannerService` وSQLite settings ثم live snapshot؛ هناك زر مسح صريح في الواجهتين، ولا يوجد localStorage أو backend موازٍ.

## البوابات المحلية

| البوابة | النتيجة |
|---|---|
| Python suite | `779 passed` |
| launcher | `53/53 ready actions resolve` |
| compileall / notebook check / cmp | PASS |
| React lint / build | PASS؛ تحذيرات baseline فقط |
| React contracts | `34/34 PASS` |
| panel bundle | rebuilt from source |
| package archive | PASS؛ SHA `28d94129…90b79`، `570612` bytes |

## حد الأمان والتحقق المتبقي

صيغة Drive-managed قرار مالك موثق في ADR-004: حماية حساب Drive هي حد الوصول العملي. لا تُطبع أو تُرسل API Hash/session/OTP إلى الواجهة أو السجلات أو Git. لا تحذف M43 `.part` أو Vault أو release/tag.

لم يثبت بعد تشغيل Cells 1–4 بالحزمة M43 المنشورة على Colab، ولم يظهر `Gradio · Live bridge` في هذا التعديل. لا تستخدم **Colab-ready** أو **Complete** قبل هذا الدليل.
