import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "TeleDrive v3.1 — Telegram to Google Drive on Colab" },
      {
        name: "description",
        content:
          "Download the TeleDrive v3.1 package and its 7-cell Colab notebook: one launcher, one runtime, native Colab Drive auth, no public link by default.",
      },
      { property: "og:title", content: "TeleDrive v3.1 — Telegram → Google Drive" },
      {
        property: "og:description",
        content:
          "A real Python backend (Telethon + Drive API + Gradio) packaged for one-command Colab startup with native Drive authorization.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

const modules = [
  "bootstrap.py",
  "app_context.py",
  "async_runtime.py",
  "config.py",
  "logging_config.py",
  "redaction.py",
  "utils.py",
  "models.py",
  "state_machine.py",
  "database.py",
  "migrations.py",
  "auth_manager.py",
  "telegram_auth.py",
  "telegram_links.py",
  "telegram_client.py",
  "media_scanner.py",
  "filters.py",
  "drive_auth.py",
  "drive_client.py",
  "drive_folders.py",
  "drive_quota.py",
  "duplicate_detector.py",
  "storage_manager.py",
  "checkpoint_manager.py",
  "queue_manager.py",
  "retry_policy.py",
  "transfer_manager.py",
  "progress_tracker.py",
  "error_handler.py",
  "errors.py",
  "snapshot.py",
  "handoff.py",
  "action_registry.py",
  "handlers.py",
  "services.py",
  "ui.py",
  "ui_binder.py",
  "app.py",
  "notebook_cells.py",
  "package_service.py",
  "i18n.py",
];

const cells = [
  "استعادة الحزمة وتثبيت الاعتماديات المثبّتة بإصدارات محددة.",
  "bootstrap.run() — سياق تشغيل واحد فقط، قاعدة بيانات SQLite في WAL على /content.",
  "تفويض Google Drive بشكل أصلي داخل Colab ثم ctx.drive_auth.adopt_service(...).",
  "تسجيل دخول تيليجرام عبر getpass، ثم launch(ctx, share=False) — بدون رابط عام.",
  "لقطة handoff مع إخفاء الأسرار تلقائياً.",
  "تشغيل حزمة الاختبارات — أي فشل يوقف الـ notebook.",
  "صيانة آمنة: حذف المؤقتات المُتحقَّق من رفعها فقط، والباقي إلى الحجر الصحي، ثم ctx.shutdown().",
];

function Index() {
  return (
    <div
      dir="rtl"
      className="min-h-screen bg-background text-foreground"
      style={{ fontFamily: "system-ui, -apple-system, 'Segoe UI', Tahoma, sans-serif" }}
    >
      <main className="mx-auto max-w-3xl px-6 py-12">
        <header className="mb-10">
          <h1 className="text-3xl font-bold tracking-tight">
            TeleDrive v3.1 — ناقل تيليجرام إلى Google Drive
          </h1>
          <p className="mt-3 text-muted-foreground leading-relaxed">
            حزمة بايثون كاملة (Telethon + Google Drive API + Gradio) تعمل داخل Google Colab. الصفحة
            دي مجرد صفحة تحميل — التطبيق الحقيقي هو الحزمة اللي هتشغّلها في Colab بأمر واحد.
          </p>
        </header>

        <section className="mb-8 rounded-lg border border-border bg-card p-6">
          <h2 className="mb-4 text-lg font-semibold">1) حمّل الملفين</h2>
          <div className="flex flex-col gap-3 sm:flex-row">
            <a
              href="/teledrive-package.zip"
              download
              className="inline-flex items-center justify-center rounded-md bg-primary px-5 py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              تحميل حزمة TeleDrive v3.1 (ZIP)
            </a>
            <a
              href="/TeleDrive.ipynb"
              download
              className="inline-flex items-center justify-center rounded-md border border-input bg-background px-5 py-3 text-sm font-medium transition-colors hover:bg-accent"
            >
              تحميل ملف Colab (.ipynb)
            </a>
          </div>
        </section>

        <section className="mb-8 rounded-lg border border-border bg-card p-6">
          <h2 className="mb-4 text-lg font-semibold">2) سبع خلايا في Colab لا أكثر</h2>
          <ol className="list-decimal space-y-2 pr-6 text-sm leading-relaxed">
            {cells.map((cell) => (
              <li key={cell}>{cell}</li>
            ))}
          </ol>
          <p className="mt-4 text-sm text-muted-foreground">
            أو مشغّل واحد بأمر واحد:{" "}
            <code className="rounded bg-muted px-1">!python teledrive_launcher.py</code> — و{" "}
            <code className="rounded bg-muted px-1">--check</code> للتحقق من الربط بدون أي بيانات
            اعتماد.
          </p>
        </section>

        <section className="mb-8 rounded-lg border border-border bg-card p-6">
          <h2 className="mb-4 text-lg font-semibold">3) اللي جوّه الحزمة</h2>
          <p className="mb-3 text-sm text-muted-foreground">
            {modules.length} وحدة بايثون فعلية — مش سلاسل نصية داخل الفرونت، ملفات
            <code className="mx-1 rounded bg-muted px-1">.py</code>حقيقية:
          </p>
          <ul className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground sm:grid-cols-3">
            {modules.map((m) => (
              <li key={m} className="font-mono">
                {m}
              </li>
            ))}
          </ul>
        </section>

        <section className="mb-8 rounded-lg border border-border bg-card p-6">
          <h2 className="mb-4 text-lg font-semibold">
            وظائف الباك-اند (كلها مربوطة بأزرار الواجهة)
          </h2>
          <ul className="list-disc space-y-1 pr-6 text-sm leading-relaxed">
            <li>سياق تشغيل واحد: حلقة async واحدة، عميل تيليجرام واحد، خدمة Drive واحدة.</li>
            <li>تسجيل دخول تيليجرام حقيقي (Telethon + phone/code/2FA).</li>
            <li>
              تفويض Drive أصلي داخل Colab — بدون رفع أي ملف OAuth وبدون لصق أي كود تفويض، ولا يُحفظ
              توكن على القرص.
            </li>
            <li>
              لا تظهر حالة «متصل» قبل نجاح فحص{" "}
              <code className="rounded bg-muted px-1">about().get()</code> على Drive.
            </li>
            <li>
              تحليل روابط: عامة، خاصة <code className="rounded bg-muted px-1">t.me/c/…</code>،
              دعوات، saved، ألبومات.
            </li>
            <li>فلاتر: نوع/امتداد/حجم/تاريخ/نطاق IDs/include/exclude.</li>
            <li>
              Queue + State Machine بـ 12 حالة وانتقالات صارمة (فقط QueueManager يعدّل الحالة).
            </li>
            <li>Semaphore: Safe=1, Balanced=2, Fast=3, Manual≤4 — بدون تجاوز.</li>
            <li>Retry: 5 محاولات، exp x2، cap 60s، jitter، transient فقط. FloodWait يُحترم.</li>
            <li>
              كشف التكرار عبر{" "}
              <code className="rounded bg-muted px-1">appProperties.source_key</code> + الحجم.
            </li>
            <li>
              Checkpoints ذرية تُرفع إلى{" "}
              <code className="rounded bg-muted px-1">TeleDrive_AppData</code> على Drive.
            </li>
            <li>Reconcile بعد إعادة تشغيل Colab: يتحقق من Drive قبل إعادة النقل.</li>
            <li>
              صيانة آمنة: حذف المؤقتات المُتحقَّق من رفعها فقط، وأي شيء غير معروف يُنقل للحجر الصحي.
            </li>
            <li>i18n عربي/إنجليزي حي مع RTL، وسجلّات مع Redaction للأسرار.</li>
          </ul>
        </section>

        <footer className="text-xs text-muted-foreground">
          v3.1 — لا رابط عام افتراضياً، ولا يُرسَل أي سرّ إلى هذا الموقع؛ كل شيء يبقى داخل حساباتك
          على Google و Telegram.
        </footer>
      </main>
    </div>
  );
}
