# ACTIVE TASK

| الحقل | القيمة |
|---|---|
| TASK ID | `M42` |
| العنوان | استعادة Telegram Session Vault المشفّر في Colab ومنع login غير لازم بعد Restart |
| code commit / merge | `b374efc` → `d54b010` عبر PR [#89](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/89) |
| الحالة | **MERGED + CI-PASSED + PACKAGE-PUBLISHED — Colab live pending** |
| Publish | [#32648838713](https://github.com/body199-cmyk/drive-buddy-3579bf74/actions/runs/32648838713) SUCCESS؛ manifest/ZIP العامان commit `d54b010…`، SHA `ffb5f6ab…b0f1`، حجم `568320` bytes |

## النطاق المثبت

1. زوج Vault format 2 كان موجودًا على Google Drive التجريبي في `TeleDrive_AppData` ولم يُحذف؛ فشل الاستعادة لا يبرر فقده.
2. كان Cell 3 يتجاوز تحميل API Hash أو prompt سري عند وجود Vault، و`restore_from_context` يهمل secret الممرر من Cell 4؛ لذلك لا يملك runtime جديد مفتاح فك blob المشفّر.
3. الإصلاح يمرر secret محليًا فقط من Cell 4 إلى `SessionVault.autorestore`، ويحمّل Cell 3 Colab Secrets قبل قرار Vault. عند وجود Vault بلا Secret، يطلب API ID/Hash المخفيين فقط؛ لا يطلب الهاتف أو OTP.
4. API Hash لا يوضع في Drive، ولا تُحذف ملفات Vault أو `.part`، ولا تتغير إجراءات Telegram أو transport أو action IDs أو bridge.

## الأدلة

`770 passed` محليًا، وCI Python/Frontend نجحا في push وPR · launcher `51/51` · notebook check + cmp PASS · React contracts `33/33` محليًا · `pnpm run build` PASS · lint exit 0 مع 9 تحذيرات baseline · package build/ZIP integrity PASS. workflow النشر الأول توقف fail-closed لاختلاف الحجم؛ استُبدل الزوج المتطابق معًا فقط، ثم تحقق workflow #32648838713 من الأصول العامة بنجاح.

## حدود لم تغلق

Cell 4 في Colab الخاص بالمالك لم يُشغّل بعد على الحزمة M42؛ لا `Colab-ready` أو `Complete`. كما أن وجود M41 lease في ZIP العام لا يمثل إثباتًا حيًا لـ`Backend bridge unavailable`; يبقى KNOWN_ISSUES #71 مفتوحًا حتى ظهور `Gradio · Live bridge` في Colab.

## نقطة التراجع والخطوة التالية

عكس merge `d54b010…` ثم إعادة نشر زوج ZIP/manifest مطابقين لـSHA سابق هو rollback الكامل إن لزم. لا يحذف release/tag. الخطوة التالية: Runtime Colab جديد على نفس Drive، Cells 1–4، وإثبات `telegram session vault: restored` ثم `Gradio · Live bridge`.
