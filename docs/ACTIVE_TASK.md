# ACTIVE_TASK

| الحقل | القيمة |
|---|---|
| TASK ID | `M34-T01` |
| العنوان | إصلاح فحص القرص وحارس Drive المُركّب عبر المنصات (`safe_disk_free` + `is_mounted_drive`) |
| الحالة | **COMMITTED LOCALLY — بوابات Python خضراء على Windows؛ ينتظر push + PR + CI** |
| Branch | `fix/m34-t01-cross-platform-disk-and-mount-guards` |
| Commit | `c85ee9f` |
| Base | main `ffadd242` (مطابق لـorigin/main) |

## النطاق المنفذ

| المسار | السلوك |
|---|---|
| `teledrive/utils.py` | `safe_disk_free()` تعود إلى `shutil.disk_usage().free` عندما لا يوجد `os.statvfs` (Windows). قبلها كانت كل عمليات النقل على Windows تفشل `disk_full` وتعلق الصفوف في `Pending`. |
| `teledrive/config.py` | `is_mounted_drive()` تستخدم `Path.as_posix()` بدل `str(Path)` الذي يشوّه البادئات على Windows، فاستُعاد حارس `MountedRootError` لمنع SQLite على Drive/FUSE. |

## البوابات المنفذة (محليًا، Windows/Python 3.11)

قبل: `19 failed, 727 passed` → بعد: **`746 passed`** · compileall OK · launcher `51/51` · notebook check + cmp متطابقان.

## الحدود الصادقة

CI الأخضر الرسمي يتأكد بعد فتح ودمج الـPR. لا اختبار Colab جديد نُفذ؛ لا ادعاء Colab-ready أو Complete.

## الخطوة التالية

Push الـbranch وفتح PR، ثم مراجعة CI، ثم الدمج وإعادة نشر الحزمة بيد المالك.
