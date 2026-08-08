# PHASE_18 — إصلاح تدفق تسجيل Telegram داخل Colab: API، الهاتف، OTP، و2FA شرطي (M15-T03)

**TASK ID:** `M15-T03`
**العنوان:** إصلاح تدفق تسجيل Telegram داخل Colab: API، الهاتف، OTP، و2FA شرطي
**الحالة:** `VERIFIED COMPLETE` — بوابات محلية خضراء واختبارات contract كاملة
**التاريخ (UTC):** 2026-08-08
**المستودع:** `https://github.com/body199-cmyk/drive-buddy-3579bf74.git`

## 1. Baseline والاستئناف

| الحقل | القيمة |
|---|---|
| Base SHA المعتمد | `8fbd18595c3b6d32d20f1c3319d0b551dee4dfa6` |
| Actual start SHA | `8fbd18595c3b6d32d20f1c3319d0b551dee4dfa6` (مطابق) |
| الفرع المفحوص | `arena/019fe1f1-drive-buddy-3579bf74` (الفرع الجانبي الثابت للجلسة) |
| الشجرة قبل العمل | نظيفة عند HEAD بعد دمج PR #10 (M15-T02) |
| آخر CI أخضر | Run `31261793720` (`push` على main عند `8fbd185`) — `status: completed`, `conclusion: success` |
| PRs المفتوحة عند البدء | صفر (`pulls?state=open` = `[]`) |
| قرار baseline | `RESUME_VERIFIED`: HEAD مطابق للقاعدة المعتمدة |

## 2. المشكلة والسبب الجذري

في `teledrive/ui.py` كانت حقول OTP و 2FA تُعرض دائمًا وبشكل غير مشروط منذ البداية:
- كان حقل `code` وزر `verify_btn` مرئيين قبل طلب الكود (`CODE_REQUESTED`).
- وكان حقل `password` وزر `verify_password_btn` مرئيين لجميع المستخدمين حتى لو لم يكن لديهم 2FA ولم يطلب Telegram كلمة سر ثنائية.
- وكانت معالجات Telegram السبعة في `handlers.py` تُرجع قيمتين فقط (`telegram_detail`, `telegram_chip`) مع `ERROR_ARITY = 2`، دون القدرة على تحديث ظهور لوحتي OTP و 2FA ديناميكيًا تبعًا لحالة آلة الحالة.

## 3. التنفيذ المنجز

### 3.1 `python-package/teledrive/ui_binder.py`
- إضافة دالة `component_update(**props: Any) -> dict[str, Any]` على مستوى الوحدة كجسر وحيد مع Gradio:
  - تُرجع `gr.update(**props)` عند وجود Gradio (بيئة Colab).
  - تُرجع `dict(props)` كـ mapping عادي عند غياب Gradio (بيئة الاختبارات و CI) بحيث يكون `payload["visible"]` قابلاً للتحقق دائمًا دون الحاجة لتثبيت Gradio في الاختبارات المعزولة.

### 3.2 `python-package/teledrive/handlers.py`
- استيراد `CODE_REQUESTED`, `PASSWORD_REQUIRED` من `.telegram_auth` و `component_update` من `.ui_binder`.
- تحديث `ERROR_ARITY` للإجراءات السبعة الخاصة بـ Telegram من `2` إلى `4`.
- تعديل `_error` بحيث يُعيد اشتقاق ظهور اللوحات ديناميكيًا من حالة آلة الحالة الحية (`state = getattr(getattr(self.ctx, "telegram_auth", None), "state", "")`) ويُرجع `(message, None, *self._telegram_panels(state))`.
- إضافة `_telegram_panels(state)` لإرجاع تحديث ظهور لوحة OTP فقط عند `state == CODE_REQUESTED` ولوحة 2FA فقط عند `state == PASSWORD_REQUIRED`.
- تحديث `_telegram_view(status)` لإرجاع الرباعية `(detail, label, code_panel, password_panel)`.

