import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import TeleDriveSandbox from "../components/teleDrive/TeleDriveSandbox";
import sandboxCss from "../components/teleDrive/teleDrive.css?url";
import { RemoteColabBridge } from "../components/teleDrive/remoteColabBridge";

export const Route = createFileRoute("/connect")({
  head: () => ({
    meta: [
      { title: "Connect your Colab runtime — TeleDrive" },
      {
        name: "description",
        content: "Connect the TeleDrive portal directly to your own Google Colab runtime.",
      },
    ],
    links: [{ rel: "stylesheet", href: sandboxCss }],
  }),
  component: ConnectPage,
});

function ConnectPage() {
  const [runtimeUrl, setRuntimeUrl] = useState("");
  const [token, setToken] = useState("");
  const [bridge, setBridge] = useState<RemoteColabBridge | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function connect() {
    setError("");
    setBusy(true);
    let candidate: RemoteColabBridge | null = null;
    try {
      candidate = new RemoteColabBridge(runtimeUrl, token);
      await candidate.connect();
      setBridge(candidate);
    } catch (reason) {
      candidate?.disconnect();
      setError(reason instanceof Error ? reason.message : "Could not connect to Colab.");
    } finally {
      setBusy(false);
    }
  }

  function disconnect() {
    bridge?.disconnect();
    setBridge(null);
    setToken("");
  }

  if (bridge) {
    return (
      <div className="min-h-screen bg-background text-foreground">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3">
          <p className="text-sm text-muted-foreground">
            Connected directly to your Colab runtime. Your pairing token is held in this tab's memory only.
          </p>
          <button
            type="button"
            onClick={disconnect}
            className="rounded-md border border-border px-4 py-2 text-sm font-medium hover:bg-muted"
          >
            Disconnect
          </button>
        </div>
        <TeleDriveSandbox bridge={bridge} />
      </div>
    );
  }

  return (
    <main dir="rtl" className="min-h-screen bg-background px-4 py-10 text-foreground">
      <div className="mx-auto max-w-2xl">
        <a href="/" className="text-sm text-primary underline underline-offset-4">
          العودة إلى TeleDrive
        </a>
        <header className="mt-5 mb-7">
          <h1 className="text-3xl font-bold tracking-tight">اربط TeleDrive بـ Colab بتاعك</h1>
          <p className="mt-3 leading-7 text-muted-foreground">
            الموقع بيتصل مباشرة ببيئة Colab اللي إنت مشغّلها. الملفات وGoogle Drive وTelegram ومحرك النقل يفضلوا داخل بيئتك؛
            الموقع مش بيشغّل Colab بدلًا منك ومش بيخزن رمز الربط على السيرفر.
          </p>
        </header>

        <section className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <h2 className="text-lg font-semibold">قبل الربط</h2>
          <ol className="mt-3 list-decimal space-y-2 pr-6 text-sm leading-6">
            <li>افتح <a className="text-primary underline" href="/TeleDrive.ipynb" target="_blank" rel="noreferrer">دفتر TeleDrive على Colab</a> وشغّل الخلايا المطلوبة بالترتيب.</li>
            <li>بعد تشغيل الواجهة الحديثة، انسخ رابط <code>TeleDrive Web Dashboard URL</code> المطبوع في مخرجات Colab.</li>
            <li>انسخ <code>TeleDrive pairing token</code> من مخرجات نفس جلسة Colab. الرمز ده سري؛ ما تبعتوش لأي حد.</li>
            <li>الصق الرابط والرمز هنا. لو الجلسة انتهت أو اتغيرت، شغّلها من جديد واستخدم الرابط والرمز الجديدين.</li>
          </ol>

          <div className="mt-6 grid gap-4">
            <label className="grid gap-2 text-sm font-medium">
              رابط Colab الخاص بك
              <input
                type="url"
                inputMode="url"
                autoComplete="url"
                value={runtimeUrl}
                onChange={(event) => setRuntimeUrl(event.target.value)}
                placeholder="https://....googleusercontent.com/"
                className="w-full rounded-md border border-input bg-background px-3 py-3 font-normal"
                required
              />
            </label>
            <label className="grid gap-2 text-sm font-medium">
              رمز الربط السري
              <input
                type="password"
                autoComplete="off"
                spellCheck={false}
                value={token}
                onChange={(event) => setToken(event.target.value)}
                placeholder="الصق الرمز المطبوع في Colab"
                className="w-full rounded-md border border-input bg-background px-3 py-3 font-mono font-normal"
                required
              />
            </label>
            {error ? (
              <p role="alert" className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
                {error}
              </p>
            ) : null}
            <button
              type="button"
              onClick={() => void connect()}
              disabled={busy || !runtimeUrl.trim() || token.trim().length < 32}
              className="rounded-md bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50"
            >
              {busy ? "جارٍ اختبار الاتصال..." : "اختبار الاتصال وفتح لوحة التحكم"}
            </button>
          </div>
        </section>

        <aside className="mt-5 rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 text-sm leading-6">
          <strong>مهم للخصوصية:</strong> رمز الربط يمنح صلاحية التحكم في جلسة Colab دي. ما تحطّوش في رابط URL أو رسالة عامة.
          الاتصال بيكون مباشر من المتصفح إلى Colab، والرمز لا يُحفظ في localStorage أو قاعدة بيانات الموقع.
        </aside>
      </div>
    </main>
  );
}
