# بطاقة التسليم — M44-T01: مفتاح التحديث التلقائي وسرعة تنزيل Telegram

| الحقل | القيمة |
|---|---|
| Updated (UTC) | `2026-10-19` |
| code commit / merge | غير مدموج بعد (العمل على `arena/1a507b63-drive-buddy-3579bf74`) |
| الحالة | **IMPLEMENTED + LOCAL-TESTED — ليس مدموجًا/منشورًا، ولا Colab live** |
| CI | لم يُشغَّل بعد؛ البوابات المحلية في التقرير |
| التقرير | `docs/PHASE_REPORTS/PHASE_M44_T01_UI_HEARTBEAT_AND_DOWNLOAD_SPEED.md` |

## النتيجة

- **مفتاح التحديث التلقائي:** إعداد backend محفوظ `auto_refresh_ms` بقيم `0/1000/2000/5000` (الافتراضي 1000). React يوقف `setInterval` عند `0`؛ زر `queue.refresh` اليدوي يظل متاحًا، والـrefresh الأحادي بعد الإجراءات يظل يعمل. Gradio shell له نفس الإعداد. لا `localStorage`.
- **سرعة التنزيل:** مسار `download_media_fast()` بطلبات `512 KiB` بدل `128 KiB` للملفات ≥1 MiB غير المصوّرة، مع fallback آمن للمسار القديم وإعادة إطلاق Pause/Stop. الاستئناف يستعمل نفس الحجم صراحةً.
- **AES:** `cryptg==0.6.0` في dependency lock، و`crypto_backend()` يسجّل التطبيق الفعّال (`cryptg`/`libssl`/`pyaes`) عند اتصال Telegram.

## الأدلة المحلية

`795 passed` · compileall PASS · launcher `54/54` · notebooks in sync · React contracts `34/34` · lint 0 errors (8 baseline warnings) · bundle rebuilt · package build PASS (`578225` bytes، `e4723b02…15f6`). `bun run build` غير قابل للتشغيل في sandbox بسبب رفض المرآة لحزمة `@lovable.dev/vite-tanstack-config@2.8.5` وحدها.

## ما لم يثبت / الخطوة التالية

1. نشر الحزمة، Restart، Cell 1 (يثبّت cryptg)، ثم Cells 2–4.
2. في Logs: `telethon crypto backend=cryptg`، ثم قياس سرعة ملف ≥100 MB في Dashboard.
3. اختبار إيقاف/تشغيل التحديث التلقائي حيًا في Colab.
4. إن بقي التنزيل مقيدًا بالزمن: خطوة تالية = 2–4 جداول `iter_download` متوازية مع اختبار حي.
5. توازي رفع Drive يحتاج ADR (قاعدة «Drive service واحد»)؛ `_drive_lock` يبقى كما هو الآن.

## ما لم يُمس

لا تغيير في notebook cells أو `.github/workflows` أو schema SQLite أو Drive/Telegram auth أو session vault. التراجع = revert هذا الـcommit؛ صف `auto_refresh_ms` في SQLite غير ضار.

---

# بطاقة التسليم السابقة — M43: Vault Drive-managed ورابط التحليل المحفوظ

