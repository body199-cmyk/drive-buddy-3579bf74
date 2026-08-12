export type Page = "connection" | "analyze" | "queue" | "logs" | "settings";
export type ScanMode = "message" | "group" | "range" | "latest" | "chat";
export type MediaType = "all" | "video" | "photo" | "document" | "audio" | "voice";
export type FileStatus =
  "new" | "duplicate" | "quarantined" | "queued" | "running" | "uploaded" | "failed";

export type MockFile = {
  id: string;
  name: string;
  meta: string;
  type: Exclude<MediaType, "all">;
  size: string;
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
  telegramConnected: boolean;
  driveConnected: boolean;
  folder: string | null;
  engine: "stopped" | "running" | "paused";
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
 * Do not implement, fetch, or wire this type to Gradio/Python.
 */
export type TeleDriveGateway = {
  getStatus(): Promise<unknown>;
  analyze(input: unknown): Promise<unknown>;
  enqueue(input: unknown): Promise<unknown>;
  start(): Promise<unknown>;
};

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
  telegramConnected: false,
  driveConnected: false,
  folder: null,
  engine: "stopped",
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

export const pageLabels: Record<Page, string> = {
  connection: "مركز الاتصال",
  analyze: "التحليل والاختيار",
  queue: "التحويلات",
  logs: "السجلات",
  settings: "الإعدادات",
};

export const modes: Array<{ value: ScanMode; label: string }> = [
  { value: "message", label: "رسالة واحدة" },
  { value: "group", label: "الألبوم المرتبط" },
  { value: "range", label: "نطاق محدود" },
  { value: "latest", label: "أحدث عدد" },
  { value: "chat", label: "القناة حتى 1000" },
];

export const mediaChoices: Array<{ value: MediaType; label: string }> = [
  { value: "all", label: "الكل" },
  { value: "video", label: "فيديو" },
  { value: "photo", label: "صور" },
  { value: "document", label: "مستندات" },
  { value: "audio", label: "صوت" },
  { value: "voice", label: "صوتيات" },
];

export function modeLabel(mode: ScanMode): string {
  return {
    message: "رسالة واحدة",
    group: "الألبوم المرتبط",
    range: "نطاق محدود",
    latest: "أحدث عدد",
    chat: "القناة حتى 1000 رسالة",
  }[mode];
}

export function typeLabel(type: MediaType): string {
  return {
    all: "الكل",
    video: "فيديو",
    photo: "صور",
    document: "مستندات",
    audio: "صوت",
    voice: "رسائل صوتية",
  }[type];
}

export function statusLabel(status: FileStatus): string {
  return {
    new: "جديد",
    duplicate: "مكرر",
    quarantined: "معزول",
    queued: "منتظر",
    running: "جارٍ",
    uploaded: "مرفوع",
    failed: "فشل",
  }[status];
}

export function scanHint(mode: ScanMode): string {
  return {
    message: "رسالة واحدة فقط",
    group: "الرسالة مع الألبوم المرتبط",
    range: "مدى محدود، الحد الأقصى 1000 رسالة",
    latest: "أحدث عدد من الرسائل، الحد الأقصى 1000",
    chat: "تحذير: فحص القناة محدود بـ 1000 رسالة، وليس فحصًا غير محدود.",
  }[mode];
}
