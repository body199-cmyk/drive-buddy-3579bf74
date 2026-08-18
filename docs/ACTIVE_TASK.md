# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

| الحقل | القيمة |
|---|---|
| TASK ID | `M24-T03` |
| العنوان | تقوية خزينة جلسة Telegram — pre-paint autorestore, logout wipe, in-memory credential fallback, restored-blob validation |
| الحالة | **Implemented + fake-tested. Not live-verified** — ليس Colab-ready ولا Complete |
| المالك التنفيذي | LM Arena Agent |
| الفرع | `arena/m24-t03-session-vault-hardening` |
| Base SHA | `a7b915cf493230e9d9ccaa79d309d50117e45171` |
| Result SHA | (يُسجَّل بعد الدفع) |
| الخطوة التالية | مراجعة Brain/المالك → دمج PR → تحقق حي Colab (M24-T04) |

## ما تغيّر

- `SessionVault.autorestore_once()` يُنادى من `ui.build()` قبل `gr.Blocks`، فأول رسم يقرأ حالة حقيقية بلا اعتماد على page-load.
- `h_telegram_logout` ينادي `forget_quiet()` قبل `telegram_auth.logout()` (الملف محمي).
- `save_now` يقرأ `api_id/api_hash/phone` من ذاكرة `TelegramAuth` عند فراغ حقول الواجهة.
- `save_after_login()` بعد `verify_code` / `verify_password` / `set_credentials` الناجحة، ويتخطى الرفع لو الخزينة موجودة.
- الاستعادة ترفض أي blob لا يبدأ بـ`SQLite format 3` ولا تكتبه على القرص.
- `binder.load` صار idempotent عبر إعادة الرسم بتغيير اللغة.

## انحرافات / قيود

- لا تعديل على أي ملف محمي (§2.3): `telegram_auth.py` / `drive_auth.py` / النوتبوك / اللوكات وغيرها لم تُلمَس.
- لا مفاتيح ترجمة جديدة، ولا actions جديدة، ولا تعديل على `ERROR_ARITY`.
- الخطر مقبول بقرار المالك: `telegram_creds.json` يبقى JSON صريحًا على Drive (مُسجَّل في KNOWN_ISSUES).
- التحقق الحي غير ممكن من Arena؛ الحالة تبقى Implemented + fake-tested حتى M24-T04.
