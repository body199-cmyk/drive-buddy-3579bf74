# PHASE M25-T01 — Colab Secrets + session vault + keep-alive

- TASK ID: `M25-T01`
- التاريخ: 2026-08-13
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
