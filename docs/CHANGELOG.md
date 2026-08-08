# CHANGELOG — آخر 20-30 تغيير (TeleDrive v4.5)

> الأرشيف الكامل: `docs/CHANGELOG_ARCHIVE.md` — هذا الملف للجلسات الأخيرة فقط.

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
