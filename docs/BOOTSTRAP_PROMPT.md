# BOOTSTRAP_PROMPT — نقطة البداية الإلزامية لأي جلسة أو حساب جديد (TeleDrive)

> أنت داخل مشروع **TeleDrive** — مشروع مستمر، وليس مشروعًا جديدًا.
> **إصدار المنتج: 4.5.0 · إصدار الحوكمة: 5.0.0.**
> اقرأ هذا الملف أولًا، ثم اتبع ترتيب القراءة، ثم تابع من رأس `docs/TODO.md`.
> ممنوع البدء من الصفر، وممنوع الادعاء بلا دليل في الريبو أو مخرجات أوامر فعلية.

## 1) السياق السريع

- المنتج: مدير نقل وسائط من حساب Telegram مستخدم إلى Google Drive داخل Google Colab. ليس Bot، وليس خدمة ويب، وليس VPS.
- الواجهة: Gradio داخل نفس عملية Python، محليًا بـ `share=False`، عربية RTL افتراضيًا.
- المستودع القانوني: `https://github.com/body199-cmyk/drive-buddy-3579bf74.git` — الفرع `main`.
- الدستور النافذ: `docs/CONSTITUTION.md` (v5.0.0). الأرشيف التاريخي غير النافذ: `docs/CONSTITUTION_V4.5_ARCHIVE.md`.

## 2) الأدوار (§3)

| الدور | من | الصلاحية |
|---|---|---|
| المهندس والمراجع وكاتب الكود | Brain عبر ClickUp Docs | يفحص GitHub، يصمم، يكتب الخطة والكود داخل DOC، يراجع النتيجة. **لا يعدّل GitHub.** |
| المنفّذ الوحيد | LM Arena Agent | يقرأ الريبو والدستور وDOC، ينفّذ، يتحقق، يرفع. **لا يعيد التصميم ولا يخفي فشلًا.** |
| المالك | body199-cmyk | الأولويات، اعتماد ADR، إرسال روابط DOC، الاختبار الحي في Colab. |

**Lovable خرج من المشروع نهائيًا.** أي إشارة قديمة إليه كمنفّذ تُصحَّح إلى LM Arena Agent.

## 3) ترتيب القراءة الإلزامي (§8)

| المستوى | الملفات | لماذا |
|---|---|---|
| L1 | `CONSTITUTION.md` ← `BOOTSTRAP_PROMPT.md` ← `AI_RULES.md` ← `PROJECT_CONTEXT.md` ← `AI_HANDOFF.md` | القانون، الهوية، الأدوار، آخر تسليم |
| L2 | `KNOWN_ISSUES.md` ← `TODO.md` ← `ACTIVE_TASK.md` ← `REPOSITORY_REGISTRY.md` ← `MIGRATION.md` | العوائق، العمل المفتوح، القفل الحالي، المصادر |
| L3 | `decisions/ADR-*.md` + `ARCHITECTURE.md` + شجرة المصدر + `python-package/tests/` + `.github/workflows/ci.yml` | القرارات والخريطة والأدلة |
| L4 | `AUDIT.md` + `PHASE_REPORTS/*` + `CHANGELOG.md` | التاريخ الكامل |

ثم **اطبع** الفرع وHEAD والشجرة، وقارن SHA المسجَّل في `AI_HANDOFF.md` بـ`git rev-parse HEAD`. إذا اختلفا فالهاندوف متقادم ويجب إعادة التدقيق قبل أي تعديل.

## 4) إذا كانت الجلسة السابقة مغلقة

طبّق **§9 كاملًا** من الدستور قبل أي تعديل: فحص baseline، تصنيف حالة PR السابق، جدول `Requirement | Expected file | Present in baseline? | Verified? | Action`، ثم إعلان تصنيف استئناف واحد: `RESUME_VERIFIED` / `RESUME_PARTIAL` / `RESUME_FAILED` / `RESUME_BLOCKED` / `RESUME_UNKNOWN`.

إغلاق جلسة Arena لا يعني نجاح المهمة. الدمج يثبت دخول commit إلى الفرع فقط، ولا يثبت الوظيفة ولا Colab readiness.

## 5) دورة العمل (§4)

1. حدد أول بند غير مكتمل في `docs/TODO.md` وخذ TASK ID الخاص به.
2. تأكد أن `KNOWN_ISSUES.md` لا يحوي عائقًا عليه، وأن `ACTIVE_TASK.md` ليس مقفلًا على مهمة أخرى.
3. أثبت الحالة الفعلية: `git log -1` + `git status` + بوابات §16.
4. نفّذ **أصغر تغيير آمن** يخدم البند وحده، على branch جانبي باسم TASK ID.
5. حدّث `AI_HANDOFF.md` + `ACTIVE_TASK.md` + `TODO.md` + `CHANGELOG.md` + `KNOWN_ISSUES.md` + تقرير مرحلة، بمخرجات حقيقية.
6. التزم صيغة التقرير الإلزامية في **§18**. أي رد بلا SHA ومخرجات يُعتبر ناقصًا.

## 6) بوابات التحقق (§16)

من `python-package`:
```bash
python -m compileall teledrive
python -m pytest -q tests
python teledrive_launcher.py --check
python -m teledrive.notebook_cells --check
cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb
python -m teledrive.package_service --build --output teledrive_v4.5.zip
```

ومن الجذر:

```
bun run lint
bun run build
```

`compileall` و`launcher --check` **ليسا بديلًا عن pytest** (§9.7). الاختبارات الوهمية ليست دليل تكامل حقيقي.

## 7) الحالة الصادقة الوحيدة (§17)

**Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.**

لا يجوز قول `Colab-ready` قبل اختبار Colab حقيقي مضبوط موثّق في `docs/PHASE_REPORTS/PHASE_10.md`، ولا `Complete` قبل نقل حقيقي + shutdown + recovery + سجلات منقّحة + handoff.

## 8) ممنوعات مختصرة (القائمة الكاملة في §11)

- لا تطبيق ثانٍ ولا `app_v2.py` ولا Python داخل نصوص TypeScript.
- لا بيانات وهمية: صفوف، سجلات، حصص، معرفات، تقدم، أو حالات اتصال.
- لا زر بلا handler مسمّى + مسار خدمة + اختبار. لا lambda في layout.
- لا أسرار في أي ملف أو سجل أو ZIP أو handoff: API ID/hash، توكنات، أرقام، رموز، session strings.
- لا SQLite على FUSE. لا concurrency فوق 4. لا streaming بدل disk-first.
- لا حذف من Drive عند cancel/stop. لا auto-resume بعد restart.
- لا force-push ولا rebase ولا amend على تاريخ منشور.
- لا ترقية اعتماديات بلا دليل توافق.

## 9) قاعدة التوقف (§20)

توقف فورًا عند: اختلاف المستودع القانوني، اختلاف HEAD بلا تفسير، تعارض غير محسوم، ملف مفقود، اختبار فاشل، فشل GitHub، ظهور سر، أو ادعاء غير قابل للإثبات. **التوقف مقبول؛ التظاهر بالنجاح مرفوض.**

---

**مصدر هذا الملف:** ADR-001 (نظام الاستمرارية) + ADR-002 (ترقية الحوكمة v5.0). لا يُحذف ولا يُدمج في ملف آخر.
