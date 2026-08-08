# TeleDrive v5.0 — الدستور الموحد الشامل مع بروتوكول استئناف LM Arena

# TeleDrive v5.0

## الدستور الموحد الشامل، عقد المنتج، ونظام التطوير عبر LM Arena Agent

**نوع الوثيقة:** المرجع الوحيد والأعلى للمشروع والحوكمة والتنفيذ والاستمرارية

**إصدار الحوكمة:** 5.0.0

**إصدار المنتج الموروث:** 4.5.0

**تاريخ الإصدار:** 2026-08-08 UTC

**المشروع:** TeleDrive، مدير نقل الوسائط من Telegram إلى Google Drive

**التشغيل:** Google Colab فقط

**الواجهة:** Gradio داخل نفس عملية Python، محليًا افتراضيًا مع `share=False`

**اللغة الافتراضية:** العربية RTL، والإنجليزية LTR

**المستودع القانوني:** `https://github.com/body199-cmyk/drive-buddy-3579bf74.git`

**منفّذ GitHub الوحيد:** LM Arena Agent

**المهندس وكاتب الكود والمراجع:** Brain عبر ClickUp Docs

> هذا الملف الواحد يحفظ عقد TeleDrive v4.5.0 التقني ويضيف نظام التطوير الجديد. لا يُفهم v5.0 على أنه إعادة بناء أو تغيير تلقائي لسلوك المنتج. كل ما هو تقني في العقد القديم باقٍ ما لم يُذكر تغيير معتمد صراحة.

* * *

# 0\. الغرض والمرجع الوحيد

هذا الملف هو الدستور الوحيد الذي يجب إرساله إلى Brain أو LM Arena في جلسة جديدة. لا يعتمد المشروع على ملف بروتوكول منفصل أو ملحق خارجي لفهم طريقة العمل. أي بروتوكول استئناف أو قاعدة تشغيل واردة هنا جزء من الدستور نفسه.

يحدد هذا الدستور: هوية المنتج، المعمارية، الأمان، Telegram، Drive، UI، queue، notebook، CI، الأدوار، DOCs، الذاكرة الدائمة، Task IDs، GitHub، الاستئناف بعد إغلاق الجلسة، التحقق، rollback، والحالات الصادقة.

الحالة الفعلية لا تثبت بالكلام أو بصورة أو DOC أو رد Agent، بل بشجرة GitHub الحالية، والفرع، وHEAD، ومخرجات الأوامر، وColab الحقيقي عند الحاجة.

# 1\. عقد المنتج غير القابل للتخفيف

TeleDrive مدير نقل وسائط من حساب Telegram مستخدم إلى Google Drive داخل Google Colab. ليس Bot Telegram، وليس خدمة ويب مستقلة، وليس VPS دائمًا.

العقد الإلزامي:

*   Telethon user account فقط، لا Bot API.

*   Google Drive عبر مصادقة Colab الأصلية فقط.

*   Gradio وPython في نفس العملية.

*   العربية RTL افتراضيًا، والإنجليزية LTR.

*   SQLite وruntime على التخزين المحلي، وليس mounted Drive/FUSE.

*   نقل disk-first: `.part` محليًا، تحقق الحجم، ثم resumable upload والتحقق من Drive.

*   concurrency افتراضي 2، سقف صلب 4.

*   لا whole-channel أو whole-chat crawl افتراضيًا.

*   لا fake rows أو logs أو quotas أو IDs أو progress أو connected states.

*   لا تشغيل عام افتراضيًا، `share=False`.

*   لا `Colab-ready` قبل اختبار Colab حقيقي مضبوط.

*   لا `Complete` قبل المصادقة الحية، نقل ملف حقيقي، التحقق على Drive، shutdown، recovery، redacted logs، وhandoff.

# 2\. ترتيب السلطة

عند التعارض استخدم هذا الترتيب:

1. تعليمة المالك الحالية، إذا كانت لا تغيّر قاعدة دائمة.

2. هذا الدستور v5.0.

3. ADR معتمد داخل المستودع.

4. شجرة GitHub الحالية والفرع وHEAD.

5. مخرجات أوامر فعلية وCI.

6. مخرجات Colab الحقيقية المنقحة.

