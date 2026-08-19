import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { gunzipSync } from "node:zlib";

import { unavailableBridge } from "../src/components/teleDrive/bridgeTypes.ts";
import { GradioTeleDriveBridge } from "../src/components/teleDrive/gradioBridge.ts";
import {
  enqueueBlockReason,
  formatBytes,
  groupQueueSessions,
  hasActiveTransfer,
  queueMetrics,
  selectableCandidates,
  validateAnalyzeInput,
} from "../src/components/teleDrive/viewModel.ts";

const paths = {
  route: new URL("../src/routes/teledrive-sandbox.tsx", import.meta.url),
  component: new URL("../src/components/teleDrive/TeleDriveSandbox.tsx", import.meta.url),
  bridgeTypes: new URL("../src/components/teleDrive/bridgeTypes.ts", import.meta.url),
  gradioBridge: new URL("../src/components/teleDrive/gradioBridge.ts", import.meta.url),
  css: new URL("../src/components/teleDrive/teleDrive.css", import.meta.url),
  panel: new URL("../python-package/teledrive/react_panel.py", import.meta.url),
  panelAsset: new URL(
    "../python-package/teledrive/react_panel_assets/panel.bundle.gz",
    import.meta.url,
  ),
  registry: new URL("../python-package/teledrive/action_registry.py", import.meta.url),
};

const emptyState = {
  language: "ar",
  theme: "light",
  telegram: { status: "DISCONNECTED", accountLabel: null },
  drive: { status: "DISCONNECTED", accountLabel: null, quotaUsed: null, quotaLimit: null },
  folder: { id: null, name: null },
  engine: "idle",
  concurrency: 2,
  queue: [],
  candidates: [],
};

function hostWith(value) {
  const writes = [];
  let submissions = 0;
  return {
    writes,
    get submissions() {
      return submissions;
    },
    readValue: () => value,
    writeValue: (next) => writes.push(next),
    submit: () => {
      submissions += 1;
    },
  };
}

test("01 — sandbox route renders the component and is never blank", async () => {
  const route = await readFile(paths.route, "utf8");
  assert.match(route, /return\s+<TeleDriveSandbox\s*\/>/);
  assert.doesNotMatch(route, /function TeleDriveSandboxPage\(\)\s*\{\s*return;\s*\}/);
  assert.doesNotMatch(route, /return\s+null/);
});

