# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

| الحقل | القيمة |
|---|---|
| TASK ID | M18-T03 |
| العنوان | **التصنيف العميق لأخطاء تسجيل دخول Telegram — «خطأ غير معروف. [fd41da8b]» عند «إرسال الكود» والكود لا يصل** — السبب الجذري: `_handle_send_error` في `telegram_auth.py` (ملف محمي، بتفويض المالك) لم يكن يصنّف سوى `FloodWaitError`؛ و`auth.sendCode` أول استدعاء يحمل زوج api_id/api_hash فكل رفض (`ApiIdInvalidError`/`PhoneNumberInvalidError`/`PhoneNumberFloodError`/نقل) كان ينتهي `err.unknown` |
| الحالة | **PR #33 مدموج في main `6281a66` (2026-08-12، بأمر المالك) — CI بعد الدمج أخضر (run `31544521923`)**؛ المتبقي بيد المالك: إعادة نشر التاج + Colab الحي |
| المالك التنفيذي | LM Arena Agent |
| المهندس | Brain (§10) |
| Base SHA | `1d72ba12e93bb929f9392a1c67bae50fb998007b` (= رأس `main`، PR #31 = M18-T02 — مُتحقق بفحص §9 كاملًا) |
| Result SHA | **`6281a66`** — commit دمج PR #33 على main |
| النطاق | تصنيف فقط داخل الملف المحمي `telegram_auth.py` (بتفويض صريح): `_TRANSPORT_EXC` + `_SEND_CODE_RPC_KEYS` + 3 فروع تصنيف (`_handle_send_error`/`_handle_code_error`/`verify_password`) · 3 مفاتيح locale × لغتين · 7 اختبارات إثبات · تحديثات الذاكرة |
| خارج النطاق | منطق تسجيل الدخول نفسه (لم يُمس) · `set_credentials` (مغطى بـM18-T02 في handlers.py) · كل الملفات المحمية الأخرى · النوت‌بوكات · locks · frontend · أسرار المالك |
| الدليل الرئيسي | compileall ok · pytest: **589 passed** (كان 582) · launcher `--check`: **45/45** · notebook_cells `--check` in sync · cmp identical · `package_service --build` ok · `git diff --stat`: 4 ملفات **+193/−0** |
| الخطوة السابقة (مُغلَقة) | M18-T02 — PR #31 مدموج في `1d72ba1`، والتاج أُعيد نشره منه (run `31441568038`) — كلاهما مُتحقق عبر git/gh هذه الجلسة |
| الخطوة التالية | **بانتظار المالك فقط:** إعادة نشر التاج `pkg-2026.08.09-m15t07` يدويًا من main الجديد `6281a66` (Actions ← Publish current TeleDrive package ← Run workflow — توكن Arena بلا `actions:write`: 403 مؤكد بمحاولة فعلية هذه الجلسة) ← في Colab: Restart runtime ← Cell 1 ← الخلايا 2–4 ← محاولة «إرسال كود» حقيقية: الرسالة يجب أن تسمّي السبب (`err.bad_api_pair`/`err.tg_phone_invalid`/`err.tg_phone_flood`/`err.tg_connect_failed`) بدل `err.unknown` — سطر `failed:` المنقّح في تبويب Logs هو سجل التأكيد |

## انحرافات عن §10 / نقاط صدق

- السبب الدقيق في جلسة المالك (أي صنف من الجدول) لم يُثبت بسطر سجل — المالك أرسل رسالة الواجهة فقط؛ الإصلاح مصمم ليجعل المحاولة القادمة تسمّي السبب بنفسها (لا ادعاء بمعرفة الصنف قبل ظهوره — §17/§20).
- أصناف RPC نادرة أخرى في `send_code` (مثل `ApiIdPublishedFloodError`) تبقى في fallback `err.unknown` عمدًا.
- لا متصفح/Colab حي في الساندبوكس → الإثبات الحي بيد المالك (KNOWN_ISSUES #41، M15-T01).
- توكن Arena بلا `actions:write` → إعادة نشر التاج يدويًا بيد المالك كما في M15-T16/M18-T02.
