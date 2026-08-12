/* eslint-disable prettier/prettier -- bun CI prettier wraps Arabic strings differently than local npm prettier */
export type Page = "connection" | "analyze" | "queue" | "logs" | "settings";
export type ScanMode = "message" | "group" | "range" | "latest" | "chat";
export type MediaType = "all" | "video" | "photo" | "document" | "audio" | "voice";
export type Language = "ar" | "en";
export type Theme = "light" | "dark";
export type FileStatus =
  | "new"
  | "duplicate"
  | "quarantined"
  | "queued"
  | "running"
  | "uploaded"
  | "failed";

export type MockFile = {
  id: string;
  name: string;
  meta: string;
  type: Exclude<MediaType, "all">;
  size: string;
  sizeBytes: number | null;
  date: string;
  status: FileStatus;
  progress: number;
  speed: string;
  remaining: string;
  selected: boolean;
};

export type Notice = { kind: "info" | "success" | "warning" | "error"; text: string } | null;

export type SandboxState = {
  page: Page;
  language: Language;
  theme: Theme;
  telegramConnected: boolean;
  driveConnected: boolean;
  folder: string | null;
  engine: "stopped" | "running" | "paused";
  concurrency: number;
  sourceLink: string;
  scanMode: ScanMode;
  mediaTypes: MediaType[];
  messageId: string;
  rangeFrom: string;
  rangeTo: string;
  latestLimit: string;
  analyzed: boolean;
  files: MockFile[];
  queue: MockFile[];
  notice: Notice;
};

/**
 * Optional future API boundary. Intentionally unused in M23.
 * Do not implement or wire this type to the production Python application.
 */
export type TeleDriveGateway = {
  getStatus(): Promise<unknown>;
  analyze(input: unknown): Promise<unknown>;
  enqueue(input: unknown): Promise<unknown>;
  start(): Promise<unknown>;
};

export const MIN_CONCURRENCY = 1;
export const MAX_CONCURRENCY = 4;
export const DEFAULT_CONCURRENCY = 2;

export const DEMO_FOLDERS = [
  "TeleDrive / أرشيف القناة",
  "TeleDrive / النسخ الاحتياطي",
  "My Drive / وسائط",
] as const;

export const initialFiles: MockFile[] = [
  {
    id: "7d2a91",
    name: "لقاء_الافتتاح_1080p.mp4",
    meta: "msg 845 · id 7d2a91",
    type: "video",
    size: "1.42 GB",
    sizeBytes: 1_524_714_721,
    date: "2026-08-09",
    status: "new",
    progress: 0,
    speed: "",
    remaining: "",
    selected: true,
  },
  {
    id: "7d2a92",
    name: "الجلسة_الثانية.mp4",
    meta: "msg 846 · id 7d2a92",
    type: "video",
    size: "870 MB",
    sizeBytes: 912_261_120,
    date: "2026-08-09",
    status: "new",
    progress: 0,
    speed: "",
    remaining: "",
    selected: false,
  },
  {
    id: "7d2a93",
    name: "العرض_التقديمي.pdf",
    meta: "msg 847 · id 7d2a93",
    type: "document",
    size: "18.4 MB",
    sizeBytes: 19_293_798,
    date: "2026-08-09",
    status: "new",
    progress: 0,
    speed: "",
    remaining: "",
    selected: true,
  },
  {
    id: "7d2a94",
    name: "صورة_المجموعة.jpg",
    meta: "msg 848 · id 7d2a94",
    type: "photo",
    size: "4.1 MB",
    sizeBytes: 4_299_162,
    date: "2026-08-09",
    status: "duplicate",
    progress: 100,
    speed: "",
    remaining: "",
    selected: true,
  },
  {
    id: "7d2a95",
    name: "تسجيل_صوتي.m4a",
    meta: "msg 849 · id 7d2a95",
    type: "audio",
    size: "62 MB",
    sizeBytes: 65_011_712,
    date: "2026-08-10",
    status: "new",
    progress: 0,
    speed: "",
    remaining: "",
    selected: false,
  },
  {
    id: "850",
    name: "ملحق_غير_مكتمل.part",
    meta: "مصدر مجهول · msg 850",
    type: "document",
    size: "—",
    sizeBytes: null,
    date: "2026-08-10",
    status: "quarantined",
    progress: 0,
    speed: "",
    remaining: "",
    selected: false,
  },
];

