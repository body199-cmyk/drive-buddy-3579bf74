# PHASE_M27_T02 — إصلاح تسليم التحديث التلقائي للوحة React

## بطاقة التنفيذ

| الحقل | القيمة |
|---|---|
| التاريخ | 2026-08-19 |
| الخط الأساسي | `main` عند `50cb7657f07c4e2432e875c0ad36e876e4aac652` |
| فرع العمل | `arena/react-auto-refresh-bundle` |
| البلاغ | أثناء النقل لا تتجدد صفوف الطابور أو شريط التقدم حتى يضغط المستخدم «تحديث» يدويًا. |
| الحالة | تغييرات محلية متحققة؛ لا commit أو PR أو merge وقت كتابة التقرير. |

## السبب الجذري المثبت

| طبقة | الدليل | النتيجة |
|---|---|---|
| مصدر React | `TeleDriveSandbox.tsx` يحوي `setInterval` كل `2000ms` ويبعث `queue.refresh` عند `hasActiveTransfer()` | منطق النبض في المصدر صحيح. |
| backend | زر «تحديث» اليدوي يعرض تقدمًا صحيحًا، وsnapshot يقرأ صفوف SQLite الحية | مسار Python لا يحتاج إصلاحًا لهذه المشكلة. |
| تحميل Colab | `react_panel.py` يفك ويحقن `react_panel_assets/panel.bundle.gz` ولا يشغل `src/` | الأصل المشحون هو السلطة وقت التشغيل. |
| البندل القديم | فحص gzip المباشر أظهر `queue.refresh` مرتين و**صفر** `setInterval` | البندل متقادم ويخلو من النبض؛ يفسر السلوك المبلغ عنه بالكامل. |

## التغيير

| الملف | الإجراء |
|---|---|
| `scripts/build-react-panel.mjs` | مولّد ثابت من `gradioEntry.tsx` باستخدام Vite/Oxc إلى IIFE باسم `TeleDriveGradioPanel` ثم gzip بـ`mtime=0`. |
| `panel.bundle.gz` و`panel.css.gz` | أعيد بناؤهما من المصدر؛ البندل الجديد يتضمن `setInterval` و`queue.refresh` وglobal panel المطلوب. |
| `tests/teledrive-sandbox.contract.test.mjs` | اختبار 25 يفك البندل المشحون ويمنع غياب IIFE أو heartbeat مستقبلًا. |

## نتائج التحقق الفعلية

| البوابة | النتيجة |
|---|---|
| React contract | `25 passed` عبر `node --experimental-strip-types --test tests/teledrive-sandbox.contract.test.mjs` |
| bundle markers | `TeleDriveGradioPanel` مرة، `setInterval` مرة، و`queue.refresh` ثلاث مرات في البندل الناتج |
| `pnpm run lint && pnpm run build` | PASS؛ توجد 7 تحذيرات Fast Refresh موجودة مسبقًا بلا errors |
| `python3 -m pytest -q tests` | `734 passed in 37.32s` |
| compileall / launcher / notebook check / cmp / package build | PASS؛ launcher `51/51` |

## حد التحقق الحي

> هذه المرحلة تثبت أن ملف JavaScript الذي تشحنه حزمة المشروع صار يحوي النبض، لكنها لا تثبت تنفيذ نقل Telegram/Drive داخل Colab حي.

بعد الدمج يلزم إعادة نشر حزمة Colab من `main` ثم Restart للـruntime وتشغيل Cells 1–4. لا تتبدل JavaScript في جلسة Colab المفتوحة أو داخل أرشيف نشر قديم لمجرد دمج المصدر.
