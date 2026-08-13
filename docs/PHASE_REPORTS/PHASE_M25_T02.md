# PHASE_M25_T02 — تحديث تلقائي للصفحة كاملة أثناء النقل (نبض هادئ)

- **TASK ID:** `M25-T02`
- **الفرع:** `arena/019ff87b-drive-buddy-3579bf74`
- **المرجع:** تعليمة المالك المباشرة 2026-08-13 (بلاغ: «شريط التقدم مش بيتحدّث لوحده إلا بعد زر تحديث» ثم «خلّي الصفحة كلها تتحدّث مش الشريط بس… زي زرار التحديث»).

## المشكلة

جسر Gradio الحالي لقطةٌ لا بثٌّ: React لا يجلب حالة جديدة إلا عند طلب صريح (زر `تحديث`/بدء/إيقاف…). أثناء النقل يتجمّد الشريط وكل أرقام الصفحة على آخر لقطة حتى يضغط المستخدم `تحديث` يدويًا. هذا تصميم الجسر السابق، وليس عطل نقل في Python.

## الحل

1. **نبض هادئ في React** (`TeleDriveSandbox.tsx` + `viewModel.ts`):
   - مؤقّت كل 2000ms ينادي `queue.refresh` عبر `bridge.request` مباشرة (لا يمر عبر `run()`)، فيحدّث **لقطة LiveUiState كاملة** — أي كل الأقسام: chips الحالة، المجلد، المحرك، الحصة، الطابور، التقدم، المرشّحون — تمامًا كضغطة `تحديث`، بلا وميض notice ولا spinner busy.
   - `hasActiveTransfer()` يبوّب النبض: يعمل فقط عندما يكون المحرك `running` أو يوجد صف بحالة in-flight (`Downloading/Uploading/Verifying/UploadedPendingCheckpoint`). لا حلقة خلفية دائمة.
   - حماية من التداخل (`pollInFlight` ref) وقراءة أحدث لقطة عبر `liveStateRef`.
2. **إصلاح داعم في Python** (`queue_manager.py`): المحرك كان يبقى `running` للأبد بعد انتهاء أول نقل (لا إعادة تعيين)، فيجعل النبض يستمر على طابور منتهٍ. أُضيف `_on_run_done` callback يعيد التسمية إلى `idle` عند انتهاء drain، ولا يمسّ `paused`/`stopped`.

## الملفات

| ملف | التغيير |
|---|---|
| `src/components/teleDrive/TeleDriveSandbox.tsx` | `AUTO_REFRESH_INTERVAL_MS` + مؤقّت نبض + `pollInFlight`/`liveStateRef` |
| `src/components/teleDrive/viewModel.ts` | `hasActiveTransfer()` + `IN_FLIGHT_STATES` |
| `python-package/teledrive/queue_manager.py` | `_on_run_done` + `add_done_callback` في `start_selected` |
| `tests/teledrive-sandbox.contract.test.mjs` | test 23 (بوابة النبض) + test 24 (عقد المصدر) |
| `python-package/tests/test_phase_3.py` | اختبارا `_on_run_done` |

## البوابات المحلية

- Python: `664 passed` (كان 662) — `pytest -q tests`.
- Launcher: `48/48 ready actions resolve` (`teledrive_launcher.py --check`).
- Notebooks: `notebooks are in sync` (`python -m teledrive.notebook_cells --check`).
- Frontend contracts: `24/24` (`node --test tests/teledrive-sandbox.contract.test.mjs`).
- Type-check: `tsc --noEmit --strict` على `bridgeTypes/viewModel/TeleDriveSandbox` PASS.
- Prettier: نظيف للملفات المعدّلة (استثناء السطر الجاهز الموجود مسبقًا في `viewModel.ts` المُعطَّل بـ`eslint-disable prettier/prettier`).
- `bun run lint` / `bun run build`: **لم تُشغَّل محليًا** — حاجز شبكة الساندبوكس (`@lovable.dev/*` من registry خاص)؛ تُنفَّذ في CI على الـPR (KNOWN_ISSUES #37).

## محمي لم يُمس

notebooks / notebook generator / telegram_auth / transfer_manager / database & migrations / requirements.* / bun.lock / package.json / workflows.

## الحالة الصادقة

**Code-complete candidate + Fake-tested.** ليس Colab-ready ولا Complete. الإثبات الحي (نقل حقيقي بشريط يتحدّث ذاتيًا في Colab) بيد المالك بعد إعادة نشر التاج (KNOWN_ISSUES #27).
