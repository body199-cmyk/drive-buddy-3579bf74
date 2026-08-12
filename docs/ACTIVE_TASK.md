# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

| الحقل | القيمة |
|---|---|
| TASK ID | M20 (T01…T05 — حزمة واحدة مترابطة) |
| العنوان | **واجهة نهارية إجبارية + تتابع منطقي 1→5 + رفع سقف التزامن إلى 100** — `theme.py` يحيّد لوحة Gradio الداكنة على مستوى متغيرات CSS ويشطب صنف `dark` باستمرار؛ `flow.py` + `ui_flow_view.py` يشتقان الخطوة الحالية من حالة السياق الحية و`ui.py` أُعيد بناؤه إلى خمس بطاقات مرقّمة رأسية بدل التبويبات المتجاورة؛ `HARD_CONCURRENCY_CAP = 100` بموجب ADR-0001 مع تحذير إجباري فوق 8 |
| الحالة | **CODE-COMPLETE CANDIDATE + FAKE-TESTED** — البوابات خضراء (`629 passed` · launcher `46/46` · النوت‌بوكان متطابقان · `cmp` OK · `package_service --build` OK · `eslint` 0 errors · `vite build` OK)؛ الإثبات البصري الحي في Colab بيد المالك (KNOWN_ISSUES #43). **ممنوع ادّعاء `Colab-ready` أو `Complete`** |
| المالك التنفيذي | LM Arena Agent |
| المهندس | Brain (§10) |
| Base SHA | `77e97b789583b07b375f188894a5aca796b03b68` (= رأس `origin/main`، آخر مدموج PR #34 — مُتحقق `git rev-parse HEAD` == `origin/main`) |
| Result SHA | انظر PR من الفرع `arena/019ff3b0-drive-buddy-3579bf74` (غير مدموج — الدمج بيد المالك) |
| النطاق | **جديد:** `teledrive/theme.py` · `teledrive/flow.py` · `teledrive/ui_flow_view.py` · `tests/test_flow.py` · `tests/test_ui_contract_proofs.py` · `python-package/docs/decisions/ADR-0001-concurrency-cap-100.md`. **معدَّل:** `config.py` · `services.py` · `handlers.py` · `action_registry.py` · `ui_binder.py` · `app_context.py` · `app.py` · `ui.py` · `locale/ar.json`+`en.json` · 8 ملفات اختبار + ملفات الذاكرة |
| خارج النطاق | `transfer_manager.py` · `queue_manager.py` · `database.py` · `migrations.py` · `drive_auth.py` · `drive_client.py` · `telegram_auth.py` · `telegram_client.py` · `checkpoint_manager.py` · `storage_manager.py` · `async_runtime.py` · `redaction.py` · `tests/mocks/` · النوت‌بوكات · `notebook_cells.py`/`colab_cells.json` · `requirements.*` · `.github/` · React/frontend |
| الدليل الرئيسي | `compileall` OK · `pytest`: **629 passed** (كان 596؛ +33) · launcher: **46/46** (45 + `flow.sync`) · `grep "gr.Tab(\|themes.Soft" teledrive/ui.py` → لا شيء · خادم Gradio حي على `0.0.0.0:7860` والصفحة المُقدَّمة تحوي `--td-bg:#F4F0F5` و`color-scheme: light` و`MutationObserver` · فحص التتابع الحي: `connect → analyze → select → queue` ثم عودة إلى `connect` فور سقوط درايف · PHASE_M20 |
| الخطوة السابقة (مُغلَقة) | M19-T01 — خمس مناطق + ثيم oklch (PR #34، مدموج في `77e97b7`) |
| الخطوة التالية | **STOP — بانتظار دمج المالك لـPR M20**؛ ثم: إعادة نشر التاج `pkg-2026.08.09-m15t07` يدويًا من main الجديد (#27) ← في Colab: Restart runtime ← Cell 1 ← الخلايا 2–4 ← فحص بصري: الصفحة نهارية حتى على متصفح داكن، المؤشر يعرض 🔵 1 والخطوات 2–5 مخفية، والسلايدر 1..100 مع التحذير فوق 8 |

## انحرافات عن §10 / نقاط صدق

- **الأساس ليس `ad3a454`** المذكور في ملف المهمة بل `77e97b7` (رأس `main` الفعلي). النسخة المحلية shallow بعمق 1 و`gh` يرد `401 Bad credentials`، فتعذّر إثبات علاقة النسب بين الاثنين — سُجِّل الانحراف بدل الادّعاء. اسم الفرع مثبَّت من المنصة (`arena/019ff3b0-…`) بدل الاسم المقترح في الملف.
- **تصحيح أمين لملف المهمة:** الملف كُتب على `ad3a454` حيث 18 إجراءً كانت `tested=False` ومرسومة مخفية. على الأساس الحقيقي كانت الـ45 **كلها** `tested=True` ببراهين أقوى من الجدول المقترح، فلا وجود لأزرار ميتة تُظهَر ولم يُخفَّض أي برهان. أُضيف `flow.sync` فصار الإجمالي 46.
- **الدمج بدل الاستبدال (بأمر المالك الصريح):** `theme.py` أُضيف بجانب `ui_theme.py` القائم، و`ui.py` الجديد دُمج في القشرة الحالية بدل استبدالها حرفيًا — لذلك بقيت لوحتا oklch وربط `settings.set_theme` واللوحات الأربع لمجلد Drive وكل اختبارات الواجهة السابقة تعمل.
- **اكتشاف حقيقي أثناء التنفيذ:** الحارس الثاني لا يعمل عبر `gr.HTML` لأن Gradio يُدرج محتوى المكوّن بـ`innerHTML` فلا يُنفَّذ `<script>` (تحذير Gradio صريح)؛ نُقل إلى `head=`/`js=` في `launch()`.
- **مخاطر مقبولة من المالك:** التزامن فوق 8 غير مختبر مقابل ذاكرة Colab الحقيقية وحدود تيليجرام (#44)، وبراهين M20 على مستوى الربط لا التكامل الحي (#45).
- `bun` غير قابل للتنصيب في الساندبوكس (حاجز TLS على `bun.sh`)، فشُغِّلت بوابتا lint/build بنفس سكربتات `package.json` عبر npm — والتعديل لا يمس أي ملف frontend، وCI يشغّل نسختَي bun على الـPR.