7. `docs/` والـhandoff والـphase reports.

8. DOC التنفيذ الحالي.

9. المحادثات والادعاءات والصور.

GitHub يحدد ما هو موجود فعليًا. الدستور يحدد ما يجب أن يكون صحيحًا. DOC يحدد مهمة مؤقتة فقط. المحادثة ليست ذاكرة دائمة. إذا قالت الوثائق Complete ولم يثبت GitHub ذلك، فالمهمة ليست Complete. تعليمة المالك التي تغيّر قاعدة دائمة تحتاج تحديث الدستور أو ADR ملتزمًا به.

# 3\. الأدوار

## Brain

Brain يراجع GitHub، يقارن بالدستور، يتحقق من آخر milestone، يصمم المعمارية، يكتب الخطة والكود الكامل داخل DOC، يحدد الملفات والأوامر والاختبارات، ويراجع نتيجة LM Arena بعد التنفيذ. Brain لا يدعي تعديل GitHub مباشرة.

## LM Arena Agent

LM Arena هو Executor الوحيد المتصل بـ GitHub. يقرأ الريبو والدستور وDOC، يفحص baseline، ينشئ branch، يطبق الكود، يشغل التحقق، يحدث الذاكرة، ينشئ commit، ينفذ push أو PR عند الإمكان، ويبلغ بالنتائج الفعلية. لا يعيد تصميم المعمارية أو يخفي فشلًا أو يدعي push بلا دليل.

## المالك

يحدد الأولويات، يعتمد تغييرات الدستور وADR الحساسة، يرسل رابط DOC إلى LM Arena، يوفر بيانات الاعتماد داخل Colab فقط، ويجري الاختبار الحي النهائي.

## قاعدة Lovable

Lovable خرج من المشروع نهائيًا. لا يُذكر كمنفذ ولا يُطلب منه شيء. أي إشارة قديمة إليه تُصحح إلى LM Arena Agent.

# 4\. دورة التطوير

1. Brain يقرأ هذا الدستور وملفات الذاكرة.

2. Brain يفحص GitHub الحالي والفرع وHEAD والشجرة.

3. Brain يتحقق من آخر TASK ID، ولا يصدق التقرير السابق تلقائيًا.

4. يصنف المهمة السابقة: `VERIFIED COMPLETE` أو `PARTIALLY COMPLETE` أو `FAILED` أو `BLOCKED`.

5. يصلح المهمة الجزئية أو الفاشلة قبل إضافة خصائص جديدة.

6. يختار milestone آمنًا أو مجموعة مترابطة يمكن اختبارها والتراجع عنها.

7. يكتب DOC يحتوي الكود الكامل والتعليمات.

8. المالك يرسل رابط DOC إلى LM Arena.

9. LM Arena يعيد فحص baseline وHEAD قبل التعديل.

10. ينفذ على branch جانبي، ثم يشغل الأوامر المطلوبة.

11. يحدث الذاكرة والhandoff بمخرجات حقيقية.

12. ينشئ commit وpush أو PR.

13. Brain يعيد فحص GitHub، الشجرة، SHA، الملفات، والأدلة.

14. لا تُغلق المهمة ولا تبدأ التالية إلا بعد تحقق مستقل.

# 5\. عقد DOC التنفيذي

كل DOC يجب أن يحتوي: TASK ID، العنوان، الهدف، سبب المهمة، الحالة الحالية، base SHA، النتيجة المطلوبة، الملفات المنشأة والمعدلة والممنوعة، الكود الكامل أو patch قابل للتطبيق، طريقة الدمج، القيود، الاعتماديات، working directory، أوامر التحقق، معايير القبول، Git/branch/commit/PR، rollback، وقالب الرد.

لا تكتب في الأجزاء الحرجة “أكمل حسب الحاجة”. إذا كان توقيع API غير معروف، اطلب من LM Arena فحص الملف أولًا ولا تخترع constructor أو اسمًا.

اجمع التغييرات المترابطة الآمنة في DOC واحد، وقسّمها إذا كان الجمع يصعّب الاختبار أو التشخيص أو rollback. الهدف أقل عدد من عمليات GitHub الآمنة، لا أقل عدد بأي ثمن.

# 6\. Task IDs والحالات

