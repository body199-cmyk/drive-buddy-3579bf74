# ARENA_WORKFLOW — طريقة الشغل المثبَّتة للتعديل والدمج (TeleDrive)

> **TASK ID:** `M46-T01` · **اعتمدها المالك:** 2026-10-19
> **المرجع الأعلى:** `docs/CONSTITUTION.md` + `docs/AI_RULES.md` — هذا الملف يشرح آلية التنفيذ فقط ولا يضعف أي بند دستوري.
> **الدليل العملي:** PR [#101](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/101) و PR [#102](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/102) — إنشاء ملف → Commit → Push → PR → دمج بأمر المالك، وكلاهما `MERGED` على `main`.

## 1) الطريقة المثبَّتة (خطوات إلزامية بالترتيب)

| # | الخطوة | من ينفذها |
|---|---|---|
| 1 | بداية الجلسة: قراءة `BOOTSTRAP_PROMPT → AI_RULES → AI_HANDOFF → TODO → CONSTITUTION` والتحقق من `git log -1` + `git status` + أحدث حالة على GitHub (PRs / Releases / Actions) | Arena Agent |
| 2 | العمل دائمًا على فرع جلسة `arena/<session>-drive-buddy-3579bf74` — **ممنوع لمس `main` مباشرة من البوت** | Arena Agent |
| 3 | مهمة واحدة بـ TASK ID لكل جلسة، أصغر تغيير آمن | Arena Agent |
| 4 | تشغيل البوابات المناسبة محليًا وذكر ما لم يُشغَّل صراحة (`TESTS NOT RUN`) | Arena Agent |
| 5 | `Commit` برسالة واضحة تبدأ بالـ TASK ID، ثم `Push` إلى فرع الجلسة فقط | Arena Agent |
| 6 | فتح Pull Request إلى `main` بوصف: التغيير + الأدلة + ما لم يثبت | Arena Agent |
| 7 | مراجعة المالك — **لا دمج قبل أمر صريح من المالك** مثل «ادمجه» | Owner |
| 8 | الدمج `gh pr merge <N> --merge` بواسطة البوت بعد أمر المالك، ثم التحقق أن حالة الـ PR أصبحت `MERGED` وأن الملفات وصلت `main` | Arena Agent |
| 9 | بعد الدمج يصبح فرع الجلسة `pr_merged` ومنتهيًا — أي عمل جديد يبدأ بفرع جديد نظيف من أحدث `main` (زر **Continue** في واجهة Arena بيد المالك/الجلسة) | Owner + Arena Agent |

## 2) محظورات دائمة

- لا `force-push` ولا `rebase` ولا `amend` لأي commit منشور (§10).
- لا تعديل على `.github/workflows/*` من البوت — تطبيق GitHub الخاص بـ Arena بلا صلاحية `workflows` (محاولة `workflow_dispatch` أعادت HTTP 403 في حادثة 2026-10-19). المالك ينفذ تشغيل الـ workflows يدويًا عند الحاجة.
- لا أسرار في أي ملف أو سجل: API ID/hash، session، OTP، توكنات — الاعتماد يدخل داخل Colab فقط بيد المالك.
- لا ادعاء نجاح بلا دليل: كل «تم/ناجح/منشور» يحتاج SHA + معرّف تشغيل Actions أو رابط PR/Release قابل للفحص.
- نجاح محلي ليس نجاح CI — لا تُقال «البوابات خضراء» إلا بتشغيل GitHub Actions ناجح.

## 3) خطوات بيد المالك وحده (قيود منصة، لا يعجز عنها البوت تقنيًا في الكود)

| الخطوة | السبب |
|---|---|
| Actions → «Publish current TeleDrive package» → Run workflow على `main` | `workflow_dispatch` من جلسة البوت محظور (403) |
| اختبار Colab الحي (Cells 1–4، Telegram/Drive، نقل ملف حقيقي) | يتطلب حسابات المالك الحية واعتماده |
| زر **Continue** بعد دمج PR | يفتح فرع جلسة جديدًا من أحدث `main` |
| عدم الضغط على Suspend / Uninstall لتطبيق «Arena AI Coding Agent» | يقطع اتصال البوت بـ GitHub نهائيًا |

## 4) إغلاق كل جلسة (ذاكرة المشروع)

تحديث إلزامي قبل اعتبار الجلسة منتهية: `docs/AI_HANDOFF.md` + `docs/ACTIVE_TASK.md` + `docs/TODO.md` + `docs/CHANGELOG.md` + `docs/KNOWN_ISSUES.md` + تقرير مرحلة في `docs/PHASE_REPORTS/` — بنفس الـ PR الخاص بالمهمة.

## 5) التراجع

أي تراجع يكون بـ revert commit / PR جديد — لا إعادة كتابة لتاريخ منشور أبدًا.

---
**سجل الاعتماد:** أُثبتت هذه الطريقة عمليًا في 2026-10-19 باختبارين متتاليين طلبهما المالك للتأكد من الاتصال (PR #101 و PR #102، ملفا `ARENA_GITHUB_TEST.md` و `ARENA_GITHUB_TEST_2.md` على `main`)، ثم اعتمدها المالك صراحة في جلسة M46-T01.
