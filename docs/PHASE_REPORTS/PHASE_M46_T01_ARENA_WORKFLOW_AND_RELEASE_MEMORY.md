# PHASE M46-T01 — تثبيت طريقة شغل Arena وتحديث ذاكرة النشر

**Date (UTC):** 2026-10-19
**Task:** `M46-T01`
**Base:** `f272e87823fd1249be6bd115e0892a3edb82daba` (`main` بعد M45-T02)
**Type:** Docs/governance only — no code, notebook, workflow, dependency, Vault, or Drive changes.

## 1. ما تم

1. إنشاء `docs/ARENA_WORKFLOW.md`: الطريقة المثبتة (فرع `arena/...` ← تعديل ← بوابات ← Commit ← Push ← PR ← دمج بأمر صريح من المالك ← فرع جديد بعد `pr_merged`)، مع المحظورات وخطوات المالك وحدها وقاعدة إغلاق الجلسة.
2. تحديث ذاكرة المشروع: `ACTIVE_TASK.md` + `AI_HANDOFF.md` + `TODO.md` + `CHANGELOG.md` + `KNOWN_ISSUES.md` (هذا التقرير).

## 2. التحقق الحي من حالة الـ Release (سبب قفل #79)

فحص مباشر من هذه الجلسة بتاريخ 2026-10-19:

| الفحص | النتيجة |
|---|---|
| `gh release view pkg-2026.08.09-m15t07` | الـ Release موجود؛ `target=f272e87823fd1249be6bd115e0892a3edb82daba` (M45-T02) |
| أصول الـ Release | `teledrive_v4.5.zip` بحجم `596345` بايت (محدّث 2026-10-19T17:09:41Z) + `teledrive_manifest.json` بحجم `378` بايت (17:09:42Z) — الأصلان معًا، لا أصل وحيد |
| حجم الـ ZIP في الشجرة | `python-package/teledrive_v4.5.zip` عند `f272e87` بنفس الحجم `596345` بايت |
| تشغيل النشر | `Publish current TeleDrive package` run `39278373927` — `workflow_dispatch` على `d991cf4783545ee838d3c2eeaf3b98fc0c22cf6f` (دمج M45-T01 / PR #100) — **SUCCESS** |
| CI على `main` بعد M45-T02 | run `39291747719` — **SUCCESS** |

**الاستنتاج:** حادثة حذف الـ Release (KNOWN_ISSUES #79) انتهت — أُعيد إنشاء الـ Release بالأصلين من `main`، ثم حُدّث لاحقًا مع M45-T02. تُقفل #79 في M46-T01.

## 3. آخر حالة TeleDrive الحقيقية عند كتابة هذا التقرير

- **M45-T01** (PR #100، دمج `d991cf4`): MERGED + CI-PASSED + **RELEASE-PUBLISHED** (run أعلاه). دليل حي جزئي: تشغيل Colab للمالك نقل 3 ملفات (1.40 GB + 671 MB + 1.34 GB = 3.41 GB) بلا `Request was unsuccessful` ولا `LimitInvalidError` — موثق في تقرير M45-T02 كمُشغّل لها.
- **M45-T02** (commit مباشر من المالك على `main`: `f272e87`، CI run `39291747719` SUCCESS): فحص تكرار بين قطع الرفع 8 MiB + تعافي SQLite من `readonly database`. أصول الـ Release الحالية بحجم ZIP مطابق لشجرتها.
- **ما لم يثبت بعد:** قياس benchmark رسمي لملف ≥100 MB مع سطر `mbps=` و`telethon crypto backend=cryptg`، والتحقق الحي من إصلاحي M45-T02 على Colab (مكرر يُكتشف قبل التنزيل + عدم تكرار خطأ readonly). لا ادعاء نسبة تسريع قبل ذلك.

## 4. TESTS NOT RUN OR NOT PROVEN

- تغييرات وثائقية فقط — لم تُشغَّل بوابات كود في هذه الجلسة.
- لم يُنزَّل أصل الـ manifest من هذه البيئة للتحقق من محتواه (مضيف أصول الـ releases أعاد `EOF` عند المحاولة)؛ الاعتماد على `gh release view` + نجاح تشغيل النشر صاحب التحقق العلني الداخلي + تطابق حجم الـ ZIP مع الشجرة.
- لا اختبار Colab/Telegram/Drive حي في هذه الجلسة.

## 5. التراجع

Revert commit M46-T01 — يعود الورق لحالته قبل هذا التقرير؛ لا أثر على كود أو Release أو Vault.
