# ACTIVE_TASK — قفل معلوماتي لمهمة واحدة

| الحقل | القيمة |
|---|---|
| TASK ID | `M24-POST-MERGE-P1` |
| العنوان | إصلاحات ما بعد الدمج: null safety + ترتيب الطلبات (P1) |
| الحالة | **Code-complete candidate + Fake-tested** — إصلاحات P1 مطبّقة محليًا على فرع الجلسة؛ **ليس** Colab-ready ولا Complete |
| المالك التنفيذي | LM Arena Agent |
| المهندس/المراجع | Brain عبر ClickUp Docs |
| الفرع | `arena/019ff805-drive-buddy-3579bf74` |
| Base SHA | `504ec5e547b7b5270d3cd00fbdb69909bbe69621` (`origin/main` = PR #40+#41 merged) |
| PR الأساس المدموج | [#40](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/40) MERGED → `bbea9bf` · [#41](https://github.com/body199-cmyk/drive-buddy-3579bf74/pull/41) MERGED → `504ec5e` |
| ما تغيّر | `TeleDriveSandbox.tsx` (optional chaining + `latestRequest` Map) · `viewModel.ts` · `panel.bundle.gz`/`panel.css.gz` · contract tests 19–20 · docs |
| ما لم يتغيّر (محمي) | notebooks · telegram_auth · queue/transfer · database/migrations · requirements.* · bun.lock · package.json · workflows |
| Concurrency | 1..100 default 2 warn>8 (CONSTITUTION + ADR-0001) — **لم** يُرجَع إلى 1..4 |
| البوابات المحلية | contracts **20/20** · tsc PASS · lint 0 errors · build PASS · launcher **47/47** |
| الخطوة التالية | دفع الفرع + فتح PR → Brain review → Colab smoke بيد المالك |

## انحرافات

- الـcommit المزعوم سابقًا `acd6029` **لم يكن موجودًا** في Git؛ أُعيد تطبيق الإصلاحات من الصفر على `504ec5e`.
- `package-lock.json` ناتج عن `npm install` في الساندبوكس **غير مُتتبَّع** (القفل القانوني `bun.lock`).
- pytest الكامل لم يُشغَّل هنا (لا venv/gradio)؛ CI على الـPR هو الحكم.
