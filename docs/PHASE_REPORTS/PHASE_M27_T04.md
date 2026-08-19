# PHASE M27-T04 — إصلاحات العيوب المكتشفة بالتحقق الحي

**التاريخ:** 2026-08-19 UTC

**الفرع:** `fix/m27-t04-live-defects`

**Base SHA:** `3bbe69b91159fb519e2d7fb6efab9835ad7788f5`
**الحالة:** **MERGED + CI-PASSED + live sandbox-verified؛ تحقق Colab النهائي ما زال pending.**

**PR:** [#59](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/59) — MERGED

**Source SHA:** `6eb5512f71ce09fd0b973280645cc3274f47eb28`
**Merge SHA:** `dfbb90b9afc25e5bcbb5ce45ad5d90efd4099ac1`

## الهدف

معالجة العيوب التي ظهرت أثناء اختبار حي معزول خارج المستودع، مع الحفاظ على عقد TeleDrive: عملية واحدة، مسار `disk-first`، عدم حذف `.part` أو ملف Drive عند التحكم، وعدم إدخال أسرار أو ملفات اعتماد إلى Git.

| العيب المثبت | الدليل قبل الإصلاح | المعالجة الجراحية |
|---|---|---|
| استئناف عنصر `Paused` قد يبدأ drain جديدًا قبل اكتمال drain السابق، فيتداخل تشغيلان على عميل Telegram واحد أو يبقى عنصر الاستئناف دون إكمال | اختبار حي Pause ثم Resume وصل إلى `Downloading` ولم يصل `Uploaded` | `QueueManager.resume()` يحيي الصف أولًا، ثم يؤجل drain الجديد إلى callback نهاية المستقبل السابق؛ يحافظ callback القديم على حالة التشغيل الجديدة ولا يصنّف الإلغاء المنضبط كتعطل محرك |
| رابط دعوة قناة خاصة لحساب عضو (`t.me/+…` / `joinchat`) كان مرفوضًا من `ScannerService` قبل الوصول إلى الكيان الصحيح | النقل الحي نجح عند تزويد المحرك بكيان خاص محلول، بينما مسار Analyze العام لم يقبل رابط الدعوة | `TelegramService.resolve_invite()` يستخدم `CheckChatInviteRequest` للحساب العضو فقط، ولا ينضم لأي قناة؛ ثم يمرر InputPeer إلى المسح المحدود المعتاد |
| بندل React المشحون داخل Gradio كان يرمي `ReferenceError: process is not defined` قبل تركيب اللوحة | فحص متصفح محلي حقيقي: لم يظهر إلا Accordion الاحتياطي وسجل المتصفح الخطأ | يثبت مولد البندل قيمة `process.env.NODE_ENV="production"` عند البناء، ويمنع اختبار العقد إعادة شحن المرجع غير المتاح في المتصفح |

## التغييرات

| الملف | التغيير |
|---|---|
| `python-package/teledrive/queue_manager.py` | ترتيب آمن لـPause/Resume، وحماية callback مستقبلي قديم، وتجاهل `CancelledError` المنضبط كتعطل محرك |
| `python-package/teledrive/telegram_client.py` | حل آمن لرابط دعوة خاصة لحساب هو عضو مسبقًا، بلا Join تلقائي |
| `python-package/teledrive/services.py` | تمرير روابط الدعوة المحلولة إلى `scan_link()` ضمن الحدود القائمة |
| `scripts/build-react-panel.mjs` | inline صريح لبيئة الإنتاج عند بناء IIFE المدمج |
| `python-package/teledrive/react_panel_assets/*` | أصول React معاد بناؤها حتميًا من المصدر |
| `python-package/tests/test_m27_hardening.py` | تغطية Future الملغى، callback قديم، وتسلسل Resume بعد drain سابق |
| `python-package/tests/test_scoped_scan.py` | تغطية مسح رابط دعوة لحساب عضو بلا إدخال للطابور |
| `python-package/tests/test_analyze_ui_modes.py` | عقد رفض الوصول الخاص غير القابل للحل بلا Join |
| `tests/teledrive-sandbox.contract.test.mjs` | منع `process.env.NODE_ENV` في الأصل المشحون |

## التحقق الحي المعزول

لم تُستخدم أي بيانات اعتماد داخل المستودع أو التقرير. تم الاحتفاظ ببيئة الاختبار وملفاتها المقيدة خارج الشجرة.

| السيناريو | النتيجة الفعلية |
|---|---|
| Telegram خاص → Drive | نقل حقيقي سابقًا إلى مجلد Drive اختبار معزول، والتحقق من حالة `Uploaded` ووجود الملف وحجمه |
| Pause → Resume | **PASS:** بقي `.part` غير فارغ، استأنف `TelegramService.download_partial()` من offset محاذٍ، ووصل العنصر إلى `Uploaded` |
| Stop أثناء تنزيل فعلي | **PASS:** الحالة النهائية `Stopped`، بقي الجزء المحلي، ولم يوجد ملف وسائط جديد على Drive |
| Analyze برابط دعوة خاص | **PASS:** المسح أعاد مرشحًا واحدًا محدودًا؛ عند وجود الملف مسبقًا أظهر المسار `Skipped` بدليل Dedupe وملف بعيد واحد في مجلد الاختبار |
| React داخل Gradio | **PASS:** ظهرت اللوحة React الكاملة محليًا بعد إعادة البناء، ولم يسجل المتصفح خطأ `process is not defined` |

## بوابات محلية فعلية

| الأمر | النتيجة |
|---|---|
| `python3 -m compileall teledrive` | PASS |
| `python3 -m pytest -q tests` | **738 passed** |
| `python3 teledrive_launcher.py --check` | **51/51 ready actions resolve** |
| `python3 -m teledrive.notebook_cells --check` | PASS |
| `cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb` | PASS، النوت‌بوكان متزامنان |
| `python3 -m teledrive.package_service --build ...` | PASS، حزمة بنيت خارج المستودع |
| `pnpm run lint` | PASS |
| `pnpm run build` | PASS |
| `node --experimental-strip-types --test tests/teledrive-sandbox.contract.test.mjs` | **26 passed** |

## ما لا يثبته هذا التقرير

هذا ليس اختبار Google Colab حقيقيًا، ولم يُنشر أرشيف Colab جديد بعد. نجحت فحوص CI الأربع على push وpull_request قبل دمج PR #59، لكن ذلك لا يساوي اختبار Colab. لذلك تظل الحالة الصادقة **ليست `Colab-ready` وليست `Complete`**. كما أن الفحص التفاعلي الحي غطى تحميل لوحة React والمسارات الحرجة، بينما check registry يثبت ربط الإجراءات الجاهزة ولا يساوي اختبارًا حيًا لكل إجراء حساس.

## نقطة التراجع

الرجوع الآمن بعد الدمج هو `git revert` لدمج `dfbb90b9afc25e5bcbb5ce45ad5d90efd4099ac1` عبر PR جديد؛ لا إعادة كتابة للتاريخ. لا توجد عمليات حذف Drive ضمن هذه المرحلة.
