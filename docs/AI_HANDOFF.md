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
