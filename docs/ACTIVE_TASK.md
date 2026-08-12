# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

| الحقل | القيمة |
|---|---|
| TASK ID | `M25-T01` |
| العنوان | جلسات الطابور + بدء كل المعلّق + مسح غير المكتمل عند الإيقاف |
| الحالة | **Code-complete candidate + Fake-tested** — بانتظار دمج PR ثم إعادة نشر الحزمة بيد المالك |
| المالك التنفيذي | LM Arena Agent |
| المهندس/المراجع | Brain عبر ClickUp Docs |
| الفرع | `arena/019ff846-drive-buddy-3579bf74` |
| Base SHA | `0c394a859770844a0526d54f4369923d05385138` |
| الخطوة التالية | ① دمج PR → ② المالك: Actions → Publish current TeleDrive package على `main` · ③ Colab Restart → Cell 1 → 2–4 |

## لماذا هذه المهمة

بعد Restart في Colab تبقى صفوف SQLite (مثل 191 معلّق) بينما التحديد في الذاكرة فارغ، فكان `queue.start_selected` يرفض البدء. Pause يُبقي الصفوف عمدًا وStop كان يوقف العمال فقط بلا مسح.

## انحرافات

- `package-lock.json` ناتج عن `npm install` في الساندبوكس **غير مُتتبَّع** (القفل القانوني `bun.lock`).
- لم يُمس أي ملف محمي للنوت‌بوك أو Telegram/Drive auth أو transfer_manager أو database/migrations.
- `queue_manager.py` عُدّل بطلب المالك الصريح لتغيير سلوك Start/Stop/Clear.
