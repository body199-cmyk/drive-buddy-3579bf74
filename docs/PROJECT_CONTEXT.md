# PROJECT_CONTEXT — TeleDrive v4.5 Canonical Context (AI-OS Home)

> **المرجع الأعلى:** `docs/CONSTITUTION.md` v4.5.0 — هذا الملف هو نقطة الدخول L1 مع `BOOTSTRAP_PROMPT.md` و `AI_RULES.md` و `AI_HANDOFF.md` و `TODO.md`
> **الموقع القديم:** `PROJECT_CONTEXT.md` في الجذر كان يحمل نفس الاسم لكنه يشير الآن إلى هذا الملف — المصدر القانوني هو هذا المسار فقط.

**Authority:** `docs/CONSTITUTION.md` v4.5.0 + `docs/ARCHITECTURE.md` + `docs/AUDIT.md`

## الهوية

- المنتج: **TeleDrive v4.5** — محرك نقل وسائط من Telegram إلى Google Drive يعمل داخل Google Colab فقط.
- الواجهة: Gradio داخل نفس عملية Python، `share=False` افتراضيًا، عربي RTL افتراضي.
- الريبو القانوني: `https://github.com/body199-cmyk/drive-buddy-3579bf74.git`
- المواصفة: `4.5.0` — مبنية على v3.1 Code-Bound مع توسيع AI-OS (§18-§19).

## الحالة الصادقة (2026-08-08)

- Phase 0: COMPLETE — docs skeleton, requirements.lock, spec_version/version 4.5.0 موحد.
- Phase 1: COMPLETE — ApplicationContext واحد + AsyncRuntime واحد، لا حلقات ad-hoc.
- Phase 2-8: COMPLETE — action_registry (41 action), ui_binder، handlers، Telegram state machine 10 حالات، Drive native auth (`adopt_service`), scanning/selection, queue/recovery, UI/theme/export, notebook 7 خلايا.
- Phase 9: COMPLETE in code — cell 4 non-blocking (`blocking=False` → `prevent_thread_lock=True`), `requirements.lock` مصدر وحيد، CI يشغل 6 بوابات + bun lint/build.
- Phase 10: **NOT VERIFIED** — يتطلب Colab حقيقي + حسابات حية (بيد المالك).
- Phase 11 (AI-OS): **COMPLETE** — توحيد بيت التوثيق في `docs/` حسب §18، وتوحيد هوية v4.5.0 بالكامل، وتحويل المواقع القديمة لمؤشرات قانونية (ADR-001).

**Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.** لا يجوز قول Colab-ready قبل PHASE_10.

## شجرة التوثيق القانونية (Constitution §18)

```
docs/
├── PROJECT_CONTEXT.md      (هذا الملف)
├── ARCHITECTURE.md         (الخريطة الحالية فقط)
├── CONSTITUTION.md         (v4.5.0 — المرجع)
├── AI_RULES.md
├── AI_HANDOFF.md           (آخر جلسة فقط، يُستبدل)
├── BOOTSTRAP_PROMPT.md     (بوابة دخول أي حساب جديد)
├── CHANGELOG.md            (آخر 20-30 بند)
├── CHANGELOG_ARCHIVE.md
├── TODO.md                 (العمود الفقري للتقدم)
├── KNOWN_ISSUES.md
├── RUNBOOK.md
├── TROUBLESHOOTING.md
├── AUDIT.md
├── PHASE_REPORTS/
└── decisions/
    ├── ADR_TEMPLATE.md
    ├── ARCHIVE.md
    └── ADR-*.md
```

المواقع القديمة تحت `python-package/docs/` و `PROJECT_CONTEXT.md` في الجذر تحتفظ **بمؤشر سطر واحد** فقط (ADR-001) — لا نسخ مكررة.

## بروتوكول الجلسة (per session)

1. اقرأ L1: BOOTSTRAP_PROMPT → AI_RULES → AI_HANDOFF → TODO → CONSTITUTION
2. تحقق: `git log -1` + `git status` + شجرة `docs/` + `python-package/teledrive/` + CI
3. نفذ بند واحد من TODO فقط — أصغر تغيير آمن
4. شغل البوابات (§16): `compileall` + `pytest -q` + `teledrive_launcher --check` + `notebook_cells --check` + `cmp notebooks` + `package_service --build` + `bun lint` + `bun build`
5. حدّث: AI_HANDOFF + CHANGELOG + TODO + KNOWN_ISSUES + PHASE_REPORT
6. لا force-push / rebase (AGENTS.md — مزامنة Lovable)

## Frontend

`src/` صفحة هبوط/تحميل فقط. لا يجوز أن يصبح runtime لتيليجرام/درايف.

## Session vault (M24-T01)

التطبيق يدعم الآن **Telegram session vault on the user's own Drive account**.
ملف الجلسة يُشغَّل محليًا فقط تحت `/content/teledrive_runtime/session/telegram.session`.
Drive يحتفظ بنسخة احتياطية (`telegram.session` + `telegram_creds.json` داخل `TeleDrive_AppData`) لا أكثر.
نفس حساب Drive يستعيد الجلسة تلقائيًا؛ حساب مختلف لا يستعيد شيئًا.

## Secrets

API ID/hash، أرقام هواتف، أكواد، 2FA، session strings، OAuth tokens، روابط خاصة، tracebacks غير منقحة — ممنوعة في كل مكان (ملفات، سجلات، checkoints، ZIP، git). تخزين `telegram_creds.json` على Drive الخاص بالمستخدم انحراف مقصود وموثّق في ADR-0002؛ القيم لا تُطبع في السجلات.

---
**Next:** TODO #4 (تشغيل البوابات الست في بيئة اختبار كاملة + فحص Gradio 6.20.0 والأسرار).
