# المهمة النشطة

| الحقل | القيمة |
|---|---|
| TASK ID | `M45-T02` |
| العنوان | فحص التكرار بين قطع الرفع (8 MiB) لمنع تنزيل المكرر + التعافي التلقائي لـ SQLite من `readonly database` |
| الأساس | `d991cf4783545ee838d3c2eeaf3b98fc0c22cf6f` — main بعد M45-T01 |
| التقرير | `docs/PHASE_REPORTS/PHASE_M45_T02_DUPLICATE_PRECHECK_AND_SQLITE_RECOVERY.md` |

## النطاق

- **قفل Drive لكل قطعة (`8 MiB`):** تحرير `_drive_lock` بين استدعاءات `request.next_chunk()` في `upload_resumable` بحيث يمر `_duplicate_precheck()` في أجزاء الثانية بين القطع ويكتشف الملفات المكررة قبل تنزيلها من تيليجرام (`Pending -> Skipped`).
- **التعافي التلقائي لقاعدة بيانات SQLite:** إضافة `_RecoveringCursor` و`_reconnect()` و`timeout=30.0` في `database.py` لمعالجة `attempt to write a readonly database` التي ظهرت في التشغيل الحي على Colab.
- **تصنيف أخطاء SQLite العابرة:** إضافة `readonly database` و`database is locked` و`disk i/o error` إلى `TRANSIENT_MARKERS` في `error_handler.py`.
