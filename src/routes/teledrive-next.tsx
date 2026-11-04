import { createFileRoute } from "@tanstack/react-router";
import TeleDriveNext from "../components/teleDrive/TeleDriveNext";
import sandboxCss from "../components/teleDrive/teleDriveNext.css?url";

export const Route = createFileRoute("/teledrive-next")({
  head: () => ({
    meta: [
      { title: "TeleDrive Next — UI Preview" },
      {
        name: "description",
        content:
          "Experimental TeleDrive third workspace. Connect to your own Colab runtime for live actions.",
      },
    ],
    links: [{ rel: "stylesheet", href: sandboxCss }],
  }),
  component: () => <TeleDriveNext />,
});
