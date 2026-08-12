# PHASE REPORT — M19-T01 — إعادة تصميم واجهة Gradio (طبقة عرض فقط)

> الدستور v5.0 · الفرع `arena/019ff35c-drive-buddy-3579bf74` · Base `6281a66` (رأس `main`) · 2026-08-12.

## 1. الهدف
إعادة تنظيم واجهة Gradio لتكون واضحة وعصرية ومتجاوبة بثيم نهاري/ليلي، **مع الحفاظ الكامل على الوظائف** (كل `action_id`/معالج/ترتيب مدخلات-مخرجات/عدد مخرجات). طبقة عرض فقط — لا منطق ولا نقل ولا قاعدة ولا نوت‌بوك.

## 2. فحص البداية (§0)
- `git rev-parse HEAD` = `6281a66133b6018a10501d21c116a582dbbcb114` = `origin/main` (آخر مدموج PR #33). ✅ الأساس هو آخر `main` الفعلي.
- SHA «النتيجة المعروفة» في المهمة `98d4a21…` **غير موجود** في شجرة `main` (`git cat-file` فشل) — إنه PR سابق غير مدموج على فرع منفصل، فالبناء الصحيح يكون من آخر `main`.
- البوابات قبل التعديل: `compileall` OK · `pytest -q tests` → **589 passed** · `launcher --check` → **45/45**.

## 3. جرد الإجراءات (§6.2)
`action_registry.ACTION_SPECS`: **45 إجراءً، كلها ready**. توزيع الأقسام: connection 14 · analyze 9 · transfers 11 · dashboard 1 · logs 3 · settings 5 · export 2.
كل زر في `ui.py` يُنشأ عبر `binder.button`/`binder.register` ويُربط عبر `binder.wire` بنفس `action_id` والمعالج المُعلَن. عدد الربطات (controls) قبل وبعد = **55** (محفوظ).

## 4. ما تغيّر (العرض فقط)
| الملف | التغيير |
|---|---|
| `teledrive/ui_theme.py` | لوحتا oklch (نهاري/ليلي) مستقلتان + `BASE_CSS` استجابي (عرض أقصى 1280، سلم مسافات 4/8/12/16/24/32، لمس ≥44px، شريط تنقل سفلي ≤900px، جداول تتمرر أفقيًا). `--td-primary` للأفعال الرئيسية، `--td-success`/`--td-danger` للحالات الحقيقية. حُوفظ على مفاتيح الـtokens + `--td-lime` للتوافق الخلفي. |
| `teledrive/ui.py` | خمس مناطق خلف تبويبات Gradio الأصلية (شريط تنقل واحد)؛ دمج لوحة التحكم في «مركز الاتصال» ودمج التصدير في «الإعدادات»؛ حُذف الشريط الجانبي الأيمن المكرر. كل الربطات محفوظة حرفيًا (المدخلات/المخرجات/الـarity). |
| `locale/ar.json` + `en.json` | 3 مفاتيح نصوص فقط. |
| `tests/test_ui_layout_contract.py`, `tests/test_ui_colab_render_contract.py` | تحديث أمين للبنية الجديدة (5 مناطق؛ لوحة oklch الداكنة). |
| `tests/test_m19_t01_ui_preservation.py` | جديد: 7 اختبارات حفاظ (عدّاد الإجراءات/الربطات لا ينخفض، أزرار تيليجرام مربوطة بنفس `action_id`، الثيم يستخدم الربط الحالي، الاتجاه يصمد). |

## 5. البوابات (مخرجات حقيقية من `python-package/.venv`)
```
$ python -m compileall -q teledrive                 → exit 0
$ python -m pytest -q tests                         → 596 passed in 23.29s   (was 589; +7)
$ python teledrive_launcher.py --check              → binding check ok: 45/45 ready actions resolve
$ python -m teledrive.notebook_cells --check        → notebooks are in sync
$ cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb → identical
$ python -m teledrive.package_service --build --output teledrive_v3.1.zip → tests passed · archive OK (414036 بايت)
$ git diff --stat                                   → 7 ملفات (6 معدَّلة + 1 جديد)، +439/−390
```
- `bun run lint`/`bun run build`: **NOT ATTEMPTED** — `bun` غير منصب و`node_modules` غائبة في الساندبوكس؛ والتعديل لا يمس React/frontend إطلاقًا فتغطيهما CI.

## 6. الملفات المحمية (لم تُلمس)
`telegram_auth.py` · `telegram_client.py` · `drive_auth.py` · `drive_client.py` · `services.py` · `queue_manager.py` · `transfer_manager.py` · `database.py` · `migrations.py` · `handlers.py` · `action_registry.py` · `ui_binder.py` · النوت‌بوكات · `notebook_cells.py` · `colab_cells.json` · `requirements.*` · `bun.lock` · `package.json` · `.github/` · React/frontend — أكّده `git diff --stat`.

## 7. انحرافات ونقاط صدق
- **النهاري كافتراضي غير مطبَّق**: الافتراضي `"dark"` مُصلَّب في `PreferencesService.set_theme`/`current_theme` (`services.py`) وفي `shell_seed` (`handlers.py`) — كلاهما محمي. Lauحتُ اللوحتين كاملتين وتبديل الثيم يعمل في الاتجاهين، لكن الافتراضي المُستمر يبقى ليليًا. التحويل للنهاري-كافتراضي يحتاج تفويضًا منفصلًا للمس `services.py` (§4 من المهمة).
- شريط التنقل السفلي على الجوال: مُنفَّذ بـCSS خالص (تبويبات Gradio الأصلية مُعاد تصميمها)؛ التحقق البصري الدقيق يحتاج Colab حي بيد المالك.
- لا متصفح/Colab في الساندبوكس → الإثبات الحي بيد المالك (KNOWN_ISSUES #41، M15-T01). لا يوجد ادّعاء `Complete` أو `Live-ready`.

## 8. الخطوة التالية
**STOP — بانتظار دمج المالك لـPR.** بعد الدمج: إعادة نشر التاج يدويًا (KNOWN_ISSUES #27) ← Restart runtime ← Cell 1 ← الخلايا 2–4 ← فحص بصري للمناطق الخمس والثيمَين وRTL/LTR.
