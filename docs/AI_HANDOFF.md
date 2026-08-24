# بطاقة التسليم — M43: Vault Drive-managed ورابط التحليل المحفوظ

| الحقل | القيمة |
|---|---|
| Updated (UTC) | `2026-08-24` |
| baseline | `main` عند `7a0d645dce28c352f59e747244f8773fc36ae383` |
| فرع العمل | `fix/m43-drive-only-vault-and-link-memory` |
| الحالة | **LOCAL VERIFICATION COMPLETE — commit / PR / merge / publish pending** |
| التقرير | `docs/PHASE_REPORTS/PHASE_M43_DRIVE_MANAGED_VAULT_AND_ANALYZE_LINK.md` |

## النتيجة المقصودة

يعالج M43 تجربة المالك المطلوبة: بعد تسجيل Telegram وحفظ Vault جديدة على حساب Drive نفسه، يستطيع Runtime Colab جديد استعادة الجلسة من Drive فقط بلا Colab Secret أو هاتف أو OTP ما دامت Telegram تقبل الجلسة. لا يعرض هذا التصميم API Hash أو session أو هاتف أو OTP في React أو السجلات أو artifacts.

الصيغة الافتراضية الجديدة هي **Vault format 3 (Drive-managed)**. تبقى format 1 وformat 2 قابلة للاستعادة؛ تحتاج format 2 مفتاحها الخارجي مرة واحدة فقط، ثم تُنشر format 3 versioned بصورة ذرية بعد نجاح الاستعادة. لا يصبح البديل نشطًا قبل اكتمال staging/manifest، ولا يمس فشل الاستعادة إلا النسخة المحلية المؤقتة.

## واجهة React وGradio

حقل رابط القناة/الرسالة يستمد آخر قيمة محفوظة من backend الحي عبر `LiveUiStateService.snapshot()` ويعيدها في React وGradio. الحفظ يتم بعد نجاح التحليل أو من زر/blur صريح، ويمكن مسحه صراحةً. القيمة تحفظ في SQLite settings ضمن Runtime المشروع؛ لا تستخدم `localStorage` أو `sessionStorage` ولا تذهب إلى Drive. لا توجد حالة React وهمية أو backend جديد.

## الأدلة المحلية

| البوابة | النتيجة |
|---|---|
| Python | `779 passed` |
| launcher | `53/53 ready actions resolve` |
| notebook check + cmp | PASS |
| React contracts | `34/34 PASS` |
| lint/build | PASS؛ تحذيرات baseline فقط |
| package build | PASS؛ `570612` bytes، SHA `28d94129…90b79` |

## حد الأمان

اختار المالك صراحةً أن Drive هو حد الحماية العملي للـVault. من يملك صلاحية كاملة لزوج Vault النشط في `TeleDrive_AppData` يستطيع استعادة جلسة Telegram؛ لا يُنشر أي credential في logs/Git/UI. راجع `docs/decisions/ADR-004-session-vault.md`.

## ما لم يثبت

لا `Colab-ready` ولا `Complete` بعد. يجب اختبار Cells 1–4 حيًا بالحزمة المنشورة على Drive نفسه، وإثبات `telegram session vault: restored` ثم `Gradio · Live bridge`. لم تُقرأ أو تُحذف أي جلسة Drive ولم يُرسل OTP أو يُجر اختبار Telegram حي ضمن M43.

## التراجع

قبل الدمج: حذف الفرع فقط. بعد الدمج: revert لـM43 ثم نشر ZIP/manifest متطابقين مع SHA المطلوب، دون حذف release/tag أو Vault تلقائيًا.