export const initialState: SandboxState = {
  page: "analyze",
  language: "ar",
  theme: "light",
  telegramConnected: false,
  driveConnected: false,
  folder: null,
  engine: "stopped",
  concurrency: DEFAULT_CONCURRENCY,
  sourceLink: "https://t.me/demo_channel/845",
  scanMode: "message",
  mediaTypes: ["all"],
  messageId: "845",
  rangeFrom: "845",
  rangeTo: "850",
  latestLimit: "100",
  analyzed: true,
  files: initialFiles,
  queue: [],
  notice: {
    kind: "info",
    text: "نموذج محلي فقط، لا يوجد اتصال فعلي بتيليجرام أو جوجل درايف.",
  },
};

type LocalizedText = Record<Language, string>;

export function localize(language: Language, ar: string, en: string): string {
  return language === "ar" ? ar : en;
}

export const pageLabels: Record<Page, LocalizedText> = {
  connection: { ar: "مركز الاتصال", en: "Connection" },
  analyze: { ar: "التحليل والاختيار", en: "Analyze & select" },
  queue: { ar: "التحويلات", en: "Transfers" },
  logs: { ar: "السجلات", en: "Logs" },
  settings: { ar: "الإعدادات", en: "Settings" },
};

export const modes: Array<{ value: ScanMode; label: LocalizedText }> = [
  { value: "message", label: { ar: "رسالة واحدة", en: "Single message" } },
  { value: "group", label: { ar: "الألبوم المرتبط", en: "Related album" } },
  { value: "range", label: { ar: "نطاق محدود", en: "Limited range" } },
  { value: "latest", label: { ar: "أحدث عدد", en: "Latest messages" } },
  { value: "chat", label: { ar: "القناة حتى 1000", en: "Channel up to 1,000" } },
];

export const mediaChoices: Array<{ value: MediaType; label: LocalizedText }> = [
  { value: "all", label: { ar: "الكل", en: "All" } },
  { value: "video", label: { ar: "فيديو", en: "Video" } },
  { value: "photo", label: { ar: "صور", en: "Photos" } },
  { value: "document", label: { ar: "مستندات", en: "Documents" } },
  { value: "audio", label: { ar: "صوت", en: "Audio" } },
  { value: "voice", label: { ar: "صوتيات", en: "Voice" } },
];

export function modeLabel(mode: ScanMode, language: Language = "ar"): string {
  return modes.find((item) => item.value === mode)?.label[language] ?? mode;
}

export function typeLabel(type: MediaType, language: Language = "ar"): string {
  const labels: Record<MediaType, LocalizedText> = {
    all: { ar: "الكل", en: "All" },
    video: { ar: "فيديو", en: "Video" },
    photo: { ar: "صور", en: "Photos" },
    document: { ar: "مستندات", en: "Documents" },
    audio: { ar: "صوت", en: "Audio" },
    voice: { ar: "رسائل صوتية", en: "Voice messages" },
  };
  return labels[type][language];
}

export function statusLabel(status: FileStatus, language: Language = "ar"): string {
  const labels: Record<FileStatus, LocalizedText> = {
    new: { ar: "جديد", en: "New" },
    duplicate: { ar: "مكرر", en: "Duplicate" },
    quarantined: { ar: "معزول", en: "Quarantined" },
    queued: { ar: "منتظر", en: "Queued" },
    running: { ar: "جارٍ", en: "Running" },
    uploaded: { ar: "مرفوع", en: "Uploaded" },
    failed: { ar: "فشل", en: "Failed" },
  };
  return labels[status][language];
}

