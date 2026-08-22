# ACTIVE_TASK

| الحقل | القيمة |
|---|---|
| TASK ID | `M36-T01` |
| العنوان | مواءمة إصدار المنتج في workflow النشر + أدلة النشر بهوية v5.0.0 |
| الحالة | **MERGED + CI-PASSED + package-published؛ Colab live verification pending** |
| PR | [#77](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/77) — MERGED |
| Merge SHA | `cb6901f4bf` |
| Publish | run #29 (id 32575076208) على main `cb6901f4bf` — SUCCESS |

## النطاق المنفذ

| المسار | السلوك |
|---|---|
| `.github/workflows/release-current.yml` | `PRODUCT_VERSION` 4.5.0 → 5.0.0 (حقل معلوماتي في الـ manifest المنشور فقط؛ بوابة Cell-1 تخزنه ولا تقارن به). اسم الأرتيفكت المثبّت والـ tag بقي كما هما عمدًا. |

## أدلة النشر المستقلة

Release `pkg-2026.08.09-m15t07` أُعيد نشره من الشجرة الحالية: `teledrive_v4.5.zip` 560,483 بايت · SHA-256 `a0d7cc4d…b66f1` · `product_version=5.0.0`. تحقق مستقل خارج الـ workflow بتنزيل الأصول العامة ومطابقة commit/الحجم/SHA-256 — ناجحة.

## البوابات المنفذة

بوابات الدستور داخل run #29: compileall + pytest كامل + launcher + notebook check + cmp — ناجحة. CI أخضر على PR#77 قبل الدمج.

## الحدود الصادقة

لم يُنفذ اختبار Colab حي جديد؛ لا تزال الحالة غير `Colab-ready` وغير `Complete`.

## الخطوة التالية

الاختبار الحي بيد المالك: شغّل Cell 1 في Colab ثم Restart Runtime عند الطلب، وبعدها Cells 2–4. بوابة التحديث ستستقبل الحزمة الجديدة (`product_version=5.0.0`) بنفس اسم الأرتيفكت المثبّت.
