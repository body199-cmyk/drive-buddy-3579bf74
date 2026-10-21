# M52-T02 — استكمال أدوات التحكم في التنزيل الخارجي (Universal URL Downloader)

**التاريخ:** 2026-10-21  
**الحالة:** MERGED TO MAIN; CI and package publication passed; live Colab/Drive verification pending  
**PR / merge:** [PR #124](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/124), commit `08363cdffa4653f95db39e88e0e124022dc86afe`

## الطلب

مقارنة لوحة «التحميل من الويب» مع أدوات التحكم الموجودة في طابور Telegram، ثم إضافة الوظائف الناقصة بشرط أن تتحكم في المهمة الحقيقية ومحركها، لا أن تكون أزرار واجهة فقط. المطلوب خصوصًا: pause/resume/retry بالإضافة إلى start/cancel الموجودين.

## نتيجة التدقيق قبل التعديل

- `UniversalDownloadManager` كان يوفر `start_download` و`cancel_task` و`clear_finished` فقط.
- الواجهة الحديثة كانت تعرض «إلغاء» فقط أثناء queued/downloading، ولا تعرض إجراءً لاستئناف مهمة أو إعادة محاولة مهمة فاشلة.
- طابور Telegram الأساسي لديه إجراءات منفصلة `queue.pause_item`, `queue.resume_item`, `queue.stop_item`, `queue.retry_item`; لكن هذه الإجراءات مبنية على `QueueManager/TransferManager` ولا يجوز تمرير معرّفات universal-download إليها، لأن المحركين منفصلان.
- رفع Drive مرحلة مستقلة؛ إيقافها قسرًا غير مدعوم بشكل آمن من هذه الواجهة.

## التعديلات

### محرك التنزيل — `python-package/teledrive/universal_downloader.py`

- إضافة resume gate لكل مهمة؛ set تعني التشغيل، وclear تعني إيقافًا مؤقتًا.
- `pause_task` يغير الحالة الفعلية إلى `paused` ويوقف العامل عند نقاط التحكم التعاونية.
- `resume_task` يفتح gate ويعيد المهمة إلى حالة التنزيل.
- `_wait_if_paused` ينتظر gate مع فحص الإلغاء دوريًا؛ الإلغاء يوقظ العامل المتوقف حتى لا يبقى محجوزًا.
- ربط نقاط التحكم مع direct HTTP chunk loop وyt-dlp progress hook، وكذلك قبل الانتقال إلى رفع Drive حتى لا تتجاوز مهمة انتهت من التنزيل للتو طلب الإيقاف المؤقت.
- `retry_task` يقبل المهام الفاشلة أو الملغاة فقط، ويبدأ مهمة جديدة فعلية باستخدام الرابط والجودة ومجلد Drive الأصليين، ويعيد التحقق من اتصال Drive.
- `bulk_action` يدعم pause/resume/cancel/retry_failed على كل المهام المؤهلة، مع عدّاد لعدد الأوامر الناجحة والمرفوضة ورسالة واضحة عند عدم وجود مهام مناسبة.
- `clear_finished` يحتفظ بالمهام paused/cancelling باعتبارها غير منتهية.
- إيقاف/إلغاء أثناء رفع Drive مرفوض بوضوح بدل إظهار نجاح زائف.

### API والواجهة — `python-package/teledrive/web_dashboard.py`

- إضافة endpoints فعلية: `POST /api/universal/pause`, `/resume`, `/retry`؛ الإلغاء الحالي باقٍ.
- كل زر فردي يرسل معرّف المهمة إلى مدير التنزيل الحقيقي؛ وأضيفت أزرار جماعية لإيقاف المهام مؤقتًا أو استئنافها أو إيقافها أو إعادة محاولة الفاشل. تعرض الواجهة نتيجة الخادم ثم تحدّث الجدول من بيانات live.
- تظهر «إيقاف مؤقت» و«إيقاف» أثناء التنزيل عندما يكون backend قابلًا للإيقاف، و«استئناف» و«إيقاف» في حالة paused، و«إعادة المحاولة» للمهام failed/cancelled.
- تعرض حالة الرفع أو الاكتمال نصًا بدل أزرار لا يمكن تنفيذها بأمان.
- لا تستخدم الواجهة `innerHTML` لعرض البيانات.

## حدود مقصودة وصريحة

- `gdown` (روابط Google Drive/Docs) لا يوفّر هنا callback آمنًا للإيقاف أثناء استدعاء التحميل الحاجب. لذلك تُعلّم المهمة `pause_supported=false` ولا يظهر لها زر pause؛ يظل الإيقاف/الإلغاء وإعادة المحاولة متاحًا حيث تسمح حالة المهمة.
- الإيقاف المؤقت تعاوني وليس قتلًا قسريًا للعملية: قد ينتظر حتى يصل yt-dlp إلى progress hook أو ينتهي طلب HTTP الجاري.
- إيقاف المهمة بعد بدء رفع الملف إلى Drive غير متاح في هذا المسار. لم أضف زرًا يدّعي ذلك.
- إعادة المحاولة تنشئ مهمة جديدة وتعيد التنزيل من البداية؛ لا ندّعي أنها تستكمل بايتات جزئية من محاولة فاشلة. التنظيف الحالي يحذف مجلد العمل بعد انتهاء المهمة.
- لم يُختبر اتصال حي في Colab أو تنزيل/رفع فعلي إلى Drive في هذه المرحلة.

## الاختبارات المضافة

اختبارات مدير التنزيل تغطي:
- pause/resume يغيران حالة المهمة وresume gate.
- رفض pause عندما لا يدعم backend الإيقاف.
- رفض resume لمهمة ليست paused.
- retry يستخدم المدخلات المحفوظة ويقبل الحالات الفاشلة/الملغاة فقط.
- cancel يوقظ العامل paused.
- عقود الواجهة ووجود endpoints والأزرار.

**حالة الإثبات:** الاختبارات مضافة إلى الفرع؛ يجب الاعتماد على GitHub Actions بعد فتح PR لنتيجة التشغيل الفعلية. لا يُقال إنها اجتازت قبل ظهور النتيجة.

## طريقة التراجع

Revert للـPR الخاص بـ M52-T02. لا تغيّر قاعدة البيانات أو Telegram queue أو Vault؛ الميزة محصورة في UniversalDownloadManager ولوحة الويب واختباراتها.

## الخطوات التالية

1. تشغيل CI واختبارات الحزمة ومزامنة notebook generator.
2. مراجعة نتائج CI وإصلاح أي إخفاق قبل الدمج.
3. بعد الدمج، السماح لآلية CI بإعادة توليد ملفات Colab الرسمية من `notebook_cells.py`.
4. نشر حزمة جديدة من المصدر المدمج.
5. اختبار حي: direct HTTP (pause/resume/cancel/retry)، رابط فيديو yt-dlp (pause/resume/retry)، ثم Drive upload. تحقق منفصل من أن gdown لا يعرض pause غير مدعوم.
6. لا تعلن «مكتمل بالكامل» حتى الاختبار الحي في Colab؛ CI وحده لا يثبت التشغيل الفعلي.


## حالة ما بعد الدمج والنشر — 2026-10-21

- Main CI: [run #39627612669](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39627612669) — **success**. Test suite: `876 passed, 1 warning`; frontend lint/build, notebook generation checks, byte compilation, and archive build passed.
- Package release: [run #39627612843](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39627612843) — **success**. Release [pkg-2026.08.09-m15t07](https://github.com/body199-cmyk/drive-buddy-3579bf74/releases/tag/pkg-2026.08.09-m15t07) targets `08363cdffa4653f95db39e88e0e124022dc86afe`.
- Exact published ZIP: `674316` bytes; SHA-256 `6b0ede407ea2e68af03f93c88041824c9328140bef5bc35e6b45bb069f9a9be6`. Workflow validated the public manifest against the exact archive bytes.
- The branch code includes both per-task and bulk actions. No live Colab download/Drive upload was performed by CI. Owner-run live verification remains mandatory before describing the controls as runtime-verified.
