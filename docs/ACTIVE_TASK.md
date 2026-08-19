# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

| الحقل | القيمة |
|---|---|
| TASK ID | `M27-T04` |
| العنوان | إصلاح عيوب النقل والقناة الخاصة وتحميل لوحة React المكتشفة بالتحقق الحي |
| الحالة | **MERGED + CI-PASSED + live sandbox-verified؛ Colab النهائي pending** |
| PR | [#59](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/59) — MERGED |
| Merge SHA | `dfbb90b9afc25e5bcbb5ce45ad5d90efd4099ac1` |
| Base SHA | `3bbe69b91159fb519e2d7fb6efab9835ad7788f5` |

## العيوب المثبتة والمغلقة

| المسار | الإصلاح المدمج | الدليل |
|---|---|---|
| Pause / Resume | يؤجل drain الاستئناف حتى يغلق المستقبل السابق؛ callback قديم لا يطفئ محركًا أحدث؛ الإلغاء المنضبط لا يسجل crash | Pause→Resume حي من offset انتهى `Uploaded`؛ Stop بقي `Stopped` بلا ملف Drive جديد |
| رابط دعوة قناة خاصة | يحل دعوة الحساب العضو فقط عبر `CheckChatInviteRequest` ثم InputPeer، بلا Join أو مسح غير محدود | Analyze حي أعاد مرشحًا محدودًا واحدًا؛ Dedupe أكد الملف البعيد الموجود |
| React داخل Gradio | يبني البندل بإدخال بيئة الإنتاج ويمنع `process.env.NODE_ENV` في الأصل المشحون | ظهرت اللوحة كاملة في متصفح محلي ولم يسجل console خطأ التحميل السابق |

## الأدلة

| البوابة | النتيجة |
|---|---|
| البوابات المحلية | `738 passed`، launcher `51/51`، compileall/notebook/cmp/package PASS؛ lint/build وReact contracts `26 passed` |
| CI | أربع فحوص ناجحة: Python وFrontend لكل من push وpull_request |
| تقرير المرحلة | `docs/PHASE_REPORTS/PHASE_M27_T04.md` |

## الخطوة التالية

ينبغي إعادة نشر حزمة Colab من `main` ثم Restart runtime واختبار لوحة React ونقل Telegram→Drive داخل Colab الحقيقي. وحتى نجاح ذلك، الحالة **ليست `Colab-ready` وليست `Complete`**.
