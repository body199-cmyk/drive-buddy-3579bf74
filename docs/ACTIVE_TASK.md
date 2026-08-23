# ACTIVE TASK

| الحقل | القيمة |
|---|---|
| TASK ID | `M42` |
| العنوان | استعادة Telegram Session Vault المشفّر في Colab ومنع login غير لازم بعد Restart |
| baseline | `b7a2dac217376a9dbc322aa307a105a37d372491` |
| branch | `fix/m42-colab-session-vault-restore` |
| الحالة | **LOCAL VERIFICATION COMPLETE — remote integration and publish pending** |

## النطاق المثبت

1. زوج Vault format 2 موجود على Google Drive التجريبي في `TeleDrive_AppData` ولم يُحذف؛ فشل الاستعادة لا يبرر فقده.
2. كان Cell 3 يتجاوز تحميل API Hash أو prompt سري عند وجود Vault، و`restore_from_context` يهمل secret الممرر من Cell 4؛ لذلك لا يملك runtime جديد مفتاح فك blob المشفّر.
3. الإصلاح يمرر secret محليًا فقط من Cell 4 إلى `SessionVault.autorestore`، ويحمّل Cell 3 Colab Secrets قبل قرار Vault. عند وجود Vault بلا Secret، يطلب API ID/Hash المخفيين فقط؛ لا يطلب الهاتف أو OTP.
4. API Hash لا يوضع في Drive، ولا تُحذف ملفات Vault أو `.part`، ولا تتغير إجراءات Telegram أو transport أو action IDs أو bridge.

## الأدلة المحلية

`770 passed` · compileall PASS · launcher `51/51` · notebook check + cmp PASS · React contracts `33/33` · `pnpm run build` PASS · lint exit 0 مع 9 تحذيرات baseline · package build/ZIP integrity PASS. اختبار regression كان أحمر قبل التصحيح وأصبح أخضر، ويثبت أن bytes زوج Vault البعيد لا تتغير أثناء الاستعادة.

## حالة bridge والحزمة العامة

تحقق قراءة فقط من release الحالي يثبت manifest عند `bc9fc5f…` ووجود `__teledriveReactPanelLease` داخل ZIP العام. لا يصح نسبة ظهور `Backend bridge unavailable` إلى ZIP قديم من دون دليل. لكن Cell 4 في Colab الخاص بالمالك لم يُشغل بعد على إصلاح M42، لذا لا `Colab-ready` أو `Complete`.

## نقطة التراجع والخطوة التالية

عكس commit M42 على الفرع المحلي قبل أي عملية بعيدة هو rollback كامل. بعد مراجعة diff وفحص الأسرار والـCI، تبقى خطوات PR/merge/publish منفصلة. عند النشر لا يحذف release/tag؛ يبنى ZIP وmanifest من SHA main النهائي، ويستبدلان معًا فقط إذا لزم، ثم يعاد workflow للتحقق العام. أخيرًا يثبت اختبار Colab الحي: `telegram session vault: restored` و`Gradio · Live bridge`.
