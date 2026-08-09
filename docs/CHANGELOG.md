# CHANGELOG — آخر 20-30 تغيير (TeleDrive v4.5)

> الأرشيف الكامل: `docs/CHANGELOG_ARCHIVE.md` — هذا الملف للجلسات الأخيرة فقط.

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