كل milestone له ID فريد مثل `M01-T01`. يظهر في DOC `docs/TODO.md` `docs/AI_HANDOFF.md` وcommit وPR والتقرير.

الحالات: `PLANNED`, `ACTIVE`, `VERIFIED COMPLETE`, `PARTIALLY COMPLETE`, `FAILED`, `BLOCKED`, `CANCELLED`.

الكود الموجود وحده لا يجعل المهمة VERIFIED COMPLETE.

# 7\. الذاكرة الدائمة

البيت القانوني الوحيد هو `docs/` في جذر GitHub. لا تنشئ `.ai/` بمعلومات مكررة؛ إن احتاجتها أداة، تكون مؤشرات فقط.

الملفات المطلوبة:

```plain
docs/
├── PROJECT_CONTEXT.md
├── ARCHITECTURE.md
├── CONSTITUTION.md
├── AI_RULES.md
├── AI_HANDOFF.md
├── BOOTSTRAP_PROMPT.md
├── CHANGELOG.md
├── CHANGELOG_ARCHIVE.md
├── TODO.md
├── KNOWN_ISSUES.md
├── RUNBOOK.md
├── TROUBLESHOOTING.md
├── AUDIT.md
├── MIGRATION.md
├── REPOSITORY_REGISTRY.md
├── ACTIVE_TASK.md
├── PHASE_REPORTS/
└── decisions/
    ├── ADR_TEMPLATE.md
    ├── ARCHIVE.md
    └── ADR-*.md
```

`AI_HANDOFF.md` يحتوي UTC، branch، HEAD، TASK ID، الحالة، الأدلة، آخر SHA أخضر، rollback، والخطوة التالية. `ACTIVE_TASK.md` قفل معلوماتي لمهمة واحدة، وليس mutex runtime. إذا اختلف HEAD عن handoff، فالهاندوف متقادم ويجب إعادة التدقيق. `PHASE_REPORTS` تاريخ أدلة ولا يمحو فشلًا سابقًا.

# 8\. جلسة جديدة أو حساب جديد

اقرأ بالترتيب: هذا الدستور، `BOOTSTRAP_PROMPT.md`، `AI_RULES.md`، `PROJECT_CONTEXT.md`، `AI_HANDOFF.md`، `KNOWN_ISSUES.md`، `TODO.md`، `ACTIVE_TASK.md`، `REPOSITORY_REGISTRY.md`، `MIGRATION.md`، ثم ADRs ذات الصلة.

اطبع branch وHEAD والشجرة. قارن SHA المسجل بالـHEAD. لا يحتاج الحساب الجديد إلى محادثة قديمة.

# 9\. بروتوكول استئناف جلسة LM Arena بعد الإغلاق

## 9.1 معنى الإغلاق

إغلاق جلسة Arena بعد دمج PR أو فشل GitHub لا يعني أن المهمة اكتملت أو أن الكود سليم. يعني أن الجلسة البعيدة انتهت، وأن push أو PR جديد يحتاج **New Coding Session**. لا تحاول استكمال عملية GitHub داخل الجلسة المغلقة. الدمج يثبت دخول commit إلى الفرع فقط، ولا يثبت الوظيفة أو Colab readiness.

## 9.2 ما يرسله المالك

ابدأ New Coding Session وأرسل: رابط هذا الدستور الواحد، رابط المستودع، رقم ورابط PR السابق، سبب الاستئناف `merged/failed/blocked/unknown`، وآخر تقرير بدون أسرار أو توكنات أو session strings. لا ترسل خطة قديمة قبل فحص main وHEAD.

## 9.3 رسالة الاستئناف الإلزامية إلى LM Arena

