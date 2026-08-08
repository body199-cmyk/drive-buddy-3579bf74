# RUNBOOK — TeleDrive v4.5 Operation

> Authority: `docs/CONSTITUTION.md` §15 + `docs/ARCHITECTURE.md`

## المتطلبات

- Google Colab runtime (Python 3.11)
- Telegram API ID/Hash (من https://my.telegram.org)
- حساب Google مع Drive
- الحزمة المختبرة `teledrive_v4.5.zip` (يُبنى من `package_service`)

## تشغيل 7 خلايا (العقد القانوني)

### Cell 1: Restore + install pinned
- يجلب ZIP من `/content/drive/MyDrive/TeleDrive/` إن وجد، وإلا من `/content/`
- يفك الضغط في `/content`، يضيف للحزمة `sys.path`
- `!pip -q install -r requirements.lock` — هذا هو المصدر الوحيد، لا `package==version` في الخلايا.
- يطبع `dependency source: .../requirements.lock` + `runtime root (local, not Drive)`

### Cell 2: Bootstrap
```python
os.environ.setdefault("TELEDRIVE_ROOT", "/content/teledrive_runtime")
from teledrive import bootstrap
ctx = bootstrap.run()   # ONE context
```
- ينشئ `data/ logs/ temp/ checkpoints/ session/ _quarantine` على local فقط
- يطبق migrations، يتحقق من WAL، يطبع `schema_version` + `free_bytes` + `journal_mode`

### Cell 3: Credentials (hidden + native Drive)
- Telegram: `getpass.getpass("API ID")` + `API Hash` — ذاكرة فقط، لا طباعة
- Drive:
```python
from google.colab import auth as colab_auth
import google.auth
from googleapiclient.discovery import build
colab_auth.authenticate_user(clear_output=False)
creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/drive"])
drive_service = build("drive","v3", credentials=creds, cache_discovery=False)
about = drive_service.about().get(fields="user(displayName,emailAddress),storageQuota(limit,usage)").execute()
```
- **Gate:** لا يوجد "Connected" قبل `about().get()` ينجح. لا `client_secret.json`، لا paste-code textbox، لا `drive_token.json`.

### Cell 4: Inject + launch UI
```python
from teledrive.app import launch
ctx.telegram_auth.set_credentials(api_id, api_hash); del api_id, api_hash
ctx.drive_auth.adopt_service(drive_service)
ctx.checkpoints.restore_and_reconcile()
launch(ctx, share=False, inline=True, blocking=False)
```
- `share=False` لا رابط عام افتراضي
- `blocking=False` → يمرر `prevent_thread_lock=True` إلى Gradio، الخلية ترجع فورًا، handle على `ctx.ui`
- `ctx.shutdown()` في Cell 7 يغلق UI handle

### Cell 5: Handoff redacted
```python
from teledrive import handoff
print(handoff.generate(objective="controlled Colab run", phase="10"))
```

### Cell 6: Tests fail loudly
```python
subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], ...)
raise SystemExit if failed
```

### Cell 7: Safe maintenance
```python
print(ctx.checkpoints.persist())
storage_manager.cleanup_verified_temp()  # يحذف فقط Uploaded الموثق، الباقي → quarantine
ctx.shutdown()
```

## CLI Launcher

```bash
!python teledrive_launcher.py --check   # بدون credentials
!python teledrive_launcher.py            # share=False
!python teledrive_launcher.py --share    # opt-in public link
```

## Recovery بعد قطع Colab

1. أعد الاتصال
2. أعد تشغيل خلايا 1-4 — session Telegram و Drive service يعاد بناؤه من نفس السياق
3. `recovery.restore` في UI أو `ctx.checkpoints.restore_and_reconcile()` — يستورد أحدث checkpoint من `TeleDrive_AppData` ويقارن مع Drive (لا auto-resume)
4. Start من جديد

## قواعد لا تنثني

- SQLite على local فقط (`config.assert_local_path`)
- لا حذف أعمى لـ TEMP_DIR — فقط `cleanup_verified_temp()`
- Cancel/stop لا يحذف ملف Drive أبدًا
- كل أسرار تبقى في الذاكرة فقط
