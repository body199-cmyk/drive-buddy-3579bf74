# بطاقة التسليم — M49-T01: حارس منع ZIP القديم في Colab

| الحقل | القيمة |
|---|---|
| Updated | `2026-10-21` |
| Base SHA | `36b9aec7b031007fce4c9b7ba784dda8730bb78c` |
| الفرع | `fix/colab-package-stale-fallback` |
| الحالة | **IMPLEMENTED ON BRANCH; PR/CI and live Colab verification pending** |
| التقرير | `docs/PHASE_REPORTS/PHASE_M49_T01_COLAB_STALE_PACKAGE_GUARD.md` |

## ما تغير في هذه الجلسة

- السبب المحدد: Cell 1 كان يتجاهل نتيجة `REFUSED` ثم يستدعي `resolve_package_zip()`. عند اكتشاف وحدات TeleDrive محمّلة، كان ذلك يسمح باستخدام ZIP محلي قديم بدل التوقف وطلب Restart.
- المصدر `python-package/teledrive/notebook_cells.py` يحفظ نتيجة التحديث ويوقف التنفيذ برسالة صريحة في حالة `runtime already loaded` قبل fallback.
- أُضيف اختبار ترتيب في `python-package/tests/test_package_update.py`، وحُدّثت نسختا `TeleDrive.ipynb` و`colab_cells.json`.
- `.github/workflows/release-current.yml` حُدّث ليعمل على تغييرات الحزمة في `main` أو dispatch يدويًا؛ يبني ويختبر قبل النشر، ويضع `build_run_id` في manifest، ويرفع ZIP قبل manifest ثم يتحقق من البصمات العامة.
- تم تحديث `CHANGELOG.md` و`TODO.md` و`KNOWN_ISSUES.md` وإضافة تقرير المرحلة.

## ما لم يُثبت بعد

لم تُشغّل اختبارات Python أو بوابات CI في checkout محلي خلال هذه الجلسة. لا تدمج قبل نجاح PR CI، خصوصًا `python -m teledrive.notebook_cells --check` وتطابق نسختي النوتبوك. لا يوجد اختبار Google Colab حي، ولا تأكيد Telegram/Drive أو نقل ملف حقيقي.

## الخطوات التالية للوكيل

1. راجع diff كاملًا على الفرع؛ انتبه لتطابق مولّد النوتبوك والنسختين و`colab_cells.json`.
2. شغّل البوابات المنصوص عليها في `docs/PROJECT_CONTEXT.md` أو افتح PR وانتظر CI: `compileall`, `pytest -q`, launcher check، notebook check، `cmp`، package build، وfrontend lint/build.
3. أصلح أي فشل على نفس الفرع وسجّل نتائج حقيقية فقط.
4. بعد الدمج، راقب Workflow النشر الآلي وتحقق من manifest وZIP وSHA-256 وcommit.
5. افتح النوتبوك من `main` في Colab، نفّذ Restart ثم Cells 1–4، وتحقق من تحديث الحزمة والواجهتين، ثم جرّب نقل ملف صغير إلى Drive قبل إغلاق Known Issue.

---

# بطاقة التسليم — M48-T01: أقسام تنقّل مستقلة للوحة الويب الحديثة

