# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

| الحقل | القيمة |
|---|---|
| TASK ID | `M27-T01` |
| العنوان | تقوية نقل TeleDrive: throttle للتقدم، كشف أعطال المحرك، القنوات الخاصة، واستئناف التنزيل من offset |
| الحالة | **MERGED + CI-passed + local/fake-tested. Not live-verified**؛ ليس Colab-ready ولا Complete |
| المالك التنفيذي | LM Arena Agent |
| فرع المصدر | `arena/m27-t01-final-hardening` (محذوف بعد الدمج) |
| Base SHA | `85822af73326d60894bde9737a35672a4aae1e08` |
| Source commit | `f6bf28161dc3c632cf27ebef505587493c208142` |
| Merge commit / main | `e230ce9da90da5b1ea2e43c0879a5930c57f9104` عبر PR [#54](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/54) في `2026-08-19T03:29:45Z` |
| CI | أربع فحوص مكتملة بنجاح على PR #54: Python وFrontend لكل من push وpull request |
| الخطوة التالية | ينفذ المالك بروتوكول Telegram/Drive/Colab الحي؛ لا تغيير كود إضافي قبل ظهور دليل حي أو بلاغ جديد. |

## ما تغيّر

| المحور | التغيير المتوافق مع الواجهات الحالية |
|---|---|
| SQLite progress | throttle لكل عنصر (`0.5s`) لتفادي كتابة قاعدة البيانات في كل chunk، مع flush مفروض عند الحدود والنهاية. |
| سلامة المحرك | تعاد استثناءات العامل غير الملغاة من drain loop؛ يسجل callback الطابور `transfer run crashed` ويعيد الحالة إلى `idle`. |
| قنوات Telegram الخاصة | `resolve_entity()` يسخن dialogs مرة واحدة عند اللزوم، و`peer_id()` ينتج هوية Telethon الصحيحة للقنوات (`-100<id>`). |
| رسالة الخطأ | عدم الوصول إلى قناة خاصة يصبح `PrivateChannelUnresolvedError` دائمًا ومترجمًا في العربية والإنجليزية. |
| resume | `download_partial()` يقص `.part` فقط حتى محاذاة `4096` ثم يواصل `iter_download(offset=...)`؛ يبقى المسار الكامل الآمن للصور أو الملف غير القابل للاستئناف. |

## التحقق الفعلي

| البوابة | النتيجة |
|---|---|
| اختبارات M27 الجديدة | `16 passed` |
| اختبارات التحكم وM26-T03 | `18 passed` |
| i18n وحظر `asyncio.run()` داخل `teledrive/**` | `5 passed` |
| المجموعة الكاملة | `734 passed` |
| `compileall` وlauncher | PASS؛ `51/51 ready actions resolve` |
| النوتبوكات و`cmp` وبناء الحزمة | PASS |
| `pnpm run lint && pnpm run build` | PASS؛ استُخدم pnpm لأن Bun غير متاح |
| CI البعيد | 4/4 SUCCESS على PR #54 |

## حدود لا تتغير

لا تعديل على الملفات المحمية أو النوتبوكات أو lockfiles أو workflows، ولا يوجد `asyncio.run()` داخل `teledrive/**`. لا تحذف مسارات Pause/Stop ملفات `.part` أو ملفات Google Drive. لم يُنفذ اختبار Telegram أو Google Drive أو Colab حي؛ لذلك تبقى الحالة الصحيحة **Merged + CI-passed + local/fake-tested** فقط.
