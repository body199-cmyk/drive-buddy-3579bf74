# PHASE_M17_T02 — إثبات وإظهار أزرار Google Drive السبعة

**المرجع:** M17-T02 DOC (بعد دمج PR #26) + M17 MASTER §3-P1 + TeleDrive Constitution v5.0
**التاريخ (UTC):** 2026-08-10
**المنفّذ:** LM Arena Agent — **المراجعة بانتظار Brain**

## التقرير (قالب M17-T02 §8)

```plain
TASK ID: M17-T02
Status: VERIFIED COMPLETE (نطاق Drive السبعة فقط — باقي أولويات M17-T02 الأصلية مسجلة كبنود لاحقة)

GitHub Status:
Commit: SUCCESS — 8325ac3c4b755ce572a9bc3c9b1367602b5a4fba
Push: SUCCESS — origin/arena/019febba-drive-buddy-3579bf74
Pull Request: UPDATED — https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/26 (لم يكن ممكنًا فتح PR ثانٍ من نفس فرع الجلسة المثبَّت و#26 ما زال مفتوحًا؛ عُدّل عنوان/متن #26 ليغطي المرحلتين بcommits منفصلة بوضوح)
Branch: arena/019febba-drive-buddy-3579bf74 (فرع الجلسة المثبَّت من المنصة؛ الاسم المقترح
        arena/m17-t02-drive-actions غير قابل للاستخدام — نفس انحراف M16-T01 الموثق)
Base SHA: e097b3d6391c0cb85ac785c605ea76f017d23f0b (= رأس PR #26 = origin/main 37377cb + محتوى PR #26؛
          صفر فروق كود منتج عن main — مُثبت بـ git diff origin/main..HEAD -- python-package/teledrive)
تنبيه انحراف: PR #26 كان ما زال OPEN لحظة بدء هذه الجلسة (المالك لم يدمجه بعد). الشرط المسبق
«main بعد دمج PR #26» تحقق بالمحتوى لا بالـSHA: الفرع يحوي 37377cb كاملًا + ملفات T01 السبعة فقط.
التوصية: يُدمج PR #26 أولًا ثم PR هذه المرحلة — لا تعارض متوقع لأنهما يستندان لنفس المحتوى.
Result SHA: 8325ac3c4b755ce572a9bc3c9b1367602b5a4fba (+ follow-up docs commit)
PR URL: https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/26
Operation error: لا شيء. (ملاحظة تعليمية: أول تشغيل دخاني سريع فشل بـ sqlite no such table لأن
  السكربت العابر لم يشغّل migrations — خطأ في أداة القياس العابرة لا في المنتج؛ أُعيد بعد
  migrations.apply() ونجح كل المسار.)
Current repository state: نظيفة بعد الـcommit.

Files created:
- python-package/tests/test_drive_folders.py          (4 اختبارات إثبات لأفعال المجلدات الثلاثة)
- docs/PHASE_REPORTS/PHASE_M17_T02.md                 (هذا الملف)
- python-package/docs/PHASE_REPORTS/PHASE_M17_T02.md  (مؤشر سطر واحد — اتفاق ADR-001؛ §5 من DOC يطلب هذا المسار و§7 يطلب الجذري)

Files modified:
- python-package/teledrive/action_registry.py  (قلب 6 أفعال إلى tested=True مع proof_test + تحديث التعليق القديم؛ drive.refresh_quota لم يُمس)
- python-package/teledrive/handlers.py         (إصلاح حقيقي: h_drive_list_folders كان يعيد قائمة خام لـgr.Dropdown — كانت ستُفسر كقيمة مختارة لا كخيارات؛ الآن component_update(choices=…))
- python-package/tests/test_drive_connection_gate.py (docstring مُحدث + PROVES(4) + 7 اختبارات إثبات handler-level)
- python-package/tests/test_bindings.py        (+اختبار AST: لا lambda ولا .click/.change/.submit حقيقية في ui.py — التوثيق قد يذكرها نصًا بأمان)
- docs/{TODO,CHANGELOG,ACTIVE_TASK,KNOWN_ISSUES,AI_HANDOFF}.md

Files deleted: لا شيء
git diff --name-only: (يُثبت في الـcommit؛ كل المسارات أعلاه ضمن قائمة §5 المسموحة حصرًا)

Protected files: لم يُلمس أي منها (تحقق آلي: notebooks, notebook_cells.py, colab_cells.json,
telegram_auth.py, queue_manager.py, transfer_manager.py, database.py, migrations.py,
requirements.*, bun.lock, package.json, workflows) — كلها PROTECTED-UNTOUCHED.
لم تُحتَج locale files: مفاتيح Drive السبعة + مفاتيح الأخطاء موجودة أصلًا في ar/en (فحص آلي).

Verification output raw:

[compileall]
python -m compileall -q teledrive → exit 0

[Drive gate tests]
python -m pytest -q tests/test_drive_connection_gate.py tests/test_drive_folders.py tests/test_drive_quota.py
→ 19 passed in 2.89s
python -m pytest -q tests/test_drive_connection_gate.py tests/test_drive_folders.py tests/test_drive_quota.py tests/test_bindings.py tests/test_action_proofs.py
→ 69 passed in 3.22s

[full pytest]
python -m pytest -q tests → 462 passed, 1 warning in 15.64s
(التحذير المعروف: مسار theme/css deprecated في Gradio 6 — موثق منذ M15-T04)

[launcher check]
python teledrive_launcher.py --check → binding check ok: 32/42 ready actions resolve (كان 26/42)

[smoke — تشغيل دخاني حقيقي للـshell مع خدمة Drive مزيفة عبر factory (ليس اختبارًا، للعرض فقط)]
connect:      ('متصل · CONNECTED · user@example.com', 'متصل')
list_folders: ('تم تحميل المجلدات', {'choices': ['Alpha :: id_alpha', 'Beta :: id_beta'], '__type__': 'update'})
create:       ('تم إنشاء المجلد', 'Backups :: id_new')
select-bad:   ('مجلد غير صالح [631cc8d2]', None)        # رفض mimeType غير folder برسالة مترجمة
select-ok:    ('تم اختيار المجلد', 'id_alpha')          # يخزّن الـID لا الاسم
quota-line:   40 B / 100 B · المتاح: 60 B
reconnect:    ('متصل · CONNECTED · user@example.com', 'متصل')
status:       ('متصل · CONNECTED · user@example.com', 'متصل')
بعد render كامل للـshell: الأفعال السبعة كلها wired (إجمالي 32) وكل أزرارها visible=True + interactive=True.
ملاحظة: demo.fns فارغة عند build الخام لأن @gr.render يعمل عند launch؛ القياس الصحيح بعد render
(وهو ما يغطيه أصلًا test_every_ready_action_is_wired_through_real_components في test_ui_shell_contract).

Drive actions ready: 7/7 — الستة المقلوبة الآن + drive.refresh_quota (لم يُمس كما طلب DOC)
  drive.connect        proof: tests/test_drive_connection_gate.py::test_connect_action_reports_connected_only_after_about_get
  drive.reconnect      proof: tests/test_drive_connection_gate.py::test_reconnect_action_clears_stale_service_and_auth_state
  drive.status         proof: tests/test_drive_connection_gate.py::test_status_action_is_read_only_and_never_calls_the_service
  drive.list_folders   proof: tests/test_drive_folders.py::test_list_folders_action_returns_real_shaped_dropdown_choices
  drive.create_folder  proof: tests/test_drive_folders.py::test_create_folder_action_validates_name_and_parent
  drive.select_folder  proof: tests/test_drive_folders.py::test_select_folder_action_validates_mimetype_and_stores_the_id
  drive.refresh_quota  proof (سابق، دون تغيير): tests/test_drive_quota.py::test_warn_90
                       + تغطية شكل الحصة الجديدة: test_drive_connection_gate.py::test_refresh_quota_action_maps_the_real_storage_quota_shape

Drive actions still blocked: لا شيء من السبعة.
  الـ10 غير الجاهزة المتبقية (خارج نطاق T02 بتعليمة Brain): dashboard.refresh · logs.refresh /
  logs.search / logs.download · settings.set_concurrency (له ملاحظة ظاهرة) · settings.set_theme ·
  export.build_zip / export.colab_cells · recovery.restore · maintenance.checkpoint
  → 9 منها ما زالت مخفية بصمت (KNOWN_ISSUES #28 محدثة).

Live Colab proof: لا يوجد — المصادقة الأصلية (google.colab auth) لا تعمل خارج Colab؛
كل البراهين أعلاه fake-factory عبر البوابة الحقيقية about().get(). الإثبات الحي بيد المالك (M15-T01).

Honest product status: Code-complete candidate / NOT Colab-ready — 32/42 action ready وظاهر وموصول.

What is not proven:
- اختيار Google الحقيقي للحساب عبر google.colab auth (يتطلب Colab حيًا)
- مسارات أخطاء شبكة Drive الحقيقية (5xx/صلاحيات) — مغطاة حاليًا بـerr.drive_auth_failed العام
- سلوك gr.Dropdown الحي في متصفح Colab (البرهان يثبت update payload الصحيح لا الرندر النهائي)
- الأفعال العشرة المتبقية (خارج النطاق)

Next step: STOP and await Brain approval
```

## تفاصيل التنفيذ

1. **الإصلاح الحقيقي الوحيد في كود المنتج:** `h_drive_list_folders` كان يعيد `choices` كقائمة خام — في Gradio تُفسَّر القيمة الخام لـDropdown كـ«قيمة مختارة» فيبقى المنُسدل فارغ الخيارات. الآن يعيد `component_update(choices=…)` (المُثبت صراحة بـ `test_list_folders_action_returns_real_shaped_dropdown_choices`).
2. **لا تخفيف لأي بوابة:** `test_action_proofs.py` لم يُعدَّل إلا باطلاعه على proofs الجديدة تلقائيًا (الملف نفسه لم يُمس — التعديل كان على القائمة المسموحة: test_drive_connection_gate/test_drive_folders/test_bindings فقط). بوابة `tested=True` تتطلب proof_test حقيقي موجود ويذكر action_id — كل proof يستدعي الـhandler الحقيقي ويتحقق `.action_id` داخله.
3. **snapshot الجرد (UI_ACTION_INVENTORY.md) لم يُحدَّث عمدًا** — ليس ضمن قائمة §5 المسموحة؛ هذا التقرير هو سجل الدلتا (26→32 ready).
