# ACTIVE TASK

| الحقل | القيمة |
|---|---|
| TASK ID | `M41-T01` |
| العنوان | حماية bridge React–Gradio من watcher/cleanup قديم في Colab |
| الحالة | **MERGED + CI-PASSED + PACKAGE-PUBLISHED**؛ تحقق Colab المنشور والنقل الحي غير مثبتين |
| code commit / merge | `4fca8e6b1c899c1b54a1adfbb38c65e247472b96` → main `bc9fc5f42bcec51d2f7f6566021cf0f2433de9d1` عبر PR [#87](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/87) |
| Publish | [#32646821416](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32646821416) SUCCESS؛ manifest/ZIP العامان commit `bc9fc5f…`، SHA `ab3d3db2…d1529`، حجم `567611` bytes |

## النطاق المثبت

1. on-load المتكرر لنفس Gradio host يعيد استخدام panel/bridge الحي بدل إنشاء bridge جديد والتخلص من bridge الذي قد تملكه React المعروضة.
2. لكل on-load lease؛ watcher وcleanup من run قديم لا يسلّمان state ولا ينفذان dispose للمالك الحالي.
3. `isLive()` مضافة إلى panel المركب فقط. لم تتغير action IDs أو transport أو Python handlers أو Telegram/Drive/session vault أو notebook أو الاعتماديات.
4. أعيد بناء الأصول المشحونة من المصدر.

## الأدلة

`769 passed` · `51/51` launcher · notebook check + cmp PASS · lint/build PASS (0 errors، 9 warnings baseline) · React contracts `33/33` · CI 4/4 · Gradio 6.20 وproxy `is_colab=True`: `Gradio · Live bridge` ثم `telegram.status` = `Action completed` · public manifest/ZIP verified.

## حدان باقيان

1. لقطة المالك أثبتت انحدارًا قبل M41، لكن لم يُفتح Cell 4 بالحزمة المنشورة M41 بعد؛ لا `Colab-ready` أو `Complete`.
2. لا نقل حي ولا Pause/Resume/Stop حقيقي في نطاق M41.

## نقطة التراجع والخطوة التالية

عكس merge `bc9fc5f…` للكود، ثم إعادة نشر archive/manifest مطابقين لـSHA سابق إن لزم تراجع كامل. الخطوة التالية: فحص Cell 4 في Colab بالحزمة المنشورة ثم إجراء طلب React واحد قبل وصف الإصلاح بأنه مثبت حيًا.
