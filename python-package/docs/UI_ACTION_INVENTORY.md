# UI_ACTION_INVENTORY — M18-T01: جرد الأفعال بعد DOC-39 (إصلاح الواجهة + الاختيار قبل النقل)
> **TASK ID:** M18-T01 (DOC-39) — محدِّث على جرد M17-T02-REST + M17-T03 (DOC-37)
> **Base SHA:** `27355232f15d07761fb9a226f8161dd22b5e0e82` (origin/main)
> **الحالة:** 45/45 ready, visible, wired — launcher `--check` 45/45

## ملخص الأرقام

| المقياس | القيمة |
|---|---|
| إجمالي الأفعال | 45 |
| ready (implemented+tested) | **45** |
| unready (blocked_reason_key) | **0** |
| wired عبر binder.wire | 45 action kinds (تصدير ZIP له زرّان، folder create/select لكل لوحة من 4) |

## الجرد الكامل

| # | action_id | section | ready | proof_test | output_arity |
|---|---|---|---|---|---|
| 1 | `telegram.set_credentials` |
| 2 | `telegram.send_code` |
| 3 | `telegram.resend_code` |
| 4 | `telegram.verify_code` |
| 5 | `telegram.verify_password` |
| 6 | `telegram.logout` |
| 7 | `telegram.status` |
| 8 | `drive.connect` |
| 9 | `drive.reconnect` |
| 10 | `drive.status` |
| 11 | `drive.list_folders` |
| 12 | `drive.create_folder` |
| 13 | `drive.select_folder` |
| 14 | `drive.refresh_quota` |
| 15 | `analyze.run` |
| 16 | `analyze.set_mode` |
| 17 | `analyze.apply_filters` |
| 18 | `analyze.select_all` |
| 19 | `analyze.clear_selection` |
| 20 | `analyze.toggle_row` |
| 21 | `analyze.select_range` |
| 22 | `analyze.select_group` |
| 23 | `analyze.enqueue_selected` |
| 24 | `queue.start_selected` |
| 25 | `queue.pause` |
| 26 | `queue.resume` |
| 27 | `queue.stop` |
| 28 | `queue.retry_failed` |
| 29 | `queue.clear_completed` |
| 30 | `queue.refresh` |
| 31 | `queue.pause_item` |
| 32 | `queue.resume_item` |
| 33 | `queue.stop_item` |
| 34 | `queue.retry_item` |
| 35 | `dashboard.refresh` |
| 36 | `logs.refresh` |
| 37 | `logs.search` |
| 38 | `logs.download` |
| 39 | `settings.set_concurrency` |
| 40 | `settings.toggle_language` |
| 41 | `settings.set_theme` |
| 42 | `export.build_zip` |
| 43 | `export.colab_cells` |
| 44 | `recovery.restore` |
| 45 | `maintenance.checkpoint` |

## الأقسام السبعة (right rail, M17-T03 §6)

1. لوحة التحكم — `nav.dashboard`
2. التحويلات — `nav.queue`
3. تحليل وروابط — `nav.analyze`
4. مركز الاتصال — `nav.connection`
5. السجلات — `nav.logs`
6. الإعدادات — `nav.settings`
7. كود/تصدير Colab — `nav.export`

RTL افتراضي (عربي) · LTR للإنجليزية · الثيم عبر CSS variables من `teledrive/ui_theme.py` · لا بيانات وهمية.

DOC-39 (M18-T01): لوحة مجلد Drive رابعة داخل التحويلات (4 لوحات من مصدر حقيقة واحد، broadcast من 10 مخارج) · مرحلة اختيار قبل النقل (جدول 8 أعمدة بخانة ☑/☐ جزءًا من قيمة الجدول، نطاق من/إلى بسقف 1000، مجموعة، معاينة، بوابة enqueue) · الاختيار لا يلمس Telegram/Drive قبل زر الإضافة.
