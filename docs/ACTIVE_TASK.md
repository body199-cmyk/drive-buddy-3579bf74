# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

| الحقل | القيمة |
|---|---|
| TASK ID | `M26-T01` |
| العنوان | Transfer control — Pause / Stop / Resume تعمل فعليًا أثناء النقل |
| الحالة | **Implemented + fake-tested. Not live-verified** — ليس Colab-ready ولا Complete |
| المالك التنفيذي | LM Arena Agent |
| الفرع | `arena/m26-t01-transfer-control` |
| Base SHA | `26fd421e68637f5d6b40b25864f6252613081fb3` |
| Result SHA | لم يُنشأ commit بعد؛ تغييرات محلية خضعت للبوابات المطلوبة |
| الخطوة التالية | مراجعة المالك ثم موافقته الصريحة على commit/push/PR/merge؛ يلي الدمج اختبار Colab حي |

## ما تغيّر

| المحور | التغيير |
|---|---|
| RC-1 | أعلام Pause/Stop أصبحت `threading.Event` آمنة بين خيط Gradio وAsyncRuntime. |
| RC-2 | callbacks التحميل والرفع تفحص التحكم كل chunk وترفع إشارات تعاونية لا تعد فشلًا. |
| RC-3 | drain loop لا يلغي المهام بالقوة؛ يجمعها بعد اكتمال الإيقاف التعاوني. |
| RC-4 | الاستئناف يعيد Paused إلى Pending ويطلق drain جديدًا عند الحاجة. |
| RC-5 | Start جديد يصفر أعلام Stop/Pause المتبقية من تشغيل سابق. |
| RC-6 | عناصر progress الموقوفة تحرر بلا تعديل عدادات النجاح أو الفشل. |

## انحرافات وقيود

لا تغيير في action IDs أو handlers أو ترتيب المخرجات أو `ERROR_ARITY` أو i18n أو الواجهة. لا تُقاطع مراحل `Verifying` و`UploadedPendingCheckpoint` عمدًا؛ وذلك يمنع ترك ملف Drive يتيمًا. لا حذف من Drive أو blind cleanup في مسارات Pause/Stop. الاختبار الحي على Telegram وDrive وColab لم يُنفذ.
