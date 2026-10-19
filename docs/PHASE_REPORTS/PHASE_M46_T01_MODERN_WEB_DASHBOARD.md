# PHASE M46-T01 — Modern Web Dashboard (FastAPI + AJAX Polling) إلى جانب Gradio الاحتياطي

**Date (UTC):** 2026-10-19  
**Task:** `M46-T01`  
**Base:** `337c19e7d69a903c1b7c5060e572d17f09ff8f86` (`main` بعد PR #104)  
**Branch:** `arena/137aa454-drive-buddy-3579bf74`

## 1. المصدر من Google Drive — ماذا وجدنا فعلًا

الرابط الذي أرسله المالك (`.../folders/1sfa3vUr_lD2Avj31q7-n-Gp4zo3sRUUa`) ليس مجلدًا؛
المعرّف نفسه على Drive هو دفتر Colab باسم `TeleDrive_GitHub_Sync_Bridge.ipynb`
(23,168 بايت). وبالبحث في Drive وجدنا المصدر الأحدث للواجهة:

| Drive ID | الاسم | الحجم | آخر تعديل |
|---|---|---|---|
| `1T1EU2dhlv0IPgqT_Up0o_t5EGcqez0I_` | `TeleDrive_WebUI_GitHub_Bridge.ipynb` | 135,253 | 2026-10-19T19:49Z |
| `1sfa3vUr_lD2Avj31q7-n-Gp4zo3sRUUa` | `TeleDrive_GitHub_Sync_Bridge.ipynb` | 23,168 | 2026-10-19T17:11Z |
| `1cRsm4GF9jcWkuWfocHTgHiKlK1y_veL8` | `teledrive_v4.5.zip` داخل مجلد `TeleDrive (18JOrpi…)` | 600,312 | 2026-10-19T18:03Z |

لا يوجد ملف مستقل باسم `web_dashboard.py` على Drive؛ الكود مضمّن كنص
(`WEB_DASHBOARD_CODE` في خلية 1 — إصدار AJAX Polling، و`WEB_UI_CODE` في خلية 4 —
إصدار WebSocket أقدم) داخل دفتر الكوبري، ومعه صيغة مقترحة للخلية الرابعة
(`CELL_4_SOURCE`). وقد اُعتمد إصدار الخلية 1 (AJAX Polling) لأنه طلب المالك صراحة،
وهو الأنسب لبروكسي Colab.

> **⚠️ أمن:** دفتر الكوبري يحتوي GitHub Token كنص صريح (`ghp_…`) داخل أكثر من خلية.
> لم يُنسخ أي جزء منه إلى المستودع (مُسحت النسخ المحلية، وفحص `ghp_` على الشجرة
> نظيف). **يجب على المالك إلغاء هذا التوكن فورًا (Revoke) من GitHub.**

## 2. لماذا لم تُنسخ الحمولة حرفيًا — تعارضات موثّقة مع الشجرة الحية

1. **حلقة أحداث ثانية:** `launch_web_dashboard` في الحمولة يستدعي
   `asyncio.run(server.serve())` — محظور دستوريًا (§3) ويكسر
   `test_no_ad_hoc_loops.py`؛ الحلقة الواحدة الشرعية هي `ctx.aio`.
2. **محرك نقل مكرر:** `start_transfer` في الحمولة يحمّل الملفات بنفسه ويكتبها
   مباشرة على مجلد Drive المُركَّب متجاوزًا `QueueManager`/`TransferManager`
   (منع التكرار، الرفع القابل للاستئناف، checkpoints) ومحرك **FastTelethon**
   الموجود أصلًا في `telegram_client.py` (M45-T04: حتى 12 منفذا
   `MTProtoSender`)، بل ويستورد `teledrive.fast_telethon` غير الموجود أصلًا.
3. **حالة خمّينة:** المقاييس تُبنى من مسح ملفات `*checkpoint*.json`/`*.part`
   على القرص بدل `ctx.progress.snapshot()` و`QueueManager.snapshot()`.
4. **خلية 4 مكسورة:** الصيغة المقترحة `await launch(ctx)` تخاطب دالة متزامنة،
   وتحذف ترتيب تبنّي Drive ← استعادة الخزنة ← بيانات الاعتماد الذي تثبته
   الاختبارات؛ وكان الكوبري يعدّل ملفي `.ipynb` مباشرة بدل المصدر الواحد
   `teledrive/notebook_cells.py` المولِّد لهما (يكسر `test_notebook.py`).
5. **مخاطر تصفح:** CORS `*`، وحقن سجلات/أسماء ملفات عبر `innerHTML`،
   ولا توجد `fastapi`/`uvicorn` في `requirements.lock`.

## 3. ما نُفّذ (نفس واجهة الاستعمال المقصودة، ربط شرعي)

* **`python-package/teledrive/web_dashboard.py` (جديد)** — يحتفظ بأسماء الحمولة
  العامة (`TeleDriveWebBridge`, `create_web_app(ctx)`,
  `launch_web_dashboard(ctx, port=8765, open_iframe=False)`, `HTML_PAGE`) وبنفس
  التصميم العربي RTL المكتفي ذاتيًا (صفر CDN):
  - `GET /` الصفحة، `GET /api/metrics` (يُستطلع كل ~1s بـ `fetch` نسبي
    `api/metrics` + `no-store`)، `GET /api/health`، `GET /api/state`،
    `GET /api/logs`، `POST /api/action` (يمرّر إلى
    `ctx.handlers.bridge_request` — نفسه جسر React الموثّق/المنقّح، ويرفض
    إجراءات الأسرار)، `POST /api/queue/{start|pause|resume|stop|retry_failed|refresh}`
    + الأسماء التوافقية `/api/start|pause|stop`، و`WS /ws` اختياريًا بنفس الحمولة.
  - المقاييس حقيقية فقط: `progress.snapshot()` + `queue_manager.snapshot()` +
    لقطة `LiveUiStateService` الآمنة للمتصفح + سجلات `LogService` المنقّحة.
  - التشغيل يُجدوَل على `ctx.aio.schedule(server.serve())` (حلقة واحدة)،
    النهايات المتزامنة `def` تعمل في ThreadPool كما تفترض Handlers أصلًا،
    والإطلاق المزدوج يعيد نفس الخادم؛ المقبض على `ctx.web_dashboard`
    ويُغلق في `ApplicationContext.shutdown()`؛ الرابط يُطبع عبر
    `colab_proxy_url(8765)` الرسمي كما في Gradio (`share=False`، بلا نفق عام).
  - بلا CORS عام؛ كل نص خادم يُرسم بـ `textContent`.
* **`requirements.txt` / `requirements.lock`** — أُضيف `fastapi==0.149.0` و
  `uvicorn==0.54.0` (مثبّتة ومتحقق منها بـ `pip check` مع `gradio==6.20.0`).
* **الخلية الرابعة** — عُدّلت في `teledrive/notebook_cells.py` فقط ثم أُعيد توليد
  `python-package/notebook/TeleDrive.ipynb` + `public/TeleDrive.ipynb` +
  `teledrive/colab_cells.json` (متطابقة بايتًا). أُضيفت قائمة
  `UI_MODE = "Modern_Web_Dashboard"` بـ `@param`
  [`Modern_Web_Dashboard`, `Classic_Gradio_Backup`, `Run_Both_Together`] +
  `WEB_DASHBOARD_PORT=8765`، مع بقاء كل عقود الخلية السابقة (ترتيب
  adopt←restore←credentials، `share=False`، `blocking=False`) وسقوط تلقائي
  إلى Gradio إن تعذّرت الواجهة الحديثة.
* **`app_context.py`** — حقل `web_dashboard` وإيقافه في `shutdown()`.
* **اختبارات:** `tests/test_web_dashboard.py` (9 اختبارات: استيراد كسول، بلا
  حلقة ثانية/CORS/محرك وهمي، صفحة مكتفية تستطلع نسبيًا، مقاييس فارغة حقيقية،
  نهايات HTTP، رفض الأسرار، قائمة انتظار مبيّضة، وإطلاق حقيقي على الحلقة
  الواحدة) + اختبار خلية 4 مزدوجة الواجهة في `tests/test_notebook.py`.

## 4. البوابات (نفس أوامر CI)

- `python -m compileall -q teledrive` — PASS
- `python -m pytest -q tests` — **823 passed** (تحذير TestClient/httpx تجميلي واحد)
- `python teledrive_launcher.py --check` — `54/54`
- `python -m teledrive.notebook_cells --check` + `cmp` النسختين — PASS
- معاينة حية محلية: `GET /api/health` و`/api/metrics` و`POST /api/queue/pause`
  تعمل بحالة صادقة (`DISCONNECTED`، طابور فارغ — بلا أي بيانات وهمية).
- حزمة: `python -m teledrive.package_service --build` (اختبارات أولًا دائمًا) —
  `teledrive_v4.5.zip` بحجم `614404` بايت، SHA-256
  `de902fa6cf50dde106ed5126627e1dd2e425c9cc658cdf1d53c0781e5c9bfaf5`،
  `171` مدخلًا تشمل `teledrive/web_dashboard.py` والنوتبوك المحدّث والاختبارات.

## 5. حدود صادقة

- حقول تسجيل دخول Telegram (الهاتف/الكود/2FA) واختيار مجلد Drive تبقى في
  Gradio الآمنة بقرار الجسر نفسه (`bridge.secure_gradio_only`)؛ الواجهة
  الحديثة تعرض التحليل/الاختيار/الطابور/التحكم/السجلات. عند استعادة الجلسة
  من خزنة Drive في الخلية 4 تظهر الحالة متصلة مباشرة، وإلا فالوضع
  `Run_Both_Together` هو المسار الموصى به لأول دخول.
- لم تُختبر الواجهة على Colab حي بجلسة Telegram/Drive حقيقية في هذه الجلسة؛
  الإثبات هنا اختبارات وحدات + HTTP حقيقي محلي على نفس كود التشغيل.