| الحقل | القيمة |
|---|---|
| Updated | `2026-10-21` |
| Base SHA | `d6320963e2e8c8b97ea7410e0fd02b537a241ba1` (`main` بعد PR #111) |
| الفرع | `arena/f4d7af29-drive-buddy-3579bf74` |
| الحالة | **IMPLEMENTED + LOCALLY VERIFIED (`854 passed`); PR/CI/merge pending** |
| التقرير | `docs/PHASE_REPORTS/PHASE_M48_T01_WEB_DASHBOARD_SECTIONS.md` |

## النتيجة

- صارت لوحة الويب تسع وجهات منفصلة (نظرة عامة، الحسابات، وجهة Drive، تحليل، نتائج، الطابور، إعدادات، سجلات، صيانة)؛ لوحة واحدة ظاهرة في كل مرة.
- الكمبيوتر يستخدم شريطًا جانبيًا، والهاتف شريطًا سفليًا وقائمة «المزيد» قابلة للإغلاق وذات دعم لوحة مفاتيح. الروابط تحفظ hash وتدعم الرجوع/التقدم.
- بقيت جميع أزرار/أفعال الصفحة والجسر، وميزات النتائج والفلاتر والطابور. لا تغيير في المصادقة: بيانات Telegram السرية تبقى في Gradio الآمن. الثيمات الثلاثة فاتح/X `dim`/داكن محفوظة كما هي.
- النموذج المرفق استُخدم مرجعًا للتقسيم والتنقل فقط؛ لم يُنقل أي من بياناته أو سلوكه الوهمي.

## الأدلة المحلية

`854 passed, 1 warning` · اختبار لوحة الويب `22 passed` · compileall PASS · launcher `54/54` · notebook check + cmp PASS · Web `node --check` PASS · اختبار DOM مصغّر للتنقل PASS · package build `654048` bytes، SHA-256 `f4659a134c90b19bc0c77b2ba5a9616064e1049060d3b7a473203bdc4854f2c4`. لا يتوفر Chromium/Playwright؛ ولا إثبات Colab/Telegram/Drive حي.

## الخطوة التالية

فتح PR من الفرع الحالي، انتظار نجاح CI، ثم الدمج بالمسار المعتاد. لا تنشر حزمة ولا تدّعِ اتصالًا حيًا قبل نشر منفصل وإثبات مالك Colab.

---

# بطاقة التسليم — M47-T02: ثلاث سمات وإصلاح تحليل القنوات وإعادة تنظيم لوحة الويب

| الحقل | القيمة |
|---|---|
| Updated | `2026-10-20` |
| Base SHA | `cec787c832b44af9e516f6447f99d6d89f430af1` (`main` بعد PR #110 / M47-T01) |
| الفرع | `arena/65c0a4f3-drive-buddy-3579bf74` |
| الحالة | **IMPLEMENTED + LOCALLY VERIFIED; PR/merge and owner Colab proof are the remaining release steps** |
| التقرير | `docs/PHASE_REPORTS/PHASE_M47_T02_MODERN_DASHBOARD_THEMES_AND_CHANNEL_ANALYZE.md` |

## النتيجة

- أُثبت أن تحليل القناة كان يفشل لأن لوحة الويب تبدأ بوضع `message`، بينما `chat` و`latest` لنفس الرابط يعملان. الافتراضي الآن «تلقائي» في المتصفح: رسالة مباشرة ← `message`، قناة/مجموعة ← `chat` بحد الرسائل؛ والأوضاع اليدوية الأربعة باقية.
- أضيفت سمة `dim` بأسلوب X (`#15202B`/`#1D9BF0`) إلى جانب الفاتح والداكن الكامل في مبدّل اللوحة الحديثة والإعدادات والتفضيل المحفوظ.
- أعيد تنظيم الصفحة إلى خمس خطوات، وأصبحت نتائج التحليل في صندوق `430px` مستقل التمرير والطابور في صندوق `350px`، مع بحث وفلاتر وتحديد نطاق/مجموعة وتحكم فردي بعناصر الطابور.
- حُفظت كل معرفات/وظائف M47-T01؛ واختبار DOM يمنع المعرفات المكررة أو المراجع المفقودة. أسرار Telegram ما زالت في Gradio الآمن فقط، والكلاسيكية باقية احتياطيًا.

## الأدلة المحلية

`853 passed` · compileall PASS · launcher `54/54` · notebook check + cmp PASS · Node contracts `34/34` · Web script `node --check` PASS. تشغيل HTTP محلي بعميل Telegram وهمي مفوّض أعاد 35 مرشحًا لتحليل قناة، ومحاكاة JSDOM نفذت التحليل التلقائي والتحديد والبحث وتبديل `dim/light/dim` بلا أخطاء JavaScript. حزمة محلية مختبرة `650261` bytes، SHA-256 `bd011ed0252a340bc1db12c6619ca1ef829603bd54e561ae2745e59853b42828`.

## ما تبقى

- متابعة PR هذا الفرع وCI ثم الدمج كما طلب المالك.
- بعد الدمج لا يُدّعى وصول Colab قبل نشر حزمة جديدة والتحقق من Tag/Manifest/ZIP، ثم تأكيد المالك الحي بلصق رابط قناة ونقل ملف صغير إلى Drive.

---

# بطاقة التسليم — M46-T03: إصلاح الواجهتين الحديثة والكلاسيكية + استمرار توزيع Colab

| الحقل | القيمة |
|---|---|
| Updated (UTC) | `2026-10-20` |
| Base SHA | `1f337c47a3f14dc4bd9d0468b80b6bdddbcebb77` (`main` بعد PR #107) |
| الفرع | `arena/955ee77e-drive-buddy-3579bf74` |
| merge | **PR [#108](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/108) MERGED** at `d8c22df07b4a672ff00389cb880c847534d15db7` |
| CI | PR run [#39452872933](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39452872933) and main push run [#39453144455](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39453144455): Python + Frontend SUCCESS |
| الحالة | **MERGED + CI-PASSED; package publish and Colab live proof pending** |
| التقرير | `docs/PHASE_REPORTS/PHASE_M46_T03_DUAL_UI_AUDIT_AND_DISTRIBUTION.md` |

## النتيجة

- تأكد أن آخر Release وقت بدء الجلسة كان `pkg-39320945506` مبنيًا من `106d8f8`، قبل دمج إصلاح M46-T02 #107؛ والتاج الثابت `pkg-2026.08.09-m15t07` كان أقدم بلا `web_dashboard.py`. إذن إصلاح T02 لم يصل Colab قط. `gh workflow run release-current.yml` من الوكيل عاد 403؛ مسار النشر يحتاج تدخل المالك.
- صُححت صفحة Web: أوضاع Scanner القانونية الأربعة وحقول الرسالة/النطاق/الحد، جدول نتائج المرشحين وتحديد/مسح، وتسميات حالة Telegram/Drive عربية.
- بوابة الخلية 1 تدعم latest-release redirect بلا API quota وتختار الأحدث فعليًا بمقارنة `build_run_id` بين أحدث إصدار والتاج المثبت. نسخة الـWorkflow الجاهزة في `docs/M46_T02_release_current_workflow.yml` تضيف هذا الحقل إلى الـManifest.
- جعل Cell 4 افتراضيًا `Run_Both_Together` (Gradio أولًا) حتى يظل مسار تسجيل الدخول الآمن متاحًا مع الحديثة.

## الأدلة المحلية

`835 passed` · compileall PASS · launcher `54/54` · notebook check + cmp PASS · React contracts `34/34` · `node --check` لسكربت Web PASS. تشغيل HTTP حي مزدوج: Gradio `/` و`/config`، Web `/` و`/api/health` و`/api/metrics` و`/api/state`، تحديد المرشحين عبر bridge، Idempotent re-launch، وحلقة `ctx.aio`=`pong`؛ **FAILURES: 0**. حزمة build مختبرة `628920` bytes، SHA-256 `89de5831be2350d564d8196c4780173a7b5b5693d7b544106fa7702327a4e736`.

## ما تبقى

- **بعد الدمج الحالي:** انشر الحزمة مرة واحدة من GitHub Actions → `Publish current TeleDrive package` (الـworkflow الحي القديم يدوي وبلا `build_run_id`، لكن أحدث `pkg-*` يُلتقط عبر API أو redirect؛ الأفضل تبنّي نسخة `docs/M46_T02_release_current_workflow.yml` لتفعيل التوزيع الآلي/التاج الثابت).
- لا يُدّعى Colab-ready قبل فتح Notebook `main` بعد النشر وتشغيل Runtime > Restart and run all والخلايا 1–4؛ يجب ظهور URL Gradio وURL/زر Web.

---

# بطاقة التسليم — M45-T01 (استئناف Arena): تحقق وإغلاق الفجوة الحرفية الوحيدة

| الحقل | القيمة |
|---|---|
| Updated (UTC) | `2026-10-19T19:24Z` |
| Session type | New Coding Session after Arena closure (استئناف DOC M45-T01) |
| Resume status | **RESUME_VERIFIED** |
| Base SHA | `d991cf4783545ee838d3c2eeaf3b98fc0c22cf6f` (main بعد دمج PR #100) |
| الفرع | `arena/3befa0b6-drive-buddy-3579bf74` |
| merge | **PR [#104](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/104) MERGED** → main `337c19e7d69a903c1b7c5060e572d17f09ff8f86` (CI على الـPR: Python + Frontend SUCCESS) |
| الحالة | **VERIFIED COMPLETE** — DOC كُتب ضد baseline `db0f2a0` وافتراضه («M44-T01 غير مدمج») غير صحيح للشجرة الحية |

## نتيجة الاستئناف

- فحص §9 أظهر أن **كل** بنود DOC §3 موجودة ومدمجة أصلًا في `main` عبر PRs
  #93/#95/#98/#100: الحدود الثلاثة، `_tg_semaphore`، خط الأنابيب مرحلتين، محاذاة
  512 KiB، حفظ `.part` عند ≥512 KiB، `_has_downloadable_media()`، مصنّفات الأخطاء،
  وكل اختبارات M45 في `test_fast_download.py` و`test_m27_hardening.py`.
- الفجوة الحرفية الوحيدة: marker `serverresent` المطلوب في §3.5 — أُضيف إلى
  `TRANSIENT_MARKERS` مع اختبار تصنيف في `test_fast_download.py`.
- `pkg-2026.08.09-m15t07` **منشور** (أحدث إصدار من `33bf50d` عبر جلسات موازية:
  sha256 `7774a340…`، `600312` bytes) — KNOWN_ISSUES #79 مغلقة.
- دُمج PR #104 بعد مطابقة `main` مرتين (M45-T02/T03 ثم M45-T04 دُمجتا بالتوازي
  أثناء الجلسة؛ تعارضان حُلّا بالاحتفاظ بالطرفين، و`teledrive_v4.5.zip` المُتبع
  في main أُبقِى كما هو).
- البوابات بعد الدمج النهائي على الشجرة الموحّدة: `813 passed` · compileall PASS ·
  launcher `54/54` · notebook check + cmp PASS · package build PASS · `node --test`
  34/34. `bun` غير مثبت (لا تغيير frontend).
- **نشر الحزمة من الجلسة: FAILED** — `gh workflow run release-current.yml` أعاد
  `HTTP 403: Resource not accessible by integration` (نفس حادث §8). الإصدار
  المنشور حاليًا يثبت M45-T01 كاملة؛ إعادة النشر من `337c19e` خطوة واحدة بيد
  المالك (Actions → Publish current TeleDrive package → Run workflow).
- ما لم يُثبت: قياس Colab/Telegram حي (بيد المالك).
- التفاصيل والأدلة: `docs/PHASE_REPORTS/PHASE_M45_T01_TELEGRAM_SPEED_AND_STABILITY.md` §9.

---

# بطاقة التسليم — M45-T01: خط أنابيب تنزيل/رفع، محاذاة 512 KiB، ووسائط حقيقية فقط

| الحقل | القيمة |
|---|---|
| Updated (UTC) | `2026-10-19` |
| Base SHA | `acab9d228e45a5a77a5fef9198cf3df9dd1f4729` |
| الفرع | `arena/5b79cd32-drive-buddy-3579bf74` |
| الحالة | **MERGED + CI-PASSED; release re-create needs one owner workflow dispatch; Colab live proof pending** |
| التقرير | `docs/PHASE_REPORTS/PHASE_M45_T01_TELEGRAM_SPEED_AND_STABILITY.md` |

## النتيجة

- أُعيد تأسيس توصيات Gemini على الشجرة الحالية بعد M44-T02 بدل تطبيقها حرفيًا على baseline قديم.
- السبب الجذري للسرعة: اتصال MTProto واحد + طلب 512 KiB متسلسل لكل ملف (زمن الرحلة يحكم)،
  وكل ملف صغير كان يفتح طلبًا غير محدود، وكل عامل يمسك إذنه أثناء انتظار قفل Drive.
- الحل: ثلاثة حدود مستقلة (`MAX_CONCURRENT_TG_DOWNLOADS=4`، `PARALLEL_DOWNLOAD_STREAMS=4`،
  `TG_INFLIGHT_REQUESTS=8`) + خط أنابيب مرحلتين يحرر عامل التنزيل قبل الرفع + `MAX_PENDING_UPLOADS=4`.
- مسار التنزيل لا ينفّذ نداء Drive حاجبًا: فحص التكرار استباقي فقط عند خمول الخدمة، وإلا
  يُعاد استخدام ملف Drive الموجود في مرحلة الرفع.
- `download_partial` يحاذي 512 KiB للملفات الكبيرة، ويستأنفها بالقارئات المتداخلة.
- فشل `download_media_fast` بعد ≥512 KiB يحفظ `.part` ويعيد المحاولة من offset بدل مسحه.
- `_has_downloadable_media()` تمنع Web Page/Poll/Geo/Contact من إنشاء صف 0 بايت `.bin`.
- تصنيف `request was unsuccessful` كـtransient و`invalid limit`/`downloaded file missing` كـpermanent.

## الأدلة المحلية

`809 passed` · compileall PASS · launcher `54/54` · notebook check + cmp PASS ·
`node --test` 34/34. لا تغيير في notebook/workflow/auth/Drive/schema/Vault.
`bun run lint` NOT RUN (`bun: command not found`), no frontend files changed.

## حادث النشر — 2026-10-19

رفع الأصول من الـsandbox غير ممكن (`uploads.github.com` محجوب). محاولة `--clobber` فقدت
`teledrive_manifest.json`، فحُذف الـrelease والـtag لإعادة إنشائهما ذريًا، لكن
`workflow_dispatch` أعاد 403 من رمز الجلسة. **المطلوب من المالك:** تشغيل
`release-current.yml` يدويًا مرة واحدة؛ المسار «release absent → create atomically» سينشر
حزمة M45-T01 من `main` بالأصلين ويتحقق علنًا. Cell 1 تعمل بالحزمة المحفوظة حتى ذلك الحين
وتطبع `REFUSED update endpoint unreachable`.

## ما لم يثبت / الخطوة التالية

لا قياس حي. يلزم: دمج، إعادة نشر ZIP + manifest من SHA المدموج، Restart Colab، تأكيد
`telethon crypto backend=cryptg`، ثم نقل ملف ≥100 MB وتسجيل `mbps=` من السجل، مع
Pause/Resume والتحقق من Drive. لا تضف اتصالات MTProto إضافية قبل A/B موثق.

## التراجع

Revert التغيير؛ يعود سيمافور واحد وfallback من الصفر. لا حذف من Drive/Vault/release.

---

# بطاقة التسليم — M44-T02: تسريع تنزيل Telegram بمدخلين محدودين

| الحقل | القيمة |
|---|---|
| Updated (UTC) | `2026-10-19` |
| Base SHA | `db0f2a02502b94d2975fa23d7bce5d6af9b24e52` |
| الفرع | `arena/360d78bc-drive-buddy-3579bf74` |
| merge | PR [#95](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/95) merged: `8c7df03` → `a032caf3be5f0b55b8b85af64dc134de2fb6a006` |
| CI | [#39271630415](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39271630415) SUCCESS |
| الحالة | **MERGED + CI-PASSED; candidate package in owner Drive; release/Colab live proof pending** |
| التقرير | `docs/PHASE_REPORTS/PHASE_M44_T02_BOUNDED_PARALLEL_TELEGRAM_DOWNLOAD.md` |

## النتيجة

- بعد بلاغ المالك عن ملف 1.3 GB وصل 41% في نحو 10 دقائق (تقدير ~0.9 MB/s)، فُحص المصدر: M44-T01 يطلب 512 KiB لكن كل ملف ما زال تنزيله تسلسليًا.
- أُضيف للميديا ≥32 MiB قارئان MTProto بقطاعات متداخلة؛ الأصغر يبقى متسلسلًا. Semaphore واحد على TelegramService يحدّ الطلبات المتزامنة إلى 2 إجمالًا، حتى مع عدة عمال للطابور.
- يُعاد ترتيب القطع بنافذة أربع قطع، ويُكتب فقط prefix متصل إلى `.part`. Pause/Stop يترك prefix صالحًا. أي خطأ/حجم غير متوقع يلغي المسارات ويترك TransferManager يستخدم fallback الحالي من byte 0.
- لا تغييرات dependency أو notebook/workflow أو auth/Drive/SQLite. لا مساس بقفل Drive.

## الأدلة المحلية

`798 passed` · compileall PASS · launcher `54/54` · notebook check + cmp PASS · package build PASS: `583226` bytes، SHA-256 `d77a4e29e63ae17b48b2720ddce52a443eee5302bd26f256fb9c9103b0480dd3`.
New tests exercise two active ranges, ordered reconstruction, valid prefix on Pause, and fallback-triggering transport failure. `bun run lint` NOT RUN: `bun: command not found`; no frontend files changed.

## ما لم يثبت / الخطوة التالية

اختبارات fake لا تثبت Telegram/Colab speed. يلزم review/CI/merge ثم إعادة نشر ZIP وmanifest، Restart Colab، التأكد من `telethon crypto backend=cryptg`، ونقل ملف كبير مع التحقق من الحجم وPause/Resume. لا ندّعي تسريعًا فعليًا قبل benchmark حي. لا تضف مسارات أو concurrency إضافية بلا دليل.

## التراجع

Revert التغيير؛ الملفات الأصغر أصلًا تسلسلية، والملفات الكبيرة تعود إلى fast sequential 512 KiB مع legacy fallback. لا حذف من Drive/Vault/release.

---

# بطاقة التسليم السابقة — M44-T01: مفتاح التحديث التلقائي وسرعة تنزيل Telegram

| الحقل | القيمة |
|---|---|
| Updated (UTC) | `2026-10-19` |
| code merge | PR [#93](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/93) merged; incorporated in release commit `db0f2a02502b94d2975fa23d7bce5d6af9b24e52` |
| الحالة | **MERGED + RELEASE-PUBLISHED; live throughput still poor per owner report** |
| release verification | workflow [#39263636789](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39263636789) SUCCESS; ZIP `580737` bytes + manifest `378` bytes; target db0f2a0 |
| التقرير | `docs/PHASE_REPORTS/PHASE_M44_T01_UI_HEARTBEAT_AND_DOWNLOAD_SPEED.md` |

The persisted refresh toggle and 512 KiB fast sequential Telegram path are present in the release. `cryptg==0.6.0` is pinned; runtime backend must still be checked in Colab logs. The owner's report that a 1.3 GB file reached 41% in about ten minutes motivated M44-T02. No live performance claim is made.

---

# بطاقة التسليم السابقة — M43: Vault Drive-managed ورابط التحليل المحفوظ

| الحقل | القيمة |
|---|---|
| Updated (UTC) | `2026-08-24` |
| code commit / merge | `e974dfd12f2bf372e34dbca463a082b7017400e2` → main `2d5893dea014c638937e953919c68f2251d035ef` عبر PR [#91](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/91) |
| الحالة | **MERGED + CI-PASSED + PACKAGE-PUBLISHED — Colab live pending** |
| CI | push [#32689166257](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689166257) وPR [#32689176699](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689176699): Python + Frontend SUCCESS |
| publish | [#32689575111](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689575111) SUCCESS |
| التقرير | `docs/PHASE_REPORTS/PHASE_M43_DRIVE_MANAGED_VAULT_AND_ANALYZE_LINK.md` |

## النتيجة المنشورة

تعالج M43 تجربة المالك المطلوبة: بعد تسجيل Telegram وحفظ Vault جديدة على حساب Drive نفسه، يستطيع Runtime Colab جديد استعادة الجلسة من Drive فقط بلا Colab Secret أو هاتف أو OTP ما دامت Telegram تقبل الجلسة. لا يعرض هذا التصميم API Hash أو session أو هاتف أو OTP في React أو السجلات أو artifacts.

الصيغة الافتراضية الجديدة هي **Vault format 3 (Drive-managed)**. تبقى format 1 وformat 2 قابلة للاستعادة؛ تحتاج format 2 مفتاحها الخارجي مرة أخيرة فقط، ثم تُنشر format 3 versioned بصورة ذرية بعد نجاح الاستعادة. لا يصبح البديل نشطًا قبل اكتمال staging/manifest، ولا يمس فشل الاستعادة إلا النسخة المحلية المؤقتة.

## واجهة React وGradio

حقل رابط القناة/الرسالة يستمد آخر قيمة محفوظة من backend الحي عبر `LiveUiStateService.snapshot()` ويعيدها في React وGradio. الحفظ يتم بعد نجاح التحليل أو من زر/blur صريح، ويمكن مسحه صراحةً. القيمة تحفظ في SQLite settings ضمن Runtime المشروع؛ لا تستخدم `localStorage` أو `sessionStorage` ولا تذهب إلى Drive. لا توجد حالة React وهمية أو backend جديد.

## الأدلة

| البوابة | النتيجة |
|---|---|
| Python محليًا وCI | `779 passed` محليًا؛ CI Python SUCCESS في push وPR |
| launcher | `53/53 ready actions resolve` |
| notebook check + cmp | PASS؛ artifacts مولدة من المصدر ومتطابقة |
| React contracts | `34/34 PASS` محليًا |
| lint/build | PASS محليًا وCI Frontend SUCCESS؛ تحذيرات baseline فقط |
| package | archive M43: SHA-256 `28d94129a9894fee0cf31545d286c176403c814c45203dbaf0e002eb7a390b79`، حجم `570612` bytes |
| النشر العام | manifest/ZIP الرسميان يطابقان merge `2d5893d…` والبصمة والحجم أعلاه |

## النشر الآمن

توقف [النشر الأول #32689333249](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689333249) كما يجب fail-closed لأن الأصل المنشور كان `568320` bytes مقابل archive M43 `570612` bytes. لم يُحذف release أو tag.

وبتفويض المالك، بُني archive وmanifest من merge SHA نفسه، واستُبدل الأصلان الرسميان معًا فقط، ثم تحقق تنزيل عام غير مخزن من SHA والحجم والـmanifest. أُزيل أصلان زائدان نتجا من محاولة تسمية مؤقتة بعد تأكيد الزوج الرسمي؛ لم يُحذف release/tag. نجح [workflow #32689575111](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32689575111) بعد ذلك في التحقق العام وتحديث metadata إلى merge M43.

## حد الأمان

اختار المالك صراحةً أن Drive هو حد الحماية العملي للـVault. من يملك صلاحية كاملة لزوج Vault format 3 في `TeleDrive_AppData` يستطيع استعادة جلسة Telegram؛ لا تُنشر القيم في logs/Git/UI. راجع `docs/decisions/ADR-004-session-vault.md`.

## ما لم يثبت

لا `Colab-ready` أو `Complete` بعد. يجب تشغيل Cells 1–4 على نفس حساب Drive وإثبات `telegram session vault: restored` ثم `Gradio · Live bridge`. لم يُقرأ أو يُحذف محتوى Vault، ولم يُنفذ OTP أو نقل Telegram/Drive حي ضمن M43. يبقى KNOWN_ISSUES #71 مفتوحًا حتى يظهر bridge الحي في Cell 4.

## التراجع

يعكس merge `2d5893d…` ثم يُنشر ZIP/manifest متطابقان مع SHA السابق عبر مسار release fail-closed. لا يحذف التراجع release/tag ولا Vault تلقائيًا.
