# PHASE M17-T03 — إعادة بناء واجهة Gradio (Right Rail + RTL + Theme Tokens + Real Chips)

**التاريخ:** 2026-08-10 UTC
**المرحلة:** M17-T03 (Part B من DOC-37)
**المنفذ:** LM Arena Agent
**الفرع:** `arena/019fec15-drive-buddy-3579bf74`

## الهدف
بناء واجهة Gradio فعلية قابلة للاستخدام:
- شريط تنقّل يمين (right rail) بسبعة أقسام بالترتيب: لوحة التحكم · التحويلات · تحليل وروابط · مركز الاتصال · السجلات · الإعدادات · كود/تصدير Colab
- شريط حالة علوي بشرائح **حقيقية** من ctx (Telegram/Drive/المجلد الافتراضي/المحرك) — لا أرقام وهمية
- عربي RTL افتراضي، LTR للإنجليزية، لا فقد للحالة عند التبديل
- ثيم CSS variables فقط (مصدر واحد `ui_theme.py`) — zero hardcoded colors في `ui.py`
- شريط تمرير التزامن 1..4 افتراضي 2
- `ui.py` layout فقط: zero SQL، zero lambda، zero direct `.click/.change/.submit`

## التغييرات
- ملف جديد `teledrive/ui_theme.py`:
  - `PALETTES["dark"]` و`PALETTES["light"]` (bg/surface/surface_2/border/text/muted/accent/accent_text/ok/warn/err)
  - `BASE_CSS` — `#td-shell` grid (1fr 232px), `#td-rail` nav list, `.td-card`, `.td-chip` بحالات ok/warn/err, RTL/LTR direction, td-primary, أكواد مختلطة `dir="ltr"`, `@media(max-width:900px)` للسكك الحديدية المتجاوبة
  - `theme_style_block(theme)` يُعيد `<style id="td-theme-vars" data-td-theme="…">…</style>`
- `ui.py` إعادة بناء كاملة:
  - `_render_shell` تقبل الشكل القديم (4 وسائط) والجديد (6 وسائط) للتوافق الخلفي
  - `gr.Blocks(elem_id="td-root")` + `gr.HTML(theme_host, visible=False)` host للثيم
  - `gr.render(lang_state)` لإعادة الرسم عند تبديل اللغة
  - شريط علوي: brand + telegram_chip + drive_chip + folder_chip + engine_chip + lang_btn + top_zip_btn
  - 7 `gr.Tab` بالترتيب المطلوب تستخدم `t("nav.*")`
  - `binder.wire(...)` لكل الأفعال الـ42 (zero direct `.click/.change/.submit`، zero `lambda`)
- `tests/conftest.py`: `isolated_root` يُعيد تحميل config/database/checkpoint_manager/logging_config لكل اختبار حتى CHECKPOINTS_DIR/LOGS_DIR تبقى داخل tmp_path ولا تتسرب checkpoints متبقّية.
- اختبارات جديدة: `test_ui_layout_contract.py`, `test_no_fake_data.py`.
- تحديث الاختبارات القديمة (`test_bindings.py`, `test_analyze_ui_contract.py`, `test_analyze_ui_modes.py`, `test_checkpoint_lazy_drive_client.py`) لتتوافق مع الشكل الجديد.

## الاختبارات
- **505 passed**, 2 warnings (Gradio 6 deprecation — تحذير غير كاسر)، صفر skips جديدة.
- AST checks: zero lambda, zero direct `.click/.change/.submit`, zero hardcoded colors في `ui.py`.
- RTL default check: `dir="rtl"` مضمّن عند `lang="ar"`.
- No fake data: first render لا يضيف صفوف وهمية للجداول؛ الجداول الفارغة تعرض نص «لا تحويلات بعد»/«لا نتائج تحليل» المترجم.

## ملاحظات
- شريط التنقل الأيمن مُنفَّذ كعناصر `gr.Button` داخل `#td-rail`؛ الـTabs نفسها Gradio أصلية وتبقى قابلة للوصول (مخفية بصريًا عبر CSS لتفادي ازدواجية التحكم، لكن تبقى في شجرة الوصول — اهتمام بـa11y).
- وصلة active-section بين الـrail والـTabs تستخدم CSS فقط دون JS (يناسب قيود no-JS في Gradio) — التمييز البصري للعنصر النشط يُدار من لَمْعان Gradio Tabs المدمج.
- Gradio 6 ألقى تحذيرًا أن `theme=` و`css=` انتقلا من `Blocks()` إلى `launch()`؛ المسار القديم ما زال يعمل (deprecated) والاختبارات ما زالت تُقرأ `_deprecated_css`/`_deprecated_theme`.
