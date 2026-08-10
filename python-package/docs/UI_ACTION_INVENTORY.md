# UI_ACTION_INVENTORY — M17-T03: جرد الأفعال بعد إكمال M17-T02-REST + M17-T03
> **TASK ID:** M17-T02-REST + M17-T03 (DOC-37)
> **Base SHA:** `a4311dafa8301c228df048930487082597c000ea` (origin/main)
> **الحالة:** 42/42 ready, visible, wired — launcher `--check` 42/42

## ملخص الأرقام

| المقياس | القيمة |
|---|---|
| إجمالي الأفعال | 42 |
| ready (implemented+tested) | **42** |
| unready (blocked_reason_key) | **0** |
| wired عبر binder.wire | 42 action kinds / 43 زرًّا (تصدير ZIP له زرّان) |

## الجرد الكامل

| # | action_id | section | ready | proof_test | output_arity |
|---|---|---|---|---|---|
| 1 | `telegram.set_credentials` | connection | ✅ | `tests/test_telegram_auth.py::test_happy_path_reuses_the_exact_phone_code_hash` | 4 |
| 2 | `telegram.send_code` | connection | ✅ | `tests/test_telegram_auth.py::test_duplicate_send_code_click_is_idempotent` | 4 |
| 3 | `telegram.resend_code` | connection | ✅ | `tests/test_telegram_auth.py::test_resend_is_rate_limited` | 4 |
| 4 | `telegram.verify_code` | connection | ✅ | `tests/test_telegram_auth.py::test_wrong_code_keeps_the_hash_and_does_not_resend` | 4 |
| 5 | `telegram.verify_password` | connection | ✅ | `tests/test_telegram_auth.py::test_two_factor_uses_the_same_client_without_a_new_code` | 4 |
| 6 | `telegram.logout` | connection | ✅ | `tests/test_telegram_auth.py::test_logout_clears_all_secret_state` | 4 |
| 7 | `telegram.status` | connection | ✅ | `tests/test_telegram_auth.py::test_status_never_exposes_the_full_phone` | 4 |
| 8 | `drive.connect` | connection | ✅ | `tests/test_drive_connection_gate.py::test_connect_action_reports_connected_only_after_about_get` | 2 |
| 9 | `drive.reconnect` | connection | ✅ | `tests/test_drive_connection_gate.py::test_reconnect_action_clears_stale_service_and_auth_state` | 2 |
| 10 | `drive.status` | connection | ✅ | `tests/test_drive_connection_gate.py::test_status_action_is_read_only_and_never_calls_the_service` | 2 |
| 11 | `drive.list_folders` | connection | ✅ | `tests/test_drive_folders.py::test_list_folders_action_returns_real_shaped_dropdown_choices` | 2 |
| 12 | `drive.create_folder` | connection | ✅ | `tests/test_drive_folders.py::test_create_folder_action_validates_name_and_parent` | 2 |
| 13 | `drive.select_folder` | connection | ✅ | `tests/test_drive_folders.py::test_select_folder_action_validates_mimetype_and_stores_the_id` | 2 |
| 14 | `drive.refresh_quota` | connection | ✅ | `tests/test_drive_quota.py::test_warn_90` | 2 |
| 15 | `analyze.run` | analyze | ✅ | `tests/test_scoped_scan.py::test_handler_passes_bounded_scan_request` | 2 |
| 16 | `analyze.set_mode` | analyze | ✅ | `tests/test_analyze_ui_modes.py::test_set_mode_shows_only_the_fields_that_mode_uses` | 4 |
| 17 | `analyze.apply_filters` | analyze | ✅ | `tests/test_filters.py::test_by_type` | 2 |
| 18 | `analyze.select_all` | analyze | ✅ | `tests/test_selection.py::test_select_all_visible_only` | 2 |
| 19 | `analyze.clear_selection` | analyze | ✅ | `tests/test_selection.py::test_clear_selection_preserves_items_and_visible_rows` | 2 |
| 20 | `analyze.enqueue_selected` | analyze | ✅ | `tests/test_queue.py::test_enqueue_and_deduplicate` | 2 |
| 21 | `queue.start_selected` | transfers | ✅ | `tests/test_phase_c.py::test_start_selected_never_processes_the_whole_table` | 2 |
| 22 | `queue.pause` | transfers | ✅ | `tests/test_phase_c.py::test_pause_exports_a_checkpoint_before_reporting_paused` | 2 |
| 23 | `queue.resume` | transfers | ✅ | `tests/test_phase_3.py::test_resume_clears_the_pause_gate_on_the_owned_manager` | 2 |
| 24 | `queue.stop` | transfers | ✅ | `tests/test_phase_3.py::test_stop_sets_the_manager_stop_flag_and_reports_stopped` | 2 |
| 25 | `queue.retry_failed` | transfers | ✅ | `tests/test_phase_c.py::test_retry_failed_never_revives_a_stopped_item` | 2 |
| 26 | `queue.clear_completed` | transfers | ✅ | `tests/test_phase_3.py::test_clear_completed_removes_finished_rows_only` | 2 |
| 27 | `queue.refresh` | transfers | ✅ | `tests/test_phase_3.py::test_refresh_snapshot_reports_live_counts` | 2 |
| 28 | `queue.pause_item` | transfers | ✅ | `tests/test_phase_3.py::test_pause_item_marks_an_in_flight_item_paused` | 2 |
| 29 | `queue.resume_item` | transfers | ✅ | `tests/test_phase_3.py::test_pause_item_and_resume_item_only_touch_that_item` | 2 |
| 30 | `queue.stop_item` | transfers | ✅ | `tests/test_phase_3.py::test_stop_item_is_permanent_for_that_item` | 2 |
| 31 | `queue.retry_item` | transfers | ✅ | `tests/test_phase_3.py::test_retry_item_returns_a_failed_item_to_pending` | 2 |
| 32 | `dashboard.refresh` | dashboard | ✅ | `tests/test_dashboard_refresh.py::test_refresh_returns_live_state_or_disconnected` | 1 |
| 33 | `logs.refresh` | logs | ✅ | `tests/test_logs_actions.py::test_refresh_returns_redacted_text_and_status` | 2 |
| 34 | `logs.search` | logs | ✅ | `tests/test_logs_actions.py::test_search_filters_by_needle_and_redacts` | 2 |
| 35 | `logs.download` | logs | ✅ | `tests/test_logs_actions.py::test_download_writes_redacted_file` | 2 |
| 36 | `settings.set_concurrency` | settings | ✅ | `tests/test_settings_concurrency.py::test_one_and_four_accepted_out_of_range_rejected` | 2 |
| 37 | `settings.toggle_language` | settings | ✅ | `tests/test_i18n.py::test_toggle` | 1 |
| 38 | `settings.set_theme` | settings | ✅ | `tests/test_theme_switch.py::test_dark_differs_from_light_and_invalid_falls_back` | 2 |
| 39 | `export.build_zip` | export | ✅ | `tests/test_export_actions.py::test_build_zip_returns_redacted_archive_without_secrets` | 2 |
| 40 | `export.colab_cells` | export | ✅ | `tests/test_export_actions.py::test_colab_cells_redacts_secrets` | 2 |
| 41 | `recovery.restore` | settings | ✅ | `tests/test_recovery_maintenance.py::test_checkpoint_then_restore_round_trip` | 1 |
| 42 | `maintenance.checkpoint` | settings | ✅ | `tests/test_recovery_maintenance.py::test_checkpoint_writes_local_file` | 1 |

## الأقسام السبعة (right rail, M17-T03 §6)

1. لوحة التحكم — `nav.dashboard`
2. التحويلات — `nav.queue`
3. تحليل وروابط — `nav.analyze`
4. مركز الاتصال — `nav.connection`
5. السجلات — `nav.logs`
6. الإعدادات — `nav.settings`
7. كود/تصدير Colab — `nav.export`

RTL افتراضي (عربي) · LTR للإنجليزية · الثيم عبر CSS variables من `teledrive/ui_theme.py` · لا بيانات وهمية.
