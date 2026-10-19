# المهمة النشطة

| الحقل | القيمة |
|---|---|
| TASK ID | `M46-T01` |
| العنوان | تثبيت طريقة شغل Arena للتعديل والدمج (`ARENA_WORKFLOW.md`) + تحديث ذاكرة النشر وقفل حادثة الـ Release #79 |
| الأساس | `f272e87823fd1249be6bd115e0892a3edb82daba` — main بعد M45-T02 |
| الفرع | `arena/a295b500-drive-buddy-3579bf74` |
| الحالة | **DOCS-ONLY — في PR بانتظار دمج المالك** |
| التقرير | `docs/PHASE_REPORTS/PHASE_M46_T01_ARENA_WORKFLOW_AND_RELEASE_MEMORY.md` |

## النطاق

- `docs/ARENA_WORKFLOW.md` جديد: فرع `arena/...` ← تعديل ← بوابات ← Commit ← Push ← PR ← دمج بأمر صريح من المالك ← فرع جديد بعد `pr_merged`. دليل الاعتماد: PR #101 و #102.
- قفل `KNOWN_ISSUES #79`: الـ Release `pkg-2026.08.09-m15t07` موجود بالأصلين؛ تشغيل النشر `39278373927` SUCCESS على دمج M45-T01؛ أصول لاحقة عند `f272e87`/M45-T02 بحجم ZIP `596345` مطابق للشجرة.
- تحديث حالة M45-T01 في `TODO.md` إلى RELEASE-PUBLISHED + تسجيل M45-T02 (commit مالك مباشر `f272e87`، CI `39291747719` SUCCESS).

## ما لم يثبت / الخطوة التالية بعد هذه المهمة

- قياس Colab رسمي لملف ≥100 MB مع `mbps=` و `telethon crypto backend=cryptg`، والتحقق الحي من إصلاحي M45-T02 (اكتشاف المكرر قبل التنزيل + عدم تكرار `readonly database`).
- لا تغيير كود أو notebook أو workflow أو اعتماديات في M46-T01.

## التراجع

Revert commit M46-T01 — وثائق فقط؛ لا أثر على كود أو Release أو Vault.
