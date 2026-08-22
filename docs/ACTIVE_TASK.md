# ACTIVE_TASK

| الحقل | القيمة |
|---|---|
| TASK ID | `M35-T01` |
| العنوان | اعتماد هوية المنتج v5.0.0 في الكود والحزمة والنوتبوك (قرار مسجّل من المالك) |
| الحالة | **CODE COMMITTED LOCALLY — بوابات خضراء على Windows؛ ينتظر push + PR + CI** |
| Branch | `fix/m35-t01-version-identity-v5` |
| Commit | `5f37814` |
| Base | main `298b3b3d97` (بعد دمج PR#73 وPR#74) |
| التنفيذ | وكيل مساعد بتكليف مباشر من المالك (2026-08-22) |

## النطاق المنفذ

| المسار | السلوك |
|---|---|
| `teledrive/__init__.py` | `__version__` / `__spec_version__` = 5.0.0 |
| `teledrive/config.py` | `RuntimeConfig.version` / `spec_version` = 5.0.0 |
| `teledrive/notebook_cells.py` | `NOTEBOOK_VERSION` = 5.0.0 و`TITLE` = TeleDrive v5.0؛ النوتبوكان أعيد توليدهما بالمولّد الرسمي (`--write`) وتحقق التطابق (`--check`) |
| `tests/test_notebook.py` | عقد العنوان محدّث إلى TeleDrive v5.0 |

ما لم يُمسَّ عمدًا: اسم الأرتيفكت المثبّت `teledrive_v4.5.zip` — هو هوية أصل منشور تستخدمها بوابة Cell-1 والـ CI وrelease-current؛ تغييره قرار release مستقل يطال ملفات محمية.

## البوابات المنفذة (محليًا، Windows/Python 3.11)

`746 passed` · compileall OK · launcher `51/51 ready actions resolve` · notebook check متطابق.

## الحدود الصادقة

CI الأخضر الرسمي يتأكد بعد فتح ودمج الـ PR. لم يُنفذ اختبار Colab جديد؛ لا ادعاء Colab-ready أو Complete.

## الخطوة التالية

Push الـ branch وفتح PR، ثم مراجعة CI، ثم الدمج. إعادة نشر الحزمة بقرار منفصل بيد المالك.
