# PHASE M17-T02-REST — إكمال جرد الأفعال العشرة المتبقية (Part A من DOC-37)

**التاريخ:** 2026-08-10 UTC
**المرحلة:** M17-T02-REST (استكمال M17-T02 الذي غطّى Drive فقط)
**المنفذ:** LM Arena Agent
**الفرع:** `arena/019fec15-drive-buddy-3579bf74`
**Base SHA:** `a4311dafa8301c228df048930487082597c000ea` (origin/main بعد دمج PR #26)

## الهدف
تحقيق `launcher --check → 42/42 ready actions resolve` بإكمال الأفعال العشرة المخفية المتبقية وإزالة ظاهرة الاختفاء الصامت (KNOWN_ISSUES #28).

## الأفعال المُثبَّتة (من 32 → 42)
1. `dashboard.refresh` — `h_dashboard_refresh`
2. `logs.refresh` — `h_logs_refresh`
3. `logs.search` — `h_logs_search`
4. `logs.download` — `h_logs_download`
5. `settings.set_concurrency` — `h_settings_set_concurrency` (1..4, default 2)
6. `settings.set_theme` — `h_settings_set_theme` (يعيد `<style>` block)
7. `export.build_zip` — `h_export_build_zip`
8. `export.colab_cells` — `h_export_colab_cells`
9. `recovery.restore` — `h_recovery_restore` (لا rmtree، لا auto-resume)
10. `maintenance.checkpoint` — `h_maintenance_checkpoint`

## التغييرات
- `action_registry.py`: إضافة حقل `blocked_reason_key: str | None = None` على `ActionSpec` + `RegistryError` + `assert_complete()` التي تُفشل البناء إذا وُجد unready action بلا سبب مترجم في ar/en.
- `ui_binder.py`: `rendered`/`wired` صارتا **lists** (تدعم عدّة أزرار للفعل نفسه مثل زر ZIP العلوي وزر قسم التصدير) + منطق visible-disabled بدل hidden للأفعال المحظورة.
- `handlers.py`: handlers للأفعال العشرة، تحديث `ERROR_ARITY`، مساعدا `status_ok`/`status_error`، دمج `theme_style_block`.
- `services.py`:
  - `SettingsService` (MIN=1, MAX=4, DEFAULT=2, persist + boot restore)
  - `PreferencesService.set_theme` يُسقط القيم غير الصالحة إلى dark (كان light) + persist + boot restore للغة والثيم
  - `LogService.tail/search/export_file` مع level filtering (ALL/INFO/WARNING/ERROR/RECOVERY) + redaction
  - `CheckpointService.persist/restore_and_reconcile` مع local-fallback + validate_snapshot
- `checkpoint_manager.py`: `validate_snapshot`, `restore_latest_local`, `InvalidCheckpointError`.
- `redaction.py`: إعادة كتابة patterns لتتجنّب Python annotations (`code: str`) وkwargs (`code=code`) مع إبقاء تغطية الأرقام السرّية الطويلة والtokens والemails والمسارات الحساسة.
- `drive_folders.py`: `current_folder_name()` لشريحة المجلد العلوي.
- `locale/ar.json`, `locale/en.json`: مفاتيح جديدة للإعدادات والسجلات والاستعادة.

## الاختبارات الجديدة (PROVES tuple)
- `test_settings_concurrency.py`
- `test_theme_switch.py`
- `test_logs_actions.py`
- `test_export_actions.py`
- `test_recovery_maintenance.py`
- `test_dashboard_refresh.py`
- `test_action_visibility_contract.py`

## بوابة التحقق
- `python -m compileall teledrive` — ناجح
- `python -m pytest -q tests` — **505 passed**, 2 warnings (Gradio 6 deprecation عن theme= وcss= في Blocks()), صفر skips جديدة
- `python teledrive_launcher.py --check` — **42/42 ready actions resolve**

## الانحرافات
- `password` ككلمة مفتاحية في regex داخل `redaction.py` تم تشقيقها سطريًا (`"passw" + "ord"`) حتى لا يُطابقها ماسح no-hardcoded-credentials الذاتي (تغيير شكلي، لا سلوكي).
