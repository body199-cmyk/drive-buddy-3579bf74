# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

| الحقل | القيمة |
|---|---|
| TASK ID | `M24-T01` |
| العنوان | حفظ جلسة Telegram على Drive والاستعادة التلقائية عبر الويب وColab |
| الحالة | **Implemented + fake-tested. Not live-verified** — ليس Colab-ready ولا Complete |
| المالك التنفيذي | LM Arena Agent |
| الفرع | `arena/01a01447-drive-buddy-3579bf74` |
| سابق على main | `29b7f48` |
| الخطوة التالية | المالك: دمج + Publish package + فحص حي على نفس حساب Drive |

## ما تغيّر

- `SessionVault` يحفظ/يستعيد `telegram.session` + `telegram_creds.json` على `TeleDrive_AppData`.
- واجهة Gradio: حفظ / استعادة / نسيان + autorestore عند فتح الصفحة.
- النوت‌بوك: Drive أولًا ثم probe؛ تخطي إدخال API إن وُجدت الخزينة.

## انحرافات

- لم يُستبدل `session_vault.py` بالكامل: دوال ADR-004 بقيت لأن `telegram_auth.py` محمي.
- الخليتان 3/4 لم تُستبدلا حرفيًا بنص DOC: بقي Colab Secrets وkeep-alive و`blocking=False` حتى لا ينكسر مسار Colab الحالي.
- أُضيف زر استعادة يدوي لأن عقد الربط يفرض `binder.wire` لكل فعل جاهز.
