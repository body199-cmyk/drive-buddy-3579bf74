# UI_ACTION_INVENTORY — M17-T01: جرد صادق لكل الأزرار والإجراءات

> **TASK ID:** M17-T01 (من ملف M17 MASTER) — جرد فقط، **بلا أي تعديل على كود المنتج**.
> **Base SHA:** `4a2dac62e0aa57092100d35a1726d464b742e48c` (= `origin/main` = merge M16-T01 عبر PR #23)
> **الفرع:** `arena/019febba-drive-buddy-3579bf74` (فرع الجلسة المثبَّت من المنصة)
> **التاريخ (UTC):** 2026-08-10
> **الحالة:** `inventory complete — awaiting Brain approval before M17-T02`

## 1) منهجية الجرد ومصدر كل عمود

| العمود | مصدر الحقيقة |
|---|---|
| `action_id`, `section`, `label_key`, `handler_name`, `service_path`, `implemented`, `tested`, `proof_test` | `teledrive/action_registry.py` (`ACTION_SPECS`، 42 عنصرًا) |
| `rendered_in_ui` | استدعاء `binder.button(gr, ...)` أو بوابة `binder.is_ready(...)` في `teledrive/ui.py` — مثبت بـ `tests/test_bindings.py::test_ui_module_renders_every_declared_action` |
| `wired_in_ui` | وجود call-site عبر `binder.wire_if_ready` في `ui.py` — مثبت بـ `test_ui_module_wires_exactly_the_ready_actions`؛ **التفعيل الفعلي وقت التشغيل للإجراءات ready فقط** (الصريح في `ui_binder.py`) |
| `visible_at_first_render` | فحص مباشر لـ `ui.py`: `binder.button` يجعل الإجراء غير الجاهز `visible=False, interactive=False`؛ لوحتا OTP/2FA مخفيتان حتى آلة الحالة؛ accordions مطوية `open=False` |
| `handler_resolves_on_context` | `tests/test_bindings.py::test_every_spec_resolves_on_the_live_context` + `test_every_spec_has_a_named_decorated_handler` + تشغيل يدوي لـ `ctx.resolve()` على الـ42 مسارًا |
| `expected_output_arity` | `teledrive/handlers.py::ERROR_ARITY` (والافتراضي `DEFAULT_QUEUE_ARITY=2`) — مثبت بـ `test_ui_shell_contract.py::test_outputs_match_handler_arity_for_every_wired_action` |
| `requires_live_colab` | حكم موثَّق: هل الإثبات الحقيقي (لا الوهمي) يتطلب Colab حيًا (Telegram/Drive) |
| `current_blocker`, `recommended_fix` | تحليل هذه الجلسة؛ يعكس قاعدة الدستور 4A.1: لا زر ظاهر بلا `implemented+tested` و`proof_test` |

**فحص ui.py:** لا `lambda` ولا `.click/.change/.submit` مباشرة (`grep` فارغ باستثناء سطر توثيقي). 39 `binder.button` + 3 بوابات `is_ready` = 42 إجراءً، و42 call-site لـ `wire_if_ready`.

## 2) ملخص الأرقام (كلها مثبتة بأوامر هذه الجلسة)

| المقياس | القيمة | الدليل |
|---|---|---|
| إجمالي الأفعال المعلنة | **42** | `len(ACTION_SPECS)` في التشغيل اليدوي |
| جاهزة (`implemented+tested`) | **26** | `launcher --check`: `26/42 ready actions resolve` |
| غير جاهزة (`implemented=True, tested=False`) | **16** | نفس التشغيل + `action_registry.unready_specs()` |
| `implemented=False` | **0** | لا يوجد أي spec غير منفَّذ |
| مفاتيح labels ناقصة في ar/en | **0** | فحص `i18n.load` على الـ42 `label_key` |
| handlers مفقودة/غير مزخرفة | **0** | `test_every_spec_has_a_named_decorated_handler` |
| service_paths لا تتحلل على context | **0** | `test_every_spec_resolves_on_the_live_context` |
| أزرار ميتة ظاهرة للمستخدم | **0** | `binder.button` يخفي غير الجاهز؛ `assert_complete`؛ اختبارات shell contract |
| بوابة T01 (3 ملفات اختبار) | **61 passed** | مخرجات خام أدناه |
| كامل الحزمة | **443 passed** | مخرجات خام أدناه |

## 3) الجدول A — هوية الإجراء وحقائق الكود (من `action_registry.py` + `handlers.py`)

| action_id | section | label_key | handler_name | service_path | implemented | tested | ready | proof_test | expected_output_arity |
|---|---|---|---|---|---|---|---|---|---|
| telegram.set_credentials | connection | btn.connect_telegram | h_telegram_set_credentials | telegram_auth.set_credentials | ✅ | ✅ | ✅ | tests/test_telegram_auth.py::test_happy_path_reuses_the_exact_phone_code_hash | 4 |
| telegram.send_code | connection | btn.send_code | h_telegram_send_code | telegram_auth.send_code | ✅ | ✅ | ✅ | tests/test_telegram_auth.py::test_duplicate_send_code_click_is_idempotent | 4 |
| telegram.resend_code | connection | btn.resend_code | h_telegram_resend_code | telegram_auth.resend_code | ✅ | ✅ | ✅ | tests/test_telegram_auth.py::test_resend_is_rate_limited | 4 |
| telegram.verify_code | connection | btn.verify | h_telegram_verify_code | telegram_auth.verify_code | ✅ | ✅ | ✅ | tests/test_telegram_auth.py::test_wrong_code_keeps_the_hash_and_does_not_resend | 4 |
| telegram.verify_password | connection | btn.verify_password | h_telegram_verify_password | telegram_auth.verify_password | ✅ | ✅ | ✅ | tests/test_telegram_auth.py::test_two_factor_uses_the_same_client_without_a_new_code | 4 |
| telegram.logout | connection | btn.logout | h_telegram_logout | telegram_auth.logout | ✅ | ✅ | ✅ | tests/test_telegram_auth.py::test_logout_clears_all_secret_state | 4 |
| telegram.status | connection | dash.telegram_status | h_telegram_status | telegram_auth.status | ✅ | ✅ | ✅ | tests/test_telegram_auth.py::test_status_never_exposes_the_full_phone | 4 |
| drive.connect | connection | btn.link_drive | h_drive_connect | drive_auth.connect | ✅ | ❌ | ❌ | — | 2 |
| drive.reconnect | connection | btn.drive_reconnect | h_drive_reconnect | drive_auth.reconnect | ✅ | ❌ | ❌ | — | 2 |
| drive.status | connection | dash.drive_status | h_drive_status | drive_auth.status | ✅ | ❌ | ❌ | — | 2 |
| drive.list_folders | connection | btn.drive_list_folders | h_drive_list_folders | drive_folders.list_children | ✅ | ❌ | ❌ | — | 2 |
| drive.create_folder | connection | btn.drive_create_folder | h_drive_create_folder | drive_folders.create | ✅ | ❌ | ❌ | — | 2 |
| drive.select_folder | connection | btn.drive_select_folder | h_drive_select_folder | drive_folders.select | ✅ | ❌ | ❌ | — | 2 |
| drive.refresh_quota | connection | btn.refresh_quota | h_drive_refresh_quota | drive_quota.refresh | ✅ | ✅ | ✅ | tests/test_drive_quota.py::test_warn_90 | 2 |
| analyze.run | analyze | btn.analyze | h_analyze_run | scanner.analyze | ✅ | ✅ | ✅ | tests/test_scoped_scan.py::test_handler_passes_bounded_scan_request | 2 |
| analyze.set_mode | analyze | form.scan_mode | h_analyze_set_mode | scanner.mode_fields | ✅ | ✅ | ✅ | tests/test_analyze_ui_modes.py::test_set_mode_shows_only_the_fields_that_mode_uses | 4 |
| analyze.apply_filters | analyze | btn.apply_filters | h_analyze_apply_filters | selection.apply_filters | ✅ | ✅ | ✅ | tests/test_filters.py::test_by_type | 2 |
| analyze.select_all | analyze | btn.select_all | h_analyze_select_all | selection.select_all_visible | ✅ | ✅ | ✅ | tests/test_selection.py::test_select_all_visible_only | 2 |
| analyze.clear_selection | analyze | btn.clear_selection | h_analyze_clear_selection | selection.clear | ✅ | ✅ | ✅ | tests/test_selection.py::test_clear_selection_preserves_items_and_visible_rows | 2 |
| analyze.enqueue_selected | analyze | btn.enqueue_selected | h_analyze_enqueue_selected | selection.enqueue_selected | ✅ | ✅ | ✅ | tests/test_queue.py::test_enqueue_and_deduplicate | 2 |
| queue.start_selected | transfers | btn.start | h_queue_start_selected | queue_manager.start_selected | ✅ | ✅ | ✅ | tests/test_phase_c.py::test_start_selected_never_processes_the_whole_table | 2 |
| queue.pause | transfers | btn.pause | h_queue_pause | queue_manager.pause | ✅ | ✅ | ✅ | tests/test_phase_c.py::test_pause_exports_a_checkpoint_before_reporting_paused | 2 |
| queue.resume | transfers | btn.resume | h_queue_resume | queue_manager.resume | ✅ | ✅ | ✅ | tests/test_phase_3.py::test_resume_clears_the_pause_gate_on_the_owned_manager | 2 |
| queue.stop | transfers | btn.stop | h_queue_stop | queue_manager.stop | ✅ | ✅ | ✅ | tests/test_phase_3.py::test_stop_sets_the_manager_stop_flag_and_reports_stopped | 2 |
| queue.retry_failed | transfers | btn.retry_failed | h_queue_retry_failed | queue_manager.retry_failed | ✅ | ✅ | ✅ | tests/test_phase_c.py::test_retry_failed_never_revives_a_stopped_item | 2 |
| queue.clear_completed | transfers | btn.clear_completed | h_queue_clear_completed | queue_manager.clear_completed_metadata | ✅ | ✅ | ✅ | tests/test_phase_3.py::test_clear_completed_removes_finished_rows_only | 2 |
| queue.refresh | transfers | btn.refresh | h_queue_refresh | queue_manager.snapshot | ✅ | ✅ | ✅ | tests/test_phase_3.py::test_refresh_snapshot_reports_live_counts | 2 |
| queue.pause_item | transfers | btn.pause_item | h_queue_pause_item | queue_manager.pause_item | ✅ | ✅ | ✅ | tests/test_phase_3.py::test_pause_item_marks_an_in_flight_item_paused | 2 |
| queue.resume_item | transfers | btn.resume_item | h_queue_resume_item | queue_manager.resume_item | ✅ | ✅ | ✅ | tests/test_phase_3.py::test_pause_item_and_resume_item_only_touch_that_item | 2 |
| queue.stop_item | transfers | btn.stop_item | h_queue_stop_item | queue_manager.stop_item | ✅ | ✅ | ✅ | tests/test_phase_3.py::test_stop_item_is_permanent_for_that_item | 2 |
| queue.retry_item | transfers | btn.retry_item | h_queue_retry_item | queue_manager.retry_item | ✅ | ✅ | ✅ | tests/test_phase_3.py::test_retry_item_returns_a_failed_item_to_pending | 2 |
| dashboard.refresh | dashboard | btn.refresh | h_dashboard_refresh | stats.dashboard | ✅ | ❌ | ❌ | — | 1 |
| logs.refresh | logs | btn.refresh | h_logs_refresh | log_service.tail | ✅ | ❌ | ❌ | — | 1 |
| logs.search | logs | btn.search_logs | h_logs_search | log_service.search | ✅ | ❌ | ❌ | — | 1 |
| logs.download | logs | btn.download_logs | h_logs_download | log_service.export_file | ✅ | ❌ | ❌ | — | 1 |
| settings.set_concurrency | settings | form.concurrency | h_settings_set_concurrency | settings.set_concurrency | ✅ | ❌ | ❌ | — | 1 |
| settings.toggle_language | settings | btn.language | h_settings_toggle_language | preferences.toggle_language | ✅ | ✅ | ✅ | tests/test_i18n.py::test_toggle | 1 |
| settings.set_theme | settings | btn.theme | h_settings_set_theme | preferences.set_theme | ✅ | ❌ | ❌ | — | 1 |
| export.build_zip | export | btn.build_zip | h_export_build_zip | package_service.build_tested_archive | ✅ | ❌ | ❌ | — | 2 |
| export.colab_cells | export | btn.colab_cells | h_export_colab_cells | colab_export.cells_text | ✅ | ❌ | ❌ | — | 1 |
| recovery.restore | settings | btn.recover | h_recovery_restore | checkpoints.restore_and_reconcile | ✅ | ❌ | ❌ | — | 1 |
| maintenance.checkpoint | settings | btn.checkpoint | h_maintenance_checkpoint | checkpoints.persist | ✅ | ❌ | ❌ | — | 1 |

## 4) الجدول B — واقع الواجهة والجاهزية (من `ui.py` + تشغيل حقيقي للـcontext)

> `wired_in_ui`: «✓ call-site (فعلي)» = الـwire حقيقي وقت التشغيل؛ «call-site فقط / يُتخطى» = `wire_if_ready` يتخطاه لأنه غير جاهز (لا حدث يُربط أصلًا — هذا مقصود ومحمي باختبارات).

| action_id | rendered_in_ui | wired_in_ui | visible_at_first_render | handler_resolves_on_context | requires_live_colab | current_blocker | recommended_fix |
|---|---|---|---|---|---|---|---|
| telegram.set_credentials | ✅ زر primary | ✓ (click) | ✅ | ✅ | نعم — إثبات حي (M15-T01 بيد المالك) | لا عائق كود؛ الإثبات الحي متبقٍ | live Colab proof |
| telegram.send_code | ✅ زر | ✓ (click) | ✅ | ✅ | نعم | كما سبق | live Colab proof |
| telegram.resend_code | ✅ زر | ✓ (click) | ✅ | ✅ | نعم | كما سبق | live Colab proof |
| telegram.verify_code | ✅ زر داخل لوحة OTP | ✓ (click) | ❌ **بتصميم** — اللوحة مخفية حتى `CODE_REQUESTED` | ✅ | نعم | — | live Colab proof |
| telegram.verify_password | ✅ زر داخل لوحة 2FA | ✓ (click) | ❌ **بتصميم** — مخفية حتى `PASSWORD_REQUIRED` | ✅ | نعم | — | live Colab proof |
| telegram.logout | ✅ زر stop | ✓ (click) | ✅ | ✅ | نعم | — | live Colab proof |
| telegram.status | ✅ زر secondary | ✓ (click) | ✅ | ✅ | نعم | — | live Colab proof |
| drive.connect | ✅ كزر placeholder مخفي | call-site فقط / يُتخطى | ❌ مخفي (غير جاهز) | ✅ | نعم — مصادقة Colab الأصلية | `tested=False`: توجد اختبارات بوابة بـfake factory في `test_drive_connection_gate.py` (about-gate) لكنها غير مربوطة كـproof_test (`PROVES=()` بقرار موثق: «حتى جلسة Colab حقيقية») | **T02-P1**: اختبار proof handler-level عبر factory مزيفة + قرار Brain بقبوله لقلب `tested`، مع بقاء الإثبات الحي للمالك |
| drive.reconnect | ✅ placeholder مخفي | call-site فقط / يُتخطى | ❌ مخفي | ✅ | نعم | `tested=False` — يوجد اختبار reconnect يمسح الخدمة ويعيد البوابة (غير مربوط) | **T02-P1**: ربط proof + فحص مسح الحالة السابقة |
| drive.status | ✅ placeholder مخفي | call-site فقط / يُتخطى | ❌ مخفي | ✅ | نعم (قراءة محلية لكن حالة Connected تتطلب بوابة حية) | `tested=False` — لا proof test | **T02-P1**: proof بأن status read-only ولا يدّعي Connected قبل about |
| drive.list_folders | ✅ placeholder مخفي | call-site فقط / يُتخطى | ❌ مخفي | ✅ | نعم | `tested=False` — تغطية handler-contract عامة فقط؛ لا اختبار سلوكي لـ`files().list` | **T02-P1**: fake Drive service يثبت بنية choices `name :: id` |
| drive.create_folder | ✅ placeholder مخفي | call-site فقط / يُتخطى | ❌ مخفي | ✅ | نعم | `tested=False` — لا proof على تحقق الاسم الفارغ/الإنشاء | **T02-P1**: proof تحقق الاسم + fake create |
| drive.select_folder | ✅ placeholder مخفي | call-site فقط / يُتخطى | ❌ مخفي | ✅ | نعم | `tested=False` — لا proof على فرض `mimeType=folder` واستخراج ID | **T02-P1**: proof mimeType validation + folder ID هو المحفوظ |
| drive.refresh_quota | ✅ زر secondary | ✓ (click) | ✅ | ✅ | نعم | لا عائق كود؛ الحي متبقٍ | live Colab proof |
| analyze.run | ✅ زر primary | ✓ (click) | ✅ | ✅ | نعم — جلب Telegram حقيقي | الإثبات الوحشي موجود بـfakes؛ الحي متبقٍ | live Colab proof |
| analyze.set_mode | ✅ Radio (is_ready gate) | ✓ (change) | ✅ | ✅ | لا — mapping محلي | — | — |
| analyze.apply_filters | ✅ زر داخل Accordion | ✓ (click) | ⚠️ داخل `form.filters` Accordion مطوي (`open=False`, visible=True) | ✅ | لا — محلي | — | — |
| analyze.select_all | ✅ زر | ✓ (click) | ✅ | ✅ | لا | — | — |
| analyze.clear_selection | ✅ زر | ✓ (click) | ✅ | ✅ | لا | — | — |
| analyze.enqueue_selected | ✅ زر primary | ✓ (click) | ✅ | ✅ | لا — enqueue محلي؛ النقل اللاحق يحتاج اتصالات | — | — |
| queue.start_selected | ✅ زر primary | ✓ (click) | ✅ | ✅ | نعم للنقل الحقيقي؛ المنطق مثبت بـfakes | مثبت أنه لا يعالج كل Pending؛ الحي متبقٍ | live Colab proof |
| queue.pause | ✅ زر | ✓ (click) | ✅ | ✅ | لا | مثبت checkpoint-قبل-paused | live Colab proof أثناء نقل حقيقي |
| queue.resume | ✅ زر | ✓ (click) | ✅ | ✅ | لا | — | live Colab proof |
| queue.stop | ✅ زر stop | ✓ (click) | ✅ | ✅ | لا | مثبت أنه لا يحذف Drive | live Colab proof |
| queue.retry_failed | ✅ زر | ✓ (click) | ✅ | ✅ | لا | مثبت أن Stopped نهائي | live Colab proof |
| queue.clear_completed | ✅ زر | ✓ (click) | ✅ | ✅ | لا | مثبت حذف metadata فقط | live Colab proof |
| queue.refresh | ✅ زر secondary | ✓ (click) | ✅ | ✅ | لا | — | — |
| queue.pause_item | ✅ زر + حقل `item_id` يدوي | ✓ (click) | ✅ | ✅ | لا | — | — |
| queue.resume_item | ✅ زر + حقل `item_id` | ✓ (click) | ✅ | ✅ | لا | — | — |
| queue.stop_item | ✅ زر stop + حقل `item_id` | ✓ (click) | ✅ | ✅ | لا | — | — |
| queue.retry_item | ✅ زر + حقل `item_id` | ✓ (click) | ✅ | ✅ | لا | — | — |
| dashboard.refresh | ✅ placeholder مخفي | call-site فقط / يُتخطى | ❌ مخفي | ✅ | لا — قراءات حية محلية | `tested=False`؛ علمًا أن `dashboard_json` **مبذور حيًا** عند أول رسم (`shell_seed`) فلا أرقام وهمية | **T02-P2**: proof على شكل payload الحقيقي + arity 1 (البيانات نفسها حقيقية أصلًا) |
| logs.refresh | ✅ placeholder مخفي | call-site فقط / يُتخطى | ❌ مخفي | ✅ | لا | `tested=False`؛ علمًا أن `logs_box` يُملأ من `LogService.tail` الحقيقي عند الرسم | **T02-P4**: proof tail + redaction |
| logs.search | ✅ placeholder مخفي | call-site فقط / يُتخطى | ❌ مخفي | ✅ | لا | `tested=False` — لا proof على الفلترة + التنقيح | **T02-P4**: proof search لا يطبع أسرارًا |
| logs.download | ✅ placeholder مخفي | call-site فقط / يُتخطى | ❌ مخفي | ✅ | لا | `tested=False` — لا proof على ملف التصدير المنقَّح | **T02-P4**: proof export_file redacted |
| settings.set_concurrency | ✅ Slider خلف is_ready gate | call-site فقط / يُتخطى | ❌ السلايدر مخفي — **لكن ملاحظة `common.unavailable` ظاهرة تشرح الغياب** | ✅ | لا | `tested=False` — لا proof على clamp 1..4 والتمرير للـTransferManager | **T02-P5**: proof clamp + apply_concurrency |
| settings.toggle_language | ✅ زر في الشريط العلوي | ✓ (click) | ✅ | ✅ | لا | — | تُثبت إعادة الرسم الحافظة للحالة في shell contract |
| settings.set_theme | ✅ Radio خلف is_ready gate داخل accordion «المتقدمة» | call-site فقط / يُتخطى | ❌ مخفي (+accordion مطوٍ) | ✅ | لا | `tested=False` **والخدمة تخزّن التفضيل فقط** (`ui_state.extra`+SQLite) — لا light theme فعلي ولا إعادة رسم؛ CSS داكن فقط | **T02-P5 + T03**: إضافة light tokens حقيقية وتفعيل تبديل بصري فعلي (render/CSS state) قبل إظهار الزر |
| export.build_zip | ✅ placeholder مخفي (الزر الوحيد في الشريط العلوي) | call-site فقط / يُتخطى | ❌ مخفي | ✅ | لا — pytest محلي داخل `package_service` | `tested=False` — لا proof على بوابة «لا ZIP قبل pytest أخضر» ولا على خلو الأرشيف من الأسرار | **T02-P6**: proof نجاح/فشل البوابة + فحص أسرار الأرشيف |
| export.colab_cells | ✅ placeholder مخفي | call-site فقط / يُتخطى | ❌ مخفي | ✅ | لا | `tested=False` — لا proof على المطابقة مع `colab_cells.json` | **T02-P6**: proof المطابقة + redaction |
| recovery.restore | ✅ placeholder مخفي داخل accordion «المتقدمة» | call-site فقط / يُتخطى | ❌ مخفي | ✅ | نعم — يتطلب Drive لاسترداد checkpoint | `tested=False` — لا proof على مسار restore/reconcile ولا على رفضه بلا Drive | **T02-P6**: proof fake-drive restore + `DriveNotReadyError` |
| maintenance.checkpoint | ✅ placeholder مخفي داخل accordion «المتقدمة» | call-site فقط / يُتخطى | ❌ مخفي | ✅ | لا — persist محلي دائمًا (Drive best-effort) | `tested=False` — لا proof على persist المحلي | **T02-P6**: proof persist_local + مسار Drive الاختياري |

## 5) النتائج المتقاطعة الصادقة (مؤكدة بالفحص المباشر في هذه الجلسة)

1. **لا زر ميت ظاهر:** الـ42 إجراءً كلها تمر عبر `binder.button`/`wire_if_ready`؛ الـ16 غير الجاهزة تُرسم `visible=False, interactive=False` ولا يُربط لها حدث أصلًا (`test_button_factory_hides_and_disables_unready_controls` + `assert_complete`).
2. **لا action بدون handler مسمّى أو مسار خدمة:** 42/42 handler مزخرف و42/42 `service_path` تتحلل على context حي.
3. **لا fake data:** أول رسم يُبزر من `shell_seed` الحي (الجداول فارغة لأن القاعدة فارغة، chips = «غير متصل» لأن آلة الحالة كذلك) — `test_fresh_render_shows_no_fake_rows_logs_or_connected_states`.
4. **15 من 16 إجراءً مخفيًا تختفي صامتة:** الوحيد الذي يشرح غيابه بملاحظة ظاهرة هو `settings.set_concurrency`. الباقي (drive.* الستة، dashboard.refresh، logs.* الثلاثة، settings.set_theme، export.* الاثنان، recovery.restore، maintenance.checkpoint) لا يظهر له أي شرح — **يتعارض مع اختبار T03 المطلوب** «All unready actions are visibly explained, not silently missing».
5. **`settings.set_theme` تفضيل بلا أثر بصري:** الخدمة تخزّن القيمة فقط؛ لا light theme حقيقي في CSS (`GRAPHITE_CSS` داكن فقط) ولا مسار إعادة رسم للثيم — إصلاحه مشروط بـT02-P5 ثم T03.
6. **تبويب Export بلا زر بناء ظاهر:** زر `export.build_zip` الوحيد في الشريط العلوي ومخفي؛ تبويب Export يعرض مخرجات فقط (zip_message/zip_file/صندوق cells) — شكليًا يوحي بوظيفة غير جاهزة. تصميميًا يجب نقل/إظهار الزر داخل التبويب عند جاهزيته (T03).
7. **drive.* لديها اختبارات بوابة حقيقية غير مربوطة:** `test_drive_connection_gate.py` يثبت (بـfake factory) أن Connected مستحيل قبل `about().get()` وأن reconnect يمسح الخدمة السابقة — لكن `PROVES=()` بقرار موثق ينتظر Colab الحقيقي. **قرار T02-P1 لـBrain:** قبول fake-factory كـproof_test لقلب `tested` (يطابق نص M17-T02 نفسه: «اختبر service factory مزيفًا لــunit tests») مع بقاء الإثبات الحي للمالك.
8. **`drive.list_folders/create_folder/select_folder` بلا أي اختبار سلوكي:** التغطية الوحيدة handler-contract العام (dispatch+redaction). تحتاج fake `files()` service.
9. **حالة الإصدار المنشور (تحقق مباشر):** التاج المثبَّت `pkg-2026.08.09-m15t07` أُعيد نشره على `4a2dac62` (دمج M16-T01) بتاريخ 2026-08-10T11:55:10Z بأصلين: `teledrive_v4.5.zip` (222699 بايت — يطابق بناء M16-T01) و`teledrive_manifest.json` (378 بايت). **ملاحظة M17 MASTER «الإصدار المنشور قديم» لم تعد دقيقة**؛ الناقص الوحيد هو استهلاك/إثبات Colab الحي (M15-T01، بيد المالك).
10. **TOPbar zip + language + status chips سليمة بنيويًا:** chips تُبزر من الحالة الحية وتتحدث فقط عبر مخرجات الـtelegram/drive handlers (arity 4/2 مثبتة).

## 6) التحقق الخام (Raw) — نفّذ على venv محلي بمثبّتات `requirements.lock` نفسها (gradio 6.20.0 / pytest 9.1.1)

```plain
$ cd python-package
$ python -m compileall teledrive            # exit 0 (Listing 'teledrive'... / locale)
$ python -m pytest -q tests/test_bindings.py tests/test_action_proofs.py tests/test_ui_shell_contract.py
61 passed, 1 warning in 5.93s               # التحذير: Gradio 6 المسار deprecated لـtheme/css — موثق في M15-T04
$ python teledrive_launcher.py --check
bootstrap: {'schema_version': 1, 'dirs': [...], 'free_bytes': 20053020672}
binding check ok: 26/42 ready actions resolve   # exit 0
$ python -m pytest -q tests                  # (إضافي، خارج بوابة T01، للصورة الكاملة)
443 passed, 1 warning in 13.67s
```

تشغيل يدوي تكميلي (سكربت فحص عابر، غير مضاف للريبو): 42/42 `ctx.resolve(service_path)` ناجح، 42/42 handler مزخرف بـaction_id الصحيح، كل `proof_test` المعلنة موجودة (file::function)، ولا `label_key` ناقص في ar/en.

## 7) حدود هذا الجرد (ما لم يُثبَت)

- لا إثبات Colab حي لأي مسار Telegram/Drive/نقل — بيد المالك (M15-T01). كل proof tests وحشية بـfakes.
- لم يُشغَّل `notebook_cells --check` أو `cmp` (خارج نطاق T01 الصريح؛ لم يُعدَّل أي ملف منتج أصلًا).
- لم تُفحص تغطية اختبارات `logs`/`export` إلى عمق إعادة إنتاج الأخطاء داخل الخدمات؛ الجرد يثبت الغياب المؤكد للـproof المربوط لا غياب كل سطر تغطية.

## 8) الخلاصة والخطوة التالية

العدسة الصادقة: **26/42 إجراءً ظاهرًا وموصولًا فعليًا بخدمات حقيقية، و16/42 منفذة الكود لكنها مخفية عمدًا (15 منها بلا شرح ظاهر) انتظارًا لـproof tests و/أو إثبات Colab الحي.** لا أزرار ميتة، ولا handlers مفقودة، ولا fake data. الأولويات جاهزة لـT02: P1 Drive (7)، P2 Dashboard (1)، P3 Transfers (مثبتة منطقيًا — تحتاج إثباتًا حيًا لا proofs جديدة)، P4 Logs (3)، P5 Settings (2 + theme بصري)، P6 Export/Recovery (4).

**STOP — بانتظار موافقة Brain على هذا الجرد قبل بدء M17-T02.**
