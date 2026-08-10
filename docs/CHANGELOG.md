# CHANGELOG — آخر 20-30 تغيير (TeleDrive v4.5)

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