```plain
هذه جلسة استئناف لمشروع TeleDrive وليست بدءًا من الصفر.

اقرأ دستور TeleDrive v5.0 كاملًا، بما فيه القسم 9 الخاص باستئناف جلسات LM Arena.

المستودع القانوني:
https://github.com/body199-cmyk/drive-buddy-3579bf74.git

Lovable غير موجود ولم يعد منفذًا.

LM Arena Agent هو Executor الوحيد المتصل بـ GitHub.

Brain هو المهندس والمراجع وكاتب الخطة والكود داخل ClickUp Docs.

قبل أي تعديل أو push:

- نفّذ git status --short
- نفّذ git branch --show-current
- نفّذ git rev-parse HEAD
- افحص آخر commit ووالديه إذا كان merge commit
- افحص حالة PR السابق: merged أو open أو closed-unmerged أو unknown
- اعرض الملفات التي دخلت في PR السابق
- قارن HEAD مع docs/AI_HANDOFF.md وdocs/ACTIVE_TASK.md وdocs/TODO.md
- تحقق أن التغييرات المبلغ عنها موجودة فعليًا في baseline

إذا اختلف HEAD أو الشجرة عن التقرير السابق، توقف وسجّل الفرق قبل تطبيق أي كود.

إذا كان PR مدموجًا، لا تعيد تطبيق تعديلاته؛ افحص commit الدمج واجعله baseline جديدًا.

إذا كان PR مغلقًا بلا دمج، لا تعتبر تعديلاته موجودة في main.

إذا فشل push أو PR، لا تدّعِ النجاح ولا تكرر العملية عشوائيًا.

بعد مطابقة baseline فقط:

- أنشئ branch جديدًا مرتبطًا بـTASK ID
- نفذ DOC الحالي فقط
- لا تنشئ تطبيقًا ثانيًا
- لا تستخدم أسرارًا أو توكنات أو session strings
- شغّل الاختبارات المطلوبة بمخرجاتها الحقيقية
- حدث الذاكرة بنتائج فعلية
- أنشئ commit وسجل SHA
- نفذ push أو PR فقط إذا كان متاحًا وسجل النتيجة الحقيقية

لا تقل Complete أو Colab-ready بلا أدلة الدستور.
```

## 9.4 تصنيف الاستئناف

يجب إعلان واحد: `RESUME_VERIFIED`، `RESUME_PARTIAL`، `RESUME_FAILED`، `RESUME_BLOCKED`، أو `RESUME_UNKNOWN`.

*   Verified: الدمج والملفات والأدلة مطابقة.

*   Partial: بعض المتطلبات موجودة وبعضها ناقص.

*   Failed: التعديل مكسور أو الاختبارات فاشلة.

*   Blocked: اتصال أو صلاحية أو اعتماد يمنع التنفيذ.

*   Unknown: الأدلة غير كافية، والتوقف واجب.

## 9.5 اختيار baseline

PR مدموج: baseline هو commit الدمج الفعلي على main بعد فحصه. PR غير مدموج: baseline هو أحدث main، لا فرع PR المغلق. تغييرات محلية غير مرفوعة لا يُكتب فوقها. إذا تغير main بعد إنشاء DOC، أعد تقييم الخطة.

أنشئ قبل التنفيذ جدولًا: `Requirement | Expected file | Present in baseline? | Verified? | Action`. الموجود والمتحقق لا يُعاد. الموجود غير المتحقق يُختبر. الناقص يُنفذ فقط إن كان داخل نطاق DOC.

## 9.6 تصنيف فشل GitHub

`LOCAL_CHANGE_ONLY`, `COMMIT_ONLY`, `PUSHED_NO_PR`, `PR_OPEN`, `PR_MERGED`, `PR_CLOSED_UNMERGED`, `UNKNOWN_REMOTE_STATE`.

لا تكرر العملية قبل معرفة التصنيف والسبب. إغلاق Arena يعني جلسة جديدة، لا retry داخل الجلسة المغلقة.

## 9.7 فحص الاستئناف

من الجذر:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git log -5 --oneline --decorate
find docs -maxdepth 2 -type f | sort
```

للمهام Python من `python-package`:

```bash
python -m compileall teledrive
python -m pytest -q tests
python teledrive_launcher.py --check
python -m teledrive.notebook_cells --check
cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb
```

ومن الجذر:

```bash
bun run lint
bun run build
```

compileall وlauncher check ليسا بديلًا عن pytest، والـfake tests ليست دليل Telegram أو Drive أو نقل حقيقي.

## 9.8 قبل إغلاق الجلسة الجديدة

حدّث `AI_HANDOFF.md` `ACTIVE_TASK.md` `TODO.md` وphase report عند الحاجة، وسجل UTC وHEAD وTASK ID والحالة وآخر SHA أخضر وrollback وcommit/push/PR منفصلة. لا تمسح دليل الفشل.

## 9.9 تقرير الاستئناف الإلزامي

```plain
RESUME REPORT

