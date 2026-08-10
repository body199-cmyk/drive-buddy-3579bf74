# PHASE_M18_T02 — §10: إصلاح «خطأ غير معروف» عند ربط Telegram بعد M18-T01

> **TASK ID:** M18-T02 (§10 fix) — **الحالة:** COMPLETE — كود + بوابات خضراء + إعادة نشر الحزمة موثّقة
> **المرجع:** رسالة المالك (cid `d75de588` في الواجهة) + أمر التنفيذ §10
> **Base SHA:** `faff35a3af12adb1adf891049917f7add8dc7751` (origin/main = PR #30, M18-T01)
> **تاريخ التنفيذ:** 2026-08-10 UTC

## 1. الأعراض (مطابقة لرسالة المالك)

في واجهة Colab، عند الضغط على زر «ربط» (Telegram Connect) بعد دمج M18-T01:

```
خطأ غير معروف. جرّب مرة أخرى. [d75de588]
```

هذه رسالة `err.unknown` المولّدة من `@action` wrapper في `handlers.py` — أي أن الـhandler
أسقط استثناءً **غير مصنّف** (ليس `TeleDriveError`) وسُجّل traceback الكامل في السجلات
(redacted) مع نفس الـcid.

## 2. التتبع المنقّح (refined traceback) — أُعيد إنتاجه محليًا بنفس المسار

لا يمكن الوصول إلى سجلات جلسة المالك من الساندبوكس، فأُعيد إنتاج **نفس المسار** بلا أسرار
حقيقية: bootstrap كامل + `TelegramAuth` بـ**العميل الحقيقي (Telethon)** مع بيانات وهمية
(بدون شبكة إلى DC). النتيجة المطابقة تمامًا لشكل خطأ المالك:

```
RETURNED MESSAGE: خطأ غير معروف. جرّب مرة أخرى. [dcd56874]   ← نفس الصيغة [cid]
arity: 4

[WARNING] teledrive.handlers: action=telegram.set_credentials cid=dcd56874 crashed
Traceback (most recent call last):
  ...
  File ".../teledrive/async_runtime.py", line 111, in run
    return self.submit(coro).result(timeout)
  ...
  File ".../teledrive/telegram_client.py", line 40, in connect
    await self.client.connect()
  ...
asyncio.exceptions.IncompleteReadError: 0 bytes read on a total of 8 expected bytes
```

**السبب الجذري:** `TelegramAuth.set_credentials()` (ملف محمي، **لم يتغيّر في M18-T01 إطلاقًا**)
ينشئ عميل Telethon ثم يستدعي `client.connect()` / `is_authorized()` **بدون أي معالج استثناءات**،
بخلاف `send_code`/`verify_code`/`verify_password` التي تصنّف أخطاءها. أي فشل في طبقة النقل/الاتصال
بخوادم Telegram — `asyncio.IncompleteReadError`، `TimeoutError`، `ConnectionError`، `OSError`,
أو RPC أثناء المصافحة — يفلت من الخدمة ويحوّله الـwrapper العام إلى `err.unknown` الجامد.

### المقارنة قبل/بعد M18-T01 (المسار المعني فقط)
| الملف | التغيير في M18-T01 | هل يمسّ مسار telegram؟ |
|---|---|---|
| `telegram_auth.py` | **لا تغيير** (git diff فارغ) | لا |
| `handlers.py` | `chip_html` + `_selection_view` + `_folder_broadcast` + 3 أفعال analyze + `ERROR_ARITY` (folder/analyze) | فقط `_telegram_view` صار يُرجع `chip_html(label)` بدل النص الخام — متّسق مع تغيير `ui.py` |
| `ui.py` | الشريط العلوي: chips صارت `gr.HTML`؛ لوحة مجلد رابعة؛ مرحلة اختيار analyze | `telegram_chip` Textbox→HTML (متّسق 4 مخارج، لا تغيير في `_section_connection` ولا wiring) |
| `ui_binder.py` | **لا تغيير** | لا |
| `action_registry.py` | +3 أفعال `analyze.*` فقط | أسماء/arity أفعال `telegram.*` **دون تغيير** |

**الخلاصة: لا يوجد mismatch من M18-T01 في مسار telegram.** أسماء الأفعال
(`telegram.set_credentials/send_code/verify_code/verify_password/logout/status`) وأعداد
المدخلات/المخرجات (4/4) وأسماء المكونات متطابقة قبل/بعد (التحقق عبر `git diff 2735523 faff35a`).
المالك لم يصادف الخطأ من قبل لأنه لم يصل إلى زر الربط في جلسات Colab السابقة (لا إثبات Colab حي
لتسجيل الدخول في أي مرحلة سابقة — KNOWN_ISSUES #38)، ووصوله الآن سببه أن إعادة نشر التاج
`pkg-2026.08.09-m15t07` (22:47Z بعد دمج M18-T01) سلّمت الحزمة الحالية إلى بوابة تحديث Cell 1.

## 3. الإصلاح (أصغر patch في المسار غير المحمي)

لا تلمس أي ملف محمي (`telegram_auth.py` وغيرها). التصنيف الصحيح العميق ينتمي داخل
`TelegramAuth.set_credentials` — ملف محمي — ويتطلب تفويضًا صريحًا (§10: توقف وأبلغ)؛
الـpatch أدناه يسدّ الفجوة من جهة الواجهة:

- **`teledrive/handlers.py`** — `h_telegram_set_credentials`: `TeleDriveError` يمرّ كما هو
  (أخطاء `err.bad_api_id`/`err.bad_api_hash` محفوظة)، وأي استثناء غير مصنّف (نقل/DC) يُحوَّل إلى
  `err.tg_connect_failed` المترجم القابل لإعادة المحاولة، مع `_log.exception` كي يبقى التتبع
  الكامل (redacted) في السجلات للتشخيص.
- **`teledrive/locale/ar.json` + `en.json`** — مفتاحان:
  - ar: «تعذر الاتصال بخوادم تيليجرام. تحقق من اتصال الإنترنت وحاول مرة أخرى.»
  - en: «Could not reach Telegram servers. Check your internet connection and try again.»
- **`tests/test_telegram_flow_contract.py`** — اختباران:
  - `test_transport_failure_at_connect_is_classified_not_unknown` (فشل نقل → `err.tg_connect_failed` لا `err.unknown`، اللوحات تبقى مغلقة)
  - `test_bad_api_id_is_not_swallowed_by_the_transport_classifier` (TeleDriveError يمرّ دون مساس)

نتيجة التشغيل الحقيقي بعد الإصلاح (نفس سيناريو الإعادة):
```
RETURNED MESSAGE: تعذر الاتصال بخوادم تيليجرام. تحقق من اتصال الإنترنت وحاول مرة أخرى. [e08c1ddc]
arity: 4
[WARNING] teledrive.handlers: action=telegram.set_credentials cid=e08c1ddc failed:
    TeleDriveError: telegram connect failed: IncompleteReadError
```
التتبع الكامل ما زال في السجلات (tab السجلات في الواجهة أو `teledrive.log`)، redacted تلقائيًا.

## 4. التحقق الخام (raw gates)

```bash
cd python-package
python -m compileall -q teledrive                        # exit 0
python -m pytest -q tests                                # 582 passed (كان 580؛ +2 جديد)
python teledrive_launcher.py --check                     # binding check ok: 45/45 ready actions resolve
python -m teledrive.notebook_cells --check               # notebooks are in sync
cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb    # متطابقان (exit 0)
```

- Live app (gradio 6.22) بفيكتور اتصال وهمي: build OK · `binder complete: 45 action kinds wired (55 controls), 0 visible-disabled` · كل أفعال telegram الـ7 موصولة بآلية `binder.wire` ذاتها.
- مسار بلا أسرار حقيقية (fake connector الحالي): `h_telegram_set_credentials` يصل للخدمة، arity 4 صحيح، والنتيجة لا تتحول إلى unknown error — 30 اختبارًا في ملفي التدفق contract خضراء.
- «زر الربط يستقبل api_id/api_hash/phone من نفس المكونات التي ترسلها الواجهة»: wiring في `_bind_actions` — `credentials_btn ← [api_id, api_hash]`، `send_code_btn ← [phone]`، `verify_btn ← [code]`، `verify_pw_btn ← [password]` — غير متغيّرة؛ `gr.render` لا يُعيد إنشاء الحقول ولا يمسح قيمها قبل submit (لا يوجد `State.change` غير `lang_state`، وإعادة الرسم لا تحدث إلا عند تبديل اللغة).

## 5. الملفات

### Changed
- `python-package/teledrive/handlers.py` (تصنيف فشل النقل في `h_telegram_set_credentials`)
- `python-package/teledrive/locale/ar.json` + `en.json` (`err.tg_connect_failed`)
- `python-package/tests/test_telegram_flow_contract.py` (+2 اختبار)

### Created
- `python-package/docs/PHASE_REPORTS/PHASE_M18_T02.md` (هذا التقرير)
- تحديثات الذاكرة: `docs/CHANGELOG.md` · `docs/KNOWN_ISSUES.md` (#40) · `docs/AI_HANDOFF.md` · `docs/ACTIVE_TASK.md` · `docs/TODO.md`

### Protected (لم تُلمس — تحقَّق بـ git diff)
`telegram_auth.py` · `telegram_client.py` · `drive_auth.py` · `database.py` · `migrations.py` ·
`queue_manager.py` · `transfer_manager.py` · `notebook_cells.py` · `colab_cells.json` ·
`notebook/TeleDrive.ipynb` · `public/TeleDrive.ipynb` · `requirements.*` · `bun.lock` ·
`package.json` · `.github/workflows/*` · كل ملفات React/frontend.

## 6. إعادة نشر الحزمة للمالك (لتشغيل Colab على التحديث)

التاج المثبَّت في Cell 1 هو `pkg-2026.08.09-m15t07`؛ لإيصال هذا الإصلاح عبر بوابة التحديث:
1. دمج PR (أو بعد الدمج) → تشغيل workflow `.github/workflows/release-current.yml`
   (`workflow_dispatch` على main) — أو إعادة نشر التاج يدويًا من واجهة GitHub
   (KNOWN_ISSUES #27: توكن Arena بلا `actions:write`).
2. في Colab: Runtime → Restart runtime → إعادة تشغيل Cell 1 فحسب (البوابة تسلّم الحزمة
   الجديدة بشيك digest) ثم Cells 2–4.

**التوقع بعد الإصلاح:** إن تعذّر الوصول لخوادم Telegram (شبكة/DC/مصادفة عابرة)، يعرض الزر
رسالة واضحة «تعذر الاتصال بخوادم تيليجرام… [cid]» بدل «خطأ غير معروف»، ونوع الاستثناء
الحقيقي متاح في tab السجلات. إن كانت البيانات سليمة والشبكة سليمة، يكتمل الربط كالمعتاد
(READY_FOR_PHONE ← إرسال الرمز ← التحقق).

## 7. ما لم يُثبت (بصدق)

- سجلات جلسة المالك نفسها (`cid d75de588`): أعِدت هندسة التتبع بنفس المسار محليًا —
  النوع الحقيقي في سجل المالك قد يكون `TimeoutError`/`ConnectionError`/`OSError`/RPC بدل
  `IncompleteReadError` حسب ظرف الشبكة، وكلها تُلتقط الآن وتُصنَّف بالمفتاح نفسه مع بقاء
  التتبع في السجلات.
- لقطة Colab بمتصفح حقيقي بيد المالك (لا متصفح في الساندبوكس) — الخطوات في §6.

## 8. قالب التقرير (§10)

```
TASK ID: M18-T02 (§10 fix)
Status: COMPLETE — patch في المسار غير المحمي + 582 passed + launcher 45/45
Root cause: TelegramAuth.set_credentials (ملف محمي، ثابت قبل/بعد M18-T01) لا يعالج
        أخطاء طبقة النقل عند connect()/is_authorized() → err.unknown + cid؛
        لا mismatch من M18-T01 (تحقَّق git diff لـ5 ملفات)
Refined traceback: action=telegram.set_credentials cid=... crashed →
        asyncio.exceptions.IncompleteReadError (نقل) في telegram_client.py:40 connect()
PR URL / SHA: PR واحد من arena/019fede6-drive-buddy-3579bf74 على base faff35a
Files: handlers.py · locale/ar.json · locale/en.json · test_telegram_flow_contract.py
        (+ PHASE_M18_T02.md + CHANGELOG/KNOWN_ISSUES/AI_HANDOFF/ACTIVE_TASK/TODO)
Gates: compileall 0 · pytest 582 passed · launcher 45/45 · notebook in sync · cmp ok
Live Colab: بيد المالك — Restart runtime → Cell 1 (التحديث عبر التاج بعد إعادة النشر) → Cells 2–4
Next: تصنيف الخطأ العميق داخل TelegramAuth.set_credentials يتطلب تفويضًا صريحًا للملف المحمي
```
