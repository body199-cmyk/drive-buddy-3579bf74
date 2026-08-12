# UI_ACTION_INVENTORY — M24: React bridge داخل Gradio فوق السجل القائم
> **TASK ID:** M24-T01..T05 — تحديث لجرد M18-T01 وM20
> **Base SHA:** `16797ca9b540d8a22885fffb38012643713ef851` (origin/main عند بدء M24)
> **Code SHA:** `56a285b5bea01b07c74d7e3ba1a2a2b26461c5fd`
> **الحالة:** 47/47 ready وموصولة — launcher `--check` = 47/47

## ملخص الأرقام

| المقياس | القيمة |
|---|---|
| إجمالي الأفعال | 47 |
| ready (implemented+tested) | **47** |
| unready (blocked_reason_key) | **0** |
| wired عبر binder.wire | 47 action kinds: 46 السابقة + `react.bridge.request` مرة واحدة؛ النقل الرسمي value/submit |

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
| 46 | `flow.sync` |
| 47 | `react.bridge.request` |

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

M24: `ReactPanel(gr.HTML)` هو السطح الأساسي داخل Gradio 6.20.0. الحدث الوحيد الجديد `react.bridge.request` يمر عبر `UIBinder.wire(..., event="submit")` ثم `Handlers` والسجل الحالي. React لا يستعمل `fetch`/XHR/WebSocket ولا يملك client أو DB. أفعال Telegram الحساسة الأربعة (`set_credentials`/`send_code`/`verify_code`/`verify_password`) محظورة في الـbridge العام وتبقى في حقول Gradio الآمنة داخل Accordion؛ بقية أزرار React تستعمل IDs القائمة أعلاه حرفيًا.
