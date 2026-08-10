# PHASE_M17_T01 — جرد صادق لكل أزرار/إجراءات الواجهة (بلا تعديل كود)

**المرجع:** M17 MASTER §2 (M17-T01) + TeleDrive Constitution v5.0
**التاريخ (UTC):** 2026-08-10
**المنفّذ:** LM Arena Agent — **المراجعة بانتظار Brain**

## التقرير (قالب M17 §7)

```plain
TASK ID: M17-T01
Status: VERIFIED COMPLETE (نطاق T01 فقط — الجرد والتوثيق؛ لا إصلاح كود)

GitHub Status:
Commit: SUCCESS — f311a0615155a681aa16b75edac7e416e0053744 (+ follow-up docs commit لتسجيل رابط PR)
Push: SUCCESS — origin/arena/019febba-drive-buddy-3579bf74
Pull Request: CREATED — https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/26
Branch: arena/019febba-drive-buddy-3579bf74
Base SHA: 4a2dac62e0aa57092100d35a1726d464b742e48c (= origin/main = merge PR #23 / M16-T01)
Result SHA: f311a0615155a681aa16b75edac7e416e0053744 (+ follow-up docs commit)
PR URL: https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/26
Operation error: لا شيء في Git. قيد بيئة معروف: pytest/gradio غير مثبتين مسبقًا في الحاوية — أُنشئ venv محلي (python-package/.venv، مستثنى من Git عبر .git/info/exclude) بمثبّتات requirements.lock حرفيًا.
Current repository state: شجرة نظيفة عند البدء؛ لا تعديل على أي ملف منتج.

Files created:
- python-package/docs/UI_ACTION_INVENTORY.md   (المخرَج الإلزامي الوحيد لـT01)
- docs/PHASE_REPORTS/PHASE_M17_T01.md          (هذا الملف)

Files modified (ذاكرة فقط، بلا كود منتج):
- docs/TODO.md           (صف M17-T01)
- docs/CHANGELOG.md      (بند M17-T01)
- docs/ACTIVE_TASK.md    (قفل M17-T01)
- docs/KNOWN_ISSUES.md   (بنود موثقة جديدة من الجرد — رُقّمت #28–#31 بعد دمج main الذي ثبّت #27 لقيد `actions:write`)
- docs/AI_HANDOFF.md     (بطاقة هذه الجلسة)

Files deleted: لا شيء
git diff --name-only: يُثبت في الـcommit (انظر أعلاه)

Verification output raw:
$ git branch --show-current -> arena/019febba-drive-buddy-3579bf74
$ git rev-parse HEAD        -> 4a2dac62e0aa57092100d35a1726d464b742e48c
$ git status --porcelain    -> (فارغ)
$ git rev-parse origin/main -> 4a2dac62e0aa57092100d35a1726d464b742e48c
$ cd python-package && python -m compileall teledrive            -> exit 0
$ python -m pytest -q tests/test_bindings.py tests/test_action_proofs.py tests/test_ui_shell_contract.py
  -> 61 passed, 1 warning in 5.93s   (env: venv بمثبّتات requirements.lock: gradio 6.20.0 / pytest 9.1.1 / telethon 1.44.0)
$ python teledrive_launcher.py --check
  -> bootstrap ok …؛ binding check ok: 26/42 ready actions resolve؛ exit 0
$ python -m pytest -q tests   (إضافي خارج البوابة الرسمية)
  -> 443 passed, 1 warning in 13.67s
$ فحص i18n يدوي: مفاتيح labels الناقصة في ar/en = NONE
$ gh pr view 23  -> MERGED 2026-08-10T02:52:31Z at 4a2dac62 (RESUME_VERIFIED)
$ gh release view pkg-2026.08.09-m15t07 -> target=4a2dac62, publishedAt=2026-08-10T11:55:10Z,
  assets: teledrive_v4.5.zip 222699B + teledrive_manifest.json 378B  (الإصدار = main HEAD؛ ليس قديمًا)

Actions proven (على مستوى الكود/العقود — 26 جاهزًا):
- telegram.* (7): handlers + state machine + إخفاء/إظهار OTP/2FA مشروط ومثبت بـshell contract (FakeClient)
- drive.refresh_quota: proof test_drive_quota.py::test_warn_90
- analyze.* (6): run/set_mode/apply_filters/select_all/clear_selection/enqueue_selected — proofs فردية
- queue.* (11): start_selected (لا يعالج كل Pending)، pause (checkpoint أولًا)، resume/stop، retry_failed (Stopped نهائي)، clear_completed (metadata فقط)، refresh، وإجراءات العنصر الأربعة
- settings.toggle_language: proof i18n + إعادة رسم حافظة للحالة

Actions still blocked (16 — implemented صادقة لكن tested=False → مخفية عمدًا):
- drive.connect / reconnect / status / list_folders / create_folder / select_folder  (T02-P1)
- dashboard.refresh  (T02-P2؛ البيانات نفسها مبذورة حية أصلًا)
- logs.refresh / search / download  (T02-P4)
- settings.set_concurrency / settings.set_theme  (T02-P5؛ set_theme تفضيل بلا أثر بصري حاليًا)
- export.build_zip / export.colab_cells / recovery.restore / maintenance.checkpoint  (T02-P6)

Live Colab proof: لا يوجد — بيد المالك (M15-T01). لا ادعاء Colab-ready.

Honest product status:
Code-complete candidate; real Telegram, Drive, and controlled transfer integrations unverified.
26/42 إجراءً ظاهرًا وموصولًا فعليًا؛ 16/42 منفذة لكن مخفية بوابة 4A.1 (15 منها بلا شرح ظاهر).
لا أزرار ميتة، لا handlers مفقودة، لا service paths مكسورة، لا fake data في أول رسم.

What is not proven:
- أي استدعاء Telegram/Drive حقيقي (كل الأدلة وحشية بـfakes)
- الأثر البصري لتبديل الثيم (غير موجود بنيويًا — light theme غير منفذ)
- سلوك 15 إجراءً مخفيًا خلف proof tests لم تُكتب بعد
- استهلاك الحزمة المنشورة من Colab حقيقي

Next step: STOP and await Brain approval
```

