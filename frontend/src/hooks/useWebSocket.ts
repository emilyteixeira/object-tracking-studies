import { useCallback, useEffect, useRef, useState } from "react";
import { ConnectionStatus, FrameMessage } from "../types";

const WS_URL = "/ws"; // proxied via Vite → ws://localhost:8000/ws

const BACKOFF_STEPS = [1000, 2000, 4000, 8000, 16000, 30000];

export function useWebSocket() {
  const [latestMessage, setLatestMessage] = useState<FrameMessage | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("connecting");

  const wsRef = useRef<WebSocket | null>(null);
  const backoffIdx = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMounted = useRef(true);

  const connect = useCallback(() => {
    if (!isMounted.current) return;

    setStatus("connecting");
    const ws = new WebSocket(
      window.location.protocol === "https:"
        ? `wss://${window.location.host}/ws`
        : `ws://${window.location.host}/ws`
    );
    wsRef.current = ws;

    ws.onopen = () => {
      if (!isMounted.current) return;
      backoffIdx.current = 0;
      setStatus("connected");
    };

    ws.onmessage = (evt) => {
      if (!isMounted.current) return;
      try {
        const msg = JSON.parse(evt.data) as FrameMessage;
        setLatestMessage(msg);
      } catch {
        // ignora mensagens malformadas
      }
    };

    ws.onclose = () => {
      if (!isMounted.current) return;
      setStatus("disconnected");
      const delay = BACKOFF_STEPS[Math.min(backoffIdx.current, BACKOFF_STEPS.length - 1)];
      backoffIdx.current = Math.min(backoffIdx.current + 1, BACKOFF_STEPS.length - 1);
      reconnectTimer.current = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  const sendThreshold = useCallback((kmh: number) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "set_threshold", speed_threshold_kmh: kmh }));
    }
  }, []);

  useEffect(() => {
    isMounted.current = true;
    connect();
    return () => {
      isMounted.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { latestMessage, status, sendThreshold };
}
