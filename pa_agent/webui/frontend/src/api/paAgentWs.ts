import { useEffect, useRef, useState } from "react";
import type {
  AnalysisWsCancel,
  AnalysisWsInbound,
  AnalysisWsSubmit,
  KlineFrame,
  KlineWsInbound,
  KlineWsSubscribe,
} from "../types/domain";

const BACKOFF_BASE_MS = 500;
const BACKOFF_MAX_MS = 10_000;

function wsUrl(path: string): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${path}`;
}

export interface KlineSubscribeParams {
  source: string;
  symbol: string;
  timeframe: string;
  n_bars: number;
  interval_ms?: number;
}

export interface KlineSocketState {
  connected: boolean;
  frame: KlineFrame | null;
  statusMessage: string;
}

/** Subscribes to /ws/kline; re-sends `subscribe` whenever `params` changes and
 * reconnects with exponential backoff (0.5s..10s, mirroring RefreshLoop's own
 * backoff constants) on disconnect. Discards frames whose `epoch` is behind
 * the most recently acknowledged subscription (stale-frame filtering). */
export function useKlineSocket(params: KlineSubscribeParams | null): KlineSocketState {
  const [state, setState] = useState<KlineSocketState>({
    connected: false,
    frame: null,
    statusMessage: "",
  });
  const wsRef = useRef<WebSocket | null>(null);
  const epochRef = useRef(0);
  const reconnectAttempt = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const paramsRef = useRef(params);
  paramsRef.current = params;

  useEffect(() => {
    let cancelled = false;

    function connect() {
      if (cancelled) return;
      const ws = new WebSocket(wsUrl("/ws/kline"));
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttempt.current = 0;
        setState((s) => ({ ...s, connected: true }));
        if (paramsRef.current) {
          const msg: KlineWsSubscribe = { type: "subscribe", ...paramsRef.current };
          ws.send(JSON.stringify(msg));
        }
      };

      ws.onmessage = (ev) => {
        const msg: KlineWsInbound = JSON.parse(ev.data);
        if (msg.type === "subscribed") {
          epochRef.current = msg.epoch;
          return;
        }
        if (msg.epoch < epochRef.current) return; // stale frame from a superseded subscription
        if (msg.type === "frame") {
          setState((s) => ({ ...s, frame: msg.frame }));
        } else if (msg.type === "status" || msg.type === "error") {
          setState((s) => ({ ...s, statusMessage: msg.message }));
        }
      };

      ws.onclose = () => {
        setState((s) => ({ ...s, connected: false }));
        if (cancelled) return;
        const delay = Math.min(BACKOFF_BASE_MS * 2 ** reconnectAttempt.current, BACKOFF_MAX_MS);
        reconnectAttempt.current += 1;
        reconnectTimer.current = setTimeout(connect, delay);
      };

      ws.onerror = () => ws.close();
    }

    connect();
    return () => {
      cancelled = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN || !params) return;
    const msg: KlineWsSubscribe = { type: "subscribe", ...params };
    ws.send(JSON.stringify(msg));
  }, [params?.source, params?.symbol, params?.timeframe, params?.n_bars, params?.interval_ms]);

  return state;
}

export interface AnalysisSocketApi {
  connected: boolean;
  submit: (msg: AnalysisWsSubmit) => void;
  cancel: () => void;
}

/** Subscribes to /ws/analysis and relays every inbound message to `onMessage`.
 * Reconnects with the same backoff policy as `useKlineSocket`. */
export function useAnalysisSocket(onMessage: (msg: AnalysisWsInbound) => void): AnalysisSocketApi {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    let cancelled = false;

    function connect() {
      if (cancelled) return;
      const ws = new WebSocket(wsUrl("/ws/analysis"));
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttempt.current = 0;
        setConnected(true);
      };
      ws.onmessage = (ev) => {
        onMessageRef.current(JSON.parse(ev.data));
      };
      ws.onclose = () => {
        setConnected(false);
        if (cancelled) return;
        const delay = Math.min(BACKOFF_BASE_MS * 2 ** reconnectAttempt.current, BACKOFF_MAX_MS);
        reconnectAttempt.current += 1;
        reconnectTimer.current = setTimeout(connect, delay);
      };
      ws.onerror = () => ws.close();
    }

    connect();
    return () => {
      cancelled = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, []);

  function submit(msg: AnalysisWsSubmit) {
    wsRef.current?.send(JSON.stringify(msg));
  }

  function cancel() {
    const msg: AnalysisWsCancel = { type: "cancel" };
    wsRef.current?.send(JSON.stringify(msg));
  }

  return { connected, submit, cancel };
}
