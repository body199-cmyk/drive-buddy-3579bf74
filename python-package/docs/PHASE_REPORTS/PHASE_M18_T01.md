# PHASE_M18_T01 — DOC-39: إصلاح الواجهة الحالية والاختيار قبل النقل (بدون React)

> **TASK ID:** M18-T01 — **الحالة:** PARTIALLY COMPLETE (كود + بوابات خضراء + دليل Colab خطوة-بخطوة؛ لا توجد جلسة Colab حية من الساندبوكس — لا بيانات اعتماد ولا متصفح)
> **المرجع:** DOC-39 (https://doc.clickup.com/90182963648/d/h/2kzn5me0-518/7d62268c1fb8c1f)
> **Base SHA:** `27355232f15d07761fb9a226f8161dd22b5e0e82` (origin/main = PR #29)
> **تاريخ التنفيذ:** 2026-08-10 UTC

## 1. الملخص التنفيذي

نُفِّذ DOC-39 كاملًا في جلسة واحدة متصلة: إصلاح المظهر (ثيم graphite داكن افتراضي + lime accent + RTL افتراضي + شريط علوي حقيقي + تنقل يمين)، لوحة اختيار مجلد Drive داخل التحويلات/لوحة التحكم (4 لوحات من مصدر حقيقة واحد)، وإعادة بناء مساحة تحليل وروابط كمرحلة اختيار حقيقية (جدول مرشحين من 8 أعمدة مع خانة تحديد جزءًا من قيمة الجدول، تحديد الكل/إلغاء/يدوي صف-بصف/نطاق من-إلى بسقف معلن/مجموعة، معاينة عدد+حجم+مجلد+مساحة، بوابة إضافة للطابور ترفض بلا تحديد/مجلد/مساحة/حصة). لا React، لا تغيير معماري، لا لمس لملفات محمية (SQLite/queue/transfer/Notebook).

أُضيفت 3 أفعال جديدة (45/45 ready)، وأُضيفت ملفات الاختبار الأربعة المطلوبة في DOC §7 (44 اختبارًا جديدًا/موسّعًا)، وكامل البوابة: **580 passed** · launcher `--check` 45/45 · notebook in sync · cmp متطابق.

## 2. القرارات

- **Gradio هي واجهة التنفيذ الرسمية** — لا React (DOC §2)؛ `M17-T04` لم يبدأ.
- **مصدر الألوان الوحيد:** `ui_theme.py` — صفر ألوان hardcoded في `ui.py` (تحقَّق آلي).
- **مصدر الحقيقة للمجلد:** `folder_id` واحد في `config/db` (`drive_folder_id`)؛ الاسم للعرض فقط. كل اللوحات الأربع (لوحة التحكم · التحويلات · الإعدادات · مركز الاتصال) + الشريحة العلوية تتحدث بنفس القيمة عبر broadcast من 10 مخارج في handler واحد لكل فعل.
- **اختيار يدوي صف-بصف:** عبر `Dataframe.select` → `analyze.toggle_row` (SelectData index → الصف n في `visible()`)، والخانة ☑/☐ جزء من قيمة الجدول (`candidate_rows_for`) لا زر شكلي.
- **المجموعة:** التجمع الذي يدعمه المصدر اليوم هو القناة/المحادثة (`chat_title`/`chat_id`) — ألبومات `grouped_id` تتطلب تغيير عقد الـscanner/SQLite خارج النطاق (موثّق في "غير المُثبت").
- **`enqueue_selected` بوابات:** تحديد غير فارغ → مجلد هدف صالح (`err.no_folder`) → مساحة محلية (`err.disk_full`) → حصة Drive عند الاتصال (`err.drive_full`). لا يبدأ نقل، لا يلمس Telegram قبل الزر.
- **النسخة:** `v{ctx.config.version}` — لا literal في `ui.py` (تحقَّق: `grep 4.5.0` في ui.py/ui_theme.py = صفر).

## 3. الملفات

### Created
- `teledrive/tests/test_ui_colab_render_contract.py` — RTL عربي افتراضي · dark افتراضي · لوحة المجلد في التحويلات/لوحة التحكم · لا blank first render · النسخة من config · شرائح HTML · أعمدة الجدول.
- `teledrive/tests/test_folder_target_flow.py` — list/select/create من لوحة التحويلات · ID يثبت وينتشر لكل الشرائح · Drive مفصول = visible+disabled+سبب مترجم · بوابة enqueue تتبع المجلد.
- `teledrive/tests/test_file_selection_flow.py` — PROVES لـ`analyze.toggle_row`/`select_range`/`select_group` · تحديد الكل/إلغاء · يدوي · نطاق (سقف 1000) · مجموعة · عداد+حجم · رفض enqueue بلا تحديد/مجلد/مساحة.
- `teledrive/tests/test_no_enqueue_before_selection.py` — التحليل لا يُدخل الطابور تلقائيًا · لا تنزيل Telegram قبل enqueue صريح · عمليات التحديد في الذاكرة فقط.
- `docs/PHASE_REPORTS/assets/make_ui_render.py` + `ui_render_fresh.png` + `ui_render_selection.png` — دليل بصري مولّد من الشجرة الحية (ألوان/قيم حقيقية).

### Changed
- `teledrive/ui.py` — شرائح علوية HTML (`td-chip`) · لوحة مجلد رابعة في التحويلات + لوحة التحكم مفتوحة · مرحلة اختيار كاملة في تحليل وروابط (جدول 8 أعمدة `CANDIDATE_HEADERS`، معاينة، نطاق، مجموعة، enqueue مقفول حسب الحالة) · wiring broadcast 10 مخارج للمجلد · 5 مخارج لمرحلة التحديد · `Dataframe.select` عبر `binder.wire`.
- `teledrive/handlers.py` — `chip_html()` · `_selection_view()` · `_folder_broadcast()` · handlers: `h_analyze_toggle_row` (SelectData) · `h_analyze_select_range` · `h_analyze_select_group` · enqueue يُحدِّث جدول/حالة الطابور الحقيقيين · `ERROR_ARITY` (create/select=10، analyze.*=5) · `shell_seed` موسّع.
- `teledrive/services.py` — `SelectionService`: `toggle_by_index` · `select_range` (تحقق+سقف `MAX_RANGE_MESSAGES`) · `select_group_by_chat` · `groups()` · `summary()` · `enqueue_selected` بوابات folder/disk/quota · `candidate_rows_for()`.
- `teledrive/action_registry.py` — 3 أفعال جديدة ready + proof_test.
- `teledrive/ui_theme.py` — عرض متناسق (max-width 1280، جداول/بطاقات 100%) · `.td-chip-host` · focus ring lime · إخفاء أزرار تحرير الجدول · hover على صفوف المرشحين.
- `teledrive/locale/ar.json` + `en.json` — 20 مفتاحًا جديدًا (col.select/msg_id/group/date · btn.select_range/group/toggle_row · err.selection_range_invalid/too_large · msg.no_folder_selected · sel.* · form.range_from/to · form.group).
- `tests/conftest.py` — إعادة تعيين `drive_folder_id`/`manual_concurrency` على CONFIG المشترك بعد كل اختبار (عزل صحيح — كشف تسرب حالة عبر reload).
- حُدِّثت اختبارات قائمة للعقد الجديد: `test_folder_picker_parity.py` (4 لوحات، arity 10) · `test_drive_folders.py` (broadcast 10) · `test_drive_connection_gate.py` · `test_telegram_flow_contract.py` (chips HTML) · `test_ui_shell_contract.py` (أعمدة 8، chips) · `test_analyze_ui_contract.py` (تخطيط الجدول) · `test_selection.py` (5 مخارج) · `test_scoped_scan.py` (5 مخارج) · `test_handlers_contract.py` (ARGS للأفعال الجديدة).
- `docs/UI_ACTION_INVENTORY.md` — 42/42 → **45/45**.

### Protected (لم تُلمس — تحقَّق بـ git diff)
`notebook/TeleDrive.ipynb` · `public/TeleDrive.ipynb` · `teledrive/notebook_cells.py` · `colab_cells.json` · `database.py` · `migrations.py` · `queue_manager.py` · `transfer_manager.py` · `telegram_auth.py` · `drive_auth.py` · `drive_folders.py`(لم يتغير في هذه الجلسة) · `requirements.*` · `bun.lock` · `package.json` · `.github/workflows/*` · كل ملفات React/frontend.

## 4. التحقق الخام (raw)

```bash
cd python-package
python -m compileall -q teledrive                       # exit 0
python -m pytest -q tests                               # 580 passed (كان 536)
python teledrive_launcher.py --check                    # binding check ok: 45/45 ready actions resolve
python -m teledrive.notebook_cells --check              # notebooks are in sync
cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb   # متطابقان (exit 0)
```

مصفوفة render حية (real gradio 6.20.0): direction=td-rtl · 4 لوحات مجلد (dash/transfer/settings/conn) · رؤوس المرشحين الـ8 بالعربية · chips HTML · enqueue interactive=False عند الفراغ · missing=[] orphans=[] · 45 wired.

الواجهة الحية: الخادم يعمل على `0.0.0.0:7860` (HTTP 200، `/config` يخدم `<style id="td-theme-vars" data-td-theme="dark">`).

## 5. دليل Colab الحي — الخطوات الدقيقة (للمالك)

لا يمكن تشغيل جلسة Colab حقيقية من الساندبوكس (لا بيانات اعتماد Telegram/Google ولا متصفح)، لذا الدليل خطوة-بخطوة + دليل بصري مولّد من الشجرة الحية:

1. افتح `notebook/TeleDrive.ipynb` في Colab (File → Upload notebook) أو من الريبو: `https://github.com/body199-cmyk/drive-buddy-3579bf74/blob/main/notebook/TeleDrive.ipynb` (افتح في Colab).
2. الخلية 1: ارفع الحزمة `teledrive_v4.5.zip` (أو شغّل التحديث عبر manifest) ثم شغّل الخلايا بالترتيب: install → bootstrap → auth → launch.
3. افتح رابط `TeleDrive URL: https://…prod.colab.dev/…` — التوقع عند أول فتح:
   - خلفية graphite داكنة (#0d0f10) وليست بيضاء، accent lime للأزرار.
   - عربي RTL، الشريط العلوي: TeleDrive v4.5.0 · تيليجرام (غير متصل) · درايف (غير متصل) · المجلد (غير متصل) · Colab Native · SQLite WAL · زر English.
   - التنقل يمينًا بأقسامه السبعة، القسم النشط بخط/إشارة lime.
   - التحويلات: لوحة «مجلد جوجل درايف الهدف» ظاهرة ومفتوحة، عناصرها disabled مع «لم يتم ربط جوجل درايف».
4. اربط درايف → «تحديث المجلدات» → اختر مجلدًا أو أنشئه → يتحدث اسمه في الشريحة العلوية + اللوحات الأربع فورًا.
5. تحليل وروابط: الصق رابط رسالة/قناة → تحليل → جدول المرشحين (☐ تحديد · معرّف الرسالة · الملف · النوع · الحجم · المجموعة · التاريخ · الحالة).
6. انقر أي صف لتبديل ☐/☑، أو تحديد الكل/إلغاء، أو نطاق من/إلى (سقف 1000)، أو مجموعة.
7. المعاينة تعرض: الملفات المحددة · الحجم الكلي · المساحة المطلوبة · مجلد الوجهة؛ زر «إضافة إلى قائمة الانتظار» مقفول حتى وجود تحديد + مجلد.
8. اضغط الإضافة → الصفوف تنتقل إلى التحويلات (Pending) دون بدء نقل؛ ابدأ النقل يدويًا بزر «بدء النقل».

الدليل البصري المولّد (شجرة حية حقيقية): `docs/PHASE_REPORTS/assets/ui_render_fresh.png` (أول فتح: تحويلات + لوحة المجلد + طابور فارغ) و`ui_render_selection.png` (مرحلة التحديد بعد أفعال حقيقية: 5 مرشحين ☑، معاينة، مجلد Alpha، enqueue مفعّل).

## 6. قالب التقرير (DOC §9)

```
TASK ID: M18-T01
Status: PARTIALLY COMPLETE — الكود والبوابات كاملة؛ دليل Colab الحي خطوة-بخطوة جاهز،
        ولا توجد جلسة Colab حية من الساندبوكس (لا creds ولا متصفح)
PR URL / Result SHA: (انظر PR المفتوح — الفرع arena/019fed9c-drive-buddy-3579bf74)
Files changed / protected files: 3 created modules · 4 test files جديدة · 9 ملفات كود/اختبارات
        محدّثة · 0 ملف محمي
UI visual smoke: screenshot proof yes (مولّد من الشجرة الحية — لا متصفح في الساندبوكس)
        · live preview: الخادم يعمل على المنفذ 7860 في هذه الجلسة
Folder target: visible in transfers/dashboard yes · list/select/create yes · ID persisted yes
Selection: all/clear/manual/group/range yes · count/size yes · empty guard yes
Enqueue safety: no enqueue before selection yes · missing folder refusal yes
        · disk/quota refusal yes
Verification raw: compileall 0 · pytest 580 passed · launcher 45/45 · notebook check ok · cmp ok
Live Colab proof: URL غير متاح من الساندبوكس + exact steps أعلاه + دليل بصري مولّد
What is not proven: لقطة Colab حقيقية بمتصفح/حساب حي · النقر الفعلي على صف الجدول في متصفح
        (select event مضمون عبر interactive=True وفحص الـbundle) · نقل ملف حقيقي
Next step: STOP and await Brain approval — لا React قبل مراجعة Brain
```

## 7. ما لم يُثبت (بصدق)

- **لقطة Colab حقيقية:** الساندبوكس بلا متصفح (CDN بلوك) وبلا جلسة Colab — الدليل البصري مولّد من الشجرة الحية بنفس القيم/الألوان، والخادم الحي يعمل في هذه الجلسة للمعاينة.
- **النقر الفعلي في متصفح على `Dataframe.select`:** الوصلة مبنية عبر `binder.wire(event="select")` والجدول `interactive=True` (مسار select مضمون في واجهة Gradio)، لكن الإثبات الحي بيد المالك.
- **ألبومات `grouped_id`:** خارج النطاق — يحتاج تغيير عقد scanner/MediaItem/SQLite (ملفات محمية)؛ التجمع المدعوم اليوم هو القناة/المحادثة.
