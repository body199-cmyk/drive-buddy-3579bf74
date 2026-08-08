# TeleDrive v4.5 — Telegram → Google Drive Transfer Manager

> **المواصفة:** v4.5.0 (AI-OS Continuity Edition)
> **بيئة التشغيل:** Google Colab (Python 3.11 + Gradio + Telethon + Google Drive API)
> **الموقع المرجعي للتوثيق:** [`docs/`](docs/) — راجع [`docs/BOOTSTRAP_PROMPT.md`](docs/BOOTSTRAP_PROMPT.md) و [`docs/CONSTITUTION.md`](docs/CONSTITUTION.md)

## نظرة عامة (Overview)

TeleDrive هو محرك لنقل الوسائط والملفات من Telegram إلى Google Drive، مصمم للعمل كلياً داخل Google Colab مع واجهة Gradio محلية (`share=False`) ومصادقة Google Drive الأصلية الخاصة بـ Colab.

## البدء السريع (Quick Start)

1. افتح النوت‌بوك [`public/TeleDrive.ipynb`](public/TeleDrive.ipynb) أو [`python-package/notebook/TeleDrive.ipynb`](python-package/notebook/TeleDrive.ipynb) في Google Colab.
2. حمّل حزمة `teledrive_v4.5.zip` أو شغّل النوت‌بوك المكوّن من 7 خلايا.
3. تفويض Google Drive أصلي داخل بيئة Colab بدون رفع أي ملفات سرية.
4. إدخال بيانات Telegram API (ID / Hash) بشكل مخفي دون تسجيلها في السجلات.

## التوثيق الدستوري (AI-OS Documentation)

- **نقطة الدخول:** [`docs/BOOTSTRAP_PROMPT.md`](docs/BOOTSTRAP_PROMPT.md)
- **قواعد التشغيل:** [`docs/AI_RULES.md`](docs/AI_RULES.md)
- **السياق المرجعي:** [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md)
- **الدستور الأعلى:** [`docs/CONSTITUTION.md`](docs/CONSTITUTION.md)
- **الخريطة المعمارية:** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- **سجل العمل المفتوح:** [`docs/TODO.md`](docs/TODO.md)
- **سجل التسليم الحي:** [`docs/AI_HANDOFF.md`](docs/AI_HANDOFF.md)
- **سجل التغييرات:** [`docs/CHANGELOG.md`](docs/CHANGELOG.md)

## التطوير والمزامنة مع Lovable

هذا المشروع متصل بـ Lovable. أي تغيير يُدفع إلى `main` يُزامن تلقائياً.