| الحقل | القيمة |
|---|---|
| Updated (UTC) | `2026-08-24` |
| code commit / merge | `e974dfd12f2bf372e34dbca463a082b7017400e2` → main `2d5893dea014c638937e953919c68f2251d035ef` عبر PR [#91](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/91) |
| الحالة | **MERGED + CI-PASSED + PACKAGE-PUBLISHED — Colab live pending** |
| CI | push [#32689166257](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689166257) وPR [#32689176699](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689176699): Python + Frontend SUCCESS |
| publish | [#32689575111](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689575111) SUCCESS |
| التقرير | `docs/PHASE_REPORTS/PHASE_M43_DRIVE_MANAGED_VAULT_AND_ANALYZE_LINK.md` |

## النتيجة المنشورة

تعالج M43 تجربة المالك المطلوبة: بعد تسجيل Telegram وحفظ Vault جديدة على حساب Drive نفسه، يستطيع Runtime Colab جديد استعادة الجلسة من Drive فقط بلا Colab Secret أو هاتف أو OTP ما دامت Telegram تقبل الجلسة. لا يعرض هذا التصميم API Hash أو session أو هاتف أو OTP في React أو السجلات أو artifacts.

الصيغة الافتراضية الجديدة هي **Vault format 3 (Drive-managed)**. تبقى format 1 وformat 2 قابلة للاستعادة؛ تحتاج format 2 مفتاحها الخارجي مرة أخيرة فقط، ثم تُنشر format 3 versioned بصورة ذرية بعد نجاح الاستعادة. لا يصبح البديل نشطًا قبل اكتمال staging/manifest، ولا يمس فشل الاستعادة إلا النسخة المحلية المؤقتة.

## واجهة React وGradio

حقل رابط القناة/الرسالة يستمد آخر قيمة محفوظة من backend الحي عبر `LiveUiStateService.snapshot()` ويعيدها في React وGradio. الحفظ يتم بعد نجاح التحليل أو من زر/blur صريح، ويمكن مسحه صراحةً. القيمة تحفظ في SQLite settings ضمن Runtime المشروع؛ لا تستخدم `localStorage` أو `sessionStorage` ولا تذهب إلى Drive. لا توجد حالة React وهمية أو backend جديد.

## الأدلة

| البوابة | النتيجة |
|---|---|
| Python محليًا وCI | `779 passed` محليًا؛ CI Python SUCCESS في push وPR |
| launcher | `53/53 ready actions resolve` |
| notebook check + cmp | PASS؛ artifacts مولدة من المصدر ومتطابقة |
| React contracts | `34/34 PASS` محليًا |
| lint/build | PASS محليًا وCI Frontend SUCCESS؛ تحذيرات baseline فقط |
| package | archive M43: SHA-256 `28d94129a9894fee0cf31545d286c176403c814c45203dbaf0e002eb7a390b79`، حجم `570612` bytes |
| النشر العام | manifest/ZIP الرسميان يطابقان merge `2d5893d…` والبصمة والحجم أعلاه |

## النشر الآمن

توقف [النشر الأول #32689333249](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689333249) كما يجب fail-closed لأن الأصل المنشور كان `568320` bytes مقابل archive M43 `570612` bytes. لم يُحذف release أو tag.

وبتفويض المالك، بُني archive وmanifest من merge SHA نفسه، واستُبدل الأصلان الرسميان معًا فقط، ثم تحقق تنزيل عام غير مخزن من SHA والحجم والـmanifest. أُزيل أصلان زائدان نتجا من محاولة تسمية مؤقتة بعد تأكيد الزوج الرسمي؛ لم يُحذف release/tag. نجح [workflow #32689575111](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689575111) بعد ذلك في التحقق العام وتحديث metadata إلى merge M43.

## حد الأمان

اختار المالك صراحةً أن Drive هو حد الحماية العملي للـVault. من يملك صلاحية كاملة لزوج Vault format 3 في `TeleDrive_AppData` يستطيع استعادة جلسة Telegram؛ لا تُنشر القيم في logs/Git/UI. راجع `docs/decisions/ADR-004-session-vault.md`.

## ما لم يثبت

لا `Colab-ready` أو `Complete` بعد. يجب تشغيل Cells 1–4 على نفس حساب Drive وإثبات `telegram session vault: restored` ثم `Gradio · Live bridge`. لم يُقرأ أو يُحذف محتوى Vault، ولم يُنفذ OTP أو نقل Telegram/Drive حي ضمن M43. يبقى KNOWN_ISSUES #71 مفتوحًا حتى يظهر bridge الحي في Cell 4.

## التراجع

يعكس merge `2d5893d…` ثم يُنشر ZIP/manifest متطابقان مع SHA السابق عبر مسار release fail-closed. لا يحذف التراجع release/tag ولا Vault تلقائيًا.
