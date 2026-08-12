export type BridgeLanguage = "ar" | "en";
export type BridgeStatus = "ok" | "error" | "blocked" | "unauthorized";
export type BridgeTheme = "light" | "dark";

export type BridgeRequest = {
  requestId: string;
  actionId: string;
  payload: Record<string, unknown>;
  language: BridgeLanguage;
};

export type QueueRow = {
  id: string;
  name: string;
  status: string;
  progress: number;
  sizeBytes: number | null;
  speedBytes: number | null;
  remainingSeconds: number | null;
  chatTitle?: string | null;
  createdAt?: string | null;
};

export type CandidateRow = {
  sourceId: string;
  name: string;
  mediaType: string;
  sizeBytes: number | null;
  groupLabel: string | null;
  dateLabel: string | null;
  selected: boolean;
  status: string;
};

export type FolderChoice = {
  id: string;
  name: string;
};

export type LiveUiState = {
  language: BridgeLanguage;
  theme: BridgeTheme;
  telegram: {
    status: string;
    accountLabel: string | null;
  };
  drive: {
    status: string;
    accountLabel: string | null;
    quotaUsed: number | null;
    quotaLimit: number | null;
  };
  folder: {
    id: string | null;
    name: string | null;
  };
  engine: string;
  concurrency: number;
  queue: QueueRow[];
  candidates: CandidateRow[];
};

export type BridgeResponse<T = unknown> = {
  requestId: string;
  actionId: string;
  status: BridgeStatus;
  data?: T;
  errorKey?: string;
  message?: string;
  state?: LiveUiState;
};

export interface TeleDriveBridge {
  request<T>(request: BridgeRequest): Promise<BridgeResponse<T>>;
  subscribe(listener: (state: LiveUiState) => void): () => void;
  isLive(): boolean;
}

export function assertBridgeResponse<T>(
  response: BridgeResponse<T>,
): asserts response is BridgeResponse<T> & { status: "ok" } {
  if (response.status !== "ok") {
    throw new Error(response.message ?? response.errorKey ?? "Bridge request failed");
  }
}

let fallbackRequestSequence = 0;

export function newRequestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  fallbackRequestSequence += 1;
  return `td-${Date.now()}-${fallbackRequestSequence}`;
}

export const unavailableBridge: TeleDriveBridge = {
  isLive: () => false,
  subscribe: () => () => undefined,
  request: async <T>(request: BridgeRequest): Promise<BridgeResponse<T>> => ({
    requestId: request.requestId,
    actionId: request.actionId,
    status: "blocked",
    errorKey: "bridge.unavailable",
    message: "Backend bridge unavailable",
  }),
};
