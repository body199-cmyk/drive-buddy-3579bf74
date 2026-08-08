# CHANGELOG — آخر 20-30 تغيير (TeleDrive v4.5)

> الأرشيف الكامل: `docs/CHANGELOG_ARCHIVE.md` — هذا الملف للجلسات الأخيرة فقط.

## v4.5.0-aios-1 — 2026-08-08 (AI-OS Phase 11 بداية — بيت التوثيق القانوني)

- **الهدف:** تطبيق §18 من دستور v4.5 (ADR-001) — إنشاء البيت القانوني `docs/` كمصدر وحيد.
- **إنشاء:** `docs/PROJECT_CONTEXT.md` (نسخة v4.5 القانونية، authority = docs/CONSTITUTION.md)، `docs/ARCHITECTURE.md` (خريطة حالية 44 وحدة + 41 action + transfer order)، `docs/CHANGELOG.md` (هذا الملف).
- **المتبقي في نفس البند:** `docs/RUNBOOK.md`, `TROUBLESHOOTING.md`, `AUDIT.md`, `PHASE_REPORTS/`, `decisions/ARCHIVE.md`, `CHANGELOG.md` — كلها سيتم إنشاؤها كمؤشرات نظيفة أو نسخ محدثة من `python-package/docs/` مع الالتزام بـ "سطر مؤشر واحد في المواقع القديمة" (ADR-001 §7).
- **الأساس:** دستور v4.5 716 سطر موجود بالفعل في `docs/CONSTITUTION.md` (من جلسة 2026-08-06).
- **سلوك التشغيل:** لا يتغير إطلاقًا — تغيير توثيقي بحت.
- **البوابات:** لم تُشغل بعد في هذه الجلسة — سيتم تشغيلها قبل push.
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
