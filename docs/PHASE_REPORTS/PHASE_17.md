# PHASE_17 — إصلاح استيراد حزمة Colab تلقائيًا من غلاف GitHub Artifact (M15-T02)

**TASK ID:** `M15-T02`
**العنوان:** إصلاح استيراد حزمة TeleDrive في Colab عند تنزيل GitHub Artifact wrapper
**الحالة:** `ACTIVE` — بوابات Python المحلية خضراء كلها؛ ينتظر CI الفعلي على الـPR ثم يرتقي إلى `VERIFIED COMPLETE`
**التاريخ (UTC):** 2026-08-08
**المستودع:** `https://github.com/body199-cmyk/drive-buddy-3579bf74.git`

## 1. Baseline والاستئناف

| الحقل | القيمة |
|---|---|
| Base SHA المعتمد | `1f60a37d91abeeb3cba5a0279fcdcf78f49d8264` |
| Actual start SHA | `1f60a37d91abeeb3cba5a0279fcdcf78f49d8264` (مطابق — لا فرق يُسجَّل) |
| الفرع المفحوص | `arena/019fe124-drive-buddy-3579bf74` (الفرع الجانبي الثابت للجلسة) |
| الشجرة قبل العمل | نظيفة باستثناء تقرير M15-T01 غير المدفوع (`docs/PHASE_REPORTS/PHASE_M15_T01.md` — تاريخي، لم يُمسّ) |
| آخر CI أخضر | Run [`31245258992`](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/31245258992) على `main @ 1f60a37` — Python ✓ 50s · Frontend ✓ 17s · artifact `teledrive-package` (126,821 بايت) |
| مصدر التشخيص | DOC M15-T01 + `docs/PHASE_REPORTS/PHASE_M15_T01.md`: السيناريوهات A–F مُعاد إنتاجها من main النظيفة |
| قرار baseline | `RESUME_VERIFIED`: لا تعديلات Gemini في الشجرة، HEAD يساوي قاعدة التشخيص المعتمدة نفسها |

## 2. السبب الجذري (معتمد من M15-T01)

CI يبني `teledrive_v4.5.zip` صحيحًا، لكن تنزيل `actions/upload-artifact@v4` يعطي غلافًا خارجيًا `teledrive-package.zip` يحتوي الملف الحقيقي. Cell 1 القديمة كانت تقبل اسمين دقيقين فقط → `AssertionError` («الملف غير موجود بعد mount») عند رفع الغلاف كما نُزّل، و`EOFError` (كتابة ذاتية أثناء extractall) عند إعادة تسمية الغلاف دون استخراج. كل ما بعد Cell 1 (اعتماديات/مصادقة/واجهة/تكامل) لم يكن قد بُلغ أصلًا — كود المنتج سليم ولم يُعدَّل.

## 3. التنفيذ (ضمن النطاق المسموح فقط)

### 3.1 التصميم — `resolve_package_zip()` في طبقة الخلية المولَّدة («notebook restore layer»)

أضيفت دالة مسمّاة + ثلاث مساعدات داخل مصدر Cell 1 في `python-package/teledrive/notebook_cells.py` (المصدر الواحد الذي تُولَّد منه النوتбуكان و`colab_cells.json`):

