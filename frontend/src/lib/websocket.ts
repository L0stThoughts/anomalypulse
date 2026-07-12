import type { WsMessage } from '../types';

export type WsCallback = (msg: WsMessage) => void;

const WS_BASE = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8080';

export class DashboardWebSocket {
  private ws: WebSocket | null = null;
  private callbacks: Set<WsCallback> = new Set();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private attempt = 0;
  private maxDelay = 30_000;
  private disposed = false;

  get connected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  connect() {
    if (this.disposed) return;
    this.cleanup();

    const ws = new WebSocket(`${WS_BASE}/ws/dashboard`);

    ws.onopen = () => {
      this.attempt = 0;
    };

    ws.onmessage = (ev) => {
      try {
        const msg: WsMessage = JSON.parse(ev.data);
        this.callbacks.forEach((cb) => cb(msg));
      } catch {
        // ignore malformed frames
      }
    };

    ws.onclose = () => {
      if (!this.disposed) this.scheduleReconnect();
    };

    ws.onerror = () => {
      ws.close();
    };

    this.ws = ws;
  }

  subscribe(cb: WsCallback) {
    this.callbacks.add(cb);
    return () => this.callbacks.delete(cb);
  }

  private scheduleReconnect() {
    const delay = Math.min(1000 * 2 ** this.attempt, this.maxDelay);
    this.attempt++;
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }

  private cleanup() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.onmessage = null;
      if (this.ws.readyState <= WebSocket.OPEN) this.ws.close();
    }
  }

  dispose() {
    this.disposed = true;
    this.cleanup();
    this.callbacks.clear();
  }
}

export const dashboardWs = new DashboardWebSocket();
