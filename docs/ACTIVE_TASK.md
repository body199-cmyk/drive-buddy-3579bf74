# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

| الحقل | القيمة |
|---|---|
| TASK ID | `M25-T01` |
| العنوان | جلسات الطابور + بدء كل المعلّق + مسح غير المكتمل عند الإيقاف |
| الحالة | **MERGED INTO MAIN · Code-complete candidate + Fake-tested** — PR #44 مدموج؛ **ليس** Colab-ready ولا Complete |
| المالك التنفيذي | LM Arena Agent |
| المهندس/المراجع | Brain عبر ClickUp Docs |
| الفرع | `arena/019ff846-drive-buddy-3579bf74` |
| Base SHA | `0c394a859770844a0526d54f4369923d05385138` |
| PR #44 | [MERGED](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/44) → merge `ce28004fda34943c7224877c5bd3eb5338ed4656` (2026-08-12T23:30:45Z) · CI على الـPR: Frontend PASS + Python PASS |
| الخطوة التالية | ① المالك: Actions → Publish current TeleDrive package → Run on `main` · ② Colab Restart → Cell 1 · ③ Cells 2–4 ثم Start للمعلّق أو إيقاف → مسح غير المكتمل |

## لماذا هذه المهمة

بعد Restart في Colab تبقى صفوف SQLite (مثل 191 معلّق) بينما التحديد في الذاكرة فارغ، فكان `queue.start_selected` يرفض البدء. Pause يُبقي الصفوف عمدًا وStop كان يوقف العمال فقط بلا مسح.

## انحرافات

- `package-lock.json` ناتج عن `npm install` في الساندبوكس **غير مُتتبَّع** (القفل القانوني `bun.lock`).
- لم يُمس أي ملف محمي للنوت‌بوك أو Telegram/Drive auth أو transfer_manager أو database/migrations.
- `queue_manager.py` عُدّل بطلب المالك الصريح لتغيير سلوك Start/Stop/Clear.
