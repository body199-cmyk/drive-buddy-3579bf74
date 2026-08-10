# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

| الحقل | القيمة |
|---|---|
| TASK ID | M18-T01 (DOC-39) |
| العنوان | **إصلاح الواجهة الحالية والاختيار قبل النقل (بدون React)** — مظهر graphite داكن + RTL + لوحة مجلد Drive في التحويلات/لوحة التحكم + مرحلة اختيار حقيقية قبل الطابور |
| الحالة | **MERGED — VERIFIED COMPLETE (بوابات الكود)** — PR #30 مدموج في main عبر squash (`faff35a`) بتاريخ 2026-08-10 · CI أخضر (Python + Frontend) قبل وبعد الدمج · لقطة Colab بمتصفح حقيقي بيد المالك (لا متصفح في الساندبوكس) |
| المالك التنفيذي | LM Arena Agent |
| المهندس | Brain (DOC-39) |
| Base SHA | `27355232f15d07761fb9a226f8161dd22b5e0e82` (= رأس `origin/main`، PR #29) |
| Result SHA | `faff35a3af12adb1adf891049917f7add8dc7751` (main) — مصدرها commit `917257f` |
| النطاق | §3 المظهر (dark افتراضي، lime، RTL، شريط علوي حقيقي، تنقل يمين، عرض متناسق، نسخة من config) · §4 لوحة مجلد Drive رابعة في التحويلات + لوحة التحكم مفتوحة + broadcast واحد لكل اللوحات والشريحة العليا + «لم يتم اختيار مجلد» · §5 مرحلة اختيار: جدول 8 أعمدة بخانة ☑/☐، تحديد الكل/إلغاء/يدوي صف-بصف/نطاق من-إلى (سقف 1000)/مجموعة، معاينة (عدد/حجم/مساحة/مجلد)، بوابات enqueue (فارغ/مجلد/مساحة/حصة) · §7 أربعة ملفات اختبار جديدة (44 اختبارًا) · 3 أفعال جديدة (45/45) |
| خارج النطاق | كل الملفات المحمية (notebooks, database/migrations, queue/transfer_manager, telegram/drive auth, requirements.*, bun.lock, package.json, workflows, React/frontend) · M17-T04 (React) — ممنوع قبل موافقة Brain · ألبومات `grouped_id` (تتطلب تغيير عقد scanner/SQLite) |
| الدليل الرئيسي | compileall: ok · pytest: **580 passed** · launcher `--check`: **45/45 ready** · notebook_cells `--check`: in sync · cmp: notebook ↔ public identical · خادم حي 0.0.0.0:7860 HTTP 200 + `/config` يخدم ثيم dark · أدلة بصرية مولّدة من الشجرة الحية في `python-package/docs/PHASE_REPORTS/assets/` |
| الخطوة السابقة (مُغلَقة) | M17-T02-REST + M17-T03 (DOC-37) — PR #27 (غير مدموج) ثم PR #29 (مدمج في `2735523`) |
| الخطوة التالية | **MERGED — STOP.** لا React (M17-T04) قبل موافقة Brain (DOC-39 §2/§9) · المتبقي بيد المالك: smoke Colab الحي (خطوات PHASE_M18_T01.md §5) |

## انحرافات عن DOC-39
- الفرع مقيّد من المنصة (`arena/019fed9c-…`) — لم أُنشئ فرعًا جديدًا.
- **لقطة Colab بمتصفح حقيقي غير ممكنة من الساندبوكس** (CDN الخاصة بـPlaywright/Chromium ومرايا apt محجوبة، ولا جلسة Colab بلا creds) — عوّضتُ بدليل بصري مولّد من شجرة الـrender الحية بنفس القيم والألوان + خادم حي للمعاينة، وسجّلت الخطوات الدقيقة للمالك في `PHASE_M18_T01.md`.
- `bun lint`/`bun build` لم يُنفَّذا — لا bun في الساندبوكس؛ لم نلمس أي ملف frontend.
- `enqueue_selected` صار يرفض عند غياب مجلد/مساحة/حصة عند الزر نفسه (بالإضافة إلى بوابة start الموجودة) — تنفيذ حرفي لـDOC §5.3 دون تغيير queue_manager/transfer_manager (كل التحقق داخل `SelectionService`).
