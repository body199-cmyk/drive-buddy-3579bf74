# PHASE_16 — إصلاح إجراءات اختيار العناصر واختبارات الربط الحقيقية (M13-T03)

**TASK ID:** `M13-T03`
**العنوان:** إصلاح `analyze.select_all` و`analyze.clear_selection` مع اختبارات binding حقيقية
**الحالة:** `VERIFIED COMPLETE` — أضيفت اختبارات إثبات حقيقية في `python-package/tests/test_selection.py` ورُقي إجرائي التحديد إلى `READY` في `action_registry.py` دون تعديل كود المنتج (لثبوت صحته).
**التاريخ (UTC):** 2026-08-08
**المستودع:** `https://github.com/body199-cmyk/drive-buddy-3579bf74.git`

## 1. Baseline والاستئناف

| الحقل | القيمة |
|---|---|
| Base SHA المعتمد | `86005ff6ef5eb55ddfd639f306c85ff17acadc4c` |
| Actual start SHA | `86005ff6ef5eb55ddfd639f306c85ff17acadc4c` |
| الفرع المفحوص | `arena/019fe024-drive-buddy-3579bf74` |
| الشجرة قبل العمل | نظيفة؛ `git status --short` لم يطبع ملفات |
| Previous PR | #8 — `M13-T02: audit Action Registry and classify unready actions` |
| Previous PR status | `MERGED` إلى `main` |
| Merge commit | `86005ff6ef5eb55ddfd639f306c85ff17acadc4c` |
| آخر CI أخضر لـ PR #8 | Run [`31244752412`](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/31244752412)، `success` |
| قرار baseline | `RESUME_VERIFIED`: PR السابق مدموج، HEAD هو merge SHA الفعلي `86005ff...`، والشجرة مطابقة لـ M13-T03 |

لم يُعاد تنفيذ M13-T02 ولم تُعدَّل workflow أو أي ملفات ممنوعة. الفرع الجانبي الثابت لهذه الجلسة هو `arena/019fe024-drive-buddy-3579bf74`؛ لم يتم إنشاء أو دفع فرع آخر.

## 2. نطاق المهمة وما نُفّذ فعليًا

المطلوب كان معالجة أصغر مجموعة مترابطة فقط:
- `analyze.select_all`
- `analyze.clear_selection`

خطوات التنفيذ المنجزة:
1. فحصنا المسارات الحالية للإجرائين في `handlers.py` (`h_analyze_select_all` و`h_analyze_clear_selection`)، والربط في `ui.py` / `ui_binder.py`، وخدمة المجال في `SelectionService` (`services.py`).
2. ثبت أن التنفيذ الحالي في كود المنتج صحيح تمامًا ولا يحتاج أي تغيير:
   - `select_all` يحدد العناصر المرئية فقط (`self.visible()`) ويعيد `len(selected)` و`rows_for(self.ctx.selection.visible())`.
   - `clear_selection` يمسح التحديد (`self.selected_ids = set()`) دون حذف العناصر أو تغيير العناصر المرئية، ويعيد الصفوف المرئية دون تغيير.
   - كلاهما يمر عبر `ctx.resolve(spec.service_path)`، كما أن معالجة الأخطاء (`_error` في `handlers.py`) ترجع الطول الصحيح (`2`) ولا تسرب أسرارًا.
3. أضفنا ملف اختبارات إثبات حقيقية `python-package/tests/test_selection.py` يحتوي على 5 اختبارات:
   - `test_select_all_visible_only`: يختبر أن `select_all` يحدد العناصر المرئية فقط مع فلترة العناصر المخفية ويعيد الصفوف المرئية بدقة.
   - `test_clear_selection_preserves_items_and_visible_rows`: يختبر أن `clear_selection` يمسح التحديد ويحتفظ بقائمة العناصر والصفوف المرئية كاملة.
   - `test_select_all_and_clear_resolve_through_ctx`: يستخدم جاسوسًا (spy) ليثبت أن استدعاء الـ handler يمر عبر `ctx.resolve` ويصل إلى `SelectionService.select_all_visible` و`SelectionService.clear`.
   - `test_error_path_arity_and_redaction`: يختبر مسار الخطأ (`RuntimeError` و`TeleDriveError`) ويؤكد إرجاع الطول الصحيح (`tuple` بطول 2) وعدم تسريب أي أسرار أو tracebacks.
   - `test_select_all_and_clear_empty_candidates`: يختبر الإجرائين في حالة عدم وجود عناصر مرشحة.
4. وفقًا للبند 6 من معايير القبول، قمنا بترقية إجرائي التحديد في `python-package/teledrive/action_registry.py` إلى `tested=True` وربطنا `proof_test` بدقة:
   - `analyze.select_all` ← `tests/test_selection.py::test_select_all_visible_only`
   - `analyze.clear_selection` ← `tests/test_selection.py::test_clear_selection_preserves_items_and_visible_rows`
5. لم نلمس أي كود آخر ولم نعدل flags لأي إجراء آخر من الإجراءات غير المختبرة.

## 3. ملخص Action Registry المحدَّث

بعد إثبات وترقية `analyze.select_all` و`analyze.clear_selection`:

- `ACTION_COUNT = 41`
- `READY_COUNT = 24` (بزيادة 2 بعد أن كانت 22)
- `UNREADY_COUNT = 17` (تناقصت من 19)
- `BLOCKED = 6` (Drive integration live gate)
- `NOT_TESTED = 11` (تناقصت من 13 إلى 11)
- `DEAD_CONTROL = 0`
- `NOT_IMPLEMENTED = 0`
- `NOT_WIRED = 0`

