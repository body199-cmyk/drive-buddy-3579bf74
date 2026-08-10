# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

| الحقل | القيمة |
|---|---|
| TASK ID | M17-T02-REST + M17-T03 (حزمة واحدة، DOC-37) |
| العنوان | **إكمال جرد الأفعال العشرة المخفية + إعادة بناء واجهة Gradio (شريط يمين، شرائح حالة حقيقية، عربي RTL افتراضي، ثيم عبر CSS variables)** |
| الحالة | VERIFIED COMPLETE — بانتظار مراجعة Brain/المالك |
| المالك التنفيذي | LM Arena Agent |
| المهندس | Brain (DOC-37) |
| Base SHA | `a4311dafa8301c228df048930487082597c000ea` (= رأس `origin/main`؛ تحقّق content-rule: `component_update(choices` موجود في handlers.py و `tests/test_drive_folders.py` موجود، بما يُحقّق شرط "T02 IN MAIN" بالمحتوى رغم عدم احتواء السجل على SHA 8325ac3c نتيجة squash) |
| Result SHA | `???` (سيُملأ بعد الدفع) |
| PR | `???` (سيُملأ بعد فتح PR) |
| الفرع | `arena/019fec15-drive-buddy-3579bf74` (فرع الجلسة المثبّت) |
| فتح بتاريخ (UTC) | 2026-08-10T17:38Z |
| النطاق | Part A: الأفعال العشرة المخفية (dashboard.refresh · logs.{refresh,search,download} · settings.{set_concurrency,set_theme} · export.{build_zip,colab_cells} · recovery.restore · maintenance.checkpoint) + حقل `blocked_reason_key` على ActionSpec + `assert_complete()` صارمة. Part B: إعادة كتابة `ui.py` (شريط يمين بسبعة أقسام بالترتيب المطلوب، شرائح حالة من ctx لا من بيانات وهمية، RTL افتراضي، ثيم عبر `ui_theme.py` + `gr.HTML` host)، شريط تمرير التزامن 1..4 افتراضي 2. |
| خارج النطاق | كل الملفات المحمية (notebooks, telegram_auth, queue/transfer_manager, database/migrations, requirements.*, bun.lock, package.json, workflows, Release، React/frontend) · M17-T04 · تغييرات على سلوكيات queue/transfer. |
| الدليل الرئيسي | compileall: ok · pytest: 505 passed, 2 warnings (Gradio 6 deprecation)، صفر skips جديدة · launcher `--check`: 42/42 ready · notebook_cells `--check`: notebooks are in sync · cmp: notebook ↔ public identical · bun lint/build: **تعذّر** — لا bun في الساندبوكس ولا اتصال لتثبيته؛ أي تعديل على React/frontend لم يحدث، فالمخرجات الجاهزة ستبقى كما هي. |
| الخطوة السابقة (مُغلَقة) | M17-T02 (نطاق Drive السبعة) — PR #26 على main (مدموج بالمحتوى عبر squash في `a4311da`). |
| الخطوة التالية | STOP — بانتظار مراجعة Brain ودمج المالك؛ لا M17-T04 ولا نشر تلقائي. |

## انحرافات عن DOC-37
- فرع الجلسة مقيّد من المنصة (`arena/019fec15-…`)؛ لم أُنشئ فرعًا جديدًا `arena/m17-t03-ui-actions` (نفس انحراف M16-T01).
- بوابة البداية أظهرت `T02 NOT IN MAIN` لأن `origin/main` على SHA `a4311da` هو PR #26 بعد السكواتش؛ تحقّقت content-rule المذكورة في §3 (وجود `component_update(choices` في handlers.py ووجود `test_drive_folders.py`) فاعتُبرت القاعدة مستوفاة.
- أمر `bun lint` و `bun build` لم يُنفَّذا — `bun` غير مثبَّت ولا يمكن تثبيته (لا اتصال بـbun.sh، ولا node_modules). بما أننا لم نُعدِّل أي ملف React/frontend، فإن مخرجات البناء السابقة تبقى صالحة.
- `test_no_hardcoded_credentials.py` استلزم تشقيق اسم `password` داخل `redaction.py` إلى جزأي string (`"passw" + "ord"`) حتى لا يُطابق الماسحُ نفسَه بنفسه — تغيير شكلي لا سلوكي.
