# M42 — استعادة Telegram Session Vault المشفّر في Colab

## الهدف والحالة

يعالج M42 طلب تسجيل Telegram من جديد بعد Restart رغم وجود Session Vault على حساب Google Drive نفسه. خط الأساس هو `main` عند `b7a2dac217376a9dbc322aa307a105a37d372491`، والعمل موجود محليًا فقط على فرع `fix/m42-colab-session-vault-restore`.

> **الحالة الصادقة:** M42 دُمج واجتاز CI ونُشرت حزمته المتطابقة، لكن لا يوجد اختبار Cell 1–4 حي للحزمة الجديدة؛ لذلك لا `Colab-ready` ولا `Complete`.

| البند | النتيجة |
|---|---|
| زوج Session Vault في Drive | موجود بصيغة versioned format 2؛ تحقق قراءة فقط |
| حذف أو تعديل ملفات Drive | لم يحدث |
| إعادة إنتاج العيب | مثبتة باختبار RED قبل التصحيح |
| إصلاح المصدر | مطبق ومثبت محليًا |
| CI / PR / merge / publish | PR #89 MERGED؛ CI Python/Frontend PASS؛ publish #32648838713 SUCCESS |
| اختبار Colab الحي | معلق |

## الدليل وسبب المشكلة

تم فتح `TeleDrive_AppData` في Google Drive التجريبي قراءةً فقط. ظهرت `td_telegram.active.json` مع زوج `.creds` و`.session` versioned نشط. لم تفتح محتويات هذه الملفات، ولم تنزل أو تنسخ أو تعدل. هذا ينفي فرضية حذف Vault كسبب مباشر لطلب تسجيل جديد.

Vault format 2 لا يخزن API Hash في Drive؛ بل يستخدمه لتغليف blob الجلسة. كان مولد Cell 3 يكتشف وجود Vault ثم لا يقرأ `TELEGRAM_API_HASH` من Colab Secrets ولا يعرض طلبًا مخفيًا للبيانات اللازمة. وفوق ذلك، كانت Cell 4 تنفذ:

```python
session_vault.restore_from_context(ctx, secret=api_hash)
```

لكن `restore_from_context` يهمل `secret` ويستدعي `autorestore_once()` بلا مفتاح فك. في runtime جديد لا توجد ذاكرة `TelegramAuth` مسبقة ولا Colab Secret متاح، فتصل `SessionVault.autorestore()` إلى `missing api_hash for unwrap` وتعود لمسار login اليدوي. يبقى زوج Drive دون حذف وفق تصميم الاستعادة.

| طبقة | العيب قبل M42 | الأثر |
|---|---|---|
| Cell 3 | يتخطى Secrets/prompt عند وجود Vault | لا يملك runtime API Hash |
| Cell 4 wrapper | يهمل `secret` الصريح | لا يصل مفتاح الفك إلى Vault |
| format 2 | لا يحفظ API Hash في Drive عمدًا | الاستعادة الصحيحة تتطلب Secret runtime |
| fallback | يبقي Vault البعيد | لا دليل أن Session Vault حذفت |

## أقل إصلاح آمن

لا يغير M42 صيغة format 2، ولا ينقل API Hash إلى Drive، ولا يغير session blob، ولا يغير action IDs أو React transport أو handlers أو مسارات النقل. التغييرات تقتصر على `SessionVault` ومولد Colab واختبارات وعلامات توثيق مولدة.

1. توسعت `restore_from_context` و`autorestore_once` و`autorestore` لقبول `secret` اختياري داخل العملية فقط. يعطي `autorestore` الأولوية لبيانات format 1 legacy إن وجدت، ثم secret الصريح، ثم fallback Colab Secrets.
2. يعيد `SessionVault.probe()` الآن `api_id` غير السري الموجود أصلًا في metadata؛ يبقى API Hash غائبًا من metadata format 2.
3. يقرأ Cell 3 Colab Secrets قبل قرار وجود Vault. إن كان Vault موجودًا ولا يوجد Secret، يطلب API ID/Hash المخفيين فقط؛ لا يطلب phone أو OTP.
4. تمرر Cell 4 hash نفسه إلى الاستعادة، ولا تعيد `set_credentials` إذا نجحت الاستعادة؛ لتفادي إنشاء عميل Telegram ثانٍ بلا داعٍ.
5. ما زال failure الناتج من revocation أو فشل النقل يحتفظ بنسخة Drive؛ لا يمس M42 `forget` أو logout أو ملفات `.part`.