Session type: New Coding Session after Arena closure

Resume status: RESUME_VERIFIED / RESUME_PARTIAL / RESUME_FAILED / RESUME_BLOCKED / RESUME_UNKNOWN

Previous PR:

Previous PR status:

Previous PR URL:

Repository:

Branch inspected:

HEAD before work:

HEAD after work:

Baseline decision:

Baseline reason:

Previous task ID:

Previous task verified status:

Files changed by previous PR:

Missing or conflicting files:

Implementation performed in this session:

FILES CREATED:

FILES MODIFIED:

FILES DELETED:

COMMANDS AND COMPLETE OUTPUT:

TESTS NOT RUN OR NOT PROVEN:

GITHUB STATUS:

Commit: SUCCESS / FAILED / NOT ATTEMPTED

Push: SUCCESS / FAILED / NOT ATTEMPTED

Pull Request: CREATED / NOT CREATED / FAILED / NOT ATTEMPTED

Branch:

Commit SHA:

PR URL:

MEMORY UPDATED:

ROLLBACK POINT:

HONEST PROJECT STATUS:

NEXT SMALLEST STEP:
```

Brain يعيد فحص GitHub بعد التقرير. إذا لم يطابق الواقع، الحالة `RESUME_PARTIAL` أو `RESUME_FAILED` ويُكتب DOC إصلاحي.

# 10\. GitHub والفروع والrollback

لا force-push أو rebase أو amend على تاريخ منشور. اعمل branch لكل milestone غير تافه، وcommit يبدأ بـTASK ID. لا تلمس main مباشرة إلا بتفويض صريح وبعد التحقق. لا تدّع push أو PR بلا SHA أو رابط.

عند فشل GitHub، سجل الحالة المحلية، SHA، branch، رسالة الخطأ، وما إذا كان commit أو push أو PR قد نجح. rollback يكون بإغلاق PR أو revert commit أو العودة إلى آخر SHA أخضر، دون إعادة كتابة التاريخ.

تقرير GitHub:

```plain
Commit: SUCCESS / FAILED
Push: SUCCESS / FAILED / NOT ATTEMPTED
Pull Request: CREATED / NOT CREATED / FAILED
Branch:
Base SHA:
Result SHA:
PR URL:
Operation error:
Recovery recommendation:
```

# 11\. قواعد الأمان المطلقة

ممنوع: تطبيق ثانٍ أو `app_v2.py`، Python داخل TypeScript strings، fake data، زر بلا handler/service/test، lambda في layout، SQLite على FUSE، تخزين أو طباعة الأسرار، Bot API أو `file_unique_id` للدedupe، concurrency فوق 4، streaming v1 بدل disk-first، حذف Drive عند cancel/stop، blind cleanup، auto-resume بعد restart، dependency upgrade بلا دليل، نقل docs/modules بلا search، أو اعتبار الصور/static scans/fake tests تكاملًا حقيقيًا.

لا تستخدم أي توكن أو سر يظهر في المحادثة. لا تضع credentials أو phone أو codes أو password أو session string أو OAuth token في DOC أو GitHub أو logs أو ZIP أو handoff.

# 12\. المعمارية التقنية الموروثة من v4.5

```plain
Colab notebook
 -> restore tested package into local /content
 -> bootstrap local dirs, logging, SQLite WAL
 -> one ApplicationContext
 -> one AsyncRuntime and event loop
 -> one Telethon client and one Drive service
 -> Gradio same process
 -> UIBinder.wire(control, action_id)
 -> named handler
 -> application service
 -> infrastructure adapter
 -> SQLite transaction/event
 -> localized UI update
 -> safe checkpoint
