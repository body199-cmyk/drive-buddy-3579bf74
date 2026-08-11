# PHASE_M18_T03 — التصنيف العميق لأخطاء تسجيل دخول Telegram (لا «خطأ غير معروف» عند إرسال الكود)

> **TASK ID:** M18-T03 — **الحالة:** COMPLETE — كود + بوابات خضراء؛ الدمج وإعادة نشر التاج بيد المالك
> **المرجع:** بلاغ المالك في الجلسة: «الاتصال بالتليجرام بيفشل… بضغط إرسال الكود لكن الكود لا يصل إلى تيليجرام ويظهر الخطأ» + الرسالة الحية «خطأ غير معروف. جرّب مرة أخرى. [fd41da8b]»
> **التفويض:** المالك وافق صراحة على لمس الملف المحمي `telegram_auth.py` **للتصنيف فقط** (§10، امتداد KNOWN_ISSUES #40)
> **Base SHA:** `1d72ba12e93bb929f9392a1c67bae50fb998007b` (main = دمج PR #31 = M18-T02)
> **تاريخ التنفيذ:** 2026-08-12 UTC

## 1. الأعراض (مطابقة لبلاغ المالك)

بعد Restart runtime والتحديث إلى حزمة M18-T02 (المنشورة من `1d72ba1`):

1. زر «ربط» (set_credentials) **ينجح** — إصلاح M18-T02 يعمل.
2. المالك يملأ رقم الهاتف ويضغط «إرسال الكود» → **الكود لا يصل أبدًا** وتظهر:

```plain
خطأ غير معروف. جرّب مرة أخرى. [fd41da8b]
```

## 2. التشخيص (مُثبت من الكود قبل أي تعديل)

| الحقيقة | الدليل |
|---|---|
| فحص baseline سليم: HEAD=`1d72ba1`، PR #31 مدموج، التاج `pkg-2026.08.09-m15t07` أُعيد نشره من نفس الكوميت (run `31441568038`، 2026-08-10T23:13:51Z) | `git log` + `gh release view` |
| البوابات قبل التعديل خضراء: `582 passed` · launcher `45/45` | تشغيل محلي من الـvenv |
| الخطأ من خطوة **send_code** وليس connect: الرسالة النصية `err.unknown` + `[cid]` تولد في `TelegramAuth._handle_send_error` الذي لم يكن يعرف سوى `FloodWaitError` وأي خطأ آخر → `TeleDriveError` بمفتاح `err.unknown` الافتراضي | قراءة `telegram_auth.py` + `errors.py` (`message_key = "err.unknown"`) + wrapper `@action` (`f"{t(exc.message_key)} [{correlation}]"`) |
| `ctx.aio.run(coro)` بلا timeout مصطنع (`timeout=None`) → الفشل حقيقي عائد من Telethon، وليس اصطناعًا محليًا | قراءة `async_runtime.py:105-111` |
| M18-T02 غطّى `set_credentials` فقط على مستوى `handlers.py`؛ مسار `send_code` يتحول إلى `TeleDriveError` **داخل** الملف المحمي قبل أن تصل أي تفاصيل للواجهة | مقارنة مساري M18-T02 وsend_code |

## 3. السبب الجذري (لماذا لا يصل الكود)

`auth.sendCode` هو **أول استدعاء** يحمل زوج `api_id`/`api_hash` معًا (ورقم الهاتف)، لذا كل رفض حقيقي من Telegram كان يسقط في هذا الزر مُخفىً خلف `err.unknown`. الأصناف التي كانت تُبلع:

| الصنف (اسم فئة Telethon) | المعنى | كان يظهر |
|---|---|---|
| `ApiIdInvalidError` | زوج api_id/api_hash مرفوض (نسخ ناقص/متبدل من my.telegram.org) | err.unknown ❌ |
| `PhoneNumberInvalidError` | الرقم مرفوض | err.unknown ❌ |
| `PhoneNumberFloodError` | تقييد مؤقت للرقم (ساعات) | err.unknown ❌ |
| `ConnectionError`/`TimeoutError`/`OSError`/`EOFError` (`IncompleteReadError`) | نقل/DC | err.unknown ❌ |

ونقائص شقيقة كان M18-T02 قد وثّقها ولم يصلحها: `verify_code` كان يبتلع فشل النقل إلى `err.unknown` مع أن `phone_code_hash` ما زال صالحًا، و`verify_password` كان يسمّي **أي** فشل «كلمة المرور غير صحيحة» — حتى انقطاع النقل أو FloodWait.

## 4. الإصلاح (بتفويض المالك — تصنيف فقط، لا تغيير في منطق الدخول)

### `python-package/teledrive/telegram_auth.py` (+55 سطرًا، صفر حذف)

- ثوابت جديدة على مستوى الوحدة:
  - `_TRANSPORT_EXC = (ConnectionError, TimeoutError, OSError, EOFError)` — بمقارنة `isinstance`
    (يشمل `asyncio.IncompleteReadError` ⊂ `EOFError`، و`ConnectionError`/`TimeoutError` ⊂ `OSError` — مُدرجة صراحةً للتوثيق).
  - `_SEND_CODE_RPC_KEYS = {"ApiIdInvalidError": "err.bad_api_pair", "PhoneNumberInvalidError": "err.tg_phone_invalid", "PhoneNumberFloodError": "err.tg_phone_flood"}` — بمقارنة الاسم (نفس نمط `FloodWaitError` القائم؛ فئات Telethon غير مستوردة في هذا الملف).
- `_handle_send_error`: بعد فرع FloodWait القائم دون تغيير:
  - نقل → `err.tg_connect_failed` + `READY_FOR_PHONE` (قابل لإعادة المحاولة فورًا).
  - `err.bad_api_pair` → حالة `ERROR` (يجب تعديل البيانات عبر «ربط» — وset_credentials متاح من أي حالة).
  - رقم مرفوض/مقيّد → `READY_FOR_PHONE` مع رسالة مسمّاة.
  - البديل fallback يبقى `err.unknown` + سجل redacted كما كان.
- `_handle_code_error`: فرع نقل جديد → `err.tg_connect_failed` + البقاء في `CODE_REQUESTED` (الهاش محفوظ — نفس الكود يُعاد).
- `verify_password`: فرعان جديدان قبل «password rejected»: نقل → `err.tg_connect_failed`، و`FloodWaitError` → `CooldownError(err.floodwait)` — وكلاهما يبقى في `PASSWORD_REQUIRED`. **لا تغيير** في تصنيف الرفض الحقيقي لكلمة المرور ولا في تصفير المتغير `password` في `finally`.

**لم يُمس:** `set_credentials` (مغطى بإصلاح M18-T02 في handlers.py) · التسلسل الكامل لتسجيل الدخول · القفل/الذاكرة المحمية/الأسرار · أي ملف محمي آخر.

### الترجمة (+3 مفاتيح × لغتين)

`err.bad_api_pair` · `err.tg_phone_invalid` · `err.tg_phone_flood` — في `locale/ar.json` و`locale/en.json`.

### الاختبارات (+7 في `tests/test_telegram_flow_contract.py`)

`test_bad_api_pair_at_send_code_is_named_and_recovers_via_reconnect` · `test_rejected_phone_returns_to_the_phone_step_with_a_named_message` · `test_phone_flood_is_named_instead_of_unknown` · `test_transport_failure_at_send_code_is_classified_and_retryable` · `test_transport_failure_at_verify_code_keeps_hash_and_otp_panel` · `test_transport_failure_at_verify_password_is_not_mislabeled` · `test_flood_at_verify_password_is_not_mislabeled_as_wrong_password`.

## 5. التحقق (مخرجات فعلية)

```plain
$ python -m compileall -q teledrive          → exit 0
$ python -m pytest -q tests                  → 589 passed in 22.57s   (كان 582؛ +7)
$ python teledrive_launcher.py --check       → binding check ok: 45/45 ready actions resolve
$ python -m teledrive.notebook_cells --check → notebooks are in sync
$ cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb → identical (exit 0)
$ python -m teledrive.package_service --build → tests passed · archive OK
$ git diff --stat                            → 4 files changed, 193 insertions(+), 0 deletions(-)
```

لم تُمس النوت‌بوكات ولا `requirements.*` ولا أي ملف frontend — بوابتا bun غير معنيتين (KNOWN_ISSUES #37 قائمة كما هي).

## 6. ما لم يُثبت (صدق §17)

- السبب **الدقيق** لفشل `send_code` في جلسة المالك (أي صنف من الجدول أعلاه) لم يُرَ سطر سجله — المالك أرسل رسالة الواجهة فقط. بعد هذا الإصلاح الرسالة نفسها ستسمّي السبب عربيًا في المحاولة القادمة، وسطر `failed: …` المنقّح في تبويب Logs يبقى للتأكيد.
- لا متصفح ولا Colab حي في الساندبوكس → الإثبات الحي بيد المالك (M15-T01).
- أصناف RPC نادرة أخرى في `send_code` (مثل `ApiIdPublishedFloodError`) ما زالت تسقط في `err.unknown` عمدًا — توسعة مستقبلية إن ظهرت في سجل حي.

## 7. خطوات المالك بعد الدمج

1. دمج PR (بيد المالك).
2. إعادة نشر التاج `pkg-2026.08.09-m15t07` من main الجديد — يدويًا عبر `release-current.yml` (توكن Arena بلا `actions:write`، KNOWN_ISSUES #27).
3. في Colab: Runtime → Restart runtime ← Cell 1 ← الخلايا 2–4.
4. إعادة محاولة «إرسال الكود»: الرسالة الجديدة ستسمّي السبب الحقيقي (بيانات API / الرقم / تقييد مؤقت / شبكة).
