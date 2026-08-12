import { createFileRoute } from "@tanstack/react-router";
import TeleDriveSandbox from "../components/teleDrive/TeleDriveSandbox";
import sandboxCss from "../components/teleDrive/teleDrive.css?url";

export const Route = createFileRoute("/teledrive-sandbox")({
  head: () => ({
    meta: [
      { title: "TeleDrive" },
      {
        name: "description",
        content: "TeleDrive operational UI running inside the official Gradio bridge.",
      },
    ],
    links: [{ rel: "stylesheet", href: sandboxCss }],
  }),
  component: TeleDriveSandboxPage,
});

function TeleDriveSandboxPage() {
  return <TeleDriveSandbox />;
}
