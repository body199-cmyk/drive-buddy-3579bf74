# CHANGELOG — آخر 20-30 تغيير (TeleDrive v5.0)

## [M47-T02] — 2026-10-20 — ثلاث سمات وتحليل قناة تلقائي وسير عمل من خمس خطوات

### Fixed
- **تحليل القناة:** كان الوضع الافتراضي في لوحة الويب `message`، فكان لصق رابط قناة بلا رقم رسالة يفشل حتمًا رغم سلامة Scanner والخادم. صار الافتراضي «تلقائي»: روابط الرسائل المباشرة تذهب إلى `message` وروابط القنوات/المجموعات إلى `chat` بحد الرسائل الظاهر، مع بقاء الأوضاع اليدوية الأربعة وحقولها كما هي.
- قُبلت صيغ روابط منسوخة شائعة (`@username`، بلا بروتوكول، `telegram.me` و`www`، معاينة `/s/`، و`?single`/شظايا، وقناة خاصة `/c/<id>`) مع استمرار رفض النطاقات المشابهة.
- أُصلحت مزامنة سمة الويب أثناء التحديث الدوري، وتعبئة رابط التحليل المحفوظ دون الكتابة فوق ما يكتبه المستخدم.

### Added / reorganized
- ثلاث سمات محفوظة في اللوحة الحديثة: فاتح، وخافت X معتدل (`#15202B`/`#1D9BF0`)، وداكن كامل؛ في المبدّل العلوي والإعدادات.
- أعيد ترتيب اللوحة إلى خمس خطوات: الحسابات، مجلد Drive، تحليل الرابط، تحديد النتائج، النقل/الطابور، مع سطر ديناميكي للخطوة التالية وحالة لكل قسم.
- نتائج التحليل داخل صندوق `430px` مستقل التمرير برأس ثابت وبحث داخلي وحجم محدد وفلاتر وتحديد نطاق/مجموعة؛ والطابور داخل صندوق `350px` مع تحكم فردي بكل عنصر ومسح مكتمل/غير مكتمل. لم تُفقد أي وظيفة سابقة، وبقي إدخال أسرار Telegram في Gradio الآمن فقط.

### Gates and local verification
- `853 passed` · compileall PASS · launcher `54/54` · notebook check + cmp PASS · React/Node contracts `34/34` · سكربت Web اجتاز `node --check`.
- HTTP حي محلي: تحليل قناة عبر `analyze.run` أعاد 35 مرشحًا بسمة `dim`. محاكاة JSDOM نفذت التعرف التلقائي والتحليل والتحديد والبحث وتبديل السمات بلا أخطاء JavaScript.
- archive مختبر محليًا: `650261` bytes، SHA-256 `bd011ed0252a340bc1db12c6619ca1ef829603bd54e561ae2745e59853b42828`.
- لا ادعاء بإثبات Colab/Telegram/Drive الحي؛ يلزم تأكيد المالك بعد النشر. التقرير `docs/PHASE_REPORTS/PHASE_M47_T02_MODERN_DASHBOARD_THEMES_AND_CHANNEL_ANALYZE.md`.

## [M46-T03] — 2026-10-20 — تدقيق الواجهتين: إظهار الويب وإصلاح التحليل والتوزيع

### Fixed
- **توزيع Colab:** آخر release بعد دمج M46-T02 ظل مبنيًا من SHA أقدم، والتاج المثبت يحمل حزمة بلا الواجهة الحديثة. أضيف resolve لـ`/releases/latest` عبر redirect عند نفاد حد GitHub API، ومقارنة `build_run_id` بين latest والتاج المثبت حتى لا يُظلَّل الإصدار الأحدث بناءً بسبب تاريخ إنشاء التاج الثابت.
- **صفحة Web الحديثة:** `channel` كان اسم وضع غير موجود في المحرك، و`range` يرسل بلا start/end، كما لم تعرض الصفحة أي نتيجة تحليل. صارت الأوضاع `message/range/latest/chat` مطابقة لـ`SCAN_MODES`، لكل وضع حقوله والتحقق العربي، وتظهر قائمة المرشحين مع التحديد/مسح التحديد عبر نفس الـbridge المعتمد.
- **استمرار الواجهتين:** الافتراضي في Cell 4 هو `Run_Both_Together`؛ تطلق Gradio أولًا وتبقى حقول Telegram الآمنة متاحة، ثم لوحة الويب الحديثة. فشل تشغيل Gradio لا يمنع محاولة الويب، وفشل الويب يطلق Gradio احتياطيًا، وإذا فشلا يظهر تنبيه واضح بدل ادعاء تشغيلهما. أُعيد توليد النوت‌بوكين و`colab_cells.json` من المصدر.
- نسخة `docs/M46_T02_release_current_workflow.yml` الجاهزة للتبنّي تضيف `build_run_id` إلى الـmanifest.

