# بطاقة تسليم AI

> آخر جلسة فقط. الأدلة التاريخية موجودة في `docs/PHASE_REPORTS/`.

## بطاقة الجلسة — M32-T01: استبدال ذري لجلسة Telegram التالفة

| الحقل | القيمة |
|---|---|
| المستودع | `body199-cmyk/drive-buddy-3579bf74` |
| فرع العمل | `fix/m32-t01-atomic-telegram-session` |
| خط الأساس | `c1a379708cc2da697e67c3147b269d6a4a57120d` |
| الحالة | **Implemented + fake-tested + full-gated local candidate؛ commit/PR/CI/merge/publish pending** |
| التقرير | `docs/PHASE_REPORTS/PHASE_M32_ATOMIC_SESSION_REPLACEMENT.md` |

## ما تغير

يعتمد `SessionVault` الآن زوج جلسة مُؤرشفًا بإصدار وملف بيان نشط. ترفع جلسة الإصدار وبياناتها أولًا، ولا يصبحان المصدر النشط إلا عند نشر البيان بعد اكتمال الرفع. إذا انقطع الحفظ أو فشل قبل البيان، تبقى الجلسة السابقة على Drive قابلة للاستعادة. ولا يزال Vault القديم مدعومًا للقراءة حتى يحل محله دخول ناجح.

تصنّف `TelegramAuth` أخطاء الجلسة المحفوظة مثل `AuthKeyDuplicatedError` كحاجة لتسجيل جديد: يفصل العميل ويرمي الملف المحلي الذي ثبت فساده فقط، ثم يعود إلى إدخال الهاتف. لا تحذف هذه الحالة زوج Drive القديم. ولا تزال أخطاء الاتصال العابر تحافظ على النسخ كي يعاد التحقق لاحقًا.

## الأدلة

| الفحص | النتيجة |
|---|---|
| اختبارات Vault/TelegramAuth/Telegram flow المركزة | `70 passed` |
| Python كامل | `746 passed` |
| Launcher | `51/51 ready actions resolve` |
| مولد النوتبوك + التطابق | ناجحان |
| Frontend lint/build | ناجحان عبر `pnpm` |
| React contracts | `26/26` ناجح |
| React bridge | `13 passed` |

لم تدخل أسرار أو ملفات جلسات أو OAuth إلى Git. لم يجر اختبار Colab جديد لهذه المرحلة؛ الجلسة الأصلية التي أُبلغ عن بطلان مفتاحها لم تُحذف أو يعاد استخدامها.

## الخطوة التالية

نفّذ مراجعة فرق وأسرار أخيرة، ثم commit وpush وPR إلى `main`، وادمج فقط بعد نجاح CI الفعلي. بعد الدمج شغّل **Publish current TeleDrive package**، وتحقق من manifest والحزمة المنشورة. حتى تجربة Colab حقيقية مستقلة على الحزمة الجديدة، لا توصف الحالة بأنها `Colab-ready` أو `Complete`.
