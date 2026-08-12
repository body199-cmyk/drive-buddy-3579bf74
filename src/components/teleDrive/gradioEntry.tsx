import { createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import TeleDriveSandbox from "./TeleDriveSandbox";
import { GradioTeleDriveBridge, type GradioComponentHost } from "./gradioBridge";
import "./teleDrive.css";

type MountOptions = GradioComponentHost & {
  element: HTMLElement;
};

export type MountedTeleDrivePanel = {
  receive(value: unknown): void;
  dispose(): void;
};

export function mount(options: MountOptions): MountedTeleDrivePanel {
  const bridge = new GradioTeleDriveBridge(options);
  let root: Root | null = null;
  let mountedNode: HTMLElement | null = null;

  const ensureMounted = () => {
    const nextNode = options.element.querySelector<HTMLElement>("[data-teledrive-react-root]");
    if (!nextNode || nextNode === mountedNode) return;
    root?.unmount();
    mountedNode = nextNode;
    root = createRoot(nextNode);
    root.render(createElement(TeleDriveSandbox, { bridge }));
  };

  ensureMounted();
  return {
    receive(value: unknown) {
      ensureMounted();
      bridge.receive(value);
    },
    dispose() {
      bridge.dispose();
      root?.unmount();
      root = null;
      mountedNode = null;
    },
  };
}
