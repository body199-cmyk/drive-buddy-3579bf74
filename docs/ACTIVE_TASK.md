# المهمة النشطة

| الحقل | القيمة |
|---|---|
| TASK ID | `M44-T02` |
| العنوان | تنزيل Telegram كبير الحجم بمسارين MTProto متوازيين ومحدودين، مع حفظ `.part` صالح واسترجاع legacy آمن |
| الأساس | `db0f2a02502b94d2975fa23d7bce5d6af9b24e52` — main/PR #94 merge |
| الفرع | `arena/360d78bc-drive-buddy-3579bf74` |
| الحالة | **IMPLEMENTED + LOCAL-TESTED — candidate only; not merged/published and no real Telegram benchmark** |
| دليل المستخدم | صورة Colab: ملف Telegram حجمه 1.3 GB، قرابة 41% بعد نحو 10 دقائق؛ تقدير تقريبي 0.9 MB/s، لا قياس مستقل. |
| التقرير | `docs/PHASE_REPORTS/PHASE_M44_T02_BOUNDED_PARALLEL_TELEGRAM_DOWNLOAD.md` |

## النطاق

- الملفات ≥32 MiB تستخدم قارئين MTProto بحد أقصى، offsets/stripes منفصلة بحجم request 512 KiB؛ الأصغر يبقى على المسار التسلسلي.
- حد عام لطلبين تنزيل متزامنين عبر TelegramService الواحد حتى لا يتضاعف الحمل مع concurrency الصفوف.
- reorder window من أربع قطع كحد أقصى؛ الكتابة النهائية إلى `.part` تكون متصلة فقط. Pause/Stop يحتفظان ببادئة صحيحة، وأي خطأ نقل/حجم يلغي القارئين ويعيد المسار القديم الذي يبدأ من الصفر.
- لا اعتماد جديد ولا تغيير في Drive upload أو auth أو schema أو notebook/workflow.

## بوابات محلية

`798 passed` · compileall PASS · launcher `54/54` · notebook check + `cmp` PASS · package build PASS بعد إثبات SHA النهائي في phase report. `bun run lint` لم يعمل: `bun: command not found`؛ لا تغييرات frontend.

## ما لم يثبت / المطلوب قبل إغلاق المهمة

- لا اختبار حي على Telegram أو Colab ولا قياس مقارنة قبل/بعد؛ اختبارات الشبكة الوهمية تثبت العقود فقط.
- يجب دمج التغيير ونشر ZIP/manifest متطابقين عبر Runner، ثم Restart Colab وتشغيل ملف ≥100 MB مع ملاحظة `telethon crypto backend=cryptg`، throughput، الحجم النهائي، Pause/Resume، ومرور الملف إلى Drive.
- لا توصف المهمة بأنها Colab-ready أو Complete قبل الاختبار الحي. لا ترفع concurrency ولا عدد المسارات فوق 2 بدون موافقة/قياس إضافيين.

## التراجع

Revert commit M44-T02. أي استثناء في المسار المتوازي يعيد استعمال fallback التسلسلي الذي يفتح `.part` من byte 0؛ لا حذف من Drive ولا تغيير للـVault.
