# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

| الحقل | القيمة |
|---|---|
| TASK ID | M18-T02 (§10 fix) |
| العنوان | **إصلاح «خطأ غير معروف. جرّب مرة أخرى. [cid]» عند ربط Telegram بعد M18-T01** — السبب الجذري: أخطاء طبقة النقل/الاتصال بـTelegram تفلت غير مصنّفة من `TelegramAuth.set_credentials` (ملف محمي، ثابت قبل/بعد M18-T01) فتصبح `err.unknown`؛ الإصلاح في `handlers.py` يصنّفها إلى `err.tg_connect_failed` المترجم مع بقاء التتبع في السجلات |
| الحالة | COMPLETE — الكود والبوابات خضراء (582 passed · launcher 45/45 · notebooks identical · cmp ok)؛ لقطة Colab بمتصفح حقيقي بيد المالك (لا متصفح في الساندبوكس) |
| المالك التنفيذي | LM Arena Agent |
| المهندس | Brain (§10) |
| Base SHA | `faff35a3af12adb1adf891049917f7add8dc7751` (= رأس `origin/main`، PR #30 = M18-T01) |
| Result SHA | انظر PR من الفرع `arena/019fede6-drive-buddy-3579bf74` (غير مدموج) |
| النطاق | فحص مسار Telegram المتأثر بـM18-T01 فقط (مقارنة 5 ملفات قبل/بعد) · استخراج التتبع المنقّح (إعادة إنتاج محلية بلا أسرار) · تصنيف فشل النقل عند الزر (connect) إلى رسالة مترجمة قابلة لإعادة المحاولة · مفتاحا locale ar/en · اختباران proof · تحديثات الذاكرة (§10 قالب التقرير) |
| خارج النطاق | كل الملفات المحمية (telegram_auth.py تحديدًا — التصنيف العميق داخله يتطلب تفويضًا صريحًا) · تغيير بيانات اعتماد المالك · إعادة تصميم الواجهة · React · أي PR آخر |
| الدليل الرئيسي | compileall: ok · pytest: **582 passed** · launcher `--check`: **45/45 ready** · notebook_cells `--check`: in sync · cmp: notebook ↔ public identical · إعادة إنتاج محلية لنفس المسار: `action=telegram.set_credentials cid=… crashed` → `asyncio.exceptions.IncompleteReadError` في `telegram_client.py:40 connect()` · بعد الإصلاح: «تعذر الاتصال بخوادم تيليجرام… [cid]» + `failed: TeleDriveError: telegram connect failed: IncompleteReadError` |
| الخطوة السابقة (مُغلَقة) | M18-T01 (DOC-39) — PR #30 مدمج في `faff35a` |
| الخطوة التالية | **STOP — بانتظار مراجعة المالك ودمج PR**؛ ثم إعادة نشر التاج `pkg-2026.08.09-m15t07` من main الجديد (release-current.yml أو يدويًا — توكن Arena بلا actions:write، KNOWN_ISSUES #27)؛ في Colab: Restart runtime ← Cell 1 فقط ← Cells 2–4 |

## انحرافات عن §10
- سجلات جلسة المالك (`cid d75de588`) غير متاحة من الساندبوكس — التتبع المنقّح أُعيد إنتاجه على **نفس المسار** محليًا بلا أسرار (عميل Telethon حقيقي + بيانات وهمية)؛ النوع الدقيق في جلسة المالك قد يكون شقيقًا لـ`IncompleteReadError` (Timeout/Connection/OSError/RPC) وكلها تُصنَّف الآن بالمفتاح نفسه.
- لم ألمس `telegram_auth.py` (§10: الخطأ داخله فعلًا → توقف وأبلغ): سدّدت الفجوة من جهة الواجهة (`handlers.py` غير محمي) وأبلغت أن التصنيف العميق داخل الملف المحمي يحتاج تفويضًا صريحًا.
- لا متصفح في الساندبوكس → الإثبات الحي في Colab بيد المالك (الخطوات في `PHASE_M18_T02.md` §6).
