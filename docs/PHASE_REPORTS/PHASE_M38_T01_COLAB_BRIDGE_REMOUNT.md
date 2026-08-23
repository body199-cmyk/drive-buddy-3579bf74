# PHASE M38-T01 — إصلاح إعادة تركيب جسر React–Gradio في Colab

> **الحالة:** Code-complete candidate + Fake-tested + proxy-verified. لا `Colab-ready` ولا `Complete` قبل فتح لوحة Colab الحية بعد نشر الحزمة.

| الحقل | القيمة |
|---|---|
| Task ID | `M38-T01` |
| الفرع | `fix/m38-t01-colab-bridge-remount` |
| خط الأساس | `main` / `origin/main` عند `c9c1a769eb9d646d8aa564a0a6e1fa94907486c9` |
| النطاق | `react_panel.py`، أصل panel المضمّن، وعقد React فقط؛ بلا نوتبوك أو اعتماديات أو جلسات |
| نقطة التراجع | حذف الفرع أو عكس commit M38 قبل الدمج؛ لا بيانات Drive أو Telegram ضمن النطاق |

## البلاغ والدليل

أظهرت واجهة Colab المنشورة رسالة **`Backend bridge unavailable`** مع تجمد عناصر لوحة React. سجلات Cell 4 نفسها أثبتت أن `react.bridge.request` رُبط بـ`handlers.bridge_request`، وأن Drive اتصل بنجاح؛ ولم يكن Telegram متصلًا بعد، وهي حالة اعتيادية لا ينبغي أن تمنع واجهة React.

تمت مطابقة مرجع الحزمة الذي أبلغ عنه المستخدم مع manifest العام: الحزمة لم تكن قديمة. كما أثبت الفحص المحلي ومحاكاة proxy ذات `root_path` خارجي أن الجسر يبدأ حيًا عندما يركب بصورة واحدة، ولذلك لا يُنسب العيب إلى Telegram أو Drive أو شكل الرابط.

## السبب الجذري والإصلاح

مسار `ReactPanel.js_on_load` كان ينشئ مثيلًا جديدًا من `TeleDriveGradioPanel` كلما أعاد Gradio تركيب HTML، من دون امتلاك للمثيل السابق أو cleanup تعيدها lifecycle. إذا أعاد Gradio تركيب العنصر بعد أن أُغلق مثيل سابق، قد تبقى شجرة React القديمة مرتبطة بجسر `disposed`؛ وهذا هو الشرط الوحيد في `GradioTeleDriveBridge` الذي يعيد الرسالة الظاهرة.

الإصلاح محدود في `_PANEL_ON_LOAD`:

1. يخزن المثيل الحي على العنصر نفسه تحت مفتاح خاص.
2. يفك المثيل السابق قبل تركيب التالي.
3. يعيد cleanup function لا تفك إلا المثيل الذي تملكه، ثم تمسح المرجع.
4. لا يغير transport الرسمي `props.value` و`trigger('submit')`، ولا يفتح endpoint أو socket أو تخزين متصفح.

## الاختبارات المنفذة

| الفحص | النتيجة |
|---|---|
| `python3 -m compileall teledrive` | PASS |
| `python3 -m pytest -q tests` | **746 passed** |
| `python3 teledrive_launcher.py --check` | **51/51** ready actions resolve |
| `python3 -m teledrive.notebook_cells --check` | PASS |
| `cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb` | PASS |
| `pnpm run lint` | PASS؛ تحذير baseline واحد فقط عن eslint-disable غير مستخدم |
| `pnpm run build` | PASS |
| `pnpm dlx tsx --test tests/teledrive-sandbox.contract.test.mjs` | **27/27** PASS |
| محاكاة Gradio 6.20 + reverse proxy + `root_path` | لوحة حية بحالة اتصال منفصلة؛ لا banner blocked |

تمت إضافة عقد `18b` **تنفيذي** يستخرج جسم `js_on_load` ويشغله على mock لعنصر Gradio و`TeleDriveGradioPanel`: يثبت أن remount يفك الجسر السابق، وأن cleanup قديم لا يفك الجسر الجديد، وأن cleanup الحالي يمسح مرجعه. أُعيد بناء `panel.bundle.gz` من المصدر بعد التغيير.

## الاختبار الحي وما لم يثبت

فتح الوكيل نوتبوك Colab الرسمي بحساب الاختبار ووصل إلى runtime جديد؛ Cell 1 نزّل الحزمة الموثقة وCell 2 أنشأ `ApplicationContext`. لكن Cell 3 توقف عند fallback إدخال بيانات Telegram لعدم وجود Session Vault لهذا حساب Drive، ثم بقي التنفيذ معلقًا قبل تشغيل Cell 4. لذلك **لم يثبت هذا التقرير نجاح لوحة Colab الحية بعد الإصلاح**، ولا يدعي نجاح Telegram أو نقل Drive.

## GitHub

| العملية | الحالة |
|---|---|
| Commit | NOT ATTEMPTED |
| Push | NOT ATTEMPTED |
| Pull Request | NOT ATTEMPTED |
| Merge | NOT ATTEMPTED |
| Publish | NOT ATTEMPTED |

الخطوة التالية: مراجعة الفرق وفحص الأسرار، ثم commit وPR وCI والدمج والنشر فقط ضمن تفويض المالك الصريح.
