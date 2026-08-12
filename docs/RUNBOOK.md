# RUNBOOK — TeleDrive v4.5 Operation

> Authority: `docs/CONSTITUTION.md` §15 + `docs/ARCHITECTURE.md`

## المتطلبات

- Google Colab runtime (Python 3.11)
- Telegram API ID/Hash (من https://my.telegram.org)
- حساب Google مع Drive
- الحزمة المختبرة `teledrive_v4.5.zip` (يُبنى من `package_service`)
  - مصدرها: آخر تشغيل CI أخضر → Actions → Artifacts → `teledrive-package` (يتطلب صلاحية على المستودع).
  - **تنبيه:** التنزيل من GitHub يعطي غلافًا خارجيًا باسم `teledrive-package.zip` يحتوي الملف الحقيقي بداخله. ارفع الغلاف **كما هو** إلى `/content/` (أو إلى `MyDrive/TeleDrive/`) — Cell 1 تكتشفه وتستخرج الملف الداخلي تلقائيًا. **لا تُعِد تسميته** أبدًا.

## تشغيل 7 خلايا (العقد القانوني)

### Cell 1: Restore + install pinned
- `resolve_package_zip()` يقبل الأشكال الثلاثة: الأرشيف الحقيقي `teledrive_v4.5.zip` (في `/content/` أو Drive)، والغلاف الرسمي `teledrive-package.zip` (في أي منهما)، وحتى غلافًا أُعيدت تسميته خطأً إلى `teledrive_v4.5.zip` (يكتشفه بالمحتوى ولا يعامله كأرشيف حقيقي).
- استخراج الغلاف يتم عبر ملف مؤقت مختلف ثم نقل ذري (`tempfile` + `os.replace`) — لا قراءة وكتابة على الملف نفسه، فلا `EOFError`؛ ومسارات الأعضاء غير الآمنة (traversal) مرفوضة، ويُتحقق من بنية الأرشيف الداخلي (`teledrive-v4.5/` + `requirements.lock`) قبل اعتماده.
- عدم وجود أي من الملفين يبقي رسالة الخطأ الواضحة نفسها مع تلميح أن الغلاف مقبول كما هو.
- بعد حل المسار: يفك الضغط في `/content`، يضيف للحزمة `sys.path`
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

### Cell 3: Credentials (Colab Secrets + native Drive)
- مرة واحدة: أيقونة المفتاح في Colab ← أضيفي `TELEGRAM_API_ID` و`TELEGRAM_API_HASH`.
- الخلية تقرأ الأسرار أولًا؛ إن نقص سر تستخدم `getpass` لهذه الجلسة فقط. لا طباعة للقيم.
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
from teledrive import session_vault
ctx.drive_auth.adopt_service(drive_service)
session_vault.restore_from_context(ctx, secret=api_hash)
ctx.telegram_auth.set_credentials(api_id, api_hash); del api_id, api_hash
ctx.checkpoints.restore_and_reconcile()
launch(ctx, share=False, inline=False, blocking=False)
session_vault.start_keepalive()
```
- Drive أولًا ثم استعادة `telegram.session` من `TeleDrive_AppData` إن وُجدت → لا OTP
- `share=False` لا رابط عام افتراضي
- `blocking=False` → الخلية ترجع فورًا، handle على `ctx.ui`
- keep-alive يأخّر فصل الخمول؛ لا يهزم حد 12 ساعة ولا التبويب المغلق
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

1. أعد الاتصال (VM جديد = `/content` فاضي). **لازم** الخلايا 1–4. الخلية الأخيرة وحدها لا تكفي.
2. إن كانت أسرار Colab محفوظة: الخلية 3 لن تطلب API ID/Hash.
3. إن سبق وسجّلتِ تليجرام بنجاح: الخلية 4 تستعيد الجلسة من Drive وتتخطى OTP. Drive عادةً كلك واحدة.
4. `recovery.restore` في UI أو `ctx.checkpoints.restore_and_reconcile()` — يستورد أحدث checkpoint من `TeleDrive_AppData` (لا auto-resume للنقل).
5. Logout من الواجهة يحذف خزنة الجلسة — المرة التالية تحتاج OTP من جديد.

## قواعد لا تنثني

- SQLite على local فقط (`config.assert_local_path`)
- لا حذف أعمى لـ TEMP_DIR — فقط `cleanup_verified_temp()`
- Cancel/stop لا يحذف ملف Drive أبدًا
- api_id/hash/phone/OTP/2FA لا تُكتب في النوتبوك ولا السجلات. جلسة تليجرام المعمّاة فقط تُحفظ في Drive AppData بموافقة المالك (ADR-004).
