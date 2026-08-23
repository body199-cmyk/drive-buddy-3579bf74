import type { BridgeRequest, BridgeResponse, LiveUiState, TeleDriveBridge } from "./bridgeTypes";

export type GradioComponentHost = {
  readValue(): unknown;
  writeValue(value: string): void;
  submit(): void;
};

type PendingRequest = {
  resolve(response: BridgeResponse<unknown>): void;
  timeout: ReturnType<typeof setTimeout>;
  /**
   * Monotonic issue order across ALL bridge requests (heartbeats and control
   * actions alike). Responses whose seq is older than an already-applied newer
   * response are stale: their state is dropped so a late queue.refresh can
   * never clobber the fresher state a control action just applied.
   */
  seq: number;
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
  /** Issue counter: bumped once per request, in call order. */
  private issueSequence = 0;
  /** Watermark: highest request sequence whose response has been applied. */
  private appliedSequence = 0;

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
      const seq = ++this.issueSequence;
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
        seq,
      });
      this.host.writeValue(JSON.stringify(request));
      this.host.submit();
    });
  }

  receive(value: unknown): void {
    const response = parseMessage(value);
    if (!response) return;
    const waiting = this.pending.get(response.requestId);
    if (!waiting) {
      // Unsolicited push (e.g. the initial snapshot): freshest at arrival.
      if (response.state) {
        this.latestState = response.state;
        for (const listener of this.listeners) listener(response.state);
      }
      return;
    }
    clearTimeout(waiting.timeout);
    this.pending.delete(response.requestId);
    if (waiting.seq < this.appliedSequence) {
      // Stale straggler: a NEWER request already applied its response, so this
      // older snapshot must not reach the UI. The caller still gets its
      // acknowledgment — minus the outdated state.
      const { state: _staleState, ...acknowledgment } = response;
      waiting.resolve(acknowledgment as BridgeResponse<unknown>);
      return;
    }
    this.appliedSequence = Math.max(this.appliedSequence, waiting.seq);
    if (response.state) {
      this.latestState = response.state;
      for (const listener of this.listeners) listener(response.state);
    }
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
