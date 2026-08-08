# PHASE 10 — تشغيل Colab الحقيقي (قالب فارغ، غير منفَّذ)

> **الحالة: NOT STARTED.** لا يُملأ هذا الملف إلا بيد المالك بعد تشغيل حقيقي في Google Colab.
> ممنوع منعًا باتًا ملء أي حقل هنا من Agent أو من لقطة شاشة أو من mock. §17 و§20.
> هذا الملف هو البوابة الوحيدة للانتقال من `Code-complete candidate` إلى `Colab-ready`.

## 0. بيانات التشغيل

| الحقل | القيمة |
|---|---|
| التاريخ (UTC) | |
| نسخة Colab / Python | |
| commit SHA المختبَر | |
| اسم الأرشيف المستخدم | teledrive_v4.5.zip |
| المنفّذ | المالك |

## 1. البيئة

- [ ] الأرشيف استُعيد داخل `/content` محليًا (لا mounted Drive، لا FUSE)
- [ ] SQLite على تخزين محلي مع WAL
- [ ] `share=False` مؤكَّد
- [ ] اللغة الافتراضية عربية RTL

## 2. مصادقة Telegram (§13)

- [ ] الوصول إلى `READY_FOR_PHONE`
- [ ] `CODE_REQUESTED` مع حفظ `phone_code_hash` صحيحًا
- [ ] `AUTHORIZED` بحساب مستخدم عبر Telethon (ليس Bot API)
- [ ] مسار 2FA إن وُجد: `PASSWORD_REQUIRED` ثم مسح كلمة المرور فورًا
- [ ] لا ظهور لأي سر في السجلات

المخرجات المنقّحة:
```plain
<الصق هنا>
```

## 3. مصادقة Drive (§13)

- `colab_auth.authenticate_user` نجحت
- `about().get(...)` أعادت المستخدم والحصة فعليًا
- لا OAuth JSON ولا InstalledAppFlow ولا token file

المخرجات المنقّحة:

```
<الصق هنا>
```

## 4. نقل ملف حقيقي واحد (§15)

| **الخطوة** | **نجحت؟** | **الدليل** |
|---|---|---|
| bounded scan (message أو group أو range) |  |  |
| فحص التكرار الحتمي |  |  |
| فحص حصة Drive |  |  |
| حجز مساحة محلية |  |  |
| تنزيل `.part` |  |  |
| تحقق الحجم محليًا |  |  |
| رفع resumable |  |  |
| تحقق Drive ID/parent/size |  |  |
| checkpoint آمن |  |  |
| Uploaded + تنظيف موجَّه |  |  |

## 5. الإغلاق والاستعادة

- shutdown يوقف UI ويلغي المهام ويحفظ checkpoints ويغلق SQLite
- recovery بعد إعادة التشغيل بلا auto-resume
- cancel/stop لا يحذف أي ملف على Drive
- السجلات منقّحة بالكامل

## 6. الحكم النهائي

| **الحقل** | **القيمة** |
|---|---|
| الحالة الصادقة بعد التشغيل | Code-complete candidate / Colab-ready / Complete |
| ما فشل |  |
| ما لم يُختبر |  |
| الخطوة التالية الأصغر |  |

> `Complete` تتطلب: Colab-ready + نقل حقيقي موثّق + shutdown + recovery + سجلات منقّحة + handoff. أي نقص = ليست Complete.
