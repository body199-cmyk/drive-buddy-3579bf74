import { createFileRoute } from "@tanstack/react-router";
import TeleDriveSandbox from "../components/teleDrive/TeleDriveSandbox";
import sandboxCss from "../components/teleDrive/teleDrive.css?url";

export const Route = createFileRoute("/teledrive-sandbox")({
  head: () => ({
    meta: [
      { title: "TeleDrive Sandbox — UI prototype only" },
      {
        name: "description",
        content:
          "Local React prototype of the M19 TeleDrive shell. No live Telegram or Drive connection.",
      },
    ],
    links: [{ rel: "stylesheet", href: sandboxCss }],
  }),
  component: TeleDriveSandboxPage,
});

function TeleDriveSandboxPage() {
  return <TeleDriveSandbox />;
}