| العنصر | الدور |
|---|---|
| `_zip_member_names(path)` | قراءة قائمة الأعضاء بأمان (`None` عند تلف/غياب) |
| `_is_tested_archive(path)` | كشف المحتوى: `True` فقط لأرشيف فيه جذر `teledrive-v4.5/` و`teledrive-v4.5/requirements.lock` — الغلاف المُعاد تسميته **يفشل هذا الفحص** فلا يُعامل كحقيقي |
| `_safe_inner_member(names)` | يختار عضوًا واحدًا فقط اسم ملفه النهائي `teledrive_v4.5.zip`؛ يرفض المسارات المطلقة و`\` ومكوّنات `..` (لا path traversal) |
| `_unwrap_inner(wrapper, destination)` | يقرأ بايتات العضو → يكتبها إلى **ملف مؤقت مختلف** (`tempfile.mkstemp`, `*.part`) → **يتحقق من بنية الأرشيف الداخلي** → `os.replace` ذريًا إلى الوجهة. الغلاف يُغلق قبل النقل؛ فحتى لو كانت الوجهة هي الغلاف نفسه (حالة إعادة التسمية) **لا قراءة وكتابة على الملف نفسه أبدًا** |
| `resolve_package_zip(local_root)` | ترتيب البحث: الحقيقي في `/content` → الحقيقي في Drive (يُنسخ) → الغلاف الرسمي في أي منهما (يُفك عبر temp) → غلاف مُعاد تسميته (يكتشفه الفحص ويُفك بأمان). الغياب التام يُبقي رسالة `AssertionError` الواضحة نفسها موسّعةً بتلميح أن الغلاف مقبول كما هو. الملف التالف/الغلاف بلا عضو آمن → `RuntimeError: invalid package at <path>: <سبب>` |

### 3.2 الاختبارات — `python-package/tests/test_restore_package.py` (جديد، 16 اختبارًا)

تُرفع طبقة `Import/Assign/FunctionDef` **AST-حرفيًا** من مصدر الخلية في المولد الواحد (مع استبعاد كتلة الـ`Try` الخاصة بالـmount والسحر `!pip`) وتُنفَّذ في namespace معزول — أي أن المختبَر هو **الكود المنشور نفسه** دون Colab ودون `/content`. التغطية:

1. قبول الأرشيف المباشر دون تعديل بايتاته.
2. الغلاف يُفك إلى وجهة مختلفة عبر temp؛ الغلاف الأصلي لا يُمَس؛ لا بقايا `*.part`.
3. الغلاف المُعاد تسميته: يُكتشف أنه ليس حقيقيًا ثم يُفك (البايتات النهائية = الداخلي) — **لا EOFError**.
4–5. الغياب يُبقي خطأ «upload the tested archive» مع تلميح قبول `teledrive-package.zip`.
6. أسماء أعضاء غير آمنة (`../`، `../../x/`，مطلق، `..\`) → مرفوضة (4 حالات parametrize)، ولا ملف يُنشأ.
7. محتوى داخلي تالف / غلاف بلا عضو / ملف تالف في مسار الحزمة → رفض واضح قبل الاعتماد، والـtemp يُنظَّف.
8. مسار داخلي آمن متداخل (`nested/dir/teledrive_v4.5.zip`) مقبول (سماحية DOC للمسار الآمن المنتهي بالاسم).
9. موضعا Drive (حقيقي/غلاف) يعملان.
10. عقد بنيوي: الخلية المنشورة تستدعي `resolve_package_zip(LOCAL_ROOT)` وتحتفظ بسطور العقد (`drive mount skipped`، الـglob، الـlock).

### 3.3 إعادة التوليد والتعليمات

- `python -m teledrive.notebook_cells --write` أعاد توليد `python-package/notebook/TeleDrive.ipynb` و`public/TeleDrive.ipynb` و`colab_cells.json` من المصدر الواحد.
- `docs/RUNBOOK.md`: مصدر الحزمة (Actions artifact + يتطلب صلاحية)، أن التنزيل يعطي غلافًا يُرفع **كما هو**، وحظر إعادة التسمية، ووصف آلية Cell 1 الجديدة.

## 4. البوابات والمخرجات الحقيقية (محليًا، من `python-package` ما لم يُذكر)

| البوابة | النتيجة | المخرجات الفعلية |
|---|---|---|
| `python -m compileall teledrive` | PASS | نجاح بلا أخطاء |
| `python -m pytest -q tests` | PASS | **`322 passed in 9.08s`** (306 + 16 جديدًا)، exit 0 |
| `python teledrive_launcher.py --check` | PASS | `binding check ok: 24/41 ready actions resolve` |
| `python -m teledrive.notebook_cells --check` | PASS | `notebooks are in sync` — بعد الكتابة لا ملفات stale |
| `cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb` | PASS | byte-identical، exit 0 |
| `python -m teledrive.package_service --build --output teledrive_v4.5.zip` | PASS | `archive: teledrive_v4.5.zip` (الاختبارات سبقت البناء؛ حُذف الملف الناتج من الشجرة بعد البوابة) |
| `bun run lint` (الجذر) | PASS | exit 0 — `0 errors, 6 warnings` (تحذيرات ما قبل المهمة) |
| `bun install --frozen-lockfile` / `bun run build` (الجذر) | **BLOCKED بيئيًا** | `UNKNOWN_CERTIFICATE_VERIFICATION_ERROR downloading tarball @lovable.dev/vite-tanstack-config@2.8.5` (ونظيره `vite-plugin-hmr-gate`) — قيد TLS في بيئة الـsandbox عند تنزيل الحزم، لا عيب بناء. `bun 1.3.14`. الإثبات يُرحَّل إلى CI الفعلي للـPR (توصيلة Frontend التي كانت خضراء على main) |

> بيئة Python: افتراضية في `/tmp` مثبتة من `requirements.lock` (نجاح كامل) — خارج Git.

## 5. ما لم يُثبَت (حدود صادقة)

- **Colab حقيقي لم يُختبر**: قبول الغلاف أُثبت بمنطق الخلية نفسه في بيئة معزولة، لا في runtime Colab فعلي. لا `Colab-ready`.
- Telegram/Drive live/transfer: خارج النطاق ولم تُلمس (BLOCKED على المرحلة 10، بيد المالك).
- `bun run build` محليًا لم يكتمل لقيد الشهادة أعلاه؛ يُنتظر CI.
- تنزيل الـartifact الثنائي عبر API ما زال محجوبًا شبكيًا في هذه البيئة (كما في M15-T01) — الاكتفاء بالبناء المحلي المطابق لخطوة CI حرفيًا.

## 6. التسليم (Git/PR) — تُحدَّث قيمه النهائية بعد الدفع

- الفرع: `arena/019fe124-drive-buddy-3579bf74` — **لا فرع آخر أُنشئ أو دُفع** (قيود الجلسة؛ وهو نمط المشروع نفسه: PR #9 جاء من `arena/019fe024-...`).
- Commits تبدأ بـ `M15-T02:` — لا push إلى `main`، لا force-push/rebase/amend.
- PR URL / CI run: **يُسجَّلان فور إنشائهما.**

## 7. الحالة الصادقة

**Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.**
إصلاح Cell 1 «code-complete candidate» أيضًا حتى تجربة Colab حقيقية على الغلاف المُنزَّل فعليًا.
