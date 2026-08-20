# المهمة النشطة

| الحقل | القيمة |
|---|---|
| TASK ID | `M32-T01` |
| العنوان | استبدال آمن وذري لجلسة Telegram التالفة |
| الحالة | **Implemented + fake-tested + full-gated local candidate؛ عمليات GitHub والنشر pending** |
| branch | `fix/m32-t01-atomic-telegram-session` |
| Base SHA | `c1a379708cc2da697e67c3147b269d6a4a57120d` |

## النطاق المنفذ

| المسار | السلوك |
|---|---|
| `session_vault.py` | زوج Vault جديد بإصدار + manifest نشط؛ لا تستبدل النسخة القديمة قبل اكتمال الزوج الجديد؛ قراءة متوافقة مع Vault القديم؛ حذف النسخ السابقة فقط بعد الالتزام الناجح؛ `forget/logout` يحذفان كل الإصدارات صراحةً. |
| `telegram_auth.py` | `AuthKeyDuplicatedError` وأخطاء بطلان الجلسة تعيد إلى `READY_FOR_PHONE` بعد تحرير العميل وحذف الجلسة المحلية المثبت فسادها، مع إبقاء Vault على Drive. |
| `tests/test_session_vault.py` | اختبارات إخفاق رفع مرحلي، تنظيف ما بعد الالتزام، وعودة AuthKeyDuplicatedError إلى تسجيل جديد مع احتفاظ Drive. |

## البوابات المنفذة

`746 passed` في Python، `compileall` ناجح، launcher `51/51`، فحص النوتبوك ومطابقته ناجحان، `pnpm lint/build` ناجحان، React contracts `26/26`، وReact bridge `13 passed`.

## الحدود الصادقة

لم يُنفذ اختبار Colab حقيقي جديد في هذه المهمة ولم تُحذف أو تعدّل بيانات Telegram/Drive المحفوظة. الاختبار الحي الذي يجب أن يأتي بعد نشر الحزمة: تشغيل Colab جديد، محاولة استعادة الجلسة التالفة، إكمال تسجيل جديد، إعادة تشغيل runtime، والتأكد أن manifest الجديد هو الذي يستعيد. لذلك لا تزال الحالة غير `Colab-ready` وغير `Complete`.

## الخطوة التالية

مراجعة فرق وأسرار نهائية، ثم commit وpush وPR ودمج بعد CI. بعد الدمج فقط يُشغَّل Publish current TeleDrive package وتتحقق الحزمة العامة.