## اختبار الانحدار

أضيف الاختبار `test_restore_from_context_uses_explicit_secret_for_format_two_vault`. ينشئ SQLite session وهمية وVault format 2 مشفرًا في `FakeDrive`، ثم يحاكي VM جديدة بمسح API Hash من ذاكرة `TelegramAuth`. يمرر الاختبار secret بالضبط مثل Cell 4.

قبل التصحيح كان الاختبار يفشل لأن `restore_from_context(..., secret="…")` يرجع `False`. بعد التصحيح يثبت الاختبار أن الاستعادة تنجح، وأن API ID/Hash يصلان إلى `set_credentials`، وأن قائمة أسماء وbytes الملفات البعيدة قبل وبعد الاستعادة متطابقة. لا يستخدم الاختبار حساب Telegram أو Google Drive حقيقيين ولا يطبع سرًا.

## نتائج التحقق المحلي

| البوابة | الأمر أو الدليل | النتيجة |
|---|---|---|
| Regression Vault | 3 اختبارات مستهدفة لـformat 2/probe/wrapper | `3 passed` |
| Python suite | `pytest -q tests` | `770 passed` |
| bytecode | `python -m compileall -q teledrive` | PASS |
| bindings | `python teledrive_launcher.py --check` | `51/51 ready actions resolve` |
| generator | `python -m teledrive.notebook_cells --write` ثم `python -m teledrive.notebook_cells --check` | PASS؛ النسخ مولدة من المصدر |
| notebook bytes | `cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb` | PASS |
| React contracts | `node --experimental-strip-types --test tests/teledrive-sandbox.contract.test.mjs` | `33/33 PASS` |
| frontend build | `pnpm run build` | PASS |
| frontend lint | `pnpm run lint` | exit 0؛ 9 تحذيرات baseline، 0 errors |
| package | `python -m teledrive.package_service --build --output /tmp/m42-teledrive_v4.5.zip` | PASS؛ archive integrity PASS |

## bridge والحزمة الحالية

تم تنزيل الأصلين العامين الحاليين قراءةً فقط. manifest يشير إلى commit `bc9fc5f42bcec51d2f7f6566021cf0f2433de9d1` وSHA-256 `ab3d3db21f754546bb2e154be56faf0a0315fea7c9cc2a6df639d85db41d1529`، واحتوى ZIP المنشور رمز `__teledriveReactPanelLease` الخاص بإصلاح M41.

إذن لا دليل أن release/tag الحالي يعود إلى كود bridge أقدم. إلا أن هذا لا يثبت المظهر أو lifecycle داخل Cell 4 الفعلي؛ KNOWN_ISSUES #71 يبقى مفتوحًا إلى أن يظهر `Gradio · Live bridge` في Colab المنشور.

## ما لم يثبت وما لم ينفذ

لم يتم تشغيل Cells 1–4 للحزمة المعدلة داخل Colab، ولم يحدث login أو نقل Telegram أو اختبار Drive حي ضمن M42. دُمج PR #89 ونُشر الزوج العام المتطابق، لكنه لا يحول الاختبارات الوهمية إلى تجربة Telegram حية.

## التراجع وخطة النشر الآمنة

التراجع هو عكس merge `d54b010…` ثم إعادة نشر ZIP وmanifest مطابقين لـSHA سابق؛ لا حذف release أو tag أو Session Vault. توقف workflow الأول fail-closed عند اختلاف الحجم، ثم استُبدل الزوج المطابق معًا وتحقق [workflow #32648838713](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32648838713) من bytes العامة بنجاح.

الخطوة التالية هي Runtime Colab جديد على نفس Drive واختبار Cell 1–4. معيار النجاح المرئي هو `telegram session vault: restored` ثم `Gradio · Live bridge`؛ عند فشل الاستعادة تسجل `telegram restore:` المنقحة فقط للتمييز بين missing secret وrevocation وtransport.
