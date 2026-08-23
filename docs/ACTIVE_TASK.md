# ACTIVE TASK

| الحقل | القيمة |
|---|---|
| TASK ID | `M41-T01` |
| العنوان | حماية bridge React–Gradio من watcher/cleanup قديم في Colab |
| baseline | `5b5d1b219d4cc279b91ece699339bc48054c6ccf` |
| الفرع | `fix/m41-t01-colab-stale-watcher-bridge` |
| الحالة | **CODE-COMPLETE CANDIDATE + LOCAL-PROXY-VERIFIED**؛ commit/PR/merge/publish pending |

## النطاق المثبت

1. عند تكرار `js_on_load` لنفس host، يعاد استخدام panel/bridge الحي بدل إنشاء مثيل جديد ثم التخلص من bridge الذي قد تملكه شجرة React المعروضة.
2. كل on-load يملك lease؛ watch أو cleanup من run قديم لا يسلّم state ولا ينفذ `dispose()` للمالك الحالي.
3. لا يمس هذا action IDs أو bridge transport أو Python handlers أو Telegram/Drive/session vault أو النوتبوك أو الاعتماديات.
4. أعيد بناء الأصول المشحونة من المصدر (`panel.bundle.gz` و`panel.css.gz`).

## الأدلة

`769 passed` · launcher `51/51` · notebook check + cmp PASS · lint/build PASS (0 errors، 9 warnings baseline) · React contracts `33/33` · Gradio 6.20 محلي وproxy `is_colab=True`: حالة `Gradio · Live bridge` ثم `telegram.status` = `Action completed`.

## حدان باقيان

1. لقطة المالك هي دليل انحدار حي قبل M41، لكن لم يُختبر bundle M41 في Runtime Colab الخاص به بعد؛ لا `Colab-ready` أو `Complete`.
2. لا نقل حي ولا Pause/Resume/Stop حقيقي في نطاق M41.

## نقطة التراجع والخطوة التالية

عكس commit M41 ثم إعادة نشر archive/manifest مطابقين إذا نُشرت الحزمة. بعد المراجعة النهائية: commit/push/PR/CI/merge والنشر، ثم Cell 4 Colab إن أمكن.
