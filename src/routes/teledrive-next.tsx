import { useEffect, useRef, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import TeleDriveNext from "../components/teleDrive/TeleDriveNext";
import sandboxCss from "../components/teleDrive/teleDriveNext.css?url";
import { RemoteColabBridge } from "../components/teleDrive/remoteColabBridge";

export const Route = createFileRoute("/teledrive-next")({
  head: () => ({
    meta: [
      { title: "TeleDrive Next — Dashboard" },
      {
        name: "description",
        content:
          "Open TeleDrive Next directly; securely pair with your Colab runtime when available.",
      },
    ],
    links: [{ rel: "stylesheet", href: sandboxCss }],
  }),
  component: NextDashboardPage,
});

// The live credential is scoped to this browser tab, never persisted in
// localStorage, cookies, query strings, or on Vercel. Reloading the same tab
// should not force another Colab handoff while the runtime is still alive.
const SESSION_KEY = "teledrive-next:tab-session";
type TabSession = { runtimeUrl: string; token: string; expiresAt: number };

function readTabSession(): TabSession | null {
  try {
    const raw = window.sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const data: unknown = JSON.parse(raw);
    if (!data || typeof data !== "object") throw new Error("Invalid saved session.");
    const record = data as Partial<TabSession>;
    if (
      typeof record.runtimeUrl !== "string" ||
      typeof record.token !== "string" ||
      record.token.length < 32 ||
      typeof record.expiresAt !== "number" ||
      Date.now() >= record.expiresAt
    ) {
      throw new Error("Expired tab session.");
    }
    new RemoteColabBridge(record.runtimeUrl, record.token);
    return record as TabSession;
  } catch {
    clearTabSession();
    return null;
  }
}

function clearTabSession() {
  try {
    window.sessionStorage.removeItem(SESSION_KEY);
  } catch {
    // Browsers that block session storage still support one-click pairing.
  }
}

function saveTabSession(session: TabSession) {
  try {
    window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } catch {
    // Storage is optional; the live in-memory bridge remains usable.
  }
}

function NextDashboardPage() {
  const [bridge, setBridge] = useState<RemoteColabBridge | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [connectionError, setConnectionError] = useState("");
  const [disconnectionNotice, setDisconnectionNotice] = useState("");
  const handoffHandled = useRef(false);

  useEffect(() => {
    if (handoffHandled.current) return;
    handoffHandled.current = true;
    const params = new URLSearchParams(window.location.hash.slice(1));
    const runtimeUrl = params.get("url");
    const handoffToken = params.get("handoff");

    // Never leave a one-time capability in the URL/history.
    if (runtimeUrl && handoffToken) {
      window.history.replaceState(
        window.history.state,
        "",
        window.location.pathname + window.location.search,
      );
    }

    setConnecting(true);
    setConnectionError("");
    void (async () => {
      let candidate: RemoteColabBridge | null = null;
      try {
        if (runtimeUrl && handoffToken) {
          new RemoteColabBridge(runtimeUrl, "validation-token-placeholder-32chars");
          const exchangeUrl = new URL("api/pairing/exchange", runtimeUrl + "/");
          const response = await fetch(exchangeUrl.toString(), {
            method: "POST",
            mode: "cors",
            credentials: "omit",
            cache: "no-store",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ handoff_token: handoffToken }),
          });
          const contentType = response.headers.get("content-type") || "";
          if (!response.ok || !contentType.toLowerCase().includes("application/json")) {
            throw new Error(
              response.status === 401
                ? "رابط الربط انتهى أو اتستخدم قبل كده. افتح زر TeleDrive Next من خلية Colab الخامسة."
                : "تعذّر تأكيد الاتصال بـ Colab. أعد تشغيل خلية الربط.",
            );
          }
          const exchanged = await response.json();
          if (
            exchanged?.ok !== true ||
            typeof exchanged.token !== "string" ||
            exchanged.token.length < 32
          ) {
            throw new Error("استجابة ربط Colab غير صالحة.");
          }
          candidate = new RemoteColabBridge(runtimeUrl, exchanged.token);
          await candidate.connect();
          const expiresAt = Number(exchanged.expires_at) * 1000;
          saveTabSession({
            runtimeUrl,
            token: exchanged.token,
            expiresAt:
              Number.isFinite(expiresAt) && expiresAt > Date.now()
                ? expiresAt
                : Date.now() + 60 * 60 * 1000,
          });
          setBridge(candidate);
          return;
        }

        // No handoff in the URL: transparently restore this tab's connection.
        const saved = readTabSession();
        if (!saved) return;
        candidate = new RemoteColabBridge(saved.runtimeUrl, saved.token);
        await candidate.connect();
        setBridge(candidate);
      } catch (error) {
        candidate?.disconnect();
        setConnectionError(
          error instanceof Error ? error.message : "تعذّر إعادة الاتصال بـ Colab.",
        );
      } finally {
        setConnecting(false);
      }
    })();
  }, []);

  useEffect(() => {
    return () => {
      bridge?.disconnect();
    };
  }, [bridge]);

  async function disconnect() {
    if (!bridge) return;
    try {
      await bridge.revokePairing();
      setDisconnectionNotice("تم فصل الاتصال وإلغاء رمز التحكم في Colab.");
    } catch {
      setDisconnectionNotice(
        "تم فصل الواجهة، لكن تعذّر إلغاء الرمز في Colab. أوقف الجلسة لو محتاج تبطله فورًا.",
      );
    } finally {
      clearTabSession();
      bridge.disconnect();
      setBridge(null);
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div
        className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 text-sm"
        dir="rtl"
        role={connectionError ? "alert" : "status"}
      >
        <p className="text-muted-foreground">
          {connecting
            ? "جاري الربط التلقائي مع Colab..."
            : bridge
              ? "متصل بـ Colab. الواجهة والتحميلات جاهزين."
              : connectionError ||
                disconnectionNotice ||
                "واجهة TeleDrive Next جاهزة. شغّل Colab واضغط زر TeleDrive Next من الخلية الخامسة مرة واحدة للربط التلقائي."}
        </p>
        {bridge ? (
          <button
            type="button"
            onClick={() => void disconnect()}
            className="rounded-xl border border-border px-4 py-2 font-semibold hover:bg-muted"
          >
            فصل الاتصال
          </button>
        ) : !connecting ? (
          <a
            href="/connect-next?manual=1"
            className="rounded-xl border border-border px-4 py-2 font-semibold hover:bg-muted"
          >
            ربط يدوي (اختياري)
          </a>
        ) : null}
      </div>
      <TeleDriveNext key={bridge ? "live" : "preview"} bridge={bridge ?? undefined} />
    </div>
  );
}
