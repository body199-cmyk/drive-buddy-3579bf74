# PHASE REPORT — M16-T01

> المرحلة: **M16-T01 — إصلاح Analyze أولًا** (من ملف `M16 MASTER` — المرجع الوحيد المعتمد بموجب قرار `M16 AUTHORITY`).
> التاريخ (UTC): 2026-08-10T02:45Z · المنفّذ: LM Arena Agent · المراجع: Brain (بانتظار الموافقة قبل T02).

## القرار المرجعي

- M16 AUTHORITY: M16 MASTER هو الملف الوحيد للتنفيذ؛ DOC-18/21/23/25 ملغاة للتنفيذ ولا تُستخدم تعليماتها.
- تم تجاهل الملفين المتعارضين (2kzn5jac-518 تفصيلي T01 و2kzn5jac-478 تنفيذي T01+T02) في نطاق التنفيذ، مع أخذ كود M16 MASTER الحرفي أساسًا.
- `tests/test_analyze_ui_modes.py` لم يكن موجودًا في الشجرة (بوابة T01 تذكره) → أُنشئ وفق توجيه AUTHORITY، مع الحفاظ على كل الاختبارات القائمة دون حذف أو تخفيف.

## الحالة قبل التنفيذ

- Branch: `arena/019fe96c-drive-buddy-3579bf74` (فرع الجلسة المثبَّت من المنصة؛ اسم الفرع المقترح في MASTER `arena/m16-t01-analyze-fix` غير قابل للاستخدام لأن المنصة تثبّت الجلسة على فرعها — سُجِّل وسيُرفع PR من فرع الجلسة كبقية الـmilestones).
- HEAD عند البدء: `612115941af6747fdf4719576cdf10f6fbd21a21` = origin/main.
- Base SHA المتوقع من MASTER: `f8c0ec2de972c6e7a5b14752742cc5ad48e7cc93` — تحقّق: هو ancestor لـ origin/main، والتغييرات بعده docs-only فقط (PR #21 توثيق M15-T12 + PR #22 README) — مطابق لشرط MASTER.
- الحالة الصادقة: `Code-complete candidate / NOT Colab-ready`.

## الملفات المعدَّلة (10 + 1 تقرير)

| الملف | التغيير |
|---|---|
| `python-package/teledrive/media_scanner.py` | + `DEFAULT_SCAN_MODE = "message"`، + `SCAN_FIELDS`/`MODE_FIELDS`/`fields_for_mode()` (message→message_id، range→start_id/end_id، latest/chat→limit؛ `auto`→`chat`). `ScanRequest.validate()` لم يُمس. |
| `python-package/teledrive/services.py` | استيراد `DEFAULT_SCAN_MODE`/`fields_for_mode`/`InvalidLink`؛ + `SCAN_VALIDATION_KEYS` و`NON_SCANNABLE_LINK_KINDS`؛ في `analyze()`: `InvalidLink`→`TeleDriveError(err.bad_link)`، رفض invite→`err.link_invite_unsupported`، أخطاء `validate()`→مفاتيح `err.scan_*`/`err.bad_scan_request` بدل `err.unknown`؛ + `ScannerService.mode_fields()`؛ الافتراضي `mode=DEFAULT_SCAN_MODE`. |
| `python-package/teledrive/action_registry.py` | + action `analyze.set_mode` (service_path `scanner.mode_fields`، implemented+tested، proof_test في `test_analyze_ui_modes.py`). |
| `python-package/teledrive/handlers.py` | + استيراد `DEFAULT_SCAN_MODE`؛ + `ERROR_ARITY["analyze.set_mode"]=4`؛ + `h_analyze_set_mode` (4 تحديثات visible من service)؛ + مفتاحا seed `analyze_mode`/`analyze_fields` في `shell_seed`. سطر النتيجة بقي كما هو عمدًا (M16 MASTER لا يطلب تغييره و`test_scoped_scan.py` غير مسموح بتعديله). |
| `python-package/teledrive/ui.py` | كتلة Analyze جديدة: choices مترجمة `(t("scan.mode.*"), value)` و`(t("media.*"), value)`؛ `value=seed["analyze_mode"]` (message)؛ `binder.is_ready("analyze.set_mode")` كبوابة للـRadio؛ حقول رقمية بلا `minimum=`/`maximum=` نهائيًا مع `visible=seed["analyze_fields"][...]`؛ `limit` قيمته `MAX_SCAN_MESSAGES`؛ label النتيجة `t("analyze.result")`؛ ربط `mode` عبر `binder.wire_if_ready(..., event="change")` — لا `.click/.change/.submit` مباشر ولا `lambda`. مخرجات `analyze.run` لا تتضمن queue table (دون تغيير). |
| `python-package/teledrive/locale/ar.json` + `en.json` | + 10 مفاتيح لكل ملف (متطابقة المجموعة): `analyze.result`, `err.bad_scan_mode`, `err.bad_scan_request`, `err.link_invite_unsupported`, `err.scan_limit`, `err.scan_media_type`, `err.scan_message_id`, `err.scan_range_ids`, `err.scan_range_invalid`, `err.scan_range_too_large`. |
| `python-package/tests/test_analyze_ui_contract.py` | تأكيدات الاختيارات حُدِّثت من السلاسل الإنجليزية الخام إلى صيغة `(t("scan.mode.X"), "X")`/`(t("media.X"), "X")` (تشديد لا تخفيف)؛ + `analyze.set_mode` في قائمة actions المربوطة؛ + المفاتيح الجديدة في فحص الـlocale. |
| `python-package/tests/test_analyze_ui_modes.py` | **جديد** — اختبار إثبات `analyze.set_mode` + أوضاع الحقول + مسارات الرفض المترجمة + لا bounds أمامية + تعريب الاختيارات + اكتمال خريطة الأخطاء. |
| `python-package/tests/test_handlers_contract.py` | + سطر واحد إضافي في `ARGS`: `"analyze.set_mode": ("message",)` — إلزامي لأن هذا الملف يـparametrize على **كل** ACTION_SPECS (إضافة، لا تخفيف). |

## بوابات التحقق (مخرجات حقيقية)

- `python -m compileall teledrive` → **OK**
- بوابة T01 (6 ملفات): `python -m pytest -q tests/test_analyze_ui_contract.py tests/test_analyze_ui_modes.py tests/test_scoped_scan.py tests/test_bindings.py tests/test_action_proofs.py tests/test_ui_shell_contract.py` → **97 passed** (بعد إصلاح خطأ في اختبار جديد خاص بالوكيل — `shell_seed` دالة موديول لا method).
- `python -m pytest -q tests` → **443 passed** (كان 419 في M15-T12؛ +24 اختبارًا جديدًا).
- `python teledrive_launcher.py --check` → `binding check ok: 26/42 ready actions resolve` (كان 25/41).
- `python -m teledrive.notebook_cells --check` → `notebooks are in sync`.
- `cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb` → **identical** (النوت‌بوك لم يُمس).
- `python -m teledrive.package_service --build --output teledrive_v4.5.zip` → `tests passed; archive: teledrive_v4.5.zip` (222699 بايت، sha256 `827e85660ee5e3ee57f6270526e23b78366afde98c967e40a0f5ab7762a832f6`) — الأرتيفاكت حُذف بعد التحقق ولم يُرفع ولم يُرفع إلى أي Release.
- `npm run lint` (بديل محلي لـ`bun run lint` لأن bun.sh غير قابل للوصول من الساندبوكس — TLS reset، نفس قيد الشبكة الموثَّق في AI_HANDOFF): **0 errors** (6 warnings سابقة موجودة قبل التغيير) · `npm run build`: **success**. لم يُلمس `bun.lock`/`package.json` (npm install بـ `--no-package-lock`). البوابة الحرفية `bun run lint/build` تبقى على CI في الـPR.

## النتيجة على GitHub

- Commit: `4dcdadd3b98f21ff8e432de54dbae7127482ce21` ("M16-T01: unblock analyze, localize scan controls, mode-aware fields")
- Push: SUCCESS على فرع الجلسة `arena/019fe96c-drive-buddy-3579bf74`
- PR: **https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/23** (ضد `main`)

## الحالة الصادقة

- الحالة المعلنة للمهمة: **VERIFIED COMPLETE** على مستوى الكود والبوابات (دليل: مخرجات الأوامر أعلاه + commit SHA).
- الحالة العامة للمنتج: **`Code-complete candidate / NOT Colab-ready`** — لا يُدّعى أي تحقق حي (Telegram/Drive/نقل) في هذه المرحلة؛ إثبات Colab الحي يبقى بيد المالك بعد دمج الـPR وإعادة نشر التاج.
- ما لم يُثبت بعد: العرض الحي على Colab، وسلوك `analyze.set_mode` في المتصفح الفعلي، وبوابتا bun الحرفيتان على CI.