export function scanHint(mode: ScanMode, language: Language = "ar"): string {
  const hints: Record<ScanMode, LocalizedText> = {
    message: { ar: "رسالة واحدة فقط", en: "One message only" },
    group: { ar: "الرسالة مع الألبوم المرتبط", en: "The message and its related album" },
    range: {
      ar: "مدى محدود، الحد الأقصى 1000 رسالة",
      en: "A limited range of up to 1,000 messages",
    },
    latest: {
      ar: "أحدث عدد من الرسائل، الحد الأقصى 1000",
      en: "The latest messages, up to 1,000",
    },
    chat: {
      ar: "تحذير: فحص القناة محدود بـ 1000 رسالة، وليس فحصًا غير محدود.",
      en: "Warning: the channel scan is limited to 1,000 messages.",
    },
  };
  return hints[mode][language];
}

export function isValidPhone(value: string): boolean {
  return /^\+?[0-9]{8,15}$/.test(value.replace(/[\s()-]/g, ""));
}

export function isValidCode(value: string): boolean {
  return /^[0-9]{5,6}$/.test(value.trim());
}

export function isPositiveInteger(value: string): boolean {
  const number = Number(value);
  return Number.isInteger(number) && number > 0;
}

export function visibleFiles(files: MockFile[], mediaTypes: MediaType[]): MockFile[] {
  return files.filter((file) => mediaTypes.includes("all") || mediaTypes.includes(file.type));
}

export function setVisibleSelection(
  files: MockFile[],
  mediaTypes: MediaType[],
  selected: boolean,
): MockFile[] {
  const visibleIds = new Set(visibleFiles(files, mediaTypes).map((file) => file.id));
  return files.map((file) =>
    visibleIds.has(file.id) && file.status !== "quarantined" ? { ...file, selected } : file,
  );
}

export function transferableSelection(files: MockFile[]): MockFile[] {
  return files.filter((file) => file.selected && file.status !== "quarantined");
}

export function enqueueBlockReason(
  folder: string | null,
  selectedCount: number,
): "folder" | "selection" | null {
  if (!folder) return "folder";
  if (selectedCount < 1) return "selection";
  return null;
}

export type QueueMetrics = {
  queued: number;
  running: number;
  uploaded: number;
  failed: number;
  transferredBytes: number;
};

export function queueMetrics(queue: MockFile[]): QueueMetrics {
  return queue.reduce<QueueMetrics>(
    (metrics, file) => ({
      queued: metrics.queued + (file.status === "queued" ? 1 : 0),
      running: metrics.running + (file.status === "running" ? 1 : 0),
      uploaded: metrics.uploaded + (file.status === "uploaded" ? 1 : 0),
      failed: metrics.failed + (file.status === "failed" ? 1 : 0),
      transferredBytes:
        metrics.transferredBytes + (file.status === "uploaded" ? (file.sizeBytes ?? 0) : 0),
    }),
    { queued: 0, running: 0, uploaded: 0, failed: 0, transferredBytes: 0 },
  );
}

export function startQueuedFiles(queue: MockFile[], concurrency: number): MockFile[] {
  const safeConcurrency = Math.max(
    MIN_CONCURRENCY,
    Math.min(MAX_CONCURRENCY, Math.trunc(concurrency)),
  );
  let available = Math.max(
    0,
    safeConcurrency - queue.filter((file) => file.status === "running").length,
  );
  return queue.map((file) => {
    if (file.status !== "queued" || available < 1) return file;
    available -= 1;
    return {
      ...file,
      status: "running",
      progress: Math.max(file.progress, 12),
      speed: "14.2 MB/s",
      remaining: "0:34",
    };
  });
}

export function formatBytes(bytes: number): string {
  if (bytes < 1) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const unitIndex = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** unitIndex;
  return `${value >= 10 || unitIndex === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[unitIndex]}`;
}
