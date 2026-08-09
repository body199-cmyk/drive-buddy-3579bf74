# PHASE_19 — M15-T04: تشخيص اتصال Telegram وإعادة بناء واجهة Colab الاحترافية (الغرافيت RTL/LTR) مع الحفاظ على التحكم الحقيقي

**TASK ID:** `M15-T04`
**العنوان:** تشخيص اتصال Telegram وإعادة بناء واجهة Colab الاحترافية مع الحفاظ على التحكم الحقيقي
**الحالة:** `VERIFIED COMPLETE` — بوابات Python المحلية كاملة خضراء (360 passed)؛ بوابتا الواجهة الأمامية مؤجلتان إلى CI (حاجز شبكة الحاوية، موثق أدناه)
**التاريخ (UTC):** 2026-08-09
**المستودع:** `https://github.com/body199-cmyk/drive-buddy-3579bf74.git`

## 1. Baseline والاستئناف

| الحقل | القيمة |
|---|---|
| Base SHA المعتمد | `a8929521359b0eab184e800412d2e0e829b0312a` (رأس `main` = دمج PR #11, M15-T03) |
| Actual start SHA | `a8929521359b0eab184e800412d2e0e829b0312a` (مطابق؛ `git status` نظيف) |
| الفرع المفحوص | `arena/019fe6c5-drive-buddy-3579bf74` (فرع جلسة Arena الثابت؛ لا يُنشأ فرع آخر) |
| حالة PR #11 | `MERGED` في `2026-08-08T16:33:30Z` عند merge commit `a892952` — لم يُعَد استخدامه |
| آخر CI أخضر على main | Run `31267239045` — `status: completed`, `conclusion: success` |
| قرار baseline | `RESUME_VERIFIED`: HEAD مطابق للقاعدة المعتمدة، وM15-T02/M15-T03 مدموجان فعلًا |
| المستند المنفَّذ | ClickUp Doc «M15-T04 — Arena execution package (fresh handoff)» (جديد مستقل؛ لم يُنفَّذ M15-T02/M15-T03 مجددًا) |

اختبارات baseline قبل أي تعديل: `compileall` PASS · `pytest` = **338 passed in 8.11s** · `launcher --check` = `24/41 ready actions resolve` · `notebook_cells --check` = in sync · `cmp` النوتبوكين = IDENTICAL.

## 2. تشخيص اتصال Telegram (المطلوب الأول)

فُحص المسار كاملًا مقابل نقاط المستند العشر:

| # | نقطة الفحص | النتيجة | الدليل |
|---|---|---|---|
| 01 | `set_credentials` ينشئ عميلًا واحدًا | PASS | `tests/test_telegram_flow_contract.py::test_set_credentials_creates_exactly_one_client`؛ المصنع يُستدعى مرة واحدة تحت `RLock` |
| 02 | Telethon User Account وليس Bot API | PASS | `telegram_client.py` يستخدم `TelegramClient(session, api_id, api_hash)` و`sign_in(phone…)`؛ لا `bot_token` في الشجرة |
| 03 | Cell 3 تجمع API ID/Hash مخفيين | PASS | `colab_cells.json` Cell 3: `getpass.getpass(...)` مرتين، بلا طباعة أو تخزين |
| 04 | Cell 4 نفس السياق/العميل/الـ loop | PASS | Cell 4 تستدعي `ctx.telegram_auth.set_credentials` ثم `launch(ctx)`؛ سياق واحد عبر `create_context/get_context`، وloop واحد مملوك لـ `AsyncRuntime` (محروس بـ `tests/test_no_ad_hoc_loops.py`) |
| 05 | الواجهة تستخدم API العامة فقط (7 دوال) | PASS | اختبار جديد `test_telegram_actions_resolve_only_the_public_auth_apis`: مجموعة `service_path` لإجراءات Telegram السبعة = المجموعة العامة حرفيًا، وكلها تحل على `ctx.telegram_auth` نفسه |
| 06 | lifecycle/loop/Deps/handler outputs/Gradio build/ctx.resolve | PASS مع ملاحظة | إصدارات مثبتة: Gradio **6.20.0**، Telethon **1.44.0** (من `requirements.lock`)؛ بناء Gradio حقيقي نُفِّذ في الحاوية (`BUILD OK: Blocks`، 24 فعلًا مربوطًا)؛ `ctx.resolve` يرفع على المسارات المجهولة. الملاحظة: Gradio 6 نقل `theme/css` من مُنشئ Blocks إلى `launch()` (تحذير deprecation) — انظر §4.2 |
| 07 | تشغيل الاختبارات الحالية وتحديد الفشل الفعلي | PASS | 338/338 خضراء عند baseline؛ لا فشل قائم |
| 08 | إصلاح أقل مسار لعيب حقيقي + contract test | **عيبان حقيقيان — انظر أدناه** | العيب (أ) في `progress_tracker.py`؛ العيب (ب) في `ui.py` نفسه وكان هدف المهمة الأصيل |
| 09 | لا كشف API ID/Hash في التشخيص | PASS | كل التشخيص بمثبتات وهمية (`"12345"`, `"abc"`) كما تفعل المجموعة القائمة |
| 10 | لا fake tests كإثبات اتصال حقيقي | PASS | الحالة الصادقة أدناه تبقى `unverified` |

### 2.1 عيب حقيقي (أ): `ProgressTracker.snapshot()` يعلِّق نفسه (self-deadlock)

- **الوصف:** `snapshot()` يمسك `threading.Lock` غير القابل لإعادة الدخول ثم يستدعي داخله `instant_speed()` و`average_speed()` و`eta_seconds()` وكلها تطلب القفل نفسه → **تعليق دائم عند أول نداء**.
- **لماذا لم يُكشف سابقًا:** إجراء `dashboard.refresh()` ما يزال `tested=False` (لا زر حي)، و`StatsService.dashboard()` لا يُستدعى في أي اختبار، فظل `snapshot()` بلا تنفيذ فعلي.
- **إثبات التنفيذ الحقيقي:** استدعاء مباشر لـ `ProgressTracker().snapshot()` علّق العملية (timeout).
- **الإصلاح الأدنى:** سطر واحد: `threading.Lock()` → `threading.RLock()` في `python-package/teledrive/progress_tracker.py`.
- **Contract test:** تغطى عمليًا عبر `tests/test_ui_shell_contract.py::test_fresh_render_shows_no_fake_rows_logs_or_connected_states` الذي يستدعي `ctx.stats.dashboard()` (→ `snapshot()`) في كل render pass — كان سيعلّق قبل الإصلاح.
- **الشفافية:** `progress_tracker.py` خارج قائمة «الملفات المتوقع تعديلها» في DOC، لكنه ليس ضمن القائمة الممنوعة صراحة؛ قاعدة DOC §5-08 تجيز إصلاح «أقل مسار لازم» لعيب مثبت. مذكور صراحة في تقرير التسليم (بند DEVIATIONS).

### 2.2 عيب حقيقي (ب): واجهة Gradio خام بلا RTL ولا ثيم ولا إدارة حالة

الشكوى المرجعية للمالك: الواجهة الظاهرة Gradio خام غير منظمة. الفحص أثبت:
- لا يوجد أي اتجاه RTL رغم أن العربية هي الافتراضية (`DEFAULT_LANGUAGE="ar"`).
- تبديل اللغة كان يحدّث صندوق نص فقط دون إعادة تسمية أي مكوّن.
- الثيم كان يمرر لـ `gr.Blocks(theme=…)` الذي صار معتمدًا على مسار deprecated في Gradio 6 (تحذير عند البناء).
- لا شريط علوي، لا تنقل جانبي، لا بطاقات حالة، ولا بذر للمكونات من الحالة الحية.

## 3. التنفيذ المنجز (المطلوب الثاني)

### 3.1 `python-package/teledrive/ui.py` — إعادة بناء كاملة (layout فقط)

- **قشرة غرافيت داكنة** بسمات سطحية رمادية متدرجة ولمسة lime محدودة (`GRAPHITE_CSS` + `_graphite_theme()`)، مع حالات semantic ثابتة: لوحة OTP بحافة `info` زرقاء، لوحة 2FA بحافة `warning` كهرمانية، وقواعد success/error/info في متغيرات CSS.
- **شريط علوي حقيقي:** اسم TeleDrive + نسخة `4.5.0` من `ctx.config.version` (حقيقية)، شريحة حالة Telegram وشريحة حالة Drive (تُحدَّثان بنفس `telegram_outputs`/`drive_outputs` للمعالجات الحقيقية)، زر اللغة (`settings.toggle_language`، READY)، وزر تصدير ZIP (`export.build_zip`، يظهر مخفيًا/معطَّلًا لأن spec غير مختبر — حسب القاعدة).
- **تنقل جانبي** عبر `gr.Tabs` الأصلي (ليس أزرارًا وهمية؛ لا يوجد أي زر «يغيّر العرض فقط») مُنسَّق كسكة رأسية بـ CSS مع عناقيد، ينهار رأسيًا على الشاشات الضيقة (`@media max-width: 900px`).
- **7 صفحات بأسماء DOC:** لوحة التحكم، التحويلات (الصفحة الرئيسية)، تحليل الروابط، مركز الاتصال، السجلات، الإعدادات، كود Colab والتصدير (قيم `nav.*` للّغتين).
- **صفحة التحويلات:** صف تحكم حقيقي كامل (بدء/إيقاف مؤقت/استئناف/**إيقاف الكل** بمتغير stop/إعادة الفاشلة/**مسح المكتمل**/تحديث) + جدول حقيقي من `db.list_items` بأعمدة `rows_for` السبعة الحقيقية (المعرف، الملف، النوع، الحجم، الحالة، التقدم، المحاولات) + صف إجراءات العنصر الأربعة. السرعة/الوقت المتبقي لكل صف غير متاحين في خدمات الصف الحالية؛ `services.py` خارج نطاق التعديل — مذكور في NOT PROVEN.
- **بطاقات Dashboard (Telegram/Drive/Queue)** + JSON إحصاءات — كلها تُبذر من الحالة الحية فقط؛ زر التحديث مخفي لعدم جاهزية spec.
- **تحليل الروابط:** رابط + scope المدعوم فعلًا (`auto/message/chat` كما ينفذها `ScannerService`) + تحليل (مخفي، غير مختبر) + جدول مرشحين مبذور من `ctx.selection.visible()` + accordion مرشحات + تحديد الكل/مسح التحديد/إضافة (الثلاثة READY). `analyze.run` لا يقرّب `queue_table` (اختبار مثبت).
- **مركز الاتصال:** API ID/Hash بـ `type="password"` (مخفيان دائمًا)، الهاتف، Send/Resend، **لوحة OTP بظهور مبذور من الحالة الحية** (`visible=seed["otp_visible"]`) و**لوحة 2FA كذلك**، logout/status، ثم قسم Drive: connect/reconnect/status + accordion المجلدات (الستة محجوبة لأنها BLOCKED على بوابة Colab الحية حسب تدقيق M13-T02) + زر المساحة (READY) وسطر وJSON المساحة المبذوران من `ctx.drive_quota.last` أو فارغين.
- **السجلات:** صندوق سجلات مبذور من `LogService.tail` الحقيقي المُنقّح + بحث/تحديث/تنزيل مخفية (غير مختبرة) — لا أزرار copy/clear لأنها غير موجودة في Action Registry.
- **الإعدادات:** مزلاج تزامن 1–`HARD_CONCURRENCY_CAP` بقيمة حقيقية `ctx.config.concurrency_value()` وملاحظة «القيمة الحالية: n/4 · غير متاح» عند عدم الجاهزية + accordion متقدم (theme، صيانة) مغلق افتراضيًا.
- **تصدير Colab:** مخرجات ZIP/الخلايا في الصفحة، والزر في الشريط العلوي (إجراء واحد، مخرجات واحدة، بلا تكرار).
- **عربية RTL افتراضيًا / إنجليزية LTR** عبر `gr.State` واحد + `@gr.render(inputs=[lang_state])` واحد: أي تبديل لغة يعيد رسم القشرة كاملة باللغة الجديدة مع بقاء الحالة التشغيلية في `ApplicationContext` دون مساس.

### 3.2 عقد الربط (لا زر شكلي)

- كل الـ 41 إجراءً المُعلن حاضر في `ui.py` عبر `binder.button(gr, …)` أو `binder.is_ready(…)`، وكلها تمر بـ `binder.wire_if_ready(…, "<id الحرفي>", …)` — اختبارا السكان الثابتان في `tests/test_bindings.py` يفرضان ذلك، ومرّا.
- `binder.assert_complete()` يعمل في نهاية كل render pass (لا مفقود، لا يتيم).
- لا `lambda`، لا `.click/.change/.submit` مباشر، لا `binder.wire(`, لا تطبيق ثانٍ، لا `share=True`.

### 3.3 `python-package/teledrive/handlers.py` (بحاجة مثبتة)

- استخراج `_quota_view(quota)` المشترك (نفس ناتج المعالج حرفيًا) واستخدامه في `h_drive_refresh_quota`.
- إضافة `shell_seed(ctx)`: قاموس بذر واحد يشتق كل القيم الابتدائية من الحالة الحية عبر نفس عارضات المعالجات (`_telegram_view`, `_drive_view`, `_queue_view`) + `rows_for(selection.visible())` + `stats.dashboard()` + `log_service.tail(300)` + quota/concurrency.
- تلميع `_queue_view`: لا فارزة زائدة عند عدم وجود عدّادات.
- **الحاجة المثبتة:** دون البذر، إعادة الرسم عند تبديل اللغة كانت ستُخفي لوحة OTP أثناء `CODE_REQUESTED` وتُعيد الشرائح إلى قيم ابتدائية كاذبة — أي «فقدان الحالة» الذي يمنعه DOC صراحة.

### 3.4 ملفات اللغة

مفاتيح جديدة بالتوازي في `ar.json` و`en.json`: `transfer.controls`, `transfer.item`, `settings.advanced`, `dash.stats`, `form.current_value`؛ وتحديث تسميات `nav.queue/link/settings/export/dashboard` لتطابق أسماء صفحات DOC. تكافؤ المجموعات (`test_keysets_match`) أخضر.

## 4. الاختبارات الجديدة (35+2 = 22 اختبارًا؛ 338 → 360)

### 4.1 `python-package/tests/test_ui_shell_contract.py` (18 اختبارًا)

بناء الصفحات بلا استثناء (ar/en/لغة غير مدعومة) · اكتمال الربط على مكوّنات Gradio حقيقية (`missing()==[]`, `orphans()==[]`, مجموعة الأفعال المربوطة = READY حرفيًا) · تطابق arity لكل فعل · `analyze.run` لا يلمس جدول الطابور ولا يُدخل تلقائيًا · أزرار الطابور تحل على `QueueManager` الحقيقي · إجراءات Telegram = الواجهة العامة السبعة فقط · OTP مخفي ابتداءً/مرئي فقط في `CODE_REQUESTED` · 2FA مرئية فقط في `PASSWORD_REQUIRED` · الإغلاق بعد المصادقة · **تبديل اللغة يحفظ حالة الدخول واللوحات والتحديد** · لا بيانات وهمية (جداول فارغة عند فراغ الحالة، شرائح Disconnected، لوحة السجلات تتغذى من `LogService.tail` عبر سنتينل) · الثيم/CSS مثبتان فعلًا على الـ Blocks + جذر render موجود.

### 4.2 `python-package/tests/test_drive_connection_gate.py` (4 اختبارات)

`Connected` مستحيل قبل تنفيذ `about().get()`: غير متصل صراحة ابتداءً · متصل فقط بعد تنفيذ البوابة فعلًا مع user/quota · فشل `about().get()` → `TeleDriveError` + `ERROR` + بلا service محتفظ به · `reconnect` يمسح الحالة ويعيد البوابة. **لم تُقلب أي أعلام registry** — الستة يبقون BLOCKED حتى Colab الحي.

## 5. بوابات التحقق ومخرجاتها الحقيقية

| البوابة | النتيجة | المخرجات الحرفية |
|---|---|---|
| `python -m compileall teledrive` (في `python-package`) | PASS | نجاح بلا أخطاء |
| `python -m pytest -q tests` | PASS | **360 passed, 1 warning in 12.10s** (التحذير = إشعار deprecation الموثق في §4.2 من DOC) |
| `python teledrive_launcher.py --check` | PASS | `binding check ok: 24/41 ready actions resolve` |
| `python -m teledrive.notebook_cells --check` | PASS | `notebooks are in sync` |
| `cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb` | PASS | متطابقان، exit 0 |
| `python -m teledrive.package_service --build --output teledrive_v4.5.zip` | PASS | `tests passed` · `archive: teledrive_v4.5.zip` |
| Gradio UI smoke check (بلا اعتماديات) | PASS | بناء+render pass حقيقيان: `BUILD OK: Blocks`، render ar→`td-rtl` OTP مخفي، بعد فرض `CODE_REQUESTED` render en→`td-ltr` OTP ظاهر؛ إقلاع `share=False` محليًا `HTTP /config 200` |
| `bun install --frozen-lockfile` / `bun run lint` / `bun run build` | **NOT RUN في الحاوية** | فشل تنزيل رزمتي `@lovable.dev/*` فقط: `UNKNOWN_CERTIFICATE_VERIFICATION_ERROR ... europe-west1-npm.pkg.dev` (حاجز شبكة الحاوية؛ الرزم ليست مطلوبة من تغييراتي — صفر ملفات frontend معدَّلة) — بوابة CI على الـPR هي الحكم |

## 6. الملفات

- معدَّلة: `python-package/teledrive/ui.py` (إعادة بناء)، `python-package/teledrive/handlers.py` (Quota مشترك + shell_seed + تلميع)، `python-package/teledrive/progress_tracker.py` (RLock — عيب مثبت)، `python-package/teledrive/locale/{ar,en}.json` (مفاتيح/تسميات).
- جديدة: `python-package/tests/test_ui_shell_contract.py`, `python-package/tests/test_drive_connection_gate.py`, `docs/PHASE_REPORTS/PHASE_19.md`.
- ذاكرة: `docs/{TODO,KNOWN_ISSUES,ACTIVE_TASK,CHANGELOG,AI_HANDOFF}.md`.
- **لم تُمس:** `action_registry.py`, `telegram_auth.py`, `telegram_client.py`, `notebook_cells.py`, النوتبوكان، `.github/**`, `services.py`, `app.py`, `ui_binder.py`, `requirements*.txt`, `requirements.lock`, `bun.lock`, وكل الواجهة الأمامية.

## 7. الحالة الصادقة

**Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.**

لا `Colab-ready` ولا `Complete`: لم يُختبر Telegram/Drive/نقل حقيقي خارج الاختبارات المعزولة. مالك التشغيل الحي هو المالك (M15-T01).

## 8. الخطوة التالية الأصغر

- مراجعة الـ PR من المالك/Brain ثم دمجه؛ تشغيل CI على الـ PR لإثبات بوابتي lint/build في بيئة قادرة على الوصول إلى `pkg.dev`.
- تشغيل المالك في Colab الحقيقي للواجهة الجديدة (تسجيل Telegram برقم وOTP و2FA اختياري، Drive native، نقل ملف واحد) — M15-T01 التشغيلي.
