# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

| الحقل | القيمة |
|---|---|
| TASK ID | `M25-T02` |
| العنوان | تحديث تلقائي للصفحة كاملة أثناء النقل (نبض هادئ كل 2 ثانية) |
| الحالة | **MERGED INTO MAIN `2bc33e9f` (PR #47) · Code-complete candidate + Fake-tested** — ليس Colab-ready ولا Complete |
| المالك التنفيذي | LM Arena Agent |
| المهندس/المراجع | تعليمة المالك المباشرة (2026-08-13) |
| الفرع | `arena/019ff87b-drive-buddy-3579bf74` |
| سابق على main | PR #46 (خزنة الجلسة) → `27f99e1` |
| الخطوة التالية | ① المالك: Publish current TeleDrive package على `main` (#27) · ② فحص حي في Colab أثناء نقل حقيقي |

## ما تغيّر

- React: نبض كل 2000ms ينادي `queue.refresh` عبر `bridge.request` مباشرة (لا عبر `run()`)، يحدّث لقطة `LiveUiState` كاملة — كل الأقسام، مثل ضغطة `تحديث` — بلا وميض notice ولا busy spinner.
- البوابة: `hasActiveTransfer()` (المحرك `running` أو صف in-flight). لا حلقة خلفية دائمة.
- Python: `_on_run_done` يعيد `queue_manager._status` إلى `idle` بعد انتهاء drain (كان يبقى `running` للأبد).

## انحرافات

- لا انحرافات دستورية. الملفات المحمية لم تُمس.
- `bun run lint`/`build` لم تُشغَّل محليًا (حاجز شبكة `@lovable.dev` — KNOWN_ISSUES #37)؛ تتحقق في CI.
