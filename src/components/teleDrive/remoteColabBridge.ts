import type { BridgeRequest, BridgeResponse, LiveUiState, TeleDriveBridge } from "./bridgeTypes";
import { newRequestId } from "./bridgeTypes";

/**
 * Browser-to-user-owned-Colab bridge. The Vercel portal never proxies or stores
 * the runtime token; requests go directly to the HTTPS Colab proxy.
 */
export class RemoteColabBridge implements TeleDriveBridge {
  private readonly baseUrl: string;
  private readonly token: string;
  private listeners = new Set<(state: LiveUiState) => void>();
  private currentState: LiveUiState | null = null;
  private connected = false;
  private disposed = false;
  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private pollInFlight = false;

  constructor(runtimeUrl: string, token: string) {
    const parsed = new URL(runtimeUrl.trim());
    const host = parsed.hostname.toLowerCase();
    const supportedHost =
      host.endsWith(".googleusercontent.com") ||
      host.endsWith(".prod.colab.dev") ||
      host.endsWith(".colab.google") ||
      host.endsWith(".trycloudflare.com");
    if (
      parsed.protocol !== "https:" ||
      !supportedHost ||
      parsed.username ||
      parsed.password ||
      parsed.search ||
      parsed.hash ||
      (parsed.pathname !== "/" && parsed.pathname !== "")
    ) {
      throw new Error("Enter the HTTPS URL printed by your own Google Colab runtime.");
    }
    if (token.trim().length < 32) {
      throw new Error(
        "The runtime pairing token looks incomplete. Copy the full token from your Colab output.",
      );
    }
    this.baseUrl = parsed.origin;
    this.token = token.trim();
  }

  isLive(): boolean {
    return this.connected && !this.disposed;
  }

  subscribe(listener: (state: LiveUiState) => void): () => void {
    this.listeners.add(listener);
    if (this.currentState) listener(this.currentState);
    return () => this.listeners.delete(listener);
  }

  private publish(state: LiveUiState) {
    this.currentState = state;
    for (const listener of this.listeners) listener(state);
  }

  private async fetchJson(path: string, init: RequestInit = {}) {
    const headers = new Headers(init.headers);
    headers.set("Authorization", `Bearer ${this.token}`);
    if (init.body) headers.set("Content-Type", "application/json");
    const response = await fetch(new URL(path, this.baseUrl + "/").toString(), {
      ...init,
      cache: "no-store",
      mode: "cors",
      credentials: this.baseUrl.toLowerCase().endsWith(".trycloudflare.com") ? "omit" : "include",
      headers,
    });
    if (response.status === 401 || response.status === 403) {
      throw new Error(
        "Pairing rejected. Check the token and make sure it belongs to this running Colab session.",
      );
    }
    if (!response.ok) {
      throw new Error(`Colab runtime returned HTTP ${response.status}.`);
    }
    return response.json();
  }

  async connect(): Promise<void> {
    const health = await this.fetchJson("api/health");
    if (health?.ok !== true || health?.service !== "teledrive-web-dashboard") {
      throw new Error("That URL did not return a TeleDrive runtime.");
    }
    this.connected = true;
    const response = await this.request({
      requestId: newRequestId(),
      actionId: "queue.refresh",
      payload: {},
      language: "ar",
    });
    if (response.status !== "ok" || !response.state) {
      this.connected = false;
      throw new Error(
        response.message ??
          response.errorKey ??
          "The runtime responded, but did not return live TeleDrive state.",
      );
    }
    this.pollTimer = setInterval(() => {
      if (!this.pollInFlight && this.isLive()) {
        this.pollInFlight = true;
        void this.request({
          requestId: newRequestId(),
          actionId: "queue.refresh",
          payload: {},
          language: this.currentState?.language ?? "ar",
        }).finally(() => {
          this.pollInFlight = false;
        });
      }
    }, 3000);
  }

  async request<T>(request: BridgeRequest): Promise<BridgeResponse<T>> {
    if (!this.isLive() && request.actionId !== "queue.refresh") {
      return {
        requestId: request.requestId,
        actionId: request.actionId,
        status: "blocked",
        errorKey: "bridge.unavailable",
        message: "Colab runtime is not connected.",
      };
    }
    try {
      const response = (await this.fetchJson("api/action", {
        method: "POST",
        body: JSON.stringify(request),
      })) as BridgeResponse<T>;
      if (response.state) this.publish(response.state);
      return response;
    } catch (error) {
      return {
        requestId: request.requestId,
        actionId: request.actionId,
        status: "error",
        errorKey: "bridge.remote_error",
        message: error instanceof Error ? error.message : "Could not reach the Colab runtime.",
      };
    }
  }

  async revokePairing(): Promise<void> {
    await this.fetchJson("api/pairing/revoke", {
      method: "POST",
      body: JSON.stringify({}),
    });
  }

  disconnect() {
    this.disposed = true;
    this.connected = false;
    if (this.pollTimer !== null) clearInterval(this.pollTimer);
    this.pollTimer = null;
    this.listeners.clear();
    this.currentState = null;
  }
}
