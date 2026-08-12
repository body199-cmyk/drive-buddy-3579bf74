import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  DEFAULT_CONCURRENCY,
  MAX_CONCURRENCY,
  MIN_CONCURRENCY,
  enqueueBlockReason,
  formatBytes,
  initialFiles,
  initialState,
  isPositiveInteger,
  isValidCode,
  isValidPhone,
  queueMetrics,
  setVisibleSelection,
  startQueuedFiles,
  transferableSelection,
  visibleFiles,
} from "../src/components/teleDrive/mockState.ts";

const componentPath = new URL("../src/components/teleDrive/TeleDriveSandbox.tsx", import.meta.url);
const mockStatePath = new URL("../src/components/teleDrive/mockState.ts", import.meta.url);
const cssPath = new URL("../src/components/teleDrive/teleDrive.css", import.meta.url);
const routePath = new URL("../src/routes/teledrive-sandbox.tsx", import.meta.url);

function queuedCopies(count = 5) {
  return Array.from({ length: count }, (_, index) => ({
    ...initialFiles[index % initialFiles.length],
    id: `queued-${index}`,
    status: "queued",
    selected: true,
    progress: 0,
  }));
}

test("01 — sandbox defaults are local, Arabic, light, and stopped", () => {
  assert.equal(initialState.language, "ar");
  assert.equal(initialState.theme, "light");
  assert.equal(initialState.engine, "stopped");
  assert.equal(initialState.queue.length, 0);
});

test("02 — concurrency contract is 1..4 with default 2", () => {
  assert.equal(MIN_CONCURRENCY, 1);
  assert.equal(DEFAULT_CONCURRENCY, 2);
  assert.equal(initialState.concurrency, 2);
  assert.equal(MAX_CONCURRENCY, 4);
});

test("03 — phone validation accepts normalized international-style numbers", () => {
  assert.equal(isValidPhone("+966 50 123 4567"), true);
  assert.equal(isValidPhone("0501234567"), true);
});

test("04 — phone validation rejects empty and malformed values", () => {
  assert.equal(isValidPhone(""), false);
  assert.equal(isValidPhone("phone-number"), false);
  assert.equal(isValidPhone("123"), false);
});

test("05 — verification code must contain 5 or 6 digits", () => {
  assert.equal(isValidCode("12345"), true);
  assert.equal(isValidCode("123456"), true);
  assert.equal(isValidCode("1234"), false);
  assert.equal(isValidCode("12a45"), false);
});

test("06 — scan numeric fields require positive integers", () => {
  assert.equal(isPositiveInteger("1"), true);
  assert.equal(isPositiveInteger("1000"), true);
  assert.equal(isPositiveInteger("0"), false);
  assert.equal(isPositiveInteger("1.5"), false);
  assert.equal(isPositiveInteger(""), false);
});

test("07 — all media exposes every result", () => {
  assert.equal(visibleFiles(initialFiles, ["all"]).length, initialFiles.length);
});

test("08 — media filters expose only matching result types", () => {
  const files = visibleFiles(initialFiles, ["video", "audio"]);
  assert.ok(files.length > 0);
  assert.ok(files.every((file) => file.type === "video" || file.type === "audio"));
});

test("09 — select all changes visible rows only and excludes quarantine", () => {
  const files = setVisibleSelection(initialFiles, ["document"], true);
  const hiddenVideo = files.find((file) => file.type === "video" && !file.selected);
  const quarantined = files.find((file) => file.status === "quarantined");
  assert.ok(hiddenVideo);
  assert.equal(quarantined?.selected, false);
  assert.ok(
    files
      .filter((file) => file.type === "document" && file.status !== "quarantined")
      .every((file) => file.selected),
  );
});

test("10 — clear selection changes visible rows only", () => {
  const allSelected = initialFiles.map((file) => ({
    ...file,
    selected: file.status !== "quarantined",
  }));
  const files = setVisibleSelection(allSelected, ["document"], false);
  assert.ok(files.filter((file) => file.type === "document").every((file) => !file.selected));
  assert.ok(files.some((file) => file.type === "video" && file.selected));
});

test("11 — transferable selection never contains quarantined files", () => {
  const files = initialFiles.map((file) => ({ ...file, selected: true }));
  const selected = transferableSelection(files);
  assert.ok(selected.length > 0);
  assert.ok(selected.every((file) => file.status !== "quarantined"));
});

test("12 — enqueue is blocked until a destination folder exists", () => {
  assert.equal(enqueueBlockReason(null, 3), "folder");
});

test("13 — enqueue is blocked until at least one transferable row is selected", () => {
  assert.equal(enqueueBlockReason("My Drive / Demo", 0), "selection");
});

test("14 — enqueue gate opens only when folder and selection both exist", () => {
  assert.equal(enqueueBlockReason("My Drive / Demo", 1), null);
});

test("15 — queue metrics are derived from queue item state and uploaded sizes", () => {
  const [queued, running, uploaded, failed] = queuedCopies(4).map((file, index) => ({
    ...file,
    status: ["queued", "running", "uploaded", "failed"][index],
    sizeBytes: index === 2 ? 1024 : file.sizeBytes,
  }));
  assert.deepEqual(queueMetrics([queued, running, uploaded, failed]), {
    queued: 1,
    running: 1,
    uploaded: 1,
    failed: 1,
    transferredBytes: 1024,
  });
});

test("16 — queue start honors concurrency and clamps it to 1..4", () => {
  assert.equal(
    startQueuedFiles(queuedCopies(), DEFAULT_CONCURRENCY).filter(
      (file) => file.status === "running",
    ).length,
    2,
  );
  assert.equal(
    startQueuedFiles(queuedCopies(), 99).filter((file) => file.status === "running").length,
    4,
  );
  assert.equal(
    startQueuedFiles(queuedCopies(), 0).filter((file) => file.status === "running").length,
    1,
  );
});

test("17 — transferred byte formatting has no hard-coded demo total", () => {
  assert.equal(formatBytes(0), "0 B");
  assert.equal(formatBytes(1024), "1.0 KB");
  assert.equal(formatBytes(1024 ** 3), "1.0 GB");
});

test("18 — route and UI remain rendered, isolated, responsive local prototype code", async () => {
  const [route, component, mockState, css] = await Promise.all([
    readFile(routePath, "utf8"),
    readFile(componentPath, "utf8"),
    readFile(mockStatePath, "utf8"),
    readFile(cssPath, "utf8"),
  ]);

  assert.match(route, /return\s+<TeleDriveSandbox\s*\/>/);
  assert.doesNotMatch(route, /fonts\.googleapis\.com|https?:\/\//);
  for (const section of ["connection", "analyze", "queue", "logs", "settings"]) {
    assert.match(component, new RegExp(`id: \\"${section}\\"`));
  }
  assert.match(component, /Prototype · Local demo/);
  assert.match(component, /dir=\{state\.language === "ar" \? "rtl" : "ltr"\}/);
  assert.match(component, /data-theme=\{state\.theme\}/);
  assert.match(css, /@media \(max-width: 768px\)/);
  assert.match(css, /@media \(max-width: 620px\)/);
  assert.doesNotMatch(component, /v4\.5\.0|\/content\/tmp|<strong>37<\/strong>|18\.4 GB<\/strong>/);
  assert.doesNotMatch(`${component}\n${mockState}`, /\b(fetch|XMLHttpRequest|WebSocket)\s*\(/);
  assert.doesNotMatch(component, /from\s+["'][^"']*(gradio|python-package)/i);
});