## تحديث ما بعد الدفع — حل تعارض PR #26 (docs-only)

main تقدّم بسجلات توثيق M16-T01 (PR #24 عبر `5a7dda2` + PR #25 عبر `416afbe`، merge `37377cb`) فتعارض مع ملفات الذاكرة الخمسة في هذا الفرع. حُل بدمج `origin/main` (commit `0dc1d0c63a325783578d93a8d8f8f164bf8fd369`): AI_HANDOFF/ACTIVE_TASK تبقيان على جلسة M17-T01 (الأحدث — تصميم الملفين)، CHANGELOG/TODO اجتماع الجانبين، وKNOWN_ISSUES أبقت #27 لقيد `actions:write` القادم من main وأُعيد ترقيم بنود الجرد إلى #28–#31 مع تصحيح كل المراجع. **صفر كود منتج في الحل.** بعد الدفع: PR `mergeable=MERGEABLE, mergeStateStatus=CLEAN`، CI أخضر (Python 1m12s run `31392467213` · Frontend 13s run `31392469908`)، والبوابات المحلية مُعادة بعد الدمج: compileall OK · T01 `61 passed` · launcher `26/42` · كامل `443 passed`.

## ملاحظات صدق إضافية خارج القالب

- **M16-T02/T03/T04 لم تُبدأ** — M17 MASTER حلّ محل خطة M16 كمرجع (بنص تعليمة المالك الحالية).
- **لا تعديل على:** Notebook، `PKG_RELEASE_TAG`، workflows، lockfiles، `package.json`، Release، أو أي ملف منتج تحت `teledrive/` أو `tests/`.
- قيد البيئة: `bun` غير متاح في الحاوية (موثق سابقًا في M15-T04) — غير متعلق بنطاق T01 (Python فقط).
- سكربت الفحص المتقاطع المستخدم لبناء الجدولين كان عابرًا (heredoc) ولم يُحفظ في الريبو.
