# بطاقة تسليم M52-T03 — وجهة مستقلة لكل مهمة تنزيل + خلية المراقبة الأخيرة (2026-10-23)

| الحقل | القيمة |
|---|---|
| الحالة | **PR #136 مفتوح كمسودة؛ CI قيد التشغيل؛ لا دمج أو نشر إنتاجي** |
| الفرع | `feat/per-task-drive-folders-monitor-cell` المبني على `feat/auto-colab-tunnel-handoff` |
| PR | [#136 — Add per-task Drive folders and final Colab monitor cell](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/136) |
| الهدف | السماح باختيار مجلد Drive مستقل لكل مهمة في Universal Downloader دون تغيير وجهة Telegram أو الوجهة العامة، وإضافة خلية مراقبة في آخر النوتبوك. |
| التنفيذ | أُضيف متصفح مجلدات مستقل في صفحة التحميل الشامل يستعمل `drive.list_folders` للقراءة فقط؛ يرسل `folder_id` و`folder_name` مع المهمة؛ تحفظ إعادة المحاولة الوجهة نفسها. لم يُعدّل اختيار المجلد العام عند اختيار مجلد للتحميل الشامل. |
| النوتبوك | أُضيفت خلية المراقبة كمصدر قانوني في `python-package/teledrive/notebook_cells.py`، مع تحديث `colab_cells.json` ونسختي `python-package/notebook/TeleDrive.ipynb` و`public/TeleDrive.ipynb`. احتُفظ بخلية Vercel التجريبية الموجودة في الفرع، وأُدخلت في المصدر القانوني حتى لا تُفقد. خلية المراقبة هي آخر خلية، وتجمع الآن أعداد المهام من طابور Telegram ومدير Universal Downloader المنفصلين. |
| أمان الخلية | في كتلة `finally` تستعيد الخلية `write` و`writelines` و`flush` للمجاري التي غيّرتها. أُحدّثت تعليمات النوتبوك: شغّل خلية المراقبة بعد بدء التحميل، ولا تشغّل خلية التنظيف/الإغلاق قبل انتهاء التحميل لأنها تغلق التطبيق. |
| الاختبارات | أُضيفت اختبارات عقد لاختيار المجلد المستقل والحفاظ على اسم المجلد عند إعادة المحاولة، وحُدّثت اختبارات تعداد الخلايا الاختيارية. فُحص JSON للنوتبوك، وتطابق المصدر مع الخلايا المصدّرة، وتطابق نسختي النوتبوك. |
| ما لم يثبت | لا يوجد اختبار حي داخل Colab أو Google Drive حتى الآن، ولم يُثبت فعليًا تحميل Telegram وUniversal Downloader بالتوازي إلى مجلدين مختلفين. لا تدّعِ نجاحًا حيًا حتى يختبر المالك ذلك. |
| التالي | انتظار CI على PR #136؛ إصلاح أي فشل قبل الدمج. بعد ذلك، اختبار حي بملفين صغيرين ومجلدين مختلفين مع التحقق من الوجهتين، ثم اختبار المراقبة أثناء النقل. لا تُحدّث الإصدار المنشور ضمن هذا التغيير قبل اجتياز البوابات. |

---

# بطاقة تسليم M52-T02 — أدوات التحكم في التنزيل الخارجي (2026-10-21)

| الحقل | القيمة |
|---|---|
| الحالة | **MERGED TO MAIN; CI and package publication passed; live Colab/Drive verification pending** |
| الدمج | [PR #124]( https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/124 ), merge commit `08363cdffa4653f95db39e88e0e124022dc86afe` |
| الملفات الأساسية | `python-package/teledrive/universal_downloader.py`, `python-package/teledrive/web_dashboard.py`, `python-package/tests/test_universal_downloader_controls.py` |
| التقرير | `docs/PHASE_REPORTS/PHASE_M52_T02_UNIVERSAL_DOWNLOAD_CONTROLS.md` |
| المقارنة | Telegram queue had per-item pause/resume/stop/retry actions; Universal URL Downloader only had start/cancel. These are separate engines, so web URL controls now call UniversalDownloadManager, not Telegram QueueManager. |
| التنفيذ | Added cooperative pause/resume gates for yt-dlp and direct HTTP, real cancel that wakes paused tasks, retry creating a new task from saved URL/quality/Drive folder, and bulk pause/resume/cancel/retry-failed. API routes: `/api/universal/pause`, `resume`, `retry`, `bulk`; existing cancel retained. |
| حدود مهمة | `gdown` blocking calls do not safely support pause; `pause_supported=false` prevents a fake pause button. Drive upload is not forcibly interrupted. Retry is a fresh task, not byte-level resume. |
| التحقق | Validation: main CI [run #39627612669](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39627612669) passed; `876 passed, 1 warning`; frontend lint/build, notebook generator checks, byte-compile, and archive build passed. Package publication [run #39627612843](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39627612843) passed; release [pkg-2026.08.09-m15t07](https://github.com/body199-cmyk/drive-buddy-3579bf74/releases/tag/pkg-2026.08.09-m15t07) targets `08363cdffa4653f95db39e88e0e124022dc86afe`, ZIP 674316 bytes, SHA-256 `6b0ede407ea2e68af03f93c88041824c9328140bef5bc35e6b45bb069f9a9be6`, and the published manifest was verified against the archive. No live Colab/Drive transfer test yet. |
| التالي | Owner-run live Colab verification remains: restart the runtime, run the normal package update/bootstrap flow, test direct HTTP and yt-dlp pause/resume/cancel/retry, then verify the Drive upload. Do not claim live success until observed. |

---

# بطاقة تسليم M52-T01 — بوابة TeleDrive العامة عبر Vercel (2026-10-21)

| الحقل | القيمة |
|---|---|
| الحالة | **PLANNED ONLY — NOT IMPLEMENTED** بناءً على طلب المالك الصريح |
| ملف التخطيط | `docs/PHASE_REPORTS/PHASE_M52_T01_PUBLIC_VERCEL_PORTAL_PROPOSAL.md` |
| قائمة العمل | `docs/TODO.md` — Task `M52-T01` |
| الهدف | رابط ويب عام واحد لتسجيل الدخول وربط Google Drive وTelegram اختياريًا، والتحكم في محرك TeleDrive الحقيقي دون مطالبة المستخدم بالتنقل يدويًا بين GitHub وColab |
| المقترح | Vercel للواجهة وAPI قصيرة؛ Google OAuth منفصل عن صلاحيات Drive؛ backend آمن للأسرار؛ طبقة اتصال worker موثقة مع المحرك؛ حالة اتصال وطابور حقيقيان. Colab خيار انتقالي منخفض التكلفة لكنه غير مضمون التشغيل التلقائي أو الاستمرار؛ worker دائم بديل أكثر استقرارًا لكنه قد يتطلب تكلفة |
| حدود النطاق | لا تغييرات على كود المحرك، لا إعداد Vercel، لا إنشاء OAuth credentials، لا ربط حسابات، ولا نشر عام لهذه الفكرة. المطلوب الآن هو التوثيق فقط |
| قواعد التنفيذ لاحقًا | ابدأ بتدقيق معماري وADR وتقدير تكلفة؛ صمم عزل المستخدمين وحماية الأسرار قبل multi-user؛ لا بيانات وهمية؛ لا تعتبر CI إثباتًا حيًا؛ لا تَعِد بتشغيل Colab المجاني تلقائيًا |
| التالي عند موافقة المالك | تدقيق معماري/إثبات مفهوم محدود فقط، بعد انتهاء أعمال الإصلاح ذات الأولوية وبموافقة صريحة على بدء التنفيذ |

---

# بطاقة تسليم M51-T01 — مسارات الصوت العربية والإنجليزية في يوتيوب (2026-10-21)

| الحقل | القيمة |
|---|---|
| الحالة | **Merged to main; CI passed; package release refreshed successfully; live YouTube/Colab test pending** |
| PR / merge | [PR #123](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/123), merged as `325848978f1f4def008df8210bc6ca15284626ca` |
| Publication | GitHub Actions [run #39624773056](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39624773056) completed successfully. Stable release [pkg-2026.08.09-m15t07](https://github.com/body199-cmyk/drive-buddy-3579bf74/releases/tag/pkg-2026.08.09-m15t07) now targets merge commit `325848978f1f4def008df8210bc6ca15284626ca` (release assets updated 2026-10-21 15:22 UTC). Colab live download/player verification remains pending. |
| الملفات | `python-package/teledrive/universal_downloader.py`; `python-package/tests/test_universal_downloader.py`; `docs/TODO.md`; `docs/PHASE_REPORTS/PHASE_M51_T01_YOUTUBE_AR_EN_AUDIO_TRACKS.md` |
| المتطلب | تنزيل المسارين العربي والإنجليزي فقط عندما يتوفران، داخل ملف واحد متعدد المسارات؛ إذا توفر واحد فقط نحتفظ به، وإذا لم يتوفر أي منهما نرجع لأفضل مسار صوت متاح. |
| التنفيذ | `_youtube_multiaudio_format()` يرتب محاولات التنسيق: عربي+إنجليزي، عربي وحده، إنجليزي وحده، ثم أفضل صوت متاح. تفعيل `audio_multistreams` وMKV محصوران في تنزيل فيديو يوتيوب؛ مسارات الصوت فقط والمنصات الأخرى تبقى كما كانت. بادئات اللغة تشمل صيغًا مثل `en-US`. |
| الاختبارات | CI run [#39624150025](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39624150025) passed Python tests/package checks, Colab contract checks, archive build, and frontend lint/build. |
| ما لم يُثبت | لم يُختبر تنزيل حقيقي من يوتيوب أو Colab/Drive، ولم يُتحقق من ظهور المسارين في مشغل فعلي. بعض الفيديوهات قد لا تعرض metadata للغة بشكل متوقع أو لا توفر اللغتين. |
| الخطوة التالية | انشر حزمة جديدة تحتوي merge commit المذكور وتحقق من ZIP/manifest/hash/commit، ثم اختبر فيديو يوتيوب حقيقيًا في Colab وتحقق من مساري MKV والتبديل في مشغل يدعمها. لا تدّعِ نجاحًا حيًا اعتمادًا على CI وحده. |
| التراجع | Revert لميزة PR؛ التغيير معزول ولا يعدل Telegram أو Vault أو مخطط قاعدة البيانات. |

---

# بطاقة التسليم الشاملة — M50-T01: سجل الإصلاحات، المشكلات، التحقق، وخطة التطوير
> **قاعدة إلزامية لكل وكيل/مطور لاحق:** هذا الملف سجل تاريخي تراكمي. لا تحذف محتواه القديم، ولا تستبدل البطاقات السابقة، ولا تعِد كتابة التاريخ على أنه حالة حالية. عند أي جلسة جديدة: اقرأ هذا القسم أولًا ثم البطاقات السابقة ذات الصلة، وافحص حالة `main` والـPRs والـActions من GitHub قبل التصرف. أضف بطاقة جديدة في أعلى الملف أو ألحق قسمًا مؤرخًا في نهايته؛ حدّث الحالة القديمة فقط بإضافة توضيح مؤرخ، ولا تمحُ الحالة التي كانت صحيحة وقتها. يجب أن يذكر كل تغيير: المشكلة، الدليل، السبب المؤكد/المحتمل، الملفات، الإصلاح، الاختبارات الفعلية، ما لم يُختبر، طريقة التراجع، والخطوة التالية. **ممنوع الادعاء أن Colab أو Telegram أو Drive أو منصة خارجية تعمل حيًا اعتمادًا على unit tests وحدها.**
>
> **حدود الأمان والاستقرار:** لا تكسر مسار Telegram العامل أو طابور النقل، ولا تحذف بيانات Drive/Vault أو ملفات `.part` أو Releases/Tags كحل سريع. لا تغيّر ملفات/مسارات محمية أو مخطط قاعدة البيانات بلا ضرورة موثقة. لا تجرّب تجاوز حواجز الأمان أو صلاحيات GitHub. لا تسجّل أسرار Telegram أو Cookies أو Tokens في Git أو السجلات. لا تعالج مشكلة بالتخمين قبل قراءة الملف والـdiff وتشغيل الاختبارات المناسبة.

| الحقل | القيمة |
|---|---|
| Updated | `2026-10-21` |
| Task ID | `M50-T01` |
| Repository | [body199-cmyk/drive-buddy-3579bf74](https://github.com/body199-cmyk/drive-buddy-3579bf74) |
| Base branch reviewed | `main` (the current default-branch content at review time) |
| Status | **DOCUMENTATION PREPARED ON BRANCH; PR/CI/merge pending** |
| Documentation branch | `docs/comprehensive-handoff-2026-10-21` |
| Related code PRs | [#120 release workflow](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/120) · [#121 Facebook cookies](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/121) |
| Related CI evidence | [PR #121 run #39620917319](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39620917319) succeeded for the PR checks; no live Facebook download was performed. |
| Detailed report | `docs/PHASE_REPORTS/PHASE_M50_T01_COMPREHENSIVE_HANDOFF_AND_AUDIT.md` |

## 1. الغرض من هذا التسليم

هذه البطاقة تجمع حالة المشروع كما أمكن إثباتها من السجل والملفات وطلبات الدمج المتاحة في 21 أكتوبر 2026. الهدف أن يستطيع وكيل جديد فهم: ما المنتج، ما الذي أُصلح بالفعل، ما الذي لا يزال مجرد PR، ما الشكاوى التي أبلغ عنها المالك، ما الذي تدعمه الأدلة، وما الخطوة الآمنة التالية. هذه ليست شهادة بأن كل شيء يعمل حيًا؛ بل سجل يفصل بين **تعديل الكود** و**نجاح الاختبارات** و**النشر** و**التحقق الحقيقي في Colab**.

## 2. قواعد ثابتة لا يجوز فقدها عند تسليم المشروع

1. **السجل تراكمي:** اقرأ `docs/AI_HANDOFF.md` و`docs/PROJECT_CONTEXT.md` و`docs/TODO.md` و`docs/KNOWN_ISSUES.md` وتقارير `docs/PHASE_REPORTS/` ذات الصلة قبل أي تعديل. أضف سجلًا جديدًا ولا تمسح ما قبله.
2. **حماية Telegram والطابور:** لا تعِد تصميم مسار Telegram أو أقفال/حدود التزامن أو طابور النقل لمجرد اقتراح عام من نموذج آخر. افحص الاختبارات والسجل، وغيّر أقل مساحة ممكنة.
3. **حزمة Colab ليست بالضرورة أحدث نسخة من GitHub:** يمكن أن يبقى ZIP/manifest أو ملف محلي قديمًا حتى لو كان الكود في `main` أحدث. تحقق من `Package update:`, و`package reference:`, والـcommit وSHA-256 والـmanifest قبل تشخيص عدم ظهور ميزة.
4. **Restart مهم بعد تحميل وحدات Python:** إذا كانت وحدات TeleDrive قد حُمّلت بالفعل في Runtime، لا تفترض أن إعادة تشغيل Cell 1 ستستبدلها بأمان. اتبع حارس التحديث في النوتبوك؛ عند حالة رفض التحديث يجب التوقف وطلب Restart بدل fallback صامت إلى ZIP قديم.
5. **لا مساواة بين CI والواقع:** اختبارات Python وواجهة الويب وبناء ZIP لا تثبت نجاح Google Colab أو جلسة Telegram أو Google Drive أو تنزيل YouTube/Facebook حقيقي. سجّل كل مستوى تحقق منفصلًا.
6. **النشر عبر GitHub Actions:** رفع الأصول من بيئة التطوير قد يفشل بسبب عدم الوصول إلى `uploads.github.com` أو صلاحيات التكامل. استخدم workflow الموثوق من GitHub Actions، ولا تدّعِ النشر بعد فشل dispatch/403.
7. **أمان الأسرار:** لا تضع session/API hash/OTP/cookies/token في ملفات المشروع أو logs أو screenshots أو manifests. ملف cookies يبقى محليًا/داخل Runtime فقط ولا يُرفع إلى Git.
8. **لا تحذف كحل افتراضي:** لا تحذف Release/Tag أو Vault أو ملف جزئي `.part` أو ملف Drive. أي تراجع يجب أن يكون محددًا ومُوثقًا، مع حماية البيانات.
9. **تحقق من الحالة الحية أولًا:** قبل إعادة تطبيق إصلاح قديم، افحص `main` وPRs المفتوحة وActions وملفات التقارير. بعض التقارير التاريخية تتحدث عن فرع غير مدمج أو baseline أقدم.
10. **إذا كان اقتراح Gemini/أي نموذج خارجي غير سليم، فلا تنقله حرفيًا:** تحقّق من صياغة الكود، والتوافق، والاختبارات. في تدقيق Gemini الأخير كانت بعض الأمثلة المقترحة غير جاهزة للتطبيق كما هي، كما أن استبدال ملف محلي ذريًا لا يثبت وحده أن رفع Drive اكتمل على السحابة.

## 3. ملخص تنفيذي للحالة في 2026-10-21

### 3.1 تغييرات موجودة على `main` وفق السجل السابق
- توجد تحسينات سابقة مدمجة في واجهة الويب الحديثة/الكلاسيكية، السمات، تحليل القنوات، حالات الطابور، نقل Telegram، الاستئناف، وحماية Vault. تفاصيلها وتواريخها وأرقام PRs محفوظة في البطاقات الأقدم أدناه؛ لا تعِد تنفيذها دون التحقق من الشجرة الحالية.
- إصلاحات Universal Downloader السابقة عبر PRs **#115 و#116** ذُكرت على أنها مدمجة: إصلاح فحص اعتماديات `yt-dlp`/`gdown`، دعم الإلغاء قبل الرفع وعرض سرعة النقل، واختبارات Python/واجهة/ZIP والتحقق من وجود `universal_downloader.py` داخل الحزمة. **لم يثبت ذلك تنزيلًا حيًا من كل منصة.**
- سبق تسجيل شكوى بطء تنزيل YouTube؛ أضيف `concurrent_fragment_downloads = 4` لمسار YouTube مع اختبار لمسار المحاولة الأساسية وإعادة المحاولة عند خطأ YouTube. هذا تحسين مبني على الكود/الاختبارات، وليس وعدًا بسرعة معينة على Colab.
- النوتبوك المباشر من `main`: [Open TeleDrive in Google Colab](https://colab.research.google.com/github/body199-cmyk/drive-buddy-3579bf74/blob/main/public/TeleDrive.ipynb).

### 3.2 تغييرات حديثة لا تزال غير مدمجة وقت إنشاء هذه البطاقة
- **PR #120 — إصلاح Release workflow:** [فتح PR #120](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/120). الفرع `fix/gemini-audit-release-pipeline`، head `e45cbbcdfc1c2d9ee8be7fa81030f7d4edc166a7`. يعيد تصميم `.github/workflows/release.yml` ليبني من commit المختار بعد الاختبارات، يتحقق من ZIP وبنية `requirements.lock`، ينشئ manifest يحوي commit/SHA-256/الحجم/build run ID والرابط، ويرفض tag مكررًا. **الـPR مفتوح وغير مدمج؛ لم يُشغّل workflow النشر end-to-end.** يلزم تدقيق YAML ومنطق النشر ونجاح CI ثم تشغيل يدوي من المالك بعد الدمج.
- **PR #121 — Cookies اختيارية لـFacebook:** [فتح PR #121](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/121). الفرع `fix/facebook-cookie-download-support`، head `45e653ab69873122e1bd96e6d69f755c3aad9fb9`. أضيف دعم cookie file بصيغة Netscape عبر `YTDLP_COOKIES_FILE` أو `/content/facebook_cookies.txt` أو `/content/cookies.txt` أو مجلد TEMP، مع حصر استخدامه بروابط Facebook وfb.watch. CI run [#39620917319](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/39620917319) نجح (اختبارات الحزمة، فحوصات Colab، بناء الأرشيف، وفحوصات frontend). **الـPR مفتوح وغير مدمج، ولم يُختبر تنزيل Facebook حيًا.** لا يمكن للكوكيز تجاوز صلاحيات الحساب أو حماية المنصة أو media غير المتاح.
- محاولة الدمج الآلي في الجلسة السابقة حُجبت بواسطة فحوصات أمان GitHub/التكامل. لا تحاول الالتفاف على الحظر؛ الدمج يحتاج مسار GitHub المعتاد وموافقة المالك.

## 4. سجل الشكاوى والمشكلات: ما قاله المالك وما أثبتناه

### 4.1 مشكلة ظهور مخرجات Colab واختفائها
**بلاغ المالك:** خلية الواجهة تظهر لحظة ثم تختفي، ويظهر خطأ JavaScript عن تعذر تحميل ملفات العرض؛ جُرّب Android ومتصفح Opera ولم يحل التغيير وحده المشكلة.  
**ما نعرفه:** هذا الخطأ قد يكون من طبقة عرض Colab/الجلسة/ملفات JavaScript أو الكوكيز، ولا يثبت بمفرده أن FastAPI أو TeleDrive تعطل. في جلسات لاحقة أبلغ المالك أن المخرجات عادت للعمل، لكن لا نعتبر ذلك إثباتًا عامًا لكل Runtime أو متصفح.  
**التصرف الصحيح:** سجّل نص الخطأ كاملًا، وحدد أي خلية وأي Runtime، وافصل بين ظهور Output في Colab وبين وصول رابط Gradio/Web وبين عمل API فعلي. لا تعد كتابة الواجهة أو تغيير الخادم قبل عزل طبقة العطل.  
**الحالة:** مشكلة تاريخية ذات حلول جزئية/تجريبية؛ لا تُغلق نهائيًا إلا بعد تشغيل النوتبوك من `main` في Colab حي.

### 4.2 تشغيل حزمة قديمة بدل أحدث كود
**بلاغ/تشخيص متكرر:** تعديلات GitHub لا تظهر بعد Restart أو إعادة تشغيل الخلايا، وقد تُحمّل Cell 1 حزمة ZIP محلية/من Drive أقدم.  
**الدليل في السجل:** البطاقات M49 تسجل أن مسار التحديث كان قد يتجاهل نتيجة `REFUSED` ثم يحاول `resolve_package_zip()`، بما قد يسمح بحزمة مخزنة قديمة؛ كما سبق أن تأخر النشر عن دمج إصلاحات الواجهة.  
**الإصلاحات ذات الصلة:** M49-T01 دمج حارس ضد ZIP قديم وأتمتة نشر الحزمة حسب السجل؛ M49-T02 ونسخة T01 التي كانت على فرع منفصل أضافتا/تستكملان مبدأ fail-closed: إذا تعذر التحقق من المصدر الأحدث، أوقف Cell 1 ولا تستعد ZIP قديمًا بصمت. يجب فحص الحالة الحالية لـM49-T02 في GitHub لأنها سُجلت على أنها على فرع وبانتظار CI/Colab، فلا تفترض دمجها.  
**التحقق المطلوب:** commit المرجعي + tag/release + manifest + SHA-256 + الحجم، ثم فتح Notebook من `main`، Restart runtime، وتشغيل الخلايا بالترتيب. لا تخلط بين نشر الحزمة وبين تشغيلها في حساب المالك.

### 4.3 Universal Downloader — واجهة التنزيل الشامل
**بلاغ المالك:** صفحة التنزيل الشامل/زر الدخول إليها لم يكن يستجيب كما ينبغي، مع طلب الحفاظ على محرك النقل والطابور الحقيقيين وعدم وضع بيانات وهمية. كما كانت هناك متطلبات لتحسين دعم روابط المنصات.  
**الإصلاحات السابقة المسجلة:** PRs #115 و#116 مدمجة حسب ملخص الجلسات: اعتماديات `yt-dlp` و`gdown`، الإلغاء قبل الرفع، إظهار سرعة النقل، وفحوصات تثبت وجود وحدة التنزيل في ZIP.  
**التعديل الحديث:** PR #121 يضيف cookies اختيارية لـFacebook/fb.watch فقط.  
**ما لا يزال غير مثبت:** تنزيل فعلي لكل من Facebook/YouTube/X/TikTok/Instagram، خصوصًا الروابط الخاصة أو المحمية، واختبار الواجهة في Colab حي.  
**قاعدة التشخيص:** إذا فشل تنزيل، احتفظ برسالة الخطأ الفعلية من job/yt-dlp، والمنصة ونوع الرابط (مع إخفاء token/query الحساسة). لا تفترض أن cookies هي السبب أو العلاج الوحيد.

### 4.4 سرعة YouTube / Telegram
- **YouTube:** أبلغ المالك أن السرعة كانت نحو 2–3 MB/s في تجربة، وظهر مثال آخر عند 3.43 MB/s. أضيفت أربعة تنزيلات fragments متزامنة في yt-dlp لمسار YouTube واختبارات للمسار الأساسي ومسار retry. هذه أرقام ملاحظة في جلسات المالك وليست benchmark معياريًا ولا ضمان سرعة.
- **Telegram:** توجد سلسلة كبيرة من التحسينات الموثقة في M44/M45: حدود تزامن مستقلة، تنزيل/رفع على مرحلتين، محاذاة 512 KiB، حفظ `.part` واستئنافها، تجنب عناصر الرسائل التي لا تحمل وسائط، وحدود للقارئات المتداخلة. كانت هناك ملاحظات سابقة أن السرعة الحية ما زالت ضعيفة؛ لا تدّعِ أن التحسين حلها بنسبة محددة من دون نقل ملف كبير وقياس `mbps=`/الوقت والحجم والتحقق من Drive.
- **قاعدة سلامة:** لا تضف اتصالات Telegram أو concurrency إضافية عشوائيًا؛ قد تزيد الضغط أو تفسد ترتيب البيانات. أي tuning جديد يجب أن يثبت بقياس A/B حقيقي مع بقاء pause/resume/stop والاستئناف سليمة.

### 4.5 ألوان واجهة X/الثيم الرمادي
**طلب المالك:** اللون السابق كان أسود أكثر من اللازم، والمطلوب رمادي داكن/متوسط بين الأسود والأبيض على غرار X.  
**ما تم توثيقه:** M47-T02 أضاف سمة `dim` مستوحاة من X بجانب الفاتح والداكن، مع ألوان `#15202B` و`#1D9BF0` في الواجهة الحديثة/الإعدادات وحفظ التفضيل.  
**التحقق:** هناك اختبارات محلية لعقود الواجهة ومحاكاة DOM وتبديل السمات، لكن هذا لا يغني عن معاينة المالك في شاشة الهاتف/Colab. لا تعُد تغيّر الثيم إلى أسود كامل بحجة التبسيط.

### 4.6 زر «التحميل الشامل» وطلب واجهة حقيقية
**بلاغ المالك:** الضغط على خيار/صفحة التنزيل الشامل لم يكن يفتح أو ينفذ شيئًا.  
**المبدأ الصحيح:** لا تُعرض بيانات وهمية ولا أزرار شكلية؛ اربط عناصر الواجهة بالـAPI والطابور الحقيقيين، وأظهر حالات loading/success/error/cancel.  
**الوضع:** إصلاحات Universal Downloader السابقة وCI لا تكفي وحدها لإثبات أن كل زر يعمل في Runtime المستخدم. يجب تجربة النقر من المتصفح بعد نشر ZIP حديث، ومراقبة الطلب/الاستجابة وسجل job، مع اختبار cancel قبل/أثناء الرفع.

### 4.7 مشكلات تحليل القنوات والواجهة الحديثة
**المشكلة السابقة المؤكدة في سجل M47:** تحليل القناة كان يفشل لأن الوضع الافتراضي `message` لا يناسب روابط القنوات، بينما `chat` و`latest` لنفس الرابط يعملان. عولج ذلك بوضع تلقائي يختار `message` للرسالة المباشرة و`chat` للقناة/المجموعة، مع بقاء الأوضاع اليدوية. كما عولج عرض نتائج التحليل والتحديد والفلاتر وتقسيم أقسام الواجهة.  
**الدليل المسجل:** اختبارات محلية وHTTP/DOM باستخدام عميل Telegram وهمي، لا إثبات عام لكل قناة/حساب حي. راجع M47/M48/M46 قبل أي تعديل لاحق.

### 4.8 مخاطر اقتراحات Gemini الأخيرة
التقرير الخارجي مفيد كقائمة أسئلة، لكنه ليس دليلًا تنفيذيًا بحد ذاته. ظهرت به أمثلة/استنتاجات لا ينبغي نقلها حرفيًا: صياغة URL غير صالحة في مثال، ومقطع Python بمسافات بادئة غير صحيحة، واقتراحات لا تثبت أن Drive أكمل الرفع السحابي. كما أن purge للـmodule cache قد يترك references قديمة أو يخلق حالات غير متسقة.  
**الإجراء:** استعمل التقرير لتحديد مواضع الفحص فقط؛ افحص كل ادعاء على الملفات الحالية، واكتب اختبارًا يثبت العطل قبل التعديل. تم اختيار إصلاحين محددين في PR #120 و#121 بدل إجراء تنظيف واسع أو إعادة كتابة شاملة.

## 5. ما تم إصلاحه تاريخيًا (ملخص، والتفاصيل في البطاقات السابقة)

هذه ليست قائمة بكل commit على حدة؛ كل تقرير مرحلة سابق هو المرجع التفصيلي ويجب الحفاظ عليه:
- **النقل والطابور:** حدود تزامن، pause/stop/resume، استئناف offset، حفظ الملفات الجزئية، منع ملفات وهمية صفرية الحجم لعناصر Telegram غير القابلة للتنزيل، حالات طابور أوضح، ومنع سباقات في worker permits.
- **سرعة Telegram:** طلبات 512 KiB، مساران متداخلان محدودان للملفات الكبيرة، reorder window محدود، ثم pipeline تنزيل→رفع وحدود مستقلة للملفات/القوارئ/طلبات GetFile. لا تزال القياسات الحية مطلوبة لكل إصدار.
- **واجهة الويب:** تقسيم أقسام مستقلة، تنقل متجاوب، ثيمات light/dim/dark، نتائج تحليل قابلة للبحث/التحديد، تحسين وضع تحليل القناة، وبقاء Gradio مسارًا آمنًا لتسجيل الدخول.
- **جسر React–Gradio:** معالجة remount/cleanup وwatcher القديم وlease وإعادة استخدام bridge الحي حسب تقارير M38/M41.
- **Vault Telegram:** استعادة Drive-managed format 3، ترحيل format 2 بعد الاستعادة الناجحة، وعدم إظهار بيانات الجلسة في React/logs/Git. التحقق الحي عبر Runtime جديد يظل منفصلًا عن الاختبارات.
- **التوزيع/الحزمة:** إصلاحات سابقة لخط النشر والتحقق من ZIP/manifest، لكن ظهرت فجوات بين الكود المدموج والحزمة المنشورة. لهذا PR #120 يعالج release workflow القديم في `.github/workflows/release.yml`، ولا يجوز اعتباره ناجحًا قبل اختبارات ونشر فعلي.
- **التوافق بين المنصات:** إصلاح سابق لـ`os.statvfs` على Windows باستخدام `shutil.disk_usage` و`Path.as_posix()` في M34.
- **Universal Downloader:** الاعتماديات والإلغاء والسرعة والتضمين في الحزمة (PRs #115/#116 وفق السجل)، مع دعم cookies اختياري لـFacebook في PR #121 غير المدمج وقت هذه البطاقة.

## 6. خطة التطوير المستقبلية — مرتبة بالأولوية

### P0 — إنهاء بوابة الإصدار والتحديث دون ZIP قديم
1. راجع PR #120 كاملًا، خاصة YAML، التحقق من tag الفريد، بناء ZIP بعد الاختبارات، محتوى manifest، والتحقق بعد النشر من **الأسماء والحجم وSHA-256 والـcommit** لا مجرد وجود الأصول.
2. افحص أي خطأ محتمل في release notes أو quoting وYAML parsing على GitHub Actions. لا تعتبر الـPR صحيحًا من قراءة diff وحدها.
3. بعد نجاح CI وموافقة المالك ودمج PR #120، شغّل workflow يدويًا بإصدار جديد غير مستخدم. تأكد أن ZIP وmanifest متطابقان ويشيران إلى نفس commit/build run.
4. قارن الـmanifest مع تنزيل عام للأصل، ثم افتح Notebook من `main`، Restart Runtime، وتحقق من commit وhash المطبوعة. لا تحذف/تستبدل tag قائمًا بلا خطة تراجع موثقة.
5. راجع حالة M49-T02 على GitHub؛ إن لم تكن مدمجة، لا تتعامل معها كميزة وصلت للمستخدم.

### P1 — إكمال دعم Facebook باختبار حقيقي
1. راجع PR #121 ثم ادمجه بالطريقة المعتادة إذا نجحت الفحوصات ووافق المالك.
2. اختبر رابطًا عامًا مسموحًا ثم رابطًا يحتاج تسجيل الدخول بحساب يملك حق المشاهدة، مع cookie Netscape محلي/Runtime فقط.
3. تحقق من أن ملف cookies لا يظهر في logs أو artifacts أو Git، وأنه لا يُرسل إلى YouTube/X أو روابط أخرى.
4. وثّق رسالة الخطأ الدقيقة إن فشل التنزيل؛ لا ترفع cookies للمساعدة في التشخيص.

### P1 — اختبار Colab end-to-end
بعد نشر الحزمة:
1. افتح رابط Notebook أعلاه مباشرة من `main`.
2. استخدم Runtime جديدًا أو Restart حسب تعليمات حارس التحديث؛ شغّل الخلايا 1–4 بالترتيب.
3. سجل نسخة الحزمة/commit/manifest وSHA-256، وحالة Drive وTelegram وظهور رابط Gradio والواجهة الحديثة.
4. اختبر ملفًا صغيرًا من Telegram إلى Drive، ثم pause/resume/stop على حالة آمنة إن أمكن.
5. اختبر Universal Downloader بمنصة عامة متاحة، ثم Facebook وفق الصلاحيات.
6. اختبر الأزرار الأساسية من الهاتف (Android) لأن هذا سياق الاستخدام الفعلي للمالك.
7. ضع مخرجات منقحة في تقرير مرحلة جديد؛ لا تنشر session IDs أو tokens أو cookies أو روابط خاصة.

### P2 — أداء وموثوقية التنزيل
- بناء benchmark متكرر للسرعة مع تسجيل حجم الملف، وقت البداية/النهاية، MB/s، عدد fragments، نوع الشبكة، ونتيجة checksum بعد الرفع.
- فصل زمن تنزيل المصدر عن زمن رفع Google Drive حتى لا تُنسب عنق زجاجة إلى الجزء الخطأ.
- اختبار pause/resume بعد انقطاع حقيقي أو محاكاة transport failure، والتحقق من عدم تكرار/فقد bytes.
- اختبار ملفات صغيرة وكبيرة، روابط بطيئة، أخطاء 429/403، وإلغاء المستخدم.
- لا ترفع حدود التزامن افتراضيًا إلا بعد benchmark وإثبات عدم تضرر Telegram rate limits والطابور.

### P2 — اختبار واجهة التنزيل الشامل
- اختبار تنقل الصفحة وزر فتحها على الهاتف والكمبيوتر.
- اختبار حالات valid URL/invalid URL/unsupported URL/expired cookies/permission denied.
- اختبار progress/queue/cancel/error/success وتحديث الحالة دون refresh يدوي.
- التأكد من أن كل حالة معروضة مصدرها backend حقيقي، لا mock data.
- وضع اختبارات contract للـAPI وتفاعل DOM في CI حيث يمكن، مع إبقاء smoke test حي مطلوبًا.

### P3 — صيانة الجودة والأمان
- الاستمرار في مراجعة redaction قبل إضافة logs جديدة؛ لا تضع قيم cookies أو secrets في logs.
- تدقيق حدود الثقة بين واجهة الويب وGradio وFastAPI وColab proxy، من دون نقل أسرار Telegram إلى React.
- مراجعة التبعيات المثبتة وقفلها واختبار توافقها مع Python/Colab الحالي.
- توثيق runbook مختصر للمستخدم النهائي: كيف يفتح أحدث Notebook، يحدد النسخة، يعيد تشغيل Runtime، ويجمع سجل خطأ آمن.
- إضافة test يفشل إذا اختلفت نسخة النوتبوك المولدة عن المصدر أو إذا لم تحتوِ الحزمة على الملفات المطلوبة.
- لا تفتح إعادة تصميم SQLite أو cleanup أو module-cache purge دون bug reproducible؛ سجلات سابقة تشير إلى أن قاعدة البيانات لديها WAL وbusy timeout وRLock، ومدير النقل يحفظ `.part` في حالات محددة.

## 7. قائمة التحقق لكل إصلاح مستقبلي

- [ ] قرأت `PROJECT_CONTEXT.md` و`AI_HANDOFF.md` و`TODO.md` و`KNOWN_ISSUES.md` والتقرير المرتبط.
- [ ] تحققت من `main` وPRs المفتوحة وActions قبل افتراض أن الإصلاح غائب.
- [ ] كتبت المشكلة مع خطوات إعادة إنتاج ودليل من log/test/code.
- [ ] فرّقت بين السبب المؤكد والفرضية.
- [ ] غيّرت أقل عدد من الملفات، وحافظت على Telegram والطابور والأسرار.
- [ ] أضفت/حدّثت اختبارًا يغطي العطل دون بيانات وهمية.
- [ ] شغّلت الاختبارات المناسبة فعلًا وسجلت الأمر والنتيجة، ولم تكتب PASS بلا تشغيل.
- [ ] تحقق build/ZIP/manifest بعد نجاح الاختبارات إذا مسّ التغيير التوزيع.
- [ ] فتحت PR ووثقت head SHA؛ لا تدّعِ الدمج قبل رؤية merged=true.
- [ ] بعد النشر، فصلت بين CI وColab live test وexternal download test.
- [ ] أضفت ملخصًا مؤرخًا إلى هذا الملف وإلى تقرير المرحلة وTODO/KNOWN_ISSUES عند الحاجة، دون حذف التاريخ.
- [ ] كتبت طريقة تراجع لا تمسح بيانات المستخدم أو Vault أو Releases/Tags.

## 8. الحالة النهائية الصادقة عند كتابة هذا التسليم

- هناك تاريخ طويل من الإصلاحات والاختبارات المحلية/CI الناجحة، وتفاصيله محفوظة في البطاقات التاريخية أسفل هذا القسم.
- PR #121 فحوصاته الآلية ناجحة حسب run #39620917319، لكنه ما زال مفتوحًا وغير مدمج ولم يُختبر تنزيل Facebook حقيقيًا.
- PR #120 لتغيير release workflow ما زال مفتوحًا وغير مدمج؛ لم يجرِ نشر end-to-end من workflow الجديد، ولذلك لا يوجد دليل أن مسار الإصدار الجديد يعمل بالكامل.
- لا يوجد في هذه الجلسة إثبات حي جديد من Colab أو Telegram أو Drive أو Facebook. لا تستخدم عبارة «اتصلح نهائيًا» لهذه الطبقات قبل الاختبار.
- الخطوة الآمنة التالية: مراجعة واعتماد PR التوثيق هذا، ثم معالجة PR #120 و#121 عبر GitHub المعتاد، وبعدها نشر نسخة جديدة والتحقق من الحزمة وColab حيًا.
- **التراجع:** هذا التغيير توثيقي فقط. يمكن revert لالتزام التوثيق إذا لزم، لكن الأفضل إصلاح النص في commit جديد مع إبقاء التاريخ السابق محفوظًا.

---

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


# M53-T01 — Telegram concurrency and adaptive GetFile pool (2026-10-23)

- Branch: fix/telegram-adaptive-request-pool (based on feat/per-task-drive-folders-monitor-cell).
- Requested behavior: owner-selected concurrency is honored up to 100 files rather than silently clamped at 4/8.
- Changes: TELEDRIVE_TG_FILES ceiling/default raised to 100; GetFile pool ceiling raised to 100 (default remains 24); Drive upload buffer ceiling/default raised to 100; download permits are released before waiting for an upload-buffer slot; new TelegramRequestPool freezes on FloodWaitError.seconds, halves its live limit and gradually recovers after successful requests. TELEDRIVE_TG_FLOODWAIT_MAX configures the freeze cap (default 3600 s, max 86400 s).
- Automated tests added/updated; CI must run before considering merge. No real Telegram/Drive or Colab benchmark has been performed.
- Risk: 100 is a requested ceiling, not a guarantee Telegram will sustain it. FloodWait, connection capacity, local disk/RAM, and serialized Drive upload remain real constraints. A live test should ramp 8→12→20→... and watch FloodWait, failures, disk and throughput.
- Do not claim production/live success based on CI alone; no package release is authorized by this note.
