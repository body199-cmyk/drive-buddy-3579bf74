# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

| الحقل | القيمة |
|---|---|
| TASK ID | M19-T01 |
| العنوان | **إعادة تصميم واجهة Gradio: خمس مناطق + ثيم oklch نهاري/ليلي + استجابة (طبقة عرض فقط)** — أُعيد تنظيم `ui.py` إلى 5 مناطق خلف شريط تنقل واحد (تبويبات Gradio الأصلية؛ حُذف الشريط الجانبي المكرر)، وأُعيد بناء `ui_theme.py` بلوحتَي oklch مستقلتين وCSS استجابي، مع الحفاظ الحرفي على كل `action_id`/المعالج/ترتيب المدخلات-المخرجات/الـarity (45 جاهزًا، 55 ربطًا = baseline) |
| الحالة | CODE-COMPLETE CANDIDATE — بوابات Python خضراء (`596 passed` · launcher `45/45` · النوت‌بوكان متطابقان · `cmp` OK · `package_service --build` OK)؛ `bun lint`/`build` NOT ATTEMPTED (#37 — لا bun في الساندبوكس والتعديل لا يمس frontend)؛ الدمج وإعادة نشر التاج والإثبات الحي في Colab بيد المالك |
| المالك التنفيذي | LM Arena Agent |
| المهندس | Brain (§10) |
| Base SHA | `6281a66133b6018a10501d21c116a582dbbcb114` (= رأس `origin/main`، آخر مدموج = PR #33 — مُتحقق بفحص §0) |
| Result SHA | انظر PR من الفرع `arena/019ff35c-drive-buddy-3579bf74` (غير مدموج — الدمج بيد المالك) |
| النطاق | عرض فقط: `teledrive/ui.py` + `teledrive/ui_theme.py` + `locale/ar.json`+`en.json` (3 مفاتيح) + اختبارات الواجهة (`test_ui_layout_contract.py`, `test_ui_colab_render_contract.py`) + اختبار حفاظ جديد (`test_m19_t01_ui_preservation.py`) + ملفات الذاكرة |
| خارج النطاق | كل المنطق/النقل/قاعدة البيانات · `handlers.py`/`action_registry.py`/`ui_binder.py` · النوت‌بوكات · `notebook_cells.py`/`colab_cells.json` · `.github/` · الاعتماديات · React/frontend |
| الدليل الرئيسي | `compileall` OK · `pytest`: **596 passed** (كان 589؛ +7) · launcher `--check`: **45/45** · `notebook_cells --check` متزامنة · `cmp` متطابقان · `package_service --build` OK (+414036 بايت) · `git diff --stat`: 7 ملفات (6 معدَّلة + 1 جديد)، +439/−390 · PHASE_M19_T01 |
| الخطوة السابقة (مُغلَقة) | M18-T03 — PR من `arena/019ff2cd-…` (غير مدموج بعد حسب آخر مراجعة). تاريخ شجرة `main` حتى `6281a66` لا يحوي `98d4a21` (نتيجة M18-T03 على فرع منفصل). |
| الخطوة التالية | **STOP — بانتظار دمج المالك لـPR M19-T01**؛ ثم: إعادة نشر التاج `pkg-2026.08.09-m15t07` يدويًا من main الجديد (KNOWN_ISSUES #27) ← في Colab: Restart runtime ← Cell 1 ← الخلايا 2–4 ← فحص بصري للمناطق الخمس والثيمَين وRTL/LTR. أما «النهاري كافتراضي» فيحتاج تفويضًا منفصلًا للمس `services.py` (KNOWN_ISSUES #42). |

## انحرافات عن §10 / نقاط صدق

- **النهاري ليس الافتراضي**: يتطلب تغيير الافتراضي في `PreferencesService` (`services.py`) و`shell_seed` (`handlers.py`) — كلاهما محمي. Lauحتُ الواجهة تشحن اللوحتين كاملتين وتبديل الثيم يعمل في الاتجاهين واختُبر، لكن الافتراضي المُستمر يبقى ليليًا (KNOWN_ISSUES #42).
- `bun run lint`/`build` غير قابلين للتشغيل في الساندبوكس (لا `bun`/`node_modules`، #37)؛ والتعديل لا يمس React/frontend إطلاقًا فتغطيهما CI على الـPR.
- لا متصفح/Colab حي في الساندبوكس → الإثبات الحي بيد المالك (KNOWN_ISSUES #38/#41، M15-T01). لا ادّعاء `Complete` أو `Live-ready`.