test("02 — route metadata describes the operational Gradio bridge without remote fonts", async () => {
  const route = await readFile(paths.route, "utf8");
  assert.match(route, /TeleDrive operational UI running inside the official Gradio bridge/);
  assert.doesNotMatch(route, /fonts\.googleapis\.com|https?:\/\//);
});

test("03 — unavailable bridge blocks rather than reporting local success", async () => {
  const response = await unavailableBridge.request({
    requestId: "blocked-1",
    actionId: "queue.start_selected",
    payload: {},
    language: "ar",
  });
  assert.equal(unavailableBridge.isLive(), false);
  assert.equal(response.status, "blocked");
  assert.equal(response.errorKey, "bridge.unavailable");
});

test("04 — Gradio adapter submits the exact bridge request shape", async () => {
  const host = hostWith("");
  const bridge = new GradioTeleDriveBridge(host);
  const request = {
    requestId: "request-4",
    actionId: "queue.refresh",
    payload: { marker: 1 },
    language: "en",
  };
  const pending = bridge.request(request);
  assert.deepEqual(JSON.parse(host.writes[0]), request);
  assert.equal(host.submissions, 1);
  bridge.receive({ ...request, status: "ok", state: emptyState });
  assert.equal((await pending).status, "ok");
  bridge.dispose();
});

test("05 — bridge response errors resolve the matching request without fake success", async () => {
  const host = hostWith("");
  const bridge = new GradioTeleDriveBridge(host);
  const pending = bridge.request({
    requestId: "request-5",
    actionId: "drive.connect",
    payload: {},
    language: "ar",
  });
  bridge.receive({
    requestId: "request-5",
    actionId: "drive.connect",
    status: "error",
    errorKey: "bridge.action_failed",
    message: "Action failed [cid123]",
  });
  const response = await pending;
  assert.equal(response.status, "error");
  assert.match(response.message, /cid123/);
  bridge.dispose();
});

test("06 — subscribed live snapshots update from the official component value", () => {
  const host = hostWith(
    JSON.stringify({
      requestId: "initial",
      actionId: "bridge.snapshot",
      status: "ok",
      state: emptyState,
    }),
  );
  const bridge = new GradioTeleDriveBridge(host);
  const snapshots = [];
  bridge.subscribe((state) => snapshots.push(state));
  bridge.receive({
    requestId: "next",
    actionId: "queue.refresh",
    status: "ok",
    state: { ...emptyState, engine: "running" },
  });
  assert.deepEqual(
    snapshots.map((state) => state.engine),
    ["idle", "running"],
  );
  bridge.dispose();
});

test("07 — analyze validation uses only the real bounded scanner modes", () => {
  assert.equal(
    validateAnalyzeInput({
      sourceLink: "https://t.me/example/1",
      mode: "message",
      messageId: "1",
      rangeFrom: "",
      rangeTo: "",
      limit: "100",
    }),
    null,
  );
  assert.equal(
    validateAnalyzeInput({
      sourceLink: "https://t.me/example",
      mode: "range",
      messageId: "",
      rangeFrom: "1",
      rangeTo: "1001",
      limit: "100",
    }),
    "range",
  );
});

test("08 — quarantined/final candidates remain visible but are not selectable", () => {
  const rows = [
    { sourceId: "a", status: "Pending" },
    { sourceId: "b", status: "Quarantined" },
    { sourceId: "c", status: "Stopped" },
  ];
  assert.deepEqual(
    selectableCandidates(rows).map((row) => row.sourceId),
    ["a"],
  );
});

test("09 — enqueue gate blocks when no live snapshot exists", () => {
  assert.equal(enqueueBlockReason(null, []), "bridge");
});

test("10 — enqueue gate blocks until Python has a real folder ID", () => {
  const candidate = { sourceId: "a", status: "Pending", selected: true };
  assert.equal(enqueueBlockReason(emptyState, [candidate]), "folder");
});

test("11 — enqueue gate requires a selected transferable candidate", () => {
  const withFolder = { ...emptyState, folder: { id: "folder-id", name: "Folder" } };
  assert.equal(
    enqueueBlockReason(withFolder, [{ sourceId: "a", status: "Pending", selected: false }]),
    "selection",
  );
  assert.equal(
    enqueueBlockReason(withFolder, [{ sourceId: "a", status: "Pending", selected: true }]),
    null,
  );
});

test("12 — queue metrics and transferred bytes derive only from live rows", () => {
  const base = {
    id: "item",
    name: "file",
    progress: 0,
    sizeBytes: 1024,
    speedBytes: null,
    remainingSeconds: null,
  };
  assert.deepEqual(
    queueMetrics([
      { ...base, id: "q", status: "Pending" },
      { ...base, id: "r", status: "Uploading" },
      { ...base, id: "u", status: "Uploaded" },
      { ...base, id: "f", status: "Failed" },
    ]),
    { queued: 1, running: 1, uploaded: 1, failed: 1, transferredBytes: 1024 },
  );
  assert.equal(formatBytes(1024), "1.0 KB");
});

test("13 — production React source contains no demo rows, folders, quotas, or logs", async () => {
  const component = await readFile(paths.component, "utf8");
  assert.doesNotMatch(
    component,
    /DEMO_FOLDERS|initialFiles|SAMPLE_LOGS|18\.4 GB|42\.7%|Local demo|fake success/i,
  );
});

test("14 — every React operational action ID exists in the Python registry", async () => {
  const [component, registry] = await Promise.all([
    readFile(paths.component, "utf8"),
    readFile(paths.registry, "utf8"),
  ]);
  const used = new Set([...component.matchAll(/actionId="([a-z_.]+)"/g)].map((match) => match[1]));
  assert.ok(used.size > 20);
  for (const actionId of used) {
    assert.match(registry, new RegExp(`action_id="${actionId.replaceAll(".", "\\.")}"`));
  }
});

test("15 — browser boundary has no manual network or secret storage transport", async () => {
  const sources = await Promise.all([
    readFile(paths.component, "utf8"),
    readFile(paths.bridgeTypes, "utf8"),
    readFile(paths.gradioBridge, "utf8"),
  ]);
  const source = sources.join("\n");
  assert.doesNotMatch(source, /\b(fetch|XMLHttpRequest|WebSocket)\s*\(/);
  assert.doesNotMatch(source, /\b(localStorage|sessionStorage)\s*\./);
  assert.doesNotMatch(source, /\/api\//);
});

test("16 — language direction comes from live state without resetting it", async () => {
  const component = await readFile(paths.component, "utf8");
  assert.match(component, /liveState\?\.language \?\? "ar"/);
  assert.match(component, /dir=\{language === "ar" \? "rtl" : "ltr"\}/);
  assert.match(component, /bridge\.subscribe\(setLiveState\)/);
});

test("17 — responsive and blocked/live CSS contracts are present", async () => {
  const css = await readFile(paths.css, "utf8");
  assert.match(css, /overflow-x: hidden/);
  assert.match(css, /\.td-status-live/);
  assert.match(css, /\.td-status-demo/);
  assert.match(css, /\.td-bridge-blocked/);
  assert.match(css, /@media \(max-width: 768px\)/);
  assert.match(css, /@media \(max-width: 620px\)/);
});

test("18 — bundled React panel uses Gradio value/submit transport only", async () => {
  const [panel, asset] = await Promise.all([
    readFile(paths.panel, "utf8"),
    readFile(paths.panelAsset),
  ]);
  assert.match(panel, /class ReactPanel\(gr\.HTML\)/);
  assert.match(panel, /trigger\('submit'\)/);
  assert.match(panel, /watch\('value'/);
  assert.ok(asset.length > 10_000);
  assert.deepEqual([...asset.subarray(0, 2)], [0x1f, 0x8b]);
});

test("19 — nested LiveUiState fields use optional chaining (null safety)", async () => {
  const component = await readFile(paths.component, "utf8");
  // Nested optional access — never crash when telegram/drive/folder is missing.
  assert.match(component, /state\?\.telegram\?\.status/);
  assert.match(component, /state\?\.drive\?\.status/);
  assert.match(component, /state\?\.folder\?\.name/);
  assert.match(component, /state\?\.folder\?\.id/);
  assert.match(component, /state\?\.drive\?\.quotaUsed/);
  assert.match(component, /state\?\.drive\?\.status\?\.toLowerCase/);
  // Forbidden: one-level optional then bare nested property (throws if parent is undefined).
  assert.doesNotMatch(component, /state\?\.telegram\.[a-zA-Z]/);
  assert.doesNotMatch(component, /state\?\.drive\.[a-zA-Z]/);
  assert.doesNotMatch(component, /state\?\.folder\.[a-zA-Z]/);
});

test("21 — queue sessions group by channel title and created date", () => {
  const base = {
    name: "file",
    progress: 0,
    sizeBytes: 10,
    speedBytes: null,
    remainingSeconds: null,
  };
  const sessions = groupQueueSessions([
    { ...base, id: "a", status: "Pending", chatTitle: "Alpha", createdAt: "2026-08-12T01:00:00" },
    { ...base, id: "b", status: "Uploaded", chatTitle: "Alpha", createdAt: "2026-08-12T02:00:00" },
    { ...base, id: "c", status: "Pending", chatTitle: "Beta", createdAt: "2026-08-11T09:00:00" },
  ]);
  assert.equal(sessions.length, 2);
  assert.equal(sessions[0].title, "Alpha");
  assert.equal(sessions[0].dateLabel, "2026-08-12");
  assert.equal(sessions[0].rows.length, 2);
  assert.equal(sessions[0].uploaded, 1);
  assert.equal(sessions[0].pending, 1);
  assert.equal(sessions[1].title, "Beta");
});

test("22 — stop offers clear-incomplete and queue rows render in sessions", async () => {
  const component = await readFile(paths.component, "utf8");
  assert.match(component, /queue\.clear_incomplete/);
  assert.match(component, /setStopConfirm\(true\)/);
  assert.match(component, /groupQueueSessions/);
  assert.match(component, /td-session/);
});

test("20 — run() drops stale responses via latestRequest Map", async () => {
  const component = await readFile(paths.component, "utf8");
  assert.match(component, /latestRequest\s*=\s*useRef\(new Map/);
  assert.match(component, /latestRequest\.current\.set\(actionId,\s*requestId\)/);
  assert.match(component, /latestRequest\.current\.get\(actionId\)\s*!==\s*requestId/);
  // Success notice only after status === "ok" (still present) and after stale guard.
  assert.match(component, /if \(response\.status !== "ok"\)/);
  assert.match(component, /kind:\s*"success"/);
});

test("23 — hasActiveTransfer gates the heartbeat on real progress only", () => {
  assert.equal(hasActiveTransfer(null), false);
  assert.equal(hasActiveTransfer(emptyState), false);
  assert.equal(hasActiveTransfer({ ...emptyState, engine: "running" }), true);
  assert.equal(
    hasActiveTransfer({ ...emptyState, queue: [{ id: "a", status: "Uploading" }] }),
    true,
  );
  // Terminal rows alone must never keep polling a finished queue.
  assert.equal(
    hasActiveTransfer({
      ...emptyState,
      queue: [
        { id: "a", status: "Uploaded" },
        { id: "b", status: "Failed" },
      ],
    }),
    false,
  );
  // A paused engine with nothing in flight stops the heartbeat.
  assert.equal(
    hasActiveTransfer({
      ...emptyState,
      engine: "paused",
      queue: [{ id: "a", status: "Paused" }],
    }),
    false,
  );
});

test("24 — sandbox auto-refreshes the whole live snapshot while transferring", async () => {
  const component = await readFile(paths.component, "utf8");
  assert.match(component, /AUTO_REFRESH_INTERVAL_MS/);
  assert.match(component, /setInterval/);
  assert.match(component, /hasActiveTransfer/);
  assert.match(component, /actionId:\s*"queue\.refresh"/);
  // Silent heartbeat: talks to the bridge directly, never through run()
  // (which would flash busy spinners and success notices every tick).
  assert.match(component, /bridge\s*\.\s*request\(\{/);
  assert.match(component, /pollInFlight/);
  // Replaces the full LiveUiState from the response, like a manual Refresh.
  assert.match(component, /setLiveState\(response\.state\)/);
});

test("25 — shipped panel bundle includes the auto-refresh heartbeat", async () => {
  const asset = await readFile(paths.panelAsset);
  const bundle = gunzipSync(asset).toString("utf8");

  assert.match(bundle, /TeleDriveGradioPanel/);
  assert.match(bundle, /setInterval/);
  assert.match(bundle, /queue\.refresh/);
  // Gradio injects this IIFE straight into a browser scope; Node's process
  // global is unavailable there and would prevent the panel from mounting.
  assert.doesNotMatch(bundle, /process\.env\.NODE_ENV/);
});

test("26 — transfer toolbar and row controls preserve every real action ID", async () => {
  const component = await readFile(paths.component, "utf8");
  const queueActions = new Set(
    [...component.matchAll(/actionId="(queue\.[a-z_]+)"/g)].map((match) => match[1]),
  );

  assert.deepEqual([...queueActions].sort(), [
    "queue.clear_completed",
    "queue.clear_incomplete",
    "queue.pause",
    "queue.pause_item",
    "queue.refresh",
    "queue.resume",
    "queue.resume_item",
    "queue.retry_failed",
    "queue.retry_item",
    "queue.start_selected",
    "queue.stop",
  ]);
});
