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
3. **شغّل** الخلايا بالترتيب. في الخلية 4 اختر `UI_MODE`: `Modern_Web_Dashboard` (FastAPI على 8765)، أو `Classic_Gradio_Backup` (7860)، أو `Run_Both_Together`.
   لوحة الويب الحديثة منظمة في خمس خطوات، وتتضمن ثلاثة ألوان (فاتح/خافت بأسلوب X/داكن كامل)، وتحليلًا تلقائيًا يميّز رابط القناة من رابط الرسالة، وصندوق نتائج مستقل التمرير، وإعدادات التوازي والتحديث، واستعراض/إنشاء/اختيار مجلد Drive. تسجيل Telegram يفتح حقول Gradio الآمنة؛ لا تُرسل مفاتيح API أو الهاتف أو OTP أو 2FA عبر الويب.
   In cell 4 choose the modern FastAPI dashboard (8765), classic Gradio (7860), or both. The modern dashboard is organized as five workflow steps and includes light/X-style dim/full-dark themes, automatic channel-vs-message link detection, an independently scrolling results pane, concurrency/refresh settings, and Drive folder browsing/creation/selection. Telegram credentials and codes remain in secure Gradio fields.
4. **فوّض Google Drive** من مطالبة Colab الأصلية في الخلية 3. لا ترفع ملف OAuth Desktop JSON. بعد الاتصال اختر مجلد الوجهة من بطاقة «وجهة الحفظ في Google Drive» في لوحة الويب.
   Authorize Drive through Colab's native prompt in cell 3 (no OAuth Desktop JSON upload), then choose the save destination from the modern dashboard's Drive folder card.
5. **الصق** رابط تيليجرام في لوحة التحليل، اضغط Analyze، حدّد الملفات، ثم أضفها للطابور وابدأ النقل.

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
