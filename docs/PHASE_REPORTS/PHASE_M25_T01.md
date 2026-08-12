# PHASE M25-T01 — شقّان مستقلان بنفس المعرّف

TASK ID `M25-T01` استُخدم في جلستين متوازيتين. هذا الملف يجمعهما ولا يمحو أيًّا منهما.

---

# أ) خزنة جلسة تليجرام + أسرار Colab + keep-alive

- التاريخ: 2026-08-13
- الفرع: `arena/019ff850-drive-buddy-3579bf74`
- الحالة: Code-complete candidate + Fake-tested (ليس Colab-ready)

## الهدف

بعد موت جلسة Colab لا يمكن تشغيل الخلية الأخيرة وحدها. المطلوب تقليل الألم: عدم إعادة كتابة API ID/Hash، وعدم إعادة OTP بعد أول دخول ناجح، وتأخير فصل الخمول.

## ما نُفِّذ

- `teledrive/session_vault.py`: حفظ/استعادة/مسح بلوب معمى + `start_keepalive`.
- `telegram_auth.py`: حفظ بعد AUTHORIZED، مسح عند logout.
- `drive_client.py`: `upsert_bytes` / `delete_file` / `mime_type` على `upload_bytes`.
- الخليتان 3 و4 في المولد (سبع خلايا كما هي).
- ADR-004 يسجّل تجاوز المالك لقاعدة «الذاكرة فقط».

## ما لم يُثبت

مصادقة تليجرام/Drive حية داخل Colab، واستعادة الخزنة على VM جديد حقيقي.

---

# ب) جلسات الطابور + بدء كل المعلّق + مسح غير المكتمل (مدموج PR #44 → `ce28004`)

```plain
UTC: 2026-08-12
Base SHA: 0c394a859770844a0526d54f4369923d05385138
Branch: arena/019ff846-drive-buddy-3579bf74
Status: MERGED INTO MAIN ce28004 · Code-complete candidate + Fake-tested
```

## Problem

After a Colab Restart, SQLite still holds leftover queue rows while the in-memory analyze selection is empty. `queue.start_selected` resolved that empty selection to "start nothing".

## Changes

- Start button (`None`) falls back to every startable Pending/NeedsRetry/Downloaded row. Explicit `[]` still starts nothing.
- New ready action `queue.clear_incomplete` deletes unfinished SQLite rows only. Drive files are never deleted.
- React Stop confirm: stop only, or stop + clear incomplete. Gradio keeps a separate button.
- Live snapshot carries `chatTitle` + `createdAt`; React groups by channel + date.

## Local gates (queue session)

`652 passed` · launcher `48/48` · notebooks identical · frontend contracts `22/22`.
