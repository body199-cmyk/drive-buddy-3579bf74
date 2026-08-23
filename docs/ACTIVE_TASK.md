# ACTIVE_TASK

| الحقل | القيمة |
|---|---|
| TASK ID | `M37-T01` |
| العنوان | تقوية نشر الحزمة الحالية — إزالة الحذف الأعمى للـRelease/tag (نتائج تدقيق خارجي Sol + تحقق تنفيذي) |
| الحالة | **CODE COMMITTED LOCALLY — بوابات خضراء؛ ينتظر push + PR + CI** |
| Branch | `fix/m37-t01-audit-release-hardening` |
| Base | main `f820529` |

## النطاق المنفذ

| المسار | السلوك |
|---|---|
| `.github/workflows/release-current.yml` | خطوة النشر أصبحت idempotent fail-closed بدون أي حذف للـrelease أو الـtag: غياب → إنشاء ذري بأصلين؛ وجود بمطابقة → تحديث metadata فقط؛ نقص/اختلاف أصول → فشل صريح والقرار للمالك (§11/§17 — KNOWN_ISSUES #70) |
| `.github/workflows/release.yml` | تعليق توثيقي: قيم v4.5 فيه وصف صادق للأرشيف التاريخي المثبّت بالبايت، ولا تُرفع لـ5.0.0 ما دامت بوابة البايتات تثبّتها (§17) |

## ملاحظات التدقيق الخارجي المرفوضة (بالأدلة)

T-1 (رفع product_version في release.yml إلى 5.0.0) وD-1 (تغيير عنوان النشر المثبّت): تنفيذهما كان يجعل الـmanifest يصف أرشيف v4.5 مثبّتًا بالبايت بقيمة 5.0.0 — كذب توثيقي يخالف §17. التفصيل في `docs/PHASE_REPORTS/PHASE_M37_T01.md`.

## البوابات المنفذة

compileall OK · pytest كامل **746 passed** · launcher `51/51` · notebook check + cmp متطابقة.

## الحدود الصادقة

لم يُشغَّل الـworkflow على GitHub ضمن هذه المهمة (تشغيله قرار نشر بيد المالك). لا اختبار Colab حي جديد؛ لا `Colab-ready` ولا `Complete`.