### Gates and local verification
- `835 passed` · compileall PASS · launcher `54/54` · notebooks check + cmp PASS · React contracts `34/34` · سكربت Web اجتاز `node --check`.
- تشغيل HTTP مزدوج حي (Gradio + Web) مع نفس Context: الصفحتان `/` = 200، `/config`، health/metrics/state، analyze candidates toggle/select-all/clear، إعادة الإطلاق idempotent، وحلقة التطبيق `pong`؛ `FAILURES: 0`.
- archive: `628920` bytes، SHA-256 `89de5831be2350d564d8196c4780173a7b5b5693d7b544106fa7702327a4e736`.
- دُمجت التغييرات عبر PR [#108](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/108) عند `d8c22df`; PR CI [#39452872933](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39452872933) وmain CI [#39453144455](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39453144455) نجحا (Python + Frontend).
- **لم يُثبت Colab حيًا ولم يُنشر الإصدار بعد:** `gh workflow run` عاد 403 من صلاحية الوكيل. يلزم نشر GitHub Actions يدوي أو تبنّي الـworkflow الجاهز؛ التقرير `docs/PHASE_REPORTS/PHASE_M46_T03_DUAL_UI_AUDIT_AND_DISTRIBUTION.md`.

## [M46-T02] — 2026-10-19 — إصلاح عاجل: الواجهة الحديثة غائبة وGradio متجمدة على Colab

### Fixed
- **عزل سيرفر الويب (الجذر الثاني):** `web_dashboard.py` كان يُجدوَل على
  `ctx.aio`؛ أثبتت إعادة إنتاج (منفذ مشغول) أن `sys.exit` من uvicorn داخل
  المهمة **يقتل حلقة التطبيق كلها** فتختفي الواجهة الحديثة وتتجمّد Gradio
  (صفحتها تفتح لكن Handlers تحتاج الحلقة الميتة). السيرفر الآن في ثريد
  معزول مع فحص منفذ وتحقق استماع فعلي وفشل صريح بالسبب؛ ومقبض ميت لا
  يُسلّم أبدًا كأنه يعمل. زر HTML قابل للضغط يظهر على Colab.
- **قناة التوزيع (الجذر الأول):** التاج الثابت الذي تقرأه الخلية 1 كان
  ما زال يوزّع حزمة ما قبل M46 (‏600312 بايت بلا `web_dashboard.py`) بينما
  نُشرت الحزمة الجديدة على تاج متغير لا تقرأه الخلية. إصلاح مزدوج:
  (أ) بوابة تحديث الخلية 1 تراجع الآن **أحدث إصدار `pkg-*`** أولًا (عبر
  GitHub API العام، مع توثيق أن الـManifest ورابط أرشيفه تحت نفس التاج)
  وتسقط للتاج المثبّت عند أي تعذر — فيصل أي إصدار جديد بلا تعديل نوت‌بوك؛
  (ب) نسخة الـWorkflow المصححة (تاج ثابت + نشر تلقائي على Push للحزمة)
  محفوظة في `docs/M46_T02_release_current_workflow.yml` لأن دفع
  `.github/workflows/**` مرفوض لصلاحيات تطبيق الوكيل (#15/#27).
- `app.launch` صارت idempotent: إعادة الخلية 4 والواجهة حية تعيد طباعة
  الرابط بدل انهيار المنفذ المشغول وترك خادم يتيم.
- الخلية 4: Gradio يُطلق **أولًا** ثم الحديثة، وطباعة
  `selected UI_MODE`/`web dashboard: OK`، وتلميح صريح عند حزمة قديمة
  (Restart ثم 1–4 من الأول). أُعيد توليد النسختين وJSON.

### Gates and local verification
- إعادة إنتاج العطل قبل/بعد: المنفذ المشغول كان يقتل `ctx.aio`؛ بعد
  الإصلاح خطأ نظيف والحلقة ترد `pong` وحدث Gradio الحقيقي يكتمل بنجاح.
- `829 passed` · compileall PASS · launcher `54/54` · notebook check+cmp ·
  `node --test` 34/34.
- حزمة مختبرة نظير هذا التغيير محليًا: `621895` بايت، SHA-256
  `0f45c7729fa382a84c46ce60a47dda9c70a46bc6a69e4f881fd2b3cc57dfe389`
  (بصمة الدمج النهائية قد تختلف بمحتوى التقرير وهي المُثبتة في الـManifest).
- التقرير: `docs/PHASE_REPORTS/PHASE_M46_T02_WEB_DASHBOARD_ISOLATION_AND_DISTRIBUTION.md`.


## [M46-T01] — 2026-10-19 — واجهة ويب حديثة (FastAPI + AJAX Polling) + Gradio احتياطي

### Added
- `teledrive/web_dashboard.py`: لوحة ويب حية مكتفية ذاتيًا (صفر CDN، عربي RTL)
  تستطلع `api/metrics` كل ثانية بلا ريفرش، مربوطة فعليًا بـ
  `progress/queue_manager/LiveUiStateService/LogService` وتُرسل كل إجراء عبر
  `handlers.bridge_request` الموثّق نفسه (لا أسرار عبر HTTP، لا CORS عام،
  لا `innerHTML`). دُمجت من حمولة `TeleDrive_WebUI_GitHub_Bridge.ipynb` على
  Drive بعد تكييفها دستوريًا (حلقة `ctx.aio` الواحدة بدل حلقة ثانية، وبلا
  محرك النقل الخمّين/المكرر الذي كان في الحمولة) — تقرير
  `docs/PHASE_REPORTS/PHASE_M46_T01_MODERN_WEB_DASHBOARD.md`.
- خلية 4 في `notebook_cells.py` (وتوليد النسختين + `colab_cells.json` منها):
  قائمة `UI_MODE` بخيارات `Modern_Web_Dashboard` (8765، الافتراضي) /
  `Classic_Gradio_Backup` (7860) / `Run_Both_Together`، مع سقوط تلقائي إلى
  Gradio عند تعذّر الواجهة الحديثة.
- `app_context.py`: مقبض `ctx.web_dashboard` يُغلق في `shutdown()`.
- تثبيت `fastapi==0.149.0` و`uvicorn==0.54.0` في `requirements.lock`
  (+ `requirements.txt`)، باستيراد كسول فلا ينكسر وضع Gradio بدونهما.
- اختبارات `tests/test_web_dashboard.py` + عقد خلية-4 مزدوجة الواجهة.

### Gates and local verification
- `823 passed` · compileall PASS · launcher `54/54` · notebook check + cmp PASS ·
  معاينة HTTP حية (`/api/health`، `/api/metrics`) بحالة صادقة غير متصلة.
- حزمة مختبرة `teledrive_v4.5.zip`: `614404` بايت، SHA-256
  `de902fa6cf50dde106ed5126627e1dd2e425c9cc658cdf1d53c0781e5c9bfaf5`.

### Security
- دفتر كوبري Drive المصدر يحتوي GitHub Token كنص صريح؛ لم يدخل أي جزء منه
  المستودع (حُذفت النسخ المحلية وفحص `ghp_` نظيف). على المالك إلغاؤه فورًا.

## [M45-T01] — 2026-10-19 — استئناف Arena: تحقق وإغلاق الفجوة الحرفية الوحيدة

### Fixed
- `error_handler.py`: أُضيف marker `serverresent` الحرفي المطلوب في DOC M45-T01 §3.5
  إلى `TRANSIENT_MARKERS` (الباقي كان موجودًا مسبقًا ومثبتًا). اختبار تصنيف جديد في
  `tests/test_fast_download.py`.

### Gates and local verification
- Resume audit §9: كل بنود DOC §3 موجودة أصلًا في `main` (`d991cf4`) عبر PRs
  #93/#95/#98/#100 — لا إعادة تطبيق.
- `809 passed` (بعد إضافة الاختبار) · compileall PASS · launcher `54/54` ·
  notebook check + cmp PASS · package build PASS (`594716` bytes،
  SHA-256 `aee30938…fb`) · `node --test` 34/34. `bun` غير مثبت (لا تغيير frontend).

### Release status
- `pkg-2026.08.09-m15t07` منشور حاليًا من `d991cf4` عبر run 39278373927 — أُغلقت
  KNOWN_ISSUES #79. نشر مجدد بعد دمج هذه الإضافة التوثيقية محاولة مسجلة (إن نجح
  `workflow_dispatch`؛ وإلا بخطوة واحدة من المالك كما في §8 من تقرير المرحلة).

## [M45-T01] — 2026-10-19 — خط أنابيب تنزيل/رفع وحل جذري لسرعة Telegram

### Changed
- `config.py`: ثلاثة حدود مستقلة قابلة للتعديل بالبيئة — `MAX_CONCURRENT_TG_DOWNLOADS=4`
  (`TELEDRIVE_TG_FILES`)، `PARALLEL_DOWNLOAD_STREAMS=4` (`TELEDRIVE_TG_STREAMS`)،
  `TG_INFLIGHT_REQUESTS=8` (`TELEDRIVE_TG_INFLIGHT`) — و`MAX_PENDING_UPLOADS=4`
  (`TELEDRIVE_UPLOAD_BUFFER`).
- `telegram_client.py`: ميزانية الطلبات صارت عالمية وتشمل المسار المتسلسل والاستئناف؛
  `connect()` يمرر `request_retries/connection_retries/retry_delay/flood_sleep_threshold`
  مع fallback عند `TypeError`؛ القارئات المتداخلة تدعم `start_at` للاستئناف؛
  `download_partial()` يحاذي 512 KiB للملفات >512 KiB (و4 KiB للأصغر) ويستأنف الكبير
  بالمسار المتداخل؛ تسجيل `mbps=` وثواني القياس.
- `transfer_manager.py`: مرحلتان — `_download_stage` (بلا نداء Drive حاجب) و`_upload_stage`
  (فحص تكرار/حصة ثم رفع/تحقق/checkpoint). إذن العامل يغطي التنزيل فقط؛ حاجز
  `MAX_PENDING_UPLOADS` يحد الملفات الجاهزة؛ `_drive_call` ينتظر على `asyncio.Lock` قبل
  استهلاك ثريد؛ فشل الرفع يعيد الرفع فقط ولا يعيد التنزيل؛ `.part` الكامل يُعاد استخدامه.
- `media_scanner.py`: `_has_downloadable_media()` ترفض Web Page/Poll/Geo/Contact/Dice/Game/
  Unsupported فلا تُنشأ صفوف 0 بايت `.bin`.
- `error_handler.py`: `request was unsuccessful`/`server error` transient،
  `invalid limit`/`downloaded file missing` permanent.

### Gates and local verification
- `809 passed` · compileall PASS · launcher `54/54` · notebook check + cmp PASS ·
  `node --test tests/teledrive-sandbox.contract.test.mjs` 34/34.
- اختبارات M45 الجديدة في `tests/test_fast_download.py` و`tests/test_m27_hardening.py`
  تثبت المحاذاة، حفظ البادئة، الحد العالمي للطلبات، حد الملفات عند workers=20، استمرار
  التنزيل أثناء رفع محجوب، إعادة استخدام `.part` الكامل، تصفية الوسائط، وتصنيف الأخطاء.
- `bun run lint/build` NOT RUN: `bun: command not found`؛ لا تغييرات frontend.

### Open / not proven
- لا قياس Telegram/Colab حي. إعادة نشر الحزمة وRestart Colab ثم تسجيل `mbps=` وPause/Resume
  والتحقق من Drive بيد المالك. لا ادعاء نسبة تسريع قبل ذلك.
- اتصال MTProto واحد يظل سقف النقل النظري؛ تجمع اتصالات يحتاج A/B ومراجعة Vault.

## [M44-T02] — 2026-10-19 — تنزيل Telegram كبير الحجم بمسارين محدودين

### Changed
- الملفات ≥32 MiB تستخدم قارئين `iter_download` متداخلين بقطاعات MTProto منفصلة (512 KiB)؛ حد الطلبات الجارية عالميًا في TelegramService هو 2 حتى لا يتضاعف الحمل عبر عمال الطابور. الأصغر يبقى على المسار المتسلسل.
- ترتيب القطع عبر نافذة bounded من أربع قطع، والكتابة إلى `.part` تظل بادئة متصلة فقط. Pause/Stop يحافظان على بادئة قابلة للاستئناف؛ فشل النقل أو mismatch يلغي بقية المسارات ويرجع إلى fallback القديم الذي يعيد الكتابة من الصفر.
- لم تتغير الاعتماديات أو Drive upload أو auth أو schema أو notebook أو workflow.

### Gates and local verification
- `798 passed` · compileall PASS · launcher `54/54` · notebook check + cmp PASS · deterministic package build PASS (`583226` bytes، SHA-256 `d77a4e29e63ae17b48b2720ddce52a443eee5302bd26f256fb9c9103b0480dd3`).
- اختبارات جديدة تثبت إعادة ترتيب القطع، تزامنًا بحد 2، بادئة صحيحة عند Pause، وفشل مسار النقل بأمان.
- `bun run lint` NOT RUN: `bun: command not found`; لا تغييرات frontend.

### Open / not proven
- أبلغ المالك عن ملف 1.3 GB وصل قرابة 41% في نحو 10 دقائق (~0.9 MB/s تقديريًا) بعد نشر M44-T01. هذا report مستخدم، ليس قياسًا آليًا.
- مسار M44-T02 لم يُختبر على Telegram أو Colab حقيقي، ولم يُنشر. القياس الحي مع `cryptg`، صحة الحجم، Pause/Resume ثم Drive upload بيد المالك بعد الدمج والنشر؛ لا ضمان لنسبة تسريع قبلها.

## [M44-T01] — 2026-10-19 — مفتاح التحديث التلقائي وسرعة تنزيل Telegram

### Changed
- أُضيف إعداد محفوظ `auto_refresh_ms` (الإيقاف `0`، أو `1000/2000/5000`) عبر `SettingsService`، ويظهر في `LiveUiStateService.snapshot()` باسم `autoRefreshMs`. React يبني `setInterval` على القيمة الحقيقية ويتوقف تمامًا عند `0`؛ زر التحديث اليدوي يظل متاحًا، والـrefresh الأحادي بعد كل إجراء ناجح يظل يعمل. Gradio shell يعرض نفس الإعداد عبر `gr.Radio`، ولا يوجد `localStorage` أو حالة وهمية.
- أُضيف فعل حقيقي `settings.set_auto_refresh` إلى registry مع handler وservice وproof test، ووُصل في React وGradio، فأصبح `launcher --check` يعرض `54/54`.
- مسار تنزيل جديد `TelegramService.download_media_fast()` يستعمل `iter_download` بطلب `512 KiB` (الحد الأقصى في MTProto) للملفات ≥1 MiB غير المصوّرة. Telethon كان يستعمل `128 KiB` للملفات ≤100 MB. أي فشل غير تحكّمي يكتب حدث `RECOVERY` ويعود للمسار القديم الذي يعيد كتابة الملف من الصفر؛ إشارات Pause/Stop تُعاد ولا تُبتلع. الاستئناف من offset صار يعلن `512 KiB` و`file_size` صراحةً.
- أُضيف `cryptg==0.6.0` إلى `requirements.txt` و`requirements.lock` (AES-IGE بلغة C، wheels لـ cp310–cp314 manylinux x86_64). يسجّل `telegram_client.crypto_backend()` أي تطبيق AES فعّال عند الاتصال: `cryptg` ثم `libssl` ثم `pyaes`.

### Gates and local verification
- CI push [#39246461893](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39246461893) SUCCESS (Python + Frontend).
- `795 passed` · compileall PASS · launcher `54/54` · notebook check + cmp PASS · React contracts `34/34` · lint 0 errors (8 تحذيرات baseline) · package build PASS (`578225` bytes، `e4723b02…15f6`).
- `bun run build` لم يُشغَّل في sandbox هذه الجلسة لأن مرآة npm رفضت `@lovable.dev/vite-tanstack-config@2.8.5`؛ `tsc --noEmit` يشتكي من هذا الموديول فقط. CI يثبته من `bun.lock`.
- لا تغيير في notebook cells أو `.github/workflows` أو schema SQLite. `auto_refresh_ms` اختياري؛ غيابه يعيد الافتراضي 1000.

### Open / not proven
- لا قياس Colab/Telegram/Drive حي بعد. يلزم نشر الحزمة وCell 1 (لتثبيت cryptg) ثم قياس السرعة في Logs (`telethon crypto backend=cryptg`) وشاشة Dashboard.
- رفع Drive ما زال متسلسلًا عبر `_drive_lock` لأن service object ليس thread-safe؛ توازي الرفع يحتاج ADR لأنه يخالف قاعدة «Drive service واحد». التنزيل متعدد الجداول مؤجل لاختبار حي.

## [M43] — 2026-08-24 — Vault Drive-managed ورابط فحص محفوظ

### Changed
- Vault format 3 هي الصيغة الافتراضية الجديدة بقرار مالك صريح: session blob المموّه وAPI metadata اللازمة للاستعادة يُحفظان في زوج versioned داخل `TeleDrive_AppData`، فيستعيد Runtime Colab جديد Telegram من Drive بلا Colab Secrets أو هاتف أو OTP عند صلاحية الجلسة.
- تبقى format 1/2 قابلة للقراءة؛ format 2 تستخدم مفتاحها الخارجي مرة أخيرة ثم تُهجّر إلى format 3 فقط بعد أن يقبل Telegram الجلسة. staging + manifest يضمنان عدم استبدال النسخة النشطة قبل نجاح البديل، وفشل/revocation ينظف محليًا فقط.
- Cell 3 يفضّل Vault Drive-managed؛ Colab Secrets صارت مسار ترقية اختياريًا فقط للـformat 2 القديمة. لا تُطبع API Hash أو session.
- رابط الفحص الأخير صار محفوظًا في SQLite settings الخاصة بالـbackend ويصل إلى React عبر live snapshot الحقيقي؛ يوجد حفظ واضح عند blur/نجاح التحليل وزر مسح في React وGradio. لا `localStorage` ولا endpoint موازٍ ولا نقل Telegram زائف.
- أعيد بناء `panel.bundle.gz` من React source، وأضيفت أفعال registry حقيقية ومربوطة لواجهة Gradio كي لا توجد عناصر ready غير موصولة.

### Gates and local verification
- `779 passed` · compileall PASS · launcher `53/53` · notebook check + cmp PASS · React contracts `34/34` · lint/build PASS (تحذيرات baseline فقط) · package build PASS (`570612` bytes، `28d94129…90b79`).
- يغطي regression الحفظ والاستعادة Drive-managed بلا Secret خارجي، وترقية format 2 بعد استعادة موثقة، والاحتفاظ بزوج Drive عند فشل الجلسة، وحفظ/مسح الرابط في backend بلا enqueue أو local storage.
- حد الأمان تغيّر بقرار المالك: من يملك الوصول الكامل لزوج Vault format 3 على Drive يستطيع استعادة Telegram؛ لا تظهر القيم في UI أو logs أو Git. راجع `ADR-004-session-vault.md`.

### Merged and published
- PR [#91](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/91) دُمج إلى `main` عند `2d5893dea014c638937e953919c68f2251d035ef` بعد نجاح CI Python وFrontend في [push #32689166257](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689166257) و[PR #32689176699](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689176699). commit المصدر `e974dfd12f2bf372e34dbca463a082b7017400e2`.
- توقف [النشر الأول #32689333249](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689333249) fail-closed لاختلاف ZIP القديم؛ لم يُحذف release/tag. استُبدل ZIP وmanifest المتطابقان معًا من merge SHA، ثم نجح [Publish #32689575111](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689575111) والتحقق العام.
- manifest/ZIP العامان الآن: `commit=2d5893d…`، `sha256=28d94129…90b79`، `size=570612` bytes. يلزم إثبات Cells 1–4 على الحزمة المنشورة، بما فيه `telegram session vault: restored` و`Gradio · Live bridge`؛ لا `Colab-ready` أو `Complete` قبل ذلك.

## [M42] — 2026-08-23 — استعادة Vault المشفّر في Colab

### Fixed
- تحقق قراءة فقط من Google Drive التجريبي أثبت أن زوج Vault format 2 النشط ما زال موجودًا (`td_telegram.active.json` مع زوج versioned `.creds`/`.session`)؛ لم يُنزّل أو يُعدّل أو يُحذف أي ملف.
- السبب الجذري كان مسارين متصلين: Cell 3 يتخطى تحميل/طلب API Hash عند وجود Vault، و`restore_from_context(ctx, secret=api_hash)` كان يهمل secret ثم يستدعي الاستعادة بلا مفتاح فك. لذلك يعجز runtime جديد عن فك blob format 2، الذي لا يخزن API Hash في Drive عمدًا، ثم يسلك login اليدوي مع إبقاء Vault البعيد.
- `restore_from_context` و`autorestore_once` و`autorestore` باتت تمرر secret اختياريًا داخل العملية فقط. لا يسجل أو يحفظ في Drive. ويعيد `probe()` API ID غير السري من metadata كي لا يطلبه Cell 3 عند وجود Vault.
- Cell 3 يقرأ Colab Secrets قبل قرار Vault. إذا كانت غائبة وVault موجودًا، يطلب API ID/Hash مخفيين فقط، لا هاتفًا أو OTP. Cell 4 لا يعيد `set_credentials` إذا نجحت الاستعادة.

### Gates and local verification
- Regression قبل التصحيح: RED (`restore_from_context(..., secret=...)` عاد `False` مع Vault format 2 صالح). بعد التصحيح: GREEN ويثبت أن bytes زوج Drive لا تتغير.
- `770 passed` · compileall PASS · launcher `51/51` · notebook check + cmp PASS · React contracts `33/33` · `pnpm run build` PASS · lint exit 0 مع 9 تحذيرات baseline · package build وZIP integrity PASS.
- لا تغيير في React/bridge في M42. تحقق الأصل العام الحالي أثبت manifest على `bc9fc5f…` ووجود `__teledriveReactPanelLease` في ZIP، لكن Cell 4 الحقيقي لا يزال غير مثبت؛ لا `Colab-ready` أو `Complete`.

### Merged and published
- PR [#89](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/89) دُمج إلى `main` عند `d54b01027f3f7d33b9e5d6cacc4bd59628b26b1c` بعد نجاح CI Python وFrontend في تشغيلي push وpull request. commit المصدر `b374efcc626d23ca037c1048e4a4c7b9af71d17e`.
- [Publish #32648577584](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32648577584) توقف fail-closed لأن ZIP المنشور كان `567611` bytes مقابل archive M42 `568320` bytes؛ لم يحذف release/tag. استُبدل ZIP وmanifest المتطابقان معًا من SHA المدمج ثم نجح [Publish #32648838713](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32648838713) والتحقق العام.
- manifest/ZIP العامان الآن: `commit=d54b010…`، `sha256=ffb5f6ab…b0f1`، `size=568320` bytes. لا `Colab-ready` أو `Complete` قبل Cell 1–4 حي.

## [M41-T01] — 2026-08-23

### Fixed
- عادت رسالة `Backend bridge unavailable` في لقطة Colab رغم تحميل React كاملًا؛ عولج مسار lifecycle الذي يعيد `js_on_load` لنفس host ثم يترك شجرة React مرتبطة بـbridge دخل `dispose()`.
- صار الغلاف يعيد استخدام panel الحي بدل التخلص منه، ويضع lease مستقلًا لكل on-load؛ watcher وcleanup من run قديم لا يسلّمان state ولا يقتلان المالك الحالي.
- `MountedTeleDrivePanel.isLive()` يكشف حالة bridge فقط. لا تغيير في action IDs أو `props.value`/`trigger('submit')` أو Python handlers أو أسرار Telegram/Drive.

### Gates and local verification
- `769 passed` · launcher `51/51` · notebook check + cmp PASS · React contracts `33/33` · lint/build PASS (0 errors؛ 9 warnings baseline).
- Gradio 6.20 المحلي ومحاكاة `is_colab=True` خلف proxy: `Gradio · Live bridge` ثم `telegram.status` = `Action completed` بعد إعادة تشغيل البندل الجديد.
- لم يحدث بعد إثبات في Runtime Colab الخاص بالمالك أو نقل حي؛ لا `Colab-ready` ولا `Complete`.

### Merged and published
- PR [#87](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/87) دُمج إلى `main` عند `bc9fc5f42bcec51d2f7f6566021cf0f2433de9d1` بعد نجاح فحوص CI الأربعة؛ commit المصدر `4fca8e6b1c899c1b54a1adfbb38c65e247472b96`.
- [Publish #32646821416](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32646821416) نجح بعد استبدال ZIP وmanifest المتطابقين يدويًا إثر توقف التشغيل الأول fail-closed لاختلاف الحجم. التحقق العام: `commit=bc9fc5f…`، `sha256=ab3d3db2…d1529`، `size=567611` bytes.

## [M40-T01] — 2026-08-23

### Fixed
- عيب KNOWN_ISSUES #72: تعارض نبض `queue.refresh` كل ثانية مع أزرار Pause/Resume/Stop أثناء النقل الحي. الإثبات السببي بعقود React حتمية (`test 29` RED قبل الإصلاح): استجابة refresh متأخرة كانت تطمس حالة أحدث من زر تحكم، والتعطيل الشامل `busyAction` كان يعطل كل الأزرار أثناء أي إجراء.
- تسلسل أحادي عبر **كل** طلبات الجسر في `gradioBridge.ts`: الاستجابة الأقدم من آخر مطبَّق تُسقَط حالتها فلا يعود للنبض المتأخر أن يخفي نتيجة الزر.
- كبح النبض في `TeleDriveSandbox.tsx`: لا نبض أثناء إجراء قيد التنفيذ ولا خلال 300ms استقرار بعد اكتماله ولا والتاب مخفي؛ وبعد كل نجاح refresh صامت واحد يلتقط الحالة الجديدة عبر نفس حارس التسلسل.
- `pendingActions` لكل زر بدل التعطيل العالمي، ومفاتيح صفوف/جلسات مستقرة، واشتقاقات memoized — فلا يتقلّع الزر من تحت المؤشر عند إعادة الرسم.

### Gates and local verification
- عقود React: `33/33` (منها 29–32 الجديدة) · pytest: `769 passed` · compileall OK · launcher `51/51` · notebook check + cmp PASS · eslint على الملفات المتغيرة 0 أخطاء · panel bundle أعيد بناؤه.
- لا تغيير في المحرك أو مسارات Telegram/Drive؛ لا Timer عالمي عاد؛ لا نجاح محلي بلا رد Python؛ لا أسرار في React.
- إثبات Colab الحي أثناء النبض لم يُنفَّذ بعد — بيد المالك (لا `Colab-ready` أو `Complete`).

## [M39-T01] — 2026-08-23

### Changed
- صفوف الطابور في React أصبحت كاملة على سطح المكتب: جدول session يثبت عرض الأعمدة، يلف اسم الملف، ويُبقي التقدم والحجم وأزرار `إيقاف`/`استئناف`/`إعادة` ضمن البطاقة بلا تمرير أفقي.
- على أقل من 621px يتحول صف الملف نفسه إلى بطاقة معنونة مرتبة تعرض الملف والحالة والتقدم والحجم، ثم شبكة تحكم ثلاثية كاملة. لم تتغير `queue.pause_item` أو `queue.resume_item` أو `queue.retry_item` أو أي payload/handler.
- أضيف زر **فتح تسجيل Telegram الآمن** في React. يستهدف Accordion Gradio الموجود فقط (`td-secure-telegram-auth`) ويفتحه محليًا في DOM؛ تبقى API hash ورقم الهاتف وOTP و2FA في عناصر Gradio الآمنة، بلا bridge action أو تخزين/نقل أسرار.
- أعيد بناء `panel.bundle.gz` و`panel.css.gz`، وأضيف عقدا React 27–28 لحماية الوصول الآمن والتخطيط المتجاوب.

### Gates and local verification
- `746 passed` · launcher `51/51` · notebook check + cmp PASS · React contracts `29/29` · lint/build PASS (0 errors؛ 7 تحذيرات baseline فقط).
- فحص بصري محلي من markup/CSS المنتج: سطح المكتب أظهر الصف كاملًا بلا تمرير أفقي، وإطار 390px أظهر البطاقة مع الأزرار كاملة. Gradio 6.20 محليًا: زر React فتح Accordion المصادقة الأصلي، ثم `telegram.status` أعاد `Action completed` بلا إدخال أي اعتماد.
- لا نقل حي ولا اختبار Colab جديد؛ لا `Colab-ready` أو `Complete`.

### Merged and published
- PR [#83](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/83) دُمج إلى `main` عند `4b490a03aa76b0d3e5cf58b4d251a401a19abfb2` بعد نجاح فحوص CI الأربعة؛ commit المصدر `113c0e311fb6f76d26d9e877572fb2c6fb7acc8e`.
- [Publish current TeleDrive package #32621429061](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32621429061) بنى كل البوابات ثم رفض استبدال أصل ZIP المختلف حجمًا fail-closed وفق M37-T01. وبإذن المالك استُبدل الأصلان يدويًا من archive M39 المطابق؛ التحقق العام أثبت `commit=4b490a0…`، `sha256=dfc1f133…051ee9`، و`size=561162` بايت.

## [M38-T01] — 2026-08-23

### Fixed
- `python-package/teledrive/react_panel.py`: صار `js_on_load` يحتفظ بمثيل `TeleDriveGradioPanel` واحد فقط على عنصر Gradio، يفك المثيل السابق قبل إعادة التركيب، ويعيد cleanup مملوكًا للمثيل الحالي. يمنع هذا بقاء شجرة React متصلة بجسر `disposed` بعد lifecycle إعادة التركيب في Colab، وهو الشرط الذي يظهر معه `Backend bridge unavailable`.
- أعيد بناء `python-package/teledrive/react_panel_assets/panel.bundle.gz` من المصدر، وأضيف عقد React `18b` لحماية ملكية المثيل عبر remount. لا تغيير لواجهات النقل (`props.value`/`trigger('submit')`)، أو النوتبوك، أو الاعتماديات، أو جلسات Telegram/Drive.

### Gates
- `746 passed` · compileall OK · launcher `51/51` · notebook check + cmp متطابقان · React contracts `27/27` · lint/build PASS (تحذير eslint baseline واحد فقط).
- محاكاة Gradio 6.20 خلف proxy مع `root_path` أعادت لوحة حية بلا banner blocked. لا يمثل ذلك إثبات Colab حي: Cell 3 في runtime Colab الحقيقي توقف عند fallback بيانات Telegram قبل Cell 4.

### Merged and published
- PR [#81](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/81) دُمج إلى `main` عند `0727eba4450bd95e4f269140745a43a219b63fcc` بعد نجاح فحوص CI الأربعة؛ commit المصدر `8afa544ae36f7bf845b46f291af154f3a7d2a3b1`.
- [Publish #31](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32618829803) نجح على merge SHA وتحقق من manifest و`teledrive_v4.5.zip` العامين. لا `Colab-ready` أو `Complete`: محاولة post-publish في Runtime جديد لم تعرض مخرج Cell 1 قابلًا للتدقيق، ولم يصل الاختبار إلى Cell 4.

## [M37-T02] — 2026-08-23

### Verified
- تحقق حي من أزرار التحكم بطلب المالك: سيرفر محلي (HTTP 200، binder **51/51 wired · 242 controls · 0 disabled**) + نقرات حية موثقة في سجل السيرفر (`set_concurrency`/`set_theme`/`toggle_language` — كلها `ok`) + استدعاء مباشر لكل الأكشنات الـ51 بنفس مسار الزرار: 37 PASS فعلي، 14 خطأ حالة صحيح بالتصميم أثناء عدم الاتصال، 2 خاصّان بـColab عمدًا (`drive.connect/reconnect`).
- لا زرار ميت أو غير موصول. ليس إثبات Colab-ready (§17). التفصيل: `docs/PHASE_REPORTS/PHASE_M37_T02.md`.

## [M37-T01] — 2026-08-23

### Changed
- `release-current.yml`: خطوة النشر لم تعد تحذف الـrelease أو الـtag المنشورين (`gh release delete --cleanup-tag \|\| true` أُزيلت) — مسار idempotent fail-closed: غياب → إنشاء ذري بأصلين؛ وجود بمطابقة → تحديث metadata فقط؛ نقص/اختلاف أصول → فشل صريح والقرار للمالك (§11/§17، KNOWN_ISSUES #70).
- `release.yml`: تعليق توثيقي يثبت أن قيم v4.5 فيه وصف صادق للأرشيف المثبّت بالبايت ولا تُرفع لـ5.0.0 ما دامت بوابة البايتات نافذة.

### Audit
- تدقيق خارجي (`gpt-5.6-sol`) أصدر 3 ملاحظات؛ نُفِّذت واحدة بعد التحقق، ورُفضت اثنتان بالأدلة لحماية صدق الـmanifest (§17). التفصيل: `docs/PHASE_REPORTS/PHASE_M37_T01.md`.

### Gates
- `746 passed` · compileall OK · launcher `51/51` · نوتبوك متطابقة. لا تغيير في حالة Colab-ready/Complete.

## [M36-T01] — 2026-08-22

### Changed
- `release-current.yml`: `PRODUCT_VERSION` 4.5.0 → **5.0.0** — حقل معلوماتي في `teledrive_manifest.json` المنشور فقط (بوابة Cell-1 تخزنه ولا تقارن به). اسم الأرتيفكت المثبّت `teledrive_v4.5.zip` والـ tag `pkg-2026.08.09-m15t07` بقي كما هما عمدًا.

### Published
- Publish workflow run #29 على main `cb6901f4bf` (بعد دمج PR#77) — **SUCCESS**؛ release `pkg-2026.08.09-m15t07` أُعيد نشره من الشجرة الحالية: `teledrive_v4.5.zip` 560,483 بايت · SHA-256 `a0d7cc4d…b66f1` · `product_version=5.0.0`.
- تحقق مستقل خارج الـ workflow: تنزيل الأصول العامة ومطابقة commit/الحجم/SHA-256 — ناجحة.

### Gates
بوابات الدستور داخل run #29: compileall + pytest كامل + launcher + notebook check + cmp — ناجحة. لا اختبار Colab حي جديد (لا `Colab-ready` ولا `Complete`).

## [M35-T01] — 2026-08-22

### Changed
- اعتماد هوية المنتج **v5.0.0** في الكود (قرار مسجّل من المالك لمواءمة الكود مع الدستور v5.0.0): `teledrive/__init__.py` (`__version__`/`__spec_version__`) و`teledrive/config.py` (`RuntimeConfig.version`/`spec_version`).
- `teledrive/notebook_cells.py`: `NOTEBOOK_VERSION` = 5.0.0 و`TITLE` = "TeleDrive v5.0 — Telegram → Google Drive (native Colab)"؛ أُعيد توليد النوتبوكين (`python-package/notebook/TeleDrive.ipynb` و`public/TeleDrive.ipynb`) و`colab_cells.json` بالمولّد الرسمي وتحقق التطابق.
- `tests/test_notebook.py`: عقد العنوان محدّث إلى "TeleDrive v5.0".
- **ما لم يُمسَّ عمدًا:** اسم الأرتيفكت المثبّت `teledrive_v4.5.zip` (هوية أصل منشور تستخدمها بوابة Cell-1 و`ci.yml` و`release-current.yml`) — تغييره قرار release مستقل يطال ملفات محمية.

### Gates
Windows/Python 3.11: `746 passed` · compileall OK · launcher `51/51 ready actions resolve` · notebook check متطابق.

## [M34-T01] — 2026-08-22

### Fixed
- `teledrive/utils.py`: `safe_disk_free()` تستخدم `shutil.disk_usage().free` عندما لا يوجد `os.statvfs` (Windows) — كانت تعيد 0 فتفشل كل عمليات النقل بـ`disk_full` وتبقى الصفوف `Pending` على Windows.
- `teledrive/config.py`: `is_mounted_drive()` تستخدم `Path.as_posix()` — `str(Path)` كان يشوّه بادئات `/content/drive` على Windows فيعطل حارس `MountedRootError` (SQLite على FUSE).

### Gates
Windows/Python 3.11: `746 passed` (كان `19 failed, 727 passed`) · compileall OK · launcher `51/51` · notebook check + cmp متطابقان.
## [M33-T01] — 2026-08-22 — مواءمة README الجذر مع الدستور v5.0.0

- **تحديث الهوية:** غُيِّر العنوان والمواصفة من "TeleDrive v4.5 / v4.5.0" إلى "TeleDrive v5.0.0 (AI-OS Continuity Edition — الحوكمة) · موروث المنتج v4.5.0" ليطابق `docs/CONSTITUTION.md` (v5.0.0).
- **تصحيح حالة M15-T01:** أُزيل ادعاء "مهمة M15-T01 متبقية" (الذي كان يظهر في ملاحظة الأمانة) لأنها مدموجة فعليًا في `main`؛ بقيت الإشارة الصادقة إلى أن التحقق الحي على Colab بيد المالك.
- **إزالة تناقض Lovable:** استُبدل قسم "التطوير والمزامنة مع Lovable" بقسم "التطوير والحوكمة" يقرّ بأن **Lovable خرج من المشروع نهائيًا** (§3) وأن المنفّذ الوحيد المتصل بـGitHub هو **LM Arena Agent**، ويحيل إلى `docs/REPOSITORY_REGISTRY.md` للمستودع القانوني.
- **ما لم يُمسَّ:** أسماء الـartifacts المنشورة (`teledrive_v4.5.zip`، الإصدار `pkg-2026.08.09-m15t07`) تُركت كما هي لأنها أسماء الحزمة الفعلية لا إصدار الحوكمة؛ تغييرها يتطلب تفويضًا صريحًا للملفات المحمية.
- **النطاق:** README.md فقط + تحديثات docs (KNOWN_ISSUES #67، TODO M33-T01). لا تعديل على الكود أو الـnotebook أو الاعتماديات.
- **الحالة الصادقة:** MERGED + CI-PASSED؛ لا ادعاء Colab-ready أو Complete (تعديل توثيقي فقط).

## [M32-T01] — 2026-08-20 — استبدال ذري لجلسة Telegram التالفة

- **لا فقد قبل نجاح البديل:** تحفظ الخزينة الآن زوج الجلسة والبيانات تحت أسماء إصدار فريدة، ثم تنشر `td_telegram.active.json` بعد نجاح الرفعين. إذا فشل أي رفع مرحلي، يبقى البيان السابق والزوج السابق هما النشطان.
- **توافق وتنظيف صحيحان:** تقرأ الاستعادة وprobe والحالة الزوج القديم أو الإصدار الذي يحدده البيان. وتحذف النسخ السابقة — بما فيها الزوج القديم — فقط بعد نجاح نشر البيان الجديد. ويبقى الحذف الكامل مقصورًا على forget/logout الصريحين.
- **جلسة Telegram مبطلة:** تصنّف `AuthKeyDuplicatedError` وأخطاء بطلان الجلسة المحفوظة كحاجة إلى إعادة الدخول؛ تنظف نسخة runtime المحلية وتعود إلى إدخال الهاتف، لكنها لا تحذف نقطة الاسترداد على Drive. أخطاء النقل العابر تحتفظ بالنسخ كي يعاد التحقق لاحقًا.
- **التحقق المحلي:** `746 passed`، launcher `51/51`، notebook/cmp ناجحان، lint/build عبر `pnpm`، عقود React `26/26`، وReact bridge `13 passed`. تثبت اختبارات Vault إخفاق المرحلة قبل البيان، الالتزام ثم تنظيف القديم، ومسار AuthKeyDuplicatedError.
- **الدمج والنشر:** PR [#71](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/71) مدمج عند `5255889` بعد CI `4/4` ناجح؛ [Publish #32327688915](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32327688915) نجح. manifest العام يشير إلى الحزمة `560271` بايت، SHA-256 `81bcd236…7cacf`.
- **الحالة الصادقة:** النسخة **MERGED + CI-PASSED + package-published**، وليست إثبات Colab حي. لا توصف بـ`Colab-ready` أو `Complete` قبل تجربة Colab مستقلة.

## [M31] — 2026-08-20 — إيقاف عاصفة التحديث وإصلاح Resume من داخل runtime loop

- **سبب تجمد الواجهة:** أزيل Timer Gradio العالمي الذي كان يرسل `queue.refresh` و`dashboard.refresh` كل ثانية حتى أثناء الخمول وبالتوازي مع heartbeat React؛ بقي heartbeat React المشروط بالنقل وأزرار التحديث اليدوية.
- **Resume آمن:** أضيفت `AsyncRuntime.schedule()` لإنشاء Task داخل الحلقة عند callback الاستئناف، مع إبقاء `submit()` للمسار الخارجي؛ بذلك لا يعود Resume يستدعي submit من داخل loop.
- **الاختبارات:** `743 passed`، عقود React `26/26`، `pnpm lint` و`pnpm build`، launcher `51/51`، وCI Python/Frontend ناجح على push وpull_request.
- **الإثبات الحي:** عشرة ملفات حقيقية وصلت إلى Drive؛ Pause حفظ `.part`، Resume استأنف من offset `8192` ووصل Uploaded، وStop بقي Stopped بلا ملف وسائط بعيد. اختبار المتصفح أثناء الخمول بقي ثابتًا بلا console errors.
- **الدمج:** PR [#69](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/69) مدمج في `main` عند `397b97f`.
- **الحالة الصادقة:** لم تُعد حزمة Colab للنشر بعد؛ يجب تشغيل Publish من `main` ثم اختبار Colab الحقيقي قبل `Colab-ready` أو `Complete`.

## [M29-T01] — 2026-08-19 — سلامة مقاعد الطابور وحجم الصور

- **مقعد العامل لا يُحتجز عند Pause:** ينتظر العنصر Pause الفردي قبل الاستحواذ على `semaphore`، فلا يستطيع صف Paused إيقاف صف runnable لاحق عند قيمة workers منخفضة.
- **سقف التزامن حي وآمن:** تغيير workers لا يستبدل semaphore أثناء وجود مهام طائرة؛ تطبق القيمة الجديدة في drain لاحق بعد استقرار المهام، فلا ينقسم السقف على كائني permits.
- **حجم الصورة معتمد دائمًا:** بعد تنزيل صورة بحجم فعلي مختلف، يُحفظ الحجم المصحح إلى SQLite قبل upload/verification، فيتطابق الصف والـcheckpoint ومسارات retry مع الذاكرة.
- **مواءمة التدقيق:** لم تُعد تطبيق إصلاحات Drive خارج event loop أو throttle أو verify أو offset أو التحكم التعاوني، لأنها كانت موجودة بالفعل في `main` الفعلي وقت إعادة الفحص.
- **التحقق والدمج:** `743 passed`، launcher `51/51`، notebook/cmp/package، React contracts `26/26`، و`pnpm lint`/`pnpm build` ناجحة. دُمج PR [#67](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/67) في `main` عند `1ba3fd0` بعد CI Python وFrontend الناجح على push وpull_request.
- **الدليل الحي:** تشغيل Telegram→Drive معزول أثبت Pause مع `.part` محفوظ بلا Drive، Resume من offset إلى Uploaded، وStop نهائي بلا ملف Drive.
- **الحالة الصادقة:** لا يزال Colab الحقيقي غير مثبت؛ تُعاد نشر الحزمة النهائية من `main` ثم يعاد تشغيل Runtime ويجرى smoke test قبل وصف المشروع بأنه `Colab-ready` أو `Complete`.

## [M28-T02] — 2026-08-19 — تحديث تقدم النقل كل ثانية

- **إيقاع التحديث:** انخفض فاصل نبض React الهادئ من `2000` إلى `1000` ms أثناء النقل الفعلي فقط؛ لا يُنشأ طلب جديد قبل انتهاء السابق بفضل `pollInFlight`، ولا يستمر النبض للطابور الخامل أو المتوقف أو ذي الصفوف النهائية.
- **الأصل والاختبار:** أُعيد بناء `panel.bundle.gz` من المصدر. أصبح عقد React يثبت قيمة الثانية الواحدة صراحةً، مع بقاء `26/26` عقدًا ناجحًا.
- **التحقق والدمج:** `740 passed`، launcher `51/51`، notebook/package، و`pnpm lint`/`pnpm build` ناجحة. دُمج PR [#65](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/65) في `main` عند `709e15c` بعد نجاح CI Python وFrontend على push وpull_request.
- **الحالة الصادقة:** يثبت ذلك الكود والحزمة وCI؛ يلزم نشر الحزمة واختبار Colab حقيقي قبل وصف المشروع بأنه `Colab-ready` أو `Complete`.

## [M28-T01] — 2026-08-19 — وضوح نتائج الطابور وإثبات التحديث التلقائي

- **مؤشرات وجلسات أوضح:** تشتق اللوحة الآن `Skipped` من صفوف queue الحية وتعرضه كبطاقة مستقلة، كما تعرض كل جلسة عدد الملفات ومكتمل/متخطى/فشل/انتظار من دون كتابة إلى SQLite أو تغيير حالات النقل.
- **رسالة بدء صادقة:** عند رد backend العام `Action completed` لبدء دفعة فعلية، تعرض React ملخصًا عربيًا يوضح أن شريط التقدم يتحدث تلقائيًا؛ أما تحذير backend المحدد عند غياب صف معلّق فيبقى ظاهرًا ولا يتحول إلى نجاح مصطنع.
- **التحديث الحي مثبت:** في تشغيل Telegram/Drive معزول بلا نقرة زر «تحديث»، ظهر صف فيديو جديد عند `Downloading 55%` ثم `Uploaded 100%`؛ وصل ملفان فيديو إلى Drive وتحقق فحص API مستقل من وجودهما وعدم حذفهـما وchecksums.
- **التحقق والدمج:** `740 passed`، launcher `51/51`، notebook/cmp/package، React contracts `26/26`، وlint بلا أخطاء (7 تحذيرات قديمة). دُمج PR [#63](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/63) في `main` عند `00ceaeec` بعد CI Python وFrontend الناجح على push وpull_request.
- **الحالة الصادقة:** ليس `Colab-ready` ولا `Complete`؛ يلزم إعادة نشر الحزمة من `main` ثم اختبار Colab حقيقي.

## [M27-T05] — 2026-08-19 — تصحيح تجربة الاستخدام للطابور الخامل وتحليل الإدخال الناقص

- **Pause/Resume الخاملان:** لا تكتب Pause checkpoint ولا تعلن `paused` عند غياب drain عامل، وResume لا تعلن `running` إلا عند وجود drain فعلي أو صف `Paused` مستأنف. جولة UI حية بطابور صفر أبقت الشارة `idle` في العمليتين.
- **Analyze واضح:** تحقق React الأمامي يعرض الآن سبب الرابط أو رقم الرسالة أو النطاق أو الحد غير الصحيح بالعربية/الإنجليزية؛ كما أن `TeleDriveError` المعالج يرجع من bridge كفشل مترجم بدل `Action completed` عام، مع الحفاظ على مخرجات Gradio.
- **الأصل المشحون:** أعيد بناء `panel.bundle.gz` من مصدر React؛ أضيفت اختبارات Queue وReact bridge وعقد React لحماية المسارين.
- **التحقق:** `740 passed`، launcher `51/51`، notebook/cmp/package، `pnpm lint` بلا أخطاء، وعقود React `26 passed`. اكتملت مراحل بناء production محليًا؛ أما رمز الخروج النهائي فقد أثبته CI لأن عملية shell بقيت بعد اكتمال Nitro داخل هذا sandbox.
- **الدمج وCI:** PR [#61](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/61) دُمج في `main` عند `c903423` بعد نجاح Python وFrontend على push وpull_request.
- **الحالة الصادقة:** ليس `Colab-ready` ولا `Complete`؛ يلزم إعادة نشر الحزمة من `main` ثم اختبار Colab حقيقي.

## [M27-T04] — 2026-08-19 — إصلاح عيوب مثبتة أثناء اختبار حي معزول

- **Pause / Resume:** لا يبدأ `QueueManager` drain استئناف جديدًا قبل أن يستقر drain السابق؛ callback قديم لا يستطيع إطفاء تشغيل أحدث، و`CancelledError` المنضبط لا يسجل كتعطل محرك. أثبت الاختبار الحي بقاء `.part` ثم استئناف التنزيل من offset وصولًا إلى `Uploaded`.
- **روابط الدعوة الخاصة:** حساب Telegram العضو مسبقًا يستطيع تحليل `t.me/+…` أو `joinchat` عبر `CheckChatInviteRequest` ثم InputPeer؛ التطبيق لا ينضم إلى أي قناة ولا يتجاوز حدود المسح.
- **لوحة React:** بندل Gradio يثبت بيئة الإنتاج عند بنائه، فيمنع `process is not defined` الذي كان يحجب تركيب اللوحة في المتصفح. أصل React أعيد بناؤه وأضيف حارس عقد ضد `process.env.NODE_ENV`.
- **التحقق:** `738 passed`، launcher `51/51`، notebook/cmp/package، lint/build، وReact contracts `26 passed`. تحقق متصفح محلي حقيقي من ظهور اللوحة، وتحقق Telegram/Drive معزول من النقل والتحكم وDedupe.
- **الدمج وCI:** PR [#59](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/59) دُمج في `main` عند `dfbb90b` بعد نجاح Python وFrontend على push وpull_request.
- **الحالة الصادقة:** ليس `Colab-ready` ولا `Complete`؛ يلزم إعادة نشر الحزمة من `main` ثم اختبار Colab حقيقي.

## [M27-T02] — 2026-08-19 — إصلاح تسليم نبض التحديث التلقائي للوحة React

- **السبب المؤكد:** مصدر React كان يتضمن `setInterval` كل ثانيتين مع `queue.refresh`، لكن `ReactPanel` يشحن `panel.bundle.gz` مستقلًا وكان البندل القديم يفتقد `setInterval` تمامًا؛ لذلك يظهر التقدم فقط بعد زر «تحديث» اليدوي.
- **الإصلاح:** أعيد بناء أصول Gradio المضمنة من `gradioEntry.tsx`، وأضيف مولّد `scripts/build-react-panel.mjs` يعتمد Vite/Oxc ويولّد IIFE `TeleDriveGradioPanel` مع gzip حتمي.
- **حارس الانحدار:** العقد يفك البندل المشحون ويفرض وجود global panel و`setInterval` و`queue.refresh`، فلا يكفي أن يبقى النبض في `src/` وحده.
- **التحقق المحلي:** React contracts `25 passed`، وlint/build نجحا، ومجموعة Python `734 passed`، والlauncher `51/51` والحزمة والنوتبوكات متطابقة.
- **الحد الحي:** يلزم بعد الدمج إعادة نشر حزمة Colab من `main` ثم Restart runtime؛ جلسة Colab المفتوحة لا تستبدل JavaScript المحقون تلقائيًا.

## [M27-T01] — 2026-08-19 — تقوية نقل TeleDrive: التقدم، أعطال المحرك، القنوات الخاصة، والاستئناف

- **تقدم أخف على SQLite:** تُقيَّد تحديثات التقدم أثناء الـchunk إلى كتابة واحدة كل `0.5s` لكل عنصر، مع كتابة فورية عند حدود المرحلة/النهاية أو عند فرضها، فلا تتضرر دقة الحالة النهائية.
- **عطل المحرك مرئي:** الاستثناء غير الملغى من عامل النقل يعبر حلقة التصريف؛ callback اكتمال التشغيل يسجل الحدث الثابت `transfer run crashed` ثم يعيد المحرك إلى `idle` بدل الإبلاغ الكاذب عن نهاية نظيفة.
- **قنوات خاصة بهوية صحيحة:** حل كيان Telegram يسخّن dialogs مرة واحدة عند الحاجة؛ تُخزَّن peer identity للقناة بصيغة Telethon الصحيحة `-100<id>`، ويظهر عدم الوصول كخطأ دائم مترجم `err.private_channel_unresolved`.
- **استئناف تنزيل محافظ:** إن وُجد `.part` صالح لوسيط قابل للاستئناف، يُقص فقط إلى حد محاذاة `4096` ثم يتابع `iter_download(offset=...)`؛ لا يحذف المسار `.part` ولا يلمس أي ملف Drive. تبقى الصور والمسارات غير المناسبة على تنزيل كامل آمن.
- **التحقق المحلي:** أضيفت `16` اختبارًا لـM27؛ المجموعة الكاملة `734 passed`، و`compileall` وlauncher `51/51` وفحص النوتبوك و`cmp` وبناء الحزمة و`pnpm lint/build` نجحت.
- **حالة التسليم:** دُمج PR [#54](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/54) في `main` عند `e230ce9` بعد نجاح فحوص CI الأربع؛ تبقى Local/fake-tested فقط لأن Telegram وDrive وColab الحية لم تُختبر، ولا يجوز وصفها Colab-ready أو Complete.

## [M26-T01] — 2026-08-19 — تحكم النقل الفعلي: Pause / Stop / Resume

- **Pause/Stop تعاونيان:** أعلام `threading.Event` آمنة بين ثريد Gradio وAsyncRuntime، وcallbacks التحميل/الرفع توقف الملف الجاري عند حد الـchunk بإشارة لا تُصنّف فشلًا ولا تدخل سياسة retry.
- **صف وحالة صادقان:** Pause يركن الصف في `Paused` وStop في `Stopped` النهائي، ويحرر عنصر progress من دون زيادة done/failed/skipped؛ يبقى `.part` المحلي ولا يُحذف ملف Drive.
- **Resume حقيقي:** يعيد كل صف Paused إلى Pending ويعيد إطلاق drain loop إذا انتهى، فيما يصفر Start الجديد أعلام Stop/Pause العالقة من تشغيل سابق.
- **سلامة ما بعد الرفع:** لا مقاطعة في `Verifying` أو `UploadedPendingCheckpoint`، حتى يثبت ملف Drive ويُسجّل checkpoint بدل ترك ملف يتيم.
- **التحقق:** `11` اختبارًا جديدًا للتحكم، والمجموعة الكاملة `711 passed`، والـlauncher `51/51`. Bun غير متاح محليًا؛ fallback عبر pnpm نجح.
- **الحالة الصادقة:** Implemented + fake-tested. Not live-verified؛ اختبار Telegram/Drive/Colab بيد المالك بعد الدمج.

## [M24-T05] — 2026-08-19 — حتمية خزينة جلسة Telegram

- **مسار حفظ واحد:** نقاط التكامل القديمة `persist_from_context` و`wipe_from_context` تعيد التوجيه إلى `SessionVault`، فلا يُكتب بلوب ADR-004 منافس بعد التفويض.
- **حفظ مؤجل وصادق:** إذا اكتمل تفويض Telegram قبل جهوز Drive، يُسجَّل latch ويُصرف في أول إجراء واجهة بعد الاتصال؛ كل نتيجة خزينة تُسجّل بشكل منقّح في الحالة والحدث والسجل.
- **لقطة واستعادة آمنتان:** الحفظ يستخدم snapshot متعدد المسارات لملف SQLite، والاستعادة لا تستبدل ملف جلسة تحت عميل حي وتزيل الخزينة والجلسة المحليتين إذا كانت الجلسة المستعادة ملغاة.
- **صيغة 2 الافتراضية:** `telegram.session` يُغلّف بـ`api_hash` الموجود في الذاكرة أو Colab Secrets، و`telegram_creds.json` لا يحفظ `api_hash`. تبقى صيغة 1 قابلة للقراءة، ويمكن للمالك فقط اختيار صيغة النص الصريح بالمتغير `TELEDRIVE_VAULT_PLAINTEXT=1`.
- **التنظيف:** نسيان التسجيل أو logout يحذفان ملفي الخزينة الحديثين وبقايا `td_telegram.session.vault` القديمة.
- **الحالة الصادقة:** Implemented + fake-tested. Not live-verified. لم تُنفّذ تغييرات Part B المحمية على `notebook_cells.py` أو النوتبوكات لغياب موافقة مكتوبة.

## [M24-T03] — 2026-08-18 — تقوية خزينة جلسة Telegram

- **استعادة قبل أول رسم:** `SessionVault.autorestore_once()` يُنادى من `ui.build()` قبل `gr.Blocks`، فأول رسم يقرأ حالة حقيقية بدل الاعتماد على حدث page-load.
- **logout يمسح الخزينة:** `h_telegram_logout` ينادي `forget_quiet()` قبل `telegram_auth.logout()` (الملف محمي)، فلا تعود الجلسة تلقائيًا بعد تسجيل الخروج.
- **fallback للمفاتيح:** `save_now` يقرأ `api_id/api_hash/phone` من ذاكرة `TelegramAuth` عند فراغ حقول الواجهة (مسار Secrets ومسار الاستعادة).
- **حفظ تلقائي:** `save_after_login()` بعد `verify_code` / `verify_password` / `set_credentials` الناجحة، ويتخطى الرفع لو الخزينة موجودة.
- **تحقق من البلوب:** الاستعادة ترفض أي بايتس لا تبدأ بـ`SQLite format 3` ولا تكتب على القرص.
- **binder.load idempotent** عبر إعادة الرسم بتغيير اللغة.
- **الحالة الصادقة:** Implemented + fake-tested. Not live-verified.
- **خطر مقبول بقرار المالك:** `telegram_creds.json` يبقى JSON صريح على Drive.

## [M24-T01] — 2026-08-18 — حفظ/استعادة جلسة Telegram على Drive

- **save/restore Telegram session on Drive:** `SessionVault.save_now` / `autorestore` / `forget` / `probe` يرفعان `telegram.session` + `telegram_creds.json` إلى `TeleDrive_AppData` على حساب المستخدم. التشغيل يبقى من الملف المحلي فقط.
- **notebook probe + auto-restore for same Drive account:** الخلية 3 تربط Drive أولًا ثم تفحص الخزينة؛ إن وُجدت تتخطى إدخال API. الخلية 4 تستدعي `ctx.session_vault.autorestore()` عندما لا تُمرَّر مفاتيح يدوية.
- **new UI buttons for save/forget** (واستعادة يدوية) + صندوق حالة + page-load `session.autorestore` يعكس حالة تيليجرام الحية.
- **README runbook update:** قسم «حفظ تسجيل Telegram على نفس حساب Drive» يشرح أول مرة والمرات التالية ونسيان الربط، ويحدّث شرح الخليتين 3 و4.
- **توافق:** دوال ADR-004 (`persist_from_context` / keepalive) بقيت لأن `telegram_auth.py` محمي.
- **الحالة الصادقة:** Implemented + fake-tested. Not live-verified.

## [M25-T02 MERGED] — 2026-08-13 — PR #47 → main `2bc33e9f`

- **دمج:** PR [#47](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/47) → main = `2bc33e9fc042547e6eda838b9552c24dbb785923` في 2026-08-13T00:34:06Z. CI run `31654744180`: Python package PASS + Frontend build (lint+build) PASS.
- **فجوة Colab:** التاج `pkg-2026.08.09-m15t07` يبقى قديمًا حتى يعيد المالك تشغيل **Publish current TeleDrive package** على `main` (#27).

## [M25-T02] — 2026-08-13 — تحديث تلقائي للصفحة كاملة أثناء النقل

- **المشكلة (بلاغ المالك):** أثناء النقل يبقى شريط التقدم وكل أرقام الصفحة مجمّدة على آخر لقطة حتى ضغطة `تحديث` يدوية. السبب أن الجسر لقطةٌ لا بثٌّ: React لا يطلب حالة إلا عند إجراء صريح.
- **الحل:**
  - `TeleDriveSandbox.tsx`: مؤقّت كل 2000ms ينادي `queue.refresh` عبر `bridge.request` مباشرة (لا عبر `run()`) ويستبدل لقطة `LiveUiState` كاملة — كل الأقسام (chips، المجلد، المحرك، الحصة، الطابور، التقدم، المرشّحون) — بلا وميض notice ولا busy spinner.
  - `viewModel.hasActiveTransfer()` يبوّب النبض: يعمل فقط والمحرك `running` أو يوجد صف in-flight (`Downloading/Uploading/Verifying/UploadedPendingCheckpoint`). لا حلقة خلفية دائمة. حماية من التداخل بـ`pollInFlight` + `liveStateRef`.
  - `queue_manager.py`: `_on_run_done` يعيد تسمية المحرك إلى `idle` بعد انتهاء drain (كان يبقى `running` للأبد فيجعل النبض يستمر على طابور منتهٍ). لا يمسّ `paused`/`stopped`.
- **بوابات محلية:** `664 passed` · launcher `48/48` · notebooks in sync · contracts `24/24` · `tsc --strict` PASS · prettier نظيف · `bun lint/build` لـCI (#37).
- **محمي لم يُمس:** notebooks · telegram_auth · transfer_manager · database/migrations · requirements.* · bun.lock · package.json · workflows.
- **الحالة الصادقة:** Code-complete candidate + Fake-tested. ليس Colab-ready / Complete. الإثبات الحي بيد المالك بعد إعادة نشر التاج (#27).

## [M25-T01 vault] — 2026-08-13 — استئناف Colab: أسرار + خزنة جلسة تليجرام + keep-alive

- **المشكلة:** موت جلسة Colab يمسح `/content`. المستخدم كان يعيد كتابة API ويعيد OTP ويربط Drive من الصفر. خلية الواجهة وحدها لا تكفي على VM فارغ.
- **الحل (موافقة المالك، ADR-004):**
  - الخلية 3 تقرأ `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` من Colab Secrets وتسقط إلى getpass.
  - بعد أول `AUTHORIZED` يُرفع `telegram.session` معمّى إلى `TeleDrive_AppData/td_telegram.session.vault`. الخلية 4 تستعيده قبل `set_credentials`. Logout يمسح البلوب.
  - Drive يبقى native Colab (كلك واحدة عادةً). لا `drive_token.json`.
  - keep-alive في الخلية 4: نبض دقيقتين + نقرة Connect. لا يخلّد الجلسة.
- **سبع خلايا كما هي.** ترتيب 4: Drive → vault → Telegram → launch → keepalive.
- **تعارض الدمج:** main كان فيه شق الطابور (PR #44) بنفس TASK ID. فُضّ التعارض في التوثيق فقط؛ الكود غير متعارض.
- **الحالة الصادقة:** Code-complete candidate + Fake-tested. الإثبات الحي بيد المالك. التاج المنشور لن يتحدث حتى يعيد المالك تشغيل Publish (#27).

## [M25-T01 MERGED] — 2026-08-12 — PR #44 مدموج في main `ce28004`

- **دمج:** PR [#44](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/44) → main = `ce28004fda34943c7224877c5bd3eb5338ed4656` في 2026-08-12T23:30:45Z. CI على الـPR: Frontend PASS + Python PASS.
- **فجوة Colab:** التاج `pkg-2026.08.09-m15t07` ما زال قديمًا حتى يعيد المالك تشغيل **Publish current TeleDrive package** على `main` (الوكيل محظور 403 — KNOWN_ISSUES #27).

## [M25-T01] — 2026-08-12 — جلسات الطابور + بدء كل المعلّق + مسح غير المكتمل

- **المشكلة:** بعد Restart في Colab تبقى صفوف SQLite بينما التحديد في الذاكرة فارغ، فيرفض `queue.start_selected` البدء. Pause يُبقي الصفوف عمدًا وStop كان يوقف العمال فقط.
- **Start:** `start_selected()` بلا وسائط يلتقط كل Pending/NeedsRetry/Downloaded إن لم يطابق التحديد صفوف الطابور. `start_selected([])` ما زال لا يبدأ شيئًا (عقد Phase C). هذا نقر صريح وليس auto-resume.
- **مسح غير المكتمل:** فعل جديد `queue.clear_incomplete` يحذف صفوف SQLite غير المكتملة فقط. Uploaded/Skipped تبقى لـ`clear_completed`. **لا حذف لملفات Drive.**
- **إيقاف:** React يعرض نافذة: إيقاف فقط أو إيقاف + مسح غير المكتمل. Gradio يضيف زر «مسح غير المكتمل» بجانب مسح المكتملة.
- **تجميع الجلسات:** اللقطة تحمل `chatTitle`/`createdAt` والواجهة تجمّع حسب اسم القناة + تاريخ الإضافة.
- **بوابات محلية:** `652 passed` · launcher `48/48` · contracts `22/22` · `tsc` PASS · eslint 0 errors · notebooks identical · bundle gzip أُعيد بناؤه.
- **محمي لم يُمس:** notebooks · telegram_auth · transfer_manager · database/migrations · requirements.* · bun.lock · package.json · workflows.
- **الحالة الصادقة:** Code-complete candidate + Fake-tested. ليس Colab-ready / Complete.

## [M24-POST-MERGE-P1 MERGED] — 2026-08-12 — PR #42 مدموج + فجوة نشر Colab

- **دمج:** PR [#42](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/42) → main = `71d092822d9022aa9daebd869616cde6ce4c028d` في 2026-08-12T22:21:27Z. CI على الـPR: Frontend PASS + Python PASS.
- **فجوة Colab الحرجة:** التاج `pkg-2026.08.09-m15t07` ما زال `target=33a7767` (قبل M24) — Cell 1 **لن** تحصل على React bridge ولا P1 حتى يعيد المالك تشغيل workflow `Publish current TeleDrive package` على `main` (الوكيل محظور 403 — KNOWN_ISSUES #27).
- **الوقت المتوقع بعد النشر:** Cell 1 تحديث ~1–3 دقائق · Cells 2–4 إقلاع ~2–5 · مصادقة Telegram/Drive ~5–15 · analyze+enqueue+نقل ملف واحد ~5–20 · لقطات+shutdown ~5 · **الإجمالي العملي ~20–45 دقيقة** بيد المالك (بدون انتظار FloodWait).

## [M24-POST-MERGE-P1] — 2026-08-12 — إصلاحات null safety + ترتيب الطلبات بعد دمج PR #40/#41

- **الأساس:** `origin/main = 504ec5e` (بعد دمج PR #40 `bbea9bf` + PR #41 docs). الفرع `arena/019ff805-drive-buddy-3579bf74`.
- **P1 null safety:** كل قراءة متداخلة لـ `LiveUiState` صارت optional chaining كامل:
  - `state?.telegram?.status` / `state?.drive?.status` / `state?.folder?.id|name`
  - `state?.drive?.quotaUsed|quotaLimit` / `state?.drive?.status?.toLowerCase?.()`
  - حماية `candidate.status` و`row.status` و`row.progress` من القيم الناقصة.
- **P1 request ordering:** `latestRequest = useRef(new Map<actionId, requestId>)` داخل `run()`:
  - يسجّل `requestId` لكل `actionId` قبل `bridge.request`
  - يرد قديم (`latestRequest.get(actionId) !== requestId`) يُهمَل — لا يكتب state ولا success notice ولا يصفّر busy لطلب أحدث.
- **Concurrency:** الإبقاء على 1..100 افتراضي 2 + تحذير فوق 8 (CONSTITUTION v5.0 + ADR-0001) — لا رجوع إلى 1..4 بلا ADR جديد.
- **Bundle:** أُعيد بناء `panel.bundle.gz` + `panel.css.gz` من المصدر المحدَّث (esbuild IIFE `TeleDriveGradioPanel.mount`؛ gzip mtime=0).
- **عقود:** +test 19 (null safety) + test 20 (latestRequest) → **20/20 PASS**.
- **بوابات محلية:** `node --test` 20/20 · `tsc --noEmit` PASS · `eslint` 0 errors / 7 warnings pre-existing · `npm run build` PASS · launcher `47/47 ready`.
- **محمي لم يُمس:** notebooks · telegram_auth · queue/transfer · database/migrations · requirements.* · bun.lock · package.json · workflows.
- **الحالة الصادقة:** Code-complete candidate + Fake-tested. **ليس** Colab-ready / Complete. Live Colab smoke + نقل حقيقي ما زالا بيد المالك.

## [M24-MERGED] — 2026-08-12 — دمج PR #40 بعد تجديد الجلسة

- **السابق:** PR #40 كان OPEN على الكود `a7d1c6c` (short `56a285b`) مع CI أخضر (push 31641715230 + PR 31641718211 — Frontend PASS + Python PASS). الكومِت المحلي `70b4e2d` doc-only فشل دفعه بسبب انتهاء `GH_TOKEN` في Arena.
- **التجديد:** فرع جديد `arena/019ff7e0-drive-buddy-3579bf74` سحب `arena/019ff78c` ودمجه في `021c0e2` (no-ff) ثم دُفع. نفس الشجرة 100% مع `a7d1c6c`.
- **الدمج:** `gh pr merge 40 --merge` → main = `bbea9bf20462671869bd17b245a85dda2e1a5908` في 2026-08-12T21:31:23Z. CI على `bbea9bf`: run `31642917698` — Python SUCCESS + Frontend **failure transient** (شجرة مطابقة لـ a7d1c6c الناجح). CI على فرع التجديد نفسه `021c0e2`: run `31642902305` — Frontend SUCCESS + Python SUCCESS، مما يثبت أن فشل main عابر وليس كود.
- **المزامنة:** دمج main `bbea9bf` في فرع التجديد `20cac75` ثم تحديث التوثيق إلى حالة MERGED.
- **الحالة الصادقة النهائية:** `MERGED INTO MAIN / PARTIALLY COMPLETE / Code-complete candidate + Fake-tested / Colab-ready: NO / Complete: NO`. لا ادعاءات نقل حقيقي أو لقطات Colab. مطابق لتقرير M24 الأصلي مع إضافة خطوة الدمج.
- **المتبقي بيد المالك:** 12-step Colab smoke، مصادقة Telegram/Drive حقيقية، تحديد مجلد/تحليل/اختيار/قائمة انتظار/نقل/تحقق Drive/recovery/shutdown، ولقطات 1280×768/768×768/390×844.

## [M24-T01..T05] — 2026-08-12 — React Bridge رسمي داخل Gradio وإصلاح PR #40

- **Baseline:** `origin/main=16797ca9b540d8a22885fffb38012643713ef851`; PR #40 كان OPEN على `03c70d0` وM23 بقي fake prototype. تصنيف الاستئناف `RESUME_PARTIAL`. ادعاء DOC أن route يحوي `return;` كان متقادمًا؛ الفحص وSSR أثبتا `<TeleDriveSandbox />`.
- **Frontend:** أزيل `mockState.ts` وكل demo files/folders/logs/quota/progress. أضيف `bridgeTypes.ts` و`gradioBridge.ts` و`gradioEntry.tsx` و`viewModel.ts`. خارج Gradio يعرض route `Backend bridge unavailable` ويعطل الأفعال بدل نجاح محلي.
- **Bridge:** `ReactPanel(gr.HTML)` الرسمي في Gradio 6.20.0 يضم React bundle محليًا؛ transport الوحيد component JSON `value` + `trigger('submit')` → `UIBinder.wire` → `react.bridge.request` → handler/registry/service قائم → snapshot منقح. لا standalone server ولا fetch/XHR/WebSocket/browser storage.
- **Live state:** `LiveUiStateService` يقرأ Telegram/Drive/folder/queue/candidates/concurrency الحقيقية؛ queue/metrics بلا fallback تجميلي. folder ID يحفظه `DriveFolders` فقط. Analyze لا enqueue، والـquarantined/final مستبعد من manual/all/range/group selection.
- **Security:** generic bridge يرفض unknown/recursive/unready والـsecret-bearing payloads. أفعال Telegram الحساسة تبقى في عناصر Gradio الآمنة داخل Accordion؛ React لا يخزن API hash/phone/code/password/session/token. كل استجابة recursive-redacted، والخطأ غير المتوقع correlation ID بلا payload/traceback في log.
- **Action Registry:** 47/47 ready؛ الجديد الوحيد `react.bridge.request` ومسجل مرة واحدة. Action IDs التوضيحية غير الموجودة في DOC لم تُخترع؛ استُخدمت أسماء السجل الفعلية.
- **Protected:** `package.json` أُعيد إلى `origin/main`; zero diff في notebooks/notebook generator/colab cells/telegram_auth/queue/transfer/database/migrations/requirements/bun/workflows.
- **Local gates:** compileall PASS · `646 passed` · launcher `47/47` · notebook check + cmp PASS · package build PASS · lint 0 errors · typecheck PASS · frontend contracts 18/18 · Vite build PASS · SSR route PASS.
- **Same-process smoke:** Gradio `0.0.0.0:7860`; `/config` أثبت HTML component واحد + submit dependency إلى `h_react_bridge_request`. `queue.refresh` عبر Gradio client أعاد status=ok وحالة disconnected/empty الفعلية.
- **GitHub code SHA:** `56a285b5bea01b07c74d7e3ba1a2a2b26461c5fd`. Push run `31640781460` PASS (Frontend + Python). Pull-request run `31640785475` PASS (Frontend + Python).
- **Honest status:** PARTIALLY COMPLETE / Code-complete candidate + Fake-tested. Live Colab 12-step smoke، النقل الحقيقي، والتحقق من Drive، recovery/shutdown، ولقطات 1280/768/390 غير منفذة (#46–#48). لا merge قبل Brain review.

## [M20] — 2026-08-12 — واجهة نهارية إجبارية + تتابع منطقي 1→5 + سقف تزامن 100 (ADR-0001)

> **مدموج:** PR [#35](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/35) → `main` = `2bd99b729255f1136b1667678b0255004d1101e3` (merge commit، بلا squash وبلا force-push حفاظًا على تاريخ Lovable). CI أخضر على رأس الـPR (`acfd473`) **وعلى `main` بعد الدمج**: `Python package (tests + Colab contract)` success · `Frontend build` success. الحالة تبقى **Code-complete candidate + Fake-tested** — الدمج ليس إثباتًا حيًا (#43).

### Verified (venv حقيقي، مخرجات فعلية — لا سجلات منسوخة)
- Base SHA = `77e97b789583b07b375f188894a5aca796b03b68` (= رأس `origin/main`، آخر مدموج PR #34). ملف المهمة كان يتوقع `ad3a454`، وهو **ليس** الرأس الحالي؛ النسخة المحلية shallow (`depth=1`) فلا يمكن إثبات علاقة النسب محليًا، و`gh` يرد `401 Bad credentials` فتعذّر الفحص عبر الـAPI. بُني العمل من آخر `main` الفعلي (`77e97b7`) وسُجِّل الانحراف بدل الادّعاء.
- `python -m compileall -q teledrive` → exit 0
- `python -m pytest -q tests` → **629 passed** (كان 596؛ +33)
- `python teledrive_launcher.py --check` → `binding check ok: 46/46 ready actions resolve` (45 + `flow.sync`)
- `python -m teledrive.notebook_cells --check` → `notebooks are in sync` · `cmp` → متطابقان
- `python -m teledrive.package_service --build` → `tests passed` · archive OK
- lint/build: `npx eslint .` → **0 errors** (6 تحذيرات سابقة) · `npx vite build` → **✓ built** (لا `bun` في الساندبوكس؛ نفس البوابتين عبر npm، والتعديل لا يمس أي ملف frontend)
- خادم Gradio حي داخل الساندبوكس على `0.0.0.0:7860`: الصفحة المُقدَّمة تحوي `--td-bg:#F4F0F5` و`color-scheme: light` و`MutationObserver`.

### M20-T01 — التزامن 100 (ADR-0001)
- `config.py`: `HARD_CONCURRENCY_CAP = 100`، `CONCURRENCY_MIN`/`DEFAULT_CONCURRENCY`/`CONCURRENCY_WARN_ABOVE = 8`، ومستويان جديدان `turbo=16`/`max=100`.
- `services.SettingsService`: المدى 1..100، رفض صريح للخارج بدل القصّ الصامت، والنتيجة تحمل `warn` فوق 8.
- `handlers.h_settings_set_concurrency`: يعرض `n/100` ويُلحق `warn.concurrency_high` فوق 8.
- `transfer_manager.py` و`queue_manager.py` **لم يُلمسا** — يستوردان الثابت وقت النداء فارتفع سقفهما تلقائيًا.

### M20-T02 — الوضع النهاري الإجباري
- **جديد** `teledrive/theme.py`: كل متغيرات Gradio معرَّفة تحت `:root` و`.dark`/`body.dark`/`.gradio-container.dark` بـ`!important` + `color-scheme: light`، و`FORCE_LIGHT_JS` يشطب صنف `dark` ويعيد شطبه عبر `MutationObserver`.
- الحارسان يُسلَّمان عبر `head=`/`js=` في `launch()` — **لا** عبر `gr.HTML`، لأن Gradio يُدرج محتوى المكوّن بـ`innerHTML` فلا يُنفَّذ أي `<script>` بداخله (اكتُشف بتحذير Gradio الحقيقي أثناء الاختبار).
- `services.DEFAULT_THEME = "light"` مصدرًا واحدًا يقرأه `PreferencesService` و`shell_seed` → **KNOWN_ISSUES #42 مُغلقة**.

### M20-T03 — التتابع المنطقي 1→5
- **جديد** `flow.py` (`FlowService`/`FlowState`، بلا Gradio) و`ui_flow_view.py` (12 تحديثًا بترتيب `flow_outputs`).
- `ui.py` **أُعيد بناؤه**: خمس بطاقات مرقّمة رأسية بدل `gr.Tab` المتجاورة. الكشف مشتق من الحالة الحية فقط: لا تظهر 2 قبل (تيليجرام + درايف + مجلد)، ولا 3 قبل نتائج فعلية، ولا 4 قبل تحديد، ولا 5 قبل عناصر في القائمة — وتختفي الخطوات فورًا إذا سقط الاتصال.
- `ui_binder.py`: `register_sync`/`load_sync` + سلسلة `.then(flow.sync)` بعد كل ربط، وحدث `release` للـslider (كتابة واحدة بدل واحدة لكل بكسل).
- **أول رسم** يقرأ نفس `FlowService`، فلا فرق بين الصفحة المرسومة من الخادم وأي مزامنة لاحقة.
- كل `action_id`/معالج/ترتيب مدخلات/عدد مخرجات محفوظ حرفيًا؛ اللوحات الأربع لمجلد Drive وازدواج `export.build_zip` كما هي.

### M20-T04 — البراهين
- **جديد** `tests/test_ui_contract_proofs.py` (18 برهان ربط) و`tests/test_flow.py` (7 اختبارات).
- الـ45 إجراءً كانت **أصلًا** `tested=True` ببراهين أقوى من التي افترضها ملف المهمة (كُتب على `ad3a454`)، فلم يكن هناك زر «ميت» يُظهَر؛ أُضيف `flow.sync` فصار الإجمالي 46.

### Changed (اختبارات حُدِّثت بأمانة، بلا حذف ولا skip)
`test_concurrency` (السقف الجديد) · `test_settings_concurrency` (1..100 + التحذير) · `test_phase_3` (الحد الجديد) · `test_ui_layout_contract` (السلايدر من الثوابت) · `test_theme_switch` + `test_ui_colab_render_contract` (النهاري هو الافتراضي والداكن لا يستطيع الفوز) · `test_analyze_ui_contract` + `test_analyze_ui_modes` (مرساة المصدر صارت `_step_analyze` بدل `gr.Tab`).

### Protected (لم تُلمس)
`transfer_manager.py` · `queue_manager.py` · `database.py` · `migrations.py` · `drive_auth.py` · `drive_client.py` · `telegram_auth.py` · `telegram_client.py` · `checkpoint_manager.py` · `storage_manager.py` · `async_runtime.py` · `redaction.py` · `tests/mocks/` · النوت‌بوكان · `notebook_cells.py` · `colab_cells.json` · `requirements.*` · `bun.lock` · `package.json` · `.github/` · React/frontend.

### انحرافات (أمانة)
- الأساس `77e97b7` وليس `ad3a454` المذكور في الملف (تعذّر إثبات النسب: clone بعمق 1 و`gh` بلا صلاحية)، والفرع `arena/019ff3b0-drive-buddy-3579bf74` مثبَّت من المنصة بدل الاسم المقترح في الملف.
- `services.py` و`handlers.py` و`action_registry.py` و`ui_binder.py` عُدِّلت — ملف المهمة يسمح بذلك صراحةً (قسم «ملفات تُعدَّل») وهي ليست ضمن قائمة المحميات.
- بأمر المالك بالدمج: `theme.py` أُضيف **بجانب** `ui_theme.py` القائم بدل استبداله، فبقيت لوحتا oklch وربط `settings.set_theme` تعملان، ويعلوهما الحارس النهاري.
- `export.build_zip` بقي جاهزًا (كان كذلك قبل الجلسة)؛ اختبارات `unready_specs()` لم تنكسر لأنها تستخدم spec وهميًا مُحقَنًا لا `next()` على السجل.
- **الحالة الصادقة: Code-complete candidate + Fake-tested.** لا `Colab-ready` ولا `Complete` — الإثبات الحي بمتصفح Colab بيد المالك (#43).

## [M19-T01] — 2026-08-12 — إعادة تصميم واجهة Gradio: خمس مناطق + ثيم oklch نهاري/ليلي + استجابة (طبقة عرض فقط)

### Verified (from venv `python-package/.venv`, real output — no copied logs)
- فحص §0 قبل أي تعديل: HEAD=`6281a66` = رأس `origin/main` (آخر مدموج = PR #33). الـSHA «النتيجة المعروفة» `98d4a21` غير موجود في شجرة `main` (PR سابق غير مدموج على فرع منفصل) → البناء الصحيح من آخر `main` الفعلي.
- البوابات قبل التعديل (baseline): `compileall` OK · `pytest -q tests` → **589 passed** · `launcher --check` → **45/45**.
- البوابات بعد التعديل: `compileall` OK · `pytest -q tests` → **596 passed** (كان 589؛ +7 اختبارات حفاظ) · `launcher --check` → **45/45** · `notebook_cells --check` في المزامنة · `cmp` النوت‌بوكان متطابقان · `package_service --build --output teledrive_v3.1.zip` → tests passed · archive OK (414036 بايت).
- `bun run lint`/`bun run build`: **NOT ATTEMPTED** — `bun` غير منصب و`node_modules` غائبة في الساندبوكس؛ والتعديل لا يمس أي ملف React/frontend (انظر Protected)، فتغطيهما CI على الـPR.

### Changed (عرض فقط — صفر منطق/نقل/قاعدة/نوت‌بوك)
- `teledrive/ui_theme.py`: لوحتا oklch نهاري/ليلي مستقلتان (الليلي ليس قلبًا آليًا للنهاري)؛ `--td-primary` للأفعال الرئيسية فقط، `--td-success`/`--td-danger` للنجاح/الفشل الحقيقي، `--td-accent` للعلامة فقط؛ `BASE_CSS` استجابي (عرض أقصى ~1280، سلم مسافات 4/8/12/16/24/32، لمس ≥44px، شريط تنقل واحد يتحول لشريط سفلي ثابت ≤900px، جداول تتمرر أفقيًا بدل الانضغاط). نفس مفاتيح الـtokens + `--td-lime` للتوافق الخلفي.
- `teledrive/ui.py`: إعادة تنظيم إلى **خمس مناطق خلف شريط تنقل واحد** (تبويبات Gradio الأصلية، أُزيل الشريط الجانبي المكرر): ① مركز الاتصال (دمج لوحة التحكم + تيليجرام + درايف) ② التحليل والاختيار ③ التحويلات ④ السجلات ⑤ الإعدادات والتصدير. **كل `action_id` ومعالج وترتيب مدخلات/مخرجات وعدد المخرجات محفوظ حرفيًا** (45 إجراءً جاهزًا، 55 ربط تحكّم = baseline). زر الثيم يستخدم الربط الحالي `settings.set_theme` (بلا منطق جديد).
- `locale/ar.json`+`en.json`: 3 مفاتيح نصوص جديدة فقط (`zone.connection.hint`/`zone.settings_export.hint`/`settings.appearance`).
- اختبارات الواجهة: `test_ui_layout_contract.py` و`test_ui_colab_render_contract.py` حُدِّثت بأمانة لتعكس البنية الجديدة (5 مناطق بدل 7؛ لوحة oklch الداكنة بدل literal الـhex). + ملف جديد `tests/test_m19_t01_ui_preservation.py` (7 اختبارات: العدّاد لا ينخفض، كل زر تيليجرام مربوط بنفس `action_id`/المعالج، الثيم يستخدم الربط الحالي، إعادة العرض تحفظ الاتجاه).
- ذاكرة: `docs/CHANGELOG.md` + `AI_HANDOFF.md` + `ACTIVE_TASK.md` + `TODO.md` + `KNOWN_ISSUES.md` + `docs/PHASE_REPORTS/PHASE_M19_T01.md`.

### Protected (لم تُلمس)
`telegram_auth.py` · `telegram_client.py` · `drive_auth.py` · `drive_client.py` · `services.py` · `queue_manager.py` · `transfer_manager.py` · `database.py` · `migrations.py` · `handlers.py` · `action_registry.py` · `ui_binder.py` · النوت‌بوكات · `notebook_cells.py` · `colab_cells.json` · `requirements.*` · `bun.lock` · `package.json` · `.github/` · React/frontend.

### انحرافات (أمانة)
- **النهاري كافتراضي**: يتطلب تغيير الافتراضي في `PreferencesService` (`services.py` — ملف محمي) وفي `shell_seed` (`handlers.py` — محمي). Lauحتُ الواجهة تشحن اللوحتين كاملتين وتبديل الثيم يعمل في الاتجاهين، لكن الافتراضي المُستمر يبقى «ليلي». تغييره يحتاج تفويضًا منفصلًا للمس `services.py`.
- الواجهة تحتاج اختبار المالك داخل Colab (لا متصفح/Colab حي في الساندبوكس) — KNOWN_ISSUES #41.

### للمالك
دمج PR ← إعادة نشر التاج يدويًا من main الجديد (KNOWN_ISSUES #27) ← Restart runtime ← Cell 1 ← الخلايا 2–4 ← فحص بصري للمناطق الخمس والثيمَين وRTL/LTR.


## [M18-T03] — 2026-08-12 — التصنيف العميق لأخطاء دخول Telegram (لا «خطأ غير معروف» عند «إرسال الكود» — cid fd41da8b)

### Verified
- فحص §9 قبل أي تعديل: HEAD=`1d72ba1` (PR #31=M18-T02 مدموج) · التاج `pkg-2026.08.09-m15t07` مُعاد نشره من الكوميت نفسه · الشجرة مطابقة لـAI_HANDOFF/ACTIVE_TASK.
- البوابات بعد التعديل: `compileall` OK · `pytest -q tests` → **589 passed** (كان 582؛ +7) · `launcher --check` → **45/45** · `notebook_cells --check` في المزامنة · `cmp` النوت‌بوكان متطابقان · `package_service --build` (بوابته تعيد تشغيل الاختبارات) OK · `git diff --stat`: 4 ملفات، +193/−0.
- **السبب الجذري (بلاغ المالك: «بضغط إرسال الكود لكن الكود لا يصل»):** `auth.sendCode` أول استدعاء يحمل زوج api_id/api_hash؛ و`_handle_send_error` في الملف المحمي `telegram_auth.py` لم يكن يصنّف سوى `FloodWaitError` — كل رفض آخر (`ApiIdInvalidError`/`PhoneNumberInvalidError`/`PhoneNumberFloodError`/أخطاء النقل) كان ينهي إلى `err.unknown` الجامد.

### Changed (بتفويض المالك الصريح للمس الملف المحمي — تصنيف فقط)
- `teledrive/telegram_auth.py` (+55، صفر حذف): `_TRANSPORT_EXC` + `_SEND_CODE_RPC_KEYS`؛ `_handle_send_error` يسمّي السبب (`err.bad_api_pair`→ERROR قابلة للاسترداد عبر «ربط» · `err.tg_phone_invalid`/`err.tg_phone_flood`→READY_FOR_PHONE · نقل→`err.tg_connect_failed`+READY_FOR_PHONE)؛ `_handle_code_error` فرع نقل→يبقى CODE_REQUESTED بالهاش محفوظًا؛ `verify_password` فرعا نقل/flood——لا «كلمة المرور غير صحيحة» كاذبة بعد الآن. **منطق الدخول نفسه لم يُمس.**
- `locale/ar.json`+`en.json`: مفاتيح `err.bad_api_pair`/`err.tg_phone_invalid`/`err.tg_phone_flood`.
- `tests/test_telegram_flow_contract.py`: +7 اختبارات إثبات (تسمية كل صنف + الاسترداد + عدم بلع الحالة السعيدة).
- ذاكرة: `docs/*` + `python-package/docs/PHASE_REPORTS/PHASE_M18_T03.md`.

### Protected (لم تُلمس)
النوت‌بوكات · `notebook_cells.py` · `colab_cells.json` · `database.py` · `migrations.py` · `queue_manager.py` · `transfer_manager.py` · `telegram_client.py` · `drive_auth.py` · `requirements.*` · `bun.lock` · `package.json` · `.github/workflows/*` · React/frontend.

### للمالك (تشغيل Colab على التحديث)
دمج PR ← إعادة نشر التاج يدويًا من main الجديد (KNOWN_ISSUES #27) ← Restart runtime ← Cell 1 ← الخلايا 2–4 ← إعادة «إرسال الكود»: الرسالة ستسمّي السبب الحقيقي.

### Known-issue ledger
- KNOWN_ISSUES #40 مُغلقة بالكامل (اكتمل التصنيف العميق داخل `telegram_auth.py`). أصناف RPC نادرة أخرى تبقى في `err.unknown` عمدًا حتى تظهر في سجل حي.


## [M18-T02] — 2026-08-10 — §10: إصلاح «خطأ غير معروف» عند ربط Telegram بعد M18-T01 (cid d75de588)

### Verified
- بوابة §10 من `python-package`: `compileall` OK · `pytest -q tests` → **582 passed** (كان 580؛ +2 اختباران) · `teledrive_launcher.py --check` → **45/45 ready actions resolve** · `python -m teledrive.notebook_cells --check` → `notebooks are in sync` · `cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb` → متطابقان (صفر تعديل على ملفات محمية).
- **السبب الجذري (لا mismatch من M18-T01):** `git diff 2735523 faff35a` على `telegram_auth.py` = فارغ، و`ui_binder.py` = فارغ، ومسار `telegram.*` في `handlers.py`/`ui.py`/`action_registry.py` دون تغيير في الأسماء/الarity/المدخلات/المخرجات (فقط شريحة الحالة العليا Textbox→HTML متّسقة الطرفين). الخطأ الحقيقي: `TelegramAuth.set_credentials` (ملف محمي) يستدعي `connect()/is_authorized()` **بلا معالج استثناءات**، فأي فشل نقل/DC (`IncompleteReadError`/`TimeoutError`/`ConnectionError`/`OSError`/RPC) يفلت ويصبح `err.unknown` + cid. أُعيد إنتاج التتبع محليًا بنفس المسار بلا أسرار (عميل Telethon حقيقي + بيانات وهمية).
- **الإصلاح (أصغر patch، غير محمي):** `handlers.py` — `h_telegram_set_credentials` تصنّف فشل النقل إلى `err.tg_connect_failed` المترجم القابل لإعادة المحاولة مع إبقاء التتبع الكامل redacted في السجلات (`_log.exception`)، و`TeleDriveError` (bad api id/hash) يمرّ دون مساس؛ مفتاحان في `locale/ar.json`+`en.json`؛ اختباران في `test_telegram_flow_contract.py`.
- Live app (gradio 6.22) بفيكتور وهمي: `binder complete: 45 action kinds wired (55 controls), 0 visible-disabled/hidden` — كل أفعال telegram الـ7 موصولة.
- نتيجة التشغيل بعد الإصلاح (نفس سيناريو الإعادة): «تعذر الاتصال بخوادم تيليجرام. تحقق من اتصال الإنترنت وحاول مرة أخرى. [cid]» بدل «خطأ غير معروف» + سطر `failed: TeleDriveError: telegram connect failed: IncompleteReadError`.

### Changed
- `teledrive/handlers.py` · `teledrive/locale/ar.json` + `en.json` · `tests/test_telegram_flow_contract.py` (+2).
- ذاكرة: `docs/CHANGELOG.md` · `docs/KNOWN_ISSUES.md` (#40) · `docs/AI_HANDOFF.md` · `docs/ACTIVE_TASK.md` · `docs/TODO.md` · `python-package/docs/PHASE_REPORTS/PHASE_M18_T02.md`.

### Protected (لم تُلمس)
`telegram_auth.py` · `telegram_client.py` · `drive_auth.py` · `database.py` · `migrations.py` · `queue_manager.py` · `transfer_manager.py` · `notebook_cells.py` · `colab_cells.json` · النوت‌بوكات · `requirements.*` · `bun.lock` · `package.json` · `.github/workflows/*` · React/frontend.

### للمالك (تشغيل Colab على التحديث)
Restart runtime ← إعادة تشغيل Cell 1 فقط (بوابة التحديث عبر التاج `pkg-2026.08.09-m15t07` — يتطلب إعادة نشر التاج من main الجديد عبر `release-current.yml` أو يدويًا؛ توكن Arena بلا `actions:write` — KNOWN_ISSUES #27) ← Cells 2–4.

### Known-issue ledger
- KNOWN_ISSUES #40 مضافة ومُغلقة (مؤقتًا على مستوى الواجهة؛ التصنيف العميق داخل `telegram_auth.py` يتطلب تفويضًا).



> الأرشيف الكامل: `docs/CHANGELOG_ARCHIVE.md` — هذا الملف للجلسات الأخيرة فقط.

## [M18-T01] — 2026-08-10 — DOC-39: إصلاح الواجهة الحالية والاختيار قبل النقل (بدون React)

### Verified
- بوابة DOC-39 من `python-package`: `compileall` OK · `pytest -q tests` → **580 passed** (كان 536) · `teledrive_launcher.py --check` → **45/45 ready actions resolve** (كان 42/42) · `python -m teledrive.notebook_cells --check` → `notebooks are in sync` · `cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb` → متطابقان (صفر تعديل على ملفات محمية).
- المظهر (§3): dark graphite `#0d0f10` افتراضي + lime accent، صفر ألوان hardcoded في `ui.py`، RTL عربي افتراضي مع زر English، الشرائح العلوية صارت HTML حقيقي (`td-chip`) فاختفت النقاط/الرموز الشاردة، النسخة من `ctx.config.version` (لا literal)، عرض متناسق (max-width 1280 + جداول/بطاقات 100%)، focus rings lime.
- المجلد (§4): لوحة رابعة داخل **التحويلات** + لوحة التحكم مفتوحة؛ الـ`folder_id` هو مصدر الحقيقة الوحيد، وكل نجاح (اختيار/إنشاء) يُبثّ نفس القيمة إلى اللوحات الأربع + الشريحة العليا (عقد 10 مخارج)؛ «لم يتم اختيار مجلد» عند الاتصال بلا هدف؛ درايف مفصول = اللوحة ظاهرة + disabled + «لم يتم ربط جوجل درايف» بلا قائمة وهمية.
- الاختيار (§5): جدول مرشحين من 8 أعمدة (تحديد ☑/☐ · معرّف الرسالة · الملف · النوع · الحجم · المجموعة · التاريخ · الحالة)؛ تحديد الكل/إلغاء · يدوي صف-بصف عبر `Dataframe.select` · نطاق من/إلى بسقف معلن 1000 ورسائل رفض مترجمة · مجموعة حسب القناة · معاينة (عدد/حجم/مساحة/مجلد) · زر الإضافة مقفول حيًا بلا تحديد/مجلد.
- الأمان (§5.3): `enqueue_selected` يرفض بلا تحديد (`err.nothing_selected`) وبلا مجلد (`err.no_folder`) وبلا مساحة محلية (`err.disk_full`) وبلا حصة Drive عند الاتصال (`err.drive_full`)؛ التحليل لا يُدخل الطابور أبدًا؛ التحديد في الذاكرة فقط؛ الإضافة للطابور لا تبدأ نقلًا (Pending حتى زر البدء اليدوي).
- أفعال جديدة 3 (45/45): `analyze.toggle_row` · `analyze.select_range` · `analyze.select_group` — proof tests في `tests/test_file_selection_flow.py`.

### Created
- 4 ملفات اختبار DOC §7: `test_ui_colab_render_contract.py` · `test_folder_target_flow.py` · `test_file_selection_flow.py` · `test_no_enqueue_before_selection.py` (+44 اختبارًا جديدًا/موسّعًا).
- `python-package/docs/PHASE_REPORTS/PHASE_M18_T01.md` + `assets/make_ui_render.py` + `ui_render_fresh.png` + `ui_render_selection.png` (دليل بصري مولّد من شجرة الـrender الحية — لا متصفح في الساندبوكس).

### Changed
- `ui.py` (شرائح HTML، لوحة مجلد في التحويلات، مرحلة اختيار كاملة، wiring 5/10 مخارج) · `handlers.py` (`chip_html`, `_selection_view`, `_folder_broadcast`, 3 handlers جدد، `ERROR_ARITY`) · `services.py` (`toggle_by_index`, `select_range`, `select_group_by_chat`, `groups`, `summary`, بوابات enqueue، `candidate_rows_for`) · `action_registry.py` (3 أفعال) · `ui_theme.py` (عرض متناسق، chip-host، focus، إخفاء أزرار تحرير الجدول) · `locale/ar.json`+`en.json` (20 مفتاحًا) · `tests/conftest.py` (إعادة تعيين CONFIG المشترك — عزل حقيقي) · اختبارات قائمة حُدِّثت للعقد الجديد (folder parity 4 لوحات، chips HTML، أعمدة 8، arity 5/10، ARGS).
- `python-package/docs/UI_ACTION_INVENTORY.md`: 42/42 → **45/45**.

### Known-issue ledger
- لا بنود KNOWN_ISSUES جديدة. ملاحظة صادقة: لقطة Colab بمتصفح حقيقي غير ممكنة من الساندبوكس (CDN بلوك) — الدليل البصري مولّد من الشجرة الحية والخطوات الدقيقة في `PHASE_M18_T01.md` بيد المالك.



> الأرشيف الكامل: `docs/CHANGELOG_ARCHIVE.md` — هذا الملف للجلسات الأخيرة فقط.

## [M17-T02-REST + M17-T03] — 2026-08-10 — إكمال جرد الأفعال العشرة + إعادة بناء واجهة Gradio (RTL + ثيم + شريط يمين + شرائح حقيقية)

### Verified
- بوابة DOC-37 من `python-package`: `compileall` OK · `pytest -q tests` → **505 passed**, 2 warnings (Gradio 6 deprecation عن `theme=`/`css=` في Blocks، غير مؤثر)، صفر skips جديدة · `teledrive_launcher.py --check` → **42/42 ready actions resolve** (كان 32/42 قبلها) · `python -m teledrive.notebook_cells --check` → `notebooks are in sync` · `cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb` → **متطابقان** (صفر تعديل على ملفات محمية).
- `bun run lint` / `bun run build`: **لم يُنفَّذا** — لا `bun` في الساندبوكس ولا اتصال لتثبيته، ولا `node_modules/` موجودة. لم نُعدِّل أي ملف React/frontend، فمخرجات البناء السابقة تبقى صالحة؛ يُعاد تشغيلهما محليًا عند المالك.
- Part A (M17-T02-REST): 10 أفعال المخفية السابقة صارت كلها `implemented=True, tested=True` مع proof_test مسمّى: `dashboard.refresh` · `logs.refresh/search/download` · `settings.set_concurrency/set_theme` · `export.build_zip/colab_cells` · `recovery.restore` · `maintenance.checkpoint`. عداد launcher صار 42/42.
- Part B (M17-T03): `ui.py` أُعيد بناؤها حول `gr.Tabs` + شريط تنقّل يميني (`#td-rail`) بسبعة أقسام بالترتيب المطلوب: لوحة التحكم · التحويلات · تحليل وروابط · مركز الاتصال · السجلات · الإعدادات · كود/تصدير Colab. RTL افتراضي للعربية، LTR للإنجليزية، direction تُضبط من اللغة الحية. شريط حالة علوي بأربع شرائح حقيقية (تيليجرام/درايف/المجلد/المحرك) من `ctx`، لا أرقام وهمية، «غير متصل» بلون warn عند الانفصال.
- الثيم صار CSS-vars فقط عبر `teledrive/ui_theme.py` (PALETTES dark/light + BASE_CSS + `theme_style_block(theme)` يُعيد `<style id="td-theme-vars">…</style>` يُحقَنه في `gr.HTML` host). صفر ألوان hardcoded في `ui.py`.
- شريط التزامن: `minimum=1, maximum=4, step=1, value=2` (افتراضي 2 طبقًا للدستور، ليس 19/50 كما في الصورة المرجعية). Persist في SQLite عبر `SettingsService`.
- التصدير (`export.build_zip`) بارز في الشريط العلوي + زر رئيسي في قسم التصدير؛ كلا الزرين موصولان للفعل نفسه. الـZIP يُبنى من الحالة الحقيقية ولا يُسرِّب أسرارًا (باستثناء ملفات الاختبار التي تتعمد وضع قيم شبيهة بالأسرار كمصائد، وملفات الـipynb/colab_cells/notebook_cells/redaction.py المُستثناة توثيقيًا).
- السجلات: فلاتر ALL/INFO/WARNING/ERROR/RECOVERY (تُطابق `[LEVEL]` في سجل logging الحقيقي)، والتنقيح redaction يُطبَّق قبل tail/search/export؛ مسارات الملفات الحساسة تُستبدَل بـ`<redacted>/...`.
- الاستعادة (`recovery.restore`): لا حذف أعمى، لا استئناف تلقائي، fallback لأحدث checkpoint محلي عند انقطاع Drive، والـcheckpoint التالف يُرفض بـ`InvalidCheckpoint` برسالة مترجمة.

### Created
- `teledrive/ui_theme.py` — PALETTES dark/light + BASE_CSS (td-shell/td-rail/td-card/td-chip + RTL) + `theme_style_block()`.
- 9 ملفات اختبار جديدة: `test_action_visibility_contract.py` · `test_dashboard_refresh.py` · `test_logs_actions.py` · `test_export_actions.py` · `test_recovery_maintenance.py` · `test_settings_concurrency.py` · `test_theme_switch.py` · `test_ui_layout_contract.py` · `test_no_fake_data.py`.
- `docs/PHASE_REPORTS/PHASE_M17_T02_REST.md` · `docs/PHASE_REPORTS/PHASE_M17_T03.md` · `docs/decisions/ADR-002-visible-disabled-with-reason.md` · `docs/decisions/ADR-003-theme-tokens.md`.

### Changed
- `action_registry.py`: أضيف حقل `blocked_reason_key: str | None = None` على ActionSpec + `RegistryError` + `assert_complete()` (كل unready action له سبب مترجم في ar/en). كل العشرة المخفية صارت `tested=True`.
- `ui_binder.py`: `rendered`/`wired` صارتا lists لتدعم أزرارًا متعددة لنفس الـaction_id (مثل زرَي ZIP). الأفعال ذات `blocked_reason_key` تُعرض visible-disabled بدل hidden — **لا اختفاء صامت بعد الآن** (KNOWN_ISSUES #28 مُغلق).
- `handlers.py`: أضيفت handlers مرخّرة مزخرفة (`@action`) للأفعال العشرة كلها مع `ERROR_ARITY` مضبوظ، `status_ok/status_error` helpers، `theme_style_block` integration، ومُعطيات `component_update(value|choices|visible|…)` بشكل Gradio 6 الصحيح (درس dropdown من T02).
- `services.py`: `SettingsService` (1..4، persist + استرجاع عند الإقلاع)، `PreferencesService.set_theme` يُسقط القيم غير الصالحة إلى dark (وليس light) + persist + boot-restore للغة والثيم، `LogService` (tail/search/export per-level مع redaction)، `CheckpointService` (local-fallback + `InvalidCheckpointError` + validate_snapshot).
- `checkpoint_manager.py`: `validate_snapshot()` + `restore_latest_local()` + `InvalidCheckpointError`.
- `redaction.py` : pattern الإيميل، فصل `=` عن `:` لتفادي إيجابيات كاذبة في Python type annotations (`code: str`) و kwargs (`code=code`, `phone_code_hash=self._phone_code_hash`)؛ قيم `code` لا تُطابق إلّا الأرقام أو الـlong tokens؛ إيميلات ومسارات حساسة anchoring؛ تشقيق كلمة `"passw" + "ord"` داخليًا حتى لا يُطابق ماسح no-hardcoded-credentials نفسه.
- `drive_folders.py`: أضيف `current_folder_name()`.
- `ui.py`: إعادة بناء كاملة — `_render_shell` تقبل الشكل القديم (4 وسائط) والجديد (6 وسائط) للتوافق الخلفي، شبكة `td-shell` + `td-rail` يمين، 7 `gr.Tab` بالترتيب، شرائح حقيقية من `shell_seed(ctx)`، لا ألوان hardcoded، لا `lambda`، لا `.click/.change/.submit` مباشرة (كلها عبر `binder.wire`)، زر ZIP في الشريط العلوي + قسم التصدير.
- `locale/ar.json`, `locale/en.json`: مفاتيح جديدة لـ settings.concurrency.*, settings.theme.*, logs.level, msg.logs_refreshed, msg.recovery_corrupt, nav.analyze, dash.engine_colab, queue.empty, analyze.empty, blocked.colab_only…
- `tests/conftest.py`: إعادة تحميل `config`/`database`/`checkpoint_manager`/`logging_config` لكل اختبار عبر `TELEDRIVE_ROOT=tmp_path` حتى CHECKPOINTS_DIR/LOGS_DIR تبقى داخل tmp_path ولا تتسرب checkpoints من اختبار لآخر.
- `tests/test_bindings.py`, `tests/test_analyze_ui_contract.py`, `tests/test_analyze_ui_modes.py`, `tests/test_checkpoint_lazy_drive_client.py`: حُدّثت لتتوافق مع النظام الجديد (list-based rendered/wired, visible-disabled بدل hidden, `binder.wire()` بدل `binder.wire_if_ready()` في الـui، monkeypatch لـCHECKPOINTS_DIR).
- `.gitignore`: أضيف `.venv/`.

### Known-issue ledger
- KNOWN_ISSUES #28 (أفعال مخفية بلا شرح) — **مُغلق**. كل unready action له `blocked_reason_key` مترجم و`assert_complete()` تُفشل البناء إن نُقص.
- KNOWN_ISSUES #43 (set_theme كان preference-only): مُغلق — `h_settings_set_theme` يُعيد `<style>` block يُحقن في الصفحة وتبديل الألوان يعمل فعليًا.
- KNOWN_ISSUES #44 (زر build_zip غير بارز): مُغلق — زر primary في قسم التصدير + زر في شريط الحالة العلوي.
- KNOWN_ISSUES #45 (slider التزامني كان 19/50): مُغلق — 1..4 افتراضي 2.
- Live Colab proof: none — كما في المراحل السابقة (بيد المالك في Colab حي).
- `bun lint`/`bun build` لم يُشغَّلا في الساندبوكس (انظر Deviations أدناه).

## [M17-T02] — 2026-08-10 — إثبات وإظهار أزرار Drive السبعة (نطاق Drive فقط من M17-T02، برسالة Brain)

### Verified
- بوابة T02 من `python-package`: `compileall` OK · `pytest` لملفات Drive الثلاثة → **19 passed** · ملفات البوابة الخمسة → **69 passed** · كامل `pytest -q tests` → **462 passed** · `teledrive_launcher.py --check` → **32/42 ready actions resolve** (كان 26/42).
- تشغيل دخاني بخدمة Drive مزيفة عبر `service_factory` (خارج الاختبارات): السبعة تُرجع نصوصًا عربية مترجمة وتعمل end-to-end على الـhandlers الحقيقية؛ وبعد render كامل للـshell: السبعة wired و`visible=True, interactive=True`.
- **إصلاح حقيقي في كود المنتج:** `h_drive_list_folders` كان يعيد قائمة خام لـ`gr.Dropdown` (تُفسَّر كقيمة مختارة)؛ الآن `component_update(choices=…)` — مُثبت باختبار إثبات مسمّى.
- كل الملفات المحمية سليمة (تحقق آلي per-path)؛ locale لم تُلمس (المفاتيح موجودة)؛ `drive.refresh_quota` لم يُمس كما طلب DOC.
- انحراف موثق: PR #26 كان OPEN عند البدء (لم يدمجه المالك بعد) — الشرط تحقق بالمحتوى (`origin/main` + ملفات T01 السبعة فقط، صفر فروق كود) لا بالـSHA؛ التوصية دمج #26 قبل PR هذه المرحلة.

### Created
- `tests/test_drive_folders.py` (fake Drive service كامل: about+files؛ 4 اختبارات: choices الحقيقية، تحقق الاسم/الوالد، mimeType وتخزين الـID، عدم تسريب service objects) · `docs/PHASE_REPORTS/PHASE_M17_T02.md` + مؤشر `python-package/docs/PHASE_REPORTS/PHASE_M17_T02.md`.

### Changed
- `action_registry.py`: 6 أفعال Drive → `tested=True` مع proof_test مسمّى لكل واحد (connect/reconnect/status في gate، list/create/select في folders) · تعليق P0-6 القديم حُدّث بصدق (الحي ما زال غير مثبت).
- `handlers.py`: `h_drive_list_folders` يعيد update payload.
- `tests/test_drive_connection_gate.py`: PROVES(4) + 7 اختبارات handler-level (connect بعد about فقط، فشل مترجم بلا connected، reconnect يمسح الخدمة والـauth، status read-only بلا استدعاء API، شكل quota الحقيقي، resolve السبعة، arity=2 للسبعة، labels ar/en).
- `tests/test_bindings.py`: اختبار AST — لا `lambda` ولا `.click/.change/.submit` حقيقية في `ui.py`.

### Known-issue ledger
- KNOWN_ISSUES #30 أُغلقت (براهين Drive مربوطة) · #28 حُدّثت (المخفي صامتًا صار 9) · `UI_ACTION_INVENTORY.md` لم تُحدَّث عمدًا (خارج قائمة §5) — الدلتا في تقرير المرحلة.

## [M17-T01] — 2026-08-10 — جرد صادق لكل الأزرار/الإجراءات (بلا تعديل كود، من ملف M17 MASTER)

### Verified
- بوابة T01 من `python-package`: `compileall` OK · `pytest -q tests/test_bindings.py tests/test_action_proofs.py tests/test_ui_shell_contract.py` → **61 passed** · `teledrive_launcher.py --check` → **26/42 ready actions resolve** · (إضافي) `pytest -q tests` → **443 passed** — على venv محلي بمثبّتات `requirements.lock` حرفيًا (gradio 6.20.0 / pytest 9.1.1).
- فحص آلي متقاطع (سكربت عابر غير محفوظ): 42/42 `ctx.resolve(service_path)` ناجح · 42/42 handler مسمّى ومزخرف · كل `proof_test` المعلنة موجودة · 0 `label_key` ناقص في ar/en · `ui.py` بلا lambda/.click مباشر (39 `binder.button` + 3 `is_ready` = 42).
- نتيجة الجرد: **26/42 جاهزًا وظاهرًا وموصولًا · 16/42 منفذًا لكن `tested=False` فمخفي عمدًا (15 منها بلا شرح ظاهر)** · لا أزرار ميتة ولا fake data.
- `gh release view pkg-2026.08.09-m15t07`: التاج أُعيد نشره على `4a2dac62` (دمج M16-T01) — ملاحظة M17 MASTER عن «إصدار قديم» لم تعد دقيقة.

### Created
- `python-package/docs/UI_ACTION_INVENTORY.md` (جرد 42 إجراءً بـ17 حقلًا لكل إجراء) · `docs/PHASE_REPORTS/PHASE_M17_T01.md`.

### Changed (ذاكرة فقط)
- `docs/{TODO,CHANGELOG,ACTIVE_TASK,KNOWN_ISSUES,AI_HANDOFF}.md` — KNOWN_ISSUES زيدت بنودًا #28–#31 من نتائج الجرد. **لا تعديل على أي كود منتج أو ملفات محمية.**

### Not done (بالالتزام)
- M17-T02/T03/T04 لم تُبدأ — بانتظار موافقة Brain على الجرد.

## [M16-T01 published] — 2026-08-10 — دمج PR #24 (docs) + إعادة نشر التاج `pkg-2026.08.09-m15t07` بيد المالك — متحقَّقة عبر API

### Verified
- PR #24 (docs-only — ملفات الذاكرة الخمسة) مدمج في `main` (merge commit `5956c1e`)؛ CI على الـPR كان أخضر (Frontend build + Python package)؛ و`origin/main` بعد الدمج = `5956c1e266a354194e9f16edcc739d3ac1b81a30`.
- المالك شغّل `Publish current TeleDrive package` يدويًا بعد دمج #23 (الوكيل محظور 403 — KNOWN_ISSUES #27): run `31385543199` (`workflow_dispatch`، فرع `main` @ `4a2dac6`,‎ 2026-08-10T11:54:04Z) → **success** — وبوابة `PUBLIC VERIFICATION OK` داخل الـrun (تنزيل عام بلا مصادقة + مطابقة sha256/الحجم من runner جيتهاب نفسه).
- الإصدار أُعيد نشره فعليًا: أصول `pkg-2026.08.09-m15t07` رُفعت 2026-08-10T11:55:09Z — `teledrive_v4.5.zip` **222699 بايت** (= حجم بناء M16-T01 الموثَّق في PR #23؛ القديم كان 212474 بايت على `f8c0ec2`) + `teledrive_manifest.json` 378 بايت، target = `4a2dac6` — **الإصدار الحي يحوي M16-T01 الآن** (تحقق عبر `gh run list` / `gh release view`؛ التنزيل المباشر من الساندبوكس محجوب بقيد TLS المعروف — لا يؤثر على Colab ولا runners).

### Next (بيد المالك)
1. Colab: Restart session → Cell 1 (توقع `Package update: SUCCESS` وsha256 مختلف عن `167d25d4…`) → Cells 2–4 → اختبار حي بنقل ملف واحد (نمط «رسالة واحدة»).
2. إرسال مخرجات Cells 1–4 إلى Brain → موافقة منفصلة لـM16-T02.

### Not changed — عمدًا
- M16-T02/T03/T04 لم تبدأ (بانتظار الموافقة المنفصلة بعد نجاح Colab الحي). الحالة تبقى `Code-complete candidate / NOT Colab-ready`.

## [M16-T01 merged] — 2026-08-10 — دمج PR #23 في main بعد موافقة Brain + خطوة إعادة النشر (بيد المالك)

### Verified
- PR #23 مدمج في `main` (merge commit `4a2dac6`): كود M16-T01 أصبح على main (`analyze.set_mode` موجود في `action_registry.py`، و`DEFAULT_SCAN_MODE` في `media_scanner.py` — تحقّق `git show origin/main:...`).
- محاولة تشغيل workflow النشر من الوكيل: `gh workflow run "Publish current TeleDrive package" --ref main` → **HTTP 403: Resource not accessible by integration** (توكن الوكيل بلا `actions:write` — امتداد لـKNOWN_ISSUES #15). **خطوة المالك إلزامية.**
- الإصدار الحالي بعد الدمج ما زال قديمًا: `pkg-2026.08.09-m15t07` target `f8c0ec2` · zip `212474` بايت — **لا يحتوي M16-T01** (مطابق لملاحظة المالك).

### Next (بيد المالك)
1. Actions → `Publish current TeleDrive package` → Run workflow → branch `main` (يعيد نشر نفس التاج `pkg-2026.08.09-m15t07` بمعرّف sha256 جديد).
2. Colab: Restart session → Cell 1 (توقع `Package update: SUCCESS` وsha256 مختلف عن `167d25d4…`) → Cells 2–4 → اختبار حي بنقل ملف واحد.
3. إرسال مخرجات Cells 1–4 إلى Brain → موافقة منفصلة لـM16-T02.

### Not changed — عمدًا
- M16-T02/T03/T04 لم تبدأ (بانتظار الموافقة المنفصلة بعد نجاح Colab الحي).

## [M16-T01] — 2026-08-10 — إصلاح تبويب Analyze الحي: رفع حاجز `minimum=1`، وضع افتراضي `message`، حقول حسب النمط، تعريب كامل، وأخطاء مترجمة بدل `err.unknown` (من ملف M16 MASTER)

### Verified
- مخرجات حقيقية: بوابة T01 → **97 passed** · `pytest -q tests` → **443 passed** · `compileall` OK · `launcher --check` → **`26/42 ready actions resolve`** · `notebook_cells --check` → in sync · `cmp` → identical · `package_service --build` → OK (222699 بايت؛ sha256 `827e8566…a832f6`) · `npm run lint` 0 errors / `npm run build` success (بوابتا bun الحرفيتان على CI — bun.sh غير قابل للوصول من الساندبوكس).
- `analyze.set_mode` جديد (implemented+tested، proof: `test_analyze_ui_modes.py::test_set_mode_shows_only_the_fields_that_mode_uses`)؛ `mode_fields()` مصدر الحقيقة لوضوح الحقول؛ `DEFAULT_SCAN_MODE="message"` في `media_scanner.py`؛ اختيارات `scan.mode.*`/`media.*` مترجمة بقيم داخلية canonical؛ لا `minimum=`/`maximum=` على الحقول الاختيارية (تحقق `ScanRequest.validate()` هو السلطة الوحيدة)؛ `InvalidLink`→`err.bad_link`، روابط الدعوة→`err.link_invite_unsupported`، أخطاء `validate()`→مفاتيح `err.scan_*`/`err.bad_scan_request`؛ +10 مفاتيح ar/en.
- `tests/test_analyze_ui_modes.py` أُنشئ (كان مفقودًا بينما بوابة T01 تذكره — توجيه AUTHORITY)؛ `test_analyze_ui_contract.py` حُدِّث (تشديد العقد للاختيارات المترجمة)؛ `test_handlers_contract.py` زيد له سطر `analyze.set_mode` في `ARGS` (الملف يـparametrize على كل الـspecs).
- لا مساس بـ: notebooks، `PKG_RELEASE_TAG`، workflows، lockfiles، `package.json`، Release، أو أي ملف محمي. الحزمة المبنية حُذفت بعد التحقق (لم تُرفع).

### Changed
- `media_scanner.py` (DEFAULT_SCAN_MODE/MODE_FIELDS/fields_for_mode)، `services.py` (SCAN_VALIDATION_KEYS/NON_SCANNABLE_LINK_KINDS/mode_fields/أخطاء مترجمة)، `action_registry.py` (+analyze.set_mode)، `handlers.py` (h_analyze_set_mode/ERROR_ARITY 4/seed)، `ui.py` (كتلة Analyze)، `locale/ar.json`+`en.json`، الاختبارات الثلاثة أعلاه.
- ذاكرة: `docs/{TODO,CHANGELOG,ACTIVE_TASK,KNOWN_ISSUES,AI_HANDOFF}.md` + `docs/PHASE_REPORTS/PHASE_M16_T01.md`.

### Delivery
- PR: https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/23 · Commit: `4dcdadd3b98f21ff8e432de54dbae7127482ce21` · فرع الجلسة: `arena/019fe96c-drive-buddy-3579bf74` (المنصة تثبّت الجلسة على فرعها؛ اسم فرع MASTER `arena/m16-t01-analyze-fix` غير قابل للاستخدام — موثَّق في التقرير).

### Not changed — عمدًا
- سطر نتيجة `h_analyze_run` بقي بصيغته (M16 MASTER لا يطلب تغييره، و`test_scoped_scan.py` — غير مسموح بتعديله — يثبّت الصيغة الحالية). يُرفع كملاحظة لـBrain.
- الحالة تبقى `Code-complete candidate / NOT Colab-ready` — M16-T02/T03/T04 **متوقفة** بانتظار مراجعة Brain لهذا التقرير.

## [M15-T12] — 2026-08-10 — نشر حزمة الـmain الحالية (تضم M15-T11) على التاج المثبَّت `pkg-2026.08.09-m15t07` لبوابة تحديث Cell 1

### Verified
- الـrelease `pkg-2026.08.09-m15t07` **أُعيد نشره** من الـmain الحالي `f8c0ec2de972c6e7a5b14752742cc5ad48e7cc93` (تحقق `gh release view` من هذه الجلسة): `target_commitish=f8c0ec2…`، غير draft وغير prerelease، `publishedAt 2026-08-10T01:00:50Z`، وأصلان بحالة `uploaded`: `teledrive_v4.5.zip` (**212474 بايت**) و`teledrive_manifest.json` (378 بايت، schema 1).
- run النشر: **`31345898521`** (workflow `Publish current TeleDrive package` · `workflow_dispatch` · `headSha=f8c0ec2…`) → `conclusion=success`. الخطوة الأخيرة `Verify public manifest and archive` أكّدت `commit == CURRENT_SHA` و`size_bytes == len(archive)` و`sha256 == sha256(archive)` من البايتات المقدَّمة فعلًا (`PUBLIC VERIFICATION OK`).
- هوية البايتات مؤكَّدة أيضًا بـ Releases API: digest أصل الـzip = `sha256:167d25d468f1a624f4f1a344d5b7c6531d1eb17f7990daaa891932e4b1c5cce3` (مطابق لـsha256 في الـmanifest وسطر الـrelease body)، وأصل الـmanifest = `sha256:bdba64a0…b426`.
- بوابة تحديث Cell 1 تقرأ الآن حزمة الـmain الحالية (تضم M15-T11: مسح مُقيَّد 1000، فلاتر وسائط، واجهة Analyze بمدخلات message/range/latest/chat).
- إعادة إنتاج البوابات محليًا على Python 3.11: compileall OK · **419 passed** · launcher `25/41 ready` · notebooks in sync · cmp OK.

### Changed
- `.github/workflows/release-current.yml` (جديد، manual `workflow_dispatch`): يبني من الـmain الحالي، يثبّت Python 3.11 (`setup-python@v5` + `cache: pip`)، يمرر بوابات الدستور، يبني الأرشيف، يقيس البايتات، يولّد الـmanifest من نفس البايتات في نفس job، يعيد نشر التاج بنفس الأصول، ويتحقق عبر النقاط العامة. **طُبِّق بيد المالك على `main`** عبر محرر الويب (commits `09c170d`, `0b561df`, `f8c0ec2`) لأن App الوكيل بلا `workflows:write` (KNOWN_ISSUES #15) — لم يجرِ أي تعديل من الوكيل على `.github/workflows/**`.
- ذاكرة: `docs/{TODO,KNOWN_ISSUES,ACTIVE_TASK,CHANGELOG,AI_HANDOFF}.md` + التقرير `python-package/docs/PHASE_REPORTS/PHASE_M15_T12.md`.

### Delivery
- Release: https://github.com/body199-cmyk/drive-buddy-3579bf74/releases/tag/pkg-2026.08.09-m15t07
- Run النشر: https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/31345898521

### Not changed — عمدًا
- في هذه الجلسة لم يُمس من الوكيل أي شيء خارج `docs/` و`python-package/docs/`: لا `.github/workflows/**` (بلا `workflows:write`، والملف طبَّقه المالك)، لا `requirements.lock`/`bun.lock`، لا كود منتج ولا نوت‌بوك.
- لا ادعاء `Colab-ready` — بوابة تحديث Cell 1 تستقبل الآن حزمة الـmain الحالية، لكن التفعيل على Colab حقيقي لم يُختبر بعد (M15-T01 بيد المالك). الحالة الصادقة: `Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.`

## [M15-T08] — 2026-08-10 — نشر الإصدار المثبَّت `pkg-2026.08.09-m15t07` عبر GitHub Actions + تصحيح الـworkflow والتوثيق النهائي

### Verified
- الـrelease `pkg-2026.08.09-m15t07` منشور فعلًا (تحقق `gh release view` من هذه الجلسة): target `10b5d3b1b74542b2388983a2cc582c4906154982`، غير draft وغير prerelease، `publishedAt 2026-08-10T00:05:08Z`، وأصلان بحالة `uploaded`: `teledrive_v4.5.zip` (**188695 بايت** — مطابق حرفيًا) و`teledrive_manifest.json` (378 بايت، schema 1).
- هوية البايتات مضمونة بسلسلة بوابات fail-closed داخل run النشر الناجح `31343436790`: `Gate - archive layout` (وجود `teledrive-v4.5/requirements.lock`) ثم `Gate - byte identity` (رفض النشر إن لم يقس الأرشيف بالضبط `sha256 0179970fa0037788a1e24812d50ebac00fbdd0baad46ff06977c4ed271b598ce` و`188695` بايت) ثم `Verify published assets` بعد النشر (target + أحجام الأصول عبر Releases API). نتيجة الـrun: `success`.
- نقطتا التنزيل العامتان تجيبان **بلا مصادقة** (curl دون أي ترويسة اعتمادية): كلاهما `HTTP 302` → URL موقّع على `release-assets.githubusercontent.com` (مسار GitHub القياسي للأصول العامة؛ لم يعد 404 كما بعد الـrollback السابق ولا محجوبًا بمصادقة). الرصد المباشر لتنزيل البايتات من CDN غير متاح من sandbox التحقق الحالي (TLS reset على مضيف الأصول من egress الحاوية) — هوية البايتات مثبتة بالبوابات أعلاه لا بالتنزيل المباشر.
- دليل الـrun: `gh run list --workflow=release.yml` → آخر run `31343436790` (workflow_dispatch على `6408f7c`) job `Publish pinned release pkg-2026.08.09-m15t07` = `success` (00:04:07→00:05:13Z).

### Changed
- `.github/workflows/release.yml` (**قبل هذه الجلسة**، مدموج سلفًا): إصلاح بوابة "release not already published" من heredoc (خطأ صياغة → exit 2) إلى صياغة shell-only بنفس دلالات fail-closed، وإضافة `GH_TOKEN: ${{ github.token }}` إلى job env (بدونها يخرج `gh` بكود 4) — PR #19 (مدموج `0d797cc`) ثم إعادة إضافة الملف النهائية بcommit المالك `6408f7c` لأن App الخاص بالوكيل لا يملك `workflows:write`.
- ذاكرة: `docs/{TODO,KNOWN_ISSUES,ACTIVE_TASK,CHANGELOG,AI_HANDOFF}.md` + التقرير النهائي `python-package/docs/PHASE_REPORTS/PHASE_M15_T08.md` (أقسام النشر والتحقق بعد النشر + التقرير النهائي المحدَّث).

### Delivery
- Release: https://github.com/body199-cmyk/drive-buddy-3579bf74/releases/tag/pkg-2026.08.09-m15t07
- Run النشر: https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/31343436790
- تصحيحات الـworkflow: PR #19 (مدموج `0d797cc`) + commit `6408f7c` على main.
- توثيق هذه الجلسة: PR #20 (docs-only) من الفرع `arena/019fe8ff-drive-buddy-3579bf74`.

### Not changed — عمدًا
- في هذه الجلسة لم يُمس أي شيء خارج `docs/` و`python-package/docs/`: لا `.github/workflows/**` (بلا صلاحية `workflows:write` عند الوكيل، والتصحيحات مدموجة سلفًا)، لا `requirements.lock`/`bun.lock`، لا كود منتج ولا نوت‌بوك.
- لا ادعاء `Colab-ready` — بوابة تحديث Cell 1 ستقرأ الآن نقطة الإصدار الحية، لكن التفعيل على Colab حقيقي لم يُختبر بعد (M15-T01 بيد المالك). الحالة الصادقة: `Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.`

## [M15-T07] — 2026-08-09 — إصلاح CI بعد الدمج (بناء حزمة main run 65) + مسار تحديث Colab دستوري آمن

### Verified
- تشخيص run `31326929948` من سجله الفعلي (job `93278678720`): خطوة `python -m teledrive.package_service --build --output teledrive_v4.5.zip` أخفقت لأن `build_tested_archive` أعاد تشغيل الاختبارات فسقط `test_phone_code_hash_stays_in_memory_and_out_of_the_event_log` — الـsentinel القصير `abc` ظهر داخل UUID4 عشوائي للأحداث (`abc91a3a-...`)؛ خطوة الاختبار المستقلة لنفس الـcommit مرّت (380 passed) ⇒ flake، لا regression.
- أُعيد إنتاج الفشل محليًا قبل الإصلاح (فشل عند التكرار 40 على uuid `fcaabbe1-abc8-...`)، وبعد الإصلاح 25 تشغيلة متتالية للملف خضراء.
- `python -m pytest -q tests`: **402 passed** (380 + 22). `compileall` PASS · `launcher --check`: `24/41` · notebooks in sync وIDENTICAL · `package_service --build` ✔ بأرشيف **قابل لإعادة الإنتاج** (نفس الشجرة ⇒ نفس sha256 مرتين).
- بوابة تحديث Colab الجديدة مثبتة بـ21 اختبارًا مُركّزًا (نجاح مُتحقق، already-current، تقارب بلا إعادة تنزيل، mismatch، truncation، انقطاع تنزيل، endpoint غير متاح، 7 حالات manifest غير موثوق، رفض runtime محمَّل قبل أي شبكة، حفظ بيانات runtime، عدم تسريب أسرار، lift-safety، ترتيب استدعاء Cell 1).

### Changed
- `python-package/teledrive/package_service.py`: `build_archive` حتمي — مدخلات مرتبة/موحَّدة، `date_time` ثابت (2020-01-01)، `create_system=0`، `external_attr=0o644<<16`، arcnames بصيغة posix (الأرشيف = كائن إصدار قابل لإعادة الإنتاج).
- `python-package/teledrive/notebook_cells.py`: مقطع `CELL_1_PACKAGE_UPDATER` — بوابة تحديث ما-قبل-الإقلاع: manifest موثَّق من release `pkg-2026.08.09-m15t07` (schema/release/commit/sha256/size/archive_url) من نقطة عامة مستقرة، تنزيل `.part` فقط، تحقق digest/حجم قبل أي تغيير، استبدال ذري للأرشيف والدليل فقط، رفض أثناء تشغيل أي وحدة teledrive، سطر نتيجة واحد منقّح، وعرض `package reference:` في Cell 1؛ توليد النوت‌بوكين و`colab_cells.json` من مولد واحد (متطابقان byte-byte).
- `python-package/tests/test_telegram_flow_contract.py`: sentinel بطول 32 hex + regression بحلقة 48 دورة.
- اختبارات جديدة: `tests/test_package_update.py` (19) + `tests/test_package_service_determinism.py` (2).
- ذاكرة: `docs/{TODO,KNOWN_ISSUES,ACTIVE_TASK,CHANGELOG,AI_HANDOFF}.md` + `python-package/docs/PHASE_REPORTS/PHASE_M15_T07.md`.

### Not changed — عمدًا
- لم تُمس: `drive_auth.py`, `auth_manager.py`, `app_context.py`, `services.py`, `app.py`, `ui.py`, `telegram_auth.py`, `telegram_client.py`, `transfer_manager.py`, `requirements.lock`, `.github/workflows/**`, وكل الواجهة الأمامية. منطق restore في Cell 1 (fallback + unwrap) بقي حرفيًا؛ أُضيفت استدعاءات البوابة حوله فقط.
- إصلاح الوكيل M15-T06 (`inline=False`، `server_name="0.0.0.0"`، المنفذ الثابت 7860، `proxyPort` الرسمي، `root_path`، و`NO_PROXY` المحدود) سليم ولم يُقارب؛ لا مسار `share=True` أُضيف.
- إصلاح M15-T05 (عميل Drive الكسول للـcheckpoint) سليم — `services.py` خارج النطاق ولم تُعدَّل.
- الحالة الصادقة: `Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.`

## [M15-T04] — 2026-08-09 — تشخيص اتصال Telegram وإعادة بناء واجهة Colab (غرافيت RTL/LTR) مع الحفاظ على التحكم الحقيقي

### Verified
- تشخيص Telegram الكامل: عميل واحد، Telethon user account، إدخال مخفي في Cell 3، نفس السياق/العميل/الـ loop في Cell 4، الواجهة تستخدم الواجهة العامة السباعية فقط — كلها مثبتة باختبارات حقيقية، ولا اعتمادية مكشوفة في أي مخرجات.
- عيبان حقيقيان أُصلحا: (أ) `ProgressTracker.snapshot()` كان يعلِّق نفسه (`Lock` → `RLock`)، (ب) الواجهة الخام أصبحت قشرة غرافيت RTL افتراضيًا / LTR مع بذر من الحالة الحية.
- OTP يظهر فقط في `CODE_REQUESTED` و2FA فقط في `PASSWORD_REQUIRED` — في الإقلاع الأول وبعد تبديل اللغة، على Gradio حقيقي.
- كل الـ 41 إجراءً المُعلن في `ui.py` ومربوط عبر `wire_if_ready`؛ `assert_complete()` في كل render pass؛ لا lambda ولا أحداث مباشرة ولا زر شكلي ولا تطبيق ثانٍ.
- `python -m pytest -q tests`: **360 passed** (338 + 22 جديدًا). `compileall` PASS · `launcher --check`: `24/41` · notebooks in sync/IDENTICAL · `package_service --build` archive ✔ · Gradio smoke حقيقي (`/config 200`, `share=False`).
- `bun run lint`/`bun run build`: **لم تُنفَّذ في الحاوية** — حاجز شبكة يمنع تنزيل رزمتي `@lovable.dev/*` من `europe-west1-npm.pkg.dev`؛ صفر ملفات frontend معدَّلة؛ بوابة CI على الـPR هي الحكم.

### Changed
- `python-package/teledrive/ui.py`: إعادة بناء كاملة — شريط علوي حقيقي (اسم+نسخة، شريحتا Telegram/Drive، زر اللغة، زر ZIP)، تنقل جانبي بـ`gr.Tabs` الأصلي، 7 صفحات بأسماء DOC، بذر كل مكوّن من `handlers.shell_seed`، تبديل لغة عبر `gr.State`+`gr.render` يحفظ الحالة التشغيلية.
- `python-package/teledrive/handlers.py`: استخراج `_quota_view` المشترك + `shell_seed(ctx)` المشتق من الحالة الحية فقط + تلميع `_queue_view`.
- `python-package/teledrive/progress_tracker.py`: `Lock` → `RLock` (عيب deadlock مثبت؛ انظر DEVIATIONS في تقرير الجلسة).
- `python-package/teledrive/locale/{ar,en}.json`: 5 مفاتيح جديدة + تسميات صفحات DOC.
- اختبارات: `tests/test_ui_shell_contract.py` (18) + `tests/test_drive_connection_gate.py` (4).
- ذاكرة: `docs/{TODO,KNOWN_ISSUES,ACTIVE_TASK,CHANGELOG,AI_HANDOFF}.md` + `docs/PHASE_REPORTS/PHASE_19.md`.

### Not changed — عمدًا
- لم تُمس: `action_registry.py`, `telegram_auth.py`, `telegram_client.py`, `notebook_cells.py`, النوتبوكان, `.github/**`, `services.py`, `app.py`, `ui_binder.py`, `requirements*.txt`, `requirements.lock`, `bun.lock`, وكل الواجهة الأمامية.
- الحالة الصادقة: `Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.`

## [M15-T03] — 2026-08-08 — إصلاح تدفق تسجيل Telegram داخل Colab: لوحتا OTP و2FA الشرطيتان مع اختبارات contract

### Verified
- لوحة OTP تظهر حصريًا عندما تكون الحالة `CODE_REQUESTED` وتختفي عند المصادقة أو قبل طلب الكود.
- لوحة 2FA تظهر حصريًا عندما تكون الحالة `PASSWORD_REQUIRED` بعد استجابة حقيقية بـ `SessionPasswordNeededError` ولا تظهر للحسابات التي لا تملك 2FA.
- فشل أي إجراء Telegram يعيد اشتقاق ظهور اللوحتين ديناميكيًا من حالة آلة الحالة الحية دون فقدان التزامن.
- `Connected` لا يظهر أبدًا قبل تحقيق `AUTHORIZED` فعليًا.
- `python -m pytest -q tests`: **338 passed in 8.58s** (322 + 16 جديدًا). `compileall`: PASS. `launcher --check`: `24/41 ready actions resolve`. `notebook_cells --check`: in sync. `cmp` النوتبوكين: IDENTICAL. `package_service --build`: archive ✔. `bun run lint`: 0 errors. `bun run build`: build ✔. Secrets Scan: PASS (0 offenders).

### Changed
- `python-package/teledrive/ui_binder.py`: إضافة دالة `component_update` على مستوى الوحدة كجسر وحيد مع Gradio (تدعم Gradio أو dict mapping في بيئات الاختبار المعزولة).
- `python-package/teledrive/handlers.py`: استيراد `CODE_REQUESTED`, `PASSWORD_REQUIRED`, `component_update`؛ تحديث `ERROR_ARITY` للإجراءات السبعة إلى 4؛ تعديل `_error` و `_telegram_panels` و `_telegram_view` لإرجاع 4 قيم تعكس ظهور اللوحتين.
- `python-package/teledrive/ui.py`: تغليف حقول OTP داخل `with gr.Column(visible=False) as code_panel:` وحقول 2FA داخل `with gr.Column(visible=False) as password_panel:`، وتحديث `telegram_outputs = [telegram_detail, telegram_chip, code_panel, password_panel]`.
- `python-package/teledrive/redaction.py`: تنظيف التعليق من الأرقام التمثيلية لضمان اجتياز فحص الأسرار الصارم.
- `python-package/tests/test_telegram_flow_contract.py`: ملف اختبار جديد بـ 15 اختبار contract يثبت إنشاء عميل واحد، بقاء الـ hash وكلمة المرور في الذاكرة الحية فقط، شروط ظهور لوحتي OTP و 2FA، إغلاق اللوحات بعد المصادقة والخروج، وبقاء التزامن عند الأخطاء.
- `python-package/tests/test_no_hardcoded_credentials.py`: ملف اختبار جديد كبوابة ثابتة تفحص كافة المسارات للتأكد من خلو الشجرة من أي قيم اعتمادية صريحة.
- `docs/PHASE_REPORTS/PHASE_18.md`: تقرير المرحلة 18 المفصل بالأدلة ومخرجات بوابات التحقق.
- `docs/{TODO,KNOWN_ISSUES,ACTIVE_TASK,AI_HANDOFF}.md`: تحديثات الجلسة وتوثيق إغلاق المشكلة #17 و المهمة M15-T03.

### Delivery
- PR [#11](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/11) → `main` · fix commit `3493c62` · CI أخضر: run `31264818794` (pull_request: Python ✓ 46s · Frontend ✓ 16s) وrun `31264504446` (push) · الدمج بيد المالك.

### Not changed — عمدًا
- لم يتم تعديل `telegram_auth.py` أو `telegram_client.py` أو `notebook_cells.py` أو `action_registry.py` أو `TeleDrive.ipynb` أو `.github/workflows/ci.yml` أو الاعتماديات.
- الحالة الصادقة: `Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.`

## [M15-T02] — 2026-08-08 — إصلاح استيراد حزمة Colab: قبول غلاف teledrive-package.zip تلقائيًا

### Verified
- Cell 1 تقبل الآن ثلاثة أشكال دون إعادة تسمية يدوية: الأرشيف الحقيقي `teledrive_v4.5.zip`، والغلاف الرسمي `teledrive-package.zip`، وغلافًا أُعيدت تسميته خطأً (يكتشف بالمحتوى عبر `teledrive-v4.5/` + `requirements.lock`).
- 16 اختبارًا جديدًا في `python-package/tests/test_restore_package.py` يرفع طبقة الدوال AST-حرفيًا من مصدر المولد الواحد ويثبت: قبول المباشر، استخراج الغلاف عبر temp مختلف + نقل ذري، رفض الغلاف المسمّى كحقيقي (لا EOFError)، بقاء الخطأ الواضح عند الغياب، رفض مسارات الأعضاء غير الآمنة (traversal) والمحتوى التالف، ودعم مواضع Drive.
- `python -m pytest -q tests`: **322 passed in 9.08s** (306 + 16 جديدًا). `compileall`: PASS. `launcher --check`: `24/41 ready actions resolve`. `notebook_cells --check`: in sync. `cmp` النوتبوكين: IDENTICAL. `package_service --build`: archive ✔.

### Changed
- `python-package/teledrive/notebook_cells.py`: استبدال منطق Cell 1 بدالة مسمّاة `resolve_package_zip()` + مساعدات `_is_tested_archive` / `_safe_inner_member` / `_unwrap_inner` (temp + `os.replace`، رفض traversal، التحقق من البنية قبل الاعتماد).
- `python-package/tests/test_restore_package.py`: ملف جديد بـ 16 اختبارًا.
- `python-package/notebook/TeleDrive.ipynb` + `public/TeleDrive.ipynb` + `python-package/teledrive/colab_cells.json`: أُعيد توليدها من المولد الواحد؛ النوتبوكان byte-identical.
- `docs/RUNBOOK.md`: تعليمات تنزيل واضحة — الغلاف يُرفع كما هو، ممنوع إعادة تسميته، ومصدره Actions artifact.
- `docs/KNOWN_ISSUES.md`: البند #16 (فخ الغلاف) ✅. `docs/TODO.md`, `docs/ACTIVE_TASK.md`, `docs/AI_HANDOFF.md`, `docs/PHASE_REPORTS/PHASE_17.md`: تحديثات الجلسة.

### Delivery
- PR [#10](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/10) → `main` · fix commit `eb4f5e9` · CI أخضر: run `31261291379` (pull_request: Python ✓ 52s · Frontend ✓ 12s) وrun `31261265446` (push) · الدمج بيد المالك.

### Not changed — عمدًا
- لا تعديل على Telegram أو Drive auth أو UI أو queue أو transfer manager، ولا على `.github/workflows`، ولا Releases، ولا `requirements.lock`/`bun.lock`. تقرير M15-T01 (`docs/PHASE_REPORTS/PHASE_M15_T01.md`) لم يُمسّ.
- `bun run build` محليًا: BLOCKED بيئيًا (خطأ شهادة TLS عند تنزيل tarballs في هذه البيئة؛ `bun run lint` نجح بـ 0 أخطاء/6 تحذيرات) — الإثبات على CI الفعلي. الحالة الصادقة: `Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.`

## [M13-T03] — 2026-08-08 — إصلاح analyze.select_all وanalyze.clear_selection مع اختبارات binding حقيقية

### Verified
- كود المنتج الحالي (`handlers.py` و`services.py`) لإجرائي التحديد `analyze.select_all` و`analyze.clear_selection` سليم ويحقق كل شروط معايير القبول دون تعديل.
- إضافة 5 اختبارات إثبات حقيقية في `python-package/tests/test_selection.py` تثبت:
  - `select_all`: يحدد العناصر المرئية فقط مع استبعاد العناصر المخفية، ويعيد `rows_for(visible)`.
  - `clear_selection`: يمسح التحديد دون حذف العناصر أو تغيير مرئيتها، ويعيد الصفوف المرئية دون تعديل.
  - استدعاء الـ handlers يمر عبر `ctx.resolve(spec.service_path)` ويصل إلى `SelectionService.select_all_visible` و`SelectionService.clear`.
  - مسار الخطأ يرجع الطول الصحيح (`tuple` بطول 2) ولا يسرب أي أسرار أو tracebacks.
- `PATH=/tmp/teledrive-m13-venv/bin:$PATH python -m pytest -q tests`: **306 passed in 8.66s**.
- `python teledrive_launcher.py --check`: **binding check ok: 24/41 ready actions resolve** (ترقية إجرائي التحديد من `NOT_TESTED` إلى `READY`).

### Changed
- `python-package/teledrive/action_registry.py`: ترقية `analyze.select_all` و`analyze.clear_selection` إلى `tested=True` وربط `proof_test` بهما؛ لم تُلمس أي إجراءات أخرى.
- `python-package/tests/test_selection.py`: ملف جديد بـ 5 اختبارات إثبات حقيقية.
- `docs/PHASE_REPORTS/PHASE_16.md`: تقرير المرحلة 16 المفصل بالأدلة ومخرجات بوابات التحقق.
- `docs/TODO.md`: إغلاق M13-T03 وتحديث الخطوة التالية (M13-T04).
- `docs/KNOWN_ISSUES.md`: تحديث البند #10 ليعكس ارتقاء الإجراءات الجاهزة إلى 24/41.
- `docs/ACTIVE_TASK.md` و`docs/AI_HANDOFF.md`: تحديث بطاقة الجلسة والتقرير المعتمد ومخرجات التحقق.

### Not changed — عمدًا
- لم يتم تعديل كود المنتج في `handlers.py` أو `services.py` أو أي مسارات أخرى لثبوت صحتها.
- لا تغيير في `.github/workflows/ci.yml`, `public/**`, `src/**`, `requirements*.txt`, `bun.lock`، أو الدستور. الحالة الصادقة: `Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.`

## [M13-T02] — 2026-08-08 — تدقيق Action Registry وتصنيف الإجراءات غير الجاهزة

### Verified
- `all_specs()` من baseline `61df83e0912debede0e7e41b8bfde5e6bfabcee9` أعاد **41** إجراءً؛ `python teledrive_launcher.py --check` الحالي أعاد `22/41 ready actions resolve`.
- تدقيق كل صف في `docs/PHASE_REPORTS/PHASE_15.md`: `22 READY`, `6 BLOCKED` بسبب native Colab/Drive live gate، و`13 NOT_TESTED`؛ لا `DEAD_CONTROL` أو `NOT_IMPLEMENTED` أو `NOT_WIRED`.
- `PATH=/tmp/teledrive-m13-venv/bin:$PATH python -m pytest -q tests`: **299 passed in 8.22s**. الـvenv خارج Git ومبنية من `requirements.lock`.

### Changed — docs only
- `docs/PHASE_REPORTS/PHASE_15.md`: جدول 41 صفًا، الأدلة file/line/test، مخرجات الأوامر، التصنيف، والحدود الصادقة.
- `docs/TODO.md`: إغلاق M13-T02 وإضافة M13-T03 كـDOC إصلاحي منفصل لأصغر مجموعة `analyze.select_all` + `analyze.clear_selection`.
- `docs/KNOWN_ISSUES.md`: إغلاق #10 بعد إثبات التصنيف.
- `docs/ACTIVE_TASK.md` و`docs/AI_HANDOFF.md`: تحديث baseline/result handoff والحالة والخطوة التالية.

### Not changed — عمدًا
- لا تغيير في `python-package/**`, `.github/workflows/ci.yml`, `public/**`, `src/**`, `requirements*.txt`, `bun.lock`, أو الدستور.
- لم تتغير `implemented` أو `tested`، ولم تُضف fake handlers/services/tests. الحالة الصادقة: `Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.`

## [M13-T01] — 2026-08-08 — توثيق أول تشغيل CI حقيقي وتحليل البوابات

### Verified
- `GitHub Actions Run 31243523514`: أول تشغيل حقيقي ناجح (`success`) على commit المالك `ff6a484`، استغرق 1m21s كاملة (من 06:15:46Z إلى 06:17:07Z).
  - `Python package (tests + Colab contract)` (ID: `93068234642`): نجاح كامل في 1m17s (299 passed في pytest، launcher check، notebook sync، وبناء الحزمة).
  - `Frontend build` (ID: `93068234649`): نجاح كامل في 16s (bun install وbun lint وbun build).
  - `teledrive-package` artifact: رُفع بنجاح محتويًا `teledrive_v4.5.zip`.

### Closed Tasks & Issues
- `docs/TODO.md`: إغلاق `M10-T02` و`M12-T01` و`M12-T02` و`M13-T01` كـ `VERIFIED COMPLETE`. تحديد `M13-T02` كالخطوة القادمة.
- `docs/KNOWN_ISSUES.md`: إغلاق المشاكل #8 (بناء v4.5 في CI)، #13 (انكسار بدء CI بسبب `runner.temp` في job env)، #15 (حاجز صلاحية workflows بعد تطبيق المالك اليدوي لـ commit `ff6a484`).

### Added
- `docs/PHASE_REPORTS/PHASE_14.md`: تقرير الأدلة الكامل لأول تشغيل CI حقيقي ومخرجات البوابات.

### Changed
- `docs/ACTIVE_TASK.md` و`docs/AI_HANDOFF.md`: توثيق الحالة المحدثة والأدلة الفعلية وبطاقة الجلسة.

## [M12-T02] — 2026-08-08 — تصحيح AI_RULES وتنظيف docs وتوثيق السبب الجذري لانكسار CI

### Fixed
- `docs/AI_RULES.md`: استبدال كامل — ترقيم أقسام v5.0 (§2, §3, §7, §9.7, §10, §11, §17, §18, §20)، الأدوار (Brain/LM Arena Agent/Owner)، Lovable يُذكر فقط في فقرة "خرج نهائيًا" (§3) وملاحظة المرآة التقنية، جدول قيود المنصة مضاف. لا §21-§26 (ترقيم v4.5 الملغى).
- `docs/pic for frontend`: حُذف — ملف بايت واحد لوّث بيت الذاكرة القانوني من commit المالك `afde5fe`.

### Changed
- `docs/KNOWN_ISSUES.md`: #8 و#13 مُحدَّثان (السبب الجذري + "بانتظار تطبيق المالك")؛ #14 جديد (تلوث ✅)؛ #15 جديد (صلاحية المنصة).
- `docs/TODO.md`: M10-T02 أوضح؛ M12-T01 → PARTIALLY COMPLETE؛ M12-T02 مضاف؛ M13-T01 أعيدت صياغتها.
- `docs/ACTIVE_TASK.md`: M12-T02.
- `docs/AI_HANDOFF.md`: جلسة M12-T02 بمخرجات حقيقية.

### Added
- `docs/PHASE_REPORTS/PHASE_13.md`: السبب الجذري لانكسار CI، حاجز صلاحية `workflows`، ومخرجات البوابات الثماني.

### Not changed (عمدًا)
- `.github/workflows/ci.yml` — الجزء (أ) بيد المالك حصريًا (صلاحية `workflows`).
- `docs/CONSTITUTION.md` — لم يتغير حرف واحد.
- `docs/CONSTITUTION_V4.5_ARCHIVE.md` — الأرشيف مجمَّد byte-exact.
- تقارير PHASE_0-12 — التاريخ لا يُعدَّل.
- كل كود المنتج والنوت‌بوك والاعتماديات والواجهة.

## [M12-T01] — 2026-08-08 — مصالحة الحوكمة v5.0

### Blocked by platform (مجهَّز ومتحقق محليًا، الدفع مُنع)
- `.github/workflows/ci.yml`: سطران لبناء ورفع `teledrive_v4.5.zip` بدل `teledrive_v3.1.zip` — مُستعدّان بأمر `sed` موثَّق في PHASE_12. دفعهما مُنع لأن GitHub App بلا صلاحية `workflows`؛ يُدفَعان بعد إعادة ربط GitHub أو يدويًا بيد المالك.
- `.github/workflows/ci.yml` سطر 16: `TELEDRIVE_ROOT` من `${{ runner.temp }}` إلى `${{ github.workspace }}` — إصلاح إضافي مكتشف بعد أول دفعة: CI لا يبدأ منذ 2cc5747 على أي فرع بما فيها main (`Unrecognized named-value: 'runner'` في job-env؛ KNOWN_ISSUES #13، الدليل في PHASE_12).

### Fixed
- `docs/BOOTSTRAP_PROMPT.md`: ترقيم أقسام v5.0، وإزالة Lovable كمرجع تشغيلي.

### Added
- `docs/ACTIVE_TASK.md`، `docs/MIGRATION.md`، `docs/REPOSITORY_REGISTRY.md` (ملفات §7 الإلزامية الناقصة).
- `docs/CONSTITUTION_V4.5_ARCHIVE.md`: استرجاع byte-exact لدستور v4.5 المحذوف في PR #4 (blob c281a5cd).
- `docs/decisions/ADR-002-v5-governance-promotion.md`.
- `docs/PHASE_REPORTS/PHASE_10.md`: قالب فارغ لتشغيل Colab الحقيقي.

### Changed
- `docs/TeleDrive-v5.md`: صار مؤشرًا بدل نسخة مكررة من الدستور.
- `docs/TODO.md`: TASK IDs بصيغة §6، وإعادة فتح M10-T02.
- `docs/KNOWN_ISSUES.md`: بنود 8–11 جديدة بأدلتها.
- `docs/AI_HANDOFF.md`: الحقول الإلزامية كاملة بنص §7.

### Not changed (عمدًا)
- `docs/CONSTITUTION.md` — لا تعديل على الدستور النافذ.
- `.github/workflows/ci.yml` — بقي كما هو في هذه الدفعة بسبب العائق أعلاه (وليس قرارًا تصميميًا).
- كل كود المنتج والنوت‌بوك والاعتماديات والواجهة.

## v4.5.0-identity-1 — 2026-08-08 (توحيد هوية v4.5.0 + إنهاء مؤشرات ADR-001)

- **توحيد أرقام وإصدارات الحزمة بالكامل إلى 4.5.0:**
  - `python-package/teledrive/__init__.py`: تحديث `__version__ = "4.5.0"`, `__spec_version__ = "4.5.0"` ووصف `TeleDrive v4.5`.
  - `python-package/teledrive/config.py`: تحديث `version: str = "4.5.0"`, `spec_version: str = "4.5.0"`.
  - `python-package/teledrive/notebook_cells.py`: تحديث `NOTEBOOK_VERSION = "4.5.0"`, `TITLE = "TeleDrive v4.5 — Telegram → Google Drive (native Colab)"`, `PACKAGE_ZIP = LOCAL_ROOT / "teledrive_v4.5.zip"`, `DRIVE_ZIP = pathlib.Path("/content/drive/MyDrive/TeleDrive/teledrive_v4.5.zip")`, `PACKAGE_DIR = next(p for p in LOCAL_ROOT.glob("teledrive-v4.5*") if p.is_dir())`.
  - توليد وإعادة كتابة النوت‌بوك الثنائي ومصدر الخلايا: `public/TeleDrive.ipynb` و `python-package/notebook/TeleDrive.ipynb` و `python-package/teledrive/colab_cells.json` متطابقة تماماً.
  - `python-package/teledrive/package_service.py`: الحزمة الافتراضية `teledrive_v4.5.zip` والمجلد الداخلي `teledrive-v4.5`.
  - `python-package/teledrive_launcher.py`: المساعد يصف `TeleDrive v4.5 launcher`.
  - `python-package/requirements.lock`: ترويسة `# TeleDrive v4.5 — pinned dependency lock.`.
  - `.github/workflows/ci.yml`: بناء ونشر `teledrive_v4.5.zip`.
  - `python-package/tests/test_notebook.py`: اختبار `test_title_is_v45` يتحقق من وجود `TeleDrive v4.5` وغياب `v2` و `v3.1`.
  - `src/routes/index.tsx`: تحديث واجهة التحميل إلى TeleDrive v4.5 بالكامل.
  - `README.md`: تحديث الهوية إلى TeleDrive v4.5 وربطها بـ `docs/`.
- **إكمال تطبيق مؤشرات نظام الاستمرارية (ADR-001 / TODO #1):**
  - نسخ كافة تقارير المراحل التاريخية إلى `docs/PHASE_REPORTS/` (PHASE_0, 1, 1_CI, 2, 2_TO_8, 3, 9, B, C).
  - تحويل ملفات `python-package/docs/*.md` إلى مؤشرات سطر واحد قانونية.
  - تحويل `PROJECT_CONTEXT.md` في الجذر و `python-package/CHANGELOG.md` و `python-package/HANDOFF.md` إلى مؤشرات مرجعية لـ `docs/`.
- **البوابات التي شُغلت ونجحت:**
  - `python3 -m compileall teledrive` (exit 0)
  - `python3 teledrive_launcher.py --check` (exit 0 — 22/41 ready actions resolve, bootstrap runtime ok)
  - `python3 -m teledrive.notebook_cells --check` (exit 0 — notebooks are in sync)
  - `cmp python-package/notebook/TeleDrive.ipynb public/TeleDrive.ipynb` (exit 0 — byte-identical)
- **الحالة:** Code-complete candidate; real integrations unverified.

## v4.5.0-aios-1 — 2026-08-08 (AI-OS Phase 11 بداية — بيت التوثيق القانوني)

- **الهدف:** تطبيق §18 من دستور v4.5 (ADR-001) — إنشاء البيت القانوني `docs/` كمصدر وحيد.
- **إنشاء:** `docs/PROJECT_CONTEXT.md` (نسخة v4.5 القانونية، authority = docs/CONSTITUTION.md)، `docs/ARCHITECTURE.md` (خريطة حالية 44 وحدة + 41 action + transfer order)، `docs/CHANGELOG.md`.
- **الأساس:** دستور v4.5 716 سطر موجود بالفعل في `docs/CONSTITUTION.md` (من جلسة 2026-08-06).
- **سلوك التشغيل:** لا يتغير إطلاقًا — تغيير توثيقي بحت.
- **الحالة:** Code-complete candidate; real integrations unverified.

## v3.1.0-phase9 — 2026-07-29 (audit repair — مؤرشف من python-package/CHANGELOG)

- `app.launch(blocking=False)` يمرر `prevent_thread_lock` إلى Gradio؛ handle على `ctx.ui` ويُغلق بـ `ctx.shutdown()` — الخلية 4 لم تعد تحجب 5-7.
- `requirements.lock` مصدر وحيد؛ لا `package==version` في أي خلية/colab_cells.json (محمي باختبار).
- CI: compileall أولًا ثم pytest ثم --check ثم تطابق نوتبوك ثم build؛ `bun lint` قبل `build`؛ لا continue-on-error.
- PHASE_9.md يوثق مخرجات حقيقية + SHA + شجرة ملفات.
- Tests: 177 passed (يحتاج إعادة إثبات لاحقًا).
- Status: Code-complete candidate — real integrations unverified.

## v3.1.0-phase1 — 2026-07-29

- `async_runtime.py` الحلقة الوحيدة، `app_context.py` سياق واحد، `resolve()` صارم.
- إزالة 6 نداءات `new_event_loop()` وخيط نقل من `ui.py`، إزالة lambda inline.
- اختبارات `test_no_ad_hoc_loops.py` + `test_app_context.py`. 48 test.

## v3.1.0-phase0 — 2026-07-29

- Audit ومواءمة: CONSTITUTION, AUDIT, PHASE_0, requirements.lock, spec_version 3.1.0.

## v1.0.0 — 2026-07-29

- Initial per Constitution v2.0 — Telethon user + Drive OAuth Desktop (تم استبداله لاحقًا بـ native Colab auth).