| Section | Total | READY | BLOCKED | NOT_TESTED |
|---|---:|---:|---:|---:|
| connection | 14 | 8 | 6 | 0 |
| analyze | 5 | 4 | 0 | 1 |
| transfers | 11 | 11 | 0 | 0 |
| dashboard | 1 | 0 | 0 | 1 |
| logs | 3 | 0 | 0 | 3 |
| settings | 5 | 1 | 0 | 4 |
| export | 2 | 0 | 0 | 2 |
| **الإجمالي** | **41** | **24** | **6** | **11** |

## 4. مخرجات التحقق الفعلية

### 4.1 بوابات الحزمة (`python-package`)

تم تشغيل كل البوابات المحلية المطلوبة بنجاح:

- `python3 -m compileall -q teledrive`: ناجح دون أخطاء.
- `python3 -m pytest -q tests`:
  ```text
  ........................................................................ [ 23%]
  ........................................................................ [ 47%]
  ........................................................................ [ 70%]
  ........................................................................ [ 94%]
  ..................                                                       [100%]
  306 passed in 8.66s
  ```
  *(تم اجتياز 306 اختبارات، بزيادة 7 اختبارات عن 299 في baseline: 5 في `test_selection.py` و 2 إضافية في `test_action_proofs.py`).*
- `python3 teledrive_launcher.py --check`:
  ```text
  bootstrap: {'schema_version': 1, 'dirs': ['/tmp/teledrive_runtime/data', ...], 'free_bytes': ...}
  binding check ok: 24/41 ready actions resolve
  ```
  *(تأكيد ارتقاء عدد الإجراءات الجاهزة إلى 24/41).*
- `python3 -m teledrive.notebook_cells --check`:
  ```text
  notebooks are in sync
  ```
- `cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb`: متطابقان تمامًا.
- `python3 -m teledrive.package_service --build --output teledrive_v4.5.zip`:
  ```text
  archive: teledrive_v4.5.zip
  ```
  *(تم بناء الحزمة بنجاح).*

## 5. ما لم يُشغّل أو لم يُثبت (`TESTS NOT RUN OR NOT PROVEN`)

- لم يُختبر تشغيل حقيقي على Google Colab (Telegram حي + Google Drive حي + نقل ملف حقيقي + shutdown/recovery/logs الحية). هذا ما زال مملوكًا للمالك في M15-T01.
- لم تُشغّل `bun run lint` أو `bun run build` محليًا لعدم توفر أمر `bun` في بيئة نظام الأوامر؛ الاعتماد هو آخر CI أخضر Run `31244752412` وسيقوم CI الخاص بالـ PR بتشغيلها على GitHub Actions.
- لم تُبنَ Gradio UI في browser/Colab حقيقي؛ binding evidence هو static/contract tests واختبارات خدمة حقيقية.
- الحالة الصادقة للمشروع تبقى دون تغيير: `Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.`

## 6. حدود المهمة والملفات

### Files created
- `python-package/tests/test_selection.py`
- `docs/PHASE_REPORTS/PHASE_16.md`

### Files modified
- `python-package/teledrive/action_registry.py` (ترقية إجرائي التحديد فقط)
- `docs/TODO.md`
- `docs/KNOWN_ISSUES.md`
- `docs/AI_HANDOFF.md`
- `docs/ACTIVE_TASK.md`
- `docs/CHANGELOG.md`

### Files deleted
- لا شيء.

### ممنوعات لم تُمس
`.github/workflows/ci.yml`, `docs/CONSTITUTION.md`, `docs/CONSTITUTION_V4.5_ARCHIVE.md`, `docs/PHASE_REPORTS/PHASE_10.md`, `requirements*.txt`, `bun.lock`, `public/**`, `src/**`.

## 7. Git / التقرير العام

```text
TASK/PHASE: M13-T03 / PHASE_16
TITLE: إصلاح analyze.select_all وanalyze.clear_selection مع اختبارات binding حقيقية
STATUS: VERIFIED COMPLETE
BASE SHA: 86005ff6ef5eb55ddfd639f306c85ff17acadc4c
ACTUAL START SHA: 86005ff6ef5eb55ddfd639f306c85ff17acadc4c
RESULT SHA: (سيُسجَّل بعد الـ commit الفعلي في التقرير النهائي)
BRANCH: arena/019fe024-drive-buddy-3579bf74
FILES CREATED: python-package/tests/test_selection.py, docs/PHASE_REPORTS/PHASE_16.md
FILES MODIFIED: python-package/teledrive/action_registry.py, docs/TODO.md, docs/KNOWN_ISSUES.md, docs/AI_HANDOFF.md, docs/ACTIVE_TASK.md, docs/CHANGELOG.md
FILES DELETED: none
CHANGES MADE: إضافة اختبارات إثبات حقيقية لإجرائي analyze.select_all وanalyze.clear_selection وترقيتهما إلى READY؛ 306 passed؛ 24/41 ready
CONSTITUTION CONFLICTS: none
UNRELATED CHANGES: none
SECURITY CHECK: لا credentials أو tokens أو session strings
HONEST PROJECT STATUS: Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.
NEXT SMALLEST STEP: مجموعة صغيرة أخرى مثبتة الحاجة من الإجراءات المتبقية (11 NOT_TESTED)، أو الانتقال إلى Colab الحقيقي (M15-T01).
```