### 3.3 `python-package/teledrive/ui.py`
- تغليف حقل OTP وزر التحقق داخل `with gr.Column(visible=False) as code_panel:`.
- تغليف حقل 2FA وزر التحقق داخل `with gr.Column(visible=False) as password_panel:`.
- تحديث مخرجات ربط Telegram: `telegram_outputs = [telegram_detail, telegram_chip, code_panel, password_panel]`.
- بقاء حقل الهاتف كـ `gr.Textbox` عادي وقابل للمراجعة البصرية (مع إخفاء وحجب الأرقام والبيانات الحساسة في السجلات والـ events والـ account label).

### 3.4 اختبارات جديدة
1. `python-package/tests/test_telegram_flow_contract.py`:
   - 15 اختبارًا تثبت:
     - `set_credentials` يُنشئ عميلاً واحداً فقط.
     - رفض API ID غير الرقمي و API Hash الفارغ ورقم الهاتف غير الدولي.
     - بقاء `phone_code_hash` وكلمة مرور 2FA في الذاكرة الحية فقط وعدم تسجيلهما في الـ events log.
     - إخفاء لوحة OTP قبل طلب الكود وإظهارها فقط عند `CODE_REQUESTED`.
     - إغلاق لوحة OTP بعد النجاح والمصادقة وعدم عرض `Connected` قبل `AUTHORIZED`.
     - بقاء لوحة OTP مفتوحة وإبقاء لوحة 2FA مغلقة عند إدخال كود خاطئ (`PhoneCodeInvalidError`).
     - ظهور لوحة 2FA فقط عند ورود استجابة حقيقية بـ `SessionPasswordNeededError`.
     - عدم ظهور لوحة 2FA أبدًا للحسابات التي لا تملك 2FA.
     - إغلاق لوحة 2FA عند قبول كلمة المرور واستخدام نفس العميل دون طلب كود جديد.
     - بقاء لوحة 2FA مفتوحة عند رفض كلمة المرور.
     - إغلاق اللوحتين وتصفير الحالات السرية عند تسجيل الخروج (`logout`).
2. `python-package/tests/test_no_hardcoded_credentials.py`:
   - فحص ثابت يمنع وجود أي قيم اعتمادية Telegram أو Google Drive صريحة في `teledrive/`, `notebook/`, `public/`.
   - لا يطبع القيم المطابقة بل المسار ورقم السطر فقط.

## 4. البوابات والمخرجات الحقيقية

| البوابة | النتيجة | المخرجات الفعلية |
|---|---|---|
| `python -m compileall teledrive` | PASS | Listing/Compiling بلا أخطاء (exit 0) |
| `python -m pytest -q tests` | PASS | **`338 passed in 8.58s`** (322 + 16 جديدًا)، exit 0 |
| `python teledrive_launcher.py --check` | PASS | `binding check ok: 24/41 ready actions resolve` |
| `python -m teledrive.notebook_cells --check` | PASS | `notebooks are in sync` |
| `cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb` | PASS | متطابقان تمامًا (exit 0) |
| `python -m teledrive.package_service --build --output teledrive_v4.5.zip` | PASS | `archive: teledrive_v4.5.zip` |
| `bun run lint` (الجذر) | PASS | exit 0 — `0 errors, 6 warnings` |
| `bun run build` (الجذر) | PASS | Vite client + SSR + Nitro (Cloudflare module) build نجح بالكامل (exit 0) |
| Secrets Scan | PASS | `0 offenders` — فحص `test_no_hardcoded_credentials` و grep نظيفان تمامًا |

## 5. ما لم يُثبَت (حدود صادقة)

- **Colab حقيقي لم يُختبر**: اختبارات flow contract أُثبتت في بيئة الاختبارات المعزولة، وليس مع خوادم Telegram أو Google Drive الحية.
- الحالة الصادقة: **`Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.`**

## 6. التسليم (Git/PR)

- Base SHA: `8fbd18595c3b6d32d20f1c3319d0b551dee4dfa6`
- Branch: `arena/019fe1f1-drive-buddy-3579bf74`
- Commit Message: `M15-T03: conditional OTP and 2FA login panels in Colab UI with flow contract tests`
