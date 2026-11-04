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

function NextDashboardPage() {
  const [bridge, setBridge] = useState<RemoteColabBridge | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [connectionError, setConnectionError] = useState("");
  const [disconnectionNotice, setDisconnectionNotice] = useState("");
  const handoffHandled = useRef(false);

  useEffect(() => {
    if (handoffHandled.current) return;
    const params = new URLSearchParams(window.location.hash.slice(1));
    const runtimeUrl = params.get("url");
    const handoffToken = params.get("handoff");
    if (!runtimeUrl || !handoffToken) return;
    handoffHandled.current = true;

    // A short-lived one-use capability is never kept in the visible URL,
    // stored in localStorage or passed to a TeleDrive action.
    window.history.replaceState(
      window.history.state,
      "",
      window.location.pathname + window.location.search,
    );
    setConnecting(true);
    setConnectionError("");

    void (async () => {
      let candidate: RemoteColabBridge | null = null;
      try {
        // Reject unsupported hosts before exchanging the one-time capability.
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
              ? "رابط الربط انتهت صلاحيته أو اتستخدم قبل كده. شغّل خلية الربط في Colab مرة تانية."
              : "تعذّر تأكيد الاتصال بـ Colab. شغّل خلية الربط مرة تانية.",
          );
        }
        const exchanged = await response.json();
        if (
          exchanged?.ok !== true ||
          typeof exchanged.token !== "string" ||
          exchanged.token.length < 32
        ) {
          throw new Error("استجابة Colab غير صالحة. شغّل خلية الربط من جديد.");
        }
        candidate = new RemoteColabBridge(runtimeUrl, exchanged.token);
        await candidate.connect();
        setBridge(candidate);
      } catch (error) {
        candidate?.disconnect();
        setConnectionError(error instanceof Error ? error.message : "تعذّر الاتصال بـ Colab.");
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
                "واجهة TeleDrive Next مفتوحة. لتفعيل التحميلات، افتحها من زر TeleDrive Next في خلية الربط داخل Colab."}
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
