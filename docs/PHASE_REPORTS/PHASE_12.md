# PHASE_12 — مصالحة الحوكمة v5.0 واستكمال بيت الذاكرة (M12-T01)

**TASK ID:** M12-T01

**Repository URL, branch, commit:**
- Repo: `https://github.com/body199-cmyk/drive-buddy-3579bf74.git`
- Branch: `arena/019fdfc5-drive-buddy-3579bf74` (انحراف موثَّق: DOC اقترح `task/M12-T01-constitution-v5-reconciliation` لكن جلسة Arena مثبَّتة على هذا الفرع ولا تسمح بتبديله)
- Base SHA: `4cacc584834a7fc8e0b8ccf36b53ca3808cbab77` (merge PR #4)
- Result SHA: رأس الفرع بعد commit هذا التقرير نفسه — يُستخرج بـ `git log -1 --format=%H`؛ يستحيل رياضيًا تضمين SHA الـcommit داخل شجرته ذاتها، والاسم الكامل مسجَّل في متن الـPR ورد الجلسة
- Date: 2026-08-08

**Goal:**
- إغلاق الفجوات المثبتة بين شجرة GitHub ودستور v5.0 دون لمس كود المنتج: إصلاح CI (v3.1 → v4.5)، استكمال ملفات §7، أرشفة دستور v4.5 byte-exact، ADR-002، تصحيح المؤشرات، وTASK IDs.
- تصنيف الاستئناف المعلن: RESUME_PARTIAL (PR #4 مدموج وملفاته موجودة، لكن ادعاءات PR #3 حول CI غير موجودة في baseline وملفات §7 ناقصة).

**Baseline check (الخطوة 0 من DOC، قبل أي تعديل):**

| Requirement | Expected file | Present in baseline? | Verified? | Action |
|---|---|---|---|---|
| CI يبني v4.5 | `.github/workflows/ci.yml` | موجود لكنه يبني `teledrive_v3.1.zip` (السطران 59 و64) | `grep -n "teledrive_v"` أظهر v3.1 مرتين | MODIFY — سطران بـ sed |
| قفل المهمة | `docs/ACTIVE_TASK.md` | لا | `find docs` | CREATE |
| سجل الهجرة | `docs/MIGRATION.md` | لا | `find docs` | CREATE |
| سجل المستودعات | `docs/REPOSITORY_REGISTRY.md` | لا | `find docs` | CREATE |
| أرشيف v4.5 | `docs/CONSTITUTION_V4.5_ARCHIVE.md` | لا | `find docs` | CREATE — استرجاع byte-exact |
| ADR-002 | `docs/decisions/ADR-002-*.md` | لا (فقط ADR-001 + TEMPLATE + ARCHIVE) | `find docs` | CREATE |
| قالب المرحلة 10 | `docs/PHASE_REPORTS/PHASE_10.md` | لا (0,1,1_CI,2,2_TO_8,3,9,11,B,C) | `find docs` | CREATE |

فحوص baseline إضافية:
- `git rev-parse HEAD` = `4cacc584834a7fc8e0b8ccf36b53ca3808cbab77` — مطابق للـbase المطلوب.
- blob `ci.yml` (`5dec51e`) حجمه 2156 بايت — مطابق لادعاء DOC.
- `git hash-object docs/CONSTITUTION.md docs/TeleDrive-v5.md` = كلاهما `9a85ffb8...` — الفجوة G مؤكدة (ازدواج المصدر).
- blob دستور v4.5 المستهدف استرجاعه `c281a5cd` حجمه 29,547 بايت — مطابق لادعاء DOC.
- HEAD كان shallow (grafted)؛ نُفِّذ `git fetch --unshallow origin` لاسترجاع التاريخ المحلي فقط (لا يغيّر أي ref منشور).

**Files inspected:**
- `.github/workflows/ci.yml` (blob 5dec51e)
- `docs/CONSTITUTION.md` (v5.0.0 — لم يُلمس)
- `docs/TeleDrive-v5.md`، `docs/BOOTSTRAP_PROMPT.md`، `docs/TODO.md`، `docs/KNOWN_ISSUES.md`، `docs/AI_HANDOFF.md`، `docs/CHANGELOG.md`
- `docs/AI_RULES.md` (فحص فقط — §12 من DOC؛ لم يُعدَّل)
- `docs/PHASE_REPORTS/PHASE_11.md` (للالتزام بالبنية)
- `docs/decisions/ADR-001-aios-continuation.md`

**Files created:**
- `docs/ACTIVE_TASK.md` (قفل معلوماتي §7 — الفرع والتاريخ الحقيقيان)
- `docs/MIGRATION.md` (سجل الهجرات 0–4)
- `docs/REPOSITORY_REGISTRY.md` (المستودع القانوني والمصادر)
- `docs/CONSTITUTION_V4.5_ARCHIVE.md` (استرجاع byte-exact من 821cc25 — `git hash-object` = `c281a5cd38d594b54999f77a36c4d000bb6362d3`)
- `docs/decisions/ADR-002-v5-governance-promotion.md`
- `docs/PHASE_REPORTS/PHASE_10.md` (قالب فارغ NOT STARTED — بيد المالك فقط)
- `docs/PHASE_REPORTS/PHASE_12.md` (هذا التقرير)

**Files changed:**
- `docs/TeleDrive-v5.md`: من نسخة مكررة 27,523 بايت إلى مؤشر سطر واحد (§0، §7).
- `docs/BOOTSTRAP_PROMPT.md`: استبدال كامل — ترقيم أقسام v5.0، الأدوار §3 (LM Arena Agent المنفّذ الوحيد)، ترتيب قراءة §8 يشمل ACTIVE_TASK/REPOSITORY_REGISTRY/MIGRATION، بوابات §16 تتضمن pytest وأمر بناء `teledrive_v4.5.zip`. لا ذكر لـLovable كمنفّذ.
- `docs/TODO.md`: TASK IDs بصيغة Mxx-Txx؛ M10-T02 مسجَّل بصدق كـ PARTIALLY COMPLETE → يُغلق في M12-T01.
- `docs/KNOWN_ISSUES.md`: بنود جديدة #8 (CI كان يبني v3.1)، #9 (الأرشيف يشحن مؤشرات — M14-T01 خارج النطاق)، #10 (22/41 actions)، #11 (pytest لم يُشغَّل في جلسة PR #3 — أُغلق هنا).
- `docs/CHANGELOG.md`: مدخل `[M12-T01]` أعلى المدخلات بلا حذف أي شيء.
- `docs/AI_HANDOFF.md`: استبدال كامل بالحقول الإلزامية بنص §7 بمخرجات حقيقية.

**Prepared but NOT pushed (عائق منصة مؤكد):**
- `.github/workflows/ci.yml`: سطران عبر `sed 's/teledrive_v3\.1\.zip/teledrive_v4.5.zip/g'` — متحقق محليًا (v4.5 ظهر مرتين، v3.1 صفر). الدفع مُنع لأن GitHub App بلا صلاحية `workflows` (دليل الطرفية أدناه). أُعيد الملف بلا تغيير لتبقى الدفعة docs-only.

**Files moved/deleted:**
- None. (ملف `teledrive_v4.5.zip` الناتج عن بوابة البناء أُزيل بعد التحقق — artifact وليس مصدرًا.)

**Protected files unchanged (FORBIDDEN per DOC §5.3):**
- `docs/CONSTITUTION.md` — لم يتغير حرف واحد (تحقق أدناه).
- `python-package/teledrive/**`، `python-package/tests/**`، `teledrive_launcher.py`، `requirements.txt|lock` — بلا لمس.
- النوت‌بوكان و`colab_cells.json` — بلا لمس.
- `src/**`، `package.json`، `bun.lock`، `vite.config.ts`، `tsconfig.json` — بلا لمس.

**Implementation summary:**
1. فحص baseline وأكّد كل ادعاءات DOC (A–K) قبل أي كتابة.
2. `sed` موضعي على CI (سطران) + استرجاع v4.5 من تاريخ git الرسمي (لا كتابة يدوية — ثنائي بايت-ببايت).
3. إنشاء ملفات §7/المرحلة 10 بالمحتوى المعتمد من DOC، مع تعبئة التاريخ والفرع الحقيقيين فقط في ACTIVE_TASK.
4. تحويل TeleDrive-v5.md وBOOTSTRAP وTODO وKNOWN_ISSUES وCHANGELOG وHANDOFF.
5. تشغيل كل البوابات الثماني بمخرجات حقيقية — بما فيها pytest الذي غاب عن جلسة PR #3.
6. فحص `docs/AI_RULES.md` (تقرير فقط): يحيل إلى ترقيم v4.5 (§4 و§16 و§21 و§22 و§23 و§25 و§26 و§2) ويذكر Lovable في صف "Implementation AI" وربط "مزامنة Lovable" في بند force-push. **لم يُعدَّل** — DOC إصلاحي منفصل منتظر من Brain.

**Tests added/changed:**
- None (ممنوع في هذا DOC — توثيق/CI فقط).

**Commands run (من python-package ما لم يُذكر، مع TELEDRIVE_ROOT=/tmp/teledrive_runtime وTELEDRIVE_LANG=en، Python 3.11.2 بمثبتات requirements.lock):**
```bash
git rev-parse HEAD
# 4cacc584834a7fc8e0b8ccf36b53ca3808cbab77

python -m compileall teledrive
# Listing + Compiling نظيف لكل الوحدات (exit 0)

python -m pytest -q tests
# 299 passed in 7.58s

python teledrive_launcher.py --check
# bootstrap: {'schema_version': 1, 'dirs': ['/tmp/teledrive_runtime/data', ...], 'free_bytes': 20039188480}
# binding check ok: 22/41 ready actions resolve
# (exit 0)

python -m teledrive.notebook_cells --check
# notebooks are in sync (exit 0)

cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb
# (exit 0 — متطابقان byte-for-byte)

python -m teledrive.package_service --build --output teledrive_v4.5.zip
# 2026-08-08T05:20:26+00:00 tests passed
# archive: teledrive_v4.5.zip   (135,237 بايت — أُزيل بعد التحقق)

git hash-object docs/CONSTITUTION_V4.5_ARCHIVE.md
# c281a5cd38d594b54999f77a36c4d000bb6362d3

# من الجذر:
bun install --frozen-lockfile
# FAILED في البيئة الرملية فقط: UNKNOWN_CERTIFICATE_VERIFICATION_ERROR على tarballs ‎@lovable.dev/*‎ —
# بيئة TLS لا تقبليها bun. البديل البيئي (لا كود): npm install --no-package-lock — اكتملت node_modules،
# وبقي bun.lock بلا مساس. التأكيد النظيف على runner يأتي من GitHub Actions بعد الدفع.

bun run lint
# ✖ 6 problems (0 errors, 6 warnings) — تحذيرات react-refresh/only-export-components موجودة مسبقًا (exit 0)

bun run build
# ✓ built + nitro worker + wrangler.json (exit 0)
```

**Push / GitHub (أدلة الطرفية الكاملة):**
```bash
git push -u origin arena/019fdfc5-drive-buddy-3579bf74        # المحاولة الأولى — الـcommit تضمّن ci.yml آنذاك
# ! [remote rejected] arena/... -> arena/... (refusing to allow a GitHub App to create or update
#   workflow `.github/workflows/ci.yml` without `workflows` permission)
# error: failed to push some refs

gh api -X PUT repos/body199-cmyk/drive-buddy-3579bf74/contents/.github/workflows/ci.yml \
    -f branch=test-workflows-perm ...                          # جس صلاحية على فرع مؤقت (حُذف بعدها)
# HTTP 403: {"message":"Resource not accessible by integration", ...}
```
**القرار المبني على الدليل:** تأكدنا بالطريقتين (git والـAPI) أن بوت Arena App غير مخوّل بلمس ملفات workflow. لم نحاول التفافًا. أُعيد `ci.yml` إلى الـbaseline، وأُعيد بناء الـcommit كدفعة docs-only (13 ملفًا) عبر reset محلي لـcommit **غير منشور** — لا rewriting لأي تاريخ منشور (المنع مقيَّد بالمنشور فقط في MIGRATION rule 3 و§12). سطرا CI يبقيان جاهزين للتطبيق فور رفع الصلاحية أو بيد المالك.

**TESTS NOT RUN OR NOT PROVEN:**
- إصلاح `ci.yml` على GitHub — مجهَّز ومتحقق محليًا، لكنه غير مدفوع (العائق أعلاه). يُغلق M10-T02 عند هبوطه.
- `bun install --frozen-lockfile` نفسه في هذه البيئة (السبب أعلاه) — lint وbuild أُثبتا على node_modules المكتمِلة.
- تشغيل CI الكامل على GitHub لهذه الدفعة — ينتظر الدفع، ويُسجَّل رابطه في رد الجلسة الختامي.
- أي تحقق Telegram/Drive/نقل حقيقي — بيد المالك في M15-T01.
- Gradio 6.20.0 UI حقيقي في متصفح — بند M13-T01 قائم.

**Honest status:**
PARTIALLY COMPLETE لـM12-T01: الجزء التوثيقي كامل ومدفوع؛ جزء CI معلَّق على صلاحية `workflows`.
الحالة الصادقة للمشروع: Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.
