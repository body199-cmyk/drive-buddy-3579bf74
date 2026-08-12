import { createFileRoute } from "@tanstack/react-router";
import TeleDriveSandbox from "../components/teleDrive/TeleDriveSandbox";

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
  }),
  component: TeleDriveSandboxPage,
});

function TeleDriveSandboxPage() {
  return <TeleDriveSandbox />;
}
