# TeleDrive v2 — Telegram → Google Drive

نقل الميديا من تيليجرام (رسائل، ألبومات، قنوات، محادثات محفوظة) إلى Google Drive باستخدام Google Colab فقط. لا خوادم، لا اشتراكات، وكل شيء داخل حسابك.

Transfer media from Telegram to Google Drive using only Google Colab. No servers, no subscriptions, everything stays in your accounts.

## متطلبات — Requirements

1. حساب Google (Drive) — Google account with Drive
2. رقم هاتف مسجّل على تيليجرام — Telegram phone number
3. Colab (المجاني كافٍ) — free Colab is enough

## الخطوات — Quick start

1. **افتح** `notebook/TeleDrive.ipynb` داخل Colab (File → Upload notebook).
2. **ارفع** الحزمة كـ ZIP في الخلية الأولى.
3. **شغّل** الخلايا بالترتيب: تثبيت → bootstrap → إدخال api_id/hash → إطلاق الواجهة.
4. **افتح** تبويب Google Drive في الواجهة وارفع ملف OAuth Desktop JSON من Google Cloud Console.
5. **الصق** رابط تيليجرام في تبويب "Link & Analyze"، اضغط Analyze، ثم Start.

## القيود الصادقة — Honest limitations

- Colab المجاني قد يفصل الجلسة في أي لحظة. الاسترجاع عبر checkpoints في Drive.
- ملف أكبر من قرص Colab لن يُنقل. سيُرفض قبل التنزيل.
- استئناف التنزيل من تيليجرام غير مضمون لكل ملف. الرفع القابل للاستئناف عبر Drive مضمون داخل عمر جلسة الرفع.
- تيليجرام يفرض FloodWait، لذا وضع Fast ليس سرعة لا نهائية.

## الأمان — Security

- لا أسرار في الكود أو السجلات أو الوثائق.
- `.session` و `client_secret*.json` و `token*.json` في `.gitignore`.
- `share=False` هو الافتراضي. المشاركة العلنية تُطلق تحذيراً واضحاً.

## اختبارات — Tests

```bash
cd python-package
pytest -q
```

جميع الاختبارات تعمل بدون بيانات اعتماد حقيقية عبر mocks (`fake_telegram`, `fake_drive`, `fake_clock`, `fake_fs`).
