import type { BridgeRequest, BridgeResponse, LiveUiState, TeleDriveBridge } from "./bridgeTypes";

export type GradioComponentHost = {
  readValue(): unknown;
  writeValue(value: string): void;
  submit(): void;
};

type PendingRequest = {
  resolve(response: BridgeResponse<unknown>): void;
  timeout: ReturnType<typeof setTimeout>;
};

function parseMessage(value: unknown): BridgeResponse<unknown> | null {
  let parsed = value;
  if (typeof value === "string") {
    try {
      parsed = JSON.parse(value);
    } catch {
      return null;
    }
  }
  if (!parsed || typeof parsed !== "object") return null;
  const candidate = parsed as Partial<BridgeResponse<unknown>>;
  if (
    typeof candidate.requestId !== "string" ||
    typeof candidate.actionId !== "string" ||
    !["ok", "error", "blocked", "unauthorized"].includes(String(candidate.status))
  ) {
    return null;
  }
  return candidate as BridgeResponse<unknown>;
}

export class GradioTeleDriveBridge implements TeleDriveBridge {
  private readonly listeners = new Set<(state: LiveUiState) => void>();
  private readonly pending = new Map<string, PendingRequest>();
  private readonly host: GradioComponentHost;
  private latestState: LiveUiState | null = null;
  private disposed = false;

  constructor(host: GradioComponentHost) {
    this.host = host;
    this.receive(host.readValue());
  }

  isLive(): boolean {
    return !this.disposed;
  }

  subscribe(listener: (state: LiveUiState) => void): () => void {
    this.listeners.add(listener);
    if (this.latestState) listener(this.latestState);
    return () => this.listeners.delete(listener);
  }

  request<T>(request: BridgeRequest): Promise<BridgeResponse<T>> {
    if (this.disposed) {
      return Promise.resolve({
        requestId: request.requestId,
        actionId: request.actionId,
        status: "blocked",
        errorKey: "bridge.unavailable",
        message: "Backend bridge unavailable",
      });
    }
    return new Promise<BridgeResponse<T>>((resolve) => {
      const timeout = setTimeout(() => {
        this.pending.delete(request.requestId);
        resolve({
          requestId: request.requestId,
          actionId: request.actionId,
          status: "error",
          errorKey: "bridge.timeout",
          message: "Backend bridge timed out",
        });
      }, 30_000);
      this.pending.set(request.requestId, {
        resolve: resolve as (response: BridgeResponse<unknown>) => void,
        timeout,
      });
      this.host.writeValue(JSON.stringify(request));
      this.host.submit();
    });
  }

  receive(value: unknown): void {
    const response = parseMessage(value);
    if (!response) return;
    if (response.state) {
      this.latestState = response.state;
      for (const listener of this.listeners) listener(response.state);
    }
    const waiting = this.pending.get(response.requestId);
    if (!waiting) return;
    clearTimeout(waiting.timeout);
    this.pending.delete(response.requestId);
    waiting.resolve(response);
  }

  dispose(): void {
    this.disposed = true;
    for (const [requestId, waiting] of this.pending) {
      clearTimeout(waiting.timeout);
      waiting.resolve({
        requestId,
        actionId: "bridge.dispose",
        status: "blocked",
        errorKey: "bridge.unavailable",
        message: "Backend bridge unavailable",
      });
    }
    this.pending.clear();
    this.listeners.clear();
  }
}
