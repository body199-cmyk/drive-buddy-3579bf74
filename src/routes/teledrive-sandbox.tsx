/* eslint-disable prettier/prettier -- bun CI prettier wraps this route file differently than local npm prettier */
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
    links: [
      { rel: "stylesheet", href: sandboxCss },
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap",
      },
    ],
  }),
  component: TeleDriveSandboxPage,
});

function TeleDriveSandboxPage() {
  return <TeleDriveSandbox />;
}