```

الطبقات: Launcher، UI، Application services، Domain، Persistence، Infrastructure. يوجد context واحد وloop واحد وclient واحد وDrive service واحد وSQLite connection واحد. `ctx.resolve()` يفشل بوضوح عند المسار المجهول أو الخدمة None أو method غير القابلة للنداء. UI لا يحتوي SQL أو رفعًا مباشرًا. shutdown يوقف UI ويلغي المهام ويحفظ checkpoints/logs ويغلق SQLite.

# 13\. Telegram وDrive

Telegram الحالات: `DISCONNECTED`, `READY_FOR_PHONE`, `SENDING_CODE`, `CODE_REQUESTED`, `VERIFYING_CODE`, `PASSWORD_REQUIRED`, `VERIFYING_PASSWORD`, `AUTHORIZED`, `REAUTH_REQUIRED`, `ERROR`. API ID/hash في الذاكرة، phone_code_hash محفوظ بدقة، 2FA يعيد استخدام العميل، password تمسح فورًا، resend cooldown، logout/account switch صريحان، ونجاح حقيقي لا يثبت إلا في Colab.

Drive يستخدم فقط:

```python
from google.colab import auth as colab_auth
import google.auth
from googleapiclient.discovery import build

colab_auth.authenticate_user(clear_output=False)
creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/drive"])
service = build("drive", "v3", credentials=creds, cache_discovery=False)
about = service.about().get(fields="user(displayName,emailAddress),storageQuota(limit,usage)").execute()
```

لا OAuth JSON أو InstalledAppFlow أو pasted code أو token file. Connected مستحيل قبل about.get. احفظ folder ID، نفذ folder operations، quota، تحذير 90% ورفض المساحة غير الكافية.

# 14\. UI وAction Registry

كل action ظاهر يعلن مرة واحدة بـID وhandler وservice path وlabel وsection وimplemented وtested وproof_test عند الحاجة. Action Registry هو مصدر عدد الإجراءات، والأرقام في النص snapshots فقط. `UIBinder.wire` `assert_complete` يمنعان dead controls. كل handler مسمى ومزخرف. ممنوع lambda وdirect click/change/submit في layout. كل action يحتاج UI→service→persistence/event→live UI→redacted log.

UI يجب أن يكون Arabic RTL، English LTR، graphite dark/light وlime، status chips حقيقية، navigation rail، Transfers رئيسية، Dashboard/Analyze/Connections/Logs/Settings/Colab export، advanced settings collapsed، concurrency slider 1–4 default 2، بلا fake data.

# 15\. Analyze وQueue وTransfer

النطاقات بالضبط `message`, `group`, وbounded `range`. لا whole chat/channel. Analyze لا ي enqueue تلقائيًا. Dedupe يستخدم MTProto identity وmetadata موثق.

الترتيب:

```plain
validate connections
 -> bounded scan
 -> MediaItem
 -> deterministic duplicate check
 -> Drive quota
 -> local disk reserve
 -> enqueue
 -> .part download
 -> local size verification
 -> resumable Drive upload
 -> Drive ID/properties/parent/size verification
 -> safe checkpoint
 -> Uploaded
 -> targeted cleanup
