# ACTIVE_TASK

| الحقل | القيمة |
|---|---|
| TASK ID | `M37-T02` |
| العنوان | تحقق حي من أزرار التحكم في الواجهة (طلب المالك: «جاهز للاستعمال وبالأذات أزرار التحكم») |
| الحالة | **LIVE-VERIFIED (local Windows) — توثيق فقط؛ ينتظر push + PR + CI** |
| Branch | `fix/m37-t02-ui-controls-verification` (base: main `60f8246`) |

## الإثبات المنفذ

1. **سيرفر حي محليًا** (`teledrive_launcher.py` بلا `--share`): bootstrap سليم · HTTP 200 · binder أكمل: **51 action kinds wired (242 controls) — صفر معطلة/مخفية**.
2. **نقرات حية موثقة في سجل السيرفر** (من متصفح فعلي): `settings.set_concurrency`، `settings.set_theme` ×2، `settings.toggle_language` ×2 — كلها انتهت بـ`ok`.
3. **استدعاء مباشر للأكشنات الـ51 الجاهزة بنفس مسار الزرار** (`Handlers.call`):
   - 30 PASS بدون وسائط + 7 PASS بوسائطها الحقيقية (بما فيها رفض concurrency=999 خارج المدى — حارس يعمل).
   - 14 خطأ حالة **صحيح بالتصميم** أثناء عدم الاتصال (`telegram is not authorized` / `drive is not connected` / `nothing selected`…) — حراس آلة الحالات ترد نظيفًا ولا تنهار.
   - 2 خاصّان بـColab عمدًا: `drive.connect/reconnect` عبر `google.colab.auth` الأصلية (بوابة Drive الحية منذ PHASE_16).

## الخلاصة الصادقة

لا زرار ميت ولا غير موصول؛ كل «فشل» مرصود هو حارس حالة صحيح أو بوابة Colab-by-design. انجماد عابر واحد لتاب الإعدادات على port 7861 لم يتكرر وليس له دليل سجل → لا يُسجل (لا شكوك نظرية).

## الحدود الصادقة (§17)

ليس إثبات `Colab-ready`: النقل الفعلي Telegram→Drive يحتاج جلسة Colab حية بيد المالك (M15-T01/M24-T06 مفتوحة). التفصيل: `docs/PHASE_REPORTS/PHASE_M37_T02.md`.
