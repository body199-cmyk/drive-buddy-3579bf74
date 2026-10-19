# ARCHITECTURE — TeleDrive v5.0 Current Map

> **Authority:** `docs/CONSTITUTION.md` §5 — هذه الخريطة للحالة الحالية فقط، لا تستبدل الدستور.

## المنتج

TeleDrive محرك نقل داخل Google Colab — واجهة Gradio في نفس عملية Python، سياق واحد، حلقة async واحدة، عميل Telethon واحد، خدمة Drive واحدة.

## الطبقات (Layers)

1. **Launcher** (`notebook_cells.py` المولد + `teledrive_launcher.py` + `bootstrap.py`):
   - يستعيد الأرشيف المُختبر، يثبت `requirements.lock`، يبني مجلدات local `/content/teledrive_runtime`، logging، SQLite WAL، migrations.
   - يجمع Telegram credentials عبر `getpass` (ذاكرة فقط)، ويؤدي Native Drive auth: `colab_auth.authenticate_user() -> google.auth.default(scopes=[drive]) -> build() -> about().get()` gate.

2. **ApplicationContext** (`app_context.py` + `async_runtime.py` + `config.py`):
   - مالك وحيد لكل: config، aio، db، auth، queue_manager، progress، telegram_auth، drive_auth، session_vault، drive_folders، drive_quota، selection، scanner، stats، log_service، settings، preferences، checkpoints، colab_export، package_service، handlers، binder، ui handle.
   - `resolve(service_path)` يفشل بصوت عالٍ على typo / None / non-callable — يمنع الأزرار الميتة.

3. **UI Binding** (`action_registry.py` + `ui_binder.py` + `handlers.py` + `ui.py` + `theme.py` + `i18n.py`):
   - `ACTION_SPECS` = 54 إجراء معلن — كل زر له `action_id`, `handler_name`, `service_path`, `label_key`, `section`, `implemented`, `tested`, `proof_test`.
   - `ready = implemented and tested` + proof_test مطلوب (القاعدة تمنع helper يقلب الاثنين معًا).
   - كل الإجراءات الـ54 حاليًا ready (`binding check ok: 54/54`).
   - إجراء غير جاهز لو وُجد يُرسم visible-disabled مع سبب مترجم (`blocked_reason_key`) — لا أزرار مخفية صامتة ولا أزرار ميتة (M17-T02/T03).
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
   - Support: `logging_config.py`, `redaction.py`, `errors.py`, `utils.py`, `progress_tracker.py`, `transfer_manager.py`, `package_service.py`, `notebook_cells.py`, `handoff.py`, `snapshot.py`, `auth_manager.py`, `session_vault.py`.
   - **SessionVault** (M24-T01): خدمة طبقة تطبيق على السياق الواحد. تعتمد على `DriveService` الموجود أصلًا ولا تملك مصادقة مستقلة. تحفظ/تستعيد `telegram.session` + `telegram_creds.json` داخل `TeleDrive_AppData` ثم تعيد الملف إلى `/content` قبل `set_credentials()` أو أثناء bootstrap النوت‌بوك. Telethon لا يعمل من Drive الموصول.

## Transfer Order (مقدس — §13)

```
validate connections → bounded scan → MediaItem → dedupe (source_key+size) → Drive quota → local disk → enqueue
→ .part download → verify local size → resumable Drive upload (8 MiB chunks)
→ verify Drive file id + appProperties + parent + size → durable checkpoint → Uploaded → targeted cleanup
```

- Concurrency: Default=2، manual 1..100، hard cap 100، وتحذير واجهة إجباري فوق 8 (ADR-0001)، Semaphore-bound worker pool حقيقي.
- **Throughput (M44-T01):** التنزيل الجديد يستعمل `iter_download` بطلب 512 KiB (حد MTProto) للملفات ≥1 MiB غير المصوّرة؛ Telethon `download_media()` كان يعطي 128 KiB≤100MB. أي فشل يعود للمسار القديم بأمان، وPause/Stop لا يُبتلعان. `cryptg` مثبّت لتفكيك AES بلغة C، ويُسجَّل التطبيق الفعّال عند الاتصال. **رفع Drive يبقى متسلسلًا عبر `_drive_lock`** لأن service object غير thread-safe؛ توسيعه يحتاج ADR.
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

## الحالة الحالية

- الهوية الرسمية للمنتج: **v5.0.0** (قرار M35-T01 / KNOWN_ISSUES #69؛ اسم أرتيفكت النشر المثبّت `teledrive_v4.5.zip` قرار release منفصل مقصود).
- `ACTION_SPECS`: **51/51 ready actions resolve** (بوابة launcher عند آخر دمج موثق).
- الاختبارات الكاملة: **746 passed** محليًا وفي CI (آخر handoff)، مع compileall وlauncher وnotebook cmp وReact contracts.
- جسر React–Gradio: مثيل واحد بملكية دورة حياة كاملة (M38-T01، PR #81).

## ما لم يتحقق بعد (حد حي صادق)

- **إثبات Colab الحي حتى Cell 4** وما بعدها (KNOWN_ISSUES #71 و#4/#5/#7 — بيد المالك): لوجين Telegram حقيقي، Drive `about().get()` حقيقي على الحزمة المنشورة، ونقل ملف فعلي. لا يُعلن `Colab-ready` قبل هذا الإثبات.
