# PHASE_M27_T01 — تقوية نقل TeleDrive

## بطاقة الجلسة

| الحقل | القيمة |
|---|---|
| التاريخ | 2026-08-19 |
| المهمة | `M27-T01` |
| المستودع | `body199-cmyk/drive-buddy-3579bf74` |
| فرع التنفيذ | `arena/m27-t01-final-hardening` |
| الخط الأساسي | `origin/main` عند `85822af73326d60894bde9737a35672a4aae1e08` |
| نطاق التعديل | throttling لتقدم SQLite، كشف عطل محرك النقل، دعم القنوات الخاصة، واستئناف تنزيل `.part` من offset |
| حالة التقرير | تغييرات محلية متحققة؛ لم يُنشأ commit أو PR أو merge بعد وقت كتابة التقرير |

## مواءمة المطلوب مع الشجرة الفعلية

| الفجوة المؤكدة | المعالجة الجراحية |
|---|---|
| callback التقدم يكتب SQLite بوتيرة chunks | throttle زمني `0.5s` لكل عنصر مع forced flush عند حدود المراحل والنهاية. |
| `gather(return_exceptions=True)` يفرغ الاستثناءات من دون إبلاغ callback الطابور | إعادة الاستثناء غير الملغى بعد جمع العاملين، فيسجله `QueueManager._on_run_done()` كـ`transfer run crashed`. |
| حفظ channel id الخام لا يمثل peer Telethon الصحيح دائمًا | دالة `peer_id()` تميز القناة (`-100<id>`) والمجموعة (`-<id>`)، بعد حل الكيان. |
| حل محادثة خاصة قد يفشل بسبب cache بارد | `resolve_entity()` يحاول الحل ثم يسخن dialogs مرة واحدة بحد `200` ويعيد المحاولة، وإلا يرفع خطأ دائمًا مترجمًا. |
| بقاء `.part` لا يحقق resume bytes فعليًا | `download_partial()` يقص فقط إلى محاذاة `4096` ثم يكتب ناتج `iter_download(offset=...)` على الملف ذاته. |

## الملفات المعدلة

| الملف | التغيير |
|---|---|
| `python-package/teledrive/errors.py` | `PrivateChannelUnresolvedError` دائم ومترجم. |
| `python-package/teledrive/telegram_links.py` | `peer_id()` كدالة نقية لهوية peer. |
| `python-package/teledrive/telegram_client.py` | حل entity مع warm-up آمن وdownload جزئي مستأنف. |
| `python-package/teledrive/media_scanner.py` | استخدام entity المحلول وهوية peer الصحيحة أثناء المسح. |
| `python-package/teledrive/transfer_manager.py` | throttle للتقدم، reset للحدود، حل chat المرجعي، ومسار download جزئي؛ مع إبراز أخطاء العامل غير الملغاة. |
| `python-package/teledrive/queue_manager.py` | تسجيل أعطال run غير الملغاة بحدث ظاهر. |
| `python-package/teledrive/locale/ar.json` و`locale/en.json` | مفتاح `err.private_channel_unresolved`. |
| `python-package/tests/test_m27_hardening.py` | 16 اختبارًا للـthrottle، الأعطال، peers، cache warming، ورسوم resume. |
| `docs/*` | تحديث الحالة والتسليم والمخاطر وسجل التغييرات لهذا العمل. |

## نتائج التحقق الفعلية

| الأمر | النتيجة |
|---|---|
| `python3 -m compileall teledrive` | PASS |
| `python3 -m pytest -q tests/test_m27_hardening.py -v` | `16 passed` |
| `python3 -m pytest -q tests/test_transfer_control.py tests/test_m26_t03_rebased.py -v` | `18 passed` |
| `python3 -m pytest -q tests/test_i18n.py tests/test_no_ad_hoc_loops.py -v` | `5 passed` |
| `python3 -m pytest -q tests` | `734 passed in 34.81s` |
| `python3 teledrive_launcher.py --check` | `binding check ok: 51/51 ready actions resolve` |
| `python3 -m teledrive.notebook_cells --check` | `notebooks are in sync` |
| `cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb` | PASS |
| `python3 -m teledrive.package_service --build --output teledrive_v4.5.zip` | PASS؛ أزيل ملف zip بعدها |
| `pnpm run lint && pnpm run build` | PASS؛ استُخدم pnpm لأن Bun غير متاح محليًا |

## حدود الإثبات والضمانات

> هذه المرحلة **local/fake-tested** وليست اختبارًا حيًا. لا تثبت بواباتها أن حساب Telegram حقيقيًا يستطيع قراءة قناة خاصة أو أن Google Drive أو Colab أنجزا جولة نقل حقيقية.

لم تُعدل النوتبوكات أو `requirements.lock` أو `bun.lock` أو workflows أو `action_registry.py` أو `handlers.py` أو `services.py` أو `ui.py` أو `app_context.py` أو `drive_client.py` أو `progress_tracker.py`. لا يضاف `asyncio.run()` تحت `teledrive/**`، ولا يحذف Pause/Stop مسار `.part` أو ملف Google Drive. في حالة عدم إمكان حل القناة، يعرض الخطأ الدائم المترجم بدل محاولة غير آمنة.

## GitHub والتراجع والخطوة التالية

قبل الالتزام: نقطة التراجع هي `85822af73326d60894bde9737a35672a4aae1e08`. بعد التدقيق النهائي فقط، ينشأ الالتزام بالرسالة المتفق عليها، ثم يُدفع الفرع ويُفتح PR إلى `main`. لا يدمج PR إلا عند نجاح كل فحوص CI. بعد الدمج، يبقى على المالك تنفيذ بروتوكول حي: قناة خاصة يمكن للحساب الوصول إليها، ملف كبير يتوقف ويُستأنف من `.part`، تحقق وصول Google Drive، وجولة Colab نظيفة.
