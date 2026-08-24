# M43 — Vault Drive-managed وحفظ رابط الفحص

## الحالة

**MERGED + CI-PASSED + PACKAGE-PUBLISHED — Colab live pending.** لا يوجد ادعاء بأن Colab live أو React bridge الحي قد أُثبتا في هذه المهمة.

## طلب المالك

طلب المالك أن يسجل Telegram مرة واحدة على حساب Google Drive نفسه، ثم يعيد تشغيل Colab من دون Colab Secrets أو OTP عند صلاحية الجلسة. كما طلب أن يحتفظ حقل فحص القناة/الرسالة بآخر رابط حتى يغيره أو يمسحه بنفسه، وألا تكون واجهة React حالة مستقلة عن المشروع الحقيقي.

## السبب والتصميم

كانت Vault format 2 تخفي API Hash من Drive وتحتاجها لفك session blob. M42 أصلح تمرير ذلك المفتاح لكن بقيت تجربة Colab Secrets إلزامية. تضيف M43 Vault format 3، وهي صيغة Drive-managed أقرها المالك صراحةً: session blob المموّه وAPI metadata الضرورية للاستعادة موجودة في زوج versioned داخل `TeleDrive_AppData`.

| المسار | السلوك بعد M43 |
|---|---|
| Vault format 3 صالحة | Cell 3 يأخذ API ID/Hash من probe الخاص بـDrive فقط، وCell 4 تستعيد Telegram بلا Secret أو هاتف أو OTP |
| Vault format 2 صالحة | تستخدم المفتاح الخارجي المتاح مرة واحدة؛ بعد تفويض Telegram تنشر Vault format 3 ذريًا |
| Vault منتهية/مرفوضة | تنظيف محلي فقط ثم مسار تسجيل يدوي؛ زوج Drive لا يُحذف قبل نجاح جلسة بديلة |
| آخر رابط تحليل | يُحفظ بعد التحقق في SQLite settings الخاصة بالـbackend ويظهر في live snapshot؛ زر مسح صريح في React وGradio |

لا يعرض React API Hash أو session أو الهاتف أو OTP. رابط التحليل لا يخزن في `localStorage` أو Drive ولا يوجد backend موازٍ؛ يمر عبر الـAction Registry وGradio bridge والسياق نفسه.

## الملفات الجوهرية

| الملف | التغيير |
|---|---|
| `session_vault.py` | format 3، probe محدود محليًا، restore/migration آمنان، status لا يعرض API Hash |
| `notebook_cells.py` | Cell 3 يفضل Vault Drive-managed، ويجعل Colab Secrets مسار ترقية اختياري لـformat 2 |
| `services.py` / `handlers.py` / `action_registry.py` | حفظ ومسح الرابط في backend والـSQLite وفي Action Registry الحقيقي |
| `react_bridge.py` / `bridgeTypes.ts` / `TeleDriveSandbox.tsx` | رابط فحص حي محفوظ، حفظ عند مغادرة الحقل/نجاح التحليل، وزر مسح |
| `ui.py` | حقلا حفظ/مسح واضحان في Gradio ومربوطان عبر Binder، من دون أفعال ready غير موصولة |
| `react_panel_assets/panel.bundle.gz` | معاد بناؤه من React source |

## الأدلة المحلية

| البوابة | النتيجة |
|---|---|
| اختبارات M43 المستهدفة | `66 passed` |
| اختبار Python الكامل | `779 passed` |
| `compileall` | PASS |
| launcher | `53/53 ready actions resolve` |
| notebook check + byte cmp | PASS؛ artifacts مولدة فقط من `notebook_cells.py` |
| React lint/build | PASS؛ تحذيرات baseline فقط |
| عقود React–Gradio | `34/34 PASS` |
| build panel | rebuilt: `234934` JS bytes, `21598` CSS bytes |
| package build المؤقت | PASS؛ SHA-256 `28d94129a9894fee0cf31545d286c176403c814c45203dbaf0e002eb7a390b79`، حجم `570612` bytes |

## مراجعة المخاطر

صيغة Drive-managed تفضّل السهولة على حد تشفير مستقل: من يملك الوصول الكامل إلى زوج Vault النشط على Drive يمكنه استعادة Telegram. هذا اختيار مالك موثق في ADR-004. لا تظهر القيم في السجلات أو النوتبوك أو React أو Git. لا تحذف M43 release/tag أو Session Vault أو `.part`، ولا تعدل `requirements.lock` أو lockfiles.

## ما لم يثبت بعد

لا يزال مطلوبًا اختبار Colab حي جديد: Cells 1–4 على الحساب نفسه، وظهور `Telegram restore source: Drive-managed vault` ثم `telegram session vault: restored` و`Gradio · Live bridge`. لم ننفذ OTP أو نقلًا حيًا ولا قرأنا محتويات Vault.

## الدمج والنشر

دُمج [PR #91](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/91) عند `2d5893dea014c638937e953919c68f2251d035ef` من commit المصدر `e974dfd12f2bf372e34dbca463a082b7017400e2`. نجح CI في [push #32689166257](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689166257) و[PR #32689176699](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689176699) بوظيفتي Python وFrontend.

توقف [Publish #32689333249](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689333249) fail-closed بسبب اختلاف حجم ZIP القديم؛ لم يحذف release أو tag. بُني archive وmanifest من merge SHA، واستُبدل الأصلان الرسميان معًا ثم تحقق تنزيل عام غير مخزّن من SHA والحجم. نجح [Publish #32689575111](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689575111) في التحقق العام. الزوج الرسمي: SHA-256 `28d94129a9894fee0cf31545d286c176403c814c45203dbaf0e002eb7a390b79`، حجم `570612` bytes، commit `2d5893d…`.

## التراجع

يعكس merge `2d5893d…` ثم ينشر ZIP/manifest متطابقان مع SHA المستهدف عبر workflow fail-closed؛ لا تُحذف release/tag ولا Vault تلقائيًا.
