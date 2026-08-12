# TROUBLESHOOTING — TeleDrive v4.5

| العرض | السبب | الحل |
|-------|-------|------|
| كود تسجيل تيليجرام لا يصل | تيليجرام يرسله داخل التطبيق في شات Telegram وليس SMS | افتح تيليجرام على الديسكتوب، شات "Telegram" |
| `PhoneCodeInvalidError` | كود خاطئ/منتهي | اضغط resend (60s cooldown) وأعد بسرعة |
| `PhoneCodeExpiredError` | انتهت صلاحية hash | ارجع لـ READY_FOR_PHONE واطلب كود جديد |
| `SessionPasswordNeededError` | 2FA مفعل | املأ حقل password قبل verify_password |
| `FloodWaitError` بثوانٍ | حد معدل تيليجرام | TeleDrive يحترم `seconds` تلقائيًا — انتظر |
| Drive "insufficient storage" | Drive ممتلئ | حرر مساحة أو غيّر حساب |
| Colab session died mid-transfer | free runtime | أعد 1–4 (مش الخلية الأخيرة وحدها) ثم Recovery من Drive. إن وُجدت الأسرار + خزنة الجلسة: بلا OTP |
| الخلية 3 تطلب API ID كل مرة | أسرار Colab غير مضافة أو الاسم غلط | أيقونة المفتاح ← `TELEGRAM_API_ID` و`TELEGRAM_API_HASH` حرفيًا ثم أعد الخلية 3 |
| بعد VM جديد يطلب كود تليجرام | أول دخول، أو Logout مسح الخزنة، أو api_hash تغيّر | سجّلي مرة من الواجهة؛ بعدها تُحفظ الجلسة في `TeleDrive_AppData` |
| كولاب فصل رغم keep-alive | تاب مقفول / حد 12 ساعة / سياسة Google | أبقي التاب ظاهرًا؛ Colab Pro أطول؛ لا يوجد تخليد مجاني |
| OAuth "access blocked" (قديم) | هذا تدفق قديم محظور الآن — الدستور يمنعه | استخدم native Colab auth فقط، لا `client_secret.json` |
| Upload size mismatch | خلل شبكة نادر | Item يبقى Failed، `.part` محفوظ، إعادة المحاولة آمنة |
| Duplicate skipped | نفس `source_key` موجود | مقصود — احذف ملف Drive أولًا لإعادة الرفع |
| لغة UI عالقة | toggle في UIState | حدث تبويب Gradio، queue لا يتأثر |
| زر معطل `common.unavailable` | action غير ready (implemented=False أو tested=False) | راجع `action_registry.py` وتقرير PHASE — الزر مخفي عمدًا حتى يثبت باختبار |
| `MountedRootError` عند bootstrap | `TELEDRIVE_ROOT` داخل `/content/drive` | غيّر إلى `/content/teledrive_runtime` — SQLite لا يعمل على FUSE |
| `DeadControlError` عند البناء | زر بدون handler أو service_path لا يحل | تحقق من `ctx.resolve(service_path)` و decorator `@action(id)` |
| `IncompleteBindingError` | ready action موصول لم يُربط | `binder.assert_complete()` يطلب `wire_if_ready` لكل ready |
| checkpoint تالف يشير لـ `teledrive` | بيئة تشغيل فيها مسار قديم | أعد فتح المشروع/الـ Colab runtime — لا يوجد checkpoint تالف في الريبو نفسه |

## قواعد لا تنثني (من CONSTITUTION §4)

- Temp يُحذف فقط بعد رفع موثق (Drive file id + appProperties + size)
- QueueManager فقط يعدل الحالة
- لا أسرار في كود/سجلات/docs أبدًا
- Concurrency ≤4، default 2
- لا ادعاء تحقق حقيقي قبل PHASE_10
