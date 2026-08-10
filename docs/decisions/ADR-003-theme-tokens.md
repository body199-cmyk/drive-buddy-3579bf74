# ADR-003 — CSS Variables كمصدر وحيد للألوان (ui_theme.py)

**الحالة:** مقبول (مطبَّق في M17-T03)
**التاريخ:** 2026-08-10
**المرجع:** DOC-37 §5.2 + §6

## السياق
قبل M17-T03:
- الثيم في TeleDrive كان ثابتًا في `GRAPHITE_CSS` داخل `ui.py` بألوان hardcoded (رمادي/أخضر).
- `settings.set_theme` كان يُخزِّن التفضيل في SQLite دون أي أثر بصري فعلي (KNOWN_ISSUES #29) — زر بلا وظيفة.
- إضافة light theme أو ألوان مخصصة كانت تتطلب تعديل CSS في `ui.py` نفسه، مما يخلط التخطيط بالألوان.

## القرار
1. **ملف واحد للألوان:** `teledrive/ui_theme.py` يحتوي:
   - `PALETTES = {"dark": {...}, "light": {...}}` — معجمات key→hex لكل الألوان (bg, surface, surface_2, border, text, muted, accent, accent_text, ok, warn, err).
   - `BASE_CSS` — كل قواعد CSS الثابتة، وتستخدم حصريًا `var(--td-*)` بدون أي لون hardcoded.
   - `theme_style_block(theme)` → `str` يُعيد وسم `<style id="td-theme-vars" data-td-theme="…">:root, .gradio-container { --td-bg: …; …}</style>`.
2. **لا ألوان في ui.py:** التخطيط يضيف `elem_classes`/`elem_id` فقط ويعتمد على CSS variables؛ استيراد Gradio الوحيد هو `theme=_graphite_theme()` كأساس هش (Gradio 6 اشتراط).
3. **زر الثيم يفعّل التبديل فعليًا:** `gr.HTML(elem_id="td-theme-vars-host")` غير المرئي يحمل كتلة `<style>`؛ الـhandler `h_settings_set_theme` يُرجّع `component_update(value=theme_style_block(chosen))` فيُستبدل المحتوى في المتصفح. يُحفَظ الاختيار في SQLite عبر `PreferencesService` ويُستعاد عند الإقلاع.
4. **RTL/LTR directions** جزء من BASE_CSS (`.td-rtl { direction: rtl; }`, `.td-ltr { direction: ltr; }`) و`dir="ltr"` على النصوص المختلطة (ids، مسارات، SHA) منعًا لتشوّهها في الواجهة العربية.

## العواقب
- **موجب:** KNOWN_ISSUES #29 و#33 مغلقتان؛ التبديل بين dark/light يعمل فعلًا.
- **موجب:** المصمم (أو الـagent لاحقًا) يستطيع إنشاء ثيم جديد بإضافة مدخل إلى PALETTES فقط دون لمس `ui.py`.
- **موجب:** عقد الاختبار يمنع رجوع ألوان hardcoded لاحقًا (`test_no_hardcoded_colors_in_ui` يفحص AST لـui.py).
- **سالب:** Gradio 6 ألقى `UserWarning` أن `theme=` و`css= في Blocks` deprecated وينبغي نقلهما إلى `launch()`؛ أبقيناهما في Blocks(…) لأن `ui.py` لا يستدعي `launch()` بنفسه (يتولاّه `app.py`) — تحذير غير كاسر وسيُعالج في مرحلة لاحقة عندما ننقل المسار بأكمله إلى launch() دون كسر الاختبارات الحالية.