```

QueueManager وحده يغير الحالات. pause/resume/retry/stop/cancel/restart/crash recovery/dedupe/mismatch/quarantine/cleanup يجب اختبارها. لا delete لملف Drive عند cancel/stop، ولا auto-resume بعد restart.

# 16\. Notebook وCI

مولد واحد ينتج notebook داخلي وpublic ويجب أن يكونا byte-identical. سبع خلايا: restore/install، bootstrap/WAL، hidden Telegram/native Drive auth، inject/restore/launch، redacted handoff، pytest الحقيقي، checkpoint/cleanup/shutdown. لا timestamps أو IDs عشوائية في generator.

الأوامر من `python-package` ثم الجذر:

```bash
cd python-package
python -m compileall teledrive
python -m pytest -q tests
python teledrive_launcher.py --check
python -m teledrive.notebook_cells --check
cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb
python -m teledrive.package_service --build --output teledrive_v4.5.zip
cd ..
bun run lint
bun run build
```

CI يجب أن يشغل compileall، pytest، launcher check، notebook check، cmp، package build، frontend lint وbuild، بلا continue-on-error. كل أمر يذكر working directory. Python وBun pinned في CI إن كان ذلك مثبتًا في المشروع، ولا تغير dependency pins بلا دليل.

# 17\. الحالات الصادقة

*   `Implemented`: المصدر موجود.

*   `Fake-tested`: fake/contract tests نجحت.

*   `Code-complete candidate`: بوابات الكود والnotebook/CI ناجحة لكن integrations الحية غير مثبتة.

*   `Colab-ready`: اختبار Colab حقيقي مضبوط نجح.

*   `Complete`: Colab-ready مع نقل حقيقي موثق وshutdown/recovery/logs/handoff.

لا تستخدم Complete أو Colab-ready بسبب screenshot أو mock أو static scan أو زر أو إعداد CI أو رد Agent أو DOC.

# 18\. التقرير العام من LM Arena

```plain
TASK/PHASE:
TITLE:
STATUS: VERIFIED COMPLETE / PARTIALLY COMPLETE / FAILED / BLOCKED
BASE SHA:
ACTUAL START SHA:
RESULT SHA:
BRANCH:
PR URL:
FILES CREATED:
FILES MODIFIED:
FILES DELETED:
CHANGES MADE:
COMMANDS AND REAL OUTPUT:
TESTS NOT RUN OR NOT PROVEN:
CONSTITUTION CONFLICTS:
UNRELATED CHANGES:
SECURITY CHECK:
GITHUB STATUS:
Commit: SUCCESS / FAILED
Push: SUCCESS / FAILED / NOT ATTEMPTED
Pull Request: CREATED / NOT CREATED / FAILED / NOT ATTEMPTED
ROLLBACK POINT:
HONEST PROJECT STATUS:
NEXT SMALLEST STEP:
```

لا يقبل Brain “تم” بلا SHA ومخرجات، ولا “كل الاختبارات نجحت” بلا output، ولا “تم الرفع” بلا دليل.

# 19\. تعديل الدستور

لا تعدل الدستور داخل milestone عادي. أي تغيير حوكمي أو تغيير عقد يحتاج مراجعة تضارب وتحديث version أو ADR. لا تحذف معلومات قديمة إلا بسبب خطأ أو تعارض مسجل. إصدار المنتج يبقى v4.5.0، وإصدار الحوكمة v5.0.0، إلى أن يعتمد المالك إصدارًا جديدًا.

# 20\. قاعدة التوقف

توقف Brain أو LM Arena عند اختلاف canonical repo، اختلاف HEAD بلا تفسير، تعارض دستور/مصدر غير محسوم، ملف مفقود، اختبار فاشل، اعتماد أو صلاحية غير متاحة، فشل GitHub، سر في المدخلات أو الملفات، محاولة تطبيق ثانٍ، أو ادعاء غير قابل للإثبات. التوقف مقبول؛ التظاهر بالنجاح مرفوض.

# 21\. أمر بدء أي محادثة جديدة

```plain
أنت Brain/Claude Opus لمشروع TeleDrive v5.0.
هذا الملف هو الدستور الوحيد؛ لا تبحث عن بروتوكول استئناف منفصل.
المستودع القانوني هو drive-buddy-3579bf74.
Lovable خرج نهائيًا. LM Arena Agent هو Executor الوحيد المتصل بـGitHub.
أنت تراجع GitHub، تتحقق من آخر TASK، تكتب الخطة والكود داخل DOC،
وتعيد فحص النتيجة بعد كل تنفيذ.
ابدأ بفحص branch وHEAD والشجرة وdocs وحالة آخر PR.
إذا كانت الجلسة السابقة مغلقة، طبّق القسم 9 كاملًا قبل أي تعديل.
لا تثق بالمحادثة أو DOC أو رد Agent دون فحص GitHub.
لا تقل Complete أو Colab-ready دون الأدلة.
```

# 22\. القرار النهائي

لا نبدأ من الصفر. نحافظ على TeleDrive v4.5 ونصلحه تدريجيًا. Brain يراجع ويصمم ويكتب الكود في DOC. LM Arena يطبق ويتحقق ويرفع. GitHub يثبت حالة الكود. `docs/` تحفظ الذاكرة. كل milestone له TASK ID وbase/result SHA. كل جلسة مغلقة تستأنف بجلسة LM Arena جديدة وفحص baseline. أي تعارض يوقف التنفيذ ولا يدمج صامتًا.

**إصدار المنتج:** 4.5.0

**إصدار الحوكمة:** 5.0.0

**الحالة الافتراضية:** Code-complete candidate، وليست Colab-ready أو Complete.
