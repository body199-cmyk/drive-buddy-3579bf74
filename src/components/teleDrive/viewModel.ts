/* eslint-disable prettier/prettier -- Prettier 3.8 and 3.9 wrap this union differently */
import type { BridgeLanguage, CandidateRow, LiveUiState, QueueRow } from "./bridgeTypes";

export type Page = "connection" | "analyze" | "queue" | "logs" | "settings";
export type ScanMode = "message" | "range" | "latest" | "chat";
export type MediaType =
  "all" | "video" | "photo" | "document" | "audio" | "voice" | "animation" | "sticker";

export const pageLabels: Record<Page, Record<BridgeLanguage, string>> = {
  connection: { ar: "مركز الاتصال", en: "Connection" },
  analyze: { ar: "التحليل والاختيار", en: "Analyze & select" },
  queue: { ar: "التحويلات", en: "Transfers" },
  logs: { ar: "السجلات", en: "Logs" },
  settings: { ar: "الإعدادات", en: "Settings" },
};

export const scanModes: Array<{
  value: ScanMode;
  label: Record<BridgeLanguage, string>;
}> = [
  { value: "message", label: { ar: "رسالة واحدة", en: "Single message" } },
  { value: "range", label: { ar: "نطاق محدود", en: "Limited range" } },
  { value: "latest", label: { ar: "أحدث الرسائل", en: "Latest messages" } },
  { value: "chat", label: { ar: "حتى 1000 رسالة", en: "Up to 1,000 messages" } },
];

export const mediaChoices: Array<{
  value: MediaType;
  label: Record<BridgeLanguage, string>;
}> = [
  { value: "all", label: { ar: "الكل", en: "All" } },
  { value: "video", label: { ar: "فيديو", en: "Video" } },
  { value: "photo", label: { ar: "صور", en: "Photos" } },
  { value: "document", label: { ar: "مستندات", en: "Documents" } },
  { value: "audio", label: { ar: "صوت", en: "Audio" } },
  { value: "voice", label: { ar: "رسائل صوتية", en: "Voice" } },
  { value: "animation", label: { ar: "صور متحركة", en: "Animation" } },
  { value: "sticker", label: { ar: "ملصقات", en: "Stickers" } },
];

export function localize(language: BridgeLanguage, ar: string, en: string): string {
  return language === "ar" ? ar : en;
}

export function formatBytes(bytes: number | null): string {
  if (bytes === null) return "—";
  if (bytes < 1) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const unit = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** unit;
  return `${value >= 10 || unit === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[unit]}`;
}

export function visibleCandidates(
  candidates: CandidateRow[],
  mediaTypes: MediaType[],
): CandidateRow[] {
  return candidates.filter(
    (candidate) =>
      mediaTypes.includes("all") || mediaTypes.includes(candidate.mediaType as MediaType),
  );
}

export function selectableCandidates(candidates: CandidateRow[]): CandidateRow[] {
  return candidates.filter(
    (candidate) =>
      !["quarantined", "deleted", "stopped"].includes((candidate.status ?? "").toLowerCase()),
  );
}

export function selectedVisibleCandidates(candidates: CandidateRow[]): CandidateRow[] {
  return selectableCandidates(candidates).filter((candidate) => candidate.selected);
}

export function enqueueBlockReason(
  state: LiveUiState | null,
  visible: CandidateRow[],
): "bridge" | "folder" | "selection" | null {
  if (!state) return "bridge";
  if (!state.folder?.id) return "folder";
  if (selectedVisibleCandidates(visible).length < 1) return "selection";
  return null;
}

export type QueueMetrics = {
  queued: number;
  running: number;
  uploaded: number;
  failed: number;
  transferredBytes: number;
};

export type QueueSession = {
  key: string;
  title: string;
  dateLabel: string;
  rows: QueueRow[];
  uploaded: number;
  pending: number;
};

export function groupQueueSessions(queue: QueueRow[]): QueueSession[] {
  const groups = new Map<string, QueueSession>();
  for (const row of queue) {
    const title = (row.chatTitle ?? "").trim() || "—";
    const dateLabel = (row.createdAt ?? "").slice(0, 10) || "—";
    const key = `${title} · ${dateLabel}`;
    const current = groups.get(key) ?? {
      key,
      title,
      dateLabel,
      rows: [],
      uploaded: 0,
      pending: 0,
    };
    const status = (row.status ?? "").toLowerCase();
    current.rows.push(row);
    current.uploaded += status === "uploaded" ? 1 : 0;
    current.pending += ["pending", "needsretry", "downloaded"].includes(status) ? 1 : 0;
    groups.set(key, current);
  }
  return [...groups.values()];
}

export function queueMetrics(queue: QueueRow[]): QueueMetrics {
  return queue.reduce<QueueMetrics>(
    (metrics, row) => {
      const status = (row.status ?? "").toLowerCase();
      return {
        queued: metrics.queued + (["pending", "needsretry", "downloaded"].includes(status) ? 1 : 0),
        running:
          metrics.running + (["downloading", "uploading", "verifying"].includes(status) ? 1 : 0),
        uploaded: metrics.uploaded + (status === "uploaded" ? 1 : 0),
        failed: metrics.failed + (status === "failed" ? 1 : 0),
        transferredBytes:
          metrics.transferredBytes + (status === "uploaded" ? (row.sizeBytes ?? 0) : 0),
      };
    },
    { queued: 0, running: 0, uploaded: 0, failed: 0, transferredBytes: 0 },
  );
}

export function isPositiveInteger(value: string): boolean {
  const numeric = Number(value);
  return Number.isInteger(numeric) && numeric > 0;
}

export function validateAnalyzeInput(input: {
  sourceLink: string;
  mode: ScanMode;
  messageId: string;
  rangeFrom: string;
  rangeTo: string;
  limit: string;
}): string | null {
  if (!input.sourceLink.trim()) return "source";
  if (input.mode === "message" && !isPositiveInteger(input.messageId)) return "message";
  if (input.mode === "range") {
    if (!isPositiveInteger(input.rangeFrom) || !isPositiveInteger(input.rangeTo)) return "range";
    const from = Number(input.rangeFrom);
    const to = Number(input.rangeTo);
    if (to < from || to - from + 1 > 1000) return "range";
  }
  if (["latest", "chat"].includes(input.mode)) {
    if (!isPositiveInteger(input.limit) || Number(input.limit) > 1000) return "limit";
  }
  return null;
}
