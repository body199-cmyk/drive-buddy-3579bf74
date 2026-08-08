# PHASE_13 — تصحيح AI_RULES وتنظيف docs وتوثيق السبب الجذري لانكسار CI (M12-T02)

**TASK ID:** M12-T02

**Repository URL, branch, commit:**
- Repo: `https://github.com/body199-cmyk/drive-buddy-3579bf74.git`
- Branch: `arena/019fdff4-drive-buddy-3579bf74` (انحراف موثَّق: DOC اقترح `arena/M12-T02-docs-hygiene` لكن جلسة Arena مثبَّتة على هذا الفرع ولا تسمح بتبديله)
- Base SHA: `ad3a454f40b8d4c8dd051f5ba94ceb0c7cd6c250` (merge PR #5)
- Result SHA: رأس الفرع بعد commit هذا التقرير نفسه — يُستخرج بـ `git log -1 --format=%H`؛ يستحيل رياضيًا تضمين SHA الـcommit داخل شجرته ذاتها، والاسم الكامل مسجَّل في متن الـPR ورد الجلسة
- Date: 2026-08-08

**Goal:**
- تصحيح `docs/AI_RULES.md` لترقيم أقسام v5.0 وإزالة Lovable كمنفّذ.
- حذف `docs/pic for frontend` (تلوث من commit المالك `afde5fe`).
- تحديث KNOWN_ISSUES وTODO بواقع CI الجديد: السبب الجذري لانكسار CI وحاجز صلاحية `workflows`.
- تسجيل السبب الجذري لانكسار CI في PHASE_13 كمرجع دائم.

**CI REVIVAL STATUS:**
- Owner part (A) applied: **NO** (ci.yml لا يزال يحوي `runner.temp` في السطر 16)
- First run that actually started: **NONE**
- Run duration: **0s** (workflow لا يزال غير صالح)
- Python job: **NOT RUN** (workflow غير صالح)
- Frontend job: **NOT RUN** (workflow غير صالح)
- First real failure surfaced: **N/A — workflow لا يبدأ أصلًا**

**السبب الجذري لانكسار CI (اكتشاف M12-T01، توثيق M12-T02):**

سياق `runner` **غير متاح** على مستوى `jobs.<id>.env`. المتاح هناك: `github`, `needs`, `strategy`, `matrix`, `vars`, `secrets`, `inputs` فقط. السطر 16 من ci.yml الحالي:

```yaml
TELEDRIVE_ROOT: ${{ runner.temp }}/teledrive_runtime
```

ينتج ملف workflow غير صالح، فيفشل GitHub Actions **قبل** تخصيص أي runner، في صفر ثانية، في **كل** تشغيل منذ commit `2cc5747` الذي أدخل هذا السطر. آخر تشغيل أخضر معروف (run `30496659877`) كان يستخدم `${{ github.workspace }}`.

**الأثر الحقيقي:** بوابات §16 (compileall, pytest, launcher, notebook, cmp, package build, bun lint, bun build) لم تُشغَّل على GitHub Actions ولا مرة منذ إدخال هذا السطر. كل ما لدينا من نتائج هو مخرجات محلية. أي ادعاء "CI أخضر" سابق كان غير قائم على تشغيل فعلي.

**حاجز صلاحية المنصة:**

تطبيق GitHub الخاص بـArena لا يملك صلاحية `workflows`:
- `git push` → `remote rejected: refusing to allow a GitHub App to create or update workflow .github/workflows/ci.yml without workflows permission`
- REST API PUT contents → `HTTP 403: Resource not accessible by integration`

هذا يفسر أيضًا لماذا لم يصل تعديل CI المزعوم في PR #3 إطلاقًا — PR #3 ادعى تحديث CI إلى v4.5 لكن شجرة `.github` عند merge (blob `86abde40`) مطابقة تمامًا لما قبل PR #3 (blob `ci.yml` = `5dec51e`).

**Baseline check (الخطوة 0 من DOC، قبل أي تعديل):**

```
git status --short    → (empty — clean tree)
git branch --show-current → arena/019fdff4-drive-buddy-3579bf74
git rev-parse HEAD    → ad3a454f40b8d4c8dd051f5ba94ceb0c7cd6c250
git log -5 --oneline --decorate → ad3a454 (HEAD -> arena/..., origin/main, main) Merge pull request #5
find docs -maxdepth 2 -type f | sort → كل ملفات §7 موجودة + "docs/pic for frontend" (التلوث المستهدف)
git log --oneline -1 -- .github/workflows/ci.yml → (ci.yml لم يتغير منذ commit سابق)
grep -n "teledrive_v\|runner.temp\|github.workspace" .github/workflows/ci.yml:
  16:      TELEDRIVE_ROOT: ${{ runner.temp }}/teledrive_runtime
  59:        run: python -m teledrive.package_service --build --output teledrive_v3.1.zip
  64:          path: python-package/teledrive_v3.1.zip
```

HEAD = `ad3a454f40b8d4c8dd051f5ba94ceb0c7cd6c250` — مطابق للـbaseline المطلوب (merge PR #5). الجزء (أ) من DOC لم يُنفَّذ بعد.

**Files inspected:**
- `.github/workflows/ci.yml` (blob `5dec51e` — لم يُلمس، خارج النطاق)
- `docs/AI_RULES.md` (الاستبدال الكامل)
- `docs/KNOWN_ISSUES.md` (تحديث #8 و#13، إضافة #14 و#15)
- `docs/TODO.md` (تحديث M10-T02 وM12-T01، إضافة M12-T02، إعادة صياغة M13-T01)
- `docs/ACTIVE_TASK.md` (استبدال لـM12-T02)
- `docs/AI_HANDOFF.md` (استبدال لهذه الجلسة)
- `docs/CHANGELOG.md` (إضافة مدخل M12-T02)
- `docs/CONSTITUTION.md` (فحص فقط — لم يُلمس)
- `docs/pic for frontend` (الحذف)

**Files created:**
- `docs/PHASE_REPORTS/PHASE_13.md` (هذا التقرير)

**Files changed:**
- `docs/AI_RULES.md`: استبدال كامل — ترقيم أقسام v5.0 (§2, §3, §7, §9.7, §10, §11, §17, §18, §20)، الأدوار §3 (Brain/LM Arena Agent/Owner)، Lovable يُذكر فقط في فقرة "خرج نهائيًا" وملاحظة المرآة التقنية، جدول قيود المنصة مضاف.
- `docs/KNOWN_ISSUES.md`: #8 و#13 مُحدَّثان بملاحظة "بانتظار تطبيق المالك — قيد صلاحية workflows" والسبب الجذري الكامل؛ #14 جديد (تلوث `docs/pic for frontend` ✅ حُذف)؛ #15 جديد (صلاحية المنصة مفتوحة بنيويًا).
- `docs/TODO.md`: M10-T02 بصياغة أوضح؛ M12-T01 → PARTIALLY COMPLETE؛ M12-T02 مضاف ACTIVE؛ M13-T01 أعيدت صياغتها إلى "تحليل نتائج أول تشغيل CI حقيقي وإصلاح ما يظهر" مع تنبيه أنها بلا معنى قبل إصلاح ci.yml.
- `docs/ACTIVE_TASK.md`: M12-T02 مع الفرع والـSHA الحقيقيين.
- `docs/AI_HANDOFF.md`: استبدال كامل بمخرجات هذه الجلسة.
- `docs/CHANGELOG.md`: مدخل [M12-T02] أعلى المدخلات.

**Files deleted:**
- `docs/pic for frontend` (1 بايت — commit المالك `afde5fe` "Create pic for frontend" أنشأ ملفًا فارغًا داخل بيت الذاكرة القانوني)

**Protected files unchanged (FORBIDDEN per DOC §3.8):**
- `.github/**` — الجزء (أ) بيد المالك
- `docs/CONSTITUTION.md` — لم يتغير حرف واحد
- `docs/CONSTITUTION_V4.5_ARCHIVE.md` — الأرشيف مجمَّد byte-exact
- `docs/PHASE_REPORTS/PHASE_0..12` — التقارير التاريخية لا تُعدَّل
- `python-package/**`, `public/**`, `src/**`, `package.json`, `bun.lock`, `AGENTS.md` — بلا لمس

**Implementation summary:**
1. فحص baseline وأكّد HEAD = `ad3a454` وكل ادعاءات DOC قبل أي كتابة.
2. حذف `docs/pic for frontend` عبر `git rm`.
3. استبدال `AI_RULES.md` بالكامل بالمحتوى المعتمد من DOC (ترقيم v5.0، بلا Lovable كمنفّذ، جدول قيود المنصة).
4. تحديث KNOWN_ISSUES: #8 و#13 بالسياق الجديد، #14 و#15 جديدان.
5. تحديث TODO: M12-T01 → PARTIALLY COMPLETE، M12-T02 مضاف، M13-T01 أعيدت صياغتها.
6. استبدال ACTIVE_TASK وAI_HANDOFF بالحقول الإلزامية.
7. إضافة مدخل CHANGELOG.
8. كتابة PHASE_13 مع السبب الجذري الكامل.
9. تشغيل كل بوابات §16 بمخرجات حقيقية.

**Tests added/changed:**
- None (ممنوع في هذا DOC — توثيق فقط).

**Commands run (من python-package ما لم يُذكر، مع TELEDRIVE_ROOT=/tmp/teledrive_runtime وTELEDRIVE_LANG=en، Python 3.11.2 بمثبتات requirements.lock):**
```bash
# Baseline
git rev-parse HEAD
# ad3a454f40b8d4c8dd051f5ba94ceb0c7cd6c250

git status --short
# (empty)

grep -n "teledrive_v\|runner.temp\|github.workspace" .github/workflows/ci.yml
# 16:      TELEDRIVE_ROOT: ${{ runner.temp }}/teledrive_runtime
# 59:        run: python -m teledrive.package_service --build --output teledrive_v3.1.zip
# 64:          path: python-package/teledrive_v3.1.zip

ls -la "docs/pic for frontend"
# -rw-r--r-- 1 user user 1 Aug  8 05:59 docs/pic for frontend

git rm "docs/pic for frontend"
# rm 'docs/pic for frontend'

# Gates (§16)
python -m compileall teledrive
# Listing + Compiling نظيف لكل الوحدات (exit 0)

python -m pytest -q tests
# 299 passed in 8.55s

python teledrive_launcher.py --check
# bootstrap ok schema=1 free=20694560768 loop=True
# binding check ok: 22/41 ready actions resolve
# (exit 0)

python -m teledrive.notebook_cells --check
# notebooks are in sync (exit 0)

cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb
# (exit 0 — متطابقان byte-for-byte)

python -m teledrive.package_service --build --output teledrive_v4.5.zip
# tests passed
# archive: teledrive_v4.5.zip (أُزيل بعد التحقق — artifact)

# من الجذر:
node node_modules/.bin/eslint .
# ✖ 6 problems (0 errors, 6 warnings) — تحذيرات react-refresh/only-export-components موجودة مسبقًا (exit 0)

node node_modules/.bin/vite build
# ✓ built in 302ms + nitro/wrangler output مكتمل (exit 0)

# Verification
grep -n "Lovable" docs/AI_RULES.md
# السطر 14 فقط: فقرة "خرج نهائيًا" + ملاحظة المرآة ✅

grep -n "§2[0-9]" docs/AI_RULES.md
# §20 فقط (v5.0 stop conditions) — لا §21-§26 ✅

ls "docs/pic for frontend" 2>/dev/null
# (لا شيء — OK: removed) ✅
```

**TESTS NOT RUN OR NOT PROVEN:**
- بوابات CI على GitHub — **لا تعمل حاليًا على أي فرع**: workflow غير صالح بسبب `runner.temp` في job-env. الجزء (أ) من DOC (استبدال ci.yml) بيد المالك ولم يُنفَّذ بعد.
- `bun install --frozen-lockfile` — bun غير متاح في هذه البيئة الرملية؛ lint وbuild أُثبتا على node_modules المكتمِلة مسبقًا.
- أي تحقق Telegram/Drive/نقل حقيقي — بيد المالك في M15-T01.
- Gradio 6.20.0 UI حقيقي في متصفح — بند M13-T01 قائم.

**Honest status:**
Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified. CI لا يزال ميتًا على GitHub — الجزء (أ) من DOC لم يُنفَّذ بعد.
