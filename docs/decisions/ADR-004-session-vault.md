# ADR-004 — Telegram Session Vault على Google Drive

- الحالة: **معتمد / منفّذ محليًا في M43 — التكامل والنشر وColab الحي معلّقة**
- التاريخ الأصلي: 2026-08-13
- تعديل M43: 2026-08-24
- القرار من: المالك، بتعليمات صريحة لتجربة «تسجيل واحد ثم Restart بلا Secret أو OTP»
- المرجع الدستوري: §11 (الأسرار) · §13 (Telegram/Drive) · §16 (سبع خلايا) · تجاوز صريح بموافقة المالك

## السياق

تزيل جلسة Colab المجانية محتوى `/content` عند إعادة التشغيل، بينما يريد المالك أن تكون تجربة Telegram مثل جهازه نفسه: يربط Drive ويُسجّل Telegram مرة واحدة فقط، ثم يستعيد نفس الحساب تلقائيًا من Drive على Runtime جديد. كان تصميم M42 يحل عيب تمرير مفتاح Vault format 2، لكنه ما زال يتطلب `TELEGRAM_API_HASH` من Colab Secrets لفك الـVault. ذلك لا يطابق تجربة Drive-only المطلوبة.

> **الحد الأمني المقبول بقرار المالك:** حساب Google Drive المخوّل بالوصول إلى `TeleDrive_AppData` هو حدّ الحماية العملي لاستعادة Telegram. لا يُطبع أي credential ولا يُرسل إلى React أو السجلات أو Git أو notebook output.

## القرار

1. تستخدم الحفظات الجديدة **Vault format 3 (Drive-managed)**. يحفظ manifest versioned زوجًا جديدًا من session blob المموّه وmetadata الضرورية لتشغيل Telethon في Runtime جديد، ومنها API credentials، داخل `TeleDrive_AppData`.
2. يُستعاد format 3 في Cell 3/4 مباشرةً من Drive؛ لا يتطلب Colab Secrets أو رقم هاتف أو OTP عندما تكون جلسة Telegram ما زالت صالحة.
3. تبقى Vault format 1 وformat 2 قابلة للقراءة. يحتاج format 2 مفتاحها مرة أخيرة من ذاكرة runtime أو Colab Secret، ثم بعد تحقق Telegram من الجلسة يُنشر زوج format 3 جديد ذريًا وتصبح الاستعادات التالية Drive-only.
4. لا تصبح النسخة الجديدة نشطة إلا بعد staging للـsession والـmetadata ثم استبدال manifest. لا يُحذف الزوج السابق قبل نجاح البديل. فشل الاستعادة أو `AuthKeyDuplicatedError` يمسح النسخة المحلية المؤقتة فقط ويترك Vault على Drive ليحمي من فقد البيانات.
5. لا يُحفظ أو يطبع هاتف Telegram أو OTP أو 2FA password أو Drive OAuth tokens. لا يحمل React أي credential ولا يوجد endpoint إضافي أو تخزين متصفح للأسرار.
6. تحفظ واجهة التحليل آخر رابط صالح في SQLite settings الخاصة بالـbackend وتعيده داخل live snapshot عبر Gradio bridge. هذا ينجو من Refresh وإعادة بناء الواجهة ضمن Runtime الحالي؛ زر مسح صريح يزيله. لا يستعمل `localStorage` ولا يُرسل الرابط إلى Drive.

## الأثر الأمني

| النموذج | تجربة Restart | حد الحماية |
|---|---|---|
| Vault format 2 | يحتاج API Hash خارج Drive | Drive **مع** مفتاح مستقل خارج Drive |
| Vault format 3 Drive-managed | لا Secret ولا OTP إذا بقيت الجلسة صالحة | حماية حساب Drive وصلاحية الوصول إلى مجلد Vault |

الصيغة 3 ليست تشفيرًا مستقلًا إذا امتلك طرفٌ ما وصولًا كاملًا إلى الـVault؛ التمويه يبقي blob غير مقروء عرضيًا لكنه لا يضيف حد أمان خارج Drive. هذا trade-off اختاره المالك صراحةً لتحسين الاستخدام. ينبغي عدم مشاركة حساب Drive أو مجلد `TeleDrive_AppData` مع غير موثوق، واستخدام حساب Google محمي بمصادقة قوية.

## البدائل المرفوضة

- Secrets مكتوبة داخل خلايا النوتبوك أو Git: مرفوضة لأنها قد تنتشر عند مشاركة النوتبوك.
- إبقاء format 2 فقط: مرفوض لأنه يفرض Colab Secrets، خلاف تجربة Drive-only التي اختارها المالك.
- تخزين session SQLite أو قاعدة runtime على Drive mounted: مرفوض بسبب FUSE/WAL والملفات المؤقتة.
- `localStorage` أو `sessionStorage` للرابط: مرفوض؛ الواجهة يجب أن تستمد الحالة من backend الحي عبر Gradio لا من نسخة مستقلة داخل المتصفح.

## التراجع

إلغاء الصيغة 3 يعني إعادة الكود السابق ونشر ZIP/manifest متطابقين مع SHA السابق عبر مسار release fail-closed. لا يُحذف release/tag. لا تحذف Vault format 3 تلقائيًا؛ تظل قابلة للاسترجاع أو الحذف فقط من إجراء `session.forget` الصريح.

## الاختبارات

يغطي `tests/test_session_vault.py` حفظ واستعادة format 3 بلا Secret خارجي، وmigration من format 2 بعد استعادة موثقة، واحتفاظ Drive عند session revoked. ويغطي `tests/test_react_bridge.py` و`tests/teledrive-sandbox.contract.test.mjs` أن رابط الفحص محفوظ في backend ويمكن مسحه ولا يفتح تخزين متصفح أو مسار نقل بديل.

## المراجع

`python-package/teledrive/session_vault.py` · `python-package/teledrive/notebook_cells.py` · `python-package/teledrive/services.py` · `python-package/teledrive/react_bridge.py` · `docs/PHASE_REPORTS/PHASE_M43_DRIVE_MANAGED_VAULT_AND_ANALYZE_LINK.md`
