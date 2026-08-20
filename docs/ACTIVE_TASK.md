# المهمة النشطة

| الحقل | القيمة |
|---|---|
| TASK ID | `M32-T01` |
| العنوان | استبدال آمن وذري لجلسة Telegram التالفة |
| الحالة | **MERGED + CI-PASSED + package-published؛ Colab recovery verification pending** |
| PR | [#71](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/71) — MERGED |
| Merge SHA | `5255889c1e153f2188939b225dfbbb8a5865d261` |
| Publish | [run #32327688915](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32327688915) — SUCCESS |

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

الحزمة المنشورة تشير إلى `5255889` وSHA-256 `81bcd23629c87022c7e0c3b9f4f725d6b47654c9a13422a639f191fb5647cacf`. شغّل Cell 1 في Colab ثم Restart Runtime عند طلبه، وبعدها Cells 2–4. يظل اختبار الاستبدال الحي (جلسة مبطلة → دخول جديد → Restart → استعادة بلا OTP) مطلوبًا قبل `Colab-ready` أو `Complete`.
