# CHANGELOG_ARCHIVE — أرشيف التغييرات التاريخية

> هذا الأرشيف للقراءة فقط. التغييرات الجارية تُسجَّل في `docs/CHANGELOG.md` (آخر 20-30 بندًا)، وعند امتلائه تُنقل أقدم البنود إلى هنا.
> المصدر الأصلي للبنود أدناه: `python-package/CHANGELOG.md` (قبل ترحيل نظام الاستمرارية) — سطر مؤشر واحد يبقى في موقعه القديم.

## v1.0.0 — 2026-07-29 (الإصدار الأولي، دستور v2.0)
- Telethon user-account + Google Drive OAuth Desktop.
- SQLite (WAL) + نقاط تحقق ذرّية مُصدَّرة إلى Drive `TeleDrive_AppData`.
- آلة حالات 12 حالة بانتقالات صارمة، تزامن Safe/Balanced/Fast/Manual (سقف 4).
- إعادة محاولة: 5 محاولات، أساس 2s، x2، سقف 60s، jitter، للأخطاء العابرة فقط.
- FloodWait محترم، إعادة المصادقة تظهر للمستخدم، تكرار يُكتشف عبر `appProperties.source_key`.
- واجهة Gradio عربية + إنجليزية (تبديل مباشر، RTL للعربية).
- notebook من 6 خلايا + مولّد خلايا الكاميرا + خلية صيانة.

## v3.1.0-phase0 — 2026-07-29 (مواءمة فقط)
- CONSTITUTION.md (Code-Bound v3.1)، AUDIT.md، تقرير PHASE_0، requirements.lock، spec_version/version = 3.1.0.

## v3.1.0-phase1 — 2026-07-29 (أساس التشغيل)
- `async_runtime.py`: حلقة الأحداث الخلفية الوحيدة.
- `app_context.py`: ApplicationContext واحد يملك config/aio/db/auth/queue/progress/UIState مع `resolve()` صارم.
- `bootstrap.run()` يعيد السياق؛ `app.launch()` و`ui.build(ctx)` تستخدمانه.
- إزالة نداءات `asyncio.new_event_loop()` الستة وخيط النقل من ui.py؛ إزالة lambda inline.
- اختبارات `test_no_ad_had_loops.py` + `test_app_context.py`. 48 اختبارًا ناجحًا.

## v3.1.0-phase9 — 2026-07-29 (إصلاح جاهزية Colab)
- `app.launch(blocking=False)` يمرر `prevent_thread_lock` إلى Gradio؛ المقبض على `ctx.ui` ويُغلق بـ `ctx.shutdown()` — الخلية 4 لم تعد تحجب الخلايا 5-7.
- `requirements.lock` هو مصدر الاعتماديات الوحيد؛ لا `package==version` في أي خلية/colab_cells.json.
- CI: compileall أولًا ثم pytest ثم --check ثم تطابق النوتبوك ثم build؛ `bun run lint` قبل `bun run build`؛ لا `continue-on-error`.
- PHASE_9.md يوثّق مخرجات حقيقية + SHA + شجرة الملفات.
- **الحالة: Code-complete candidate — التكاملات الحقيقية غير مُتحقَّق منها.** 177 passed (يُعاد إثباته).

## v4.5.0 — (قيد التنفيذ، ADR-001)
- إنشاء نظام الاستمرارية متعدد الحسابات (حزمة `docs/`) + توحيد هوية الإصدار إلى 4.5.0 + نسخ دستور v4.5 حرفيًا. التفاصيل عند اكتمال التنفيذ في `docs/CHANGELOG.md`.
