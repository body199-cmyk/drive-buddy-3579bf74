# CHANGELOG — آخر 20-30 تغيير (TeleDrive v4.5)

> الأرشيف الكامل: `docs/CHANGELOG_ARCHIVE.md` — هذا الملف للجلسات الأخيرة فقط.

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
