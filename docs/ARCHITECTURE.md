# ARCHITECTURE — TeleDrive v4.5 Current Map

> **Authority:** `docs/CONSTITUTION.md` §5 — هذه الخريطة للحالة الحالية فقط، لا تستبدل الدستور.

## المنتج

TeleDrive محرك نقل داخل Google Colab — واجهة Gradio في نفس عملية Python، سياق واحد، حلقة async واحدة، عميل Telethon واحد، خدمة Drive واحدة.

## الطبقات (Layers)

1. **Launcher** (`notebook_cells.py` المولد + `teledrive_launcher.py` + `bootstrap.py`):
   - يستعيد الأرشيف المُختبر، يثبت `requirements.lock`، يبني مجلدات local `/content/teledrive_runtime`، logging، SQLite WAL، migrations.
   - يجمع Telegram credentials عبر `getpass` (ذاكرة فقط)، ويؤدي Native Drive auth: `colab_auth.authenticate_user() -> google.auth.default(scopes=[drive]) -> build() -> about().get()` gate.

2. **ApplicationContext** (`app_context.py` + `async_runtime.py` + `config.py`):
   - مالك وحيد لكل: config، aio، db، auth، queue_manager، progress، telegram_auth، drive_auth، drive_folders، drive_quota، selection، scanner، stats، log_service، settings، preferences، checkpoints، colab_export، package_service، handlers، binder، ui handle.
   - `resolve(service_path)` يفشل بصوت عالٍ على typo / None / non-callable — يمنع الأزرار الميتة.

3. **UI Binding** (`action_registry.py` + `ui_binder.py` + `handlers.py` + `ui.py` + `theme.py` + `i18n.py`):
   - `ACTION_SPECS` = 41 إجراء معلن — كل زر له `action_id`, `handler_name`, `service_path`, `label_key`, `section`, `implemented`, `tested`, `proof_test`.
   - `ready = implemented and tested` + proof_test مطلوب (القاعدة تمنع helper يقلب الاثنين معًا).
   - `binder.button(gr, action_id)` ينشئ زر عادي لو ready، أو مخفي+معطل بـ `common.unavailable` لو ليس ready — لا زر ميت يصل للمستخدم.
   - `binder.wire_if_ready()` يربط click/change بـ handler مسمى فقط، لا `.click(` ولا `lambda` في `ui.py`.
   - `binder.assert_complete()` يفشل البناء إذا وجد ready غير موصول أو مرسوم غير موصول.

4. **Domain** (`models.py` + `state_machine.py` + `filters.py` + `retry_policy.py` + `duplicate_detector.py`):
   - `MediaItem` مع `source_key` محدد (MTProto identity، ليس filename ولا Bot API file_unique_id).
   - State machine 12 حالة: انتقالات صارمة فقط QueueManager يعدلها.
   - Retry: 5 محاولات، base 2s، x2، cap 60s، jitter، transient فقط، FloodWait محترم.

5. **Persistence** (`database.py` + `migrations.py` + `checkpoint_manager.py` + `storage_manager.py`):
   - SQLite WAL على local `/content` فقط — مرفوض على `/content/drive` و أي FUSE mount (config.py `assert_local_path`).
   - Checkpoints ذرية محليًا + مرفوعة إلى `TeleDrive_AppData` على Drive.
   - reconcile بعد إعادة تشغيل: يتحقق من Drive قبل إعادة النقل.

6. **Infrastructure**
   - Telegram: `telegram_auth.py` (10 حالات: DISCONNECTED..AUTHORIZED) + `telegram_client.py` + `telegram_links.py` + `media_scanner.py`
   - Drive: `drive_auth.py` (native only) + `drive_client.py` + `drive_folders.py` (persist folder ID لا name) + `drive_quota.py`
   - Support: `logging_config.py`, `redaction.py`, `errors.py`, `utils.py`, `progress_tracker.py`, `transfer_manager.py`, `package_service.py`, `notebook_cells.py`, `handoff.py`, `snapshot.py`, `auth_manager.py`.

## Transfer Order (مقدس — §13)

```
validate connections → bounded scan → MediaItem → dedupe (source_key+size) → Drive quota → local disk → enqueue
→ .part download → verify local size → resumable Drive upload (8 MiB chunks)
→ verify Drive file id + appProperties + parent + size → durable checkpoint → Uploaded → targeted cleanup
```

- Concurrency: Safe=1, Balanced=2, Fast=3, Manual≤4 — hard cap 4، Semaphore-bound worker pool حقيقي.
- Cancel/stop/clear-completed لا تحذف ملف Drive أبدًا.
- Size mismatch يبقي `.part`، ملفات مجهولة → quarantine لا حذف أعمى.

## UI/UX (§14)

- افتراضي عربي RTL، تبديل حي لإنجليزي LTR يحافظ على runtime state.
- شريط علوي: ZIP export · theme · AR/EN · Drive status + folder chip · Telegram status · version badge (reads real values).
- أقسام: Dashboard, Transfers, Analyze, Connection Center, Logs, Settings, Colab Code/Export.
- Empty runtime يعرض localized empty component — لا rows وهمية، لا عدادات وهمية، لا نقاط اتصال مزيفة.

## Notebook Contract (7 خلايا + 2 اختيارية §15)

1. restore + `pip install -r requirements.lock` (مصدر وحيد) + طباعة path lock
2. `bootstrap.run()` → dirs + logging + migrations/WAL
3. `getpass` hidden Telegram + native Drive auth + `about().get()` gate
4. `ctx.telegram_auth.set_credentials()` + `ctx.drive_auth.adopt_service(drive_service)` + `restore_and_reconcile()` + `launch(ctx, share=False, blocking=False)` — handle على `ctx.ui`
5. `handoff.generate()` مع redaction تلقائي
6. `python -m pytest -q tests` يفشل الخلية عند فشل
7. `checkpoint.persist()` + `storage_manager.cleanup_verified_temp()` + `quarantine` + `ctx.shutdown()` (يغلق UI handle أولاً)

`teledrive_launcher.py` هو نقطة دخول مستقرة — `teledrive_launcher.py --check` يتحقق من bindings بدون credentials.

## CI (§16)

```
python -m compileall teledrive
python -m pytest -q tests
python teledrive_launcher.py --check
python -m teledrive.notebook_cells --check
cmp notebook/TeleDrive.ipynb ../public/TeleDrive.ipynb
python -m teledrive.package_service --build --output teledrive_v4.5.zip
bun run lint
bun run build
```

لا `continue-on-error`. `package_service.build_tested_archive()` يرفض البناء إذا فشلت الاختبارات.

## Current Counts (2026-08-08)

- `teledrive/`: 44 وحدة (تحقق بـ `ls`)
- `ACTION_SPECS`: 41 — ready 22، unready 19 (Drive 6، Analyze 3، Dashboard 1، Logs 3، Settings 2، Export 2، Recovery 2)
- Tests: مؤرشف 177 passed في PHASE_9.md لكن يحتاج إعادة إثبات بمثبتات الحالية.

## ما لم يتحقق

- Real Telegram login, real Drive `about().get()`, بناء Gradio 6.20.0 حقيقي `prevent_thread_lock`، تشغيل Colab حقيقي 1→7 (بيد المالك PHASE_10).
